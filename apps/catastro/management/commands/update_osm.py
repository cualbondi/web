from django.core.management.base import BaseCommand
from urllib import request
import subprocess
import os
import sys
from apps.catastro.models import Poi, Poicb, Interseccion, Calle
from django.db import connection
from datetime import datetime
import time

import geopandas as gpd
from psycopg2.extras import execute_values


class Command(BaseCommand):
    help = 'update local database with osm POIs and Streets'

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            action  = 'store',
            dest    = 'inputFile',
            default = '',
            help    = 'Use an input file instead of trying to download osm data'
        )
        parser.add_argument(
            '--use-cache',
            action  = 'store_true',
            dest    = 'use_cache',
            default = False,
            help    = 'Use the cache of downloaded osm'
        )
        parser.add_argument(
            '-s',
            action  = 'store_true',
            dest    = 'slim',
            default = False,
            help    = 'Set osm2pgsql slim mode (create raw tables: nodes, rels, ways)'
        )
        parser.add_argument(
            '--no-o2p',
            action  = 'store_true',
            dest    = 'no-o2p',
            default = False,
            help    = 'Ignore osm2pgsql execution (debug purposes only)'
        )
        parser.add_argument(
            '--no-tmp',
            action  = 'store_true',
            dest    = 'no-tmp',
            default = False,
            help    = 'Don\'t use /tmp folder, instead use apps/catastro/management/commands folder to save the downloaded argentina.osm.pbf file'
        )
        parser.add_argument(
            '--ciudad',
            action  = 'store',
            dest    = 'ciudad',
            help    = 'Only import this ciudad slug'
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

    def out2(self, s):
        print('[{}]    - {}'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), s))

    def handle(self, *args, **options):

        cu = connection.cursor()

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
                f, d = request.urlretrieve(url, inputfile, lambda nb, bs, fs, url=url: self.reporthook(nb,bs,fs,url))

            dbname = connection.settings_dict['NAME']
            dbuser = connection.settings_dict['USER']
            dbpass = connection.settings_dict['PASSWORD']
            dbhost = connection.settings_dict['HOST']

            cu = connection.cursor()
            cu.execute('SELECT slug, box(poligono::geometry) as box FROM catastro_ciudad;')

            # TODO: osmconvert /tmp/argentina.cache.osm-20160711192104.pbf -b=-57.8526306071815,-38.1354198737499,-57.5065612712919,-37.8562051788731 -o=1.pbf

            self.out1('Cargando data de osm en la base de cualbondi')

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

                subprocess.Popen(prog).wait()

            self.out2('Uniendo partes')
            partfiles = ['/tmp/part-{}.osm'.format(c[0]) for c in ciudades]
            prog = [
                'osmconvert',
                '-o=/tmp/part-all.pbf'
            ] + partfiles
            subprocess.Popen(prog).wait()

            self.out2('Cargando en la base de datos')
            prog = [
                'osm2pgsql',
                '--latlong',
                '--style={}'.format(os.path.join(os.path.abspath(os.path.dirname(__file__)),'update-osm.style')),
                '--database={}'.format(dbname),
                '--username={}'.format(dbuser),
                '--host={}'.format(dbhost),
                '--create',
                '--number-processes=4',
                '--hstore-all',
                '--extra-attributes',
                '/tmp/part-all.pbf'
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
                        JOIN catastro_ciudad_recorridos ccr ON (ccr.recorrido_id = cr.id)
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
            way_buffer_40_simplify = gpd.GeoSeries(bus_routes_buffer.loc[intersections.osm_id].way_buffer_40_simplify.values, crs=crs)

            self.out2('Generando ruta_buffer_40_simplify')
            ruta_buffer_40_simplify = gpd.GeoSeries(core_recorrido_buffer.loc[intersections.id].ruta_buffer_40_simplify.values, crs=crs)

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

            self.out2('LISTO!')


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
        #cx.commit()
        #cx.close()

        self.out1('LISTO!')
