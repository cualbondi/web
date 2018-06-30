from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView

urlpatterns = [
    url(r'^$', 'apps.core.views.index', name='index'),

    # Agregar contenido
#    url(r'^lineas/agregar/$', 'apps.core.views.agregar_linea', name='agregar_linea'),
#    url(r'^recorridos/agregar/$', 'apps.core.views.agregar_recorrido', name='agregar_recorrido'),

    url(r'^facebook_tab/$', 'apps.core.views.facebook_tab', name='facebook_tab'),

    # Paradas
    url(r'^parada/(?P<id>[\d]+)/$', 'apps.core.views.ver_parada', name='ver_parada'),

    # Redirects para las URLs viejas
    url(r'^recorridos/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/(?P<recorrido>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),
    url(r'^(?P<ciudad>[^/]+)/recorridos/(?P<linea>[^/]+)/(?P<ramal>[^/]+)/(?P<recorrido>[^/]+)/$', 'apps.core.views.redirect_nuevas_urls', name='redirect_nuevas_urls'),

    # Ciudades
    url(r'^(?P<nombre_ciudad>[\w-]+)/$', 'apps.core.views.ver_ciudad', name='ver_ciudad'),
    url(r'^mapa/(?P<nombre_ciudad>[\w-]+)/$',
        'apps.core.views.ver_mapa_ciudad', name='ver_mapa_ciudad'),

    # Lineas
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/$', 'apps.core.views.ver_linea', name='ver_linea'),

    # Recorridos
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/(?P<nombre_recorrido>[\w-]+)/$', 'apps.core.views.ver_recorrido', name='ver_recorrido'),

]

#        // *** TODO: django debug toolbar ** * //
#        // *** TODO: mover calles arriba ** * //
#        // *** TODO: cache nginx? ** * //


#cualbondi.com.ar/la-plata/recorridos/Norte/10/IDA/
