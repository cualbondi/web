from django.urls import re_path
from apps.core.views import ver_parada, ver_mapa_ciudad, ver_linea, ver_recorrido
from apps.core.views import redirect_nuevas_urls
from apps.catastro.views import administrativearea


urlpatterns = [
    re_path(r'^a/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', administrativearea, name='administrativearea'),
    re_path(r'^a/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', administrativearea, name='administrativearea_redirect'),

    re_path(r'^l/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', ver_linea, name='ver_linea'),
    re_path(r'^l/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', ver_linea, name='ver_linea_redirect'),

    re_path(r'^r/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', ver_recorrido, name='ver_recorrido'),
    re_path(r'^r/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', ver_recorrido, name='ver_recorrido_redirect'),

    # Paradas
    re_path(r'^parada/(?P<id>[\d]+)/$', ver_parada, name='ver_parada'),

    # Redirects para las URLs viejas
    re_path(r'^(?P<slug_ciudad>[\w-]+)/$', redirect_nuevas_urls),
    re_path(r'^(?P<slug_ciudad>[\w-]+)/(?P<slug_linea>[\w-]+)/$', redirect_nuevas_urls),
    re_path(r'^(?P<slug_ciudad>[\w-]+)/(?P<slug_linea>[\w-]+)/(?P<slug_recorrido>[\w-]+)/$', redirect_nuevas_urls),
    re_path(r'^$', redirect_nuevas_urls),

    # only for local dev / debugging purposes
    # re_path(r'mapa/(?P<administrativearea_slug>[^/]+)/$', ver_mapa_ciudad, name='ver_mapa_ciudad'),
]
