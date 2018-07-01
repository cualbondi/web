# -*- coding: UTF-8 -*-
from django.shortcuts import (get_object_or_404, render)
from django.http import HttpResponse

from apps.catastro.models import Poi, Ciudad
from apps.core.models import Recorrido, Parada

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


@csrf_exempt
@require_GET
def poi(request, slug=None):
    poi = get_object_or_404(Poi, slug=slug)
    # TODO: resolver estas queries en 4 threads
    #       ver https://stackoverflow.com/a/12542927/912450
    recorridos = Recorrido.objects.filter(ruta__dwithin=(poi.latlng, 0.00111)).select_related('linea').prefetch_related('linea__ciudad_set').order_by('linea__nombre', 'nombre')
    pois = Poi.objects.filter(latlng__dwithin=(poi.latlng, 0.111)).exclude(id=poi.id)
    ps = Parada.objects.filter(latlng__dwithin=(poi.latlng, 0.003))
    ciudad_actual = Ciudad.objects.filter(poligono__intersects=poi.latlng)
    return render(
        request,
        'catastro/ver_poi.html',
        {
            'ciudad_actual': ciudad_actual,
            'paradas': ps,
            'poi': poi,
            'recorridos': recorridos,
            'pois': pois
        }
    )

def zona(request, slug=None):
    return HttpResponse(status=504)
