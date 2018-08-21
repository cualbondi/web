from django.core.management.base import BaseCommand
from apps.catastro.models import Ciudad
from apps.core.models import Recorrido, Linea


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Calculando envolventes para ciudades...")
        ciudades = Ciudad.objects.all()
        query = """
            SELECT
                id,
                wkt
            FROM
                (
                SELECT
                    id,
                    (ST_Dump(wkt)).geom as wkt
                FROM
                    (
                    SELECT
                        c.id as id,
                        ST_Union(ST_Buffer(r.ruta, 0.0045)) as wkt
                    FROM
                        core_recorrido as r
                        join catastro_ciudad_recorridos as cr on (cr.recorrido_id = r.id)
                        join catastro_ciudad as c on (cr.ciudad_id = c.id)
                    WHERE
                        cr.ciudad_id = %(id_ciudad)s
                    GROUP BY
                        c.id
                    ) as inner1
                ) as inner2
            ORDER BY
                ST_Area(wkt) desc
            LIMIT
                1
            ;
        """
        for ciudad in ciudades:
            print("Procesando ciudad:", ciudad.nombre)
            params = {"id_ciudad": int(ciudad.id)}
            envolvente = Recorrido.objects.raw(query, params)[0].wkt
            ciudad.envolvente = envolvente
            try:
                ciudad.save()
            except TypeError as e:
                print("no se pudo asignar envolvente:", ciudad.nombre)
                print(e)

        print()
        print("Calculando envolventes para lineas...")
        lineas = Linea.objects.all()
        query = """
            SELECT
                id,
                wkt
            FROM
                (
                SELECT
                    id,
                    (ST_Dump(wkt)).geom as wkt
                FROM
                    (
                    SELECT
                        l.id,
                        ST_Union(ST_Buffer(ruta, 0.0045)) as wkt
                    FROM
                        core_recorrido as r
                        join core_linea as l on (r.linea_id = l.id)
                    WHERE
                        l.id = %(id_li)s
                    GROUP BY
                        l.id
                    ) as inner1
                ) as inner2
            ORDER BY
                ST_Area(wkt) desc
            LIMIT
                1
            ;
        """
        for linea in lineas:
            print("Procesando:", linea.nombre)
            params = {"id_li": int(linea.id)}
            try:
                envolvente = Recorrido.objects.raw(query, params)[0].wkt
            except IndexError:
                envolvente = None
            linea.envolvente = envolvente
            try:
                linea.save()
            except TypeError:
                print("No se pudo asignar envolvente:", linea.nombre, linea.ciudad_set.all())
