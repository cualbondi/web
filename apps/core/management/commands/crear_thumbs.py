from django.core.management.base import BaseCommand
from apps.catastro.models import Ciudad, Poi, AdministrativeArea
from apps.core.models import Recorrido, Linea
from django.conf import settings
from urllib import request
import json
import os
from django.core.files import File
from concurrent.futures import ThreadPoolExecutor

def run_io_tasks_in_parallel(tasks):
    with ThreadPoolExecutor() as executor:
        running_tasks = [executor.submit(*task) for task in tasks]
        for running_task in running_tasks:
            running_task.result()

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--administrativearea_id',
            action  = 'store',
            dest    = 'administrativearea_id',
            default = '',
            help    = 'Rehacer thumb de una administrativearea (buscar por id)'
        )
        parser.add_argument(
            '--administrativearea_osm_id',
            action  = 'store',
            dest    = 'administrativearea_osm_id',
            default = '',
            help    = 'Rehacer thumb de una administrativearea (buscar por osm_id)'
        )
        parser.add_argument(
            '--linea_osm_id',
            action  = 'store',
            dest    = 'linea_osm_id',
            default = '',
            help    = 'Rehacer thumb de una linea (buscar por osm_id)'
        )
        parser.add_argument(
            '--linea_id',
            action  = 'store',
            dest    = 'linea_id',
            default = '',
            help    = 'Rehacer thumb de una linea (buscar por id)'
        )
        parser.add_argument(
            '--recorrido_osm_id',
            action  = 'store',
            dest    = 'recorrido_osm_id',
            default = '',
            help    = 'Rehacer thumb de un recorrido (buscar por osm_id)'
        )
        parser.add_argument(
            '--recorrido_id',
            action  = 'store',
            dest    = 'recorrido_id',
            default = '',
            help    = 'Rehacer thumb de un recorrido (buscar por id)'
        )
        parser.add_argument(
            '--poi_slug',
            action  = 'store',
            dest    = 'poi_slug',
            default = '',
            help    = 'Rehacer thumb de un poi (buscar por osm_id)'
        )
        parser.add_argument(
            '--poi_id',
            action  = 'store',
            dest    = 'poi_id',
            default = '',
            help    = 'Rehacer thumb de un poi (buscar por id)'
        )
        parser.add_argument(
            '-A',
            action  = 'store_true',
            dest    = 'administrativeareas',
            default = False,
            help    = 'Rehacer thumbs de todas las administrative areas'
        )
        parser.add_argument(
            '-L',
            action  = 'store_true',
            dest    = 'lineas',
            default = False,
            help    = 'Rehacer thumbs de todas las lineas'
        )
        parser.add_argument(
            '-R',
            action  = 'store_true',
            dest    = 'recorridos',
            default = False,
            help    = 'Rehacer thumbs de todos los recorridos'
        )
        parser.add_argument(
            '-P',
            action  = 'store_true',
            dest    = 'pois',
            default = False,
            help    = 'Rehacer thumbs de todos los puntos de interes POI'
        )
        parser.add_argument(
            '-F',
            action  = 'store_true',
            dest    = 'full',
            default = False,
            help    = 'Rehacer todas las thumbs (igual a -ALRP)'
        )
        # parser.add_argument(
        #     '-r',
        #     action  = 'store_true',
        #     dest    = 'recursivo',
        #     default = False,
        #     help    = 'Recursivo, dada una administrativearea, rehacer las thumb de todas sus lineas y recorridos. Para una linea, rehacer la thumb de la linea mas las thumb de cada uno de los recorridos que contiene esa linea'
        # )
        parser.add_argument(
            '-s',
            action  = 'store_true',
            dest    = 'skip',
            default = False,
            help    = 'Saltear objetos que ya tienen thumbs creadas'
        )


    def create_screenshot(self, url, filename, size):
        self.driver.set_window_size(size[0], size[1])
        u = url+'&size='+str(size[0]+size[1])
        self.driver.get(u)
        print(u)
        try:
            print('WAITING to load')
            WebDriverWait(self.driver, 20).until(EC.title_is('loaded'))
            print("loaded, saving img")
            png = self.driver.get_screenshot_as_png()
            try:
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'wb') as f:
                    f.write(png)
            except IOError as e:
                print(e)
            finally:
                del png
            print("SAVED TO ", filename)
        except TimeoutException:
            print("no alert")
        except Exception as e:
            print("OTRO ERROR: ", str(e))


    def save_img(self, path, name, prefix, obj, img_field):
        fname = "{}{}".format(path.format(prefix), name.format(prefix, getattr(obj, 'osm_id', obj.osm_id)))
        print("  > a punto de grabar ", fname)
        try:
            with open(fname, 'rb') as f:
                getattr(obj, img_field).save(name.format(prefix, getattr(obj, 'osm_id', obj.osm_id)), File(f))
                try:
                    obj.save()
                except Exception as e:
                    print("ERROR al intentar guardar imagen de objeto ", str(obj))
                    raise
                    #print(str(e))
            #os.remove(fname)
        except IOError as e:
            print("ERROR abrir imagen de objeto",
                str(obj), ". No habia sido creada.")
            print(str(e))

    def make_map_img(self, obj, skip=False):
        prefix = obj._meta.label_lower.split('.')[-1]
        print(obj.get_absolute_url())
        tasks = []
        if (not skip) or (not (obj.img_cuadrada and obj.img_panorama)):
            for size in [(500, 500), (880, 300)]:
                def fn(prefix, obj, size):
                    fname = f'{settings.MEDIA_ROOT}/{prefix}/{prefix}-{getattr(obj, "osm_id", obj.osm_id)}.{size[0]}x{size[1]}.png'
                    print(f'  > Getting image size: {size} ')
                    params = {
                        'geojson': obj.geoJSON,
                        'attribution': 'cualbondi.com.ar & openstreetmap contributors',
                        'vectorserverUrl': 'https://tiles.cualbondi.com.ar/styles/osm-bright/style.json',
                        'imagemin': 'true',
                        'width': size[0],
                        'height': size[1],
                        'maxZoom': 16,
                    }
                    if prefix == 'recorrido':
                        params['arrows'] = 'true'
                    req = request.Request(
                        'http://osm-static-maps:3000/',
                        data=json.dumps(params).encode('utf8'),
                        headers={'content-type': 'application/json'},
                        method='POST'
                    )
                    try:
                        image = request.urlopen(req)
                        with open(fname, "wb") as f:
                            f.write(image.read())
                    except Exception as e:
                        print(e)
                        print(e.read())
                        print(params['geojson'])
                tasks.append((fn, prefix, obj, size,))
            run_io_tasks_in_parallel(tasks)
            self.save_img(settings.MEDIA_ROOT + '/{0}/', '{0}-{1}.500x500.png', prefix, obj, 'img_cuadrada')
            self.save_img(settings.MEDIA_ROOT + '/{0}/', '{0}-{1}.880x300.png', prefix, obj, 'img_panorama')
        else:
            print("  > WARNING: Salteando objeto porque utilizaste el parametro -s y el objeto ya tiene ambas thumbs precalculadas")

    def handle(self, *args, **options):

        # lineas
        lineas = []
        if options['lineas'] or options['full']:
            lineas = Linea.objects.all()
        elif options['linea_osm_id']:
            lineas = [Linea.objects.get(osm_id=options['linea_osm_id'])]
        elif options['linea_id']:
            lineas = [Linea.objects.get(id=options['linea_id'])]
        for linea in lineas:
            self.make_map_img(linea, skip=options['skip'])

        # recorridos
        recorridos = []
        if options['recorridos'] or options['full']:
            recorridos = Recorrido.objects.all()
        elif options['recorrido_osm_id']:
            recorridos = [Recorrido.objects.get(osm_id=options['recorrido_osm_id'])]
        elif options['recorrido_id']:
            recorridos = [Recorrido.objects.get(id=options['recorrido_id'])]
        for recorrido in recorridos:
            self.make_map_img(recorrido, skip=options['skip'])

        # pois
        pois = []
        if options['pois'] or options['full']:
            pois = Poi.objects.all()
        elif options['poi_slug']:
            pois = [Poi.objects.get(slug=options['poi_slug'])]
        elif options['poi_id']:
            pois = [Poi.objects.get(id=options['poi_id'])]
        for poi in pois:
            self.make_map_img(poi, skip=options['skip'])

        # administrativearea
        administrativeareas = []
        if options['administrativeareas'] or options['full']:
            administrativeareas = AdministrativeArea.objects.all()
        elif options['administrativearea_osm_id']:
            administrativeareas = [AdministrativeArea.objects.get(osm_id=options['administrativearea_osm_id'])]
        elif options['administrativearea_id']:
            administrativeareas = [AdministrativeArea.objects.get(id=options['administrativearea_id'])]
        for administrativearea in administrativeareas:
            self.make_map_img(administrativearea, skip=options['skip'])
