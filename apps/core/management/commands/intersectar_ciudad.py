from django.core.management.base import BaseCommand
from apps.core.models import Recorrido
from apps.catastro.models import Ciudad
from django.contrib.gis.db.models.functions import Distance


class Command(BaseCommand):

    def handle(self, *args, **options):
        stats = {}
        recorridos = Recorrido.objects.all()
        ciudades = Ciudad.objects.all()
        for ciudad in ciudades:
            print(ciudad.recorridos.through.objects.all().count())
            stats[ciudad.id] = 0
            for recorrido in recorridos:
                """ Checkear si la ciudad intersecta
                    al recorrido. Si lo intersecta
                    agregarlo a la relacion ManyToMany
                """
                if ciudad.poligono.intersects(recorrido.ruta):
                    stats[ciudad.id] += 1
                    ciudad.recorridos.add(recorrido)
                    ciudad.lineas.add(recorrido.linea)
            if len(ciudad.recorridos.all())>0:
                ciudad.activa=True
                ciudad.save()
                print(ciudad, stats[ciudad.id])

        for recorrido in recorridos:
            ok = False
            for ciudad in ciudades:
                if ciudad.poligono.intersects(recorrido.ruta):
                    ok = True
                    break
            if not ok:
                c = Ciudad.objects.annotate(
                    dist=Distance('poligono', recorrido.ruta)
                ).order_by('dist').first()
                print("NO COLLIDE", recorrido, "assigning closest: ", c.slug)
                c.recorridos.add(recorrido)
                c.lineas.add(recorrido.linea)
