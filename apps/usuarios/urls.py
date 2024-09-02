from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^logout/$', views.cerrar_sesion),
    # re_path(r'^login_ajax/(?P<backend>[^/]+)/$', views.ajax_auth, name='ajax_auth'),
    re_path(r'^(?P<username>[^/]+)/$', views.ver_perfil, name="ver_perfil"),
]
