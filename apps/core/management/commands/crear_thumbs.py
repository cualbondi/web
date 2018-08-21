from django.core.management.base import BaseCommand
from apps.catastro.models import Ciudad, Poi
from apps.core.models import Recorrido, Linea
from django.conf import settings

from multiprocessing import Process
import os
from django.core.files import File
from subprocess import call
import shutil
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from time import sleep


def pngcrush(fname):
    call('pngcrush -q -rem gAMA -rem cHRM -rem iCCP -rem sRGB -rem alla -rem text -reduce -brute {0} {1}.min'.format(fname, fname).split())
    os.remove(fname)
    shutil.move('{0}.min'.format(fname), fname)


class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.driver = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--ciudad_slug',
            action  = 'store',
            dest    = 'ciudad_slug',
            default = '',
            help    = 'Rehacer thumb de una ciudad (buscar por slug)'
        )
        parser.add_argument(
            '--ciudad_id',
            action  = 'store',
            dest    = 'ciudad_id',
            default = '',
            help    = 'Rehacer thumb de una ciudad (buscar por id)'
        )
        parser.add_argument(
            '--linea_slug',
            action  = 'store',
            dest    = 'linea_slug',
            default = '',
            help    = 'Rehacer thumb de una linea (buscar por slug)'
        )
        parser.add_argument(
            '--linea_id',
            action  = 'store',
            dest    = 'linea_id',
            default = '',
            help    = 'Rehacer thumb de una linea (buscar por id)'
        )
        parser.add_argument(
            '--recorrido_slug',
            action  = 'store',
            dest    = 'recorrido_slug',
            default = '',
            help    = 'Rehacer thumb de un recorrido (buscar por slug)'
        )
        parser.add_argument(
            '--recorrido_id',
            action  = 'store',
            dest    = 'recorrido_id',
            default = '',
            help    = 'Rehacer thumb de un recorrido (buscar por id)'
        )
        parser.add_argument(
            '-C',
            action  = 'store_true',
            dest    = 'ciudades',
            default = False,
            help    = 'Rehacer thumbs de todas las ciudades'
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
            '-A',
            action  = 'store_true',
            dest    = 'todas',
            default = False,
            help    = 'Rehacer todas las thumbs (igual a -rC)'
        )
        parser.add_argument(
            '-r',
            action  = 'store_true',
            dest    = 'recursivo',
            default = False,
            help    = 'Recursivo, dada una ciudad, rehacer las thumb de todas sus lineas y recorridos. Para una linea, rehacer la thumb de la linea mas las thumb de cada uno de los recorridos que contiene esa linea'
        )
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
        fname = "{}{}".format(path.format(prefix), name.format(prefix, obj.slug))
        print("a punto de grabar ", fname)
        try:
            with open(fname, 'rb') as f:
                getattr(obj, img_field).save(name.format(prefix, obj.slug), File(f))
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

    def ghost_make_map_img(self, obj, prefix, ciudad=None, skip=False):
        print(obj,)
        if (not skip) or (not (obj.img_cuadrada and obj.img_panorama)):
            try:
                if ciudad is None:
                    print(settings.HOME_URL)
                    url = '{0}{1}?dynamic_map=True'.format(
                        settings.HOME_URL, obj.get_absolute_url())
                else:
                    url = '{0}{1}?dynamic_map=True'.format(
                        settings.HOME_URL, obj.get_absolute_url(ciudad.slug))
            except Exception as e:
                print(e)
                return 0
            print(">>> " + url)
            for size in [(500, 500), (880, 300)]:
                fname = '/media/{0}/{0}-{1}.{2}x{3}.png'.format(
                    prefix, obj.slug, size[0], size[1])
                print("  >- Size: ", size)
                print("   - Rendering HTML...")
                self.create_screenshot(url, fname, size)
                # optimizamos la imagen si tenemos pngcrush
                print("   - pngcrushing it")
                try:
                    # proc = Process(target=pngcrush, args=(fname,))
                    # proc.start()
                    #pngcrush(fname)
                    pass
                except OSError as e:
                    print("pngcrush no instalado o no se encuentra en el PATH")
            self.save_img('/media/{0}/', '{0}-{1}.500x500.png', prefix, obj, 'img_cuadrada')
            self.save_img('/media/{0}/', '{0}-{1}.880x300.png', prefix, obj, 'img_panorama')
        else:
            print("WARNING: Salteando objeto porque utilizaste el parametro -s y el objeto ya tiene ambas thumbs precalculadas")

    def ciudad_recursiva(self, c, skip=False):
        for l in c.lineas.all():
            self.ghost_make_map_img(l, 'linea', c, skip)
            for r in l.recorridos.all():
                self.ghost_make_map_img(r, 'recorrido', c, skip)

    def foto_de_linea(self, l, recursiva=False, skip=False):
        try:
            c = l.ciudad_set.all()[0]
        except l.ciudad_set.DoesNotExist:
            print("ERROR: Salteando linea {0}. No se pudo encontrar la url porque la linea no tiene ninguna ciudad asociada [linea_id={1}]".format(
                l.slug, l.id))
        else:
            self.ghost_make_map_img(l, 'linea', c, skip)
            if recursiva:
                for r in l.recorrido_set.all():
                    self.ghost_make_map_img(r, 'recorrido', c, skip)

    def handle(self, *args, **options):

        self.driver = webdriver.Chrome(
            chrome_options=self.chrome_options,
            service_args=[
                '--verbose',
                '--log-path=/tmp/chromedriver.log'
            ]
        )

        #ciudad
        if (options['ciudades'] and options['recursivo'] ) or options['todas']:
            for ciudad in Ciudad.objects.all():
                self.ghost_make_map_img(ciudad, 'ciudad', skip=options['skip'])
                self.ciudad_recursiva(ciudad, skip=options['skip'])
            return 0

        if options['ciudades']:
            for ciudad in Ciudad.objects.all():
                self.ghost_make_map_img(ciudad, 'ciudad', skip=options['skip'])
        elif options['ciudad_slug'] or options['ciudad_id']:
            if options['ciudad_slug']:
                c = Ciudad.objects.get(slug=options['ciudad_slug'])
            else:
                c = Ciudad.objects.get(slug=options['ciudad_id'])
            self.ghost_make_map_img(c, 'ciudad', skip=options['skip'])
            if options['recursivo']:
                self.ciudad_recursiva(c, skip=options['skip'])

        #linea
        if options['lineas'] and options['recursivo']:
            for l in Linea.objects.all():
                self.foto_de_linea(l, True, skip=options['skip'])
            return 0

        if options['lineas']:
            for l in Linea.objects.all():
                self.foto_de_linea(l, skip=options['skip'])

        elif options['linea_slug'] or options['linea_id']:
            if options['linea_slug']:
                l = Linea.objects.get(slug=options['linea_slug'])
            else:
                l = Linea.objects.get(id=options['linea_id'])
            self.foto_de_linea(l, skip=options['skip'])
            if options['recursivo']:
                self.foto_de_linea(l, recursiva=options['recursivo'], skip=options['skip'])

        #recorrido
        rs=[]
        if options['recorridos']:
            rs = Recorrido.objects.all()
        elif options['recorrido_slug']:
            rs = [Recorrido.objects.get(slug=options['recorrido_slug'])]
        elif options['recorrido_id']:
            rs = [Recorrido.objects.get(id=options['recorrido_id'])]

        for r in rs:
            try:
                c = r.linea.ciudad_set.all()[0]
            except DoesNotExist:
                print("ERROR: Salteando recorrido {0}. No se pudo encontrar la url porque el recorrido no tiene ninguna ciudad asociada [recorrido_id={1}]".format(r.slug, r.id))
            else:
                self.ghost_make_map_img(r, 'recorrido', ciudad=c, skip=options['skip'])

        # pois
        if options['pois']:
            pois = Poi.objects.all()
            for p in pois:
                self.ghost_make_map_img(p, 'poi', skip=options['skip'])

        self.driver.close()
