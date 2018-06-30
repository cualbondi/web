# -*- coding: UTF-8 -*-
from django.shortcuts import (get_object_or_404, render_to_response,
                              redirect)
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.views.decorators.http import require_GET, require_http_methods
from django.core.exceptions import ObjectDoesNotExist

from apps.core.models import Linea, Recorrido, Tarifa, Parada
from apps.catastro.models import Ciudad, ImagenCiudad, Poi, Zona

from django.contrib.auth.models import User
from django.contrib.flatpages.models import FlatPage
from apps.editor.models import LogModeracion


from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


@csrf_exempt
@require_GET
def agradecimientos(request):
    # TODO: Refactor for better performance (too many database hits)
    us1 = User.objects.filter(is_staff=False)
    us2 = []
    for u in us1:
        # Obtener los logmoderacion de este usuario
        lms = LogModeracion.objects.filter(created_by=u)
        # Obtener todos los recorridosproposed que son de esos logmoderacion
        rps = [ x.recorridoProposed for x in lms ]
        # de esos solo tomar aquellos que alguna vez fueron aceptados (que tienen un logmoderacion aceptado)
        count = len([ 1 for x in rps if x.logmoderacion_set.filter(newStatus='S') ])
        # devolver el contador de eso
        u.count_ediciones_aceptadas = count
        # eliminar los usuarios que tienen count = 0
        if count > 0:
            us2.append(u)
    # ordenar us2 (in-place)
    us2.sort(key=lambda x: x.count_ediciones_aceptadas, reverse=True)

    try:
        flatpage_edicion = FlatPage.objects.get(url__contains='contribuir')
    except:
        flatpage_edicion = None

    return render_to_response(
        'core/agradecimientos.html',
        {
            'usuarios': us2,
            'flatpage_edicion': flatpage_edicion,
        },
        context_instance=RequestContext(request)
    )


def natural_sort_qs(qs, key):
    """ Hace un sort sobre un queryset sobre el campo key
        utilizando una tecnica para obtener un natural_sort
        ej de algo ordenado naturalmente:             ['xx1', 'xx20', 'xx100']
        lo mismo ordenado con sort comun (asciisort): ['xx1', 'xx100', 'xx20']
    """
    import re, operator
    def natural_key(string_):
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]
    op = operator.attrgetter(key)
    return sorted(qs, key=lambda a:natural_key(op(a)) )


@require_http_methods(["GET"])
def index(request):
    return render_to_response(
        'core/seleccionar_ciudad.html',
        {},
        context_instance=RequestContext(request)
    )


@csrf_exempt
@require_GET
def ver_ciudad(request, nombre_ciudad):
    slug_ciudad = slugify(nombre_ciudad)
    ciudad_actual = get_object_or_404(Ciudad, slug=slug_ciudad, activa=True)

    lineas = natural_sort_qs(ciudad_actual.lineas.all(), 'slug')
    tarifas = Tarifa.objects.filter(ciudad=ciudad_actual)

    imagenes = ImagenCiudad.objects.filter(ciudad=ciudad_actual)

    template = "core/ver_ciudad.html"
    if ( request.GET.get("dynamic_map") ):
        template = "core/ver_obj_map.html"

    return render_to_response(template,
                              {'obj': ciudad_actual,
                               'ciudad_actual': ciudad_actual,
                               'imagenes': imagenes,
                               'lineas': lineas,
                               'tarifas': tarifas},
                              context_instance=RequestContext(request))


@csrf_exempt
@require_GET
def ver_mapa_ciudad(request, nombre_ciudad):
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")
    slug_ciudad = slugify(nombre_ciudad)
    ciudad_actual = get_object_or_404(Ciudad, slug=slug_ciudad, activa=True)
    #        "default_lat":ciudad_actual.centro.coords[1],
    #        "default_lon":ciudad_actual.centro.coords[0],
#    pois = Poi.objects.filter(ciudad=ciudad_actual)
#    comercios = Comercio.objects.filter(ciudad=ciudad_actual)

    API_URL = settings.API_URL

    return render_to_response('core/buscador.html', {
                                    'es_vista_mapa': True,
                                    'ciudad_actual': ciudad_actual,
                                    'desde': desde,
                                    'hasta': hasta,
                                    'API_URL': API_URL,
                              },
                              context_instance=RequestContext(request))


@csrf_exempt
def redirect_sockjs_dev(request):
    return redirect('http://localhost:8083' + request.path + '?' + request.GET.urlencode())


@csrf_exempt
@require_GET
def ver_linea(request, nombre_ciudad, nombre_linea):
    slug_ciudad = slugify(nombre_ciudad)
    slug_linea = slugify(nombre_linea)

    ciudad_actual = get_object_or_404(Ciudad, slug=slug_ciudad, activa=True)
    """ TODO: Buscar solo lineas activas """
    linea_actual = get_object_or_404(Linea,
                                     slug=slug_linea,
                                     ciudad=ciudad_actual)
    recorridos = natural_sort_qs(Recorrido.objects.filter(linea=linea_actual), 'slug')

    template = "core/ver_linea.html"
    if ( request.GET.get("dynamic_map") ):
        template = "core/ver_obj_map.html"

    return render_to_response(template,
                              {'obj': linea_actual,
                               'ciudad_actual': ciudad_actual,
                               'linea_actual': linea_actual,
                               'recorridos': recorridos
                               },
                              context_instance=RequestContext(request))


@csrf_exempt
@require_GET
def ver_recorrido(request, nombre_ciudad, nombre_linea, nombre_recorrido):
    slug_ciudad = slugify(nombre_ciudad)
    slug_linea = slugify(nombre_linea)
    slug_recorrido = slugify(nombre_recorrido)

    ciudad_actual = get_object_or_404(Ciudad, slug=slug_ciudad, activa=True)
    """ TODO: Buscar solo lineas activas """
    linea_actual = get_object_or_404(Linea,
                                     slug=slug_linea,
                                     ciudad=ciudad_actual)
    """ TODO: Buscar solo recorridos activos """
    recorrido_actual = get_object_or_404(Recorrido,
                                         slug=slug_recorrido,
                                         linea=linea_actual)

    # Calles por las que pasa el recorrido
    """
    # solucion 1
    # toma todas las calles cercanas al recorrido
    # simple pero no funciona bien, genera "falsos positivos", trae calles perpendiculares al recorrido
    # igual es lento: 13 seg
    calles_fin = Calle.objects.filter(way__distance_lte=(recorrido_actual.ruta, D(m=20)))

    # alternativa con dwithin
    # igual es lento, pero 10 veces mejor que antes: 1.4 seg
    calles_fin = Calle.objects.filter(way__dwithin=(recorrido_actual.ruta, D(m=20)))
    """
    """
    # solucion 2
    # toma las calles que estan cercanas y se repiten cada par de puntos
    # hace 1 query lenta por cada punto: funciona bien, pero un poco lento!
    # 0.003 seg x cant_puntos
    calles_ant = None
    calles_fin = []
    for p in recorrido_actual.ruta.coords:
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
    if not recorrido_actual.descripcion or not recorrido_actual.descripcion.strip():
        def uniquify(seq, idfun=None):
            if idfun is None:
                def idfun(x): return x
            seen = {}
            result = []
            for item in seq:
                marker = idfun(item)
                if marker in seen: continue
                seen[marker] = 1
                result.append(item)
            return result

        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('''
                SELECT
                    (dp).path[1] as idp,
                    cc.nom       as nom
                FROM
                    (SELECT ST_DumpPoints(ST_Simplify(%s, 0.00005)) as dp ) as dpa
                    JOIN catastro_calle as cc
                    ON ST_DWithin(cc.way, (dp).geom, 20)
            ''',
            (
                recorrido_actual.ruta.ewkb,
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
    pois = Poi.objects.filter(latlng__dwithin=(recorrido_actual.ruta, D(m=400)))

    # Zonas por las que pasa el recorrido
    zonas = Zona.objects.filter(geo__intersects=recorrido_actual.ruta).values('name')

    # Horarios + paradas que tiene este recorrido
    horarios = recorrido_actual.horario_set.all().prefetch_related('parada')

    favorito = False
    if request.user.is_authenticated():
        favorito = recorrido_actual.es_favorito(request.user)

    template = "core/ver_recorrido.html"
    if ( request.GET.get("dynamic_map") ):
        template = "core/ver_obj_map.html"

    return render_to_response(
        template,
        {
            'obj': recorrido_actual,
            'ciudad_actual': ciudad_actual,
            'linea_actual': linea_actual,
            'recorrido_actual': recorrido_actual,
            'favorito': favorito,
            'calles': calles_fin,
            'pois': pois,
            'zonas': zonas,
            'horarios': horarios,
            'recorridos_similares': Recorrido.objects.similar_hausdorff(recorrido_actual)
        },
        context_instance=RequestContext(request)
    )


@csrf_exempt
@require_GET
def ver_parada(request, id=None):
    p = get_object_or_404(Parada, id=id)
    recorridosn = Recorrido.objects.filter(ruta__dwithin=(p.latlng, 0.00111)).select_related('linea').order_by('linea__nombre', 'nombre')
    recorridosp = [h.recorrido for h in p.horario_set.all().select_related('recorrido', 'recorrido__linea').order_by('recorrido__linea__nombre', 'recorrido__nombre')]
    #Recorrido.objects.filter(horarios_set__parada=p).select_related('linea').order_by('linea__nombre', 'nombre')
    pois = Poi.objects.filter(latlng__dwithin=(p.latlng, 300)) # este esta en metros en vez de degrees... no se por que, pero esta genial!
    ps = Parada.objects.filter(latlng__dwithin=(p.latlng, 0.004)).exclude(id=p.id)
    return render_to_response(
        "core/ver_parada.html",
        {
            'ciudad_actual': Ciudad.objects.filter(poligono__intersects=p.latlng),
            'parada': p,
            'paradas': ps,
            'recorridosn': recorridosn,
            'recorridosp': recorridosp,
            'pois': pois
        },
        context_instance=RequestContext(request)
    )


@csrf_exempt
@require_GET
def redirect_nuevas_urls(request, ciudad=None, linea=None, ramal=None, recorrido=None):
    """
    cualbondi.com.ar/la-plata/recorridos/Norte/10/IDA/ (ANTES)
    cualbondi.com.ar/la-plata/norte/10-desde-x-hasta-y (DESPUES)
    cualbondi.com.ar/cordoba/recorridos/T%20(Transversal)/Central/IDA/
    """
    url = '/'
    if not ciudad:
        ciudad = 'la-plata'
    url += slugify(ciudad) + '/'
    if linea:
        url += slugify(linea) + '/'
        if ramal and recorrido:
            try:
                recorrido = Recorrido.objects.get(linea__nombre=linea, nombre=ramal, sentido=recorrido)
                url += slugify(recorrido.nombre) + '-desde-' + slugify(recorrido.inicio) + '-hasta-' + slugify(recorrido.fin)
            except ObjectDoesNotExist:
                pass
    return redirect(url)
