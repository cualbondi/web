from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'apps.core.views.index', name='index'),

    # Agregar contenido
#    url(r'^lineas/agregar/$', 'apps.core.views.agregar_linea', name='agregar_linea'),
#    url(r'^recorridos/agregar/$', 'apps.core.views.agregar_recorrido', name='agregar_recorrido'),

    # Editor
    url(r'^login_ajax/(?P<backend>[^/]+)/$', 'apps.core.views.ajax_auth', name='ajax_auth'),
    url(r'^editor/moderar/$', 'apps.core.views.mostrar_ediciones', name='mostrar_ediciones'),
    url(r'^editor/moderar/id:(?P<id>\d+)/$', 'apps.core.views.moderar_ediciones_id', name='moderar_ediciones_id'),
    url(r'^editor/moderar/uuid:(?P<uuid>[-\w]+)/$', 'apps.core.views.moderar_ediciones_uuid', name='moderar_ediciones_uuid'),
    url(r'^editor/moderar/uuid:(?P<uuid>[-\w]+)/aprobar/$', 'apps.core.views.moderar_ediciones_uuid_aprobar', name='moderar_ediciones_uuid_aprobar'),
    url(r'^editor/moderar/uuid:(?P<uuid>[-\w]+)/rechazar/$', 'apps.core.views.moderar_ediciones_uuid_rechazar', name='moderar_ediciones_uuid_rechazar'),
    url(r'^editor/(?P<id_recorrido>\d+)/$', 'apps.core.views.editor_recorrido', name='editor_recorrido'),

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
    url(r'^mapa/(?P<nombre_ciudad>[\w-]+)/$', 'apps.core.views.ver_mapa_ciudad', name='ver_mapa_ciudad'),

    # Lineas
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/$', 'apps.core.views.ver_linea', name='ver_linea'),

    # Recorridos
    url(r'^(?P<nombre_ciudad>[\w-]+)/(?P<nombre_linea>[\w-]+)/(?P<nombre_recorrido>[\w-]+)/$', 'apps.core.views.ver_recorrido', name='ver_recorrido'),

)

#cualbondi.com.ar/la-plata/recorridos/Norte/10/IDA/
