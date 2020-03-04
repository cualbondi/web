from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^p/(?P<osm_type>w|n)(?P<osm_id>\d+)/(?P<slug>[^/]*)/$', views.poi, name='poi'),
    url(r'^como-llegar/(?P<slug>[^/]+)/$', views.poiORint, name='poi_old'),
]

oldurlpattern = [
    url(r'^(?P<slug>[^/]+)/$', views.poiORint, name='poi_old'),
]
