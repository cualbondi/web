from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^moderar/$', views.mostrar_ediciones, name='mostrar_ediciones'),
    url(r'^moderar/id:(?P<id>\d+)/$', views.moderar_ediciones_id, name='moderar_ediciones_id'),
    url(r'^moderar/uuid:(?P<uuid>[-\w]+)/$', views.moderar_ediciones_uuid, name='moderar_ediciones_uuid'),
    url(r'^moderar/uuid:(?P<uuid>[-\w]+)/aprobar/$', views.moderar_ediciones_uuid_aprobar, name='moderar_ediciones_uuid_aprobar'),
    url(r'^moderar/uuid:(?P<uuid>[-\w]+)/rechazar/$', views.moderar_ediciones_uuid_rechazar, name='moderar_ediciones_uuid_rechazar'),

    # Indexable por google (pretty url)
    url(r'^revision/(?P<id_revision>[-\w]+)/$', views.revision, name='revision'),

    url(r'^(?P<id_recorrido>\d+)/$', views.editor_recorrido, name='editor_recorrido'),
]
