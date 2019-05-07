from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^logout/$', views.cerrar_sesion),
    # url(r'^login_ajax/(?P<backend>[^/]+)/$', views.ajax_auth, name='ajax_auth'),
    url(r'^(?P<username>[^/]+)/$', views.ver_perfil, name="ver_perfil"),
]
