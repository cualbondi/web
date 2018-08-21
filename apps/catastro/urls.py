from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^zona/(?P<slug>[^/]+)/$', views.zona, name='zona'),
    url(r'^(?P<slug>[^/]+)/$', views.poiORint, name='poi'),
]
