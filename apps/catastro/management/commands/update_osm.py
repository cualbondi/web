from django.core.management.base import BaseCommand
from urllib import request
import subprocess
import os
import sys
from apps.catastro.models import Poi, Poicb, Interseccion
from django.db import connection
from psycopg2 import connect
from datetime import datetime

import pandas as pd
import geopandas as gpd
import psycopg2
import shapely


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
            '--pois'
            action='store_true',
            dest='pois',
            default=False,
            help='Build poi data from osm'
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

    def handle(self, *args, **options):

        cu = connection.cursor()

        # print(' => Generando Intersecciones')
        # cu.execute('delete from catastro_interseccion')
        # cu.execute('''
        #     SELECT
        #         SEL1.nom || ' y ' || SEL2.nom || coalesce(', ' || z.name, '') as nom,
        #         upper(translate(SEL1.nom || ' y ' || SEL2.nom || coalesce(', ' || z.name, ''), 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')) as nom_normal,
        #         ST_Intersection(SEL1.way, SEL2.way) as latlng
        #     FROM
        #         catastro_calle AS SEL1
        #         join catastro_calle as SEL2 on (ST_Intersects(SEL1.way, SEL2.way) and ST_GeometryType(ST_Intersection(SEL1.way, SEL2.way):: Geometry)='ST_Point' )
        #         left outer join catastro_zona as z on(ST_Intersects(z.geo, ST_Intersection(SEL1.way, SEL2.way)))
        # ''')
        # print('    - Generando slugs')
        # intersections = cu.fetchall()
        # total = len(intersections)
        # i = 0
        # for inter in intersections:
        #     i = i + 1
        #     Interseccion.objects.create(nom=inter[0], nom_normal=inter[1], latlng=inter[2])
        #     if (i * 100.0 / total) % 1 == 0:
        #         print('    - {:2.0f}%'.format(i * 100.0 / total))

        # return 0

        inputfile = '/tmp/argentina.cache.osm-{}.pbf'.format(datetime.now().strftime('%Y%m%d%H%M%S'))
        if options['no-tmp']:
            inputfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'argentina.cache.osm.pbf')
        if options['inputFile'] or options['use_cache']:
            if options['inputFile']:
                inputfile = options['inputFile']
        else:
            print(' => Descargando mapa de Argentina de geofabrik')
            url = 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf'
            print('    - {}'.format(url))
            f, d = request.urlretrieve(url, inputfile, lambda nb, bs, fs, url=url: self.reporthook(nb,bs,fs,url))
            #print('Descomprimiendo')
            #subprocess.Popen(['bunzip2', '-vvf', inputfile+'.bz2']).wait()
            #os.chmod(inputfile, S_IROTH | S_IRUSR | S_IROTH | S_IWOTH | S_IWUSR | S_IWOTH)

        dbname = connection.settings_dict['NAME']
        dbuser = connection.settings_dict['USER']
        dbpass = connection.settings_dict['PASSWORD']
        dbhost = connection.settings_dict['HOST']

        cu = connection.cursor()
        cu.execute('SELECT slug, box(poligono::geometry) as box FROM catastro_ciudad;')

        # TODO: osmconvert /tmp/argentina.cache.osm-20160711192104.pbf -b=-57.8526306071815,-38.1354198737499,-57.5065612712919,-37.8562051788731 -o=1.pbf

        print(' => Cargando data de osm en la base de cualbondi')

        ciudades = cu.fetchall()
        for c in ciudades:

            # if options.ciudad is defined, and this is not it, skip it
            if options['ciudad'] and options['ciudad'] != c[0]:
                continue

            l = c[1][1:-1].replace(')', '').replace('(', '').split(',')
            box = ','.join([l[2], l[3], l[0], l[1]])
            print('    - Extrayendo {} ({})'.format(c[0], box))
            prog = [
                'osmconvert',
                inputfile,
                '-b={}'.format(box),
                '-o=/tmp/part-{}.osm'.format(c[0])
            ]

            subprocess.Popen(prog).wait()


        print('    - Uniendo partes')
        partfiles = ['/tmp/part-{}.osm'.format(c[0]) for c in ciudades]
        prog = [
            'osmconvert',
            '-o=/tmp/part-all.pbf'
        ] + partfiles
        subprocess.Popen(prog).wait()


        print('    - Cargando en la base de datos')
        prog = [
            'osm2pgsql',
            '--latlong',
            '--style={}'.format(os.path.join(os.path.abspath(os.path.dirname(__file__)),'update-osm.style')),
            '--database={}'.format(dbname),
            '--username={}'.format(dbuser),
            '--host={}'.format(dbhost),
            '--create',
            '--number-processes=4',
            '/tmp/part-all.pbf'
        ]
        if options['slim']:
            prog.append('-s')
        print('    - ejecutando:',)
        print(' '.join(prog))
        if not options['no-o2p']:
            p = subprocess.Popen(prog, env={'PGPASSWORD': dbpass})
            p.wait()

        # POST PROCESAMIENTO
        print('POSTPROCESO')
        print(' => Dando nombres alternativos a los objetos sin nombre')
        print('    - planet_osm_line')
        cu.execute('update planet_osm_line    set name=ref where name is null;')
        print('    - planet_osm_point')
        cu.execute('update planet_osm_point   set name=ref where name is null;')
        print('    - planet_osm_polygon')
        cu.execute('update planet_osm_polygon set name=ref where name is null;')

        #######################
        #  recorridos de osm  #
        #######################

        bus_routes = gpd.read_postgis(
            """
                select
                    osm_id,
                    name,
                    st_linemerge(st_union(way)) as way
                from
                    planet_osm_line
                where
                    route = 'bus'
                group by
                    osm_id,
                    name
            """,
            cu,
            geom_col='way',
            crs={'init': 'epsg:4326'}
        )
        bus_routes.set_index('osm_id', inplace=True)

        bus_routes_buffer = gpd.GeoDataFrame({
            'osm_id': bus_routes.osm_id,
            'way': bus_routes.way
            'name': bus_routes.name,
            'way_buffer_40_simplify': bus_routes.way.simplify(0.0001).buffer(0.0004),
        }).set_geometry('way_buffer_40_simplify')

        core_recorrido = gpd.read_postgis(
            """
                select
                    id,
                    ruta,
                    li.nombre || ' ' || re.nombre as nombre,
                from
                    core_recorrido re
                    join core_linea li on (re.linea_id = li.id)
            """,
            cu,
            geom_col='ruta',
            crs={'init': 'epsg:4326'}
        )
        core_recorrido.set_index('id', inplace=True)

        core_recorrido_buffer = gpd.GeoDataFrame({
            'id': core_recorrido.id
            'ruta': core_recorrido.ruta.simplify(0.0001),
            'nombre': core_recorrido.nombre,
            'ruta_buffer_40_simplify': core_recorrido.ruta.simplify(0.0001).buffer(0.0004),
        }).set_geometry('ruta')

        join = gpd.sjoin(core_recorrido_buffer, bus_routes_buffer, how='inner', op='intersects')

        join["way_buffer_40_simplify"] = join.apply(lambda row: bus_routes_buffer.loc[row.index_right].way_buffer_40_simplify, axis=1)
        diffs = gpd.GeoSeries(join.ruta_buffer_40_simplify).symmetric_difference(gpd.GeoSeries(join.way_buffer_40_simplify))

        join['area'] = diffs.area



        if options['pois']:

            print(' => Juntando tablas de caminos, normalizando nombres')
            cu.execute('delete from catastro_calle')
            print('    - planet_osm_line')
            cu.execute("""
                INSERT
                    INTO catastro_calle(osmid, way, nom_normal, nom)
                SELECT
                    osm_id,
                    way,
                    trim(regexp_replace(upper(translate(name, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')), E'AV\.|AVENIDA|CALLE|DIAGONAL|BOULEVARD', '')) as nom_normal,
                    name as nom
                FROM
                    planet_osm_line
                WHERE
                    name is not null and
                    highway is not null and
                    route is null and
                    osm_id > 0
                ;
            """)
            print('    - Generando slugs')
            calles = cu.fetchall()
            total = len(intersections)
            i = 0
            for inter in intersections:
                i = i + 1
                Interseccion.objects.create(nom=inter[0], nom_normal=inter[1], latlng=inter[2])
                if (i * 100.0 / total) % 1 == 0:
                    print('    - {:2.0f}%'.format(i * 100.0 / total))

            print('    - Eliminando nombres comunes (av., avenida, calle, diagonal, boulevard)')
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'AV. ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'AVENIDA ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'CALLE ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'DIAGONAL ', '');")
            cu.execute("update catastro_calle set nom_normal = replace(nom_normal, 'BOULEVARD ', '');")



            print(' => Generando POIs a partir de poligonos normalizando nombres, agregando slugs (puede tardar bastante)')
            cu.execute('delete from catastro_poi')
            cu.execute("select ST_Centroid(way), upper(translate(name, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')), name||coalesce(', '||(select name from catastro_zona zo where ST_Intersects(ST_Centroid(way), zo.geo)), '') from planet_osm_polygon as pop where name is not null;")
            polygons = cu.fetchall()
            total = len(polygons)
            i = 0
            for poly in polygons:
                i = i + 1
                Poi.objects.create(nom_normal = poly[1], nom = poly[2], latlng = poly[0])
                if i * 100.0 / total % 1 == 0:
                    print('    - {:2.0f}%'.format(i * 100.0 / total))
            # unir catastro_poicb (13 y 60, 13 y 66, 13 y 44) con catastro_poi (osm_pois)
            print('    - Mergeando POIs propios de cualbondi')
            for poicb in Poicb.objects.all():
                Poi.objects.create(nom_normal = poicb.nom_normal.upper(), nom = poicb.nom, latlng = poicb.latlng)
            print('    - Purgando nombres repetidos')
            cu.execute('delete from catastro_poi where id not in (select min(id) from catastro_poi group by nom_normal)')

            print(' => Regenerando indices')
            print('    - Eliminando viejos')
            cu.execute('DROP INDEX IF EXISTS catastrocalle_nomnormal_gin;')
            cu.execute('DROP INDEX IF EXISTS catastropoi_nomnormal_gin;')
            print('    - Generando catastro_calle')
            cu.execute('CREATE INDEX catastrocalle_nomnormal_gin ON catastro_calle USING gin (nom_normal gin_trgm_ops);')
            print('    - Generando catastro_poi')
            cu.execute('CREATE INDEX catastropoi_nomnormal_gin ON catastro_poi USING gin (nom_normal gin_trgm_ops);')



        #print(' => Eliminando tablas no usadas')
        #cu.execute('drop table planet_osm_roads;')
        #cu.execute('drop table planet_osm_polygon;')
        #cx.commit()
        #cx.close()

        print(' LISTO! ')
