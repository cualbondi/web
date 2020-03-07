from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi, AdministrativeArea
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


class CBSitemap(Sitemap):

    priority = None
    changefreq = None

    def __init__(self, info_dict, priority=None, changefreq=None, protocol=None):
        self.queryset = info_dict['queryset']
        self.date_field = info_dict.get('date_field')
        self.priority = priority
        self.changefreq = changefreq
        self.protocol = protocol

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
                'location': loc,
                'lastmod': lastmod,
                'changefreq': self.__get('changefreq', item),
                'priority': str(priority if priority is not None else ''),
            }
            if domain in loc:
                urls.append(url_info)
        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod
        return urls


sitemaps = {
    # 'flatpages': FlatPageSitemap,
    'lineas': CBSitemap({
        'queryset': Linea.objects.defer('envolvente'),
    }, priority=0.6),
    'recorridos': CBSitemap({
        'queryset': Recorrido.objects.defer('ruta'),
    }, priority=0.6),
    'paradas': CBSitemap({
        'queryset': Parada.objects.defer('latlng'),
    }, priority=0.4),
    'pois': CBSitemap({
        'queryset': Poi.objects.defer('latlng'),
    }, priority=0.6),
    'administrativeareas': CBSitemap({
        'queryset': AdministrativeArea.objects.defer('geometry', 'geometry_simple'),
    }, priority=0.6),
}

def getsitemaps(cc):
    return {
        # 'flatpages': FlatPageSitemap,
        'lineas': CBSitemap({
            'queryset': Linea.objects.defer('envolvente').filter(country_code=cc),
        }, priority=0.6),
        'recorridos': CBSitemap({
            'queryset': Recorrido.objects.defer('ruta').filter(country_code=cc),
        }, priority=0.6),
        'paradas': CBSitemap({
            'queryset': Parada.objects.defer('latlng').filter(country_code=cc),
        }, priority=0.4),
        'pois': CBSitemap({
            'queryset': Poi.objects.defer('latlng').filter(country_code=cc),
        }, priority=0.6),
        'administrativeareas': CBSitemap({
            'queryset': AdministrativeArea.objects.defer('geometry', 'geometry_simple').filter(country_code=cc),
        }, priority=0.6),
    }
