from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^moderar/$', views.mostrar_ediciones, name='mostrar_ediciones'),
    re_path(r'^moderar/id:(?P<id>\d+)/$', views.moderar_ediciones_id, name='moderar_ediciones_id'),
    re_path(r'^moderar/uuid:(?P<uuid>[-\w]+)/$', views.moderar_ediciones_uuid, name='moderar_ediciones_uuid'),
    re_path(r'^moderar/uuid:(?P<uuid>[-\w]+)/aprobar/$', views.moderar_ediciones_uuid_aprobar, name='moderar_ediciones_uuid_aprobar'),
    re_path(r'^moderar/uuid:(?P<uuid>[-\w]+)/rechazar/$', views.moderar_ediciones_uuid_rechazar, name='moderar_ediciones_uuid_rechazar'),

    # Indexable por google (pretty url)
    re_path(r'^revision/(?P<id_revision>[-\w]+)/$', views.revision, name='revision'),

    re_path(r'^(?P<id_recorrido>\d+)/$', views.editor_recorrido, name='editor_recorrido'),
]
