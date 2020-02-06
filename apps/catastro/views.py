from django.shortcuts import (get_object_or_404, render)
from django.http import HttpResponsePermanentRedirect
from django.views.decorators.http import require_GET
from django.db.models import Prefetch, Count, OuterRef, Subquery, IntegerField
from django.contrib.gis.db.models.functions import GeoFunc, Cast, Value
from django.template.defaultfilters import slugify

from apps.catastro.models import Poi, Ciudad, Interseccion, AdministrativeArea
from apps.core.models import Recorrido, Parada, Linea
from apps.utils.parallel_query import parallelize


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


def poiORint(request, slug=None):
    poi = None
    pois = Poi.objects.filter(slug=slug)

    try:
        if pois:
            poi = pois[0]
        else:
            poi = get_object_or_404(Interseccion, slug=slug)
    except Exception:
        pois = fuzzy_like_query(slug)
        slug = slug.replace('-', ' ')
        return render(request, 'catastro/ver_poi-404.html', {'slug': slug, 'pois': pois}, status=404)

    aas = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=poi.latlng) \
        .order_by('depth') \
        .reverse()

    # poi found, check if url is ok
    correct_url = poi.get_absolute_url()
    if aas:
        aarootname = aas[0].name
        correct_url = poi.get_absolute_url(aarootname == 'Argentina')
    if request.build_absolute_uri() != correct_url:
        return HttpResponsePermanentRedirect(correct_url)

    # TODO: resolver estas queries en 4 threads
    #       ver https://stackoverflow.com/a/12542927/912450
    recorridos = Recorrido.objects \
        .filter(ruta__dwithin=(poi.latlng, 0.002)) \
        .select_related('linea') \
        .prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.all().only('slug'))) \
        .order_by('linea__nombre', 'nombre') \
        .defer('linea__envolvente', 'ruta')
    near_pois = Poi.objects.filter(latlng__dwithin=(poi.latlng, 0.111)).exclude(id=poi.id)
    ps = Parada.objects.filter(latlng__dwithin=(poi.latlng, 0.003))

    try:
        amenity = amenities[poi.tags['amenity']]
    except KeyError:
        amenity = None

    return render(
        request,
        'catastro/ver_poi.html',
        {
            'obj': poi,
            'amenity': amenity,
            'adminareas': aas,
            'paradas': ps,
            'poi': poi,
            'recorridos': recorridos,
            'pois': near_pois
        }
    )


class Simplify(GeoFunc):
    def __init__(self, expression, tolerance=0.02, **extra):
        super().__init__(expression, tolerance, **extra)


def administrativearea(request, osm_type=None, osm_id=None, slug=None):
    qs = AdministrativeArea.objects.defer('geometry')
    aa = get_object_or_404(qs, osm_type=osm_type, osm_id=osm_id)
    aarootname = aa.get_root().name
    correct_url = aa.get_absolute_url(aarootname == 'Argentina')
    if request.build_absolute_uri() != correct_url:
        return HttpResponsePermanentRedirect(correct_url)
    else:
        lineas = None
        pois = None
        ps = None
        if aa.geometry_simple is not None:
            lineas, pois, ps, aaancestors, children, recorridos = parallelize(
                Linea
                .objects
                .filter(recorridos__ruta__intersects=aa.geometry_simple)
                .order_by('nombre')
                .annotate(dcount=Count('id'))
                .defer('envolvente') if aa.depth > 2 else None,
                Poi
                .objects
                .filter(latlng__intersects=aa.geometry_simple)
                .order_by('?')[:30] if aa.depth > 2 else None,
                Parada
                .objects
                .filter(latlng__intersects=aa.geometry_simple)
                .order_by('?')[:30] if aa.depth > 2 else None,
                aa.get_ancestors().reverse(),
                aa.get_children().annotate(
                    recorridos_count=Cast(Subquery(
                        Recorrido.objects
                        .order_by()
                        .annotate(group=Value(1))
                        .filter(ruta__intersects=OuterRef('geometry'))
                        .values('group')
                        .annotate(count=Count('*'))
                        .values('count')
                    ), output_field=IntegerField())
                ).order_by('-recorridos_count', 'name'),
                Recorrido
                .objects
                .filter(ruta__intersects=aa.geometry_simple, linea__isnull=True)
                .order_by('nombre')
                .defer('ruta') if aa.depth > 2 else None
            )
        return render(
            request,
            'catastro/ver_administrativearea.html',
            {
                'obj': aa,
                'adminarea': aa,
                'adminareaancestors': aaancestors,
                'aacentroid': aa.geometry_simple.centroid,
                'children': children,
                'paradas': ps,
                'lineas': lineas,
                'recorridos': recorridos,
                'pois': pois
            }
        )
