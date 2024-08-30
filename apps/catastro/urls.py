from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^p/(?P<osm_type>w|n)(?P<osm_id>\d+)/(?P<slug>[^/]*)/$', views.poi, name='poi'),
    re_path(r'^como-llegar/(?P<slug>[^/]+)/$', views.poiORint, name='poi_old'),
]

oldurlpattern = [
    re_path(r'^(?P<slug>[^/]+)/$', views.poiORint, name='poi_old'),
]
