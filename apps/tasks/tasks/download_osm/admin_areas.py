from prefect import task
from apps.catastro.models import AdministrativeArea
import osmium
from datetime import datetime
from django.contrib.gis.geos import Polygon, MultiPolygon
from apps.utils.fix_way import fix_polygon
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.db.models.functions import MakeValid
from django.db.models import F


@task
def admin_areas(king):

    ADMIN_LEVEL_MIN = 1
    ADMIN_LEVEL_MAX = 8
    KING_ID = king['id']  # osm_id king
    run_timestamp = datetime.now()
    inputfile = f'/tmp/osm-{king["name"]}.pbf'

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

    print(f'Collecting rels, using {inputfile}')
    h = RelsHandler()
    h.apply_file(inputfile)
    print('Collecting ways & nodes')
    h = WaysHandler()
    h.apply_file(inputfile, locations=True)

    admin_count_ok = 0
    admin_count_all = 0
    admin_count = 0
    print('Joining ways')
    for (k, v) in admin_relations.items():
        admin_count_all = admin_count_all + 1
        dbadminarea = AdministrativeArea.objects.filter(osm_id=v['osm_id'], osm_type=v['osm_type'])
        if dbadminarea:
            dbadminarea = dbadminarea[0]
            v['img_panorama'] = dbadminarea.img_panorama
            v['img_cuadrada'] = dbadminarea.img_cuadrada

        if v['admin_level'] >= ADMIN_LEVEL_MIN and v['admin_level'] <= ADMIN_LEVEL_MAX:
            print(f"osmid={k} level={v['admin_level']} name={v['name'].encode('utf-8')}", end="")
            wfull = [w for w in v['ways'] if not isinstance(w, int)]
            if len(wfull) == 0 or float(len(wfull)) / float(len(v['ways'])) < 0.8:
                print(f" NOK skipping adminarea, less than 80% of fragments")
                continue
            way, status = fix_polygon(wfull, 1000)
            if way is None:
                # si esta roto, buscar en la base de datos si hay uno con ese id y usar ese way
                print(f' ERROR: {status}')
                if dbadminarea:
                    way = dbadminarea.geometry
            else:
                admin_count = admin_count + 1
                print(f" OK -> {len(way)}")
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
                        print(f" {e}, retrying as multipolygon")
                        mp = []
                        for p in way:
                            p_fixed, status = fix_polygon(p, 1000)
                            if p_fixed:
                                try:
                                    mp.append(Polygon(p_fixed))
                                except Exception as e3:
                                    print(f" {e3} {status}, skipping fragment")
                        poly = MultiPolygon(mp)
                        v['geometry'] = poly
                        v['geometry_simple'] = poly.simplify(0.01, True)
                        if v['osm_id'] != KING_ID:
                            admin_areas[v['admin_level']].append(v)
                        print('-> ok')
                    except Exception as e2:
                        print(f" {e2}, error")
                if v['osm_id'] == KING_ID:
                    KING = v
    print(f"TOTALS: {admin_count_all} {admin_count} {admin_count_ok}, {len(admin_areas)}")

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
                    print(f" {aa['osm_id']}: {aa['name'].encode('utf-8').strip()}, does not have 'ways' attribute")
                if parent_aa is None:
                    tree['children'].append({'children': [], 'data': aa})
                else:
                    parent_aa['children'].append({'children': [], 'data': aa})
            except GEOSException as e:
                print(f'{str(e)}\n{tree["data"]["osm_id"]} {tree["data"]["name"].encode("utf-8")}\n{aa["osm_id"]} {aa["name"].encode("utf-8")}')

    def print_tree(node, level=0):
        print(f'{" " * level} {level} {node["data"]["name"].encode("utf-8")}')
        for node in node['children']:
            print_tree(node, level + 1)

    # print_tree(tree)
    print('saving admin areas tree...')
    AdministrativeArea.load_bulk([tree])
    print('finished saving admin areas')

    for K in OLD_KING:
        K.delete()

    # fix invalid geometries
    # TODO: I think these should be makeValid(ated) earlier in the process, not here but ASAP
    # that way we would avoid some issues around intersections that fail earlier in the process of creating the adminareas tree
    # the makevalid function is only available in postgis (is not in a library like GEOS)
    # in ~4000 shapes we had 10 not valid, so we can use something like `if not geom.valid: cursor.exec('SELECT ST_MAKEVALID(POLYGON('WKT text here'));')`
    AdministrativeArea.objects.filter(geometry_simple__isvalid=False).update(geometry_simple=MakeValid(F('geometry_simple')))
    AdministrativeArea.objects.filter(geometry__isvalid=False).update(geometry_simple=MakeValid(F('geometry')))
