import os

from django.contrib.gis.db.models.functions import Cast, GeoFunc, Value
from django.db.models import Count, IntegerField, OuterRef, Prefetch, Subquery
from django.http import (Http404, HttpResponse, HttpResponsePermanentRedirect,
                         StreamingHttpResponse)
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.utils.translation import pgettext
from django.views.decorators.http import require_GET

from apps.catastro.models import AdministrativeArea, Ciudad, Interseccion, Poi
from apps.core.models import Linea, Parada, Recorrido
from apps.utils.parallel_query import parallelize
from apps.utils.slugify import slugify
from apps.core.templatetags.lang_list import add_lang_qs


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

amenities_schemaorg_itemtype = {
    'restaurant': 'LocalBusiness',
    'school': 'EducationalOrganization',
    'pharmacy': 'MedicalOrganization',
    'Kindergarten': 'EducationalOrganization',
    'cafe': 'LocalBusiness',
    'fast_food': 'LocalBusiness',
    'bar': 'LocalBusiness',
    'place_of_worship': 'NGO',
    'college': 'EducationalOrganization',
    'ice_cream': 'LocalBusiness',
    'police': 'GovernmentOrganization',
    'hospital': 'MedicalOrganization',
    'clinic': 'MedicalOrganization',
    'community_centre': '',
    'veterinary': 'MedicalOrganization',
    'doctors': 'MedicalOrganization',
    'bicycle_rental': 'LocalBusiness',
    'taxi': 'Organization',
    'library': 'Organization',
    'dentist': 'MedicalOrganization',
    'bank': 'Organization',
    'theatre': 'Organization',
    'car_wash': 'LocalBusiness',
    'pub': 'LocalBusiness',
    'university': 'EducationalOrganization',
}

@require_GET
def poi(request, osm_type, osm_id, slug):
    poi = get_object_or_404(Poi, osm_type=osm_type, osm_id=osm_id)
    if slug != slugify(poi.nom):
        return HttpResponsePermanentRedirect(add_lang_qs(poi.get_absolute_url(), request))


def poiORint(request, slug=None, country_code=None):
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
        .order_by('depth')

    # poi found, check if url is ok
    if not aas:
        raise Http404
    correct_url = poi.get_absolute_url()
    if correct_url not in request.build_absolute_uri():
        return HttpResponsePermanentRedirect(add_lang_qs(correct_url, request))

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

    amenities = {
        'restaurant': pgettext('an amenity type', 'restaurant'),
        'school': pgettext('an amenity type', 'school'),
        'pharmacy': pgettext('an amenity type', 'pharmacy'),
        'Kindergarten': pgettext('an amenity type', 'Kindergarten'),
        'cafe': pgettext('an amenity type', 'cafe'),
        'fast_food': pgettext('an amenity type', 'fast_food'),
        'bar': pgettext('an amenity type', 'bar'),
        'place_of_worship': pgettext('an amenity type', 'place_of_worship'),
        'college': pgettext('an amenity type', 'college'),
        'ice_cream': pgettext('an amenity type', 'ice_cream'),
        'police': pgettext('an amenity type', 'police'),
        'hospital': pgettext('an amenity type', 'hospital'),
        'clinic': pgettext('an amenity type', 'clinic'),
        'community_centre': pgettext('an amenity type', 'community_centre'),
        'veterinary': pgettext('an amenity type', 'veterinary'),
        'doctors': pgettext('an amenity type', 'doctors'),
        'bicycle_rental': pgettext('an amenity type', 'bicycle_rental'),
        'taxi': pgettext('an amenity type', 'taxi'),
        'library': pgettext('an amenity type', 'library'),
        'dentist': pgettext('an amenity type', 'dentist'),
        'bank': pgettext('an amenity type', 'bank'),
        'theatre': pgettext('an amenity type', 'theatre'),
        'car_wash': pgettext('an amenity type', 'car_wash'),
        'pub': pgettext('an amenity type', 'pub'),
        'university': pgettext('an amenity type', 'university'),
    }

    try:
        amenity = amenities[poi.tags['amenity']]
    except KeyError:
        amenity = None

    try:
        schemaorg_itemtype = amenities_schemaorg_itemtype[poi.tags['amenity']]
    except KeyError:
        schemaorg_itemtype = 'Organization'


    context = {
        'obj': poi,
        'amenity': amenity,
        'schemaorg_itemtype': schemaorg_itemtype,
        'adminareas': aas,
        'paradas': ps,
        'poi': poi,
        'recorridos': recorridos,
        'pois': near_pois
    }

    return render(request, 'catastro/ver_poi.html', context)


class Simplify(GeoFunc):
    def __init__(self, expression, tolerance=0.02, **extra):
        super().__init__(expression, tolerance, **extra)

def administrativearea(request, osm_type=None, osm_id=None, slug=None, country_code=None):
    qs = AdministrativeArea.objects.defer('geometry')
    aa = get_object_or_404(qs, osm_type=osm_type, osm_id=osm_id)
    correct_url = aa.get_absolute_url()
    if correct_url not in request.build_absolute_uri():
        return HttpResponsePermanentRedirect(add_lang_qs(correct_url, request))
    else:
        lineas = None
        pois = None
        ps = None
        if aa.geometry_simple is not None:
            # lineas, pois, ps, aaancestors, children, recorridos = parallelize(
            lineas, pois, ps, aaancestors, children, recorridos = (
                Linea
                .objects
                .filter(recorridos__ruta__intersects=aa.geometry_simple)
                .order_by('nombre')
                .annotate(dcount=Count('id'))
                .defer('envolvente') if aa.depth > 2 or aa.is_leaf() else None,
                Poi
                .objects
                .filter(latlng__intersects=aa.geometry_simple)
                .order_by('?')[:30] if aa.depth > 2 or aa.is_leaf() else None,
                Parada
                .objects
                .filter(latlng__intersects=aa.geometry_simple)
                .order_by('?')[:30] if aa.depth > 2 or aa.is_leaf() else None,
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
                ).order_by('-recorridos_count', 'name') if osm_id != '60189' else aa.get_children().order_by('name'), # russia workaround
                Recorrido
                .objects
                .filter(ruta__intersects=aa.geometry_simple, linea__isnull=True)
                .order_by('nombre')
                .defer('ruta') if aa.depth > 2 or aa.is_leaf() else None
            )

        context = {
            'request': request,
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

        # jinja: parallelize=300, no parallel=480, streaming=30/600

        return render(request, 'catastro/ver_administrativearea.html', context)

        # return HttpResponse(get_template('ver_administrativearea.html').template.render(context))

        # os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        # template = get_template('ver_administrativearea.html').template
        # generator = template.generate(context)
        # response = StreamingHttpResponse(generator)
        # return response
