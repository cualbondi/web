# -*- coding: UTF-8 -*-
from django.shortcuts import (get_object_or_404, render)
from django.http import HttpResponse

from apps.catastro.models import Poi, Ciudad, Interseccion
from apps.core.models import Recorrido, Parada

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.db.models import Prefetch
from django.contrib.gis.db.models.functions import Distance


@csrf_exempt
@require_GET
def poiORint(request, slug=None):
    poi = None
    pois = Poi.objects.filter(slug=slug)
    if pois:
        poi = pois[0]
    else:
        poi = get_object_or_404(Interseccion, slug=slug)
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

    return render(
        request,
        template,
        {
            'obj': poi,
            'ciudad_actual': ciudad_actual,
            'paradas': ps,
            'poi': poi,
            'recorridos': recorridos,
            'pois': pois
        }
    )


def zona(request, slug=None):
    return HttpResponse(status=504)
