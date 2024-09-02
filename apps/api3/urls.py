from django.urls import re_path, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()

router.register(r'ciudades', views.CiudadesViewSet)
router.register(r'lineas', views.LineasViewSet)
router.register(r'recorridos', views.RecorridosViewSet)
router.register(r'geocoder', views.GeocoderViewSet, "geocoder")
router.register(r'geocoder/suggest', views.GeocoderSuggestViewSet, "geocoder/suggest"),
router.register(r'geocoder/reverse', views.ReverseGeocoderView, "geocoder/reverse")
router.register(r'me', views.UserViewSet, basename='me')
router.register(r'importerlog', views.ImporterLogViewSet, basename='importerlog')

urlpatterns = [
    re_path(r'^recorridos-por-ciudad/(?P<ciudad_id>\d+)/$', views.RecorridosPorCiudad.as_view({'get': 'list'})),
    re_path(r'^recorridos-best-matches/(?P<ciudad_id>\d+)/$', views.best_matches),
    re_path(r'^match-recorridos/(?P<recorrido_id>\d+)/$', views.match_recorridos),
    re_path(r'^importerlog-stats/$', views.importerlog_stats),
    re_path(r'^display-recorridos/', views.display_recorridos),
    re_path(r'^', include((router.urls, 'v3'), namespace='v3')),
]
