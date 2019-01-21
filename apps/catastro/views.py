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


@csrf_exempt
@require_GET
def poiORint(request, slug=None):
    poi = None
    pois = Poi.objects.filter(slug=slug)

    try:
        if pois:
            poi = pois[0]
        else:
            poi = get_object_or_404(Interseccion, slug=slug)
    except Exception as e:
        pois = fuzzy_like_query(slug)
        slug = slug.replace('-', ' ')
        return render(request, 'catastro/ver_poi-404.html', {'slug': slug, 'pois': pois}, status=404)
    # TODO: resolver estas queries en 4 threads
    #       ver https://stackoverflow.com/a/12542927/912450
    recorridos = Recorrido.objects \
        .filter(ruta__dwithin=(poi.latlng, 0.002)) \
        .select_related('linea') \
        .prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.all().only('slug'))) \
        .order_by('linea__nombre', 'nombre') \
        .defer('linea__envolvente', 'ruta')
    pois = Poi.objects.filter(latlng__dwithin=(poi.latlng, 0.111)).exclude(id=poi.id)
    ps = Parada.objects.filter(latlng__dwithin=(poi.latlng, 0.003))
    ciudad_actual = Ciudad.objects.annotate(distance=Distance('centro', poi.latlng)).order_by('distance').first()

    template = 'catastro/ver_poi.html'
    if (request.GET.get("dynamic_map")):
        template = 'core/ver_obj_map.html'

    amenity = None
    try:
        amenity = amenities[poi.tags['amenity']]
    except KeyError:
        pass

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
            'pois': pois
        }
    )


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
