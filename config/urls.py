from django.conf.urls import include, url
from django.contrib.gis import admin
from django.conf import settings

from django.contrib.sitemaps.views import sitemap
from django.contrib.sitemaps import GenericSitemap  # , FlatPageSitemap
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi, Ciudad

from django.views.static import serve
from apps.core.urls import urlpatterns as urlpatternsCore
from apps.editor.urls import urlpatterns as editorUrls
from apps.usuarios.urls import urlpatterns as usuariosUrls
from apps.editor.views import revision
from apps.catastro.urls import urlpatterns as catastroUrls
from apps.api3.urls import urlpatterns as api3Urls
from apps.core.views import agradecimientos
from django.db.models import Prefetch


# Uncomment the next two lines to enable the admin:
admin.autodiscover()

sitemaps = {
    # 'flatpages': FlatPageSitemap,
    'lineas': GenericSitemap({
        'queryset': Linea.objects.all().prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.filter(activa=True).only('slug'))).defer('envolvente'),
    }, priority=0.6),
    'recorridos': GenericSitemap({
        'queryset': Recorrido.objects.select_related('linea').prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.all().only('slug'))).only('slug', 'nombre', 'linea__slug', 'linea__nombre').all(),
    }, priority=0.6),
    'paradas': GenericSitemap({
        'queryset': Parada.objects.all().defer('latlng'),
    }, priority=0.4),
    'pois': GenericSitemap({
        'queryset': Poi.objects.all().exclude(slug=''),
    }, priority=0.6),
}

urlpatterns = [

    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    # APPS de CualBondi
    url(r'^admin/', admin.site.urls),
    url(r'^editor/', include(editorUrls)),
    url(r'^usuarios/', include(usuariosUrls)),
    url(r'^revision/(?P<id_revision>\d+)/$', revision, name='revision_externa'),

    url(r'^como-llegar/', include(catastroUrls)),

    # Ranking aka agradecimientos
    url(r'^agradecimientos/$', agradecimientos, name='agradecimientos'),

    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    url(r'^api/v3/', include(api3Urls)),
    url(r'^v3/', include(api3Urls)),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

urlpatterns += [
    url(r'^', include(urlpatternsCore)),
]
