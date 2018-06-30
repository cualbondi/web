from django.conf.urls import include, url
from django.contrib.gis import admin
import settings

from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import FlatPageSitemap, GenericSitemap
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

sitemaps = {
    'flatpages': FlatPageSitemap,
    'lineas': GenericSitemap({
        'queryset': Linea.objects.all(),
        }, priority=0.6),
    'recorridos': GenericSitemap({
        'queryset': Recorrido.objects.all(),
        }, priority=0.6),
    'pois': GenericSitemap({
        'queryset': Poi.objects.all(),
        }, priority=0.6),
    'paradas': GenericSitemap({
        'queryset': Parada.objects.all(),
        }, priority=0.4),
}

from apps.core.urls import urlpatterns as urlpatternscore
urlpatterns = [

    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),

    # APPS de CualBondi
    url(r'^admin/', include(admin.site.urls)),
    url(r'^editor/', include('apps.editor.urls')),
    url(r'^revision/(?P<id_revision>\d+)/$', 'apps.editor.views.revision', name='revision_externa'),

    url(r'^como-llegar/', include('apps.catastro.urls')),

    # Ranking aka agradecimientos
    url(r'^agradecimientos/$', 'apps.core.views.agradecimientos', name='agradecimientos'),

    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    url(r'^', include(urlpatternscore)),
]
