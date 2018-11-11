from django.core.management.base import BaseCommand
from apps.core.models import Recorrido
from apps.editor.models import RecorridoProposed
from django.utils.timezone import datetime


class Command(BaseCommand):
    help = 'update local database with osm POIs and Streets'

    def handle(self, *args, **options):

        print('FIXER')
        print('STEP 1')

        # agrega todos los cr en tabla rp
        for recorrido in Recorrido.objects.all():
            # if recorrido.id != 286:
            #     continue
            print(recorrido.id, end=' ')
            rp_accepted = RecorridoProposed.objects.filter(logmoderacion__newStatus='S', ruta=recorrido.ruta).order_by('-date_create')
            if rp_accepted:
                print('OK')
                recorrido.uuid = rp_accepted[0].uuid
                recorrido.save()
            else:
                print('creating proposed')
                rp = RecorridoProposed.from_recorrido(recorrido)
                rp.save(logmoderacion__newStatus='S')
                # set date to an init date
                date = datetime(2010, 1, 1)
                rp2 = RecorridoProposed.objects.filter(id=rp.id)
                rp2.update(date_create=date, date_update=date)
                rp2[0].logmoderacion_set.update(date_create=date)

        print('STEP 2')
        # acomoda parent uuid en tabla rp
        for recorrido in Recorrido.objects.all():
            # if recorrido.id != 286:
            #     continue
            print(recorrido.id)
            # recorrer todo el log desde el mas viejo viendo si alguno fue aceptado
            rps = list(RecorridoProposed.objects.filter(recorrido=recorrido).order_by('date_create'))
            if len(rps) > 0:
                current_parent = rps[0]
                current_parent.parent = None
                date_create = current_parent.date_create
                date_update = current_parent.date_update
                current_parent.save()
                RecorridoProposed.objects.filter(id=current_parent.id).update(date_create=date_create, date_update=date_update)
                for rp in rps[1:]:
                    rp.parent = current_parent.uuid
                    date_create = rp.date_create
                    date_update = rp.date_update
                    rp.save()
                    RecorridoProposed.objects.filter(id=rp.id).update(date_create=date_create, date_update=date_update)
                    if rp.logmoderacion_set.filter(newStatus='S').exists():
                        current_parent = rp
            else:
                print('error, no tiene RecorridoProposed el core_recorrido con recorrido_id: {}'.format(recorrido.id))

        print('FINISH')
