from django.contrib.gis.db.models.functions import Area, Intersection, Length
from django.contrib.gis.measure import A, D
from django.db.models import F
from django.core.management.base import BaseCommand

from apps.catastro.management.commands.update_osm import kings
from apps.catastro.models import AdministrativeArea, Poi
from apps.core.models import Linea, Parada, Recorrido


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Calculando country codes")
        b = kings
        aas = AdministrativeArea.objects.filter(depth=1)
        for aa in aas:
            cc = next(v['country_code'] for k,v in kings.items() if v['id'] == aa.osm_id)
            print(f' > {aa.osm_type} {aa.osm_id} {aa.name}')
            print('   - Lineas: ', end='')
            # Linea.objects.filter(envolvente__intersects=aa.geometry_simple).update(country_code=cc)
            print(Linea.objects \
                .annotate(intersection_area=Area(Intersection(F('envolvente'), aa.geometry_simple)) / Area(F('envolvente'))) \
                .filter(intersection_area__gt=A(sq_m=0.65)) \
                .update(country_code=cc))
            print('   - Recorrido: ', end='')
            print(Recorrido.objects \
                .annotate(intersection_len=Length(Intersection(F('ruta_simple'), aa.geometry_simple)) / Length(F('ruta_simple'))) \
                .filter(intersection_len__gt=D(m=0.65)) \
                .update(country_code=cc))
            print('   - Parada: ', end='')
            print(Parada.objects.filter(latlng__intersects=aa.geometry_simple).update(country_code=cc))
            print('   - Poi: ', end='')
            print(Poi.objects.filter(latlng__intersects=aa.geometry_simple).update(country_code=cc))
            print('   - AdministrativeArea: ', end='')
            print(AdministrativeArea.objects \
                .annotate(intersection_area=Area(Intersection(F('geometry_simple'), aa.geometry_simple)) / Area(F('geometry_simple'))) \
                .filter(intersection_area__gt=A(sq_m=0.65)) \
                .update(country_code=cc))
            print(' > DONE')
