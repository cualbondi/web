from django.conf.urls import url
from apps.core.views import index, ver_parada, ver_mapa_ciudad, ver_linea, ver_recorrido
from apps.catastro.views import administrativearea


urlpatterns = [
    url(r'^$', index, name='index'),

    url(r'^a/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', administrativearea, name='administrativearea'),
    url(r'^a/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', administrativearea, name='administrativearea_redirect'),

    url(r'^l/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', ver_linea, name='ver_linea'),
    url(r'^l/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', ver_linea, name='ver_linea_redirect'),

    url(r'^r/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)/(?P<slug>[^/]+)/$', ver_recorrido, name='ver_recorrido'),
    url(r'^r/(?P<osm_type>[^\d])(?P<osm_id>[^/]+)', ver_recorrido, name='ver_recorrido_redirect'),

    # Paradas
    url(r'^parada/(?P<id>[\d]+)/$', ver_parada, name='ver_parada'),

    # TODO: Redirects para las URLs viejas

    url(r'mapa/(?P<administrativearea_slug>[^/]+)/$', ver_mapa_ciudad, name='ver_mapa_ciudad'),

    # Ciudades
    # url(r'^(?P<nombre_ciudad>[\w-]+)/$', ver_ciudad, name='ver_ciudad'),
    # url(r'^mapa/(?P<nombre_ciudad>[\w-]+)/$', ver_mapa_ciudad, name='ver_mapa_ciudad'),

    # Lineas
    # url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/$', ver_linea_redirect_old, name='ver_linea_redirect_old'),

    # Recorridos
    # url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/(?P<nombre_recorrido>[\w-]+)/$', ver_recorrido, name='ver_recorrido'),
]
