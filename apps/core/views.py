# -*- coding: UTF-8 -*-
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponsePermanentRedirect, Http404
from django.db.models import Prefetch, Count, F
from django.contrib.gis.measure import D, A
from django.contrib.gis.db.models.functions import SymDifference, Area, Intersection
from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from django.contrib.postgres.search import TrigramSimilarity

from apps.core.models import Linea, Recorrido, Parada
from apps.catastro.management.commands.update_osm import kings
from apps.catastro.models import Ciudad, Poi, AdministrativeArea
from apps.utils import data
from apps.utils.parallel_query import parallelize
from apps.utils.slugify import slugify
from apps.core.templatetags.lang_list import add_lang_qs


@csrf_exempt
@require_GET
def agradecimientos(request):
    us = User.objects.filter(is_staff=False)
    us = us.filter(logmoderacion__recorridoProposed__logmoderacion__newStatus='S')
    us = us.annotate(count_ediciones_aceptadas=Count('logmoderacion__recorridoProposed', distinct=True))
    us = us.order_by('-count_ediciones_aceptadas')

    try:
        flatpage_edicion = FlatPage.objects.get(url__contains='contribuir')
    except Exception:
        flatpage_edicion = None

    return render(
        request,
        'core/agradecimientos.html',
        {
            'usuarios': us,
            'flatpage_edicion': flatpage_edicion,
        }
    )


def natural_sort_qs(qs, key):
    """ Hace un sort sobre un queryset sobre el campo key
        utilizando una tecnica para obtener un natural_sort
        ej de algo ordenado naturalmente:             ['xx1', 'xx20', 'xx100']
        lo mismo ordenado con sort comun (asciisort): ['xx1', 'xx100', 'xx20']
    """
    import re
    import operator

    def natural_key(string_):
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]
    op = operator.attrgetter(key)
    return sorted(qs, key=lambda a: natural_key(op(a)))


@require_http_methods(["GET"])
def index(request):
    return render(
        request,
        'core/seleccionar_ciudad.html'
    )


@csrf_exempt
@require_GET
def ver_mapa_ciudad(request, administrativearea_slug):
    return redirect('https://localhost:8083' + request.path + '?' + request.GET.urlencode())


@csrf_exempt
def redirect_sockjs_dev(request):
    return redirect('http://localhost:8083' + request.path + '?' + request.GET.urlencode())


@csrf_exempt
@require_GET
def ver_linea(request, osm_type=None, osm_id=None, slug=None, country_code=None):
    """
        osm_type =
            - 'c': cualbondi recorrido, usar id de la tabla directamente
            - 'r': relation de osm, usar osm_id con el campo osm_id
    """
    # TODO: redirect id c123 a r123 si viene con osm_type=c y existe el osm_id
    linea_q = Linea.objects.only('nombre', 'slug', 'img_cuadrada', 'info_empresa', 'info_terminal', 'img_panorama', 'envolvente')
    linea = None
    if osm_type == 'c':
        linea = get_object_or_404(linea_q, id=osm_id)
    elif osm_type == 'r':
        linea = get_object_or_404(linea_q, osm_id=osm_id)

    linea__envolvente = linea.envolvente.simplify(0.001, True)

    recorridos = natural_sort_qs(linea.recorridos.all().defer('ruta'), 'slug')

    # aa = AdministrativeArea.objects \
    #     .filter(geometry_simple__intersects=linea.envolvente) \
    #     .annotate(inter_area=DBArea(Intersection(F('geometry_simple'), linea.envolvente))) \
    #     .filter(inter_area__gt=Area(sq_m=linea.envolvente.area * 0.8)) \
    #     .annotate(area=DBArea(F('geometry_simple'))) \
    #     .order_by('area')

    # aa = AdministrativeArea.objects \
    #     .filter(geometry_simple__intersects=linea.envolvente) \
    #     .annotate(symdiff_area=Area(SymDifference(F('geometry_simple'), linea.envolvente)) / Area(Union(F('geometry_simple'), linea.envolvente))) \
    #     .order_by('symdiff_area')

    aa = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=linea__envolvente) \
        .annotate(symdiff_area=Area(SymDifference(F('geometry_simple'), linea__envolvente)) / (Area(F('geometry_simple')) + Area(linea__envolvente))) \
        .annotate(intersection_area=Area(Intersection(F('geometry_simple'), linea__envolvente)) / Area(linea__envolvente)) \
        .filter(intersection_area__gt=0.8) \
        .order_by('symdiff_area')

    # for a in aa:
    #     print(f'{a.symdiff_area, a.intersection_area, a.name}')

    # aa = AdministrativeArea.objects \
    #     .filter(geometry_simple__intersects=linea.envolvente) \
    #     .annotate(symdiff_area=Area(SymDifference(F('geometry_simple'), linea.envolvente))) \
    #     .order_by('symdiff_area')

    if aa:
        aa = aa[0]
        aaancestors = aa.get_ancestors().reverse()
    else:
        aa = None
        aaancestors = None

    # linea found, check if url is ok
    correct_url = linea.get_absolute_url()
    if correct_url not in request.build_absolute_uri():
        return HttpResponsePermanentRedirect(add_lang_qs(correct_url, request))

    # Zonas por las que pasa el recorrido
    aas = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=linea__envolvente, depth__gt=3) \
        .order_by('depth', 'name')

    return render(
        request,
        "core/ver_linea.html",
        {
            'obj': linea,
            'recorridos': recorridos,
            'adminarea': aa,
            'adminareaancestors': aaancestors,
            'adminareas': aas,
        }
    )


@csrf_exempt
@require_GET
def ver_recorrido(request, osm_type=None, osm_id=None, slug=None, country_code=None):
    """
        osm_type =
            - 'c': cualbondi recorrido, usar id de la tabla directamente
            - 'r': relation de osm, usar osm_id con el campo osm_id
    """
    recorrido_q = Recorrido.objects \
        .only('nombre', 'slug', 'inicio', 'fin', 'img_cuadrada', 'img_panorama', 'ruta', 'linea', 'osm_id') \
        .select_related('linea')
    recorrido = None
    if osm_type == 'c':
        recorrido = get_object_or_404(recorrido_q, id=osm_id)
    elif osm_type == 'w':
        # there can be multiple with the same id, so we filter using the most approximate slug
        recorridos = Recorrido.objects.filter(osm_id=osm_id).annotate(similarity=TrigramSimilarity('slug', slug or '')).order_by('-similarity')
        if recorridos:
            recorrido = recorridos[0]
        else:
            raise Http404


    recorrido_simplified = recorrido.ruta.simplify(0.00005)
    recorrido_buffer = recorrido_simplified.buffer(0.0001)

    # aa = AdministrativeArea.objects \
    #     .filter(geometry_simple__intersects=recorrido_simplified) \
    #     .annotate(symdiff_area=Area(SymDifference(F('geometry_simple'), recorrido_simplified)) / (Area(F('geometry_simple')) + Area(recorrido_simplified))) \
    #     .order_by('symdiff_area')

    aa = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=recorrido_buffer) \
        .annotate(symdiff_area=Area(SymDifference(F('geometry_simple'), recorrido_buffer)) / (Area(F('geometry_simple')) + Area(recorrido_buffer))) \
        .annotate(intersection_area=Area(Intersection(F('geometry_simple'), recorrido_buffer)) / Area(recorrido_buffer)) \
        .filter(intersection_area__gt=0.8) \
        .order_by('symdiff_area')

    if aa:
        aa = aa[0]
        aaancestors = aa.get_ancestors().reverse()
    else:
        aa = None
        aaancestors = None

    # recorrido found, check if url is ok
    correct_url = recorrido.get_absolute_url()
    if correct_url not in request.build_absolute_uri():
        return HttpResponsePermanentRedirect(add_lang_qs(correct_url, request))

    # Calles por las que pasa el recorrido
    """
    # solucion 1
    # toma todas las calles cercanas al recorrido
    # simple pero no funciona bien, genera "falsos positivos", trae calles perpendiculares al recorrido
    # igual es lento: 13 seg
    calles_fin = Calle.objects.filter(way__distance_lte=(recorrido.ruta, D(m=20)))

    # alternativa con dwithin
    # igual es lento, pero 10 veces mejor que antes: 1.4 seg
    calles_fin = Calle.objects.filter(way__dwithin=(recorrido.ruta, D(m=20)))
    """
    """
    # solucion 2
    # toma las calles que estan cercanas y se repiten cada par de puntos
    # hace 1 query lenta por cada punto: funciona bien, pero un poco lento!
    # 0.003 seg x cant_puntos
    calles_ant = None
    calles_fin = []
    for p in recorrido.ruta.coords:
        calles = Calle.objects.filter(way__dwithin=(Point(p), D(m=50)))
        if calles_ant is not None:
            for c in calles_ant:
                if len(calles_fin) > 0:
                    if c.nom != calles_fin[-1].nom and c in calles:
                        calles_fin.append(c)
                else:
                    calles_fin.append(c)
        calles_ant = calles
    # TODO: tal vez se pueda mejorar eso con una custom query sola.
    """
    # solucion 3, como la solucion 2 pero con raw query (para bs as no anda bien)
    if not recorrido.descripcion or not recorrido.descripcion.strip():
        def uniquify(seq, idfun=None):
            if idfun is None:
                def idfun(x):
                    return x
            seen = {}
            result = []
            for item in seq:
                marker = idfun(item)
                if marker in seen:
                    continue
                seen[marker] = 1
                result.append(item)
            return result

        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(
            '''
                SELECT
                    cc.id        as id,
                    (dp).path[1] as idp,
                    cc.nom       as nom
                FROM
                    (SELECT ST_DumpPoints(%s) as dp ) as dpa
                    JOIN catastro_calle as cc
                    ON ST_DWithin(cc.way, (dp).geom, 20)
            ''',
            (
                recorrido_simplified.ewkb,
            )
        )
        from collections import OrderedDict
        calles = OrderedDict()
        for c in cursor.fetchall():
            if c[0] in calles:
                calles[c[0]].append(c[1])
            else:
                calles[c[0]] = [c[1]]

        calles_fin = []
        calles_ant = []
        for k in calles:
            calles_aca = []
            for c in calles_ant:
                if len(calles_fin) > 0:
                    if c not in calles_fin[-1] and c in calles[k]:
                        calles_aca.append(c)
                else:
                    calles_aca.append(c)
            if calles_aca:
                calles_fin.append(calles_aca)
            calles_ant = calles[k]

        calles_fin = [item for sublist in calles_fin for item in uniquify(sublist)]
    else:
        calles_fin = None

    # POI por los que pasa el recorrido
    pois = Poi.objects.filter(latlng__dwithin=(recorrido_simplified, D(m=400))).order_by('?')[:60]

    # Zonas por las que pasa el recorrido
    aas = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=recorrido_buffer, depth__gt=3) \
        .order_by('depth')

    # Horarios + paradas que tiene este recorrido
    horarios = recorrido.horario_set.all().prefetch_related('parada').order_by('?')[:60]

    recorridos_similares = Recorrido.objects.similar_hausdorff(recorrido_simplified)

    # aaancestors, calles_fin, pois, aas, horarios, recorridos_similares = parallelize(aaancestors, calles_fin, pois, aas, horarios, recorridos_similares)

    try:
        schemaorg_itemtype = {
            'bus': 'BusTrip',
            'trolleybus': 'BusTrip',
            'train': 'TrainTrip',
            'subway': 'TrainTrip',
            'monorail': 'TrainTrip',
            'tram': 'TrainTrip',
            'light_rail': 'TrainTrip',
        }[recorrido.type]
    except:
        schemaorg_itemtype = 'Trip'

    context = {
        'schemaorg_itemtype': schemaorg_itemtype,
        'obj': recorrido,
        'linea': recorrido.linea,
        'adminarea': aa,
        'adminareaancestors': aaancestors,
        'calles': calles_fin,
        'pois': pois,
        'adminareas': aas,
        'horarios': horarios,
        'recorridos_similares': recorridos_similares,
    }

    return render(request, "core/ver_recorrido.html", context)


@csrf_exempt
@require_GET
def ver_parada(request, id=None, country_code=None):
    p = get_object_or_404(Parada, id=id)

    aas = AdministrativeArea.objects \
        .filter(geometry_simple__intersects=p.latlng) \
        .order_by('depth')

    # p found, check if url is ok
    correct_url = p.get_absolute_url()
    if correct_url not in request.build_absolute_uri():
        return HttpResponsePermanentRedirect(add_lang_qs(correct_url, request))

    recorridosn = Recorrido.objects \
        .filter(ruta__dwithin=(p.latlng, 0.00111)) \
        .select_related('linea') \
        .prefetch_related(Prefetch('ciudades', queryset=Ciudad.objects.all().only('slug'))) \
        .order_by('linea__nombre', 'nombre') \
        .defer('linea__envolvente', 'ruta')
    recorridosp = [
        h.recorrido for h in
        p.horario_set
        .all()
        .select_related('recorrido', 'recorrido__linea')
        .prefetch_related(Prefetch('recorrido__ciudades', queryset=Ciudad.objects.all().only('slug')))
        .order_by('recorrido__linea__nombre', 'recorrido__nombre')
    ]
    # Recorrido.objects.filter(horarios_set__parada=p).select_related('linea').order_by('linea__nombre', 'nombre')
    pois = Poi.objects.filter(latlng__dwithin=(p.latlng, 300))  # este esta en metros en vez de degrees... no se por que, pero esta genial!
    ps = Parada.objects.filter(latlng__dwithin=(p.latlng, 0.004)).exclude(id=p.id)
    context = {
        'adminareas': aas,
        'parada': p,
        'paradas': ps,
        'recorridosn': recorridosn,
        'recorridosp': recorridosp,
        'pois': pois,
    }
    return render(request, "core/ver_parada.html", context)


@csrf_exempt
@require_GET
def redirect_nuevas_urls(request, slug_ciudad=None, slug_linea=None, slug_recorrido=None, country_code=None):
    """
    # v1
    cualbondi.com.ar/la-plata/recorridos/Norte/10/IDA/
    cualbondi.com.ar/cordoba/recorridos/T%20(Transversal)/Central/IDA/
    # v2
    cualbondi.com.ar/la-plata/norte/10-desde-x-hasta-y
    # v3
    cualbondi.com.ar/r/c123/asdasd
    """
    ciudades = data.ciudades + data.ciudades_es
    ciudad = next((c for c in ciudades if c.slug == slug_ciudad), False)
    if not ciudad:
        country = next((v for k,v in kings.items() if v['country_code'] == country_code), False)
        if country:
            return redirect(get_object_or_404(AdministrativeArea, osm_id=str(country['id'])), permanent=True)
        else:
            raise Http404

    # ciudad
    if not slug_linea:
        return redirect(get_object_or_404(AdministrativeArea, osm_type='r', osm_id=ciudad.osm_id), permanent=True)

    # linea
    lineas = Linea.objects.filter(slug=slug_linea, ciudades__slug=ciudad.slug)
    if len(lineas) == 0:
        raise Http404

    if not slug_recorrido:
        return redirect(lineas[0], permanent=True)

    # recorrido
    recorridos = Recorrido.objects.filter(slug=slug_recorrido, ciudades__slug=ciudad.slug, linea__slug=lineas[0].slug)
    if len(recorridos) == 0:
        raise Http404
    return redirect(recorridos[0], permanent=True)


def server_error(request):
    response = render(request, '500.html', status=500)
    return response
