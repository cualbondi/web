from django.conf.urls import url, include
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
    url(r'^recorridos-por-ciudad/(?P<ciudad_id>\d+)/$', views.RecorridosPorCiudad.as_view({'get': 'list'})),
    url(r'^recorridos-best-matches/(?P<ciudad_id>\d+)/$', views.best_matches),
    url(r'^match-recorridos/(?P<recorrido_id>\d+)/$', views.match_recorridos),
    url(r'^importerlog-stats/$', views.importerlog_stats),
    url(r'^display-recorridos/', views.display_recorridos),
    url(r'^', include((router.urls, 'v3'), namespace='v3')),
]
