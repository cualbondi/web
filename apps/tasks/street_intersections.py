from .logging import logger
from django.db import connection
from apps.catastro.models import Interseccion


class StreetIntersectionsTask:
    def run(self):
        cu = connection.cursor()

        logger.info("Generando Intersecciones")
        cu.execute("delete from catastro_interseccion")
        cu.execute(
            """
            SELECT
                SEL1.nom || ' y ' || SEL2.nom as nom,
                upper(translate(SEL1.nom || ' y ' || SEL2.nom, 'áéíóúÁÉÍÓÚäëïöüÄËÏÖÜñÑàèìòùÀÈÌÒÙ', 'AEIOUAEIOUAEIOUAEIOUNNAEIOUAEIOU')) as nom_normal,
                ST_Intersection(SEL1.way, SEL2.way) as latlng
            FROM
                catastro_calle AS SEL1
                join catastro_calle as SEL2 on (ST_Intersects(SEL1.way, SEL2.way) and ST_GeometryType(ST_Intersection(SEL1.way, SEL2.way):: Geometry)='ST_Point' )
        """
        )
        logger.info("Generando slugs")
        intersections = cu.fetchall()
        total = len(intersections)
        i = 0
        for inter in intersections:
            i = i + 1
            Interseccion.objects.create(
                nom=inter[0], nom_normal=inter[1], latlng=inter[2]
            )
            if (i * 100.0 / total) % 1 == 0:
                logger.info("{:2.0f}%".format(i * 100.0 / total))
