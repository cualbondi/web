from django.conf.urls import patterns, url


urlpatterns = [
    url(r'^zona/(?P<slug>[^/]+)/$', 'apps.catastro.views.zona', name='zona'),
    url(r'^(?P<slug>[^/]+)/$', 'apps.catastro.views.poi', name='poi'),
]
