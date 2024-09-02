# TODO: rename this module back to admin.py and migrate it
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis import admin
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from apps.core.models import (Linea, Recorrido, Tarifa, Parada,
                              Horario, Posicion)

UserAdmin.list_display += ('date_joined',)
UserAdmin.list_filter += ('date_joined',)
UserAdmin.list_display += ('last_login',)
UserAdmin.list_filter += ('last_login',)


class CustomAdmin(admin.GISModelAdmin):
    default_lon = -6428013
    default_lat = -4177742
    search_fields = ['nombre', 'recorrido__nombre']
    exclude = ()


class HorarioAdminInline(admin.TabularInline):
    model = Horario


class RecorridoCustomAdmin(admin.GISModelAdmin):
    display_raw = True
    search_fields = ['nombre', 'linea__nombre']
    inlines = (HorarioAdminInline,)
    exclude = ('horarios',)


# class ParadaCustomAdmin(admin.GISModelAdmin):
#     display_raw = True
#     search_fields = ['nombre', 'codigo']
#     # inlines = (HorarioAdminInline,)
#     readonly_fields = ('horarios',)

    # def horarios(self, instance):
    #     return format_html_join(
    #         mark_safe('<br/>'),
    #         '{0}',
    #         ((line,) for line in instance.horario_set.all()),
    #     ) or "<span class='errors'>Can't find horarios.</span>"

    # horarios.short_description = "Horarios"
    # horarios.allow_tags = True


admin.site.register(Linea, CustomAdmin)
admin.site.register(Recorrido, RecorridoCustomAdmin)
# admin.site.register(Parada, ParadaCustomAdmin)
admin.site.register(Tarifa)
admin.site.register(Posicion)
