from django.conf import settings
from django.templatetags.static import static
from django.utils import translation
from django.utils.translation import gettext, ngettext
from django.urls import reverse
from math import ceil

from jinja2 import Environment
from apps.utils.slugify import slugify


def dividir_columnas(lista, cantidad_columnas):
    try:
        cantidad_columnas = int(cantidad_columnas)
        lista = list(lista)
    except (ValueError, TypeError):
        return [lista]
    result = []
    tamano = len(lista) // (cantidad_columnas)
    if tamano * cantidad_columnas < len(lista):
        tamano = tamano + 1
    for i in range(cantidad_columnas):
        result.append(lista[i*tamano:(i+1)*tamano])
    return result


def partition_horizontal(thelist, n):
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    newlists = [list() for i in range(int(ceil(len(thelist) / float(n))))]
    for i, val in enumerate(thelist):
        newlists[i//n].append(val)
    return newlists


def environment(**options):
    options.pop('debug', None)
    options['extensions'] = ['jinja2.ext.i18n']
    # options['enable_async'] = True
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'FACEBOOK_APP_ID': 'pedo',
        'HOME_URL': settings.HOME_URL,
        'STATIC_URL': settings.STATIC_URL,
        'dividir_columnas': dividir_columnas,
        'partition_horizontal': partition_horizontal,
        'uslugify': slugify,
        'get_current_language': translation.get_language,
    })
    env.install_gettext_callables(gettext=gettext, ngettext=ngettext, newstyle=True)
    return env
