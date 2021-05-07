from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi, AdministrativeArea
from apps.catastro.management.commands.update_osm import kings
import datetime
from calendar import timegm
from functools import wraps

from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import http_date
from django.contrib.sitemaps.views import x_robots_tag


def get_alternates(loc, sitemap_lang_code):
    alternates = []
    for (lang_code, lang_name) in settings.LANGUAGES:
        cc = loc.split('/')[3]
        if len(cc) != 2:
            cc = 'ar'
        language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), 'en')
        if lang_code[:2] != sitemap_lang_code:
            # only add as alternate if this url is not the sitemap_lang_code
            # (if this url is the sitemap_lang_code, then it goes directly in <loc></loc> (not alternate))
            if language_default[:2] == lang_code[:2]:
                alternates.append({'location': loc, 'lang': lang_code})
                alternates.append({'location': loc, 'lang': 'x-default'})
            alternates.append({'location': loc + '?lang=' + lang_code, 'lang': lang_code})
        else:
            if language_default[:2] == lang_code[:2]:
                alternates.append({'location': loc, 'lang': lang_code})
                alternates.append({'location': loc, 'lang': 'x-default'})
    return alternates


def get_loc(loc, sitemap_lang_code):
    cc = loc.split('/')[3]
    if len(cc) != 2:
        cc = 'ar'
    language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), 'en')
    if language_default[:2] == sitemap_lang_code[:2]:
        return loc
    return loc + '?lang=' + sitemap_lang_code


class CBSitemap(Sitemap):

    priority = None
    changefreq = None
    limit = 10000

    def __init__(self, info_dict, priority=None, changefreq=None, protocol=None, lang='en'):
        self.queryset = info_dict['queryset']
        self.date_field = info_dict.get('date_field')
        self.priority = priority
        self.changefreq = changefreq
        self.protocol = protocol
        self.lang = lang

    def items(self):
        # Make sure to return a clone; we don't want premature evaluation.
        return self.queryset.filter()

    def lastmod(self, item):
        if self.date_field is not None:
            return getattr(item, self.date_field)
        return None

    def __get(self, name, obj, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            return attr(obj)
        return attr

    def _urls(self, page, protocol, domain):
        urls = []
        latest_lastmod = None
        all_items_lastmod = True  # track if all items have a lastmod
        for item in self.paginator.page(page).object_list:
            loc = self.__get('location', item)
            priority = self.__get('priority', item)
            lastmod = self.__get('lastmod', item)
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if (all_items_lastmod and
                        (latest_lastmod is None or lastmod > latest_lastmod)):
                    latest_lastmod = lastmod
            url_info = {
                'item': item,
                'location': get_loc(loc, self.lang),
                'lastmod': lastmod,
                'changefreq': self.__get('changefreq', item),
                'priority': str(priority if priority is not None else ''),
                'alternates': get_alternates(loc, self.lang),
            }
            if domain in loc:
                urls.append(url_info)
        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod
        return urls


sitemaps = {}

for (lang_code, lang_name) in settings.LANGUAGES:
    sitemaps['lineas_' + lang_code] = CBSitemap({
        'queryset': Linea.objects.defer('envolvente'),
    }, priority=0.6, lang=lang_code)
    sitemaps['recorridos_' + lang_code] = CBSitemap({
        'queryset': Recorrido.objects.defer('ruta'),
    }, priority=0.6, lang=lang_code)
    sitemaps['paradas_' + lang_code] = CBSitemap({
        'queryset': Parada.objects.defer('latlng'),
    }, priority=0.4, lang=lang_code)
    sitemaps['pois_' + lang_code] = CBSitemap({
        'queryset': Poi.objects.defer('latlng'),
    }, priority=0.6, lang=lang_code)
    sitemaps['administrativeareas_' + lang_code] = CBSitemap({
        'queryset': AdministrativeArea.objects.defer('geometry', 'geometry_simple'),
    }, priority=0.6, lang=lang_code)


def getsitemaps(cc):
    sitemaps = {}
    cclang = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), '')[:2]
    print('CCLANG:' + cclang)
    for (lang_code, lang_name) in settings.LANGUAGES:
        suffix = ''
        if cclang != lang_code[:2]:
            suffix = '_' + lang_code
        sitemaps['lineas' + suffix] = CBSitemap({
            'queryset': Linea.objects.defer('envolvente').filter(country_code=cc),
        }, priority=0.6, lang=lang_code)
        sitemaps['recorridos' + suffix] = CBSitemap({
            'queryset': Recorrido.objects.defer('ruta').filter(country_code=cc),
        }, priority=0.6, lang=lang_code)
        sitemaps['paradas' + suffix] = CBSitemap({
            'queryset': Parada.objects.defer('latlng').filter(country_code=cc),
        }, priority=0.4, lang=lang_code)
        sitemaps['pois' + suffix] = CBSitemap({
            'queryset': Poi.objects.defer('latlng').filter(country_code=cc),
        }, priority=0.6, lang=lang_code)
        sitemaps['administrativeareas' + suffix] = CBSitemap({
            'queryset': AdministrativeArea.objects.defer('geometry', 'geometry_simple').filter(country_code=cc),
        }, priority=0.6, lang=lang_code)
    return sitemaps
