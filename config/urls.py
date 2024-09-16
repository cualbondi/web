from django.urls import path, re_path, include
from django.contrib.gis import admin
from django.conf import settings

from django.contrib.sitemaps import views as sitemaps_views
from .sitemaps import sitemaps
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
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

    # APPS de CualBondi
    re_path(settings.ADMIN_URL, admin.site.urls),
    re_path(r'^editor/', include(editorUrls)),
    re_path(r'^usuarios/', include(usuariosUrls)),
    re_path(r'^comments/', include('django_comments.urls')),
    re_path(r'^revision/(?P<id_revision>[-\w]+)/$', revision, name='revision_externa'),

    # Ranking aka agradecimientos
    re_path(r'^agradecimientos/$', agradecimientos, name='agradecimientos'),

    path('sitemap.xml', sitemaps_views.index, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.index'),
    path('sitemap-<section>.xml', sitemaps_views.sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    re_path(r'^api/v3/', include(api3Urls)),
    re_path(r'^v3/', include(api3Urls)),
    re_path(r'^auth/', include('rest_framework_social_oauth2.urls', namespace='drfsocial')),

    re_path(r'^robots.txt$', serve, {'document_root': settings.STATIC_ROOT, 'path': 'robots.txt', 'show_indexes': False}),
    re_path(r'^ads.txt$', serve, {'document_root': settings.STATIC_ROOT, 'path': 'ads.txt', 'show_indexes': False}),

    re_path(r'', include('social_django.urls', namespace='social'))
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

urlpatterns += [
    re_path(r'^$', index, name='index'),
    re_path(r'^como-llegar/', include(oldurlpatternsCatastro)),
    re_path(r'^(?P<country_code>[a-z][a-z])/', include(urlpatternsCatastro)),
    re_path(r'^(?P<country_code>[a-z][a-z])/', include(urlpatternsCore)),
    re_path(r'^', include(urlpatternsCatastro)),
    re_path(r'^', include(urlpatternsCore)),
]

handler500 = 'apps.core.views.server_error'
