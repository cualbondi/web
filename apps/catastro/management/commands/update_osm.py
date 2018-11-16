from django.core.management.base import BaseCommand
from urllib import request
import subprocess
import os
import sys
from apps.catastro.models import Poi, Interseccion, Calle
from apps.core.models import Recorrido, ImporterLog
from apps.editor.models import RecorridoProposed
from apps.utils.fix_way import fix_way
from django.contrib.auth import get_user_model
from django.db import connection
from datetime import datetime
import time

import osmium
import geopandas as gpd
from psycopg2.extras import execute_values
from django.contrib.gis.geos import LineString, MultiLineString


class Command(BaseCommand):
    help = 'update local database with osm POIs and Streets'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            action='store',
            dest='inputFile',
            default='',
            help='Use an input file instead of trying to download osm data'
        )
        parser.add_argument(
            '--use-cache',
            action='store_true',
            dest='use_cache',
            default=False,
            help='Use the cache of downloaded osm'
        )
        parser.add_argument(
            '-s',
            action='store_true',
            dest='slim',
            default=False,
            help='Set osm2pgsql slim mode (create raw tables: nodes, rels, ways)'
        )
        parser.add_argument(
            '--no-o2p',
            action='store_true',
            dest='no-o2p',
            default=False,
            help='Ignore osm2pgsql execution (debug purposes only)'
        )
        parser.add_argument(
            '--no-tmp',
            action='store_true',
            dest='no-tmp',
            default=False,
            help='Don\'t use /tmp folder, instead use apps/catastro/management/commands folder to save the downloaded argentina.osm.pbf file'
        )
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
            '--cross',
            action='store_true',
            dest='cross',
            default=False,
            help='Build cross data from planet_osm_line'
        )
        parser.add_argument(
            '--import_osm',
            action='store_true',
            dest='import_osm',
            default=False,
            help='Run importer/download routine from OSM'
        )
        parser.add_argument(
            '--intersections',
            action='store_true',
            dest='intersections',
            default=False,
            help='Run intersections routine'
        )
        parser.add_argument(
            '--update_routes',
            action='store_true',
            dest='update_routes',
            default=False,
            help='Update routes'
        )
        parser.add_argument(
            '--osm_id',
            action='store',
            dest='osm-id',
            default='',
            help='Update routes this osm id only'
        )
        parser.add_argument(
            '--all_arg',
            action='store_true',
            dest='all_arg',
            default=False,
            help='Use all arg (do not import ONLY cities)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry-run',
            default=False,
            help='Do not save fixes'
        )

    def reporthook(self, numblocks, blocksize, filesize, url=None):
        base = os.path.basename(url)
        try:
            percent = min((numblocks * blocksize * 100) / filesize, 100)
        except:
            percent = 100
        if numblocks != 0:
            sys.stdout.write('\b' * 70)
        sys.stdout.write('%-66s%3d%%' % (base, percent))

    def out1(self, s):
        print('[{}] => {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))

    def out2(self, s, start=None, end='\n'):
        if start is None:
            print('[{}]    - {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s), end=end)
        else:
            print('{}'.format(s), end=end)

    def handle(self, *args, **options):

        run_timestamp = datetime.now()

        cu = connection.cursor()

        inputfile = '/tmp/argentina.cache.osm-{}.pbf'.format(datetime.now().strftime('%Y%m%d%H%M%S'))
        if options['no-tmp']:
            inputfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'argentina.cache.osm.pbf')
        if options['inputFile'] or options['use_cache']:
            if options['inputFile']:
                inputfile = options['inputFile']

        if options['import_osm']:

            inputfile = '/tmp/argentina.cache.osm-{}.pbf'.format(datetime.now().strftime('%Y%m%d%H%M%S'))
            if options['no-tmp']:
                inputfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'argentina.cache.osm.pbf')
            if options['inputFile'] or options['use_cache']:
                if options['inputFile']:
                    inputfile = options['inputFile']
            else:
                self.out1('Descargando mapa de Argentina de geofabrik')
                url = 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf'
                self.out2(url)
                f, d = request.urlretrieve(url, inputfile, lambda nb, bs, fs, url=url: self.reporthook(nb, bs, fs, url))

            dbname = connection.settings_dict['NAME']
            dbuser = connection.settings_dict['USER']
            dbpass = connection.settings_dict['PASSWORD']
            dbhost = connection.settings_dict['HOST']

            cu = connection.cursor()
            cu.execute('SELECT slug, box(poligono::geometry) as box FROM catastro_ciudad;')

            # TODO: osmconvert /tmp/argentina.cache.osm-20160711192104.pbf -b=-57.8526306071815,-38.1354198737499,-57.5065612712919,-37.8562051788731 -o=1.pbf

            self.out1('Cargando data de osm en la base de cualbondi')

            filetoimport = inputfile

            if not options['all_arg']:
                self.out2('only-cities')
                ciudades = cu.fetchall()
                for c in ciudades:

                    # if options.ciudad is defined, and this is not it, skip it
                    if options['ciudad'] and options['ciudad'] != c[0]:
                        continue

                    l = c[1][1:-1].replace(')', '').replace('(', '').split(',')
                    box = ','.join([l[2], l[3], l[0], l[1]])
                    self.out2('{} ({})'.format(c[0], box))
                    prog = [
                        'osmconvert',
                        inputfile,
                        '-b={}'.format(box),
                        '-o=/tmp/part-{}.osm'.format(c[0])
                    ]
                    filetoimport = '/tmp/part-all.o5m'
                    subprocess.Popen(prog).wait()

                self.out2('Uniendo partes')
                partfiles = ['/tmp/part-{}.osm'.format(c[0]) for c in ciudades]
                prog = [
                    'osmconvert',
                    '-o={}'.format(filetoimport)
                ] + partfiles
                subprocess.Popen(prog).wait()
            else:
                filetoimport = '/tmp/part-all.o5m'
                prog = [
                    'osmconvert',
                    '-o={}'.format(filetoimport),
                    inputfile
                ]
                subprocess.Popen(prog).wait()
                self.out2('all Argentina')

            self.out2('Cargando en la base de datos')
            prog = [
                'osm2pgsql',
                '--latlong',
                '--style={}'.format(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'update-osm.style')),
                '--database={}'.format(dbname),
                '--username={}'.format(dbuser),
                '--host={}'.format(dbhost),
                '--create',
                '--number-processes=4',
                '--hstore-all',
                '--extra-attributes',
                filetoimport
            ]
            if options['slim']:
                prog.append('-s')
            self.out2('ejecutando:',)
            self.out2(' '.join(prog))
            if not options['no-o2p']:
                p = subprocess.Popen(prog, env={'PGPASSWORD': dbpass})
                p.wait()

            # POST PROCESAMIENTO
            self.out1('POSTPROCESO')
            self.out1('Dando nombres alternativos a los objetos sin nombre')
            self.out2('planet_osm_line')
            cu.execute('update planet_osm_line    set name=ref where name is null;')
            self.out2('planet_osm_point')
            cu.execute('update planet_osm_point   set name=ref where name is null;')
            self.out2('planet_osm_polygon')
            cu.execute('update planet_osm_polygon set name=ref where name is null;')

        #######################
        #  recorridos de osm  #
        #######################

        if options['cross']:

            crs = {'init': 'epsg:4326'}

            self.out1('Cross osm recorridos')
            self.out2('Obteniendo bus routes de osm planet_osm_line')
            bus_routes = gpd.read_postgis(
                """
                    SELECT
                        @osm_id AS osm_id, -- @=modulus operator
                        name,
                        ref,
                        st_linemerge(st_union(way)) AS way
                    FROM
                        planet_osm_line
                    WHERE
                        route = 'bus'
                    GROUP BY
                        osm_id,
                        name,
                        ref
                """,
                connection,
                geom_col='way',
                crs=crs
            )
            bus_routes.set_index('osm_id', inplace=True)

            self.out2('Creando geodataframe')
            bus_routes_buffer = gpd.GeoDataFrame({
                'osm_id': bus_routes.index,
                'way': bus_routes.way,
                'way_buffer_40': bus_routes.way.buffer(0.0004),
                'way_buffer_40_simplify': bus_routes.way.simplify(0.0001).buffer(0.0004),
                'name': bus_routes.name
            }, crs=crs).set_geometry('way_buffer_40_simplify')

            self.out2('Obteniendo recorridos de cualbondi core_recorridos')
            core_recorrido = gpd.read_postgis(
                """
                    SELECT
                        cr.id,
                        cr.nombre,
                        cr.linea_id,
                        cr.ruta,
                        cl.nombre AS linea_nombre
                    FROM
                        core_recorrido cr
                        JOIN core_linea cl ON (cr.linea_id = cl.id)
                    --  JOIN catastro_ciudad_recorridos ccr ON (ccr.recorrido_id = cr.id)
                    --WHERE
                    --    ccr.ciudad_id = 1
                    ;
                """,
                connection,
                geom_col='ruta',
                crs=crs
            )
            core_recorrido.set_index('id', inplace=True)

            self.out2('Creando geodataframe')
            core_recorrido_buffer = gpd.GeoDataFrame({
                'id': core_recorrido.index,
                'ruta': core_recorrido.ruta.simplify(0.0001),
                'ruta_buffer_40_simplify': core_recorrido.ruta.simplify(0.0001).buffer(0.0004),
                'nombre': core_recorrido.nombre,
                'linea_id': core_recorrido.linea_id,
            }, crs=crs).set_geometry('ruta')

            self.out2('Generando intersecciones')
            intersections = gpd.sjoin(core_recorrido_buffer, bus_routes_buffer, how='inner', op='intersects')

            self.out2('Copiando indice, id')
            intersections['id'] = intersections.index

            self.out2('Copiando indice, osm_id')
            intersections['osm_id'] = intersections.index_right

            self.out2('Drop indice, osm_id')
            intersections.drop('index_right', inplace=True, axis=1)

            self.out2('Generando match [id, osm_id]')
            intersections = intersections[['id', 'osm_id']]

            self.out2('Generando indice de match [id, osm_id]')
            intersections.index = range(len(intersections))

            self.out2('Generando way_buffer_40_simplify')
            way_buffer_40_simplify = gpd.GeoSeries(
                bus_routes_buffer.loc[intersections.osm_id].way_buffer_40_simplify.values, crs=crs)

            self.out2('Generando ruta_buffer_40_simplify')
            ruta_buffer_40_simplify = gpd.GeoSeries(
                core_recorrido_buffer.loc[intersections.id].ruta_buffer_40_simplify.values, crs=crs)

            self.out2('Generando symmetric_difference')
            diffs = ruta_buffer_40_simplify.symmetric_difference(way_buffer_40_simplify).area.values

            self.out2('Generando norm_factor')
            norm_factor = ruta_buffer_40_simplify.area.values + way_buffer_40_simplify.area.values

            self.out2('Generando diffs')
            diffs = (diffs/norm_factor).tolist()

            self.out2('Pasando osm_ids a lista')
            osm_ids = intersections.osm_id.values.tolist()

            self.out2('Pasando osm_names a lista')
            osm_names = bus_routes.loc[osm_ids].name.values.tolist()
            # ways = bus_routes.loc[osm_ids].way.map(lambda x: x.wkb).values.tolist()

            self.out2('Pasando recorrido_ids de intersections a lista')
            recorrido_ids = intersections['id'].values.tolist()

            self.out2('Pasando linea_ids a lista')
            linea_ids = core_recorrido.loc[recorrido_ids].linea_id.values.tolist()
            # rutas = core_recorrido.loc[recorrido_ids].ruta.map(lambda x: x.wkb).values.tolist()

            self.out2('Pasando recorrido_nombres a lista')
            recorrido_nombres = core_recorrido.loc[recorrido_ids].nombre.values.tolist()
            # ruta_buffer_40_simplifys = ruta_buffer_40_simplify.map(lambda x: x.wkb).values.tolist()
            # way_buffer_40_simplifys = way_buffer_40_simplify.map(lambda x: x.wkb).values.tolist()

            self.out2('Pasando linea_nombres a lista')
            linea_nombres = core_recorrido.loc[recorrido_ids].linea_nombre.values.tolist()

            self.out2('DROP TABLE crossed_areas')
            cu.execute("DROP TABLE IF EXISTS crossed_areas;")
            cu.execute('DROP INDEX IF EXISTS crossed_areas_recorrido_id;')
            cu.execute('DROP INDEX IF EXISTS crossed_areas_area;')

            self.out2('CREATE TABLE crossed_areas')
            cu.execute(
                """
                    CREATE TABLE crossed_areas (
                        area FLOAT,
                        linea_id INTEGER,
                        recorrido_id INTEGER,
                        osm_id BIGINT,
                        linea_nombre VARCHAR(100),
                        recorrido_nombre VARCHAR(100),
                        osm_name TEXT
                    );
                """
            )

            self.out2('Preparando lista de values')
            data = list(zip(diffs, linea_ids, recorrido_ids, osm_ids, linea_nombres, recorrido_nombres, osm_names))

            self.out2('Ejecutando insert query')
            insert_query = """
                INSERT INTO crossed_areas (
                    area,
                    linea_id,
                    recorrido_id,
                    osm_id,
                    linea_nombre,
                    recorrido_nombre,
                    osm_name
                )
                VALUES %s
            """
            execute_values(cu, insert_query, data)

            self.out2('Commit insert query')
            connection.commit()

            self.out2('Generando indice crossed_areas_recorrido_id')
            cu.execute('CREATE INDEX crossed_areas_recorrido_id ON crossed_areas (recorrido_id);')
            cu.execute('CREATE INDEX crossed_areas_area ON crossed_areas (area);')

            self.out2('LISTO!')

        if options['update_routes']:

            self.out1('UPDATE ROUTES FROM OSM')
            self.out1('Get routes from osm file')
            inputfile = '/tmp/part-all.o5m'

            # self.out2('filter out buses from o5m full')
            # this might be useful for future performance
            # but actually pyosmium uses the same libosmium as osmfilter
            # prog = [
            #     'osmfilter',
            #     inputfile,
            #     '--keep=',
            #     '--keep-relations="route=bus"',
            #     '-o=/tmp/buses.osm'
            # ]
            # subprocess.Popen(prog).wait()

            self.out2('process .osm input file')

            # we can see if all tags are ok and give hints to mappers according to spec:
            # https://wiki.openstreetmap.org/w/index.php?oldid=625726
            # https://wiki.openstreetmap.org/wiki/Buses

            buses = {}  # pasar a self.buses { relation_id: { name: name, fixed_way: GEOSGeom, ways: { way_id: { name: name, nodes: { node_id: { lat: lat, lng: lng } } } } } }
            ways = {}  # aux structure { way_id: [ relation_id ] }

            route_id_only = int(options['osm-id']) if options['osm-id'] else ''

            class RelsHandler(osmium.SimpleHandler):
                def relation(self, r):
                    if ((not route_id_only or r.id == route_id_only) and 'route' in r.tags and r.tags['route'] == 'bus' and 'name' in r.tags):
                        bus = {
                            'name': r.tags['name'].encode('utf-8').strip(),
                            'ways': []
                        }
                        for m in r.members:
                            # forward / backward / alternate are deprecated in PTv2, add warning
                            if m.type == 'w' and m.role in ['', 'forward', 'backward', 'alternate']:
                                bus['ways'].append(m.ref)
                                ways.setdefault(m.ref, []).append(r.id)
                        buses[r.id] = bus

            class WaysHandler(osmium.SimpleHandler):
                def way(self, w):
                    if w.id in ways:
                        linestring = []
                        for node in w.nodes:
                            linestring.append([float(node.x)/10000000, float(node.y)/10000000])

                        for rel_id in ways[w.id]:
                            for i, wid in enumerate(buses[rel_id]['ways']):
                                if wid == w.id:
                                    buses[rel_id]['ways'][i] = linestring

            self.out2('relations')
            h = RelsHandler()
            h.apply_file(inputfile)
            self.out2('ways')
            h = WaysHandler()
            h.apply_file(inputfile, locations=True)

            self.out2('fixer routine')

            counters = {}
            for bus_id, bus in buses.items():
                self.out2(bus_id, end=': ')
                way, status = fix_way(bus['ways'], 150)
                buses[bus_id]['way'] = LineString(way) if way else None
                buses[bus_id]['status'] = status
                counters.setdefault(status, 0)
                counters[status] += 1
                self.out2('{} > {}'.format(status, bus['name']), start='')

            for key, counter in sorted(counters.items(), key=lambda e: e[1], reverse=True):
                self.out2('{} | {}'.format(counter, key))

            self.out1('Update linked routes from osm to cualbondi')
            colnames = ','.join([
                'cr.{}'.format(f.column)
                for f in
                Recorrido._meta.get_fields()
                if hasattr(f, 'column') and f.column != 'ruta' and f.column != 'osm_id'
            ])
            cu.execute('SET STATEMENT_TIMEOUT=1000000')
            recorridos = Recorrido.objects.raw("""
                SELECT
                    {},
                    cr.ruta::bytea as ruta,
                    max(@pl.osm_id) as osm_id,
                    max((pl.tags->'osm_timestamp')::timestamptz) as osm_last_updated,
                    max((pl.tags->'osm_version')::int) as osm_osm_version, --used this name so it doesnt collide with core_recorrido.osm_version
                    array_to_string(array_distinct(array_agg(pop.name ORDER BY ((pop.tags->'admin_level')::int))), ', ') as osm_administrative,
                    pl.name as osm_name,
                    cl.nombre as linea_nombre
                FROM
                    core_recorrido cr
                    right outer join core_linea cl on (cr.linea_id = cl.id)
                    right outer join public.planet_osm_line pl on (cr.osm_id = @pl.osm_id)
                    right outer join planet_osm_polygon pop on (ST_Intersects(pl.way, pop.way))
                where
                    pl.route='bus'
                    and pop.tags @> 'boundary=>administrative'
                    and pop.tags->'admin_level' <= '5'
                group by
                    cr.id,
                    cl.id,
                    pl.osm_id,
                    pl.name;
            """.format(colnames))

            # HINT: run migrations in order to have osmbot in the db
            user_bot_osm = get_user_model().objects.get(username='osmbot')

            self.out2('fixer routine')

            for rec in recorridos:
                # try to fix way, returns None if it can't
                if rec.osm_id in buses:
                    way = buses[rec.osm_id]['way']
                    status = buses[rec.osm_id]['status']
                else:
                    way = None
                    status = None

                ilog = ImporterLog(
                    osm_id=rec.osm_id,
                    osm_version=rec.osm_osm_version,
                    osm_timestamp=rec.osm_last_updated,
                    run_timestamp=run_timestamp,
                    proposed=False,
                    accepted=False,
                    status=status,
                    proposed_reason='',
                    accepted_reason='',
                    osm_administrative=rec.osm_administrative,
                    osm_name=rec.osm_name
                )
                ilog.save()

                if rec.id is None:
                    self.out2('{} | {} : SKIP not linked {}'.format(rec.id, rec.osm_id, status))
                    continue

                # recorrido proposed creation checks
                if way is None:
                    self.out2('{} | {} : SKIP {}'.format(rec.id, rec.osm_id, status))
                    ilog.proposed_reason = 'broken'
                    ilog.save()
                    continue

                if rec.ruta_last_updated >= rec.osm_last_updated:
                    self.out2('{} | {} : SKIP, older than current recorrido {}, ({} >= {})'.format(rec.id, rec.osm_id, status, rec.ruta_last_updated, rec.osm_last_updated))
                    ilog.proposed_reason = 'older than current recorrido'
                    ilog.save()
                    continue

                # check if there is another proposal already submitted (with same timestamp or greater)
                if RecorridoProposed.objects.filter(osm_id=rec.osm_id, parent=rec.uuid, ruta_last_updated__gte=rec.osm_last_updated).exists():
                    self.out2('{} | {} : SKIP, older than prev proposal {}'.format(rec.id, rec.osm_id, status))
                    ilog.proposed_reason = 'older than previous proposal'
                    ilog.save()
                    continue

                # update previous proposal if any
                previous_proposals = RecorridoProposed.objects.filter(
                    osm_id=rec.osm_id,
                    parent=rec.uuid,
                    ruta_last_updated__lt=rec.osm_last_updated,
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
                rp.ruta_last_updated = rec.osm_last_updated
                rp.osm_version = rec.osm_osm_version  # to not be confsed with Recorrido.osm_version
                if not options['dry-run']:
                    rp.save(user=user_bot_osm)

                ilog.proposed = True
                ilog.save()

                # AUTO ACCEPT CHECKS
                if rec.osm_version is None:
                    self.out2('{} | {} : {} | NOT auto accepted: previous accepted proposal does not come from osm'.format(rec.id, rec.osm_id, proposal_info))
                    ilog.accepted_reason = 'previous accepted proposal does not come from osm'
                    ilog.save()
                    continue

                if RecorridoProposed.objects.filter(parent=rec.uuid).count() > 1:
                    self.out2('{} | {} : {} | NOT auto accepted: another not accepted recorridoproposed exists for this recorrido'.format(rec.id, rec.osm_id, proposal_info))
                    ilog.accepted_reason = 'another not accepted proposal exists for this recorrido'
                    ilog.save()
                    continue

                self.out2('{} | {} : {} | AUTO ACCEPTED!'.format(rec.id, rec.osm_id, proposal_info))
                if not options['dry-run']:
                    rp.aprobar()

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

            self.out1('Calles')
            self.out2('Borrando las que no tienen osm_id')
            Calle.objects.filter(osm_id__isnull=True).delete()
            self.out2('Insert desde planet_osm_line las nuevas')
            cu.execute("""
                INSERT INTO
                    catastro_calle(osm_id, way, nom_normal, nom)
                (
                    SELECT
                        osm_id,
                        way,
                        trim(regexp_replace(upper(translate(name, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')), E'AV\.|AVENIDA|CALLE|DIAGONAL|BOULEVARD', '')) as nom_normal,
                        name as nom
                    FROM
                        planet_osm_line as pol
                    WHERE
                        name is not null and
                        highway is not null and
                        route is null and
                        osm_id > 0 and
                        not EXISTS (
                            SELECT osm_id FROM catastro_calle as cc2 WHERE cc2.osm_id = pol.osm_id
                        )
                    LIMIT 10
                )
                ;
            """)

            self.out2('Eliminando nombres comunes (av., avenida, calle, diagonal, boulevard)')
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'AV. ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'AVENIDA ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'CALLE ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'DIAGONAL ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'BOULEVARD ', '');")

            self.out1('POIs')
            self.out2('Borrando POIs sin osm_id')
            cu.execute("""DELETE FROM catastro_poi WHERE osm_id IS NULL""")
            self.out2('Generando POIs a partir de poligonos normalizando nombres')
            cu.execute("""
                INSERT INTO
                    catastro_poi(osm_id, latlng, nom_normal, nom, tags)
                (
                    SELECT
                        osm_id,
                        ST_Centroid(way),
                        upper(translate(pop.name, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ"', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU ')),
                        pop.name || coalesce(', ' || zo.name, ''),
                        tags
                    FROM
                        planet_osm_polygon as pop
                        left outer join catastro_zona zo on (ST_Intersects(pop.way, zo.geo))
                    WHERE
                        pop.name is not null and
                        highway is null and
                        route is null and
                        char_length(pop.name) > 2 and
                        osm_id > 0 and
                        not (landuse = 'residential' and char_length(pop.name)<7) and
                        not EXISTS (
                            SELECT osm_id FROM catastro_poi as cp2 WHERE cp2.osm_id = pop.osm_id
                        )
                )
                ;
            """)

            self.out2('Generando POIs a partir de puntos normalizando nombres')
            cu.execute("""
                INSERT INTO
                    catastro_poi(osm_id, latlng, nom_normal, nom, tags)
                (
                    SELECT
                        osm_id,
                        way,
                        upper(translate(pop.name, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ"', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU ')),
                        pop.name || coalesce(', ' || zo.name, ''),
                        tags
                    FROM
                        planet_osm_point as pop
                        left outer join catastro_zona zo on (ST_Intersects(pop.way, zo.geo))
                    WHERE
                        pop.name is not null
                        and osm_id > 0
                        and char_length(pop.name) > 2
                        and amenity is not null
                        and not EXISTS(
                            SELECT osm_id FROM catastro_poi as cp2 WHERE cp2.osm_id=pop.osm_id
                        )
                )
                ;
            """)

            self.out2('Generando slugs')
            total = Poi.objects.filter(slug__isnull=True).count()
            i = 0
            start = time.time()
            for o in Poi.objects.filter(slug__isnull=True):
                o.save()
                i = i + 1
                if i % 50 == 0 and time.time()-start > 1:
                    start = time.time()
                    self.out2('{}/{} ({:2.0f}%)'.format(i, total, i * 100.0 / total))

            # unir catastro_poicb (13 y 60, 13 y 66, 13 y 44) con catastro_poi (osm_pois)
            # self.out2('Mergeando POIs propios de cualbondi')
            # for poicb in Poicb.objects.all():
            #     Poi.objects.create(nom_normal = poicb.nom_normal.upper(), nom = poicb.nom, latlng = poicb.latlng)
            # self.out2('Purgando nombres repetidos')
            # cu.execute('delete from catastro_poi where id not in (select min(id) from catastro_poi group by nom_normal)')

            self.out1('Regenerando indices')
            self.out2('Eliminando viejos')
            cu.execute('DROP INDEX IF EXISTS catastrocalle_nomnormal_gin;')
            cu.execute('DROP INDEX IF EXISTS catastropoi_nomnormal_gin;')
            self.out2('Generando catastro_calle')
            cu.execute('CREATE INDEX catastrocalle_nomnormal_gin ON catastro_calle USING gin (nom_normal gin_trgm_ops);')
            self.out2('Generando catastro_poi')
            cu.execute('CREATE INDEX catastropoi_nomnormal_gin ON catastro_poi USING gin (nom_normal gin_trgm_ops);')

        ##########################
        #  Intersections de osm  #
        ##########################

        if options['intersections']:

            self.out1('Generando Intersecciones')
            cu.execute('delete from catastro_interseccion')
            cu.execute('''
                SELECT
                    SEL1.nom || ' y ' || SEL2.nom || coalesce(', ' || z.name, '') as nom,
                    upper(translate(SEL1.nom || ' y ' || SEL2.nom || coalesce(', ' || z.name, ''), 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')) as nom_normal,
                    ST_Intersection(SEL1.way, SEL2.way) as latlng
                FROM
                    catastro_calle AS SEL1
                    join catastro_calle as SEL2 on (ST_Intersects(SEL1.way, SEL2.way) and ST_GeometryType(ST_Intersection(SEL1.way, SEL2.way):: Geometry)='ST_Point' )
                    left outer join catastro_zona as z on(ST_Intersects(z.geo, ST_Intersection(SEL1.way, SEL2.way)))
            ''')
            self.out2('Generando slugs')
            intersections = cu.fetchall()
            total = len(intersections)
            i = 0
            for inter in intersections:
                i = i + 1
                Interseccion.objects.create(nom=inter[0], nom_normal=inter[1], latlng=inter[2])
                if (i * 100.0 / total) % 1 == 0:
                    self.out2('{:2.0f}%'.format(i * 100.0 / total))

        #self.out1('Eliminando tablas no usadas')
        #cu.execute('drop table planet_osm_roads;')
        #cu.execute('drop table planet_osm_polygon;')
        # cx.commit()
        # cx.close()

        self.out1('LISTO!')
