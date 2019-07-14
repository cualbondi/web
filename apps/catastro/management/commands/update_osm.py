import traceback
import subprocess
import os
import sys
import time

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import F, Func, Value
from django.db.models import BooleanField
from django.db.models.functions import Upper, Trim, Substr
from django.db.models.expressions import RawSQL
from django.contrib.gis.geos import LineString, Polygon, MultiPolygon, Point
from django.contrib.gis.db.models.functions import MakeValid
from django.contrib.gis.geos.error import GEOSException

from apps.catastro.models import Poi, AdministrativeArea
from apps.core.models import Recorrido, ImporterLog, Parada, Horario
from apps.editor.models import RecorridoProposed
from apps.utils.fix_way import fix_way, fix_polygon

import osmium
from datetime import datetime
from urllib import request


class Nonegetter():
    def __getitem__(self, key):
        return None


kings = {
    'argentina': {
        'name': 'argentina',
        'url': 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf',
        'id': 286393,
        'paradas_completas': False,
    },
    'spain': {
        'name': 'spain',
        'url': 'http://download.geofabrik.de/europe/spain-latest.osm.pbf',
        'id': 1311341,
        'paradas_completas': True,
    }
}


class Command(BaseCommand):
    help = 'update local database with osm POIs and Streets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ciudad',
            action='store',
            dest='ciudad',
            help='Only import this ciudad slug'
        )
        parser.add_argument(
            '--pois',
            action='store_true',
            dest='pois',
            default=False,
            help='Build poi data from osm'
        )
        parser.add_argument(
            '--download',
            action='store_true',
            dest='download',
            default=False,
            help='Run importer/download routine from OSM'
        )
        parser.add_argument(
            '--update_routes',
            action='store_true',
            dest='update_routes',
            default=False,
            help='Update routes'
        )
        parser.add_argument(
            '--add_routes',
            action='store_true',
            dest='add_routes',
            default=False,
            help='Add routes'
        )
        parser.add_argument(
            '--admin_areas',
            action='store_true',
            dest='admin_areas',
            default=False,
            help='Update admin areas'
        )
        parser.add_argument(
            '--osm_id',
            action='store',
            dest='osm-id',
            default='',
            help='Update routes this osm id only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry-run',
            default=False,
            help='Do not save fixes'
        )
        parser.add_argument(
            '--king',
            action='store',
            dest='king',
            default='argentina',
            help='Name of the country to import the data from osm'
        )

    def reporthook(self, numblocks, blocksize, filesize, url=None):
        base = os.path.basename(url)
        try:
            percent = min((numblocks * blocksize * 100) / filesize, 100)
        except ZeroDivisionError:
            percent = 100
        if numblocks != 0:
            sys.stdout.write('\b' * 70)
        sys.stdout.write('%-66s%3d%%' % (base, percent))

    def out1(self, s):
        print('[{}] => {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))
        sys.stdout.flush()

    def out2(self, s, start=None, end='\n'):
        if start is None:
            print('[{}]    - {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s), end=end)
        else:
            print('{}'.format(s), end=end)
        sys.stdout.flush()

    def handle(self, *args, **options):

        king = kings[options['king']]

        run_timestamp = datetime.now()

        cu = connection.cursor()

        inputfile = f'/tmp/osm-{king["name"]}.pbf'

        if options['download']:

            self.out1(f'Descargando mapa de {king["name"]} de geofabrik')
            # url = 'http://download.geofabrik.de/south-america-latest.osm.pbf'
            url = king['url']
            self.out2(url)
            f, d = request.urlretrieve(url, inputfile, lambda nb, bs, fs, url=url: self.reporthook(nb, bs, fs, url))

        #######################
        #  Adminareas de osm  #
        #######################
        # 1. ./manage.py update_osm --download --admin_areas
        # 2. ./manage.py update_osm -f /tmp/part-all.o5m --admin_areas

        if options['admin_areas']:
            self.out1('Admin Areas')

            ADMIN_LEVEL_MIN = 1
            ADMIN_LEVEL_MAX = 8
            KING_ID = king['id']  # osm_id king

            OLD_KING = list(AdministrativeArea.objects.filter(osm_id=KING_ID))
            KING = None

            admin_areas = [[] for i in range(12)]  # index: admin_level, value
            admin_relations = {}  # index: admin_level, value
            admin_relations_ways_ids = {}
            # this = self

            class RelsHandler(osmium.SimpleHandler):
                def relation(self, r):
                    if 'boundary' in r.tags and r.tags['boundary'] == 'administrative' and 'name' in r.tags and 'admin_level' in r.tags:  # and r.id == KING_ID:
                        ways = []
                        for m in r.members:
                            # outer (parts and exclaves) / inner (hole)
                            if m.type == 'w' and m.role in ['outer']:
                                ways.append(m.ref)
                                admin_relations_ways_ids.setdefault(m.ref, []).append(r.id)
                        try:
                            admin_level = int(r.tags['admin_level'])
                        except ValueError:
                            return
                        admin_relations[r.id] = {
                            'import_timestamp': run_timestamp,
                            'osm_id': r.id,
                            'osm_type': 'r',
                            'ways': ways,
                            'admin_level': admin_level,
                            'name': r.tags['name'],  # .encode('utf-8').strip(),
                            'tags': r.tags.__dict__,
                        }
                        # this.out2(f"REL {r.id} {r.tags['name'].encode('utf-8').strip()}")

            class WaysHandler(osmium.SimpleHandler):
                def way(self, w):

                    # ways that are admin areas
                    if 'boundary' in w.tags and w.tags['boundary'] == 'administrative' and 'name' in w.tags and 'admin_level' in w.tags:
                        linestring = []
                        for node in w.nodes:
                            linestring.append([float(node.x) / 10000000, float(node.y) / 10000000])
                        if linestring[0][0] == linestring[-1][0] and linestring[0][1] == linestring[-1][1]:
                            if int(w.tags['admin_level']) >= ADMIN_LEVEL_MIN and int(w.tags['admin_level']) <= ADMIN_LEVEL_MAX:
                                poly = Polygon(linestring)
                                admin_areas[int(w.tags['admin_level'])].append({
                                    'import_timestamp': run_timestamp,
                                    'osm_id': w.id,
                                    'osm_type': 'w',
                                    'geometry': poly,
                                    'geometry_simple': poly.simplify(0.01, True),
                                    'admin_level': int(w.tags['admin_level']),
                                    'name': w.tags['name'],  # .encode('utf-8').strip(),
                                    'tags': w.tags.__dict__,
                                })

                    # fill relations that are admin areas
                    if w.id in admin_relations_ways_ids:
                        linestring = []
                        for node in w.nodes:
                            linestring.append([float(node.x) / 10000000, float(node.y) / 10000000])

                        for rel_id in admin_relations_ways_ids[w.id]:
                            for i, wid in enumerate(admin_relations[rel_id]['ways']):
                                if wid == w.id:
                                    admin_relations[rel_id]['ways'][i] = linestring

            self.out2(f'Collecting rels, using {inputfile}')
            h = RelsHandler()
            h.apply_file(inputfile)
            self.out2('Collecting ways & nodes')
            h = WaysHandler()
            h.apply_file(inputfile, locations=True)

            admin_count_ok = 0
            admin_count_all = 0
            admin_count = 0
            self.out2('Joining ways')
            for (k, v) in admin_relations.items():
                admin_count_all = admin_count_all + 1
                dbadminarea = AdministrativeArea.objects.filter(osm_id=v['osm_id'], osm_type=v['osm_type'])
                if dbadminarea:
                    dbadminarea = dbadminarea[0]
                    v['img_panorama'] = dbadminarea.img_panorama
                    v['img_cuadrada'] = dbadminarea.img_cuadrada

                if v['admin_level'] >= ADMIN_LEVEL_MIN and v['admin_level'] <= ADMIN_LEVEL_MAX:
                    self.out2(f"osmid={k} level={v['admin_level']} name={v['name'].encode('utf-8')}", end="")
                    wfull = [w for w in v['ways'] if not isinstance(w, int)]
                    if len(wfull) == 0 or float(len(wfull)) / float(len(v['ways'])) < 0.8:
                        self.out2(f" NOK skipping adminarea, less than 80% of fragments")
                        continue
                    way, status = fix_polygon(wfull, 1000)
                    if way is None:
                        # si esta roto, buscar en la base de datos si hay uno con ese id y usar ese way
                        self.out2(f' ERROR: {status}')
                        if dbadminarea:
                            way = dbadminarea.geometry
                    else:
                        admin_count = admin_count + 1
                        self.out2(f" OK -> {len(way)}")
                        # last point equals first
                        admin_count_ok = admin_count_ok + 1
                        try:
                            poly = Polygon(way)
                            v['geometry'] = poly
                            v['geometry_simple'] = poly.simplify(0.01, True)
                            if v['osm_id'] != KING_ID:
                                admin_areas[v['admin_level']].append(v)
                        except Exception as e:
                            try:
                                self.out2(f" {e}, retrying as multipolygon")
                                mp = []
                                for p in way:
                                    p_fixed, status = fix_polygon(p, 1000)
                                    if p_fixed:
                                        try:
                                            mp.append(Polygon(p_fixed))
                                        except Exception as e3:
                                            self.out2(f" {e3} {status}, skipping fragment")
                                poly = MultiPolygon(mp)
                                v['geometry'] = poly
                                v['geometry_simple'] = poly.simplify(0.01, True)
                                if v['osm_id'] != KING_ID:
                                    admin_areas[v['admin_level']].append(v)
                                self.out2('-> ok')
                            except Exception as e2:
                                traceback.print_exc()
                                self.out2(f" {e2}, error")
                        if v['osm_id'] == KING_ID:
                            KING = v
            self.out2(f"TOTALS: {admin_count_all} {admin_count} {admin_count_ok}, {len(admin_areas)}")

            def fuzzy_contains(out_geom, in_geom, buffer=0):
                return (
                    out_geom.intersects(in_geom) and  # optimization
                    out_geom.buffer(buffer).contains(in_geom)
                )

            KING_GEOM_BUFF = KING['geometry_simple'].buffer(0.01)

            def get_parent_aa(node, geometry):
                try:
                    if (
                        node['data']['osm_id'] is KING_ID or
                        fuzzy_contains(node['data']['geometry_simple'], geometry, 0.01)
                    ):
                        parent_aa = None
                        for child in node['children']:
                            parent_aa = get_parent_aa(child, geometry)
                            if parent_aa is not None:
                                break
                        if parent_aa is None:
                            return node
                        else:
                            return parent_aa
                    else:
                        return None
                except Exception:
                    # print('node.geometry', node['data']['geometry'])
                    print('node.data', node['data']['name'].encode('utf-8'))
                    print('node.osm_id', node['data']['osm_id'])
                    print('node.osm_type', node['data']['osm_type'])
                    traceback.print_exc()
                    raise

            tree = {
                'children': [],
                'data': {
                    'import_timestamp': run_timestamp,
                    'geometry': KING['geometry_simple'],
                    'geometry_simple': KING['geometry_simple'],
                    'osm_id': KING['osm_id'],
                    'osm_type': KING['osm_type'],
                    'name': KING['name'],
                    'tags': KING['tags'],
                }
            }
            for li in admin_areas:
                # aa = admin area
                for aa in li:
                    if not aa['geometry'].intersects(KING_GEOM_BUFF):
                        continue
                    try:
                        parent_aa = get_parent_aa(tree, aa['geometry'])
                        aa.pop('admin_level')
                        if 'ways' in aa:
                            aa.pop('ways')
                        else:
                            self.out2(f" {aa['osm_id']}: {aa['name'].encode('utf-8').strip()}, does not have 'ways' attribute")
                        if parent_aa is None:
                            tree['children'].append({'children': [], 'data': aa})
                        else:
                            parent_aa['children'].append({'children': [], 'data': aa})
                    except GEOSException as e:
                        self.out2(f'{str(e)}\n{tree["data"]["osm_id"]} {tree["data"]["name"].encode("utf-8")}\n{aa["osm_id"]} {aa["name"].encode("utf-8")}')

            def print_tree(node, level=0):
                print(f'{" " * level} {level} {node["data"]["name"].encode("utf-8")}')
                for node in node['children']:
                    print_tree(node, level + 1)

            # print_tree(tree)

            AdministrativeArea.load_bulk([tree])

            for K in OLD_KING:
                K.delete()

            # fix invalid geometries
            # TODO: I think these should be makeValid(ated) earlier in the process, not here but ASAP
            # that way we would avoid some issues around intersections that fail earlier in the process of creating the adminareas tree
            # the makevalid function is only available in postgis (is not in a library like GEOS)
            # in ~4000 shapes we had 10 not valid, so we can use something like `if not geom.valid: cursor.exec('SELECT ST_MAKEVALID(POLYGON('WKT text here'));')`
            AdministrativeArea.objects.filter(geometry_simple__isvalid=False).update(geometry_simple=MakeValid(F('geometry_simple')))
            AdministrativeArea.objects.filter(geometry__isvalid=False).update(geometry_simple=MakeValid(F('geometry')))

        #######################
        #  recorridos de osm  #
        #######################

        if options['update_routes']:
            # TODO: consider also trains / trams / things that have fixed stops

            self.out1('UPDATE ROUTES FROM OSM')
            self.out2('process .osm input file')

            # we can see if all tags are ok and give hints to mappers according to spec:
            # https://wiki.openstreetmap.org/w/index.php?oldid=625726
            # https://wiki.openstreetmap.org/wiki/Buses

            buses = {}  # pasar a self.buses { relation_id: { name: name, fixed_way: GEOSGeom, ways: { way_id: { name: name, nodes: { node_id: { lat: lat, lng: lng } } } } } }
            ways = {}  # aux structure { way_id: [ relation_id ] }
            stops = {}  # aux structure { node_id: [ relation_id ] }

            route_id_only = int(options['osm-id']) if options['osm-id'] else ''

            class RelsHandler(osmium.SimpleHandler):
                def relation(self, r):
                    routetypes_stops = ['train', 'subway', 'monorail', 'tram', 'light_rail']
                    routetypes = routetypes_stops + ['bus', 'trolleybus']
                    if ((not route_id_only or r.id == route_id_only) and 'route' in r.tags and r.tags['route'] in routetypes and 'name' in r.tags):
                        paradas_completas = None
                        if r.tags['route'] in routetypes_stops:
                            paradas_completas = True
                        bus = {
                            'name': r.tags['name'][:200],
                            'ways': [],
                            'stops': [],
                            'timestamp': r.timestamp,
                            'version': r.version,
                            'paradas_completas': paradas_completas,
                            'type': r.tags['route'],
                        }
                        for m in r.members:
                            # forward / backward / alternate are deprecated in PTv2, add warning
                            if m.type == 'w' and m.role in ['', 'forward', 'backward', 'alternate']:
                                bus['ways'].append(m.ref)
                                ways.setdefault(m.ref, []).append(r.id)
                            if m.type == 'n' and m.role in ['stop', ]:
                                bus['stops'].append(m.ref)
                                stops.setdefault(m.ref, []).append(r.id)
                        if len(bus['stops']) > 20:
                            bus['paradas_completas'] = True
                        buses[r.id] = bus

            class WaysHandler(osmium.SimpleHandler):
                def way(self, w):
                    if w.id in ways:
                        linestring = []
                        for node in w.nodes:
                            linestring.append([float(node.x) / 10000000, float(node.y) / 10000000])

                        for rel_id in ways[w.id]:
                            for i, wid in enumerate(buses[rel_id]['ways']):
                                if wid == w.id:
                                    buses[rel_id]['ways'][i] = linestring

            class NodesHandler(osmium.SimpleHandler):
                def node(self, n):
                    if n.id in stops:
                        stop = {
                            'osm_id': n.id,
                            'name': n.tags['name'][:200] if 'name' in n.tags else '',
                            'point': Point([float(n.location.x) / 10000000, float(n.location.y) / 10000000]),
                            'tags': n.tags,
                        }

                        for rel_id in stops[n.id]:
                            for i, nid in enumerate(buses[rel_id]['stops']):
                                if nid == n.id:
                                    buses[rel_id]['stops'][i] = stop

            self.out2('relations')
            h = RelsHandler()
            h.apply_file(inputfile)
            self.out2('ways')
            h = WaysHandler()
            h.apply_file(inputfile, locations=True)
            self.out2('nodes (stops)')
            h = NodesHandler()
            h.apply_file(inputfile)

            self.out2('fixer routine')

            counters = {}
            for bus_id, bus in buses.items():
                self.out2(bus_id, end=': ')
                way, status = fix_way(bus['ways'], 150)
                buses[bus_id]['way'] = LineString(way) if way else None
                buses[bus_id]['status'] = status
                counters.setdefault(status, 0)
                counters[status] += 1
                self.out2('{} > {}'.format(status, bus['name'].encode('utf-8').strip()), start='')

            for key, counter in sorted(counters.items(), key=lambda e: e[1], reverse=True):
                self.out2('{} | {}'.format(counter, key))

            # HINT: run migrations in order to have osmbot in the db
            user_bot_osm = get_user_model().objects.get(username='osmbot')

            self.out2('fixer routine')

            # add all as new routes
            if options['add_routes']:

                for bus_osm_id, bus in buses.items():
                    # try to fix way, returns None if it can't
                    way = bus['way']
                    status = bus['status']

                    # recorrido proposed creation checks
                    if bus['way'] is None:
                        self.out2('{} : SKIP {}'.format(bus_osm_id, bus['status']))
                        continue

                    # set proposal fields
                    # rp.paradas_completas = len(bus['stops']) > options['paradas_completas_threshold'] o usar una config en el pais KINGs
                    rp = RecorridoProposed(nombre=bus['name'])
                    rp.osm_id = bus_osm_id
                    rp.ruta = bus['way']
                    rp.ruta_last_updated = bus['timestamp']
                    rp.osm_version = bus['version']
                    rp.import_timestamp = run_timestamp
                    rp.paradas_completas = bus['paradas_completas'] if bus['paradas_completas'] is not None else king['paradas_completas']
                    rp.type = bus['type']
                    if not options['dry-run']:
                        rp.save(user=user_bot_osm)

                    self.out2('{} | AUTO ACCEPTED!'.format(bus_osm_id))
                    if not options['dry-run']:
                        rp.aprobar(user_bot_osm)

                    # add stops!
                    if not options['dry-run'] and len(bus['stops']) > 0:
                        self.out2(f'ADDing STOPS {len(bus["stops"])}', end=' > ')
                        count_created = 0
                        count_associated = 0
                        for s in bus['stops']:
                            if isinstance(s, dict):
                                parada, created = Parada.objects.update_or_create(
                                    osm_id=s['osm_id'],
                                    defaults={
                                        'import_timestamp': run_timestamp,
                                        'nombre': s['name'],
                                        'latlng': s['point'],
                                        'tags': s['tags'].__dict__,
                                    }
                                )
                                if created:
                                    count_created = count_created + 1
                                horario, created = Horario.objects.update_or_create(
                                    recorrido=rp.recorrido,
                                    parada=parada,
                                )
                                if created:
                                    count_associated = count_associated + 1
                        self.out2(f'CREATED STOPS {count_created}, ASSOCIATED {count_associated}')

            else:

                for rec in Recorrido.objects.filter(osm_id__isnull=False, ruta__intersects=AdministrativeArea.objects.get(osm_id=king['id']).geometry):
                    # try to fix way, returns None if it can't
                    adminareas_str = ', '.join(AdministrativeArea.objects.filter(geometry__intersects=rec.ruta).order_by('depth').values_list('name', flat=True))
                    osm_id = rec.osm_id
                    if osm_id in buses:
                        way = buses[osm_id]['way']
                        status = buses[osm_id]['status']
                        osm_osm_version = buses[osm_id]['version']
                        osm_last_updated = buses[osm_id]['timestamp']
                        name = buses[osm_id]['name']
                        paradas_completas = buses[osm_id]['paradas_completas']
                        routetype = buses[osm_id]['type']
                    else:
                        way = None
                        status = None
                        osm_osm_version = -1
                        osm_last_updated = None
                        name = None
                        paradas_completas = None
                        routetype = None

                    ilog = ImporterLog(
                        osm_id=osm_id,
                        osm_version=osm_osm_version,
                        osm_timestamp=osm_last_updated,
                        run_timestamp=run_timestamp,
                        proposed=False,
                        accepted=False,
                        status=status,
                        proposed_reason='',
                        accepted_reason='',
                        osm_administrative=adminareas_str,
                        osm_name=name,
                        type=routetype,
                        king=king['name'],
                    )
                    ilog.save()

                    # recorrido proposed creation checks
                    if way is None:
                        self.out2('{} | {} : SKIP {}'.format(rec.id, osm_id, status))
                        ilog.proposed_reason = 'broken'
                        ilog.save()
                        continue

                    if rec.ruta_last_updated >= osm_last_updated:
                        self.out2('{} | {} : SKIP, older than current recorrido {}, ({} >= {})'.format(rec.id, osm_id, status, rec.ruta_last_updated, osm_last_updated))
                        ilog.proposed_reason = 'older than current recorrido'
                        ilog.save()
                        continue

                    # check if there is another proposal already submitted (with same timestamp or greater)
                    if RecorridoProposed.objects.filter(osm_id=osm_id, parent=rec.uuid, ruta_last_updated__gte=osm_last_updated).exists():
                        self.out2('{} | {} : SKIP, older than prev proposal {}'.format(rec.id, osm_id, status))
                        ilog.proposed_reason = 'older than previous proposal'
                        ilog.save()
                        continue

                    # update previous proposal if any
                    previous_proposals = RecorridoProposed.objects.filter(
                        osm_id=osm_id,
                        parent=rec.uuid,
                        ruta_last_updated__lt=osm_last_updated,
                        logmoderacion__newStatus='E'
                    ).order_by('-ruta_last_updated')
                    if len(previous_proposals) > 0:
                        proposal_info = 'UPDATE prev proposal'
                        rp = previous_proposals[0]
                    # else create a new proposal
                    else:
                        proposal_info = 'NEW prev proposal'
                        rp = RecorridoProposed.from_recorrido(rec)

                    # set proposal fields
                    rp.ruta = way
                    rp.ruta_last_updated = osm_last_updated
                    rp.osm_version = osm_osm_version  # to not be confsed with Recorrido.osm_version
                    rp.import_timestamp = run_timestamp
                    rp.paradas_completas = paradas_completas if paradas_completas is not None else king['paradas_completas']
                    rp.type = routetype
                    if not options['dry-run']:
                        rp.save(user=user_bot_osm)

                    ilog.proposed = True
                    ilog.save()

                    # AUTO ACCEPT CHECKS
                    if rec.osm_version is None:
                        self.out2('{} | {} : {} | NOT auto accepted: previous accepted proposal does not come from osm'.format(rec.id, osm_id, proposal_info))
                        ilog.accepted_reason = 'previous accepted proposal does not come from osm'
                        ilog.save()
                        continue

                    if RecorridoProposed.objects.filter(parent=rec.uuid).count() > 1:
                        self.out2('{} | {} : {} | NOT auto accepted: another not accepted recorridoproposed exists for this recorrido'.format(rec.id, osm_id, proposal_info))
                        ilog.accepted_reason = 'another not accepted proposal exists for this recorrido'
                        ilog.save()
                        continue

                    self.out2('{} | {} : {} | AUTO ACCEPTED!'.format(rec.id, osm_id, proposal_info))
                    if not options['dry-run']:
                        rp.aprobar(user_bot_osm)

                    ilog.accepted = True
                    ilog.save()

                #
                # TODO: think how to do "stops" change proposals
                # el recorrido podria tener una lista de paradas, una lista de latlongs nada mas
                # cambiar una parada es cambiar el recorrido tambien. El problema es que las paradas se comparten
                #

        #######################
        #  POIs de osm        #
        #######################

        if options['pois']:

            self.out2('Eliminando indices viejos de la base de datos')
            # cu.execute('DROP INDEX IF EXISTS catastrocalle_nomnormal_gin;')
            cu.execute('DROP INDEX IF EXISTS catastropoi_nomnormal_gin;')

            self.out2('counting')
            result = subprocess.run(f'osmium fileinfo -g data.count.nodes -e {inputfile}'.split(' '), stdout=subprocess.PIPE)
            nodes_count = int(result.stdout)
            self.out2(f'end counting = {nodes_count}')

            class Unaccent(Func):
                function = 'UNACCENT'
                arity = 1

            class RegexpReplace(Func):
                function = 'REGEXP_REPLACE'
                arity = 3

            class POIsHandler(osmium.SimpleHandler):

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.nodes_current = 0
                    self.nodes_added = 0

                # # TODO: necesito las calles por ahora? son muchas en espana
                # def way(self, w):
                #     if 'highway' in w.tags and 'route' not in w.tags and 'name' in w.tags:
                #         points = []
                #         for node in w.nodes:
                #             points.append([float(node.x) / 10000000, float(node.y) / 10000000])
                #         linestring = LineString(points, srid=4326)
                #         if Recorrido.objects.filter(ruta__intersects=linestring).exists():
                #             print('|', end='')
                #             Calle.objects.update_or_create(
                #                 osm_id=w.id,
                #                 defaults={
                #                     'nom': w.tags['name'][:200],
                #                     'nom_normal': Substr(Trim(RegexpReplace(Upper(Unaccent(Value(w.tags['name']))), r'AV\.|AVENIDA|CALLE|DIAGONAL|BOULEVARD', '')), 1, 199),
                #                     'way': linestring,
                #                 }
                #             )

                def node(self, n):
                    self.nodes_current += 1
                    if 'amenity' in n.tags and 'name' in n.tags and len(n.tags['name']) > 2:
                        point = Point([float(n.location.x) / 10000000, float(n.location.y) / 10000000], srid=4326)
                        # this is a little slow, but it uses indexes :)
                        q = Recorrido.objects \
                            .order_by() \
                            .annotate(cond=RawSQL("ST_Intersects(ST_Buffer(%s::geography, 400, 2)::geometry, ruta)", (point.ewkb,), output_field=BooleanField())) \
                            .filter(cond=True) \
                            .only('id')
                        if q:
                            defaults = {
                                'tags': n.tags.__dict__,
                                'nom': n.tags['name'][:200],
                                'nom_normal': Substr(Trim(Upper(Unaccent(Value(n.tags['name'])))), 1, 200),
                                'latlng': point,
                            }
                            Poi.objects.update_or_create(
                                osm_id=n.id,
                                osm_type='n',
                                defaults=defaults
                            )
                            self.nodes_added += 1
                            print(f'[{self.nodes_current*100/nodes_count:7.3f}%] / Nodes added: {self.nodes_added} | processed: {self.nodes_current} / {nodes_count}')

            self.out2('POIS from ways and nodes with osmosis')
            h = POIsHandler()
            with transaction.atomic():
                h.apply_file(inputfile, locations=True)

            self.out2('POIS from AdministrativeAreas in database')
            adminareas = AdministrativeArea.objects.get(osm_id=king['id']).get_descendants()
            adminareascount = adminareas.count()
            i = 0
            for aa in adminareas:
                i = i + 1
                self.out2(f' [{i*100/adminareascount:7.3f}%] {aa.name}')
                Poi.objects.update_or_create(
                    osm_id=aa.osm_id,
                    osm_type=aa.osm_type,
                    defaults={
                        'tags': aa.tags,
                        'nom': aa.name,
                        'nom_normal': Substr(Trim(Upper(Unaccent(Value(aa.name)))), 1, 200),
                        'latlng': aa.geometry.centroid,
                    }
                )

            self.out2('Generando slugs')
            total = Poi.objects.filter(slug__isnull=True).count()
            i = 0
            start = time.time()
            for o in Poi.objects.filter(slug__isnull=True):
                o.save()
                i = i + 1
                if i % 50 == 0 and time.time() - start > 1:
                    start = time.time()
                    self.out2('{}/{} ({:2.0f}%)'.format(i, total, i * 100.0 / total))

            # unir catastro_poicb (13 y 60, 13 y 66, 13 y 44) con catastro_poi (osm_pois)
            # self.out2('Mergeando POIs propios de cualbondi')
            # for poicb in Poicb.objects.all():
            #     Poi.objects.create(nom_normal = poicb.nom_normal.upper(), nom = poicb.nom, latlng = poicb.latlng)
            # self.out2('Purgando nombres repetidos')
            # cu.execute('delete from catastro_poi where id not in (select min(id) from catastro_poi group by nom_normal)')

            self.out1('Regenerando indices')
            # self.out2('Generando catastro_calle')
            # cu.execute('CREATE INDEX catastrocalle_nomnormal_gin ON catastro_calle USING gin (nom_normal gin_trgm_ops);')
            self.out2('Generando catastro_poi')
            cu.execute('CREATE INDEX catastropoi_nomnormal_gin ON catastro_poi USING gin (nom_normal gin_trgm_ops);')

        # self.out1('Eliminando tablas no usadas')
        # cu.execute('drop table planet_osm_roads;')
        # cu.execute('drop table planet_osm_polygon;')
        # cx.commit()
        # cx.close()

        self.out1('LISTO!')
