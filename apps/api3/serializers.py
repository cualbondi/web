import base64
import json

import geobuf
from django.contrib.gis.geos import GEOSGeometry
from rest_framework import serializers

from apps.catastro.models import Ciudad
from apps.core.models import Linea, Parada, Recorrido, ImporterLog


class CiudadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ciudad
        fields = (
            'id',
            'nombre',
            'slug',
            'centro',
            'activa',
            'img_panorama',
            'img_cuadrada',
        )


class LineaSerializerFull(serializers.ModelSerializer):
    class Meta:
        model = Linea
        fields = (
            'id',
            'nombre',
            'slug',
            'ciudades',
        )


class RouterResultSerializer(serializers.Serializer):

    def to_representation(self, obj):
        if not hasattr(obj, 'id2'):
            return {
                "id": obj.id,
                "itinerario": [
                    {
                        "id": obj.id,
                        "ruta_corta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_corta_geojson))),
                        "long_bondi": obj.long_ruta,
                        "long_pata": obj.long_pata,
                        "color_polilinea": obj.color_polilinea,
                        "inicio": obj.inicio,
                        "fin": obj.fin,
                        "nombre": obj.nombre,
                        "foto": obj.foto,
                        "p1": getParada(obj.p1),
                        "p2": getParada(obj.p2),
                        "paradas": [
                            {
                                "latlng": p.latlng.coords[::-1],
                                "codigo": p.codigo,
                                "nombre": p.nombre
                            }
                            for p in obj.paradas.all()
                        ],
                        "url": obj.get_absolute_url(),
                    }
                ]
            }
        else:
            obj2 = Recorrido.objects.prefetch_related('paradas').get(pk=obj.id2)
            return {
                "id": str(obj.id) + str(obj.id2),
                "long_pata_transbordo": obj.long_pata_transbordo,
                "itinerario": [
                    {
                        "id": obj.id,
                        "ruta_corta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_corta_geojson))),
                        "ruta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_larga))),
                        "long_bondi": obj.long_ruta,
                        "long_pata": obj.long_pata,
                        "color_polilinea": obj.color_polilinea,
                        "inicio": obj.inicio,
                        "fin": obj.fin,
                        "nombre": obj.nombre,
                        "foto": obj.foto,
                        "p1": getParada(obj.p11ll),
                        "p2": getParada(obj.p12ll),
                        "paradas": [
                            {
                                "latlng": p.latlng.coords[::-1],
                                "codigo": p.codigo,
                                "nombre": p.nombre
                            } for p in obj.paradas.all()
                        ],
                        "url": obj.get_absolute_url(),
                    },
                    {
                        "id": obj.id2,
                        "ruta_corta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_corta_geojson2))),
                        "ruta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_larga2))),
                        "long_bondi": obj.long_ruta2,
                        "long_pata": obj.long_pata2,
                        "color_polilinea": obj.color_polilinea2,
                        "inicio": obj.inicio2,
                        "fin": obj.fin2,
                        "nombre": obj.nombre2,
                        "foto": obj.foto2,
                        "p1": getParada(obj.p21ll),
                        "p2": getParada(obj.p22ll),
                        "paradas": [
                            {
                                "latlng": p.latlng.coords[::-1],
                                "codigo": p.codigo,
                                "nombre": p.nombre
                            } for p in obj2.paradas.all()
                        ],
                        "url": obj2.get_absolute_url(),
                    }
                ]
            }


def getParada(parada_id):
    if parada_id is None:
        return None
    else:
        p = Parada.objects.get(pk=parada_id)
        return {
            "latlng": p.latlng.coords[::-1],
            "codigo": p.codigo,
            "nombre": p.nombre
        }


class RecorridoPureModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recorrido
        fields = '__all__'

# class RecorridoSerializer(serializers.Serializer):

#     def to_representation(self, obj):
#         ruta = copy(obj.ruta)
#         ruta.transform(3857)
#         length = ruta.length
#         return {
#             'id': obj.id,
#             'nombre': obj.nombre,
#             'nombre_linea': obj.linea.nombre,
#             'color_polilinea': obj.color_polilinea,
#             'sentido': obj.sentido,
#             'descripcion': obj.descripcion,
#             'inicio': obj.inicio,
#             'fin': obj.fin,
#             'ruta': obj.ruta.wkt,
#             'long_ruta': length,
#             'foto': obj.foto if hasattr(obj, 'foto') else '',
#             # 'url': obj.get_absolute_url(None, None, obj.slug),
#         }


class RecorridoCustomSerializer(serializers.Serializer):

    def to_representation(self, obj):
        return {
            "id": obj.id,
            "osm_id": obj.osm_id,
            "ruta_corta": base64.b64encode(geobuf.encode(json.loads(obj.ruta_corta_geojson))),
            "long_bondi": obj.long_ruta,
            "color_polilinea": obj.color_polilinea,
            "inicio": obj.inicio,
            "fin": obj.fin,
            "nombre": obj.nombre,
            "foto": obj.foto,
            "paradas": [
                {
                    "latlng": p.latlng.coords[::-1],
                    "codigo": p.codigo,
                    "nombre": p.nombre
                }
                for p in obj.paradas.all()
            ],
        }


class LineaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Linea
        fields = ('id', 'nombre')


class RecorridoModelSerializer(serializers.ModelSerializer):
    linea = LineaSerializer()

    class Meta:
        model = Recorrido
        fields = ('id', 'nombre', 'linea', 'ruta', 'osm_id')


class GeocoderSerializer(serializers.Serializer):
    nombre = serializers.ReadOnlyField()
    geom = serializers.SerializerMethodField()
    precision = serializers.ReadOnlyField()
    tipo = serializers.ReadOnlyField()

    def get_geom(self, obj):
        return json.loads(GEOSGeometry(obj['geom'], srid=4326).geojson)


class GeocoderSuggestSerializer(serializers.Serializer):
    nombre = serializers.ReadOnlyField()
    magickey = serializers.ReadOnlyField()


class ImporterLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ImporterLog
        fields = '__all__'
