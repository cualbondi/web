from django.contrib.gis import admin

from .models import Provincia, Ciudad, Poicb, Zona, ImagenCiudad, AdministrativeArea
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory


class CustomAdmin(admin.OSMGeoAdmin):
    search_fields = ['nombre', 'variantes_nombre']
    exclude = ()


class ZonaAdmin(admin.OSMGeoAdmin):
    search_fields = ['name']


class AdministrativeAreaAdmin(TreeAdmin):
    form = movenodeform_factory(AdministrativeArea)


admin.site.register(Provincia, CustomAdmin)
admin.site.register(Ciudad, CustomAdmin)
admin.site.register(Poicb, CustomAdmin)
admin.site.register(ImagenCiudad, CustomAdmin)
admin.site.register(Zona, ZonaAdmin)
admin.site.register(AdministrativeArea, AdministrativeAreaAdmin)
