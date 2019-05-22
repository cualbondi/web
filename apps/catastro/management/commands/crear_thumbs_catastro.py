from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from django.core.files import File
from apps.catastro.models import AdministrativeArea

import os
import shutil
from subprocess import call

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import chromedriver_binary  # noqa


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
        self.chrome_options.add_argument('--user-data-dir=/tmp/chromecache')
        self.chrome_options.add_argument('--disk-cache-size=2147483648')
        self.driver = None

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            dest='skip',
            help='Saltear objetos que ya tienen thumbs creadas',
            action='store_true',
            default=False,
        )

    def create_screenshot(self, url, filename, size):
        self.driver.set_window_size(size[0], size[1])
        u = f'{url}&size={size[0]}{size[1]}'
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
        fname = "{}{}".format(path.format(prefix), name.format(prefix, slugify(obj.name)))
        print("a punto de grabar ", fname)
        try:
            with open(fname, 'rb') as f:
                getattr(obj, img_field).save(name.format(prefix, slugify(obj.name)), File(f))
                try:
                    obj.save()
                except Exception:
                    print("ERROR al intentar guardar imagen de objeto ", str(obj))
                    raise
                    # print(str(e))
            # os.remove(fname)
        except IOError as e:
            print("ERROR abrir imagen de objeto", str(obj), ". No habia sido creada.")
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
                    prefix, slugify(obj.name), size[0], size[1])
                print("  >- Size: ", size)
                print("   - Rendering HTML...")
                self.create_screenshot(url, fname, size)
                # optimizamos la imagen si tenemos pngcrush
                print("   - pngcrushing it")
                try:
                    # proc = Process(target=pngcrush, args=(fname,))
                    # proc.start()
                    # pngcrush(fname)
                    pass
                except OSError:
                    print("pngcrush no instalado o no se encuentra en el PATH")
            self.save_img('/media/{0}/', '{0}-{1}.500x500.png', prefix, obj, 'img_cuadrada')
            self.save_img('/media/{0}/', '{0}-{1}.880x300.png', prefix, obj, 'img_panorama')
        else:
            print("WARNING: Salteando objeto porque utilizaste el parametro -s y el objeto ya tiene ambas thumbs precalculadas")

    def handle(self, *args, **options):

        self.driver = webdriver.Chrome(
            chrome_options=self.chrome_options,
            service_args=[
                '--verbose',
                '--ignore-certificate-errors',
                '--log-path=/tmp/chromedriver.log',
            ]
        )

        for aa in AdministrativeArea.objects.all():
            self.ghost_make_map_img(aa, 'administrativearea', skip=options['skip'])

        self.driver.close()
