from django.conf.urls import url
from apps.core.views import index, ver_parada, redirect_nuevas_urls, ver_ciudad, ver_mapa_ciudad, ver_linea, ver_recorrido


urlpatterns = [
    url(r'^$', index, name='index'),

    # Paradas
    url(r'^parada/(?P<id>[\d]+)/$', ver_parada, name='ver_parada'),

    # Redirects para las URLs viejas
    url(r'^recorridos/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/(?P<recorrido>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/(?P<recorrido>[^/]+)/$', redirect_nuevas_urls, name='redirect_nuevas_urls'),

    # Ciudades
    url(r'^(?P<nombre_ciudad>[\w-]+)/$', ver_ciudad, name='ver_ciudad'),
    url(r'^mapa/(?P<nombre_ciudad>[\w-]+)/$', ver_mapa_ciudad, name='ver_mapa_ciudad'),

    # Lineas
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/$', ver_linea, name='ver_linea'),

    # Recorridos
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/(?P<nombre_recorrido>[\w-]+)/$', ver_recorrido, name='ver_recorrido'),

]
