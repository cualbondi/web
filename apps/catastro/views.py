# -*- coding: UTF-8 -*-
from django.shortcuts import (get_object_or_404, render)
from django.http import HttpResponse, HttpResponsePermanentRedirect

from apps.catastro.models import Poi, Ciudad, Interseccion, AdministrativeArea
from apps.core.models import Recorrido, Parada, Linea

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.db.models import Prefetch, Count
from django.contrib.gis.db.models.functions import Distance
from django.template.defaultfilters import slugify


def fuzzy_like_query(q):
    params = {"q": q}
    query = """
        SELECT
            id,
            slug,
            nom,
            latlng::bytea
        FROM
            catastro_poi
        WHERE
            slug %% %(q)s
        ORDER BY
            similarity(slug, %(q)s) DESC
        LIMIT
            10
        ;
    """
    query_set = Poi.objects.raw(query, params)
    return list(query_set)


amenities = {
    'restaurant': 'Restaurant',
    'school': 'Escuela',
    'pharmacy': 'Farmacia',
    'Kindergarten': 'Jardin',
    'cafe': 'Cafe',
    'fast_food': 'Comida rapida',
    'bar': 'Bar',
    'place_of_worship': 'Templo',
    'college': 'Secundario',
    'ice_cream': 'Heladeria',
    'police': 'Policia',
    'hospital': 'Hospital',
    'clinic': 'Clinica',
    'community_centre': 'Centro comunitario',
    'veterinary': 'Veterinaria',
    'doctors': 'Doctor',
    'bicycle_rental': 'Alquiler de bicicletas',
    'taxi': 'Taxi',
    'library': 'Biblioteca',
    'dentist': 'Dentista',
    'bank': 'Banco',
    'theatre': 'Teatro',
    'car_wash': 'Lavadero de autos',
    'pub': 'Bar',
    'university': 'Universidad',
}


@require_GET
def poi(request, osm_type, osm_id, slug):
    poi = get_object_or_404(Poi, osm_type=osm_type, osm_id=osm_id)
    if slug != slugify(poi.nom):
        return HttpResponsePermanentRedirect(poi.get_absolute_url())
    recorridos = Recorrido.objects \
        .filter(ruta__dwithin=(poi.latlng, 0.002)) \
        .select_related('linea') \
        .prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.all().only('slug'))) \
        .order_by('linea__nombre', 'nombre') \
        .defer('linea__envolvente', 'ruta')
    near_pois = Poi.objects.filter(latlng__dwithin=(poi.latlng, 0.111)).exclude(id=poi.id)
    ps = Parada.objects.filter(latlng__dwithin=(poi.latlng, 0.003))
    ciudad_actual = Ciudad.objects.annotate(distance=Distance('centro', poi.latlng)).order_by('distance').first()

    template = 'catastro/ver_poi.html'
    if (request.GET.get("dynamic_map")):
        template = 'core/ver_obj_map.html'

    try:
        amenity = amenities[poi.tags['amenity']]
    except KeyError:
        amenity = None

    return render(
        request,
        template,
        {
            'obj': poi,
            'amenity': amenity,
            'ciudad_actual': ciudad_actual,
            'paradas': ps,
            'poi': poi,
            'recorridos': recorridos,
            'pois': near_pois
        }
    )


@csrf_exempt
@require_GET
def poiORint(request, slug=None):
    # poi = get_object_or_404(EntityRedirect, old_url=f'{slug}')
    # return HttpResponsePermanentRedirect(poi.get_absolute_url())
    pass


def zona(request, slug=None):
    return HttpResponse(status=504)


def administrativearea(request, osm_type=None, osm_id=None, slug=None):
    aa = get_object_or_404(AdministrativeArea, osm_type=osm_type, osm_id=osm_id)
    if slug is None or slug != slugify(aa.name):
        # Redirect with slug
        return HttpResponsePermanentRedirect(aa.get_absolute_url())
    else:
        template = 'catastro/ver_administrativearea.html'
        if (request.GET.get("dynamic_map")):
            template = 'core/ver_obj_map.html'
        aa_geometry = aa.geometry.simplify(0.02).ewkt
        lineas = Linea.objects \
            .filter(recorridos__ruta__intersects=aa_geometry) \
            .order_by('nombre') \
            .annotate(dcount=Count('id')) \
            .defer('envolvente')
        pois = Poi \
            .objects \
            .filter(latlng__intersects=aa_geometry) \
            .order_by('?') \
            [:30]
        ps = Parada.objects.filter(latlng__intersects=aa_geometry)
        return render(
            request,
            template,
            {
                'obj': aa,
                'paradas': ps,
                'lineas': lineas,
                'pois': pois
            }
        )
