from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^login/$', views.iniciar_sesion, {'template_name': 'usuarios/login.html'}, name='iniciar_sesion'),
    url(r'^logout/$', views.cerrar_sesion),
    url(r'^registracion/$', views.registrar_usuario),
    url(r'^confirmar-email/(\w+)/$', views.confirmar_email),
    url(r'^editar-perfil/$', views.editar_perfil),
    #url(r'^login_ajax/(?P<backend>[^/]+)/$', views.ajax_auth, name='ajax_auth'),
    url(r'^(?P<username>[^/]+)/$', views.ver_perfil),
]
