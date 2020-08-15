from django.conf.urls import include, url
from django.urls import path
from django.contrib.gis import admin
from django.conf import settings

from django.contrib.sitemaps import views as sitemaps_views
from .sitemaps import sitemaps, getsitemaps
from apps.catastro.management.commands.update_osm import kings

from django.views.static import serve
from apps.core.views import index
from apps.core.urls import urlpatterns as urlpatternsCore
from apps.catastro.urls import urlpatterns as urlpatternsCatastro, oldurlpattern as oldurlpatternsCatastro
from apps.editor.urls import urlpatterns as editorUrls
from apps.usuarios.urls import urlpatterns as usuariosUrls
from apps.editor.views import revision
from apps.api3.urls import urlpatterns as api3Urls
from apps.core.views import agradecimientos
from django.contrib.sites.models import Site

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = [
    url(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    # APPS de CualBondi
    url(settings.ADMIN_URL, admin.site.urls),
    url(r'^editor/', include(editorUrls)),
    url(r'^usuarios/', include(usuariosUrls)),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^revision/(?P<id_revision>[-\w]+)/$', revision, name='revision_externa'),

    # Ranking aka agradecimientos
    url(r'^agradecimientos/$', agradecimientos, name='agradecimientos'),

    path(r'sitemap.xml', sitemaps_views.index, {'sitemaps': sitemaps}),
    path('sitemap-<section>.xml', sitemaps_views.sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    url(r'^api/v3/', include(api3Urls)),
    url(r'^v3/', include(api3Urls)),
    url(r'^auth/', include('rest_framework_social_oauth2.urls', namespace='drfsocial')),
    url('', include('social_django.urls', namespace='social'))
]


for name,k in kings.items():
    cc = k['country_code']
    urlpatterns.append(path(f'{cc}/sitemap.xml', sitemaps_views.index, {'sitemaps': getsitemaps(cc), 'sitemap_url_name': f'django.contrib.sitemaps.views.sitemap-{cc}'}))
    urlpatterns.append(path(f'{cc}/sitemap-<section>.xml', sitemaps_views.sitemap, {'sitemaps': getsitemaps(cc)}, name=f'django.contrib.sitemaps.views.sitemap-{cc}'))


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

urlpatterns += [
    url(r'^$', index, name='index'),
    url(r'^como-llegar/', include(oldurlpatternsCatastro)),
    url(r'^(?P<country_code>[a-z][a-z])/', include(urlpatternsCatastro)),
    url(r'^(?P<country_code>[a-z][a-z])/', include(urlpatternsCore)),
    url(r'^', include(urlpatternsCatastro)),
    url(r'^', include(urlpatternsCore)),
]

handler500 = 'apps.core.views.server_error'
