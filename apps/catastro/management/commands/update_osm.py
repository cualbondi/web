import traceback
import subprocess
import os
import sys
import time
import pytz
from cProfile import Profile

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.db.models import F, Func, Value
from django.db.models import BooleanField
from django.db.models.functions import Upper, Trim, Substr
from django.db.models.expressions import RawSQL
from django.contrib.gis.geos import LineString, Polygon, MultiPolygon, Point
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.db.models.functions import MakeValid
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.db.backends.postgis.adapter import PostGISAdapter

from apps.catastro.models import Poi, Interseccion, AdministrativeArea
from apps.core.models import Recorrido, ImporterLog, Parada, Horario
from apps.editor.models import RecorridoProposed
from apps.utils.fix_way import fix_way, fix_polygon

import osmium
import pyosmptparser
import geopandas as gpd
from datetime import datetime
from urllib import request
from psycopg2.extras import execute_values
from .utils_admin_areas import get_admin_area, get_admin_areas, make_poly_file


class Nonegetter():
    def __getitem__(self, key):
        return None


kings = {
    'argentina': {
        'name': 'argentina',
        'url': 'http://download.geofabrik.de/south-america/argentina-latest.osm.pbf',
        'id': 286393,
        'paradas_completas': False,
        'country_code': 'ar',
        'lang': 'es_AR',
    },
    'spain': {
        'name': 'spain',
        'url': 'http://download.geofabrik.de/europe/spain-latest.osm.pbf',
        'id': 1311341,
        'paradas_completas': True,
        'country_code': 'es',
        'lang': 'es_ES',
    },
    # 'uruguay': {
    #     'name': 'uruguay',
    #     'url': 'http://download.geofabrik.de/south-america/uruguay-latest.osm.pbf',
    #     'id': 287072,
    #     'paradas_completas': False,
    #     'country_code': 'uy',
    #     'lang': 'es_UY',
    # },
    # 'ecuador': {
    #     'name': 'ecuador',
    #     'url': 'http://download.geofabrik.de/south-america/ecuador-latest.osm.pbf',
    #     'id': 108089,
    #     'paradas_completas': False,
    #     'country_code': 'ec',
    #     'lang': 'es_EC',
    # },
    # 'peru': {
    #     'name': 'peru',
    #     'url': 'http://download.geofabrik.de/south-america/peru-latest.osm.pbf',
    #     'id': 288247,
    #     'paradas_completas': False,
    #     'country_code': 'pe',
    #     'lang': 'es_PE',
    # },
    'brazil': {
        'name': 'brasil',
        'url': 'https://download.geofabrik.de/south-america/brazil-latest.osm.pbf',
        'id': 59470,
        'paradas_completas': False,
        'country_code': 'br',
        'lang': 'pt_BR',
    },
    'ivorycoast': {
        'name': 'cotedivoire',
        'url': 'https://download.geofabrik.de/africa/ivory-coast-latest.osm.pbf',
        'id': 192779,
        'paradas_completas': False,
        'country_code': 'ci',
        'lang': 'fr_CI',
    },
    'china': {
        'name': 'china',
        'url': 'http://download.geofabrik.de/asia/china-latest.osm.pbf',
        'id': 270056,
        'paradas_completas': False,
        'country_code': 'cn',
        'lang': 'zh_CN',
    },
    'russia': {
        'name': 'russia',
        'url': 'http://download.geofabrik.de/russia-latest.osm.pbf',
        'id': 60189,
        'paradas_completas': False,
        'country_code': 'ru',
        'lang': 'ru_RU',
    },
    'srilanka': {
        'name': 'srilanka',
        'url': 'https://download.geofabrik.de/asia/sri-lanka-latest.osm.pbf',
        'id': 536807,
        'paradas_completas': False,
        'country_code': 'lk',
        'lang': 'en_LK',
    },
    'taiwan': {
        'name': 'taiwan',
        'url': 'https://download.geofabrik.de/asia/taiwan-latest.osm.pbf',
        'id': 449220,
        'paradas_completas': True,
        'country_code': 'tw',
        'lang': 'zh_TW',
    },
    # 'morocco': {
    #     'name': 'morocco',
    #     'url': 'https://download.geofabrik.de/africa/morocco-latest.osm.pbf',
    #     'id': 3630439,
    #     'paradas_completas': False,
    #     'country_code': 'ma',
    #     'lang': 'ar_MA',  # TODO: falta ar como lang
    # },
    'burkinafaso': {
        'name': 'burkinafaso',
        'url': 'https://download.geofabrik.de/africa/burkina-faso-latest.osm.pbf',
        'id': 192783,
        'paradas_completas': False,
        'country_code': 'bf',
        'lang': 'fr_BF',
    },
    'iran': {
        'name': 'iran',
        'url': 'http://download.geofabrik.de/asia/iran-latest.osm.pbf',
        'id': 304938,
        'paradas_completas': False,
        'country_code': 'ir',
        'lang': 'fa_IR',
    },
    'southkorea': {
        'name': 'southkorea',
        'url': 'https://download.geofabrik.de/asia/south-korea-latest.osm.pbf',
        'id': 307756,
        'paradas_completas': True,
        'country_code': 'kr',
        'lang': 'ko_KR',
    },
    'newzealand': {
        'name': 'newzealand',
        'url': 'https://download.geofabrik.de/australia-oceania/new-zealand-latest.osm.pbf',
        'id': 556706,
        'paradas_completas': False,
        'country_code': 'nz',
        'lang': 'en_NZ',
    },
    'australia': {
        'name': 'australia',
        'url': 'https://download.geofabrik.de/australia-oceania/australia-latest.osm.pbf',
        'id': 80500,
        'paradas_completas': False,
        'country_code': 'au',
        'lang': 'en_AU',
    },
    'portugal': {
        'name': 'portugal',
        'url': 'https://download.geofabrik.de/europe/portugal-latest.osm.pbf',
        'id': 295480,
        'paradas_completas': False,
        'country_code': 'pt',
        'lang': 'pt_PT',
    },
    # 'england': { great britain, united kingdom? iso country code is GB but there is no england country code
    #     'name': 'england',
    #     'url': 'https://download.geofabrik.de/europe/great-britain/england-latest.osm.pbf',
    #     'id': 58447,
    #     'paradas_completas': False,
    #     'country_code': 'pt',
    #     'lang': 'pt_PT',
    # },
    'switzerland': {
        'name': 'switzerland',
        'url': 'https://download.geofabrik.de/europe/switzerland-latest.osm.pbf',
        'id': 51701,
        'paradas_completas': True,
        'country_code': 'ch',
        'lang': 'de_CH',
    },
    'nicaragua': {
        'name': 'nicaragua',
        'url': 'https://download.geofabrik.de/central-america/nicaragua-latest.osm.pbf',
        'id': 287666,
        'paradas_completas': False,
        'country_code': 'ni',
        'lang': 'es_NI',
    },
    'cuba': {
        'name': 'cuba',
        'url': 'http://download.geofabrik.de/central-america/cuba-latest.osm.pbf',
        'id': 307833,
        'paradas_completas': False,
        'country_code': 'cu',
        'lang': 'es_CU',
    },
    'japan': {
        'name': 'japan',
        'url': 'https://download.geofabrik.de/asia/japan-latest.osm.pbf',
        'id': 382313,
        'paradas_completas': True,
        'country_code': 'jp',
        'lang': 'ja_JP',
    },
    'usa': {
        'name': 'usa',
        'url': 'https://download.geofabrik.de/north-america/us-latest.osm.pbf',
        'id': 148838,
        'paradas_completas': False,
        'country_code': 'us',
        'lang': 'en_US',
    },
    'unitedkingdom': {
        'name': 'unitedkingdom',
        'url': 'https://download.geofabrik.de/europe/britain-and-ireland-latest.osm.pbf',
        'id': 62149,
        'clip_country': True,
        'paradas_completas': False,
        'country_code': 'gb',
        'lang': 'en_GB',
    },
    'ireland': {
        'name': 'ireland',
        'url': 'https://download.geofabrik.de/europe/ireland-and-northern-ireland-latest.osm.pbf',
        'id': 62273,
        'clip_country': True,
        'paradas_completas': False,
        'country_code': 'ie',
        'lang': 'en_IE',
    },
    'malaysia': {
        'name': 'malaysia',
        'url': 'https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf',
        'id': 2108121,
        'clip_country': True,
        'paradas_completas': False,
        'country_code': 'my',
        'lang': 'ms_MY',
    },
    'singapore': {
        'name': 'singapore',
        'url': 'https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf',
        'id': 536780,
        'clip_country': True,
        'paradas_completas': False,
        'country_code': 'sg',
        'lang': 'en_SG',
    },
    'germany': {
        'name': 'germany',
        'url': 'https://download.geofabrik.de/europe/germany-latest.osm.pbf',
        'id': 51477,
        'paradas_completas': True,
        'country_code': 'de',
        'lang': 'de_DE',
    },
    'france': {
        'name': 'france',
        'url': 'https://download.geofabrik.de/europe/france-latest.osm.pbf',
        'id': 2202162,
        'paradas_completas': True,
        'country_code': 'fr',
        'lang': 'fr_FR',
    },
    'italy': {
        'name': 'italy',
        'url': 'https://download.geofabrik.de/europe/italy-latest.osm.pbf',
        'id': 365331,
        'paradas_completas': False,
        'country_code': 'it',
        'lang': 'it_IT',
    },
    'austria': {
        'name': 'austria',
        'url': 'https://download.geofabrik.de/europe/austria-latest.osm.pbf',
        'id': 16239,
        'paradas_completas': False,
        'country_code': 'at',
        'lang': 'de_AT',
    },
    'turkey': {
        'name': 'turkey',
        'url': 'https://download.geofabrik.de/europe/turkey-latest.osm.pbf',
        'id': 174737,
        'paradas_completas': False,
        'country_code': 'tr',
        'lang': 'tr_TR',
    },
    'ethiopia': {
        'name': 'ethiopia',
        'url': 'https://download.geofabrik.de/africa/ethiopia-latest.osm.pbf',
        'id': 192800,
        'paradas_completas': False,
        'country_code': 'et',
        'lang': 'am_ET',
    },
    'philippines': {
        'name': 'philippines',
        'url': 'https://download.geofabrik.de/asia/philippines-latest.osm.pbf',
        'id': 443174,
        'paradas_completas': False,
        'country_code': 'ph',
        'lang': 'en_PH',
    },
}


class Command(BaseCommand):
    help = 'update local database with osm POIs and Streets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--profile',
            action='store_true',
            dest='profile',
            default=False,
            help='Run cProfile'
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
            '--download',
            action='store_true',
            dest='download',
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
        if options['profile']:
            profiler = Profile()
            profiler.runcall(self._handle, *args, **options)
            profiler.print_stats()
        else:
            self._handle(*args, **options)

    def _handle(self, *args, **options):

        king = kings[options['king']]

        run_timestamp = datetime.now()

        inputfile = f'/tmp/osm-{king["name"]}.pbf'

        if options['download']:

            self.out1(f'Descargando mapa de {king["name"]} de geofabrik')
            # url = 'http://download.geofabrik.de/south-america-latest.osm.pbf'
            url = king['url']
            self.out2(url)
            f, d = request.urlretrieve(url, inputfile, lambda nb, bs, fs, url=url: self.reporthook(nb, bs, fs, url))

        if 'clip_country' in king and king['clip_country'] == True:
            self.out1('Clip big pbf file to the country adminarea')
            self.out2('get full country admin area polygon')
            KING_ADMIN_AREA = get_admin_area(inputfile, king['id'], self.out2)
            self.out2('make poly file for osmconvert')
            filename = make_poly_file(KING_ADMIN_AREA['geometry'].buffer(0.001))
            self.out2(f'generated temp poly file at {filename}')
            self.out2('run osmconvert to clip pbf file')
            # result = subprocess.run(['osmconvert', inputfile, f'-B={filename}', '--complete-ways', '--complete-multipolygons', f'-o={inputfile}-cropped.pbf'], stdout=subprocess.PIPE)
            result = subprocess.run(['osmium', 'extract', f'-p{filename}', inputfile, f'-o{inputfile}-cropped.pbf'], stdout=subprocess.PIPE)
            inputfile = f'{inputfile}-cropped.pbf'
            self.out2(f'pbf clipped at {inputfile}')

        #######################
        #  Adminareas de osm  #
        #######################
        # 1. ./manage.py update_osm --download --admin_areas
        # 2. ./manage.py update_osm -f /tmp/part-all.o5m --admin_areas

        if options['admin_areas']:
            self.out1('Admin Areas')

            KING_ID = king['id']  # osm_id king

            OLD_KING = list(AdministrativeArea.objects.filter(osm_id=KING_ID))

            admin_areas, KING = get_admin_areas(run_timestamp, inputfile, king['country_code'], KING_ID, self.out2)
            KING_GEOM_BUFF = KING['geometry_simple'].buffer(0.01)

            def fuzzy_contains(out_geom, in_geom, buffer=0, attempts=3):
                try:
                    return (
                        out_geom.intersects(in_geom) and  # optimization
                        out_geom.buffer(buffer).contains(in_geom)
                    )
                except GEOSException as e:
                    if attempts > 0:
                        self.out2(f'''
                        out_geom.valid: {out_geom.valid}
                        out_geom.valid_reason: {out_geom.valid_reason}
                        in_geom.valid: {in_geom.valid}
                        in_geom.valid_reason: {in_geom.valid_reason}
                        ''')
                        return fuzzy_contains(maybe_make_valid(out_geom), maybe_make_valid(in_geom), buffer, attempts - 1)
                    else:
                        raise

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
                    print('node.data', node['data']['name'])
                    print('node.osm_id', node['data']['osm_id'])
                    print('node.osm_type', node['data']['osm_type'])
                    # traceback.print_exc()
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
                    'country_code': king['country_code'],
                }
            }
            for li in admin_areas:
                # aa = admin area
                for aa in li:
                    try:
                        if not aa['geometry'].intersects(KING_GEOM_BUFF):
                            continue
                    except GEOSException as e:
                        self.out2(f'{str(e)}\n{aa["osm_id"]} {aa["name"]}')
                    try:
                        parent_aa = get_parent_aa(tree, aa['geometry'])
                        aa.pop('admin_level')
                        if 'ways' in aa:
                            aa.pop('ways')
                        else:
                            self.out2(f" {aa['osm_id']}: {aa['name']}, does not have 'ways' attribute")
                        if parent_aa is None:
                            tree['children'].append({'children': [], 'data': aa})
                        else:
                            parent_aa['children'].append({'children': [], 'data': aa})
                    except GEOSException as e:
                        self.out2(f'{str(e)}\n{tree["data"]["osm_id"]} {tree["data"]["name"]}\n{aa["osm_id"]} {aa["name"]}')

            def print_tree(node, level=0):
                print(f'{" " * level} {level} {node["data"]["name"].decode("utf-8")}')
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

        if options['cross']:

            crs = {'init': 'epsg:4326'}

            self.out1('Cross osm recorridos')
            self.out2('Obteniendo bus routes de osm planet_osm_line')
            bus_routes = gpd.read_postgis(
                """
                    # esto cambiarlo para no usar mas planet_osm_line (osm2pgsql), usar osmosis para construir las bus_routes
                    # SELECT
                    #     @osm_id AS osm_id, -- @=modulus operator
                    #     name,
                    #     ref,
                    #     st_linemerge(st_union(way)) AS way
                    # FROM
                    #     planet_osm_line
                    # WHERE
                    #     route = 'bus'
                    # GROUP BY
                    #     osm_id,
                    #     name,
                    #     ref
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
            diffs = (diffs / norm_factor).tolist()

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
            cu = connection.cursor()
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
            # TODO: consider also trains / trams / things that have fixed stops

            self.out1('UPDATE ROUTES FROM OSM')
            self.out2('process .osm input file')

            # we can see if all tags are ok and give hints to mappers according to spec:
            # https://wiki.openstreetmap.org/w/index.php?oldid=625726
            # https://wiki.openstreetmap.org/wiki/Buses

            p = pyosmptparser.Parser(inputfile)
            pts = p.get_public_transports(500)
            routetypes_stops = ['train', 'subway', 'monorail', 'tram', 'light_rail']
            routetypes = routetypes_stops + ['bus', 'trolleybus']
            buses = {}
            counters = {}
            for pt in pts:
                self.out2(pt.id, end=': ')
                buses[pt.id] = {
                    'pt': pt,
                    'way': LineString(pt.geometry[0]) if pt.status.code < 500 and len(pt.geometry) == 1 else None,
                    'paradas_completas': (pt.tags['route'] in routetypes_stops or len(pt.stops) > 20) and king['paradas_completas'],
                }
                counters.setdefault(pt.status.code, 0)
                counters[pt.status.code] += 1
                self.out2('{}: {} > {}'.format(pt.status.code, pt.status.detail, pt.tags['name'], start=''))

            self.out2('status | count')
            for key, counter in sorted(counters.items(), key=lambda e: e[1], reverse=True):
                self.out2('{} | {}'.format(key, counter))

            # HINT: run migrations in order to have osmbot in the db
            user_bot_osm = get_user_model().objects.get(username='osmbot')

            self.out2('fixer routine')

            # add all as new routes
            if options['add_routes']:

                for bus_osm_id, bus in buses.items():
                    # try to fix way, returns None if it can't
                    way = bus['way']

                    # recorrido proposed creation checks
                    if bus['way'] is None:
                        self.out2('{} : SKIP {}'.format(bus['pt'].id, bus['pt'].status.code))
                        continue

                    # set proposal fields
                    # rp.paradas_completas = len(bus['stops']) > options['paradas_completas_threshold'] o usar una config en el pais KINGs
                    rp = RecorridoProposed(nombre=bus['pt'].tags['name'][:199])
                    rp.osm_id = bus['pt'].id
                    rp.ruta = bus['way']
                    rp.ruta_last_updated = datetime.utcfromtimestamp(int(bus['pt'].info['timestamp'])).replace(tzinfo=pytz.utc)
                    rp.osm_version = int(bus['pt'].info['version'])
                    rp.import_timestamp = run_timestamp
                    rp.paradas_completas = bus['paradas_completas']
                    rp.type = bus['pt'].tags['route']
                    rp.king = king['id']
                    rp.country_code = king['country_code']
                    if not options['dry-run']:
                        rp.save(user=user_bot_osm)

                    self.out2('{} | AUTO ACCEPTED!'.format(bus['pt'].id))
                    if not options['dry-run']:
                        rp.aprobar(user_bot_osm)

                    # add stops!
                    if not options['dry-run'] and len(bus['pt'].stops) > 0:
                        self.out2(f'ADDing STOPS {len(bus["pt"].stops)}', end=' > ')
                        count_created = 0
                        count_associated = 0
                        for s in bus['pt'].stops:
                            parada, created = Parada.objects.update_or_create(
                                osm_id=s.id,
                                defaults={
                                    'import_timestamp': run_timestamp,
                                    'nombre': s.tags['name'] if 'name' in s.tags else f'{s.lon}, {s.lat}',
                                    'latlng': Point(s.lon, s.lat),
                                    'tags': s.tags,
                                    'country_code': king['country_code'],
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
                        status = buses[osm_id]['pt'].status.code
                        osm_osm_version = buses[osm_id]['pt'].info['version']
                        osm_last_updated = buses[osm_id]['pt'].info['timestamp']
                        name = buses[osm_id]['pt'].tags['name']
                        paradas_completas = buses[osm_id]['paradas_completas']
                        routetype = buses[osm_id]['pt'].tags['route']
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
            cu = connection.cursor()
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
                    # TODO: add 'shop' in n.tags also, more info in https://github.com/gravitystorm/openstreetmap-carto/blob/96c64fa5b0449e79c17e39626f3b8f38c96a12bb/project.mml#L1504
                    if 'amenity' in n.tags and 'name' in n.tags and len(n.tags['name']) > 2:
                        try:
                            point = Point([float(n.location.x) / 10000000, float(n.location.y) / 10000000], srid=4326)
                            # this is a little slow, but it uses indexes :)
                            # TODO: improve this by using in-memory pandas queries like we did with the 'cross'
                            q = Recorrido.objects \
                                .order_by() \
                                .annotate(cond=RawSQL("ST_Intersects(ST_Buffer(%s::geography, 400, 2)::geometry, ruta)", (point.ewkb,), output_field=BooleanField())) \
                                .filter(cond=True) \
                                .only('id') \
                                .exists()
                            if q:
                                defaults = {
                                    'tags': {k:v for k,v in n.tags},
                                    'nom': n.tags['name'][:200],
                                    'nom_normal': Substr(Trim(Upper(Unaccent(Value(n.tags['name'])))), 1, 200),
                                    'latlng': point,
                                    'country_code': king['country_code'],
                                }
                                Poi.objects.update_or_create(
                                    osm_id=n.id,
                                    osm_type='n',
                                    defaults=defaults
                                )
                                self.nodes_added += 1
                                print(f'[{self.nodes_current*100/nodes_count:7.3f}%] / Nodes added: {self.nodes_added} | processed: {self.nodes_current} / {nodes_count}')
                        except Exception as e:
                            print(f'Could not save, exception {e}')

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
                        'country_code': king['country_code'],
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

        ##########################
        #  Intersections de osm  #
        ##########################

        if options['intersections']:

            self.out1('Generando Intersecciones')
            cu = connection.cursor()
            cu.execute('delete from catastro_interseccion')
            cu.execute('''
                SELECT
                    SEL1.nom || ' y ' || SEL2.nom as nom,
                    upper(translate(SEL1.nom || ' y ' || SEL2.nom, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')) as nom_normal,
                    ST_Intersection(SEL1.way, SEL2.way) as latlng
                FROM
                    catastro_calle AS SEL1
                    join catastro_calle as SEL2 on (ST_Intersects(SEL1.way, SEL2.way) and ST_GeometryType(ST_Intersection(SEL1.way, SEL2.way):: Geometry)='ST_Point' )
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

        # self.out1('Eliminando tablas no usadas')
        # cu.execute('drop table planet_osm_roads;')
        # cu.execute('drop table planet_osm_polygon;')
        # cx.commit()
        # cx.close()

        self.out1('LISTO!')
