from django.conf.urls import include, url
from django.contrib.gis import admin
import settings

from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import GenericSitemap#, FlatPageSitemap
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi

from django.views.static import serve
from apps.core.urls import urlpatterns as urlpatternscore
from apps.editor.urls import urlpatterns as editorUrls
from apps.usuarios.urls import urlpatterns as usuariosUrls
from apps.editor.views import revision
from apps.catastro.urls import urlpatterns as catastroUrls
from apps.core.views import agradecimientos

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

sitemaps = {
    #'flatpages': FlatPageSitemap,
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

urlpatterns = [

    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

    # APPS de CualBondi
    url(r'^admin/', admin.site.urls),
    url(r'^editor/', include(editorUrls)),
    url(r'^usuarios/', include(usuariosUrls)),
    url(r'^revision/(?P<id_revision>\d+)/$', revision, name='revision_externa'),

    url(r'^como-llegar/', include(catastroUrls)),

    # Ranking aka agradecimientos
    url(r'^agradecimientos/$', agradecimientos, name='agradecimientos'),

    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    url(r'^', include(urlpatternscore)),
]
