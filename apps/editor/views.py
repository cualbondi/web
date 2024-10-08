import json

from django.contrib.auth.decorators import permission_required
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import (csrf_exempt, csrf_protect,
                                          ensure_csrf_cookie)
from django.views.decorators.http import require_GET, require_http_methods
from django.core.exceptions import ValidationError
from apps.core.models import Recorrido
from apps.editor.models import LogModeracion, RecorridoProposed


@ensure_csrf_cookie
@csrf_protect
@require_http_methods(["GET", "POST"])
def editor_recorrido(request, id_recorrido):
    if request.method == 'GET':
        recorrido = get_object_or_404(Recorrido, pk=id_recorrido)
        ediciones = RecorridoProposed.objects.select_related('linea').exclude(logmoderacion__created_by__isnull=True).order_by('-date_update')[:10]
        return render(
            request,
            'editor/editor_recorrido.html',
            {
                'recorrido': recorrido,
                'user': request.user,
                'ediciones' : ediciones
            }
        )
    elif request.method == 'POST':
        # save anyway! all info is useful
        recorrido = get_object_or_404(Recorrido, pk=id_recorrido)
        user = request.user if request.user.is_authenticated else None
        if (request.POST.get("uuid", False)):
            r = get_object_or_404(RecorridoProposed, uuid=request.POST.get("uuid"))
        else:
            r = RecorridoProposed()
        r.recorrido       = recorrido
        r.nombre          = recorrido.nombre
        r.linea           = recorrido.linea
        r.sentido         = recorrido.sentido
        r.inicio          = recorrido.inicio
        r.fin             = recorrido.fin
        r.semirrapido     = recorrido.semirrapido
        r.color_polilinea = recorrido.color_polilinea
        r.pois            = recorrido.pois
        r.descripcion     = recorrido.descripcion
        r.ruta            = GEOSGeometry(request.POST.get("geojson"))
        r.parent          = recorrido.uuid
        r.osm_id          = recorrido.osm_id
        r.osm_version     = None  # set to none because this is not created from osm
        # save anyway, but respond as forbidden if not auth ;)
        r.save(user=user)

        ciudad = None
        if len(r.ciudades) > 0:
            ciudad = r.ciudades[0].nombre

        data = {
            "id"    : r.id,
            "uuid"  : str(r.uuid),
            "nombre": r.nombre,
            "linea" : r.linea.nombre,
            "ciudad": ciudad
        }
        if request.user.is_authenticated:
            return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            return HttpResponse(json.dumps(data), content_type="application/json", status=403)
    else:
        return HttpResponse(status=405)


@permission_required('editor.moderate_recorridos', login_url="/usuarios/login/", raise_exception=True)
@require_GET
def mostrar_ediciones(request):
    estado = request.GET.get('estado', None)
    ediciones = RecorridoProposed.objects.all()
    if estado != 'all':
        ediciones = ediciones.filter(current_status='E')
    ediciones = ediciones.order_by('-date_create')
    ediciones = ediciones.select_related('linea')
    ediciones = ediciones.defer('ruta', 'linea__envolvente')
    ediciones = ediciones.prefetch_related(Prefetch('logmoderacion_set', LogModeracion.objects.order_by('-date_create')))
    ediciones = ediciones[:500]
    return render(
        request,
        'editor/moderacion_listado.html',
        {
            'ediciones': ediciones
        }
    )

@permission_required('editor.moderate_recorridos', login_url="/usuarios/login/", raise_exception=True)
@require_GET
def moderar_ediciones_id(request, id=None):
    ediciones = RecorridoProposed.objects.filter(recorrido__id=id).order_by('-date_create')[:50]
    original = Recorrido.objects.get(id=id)
    #original = RecorridoProposed.objects.get(uuid=ediciones[0].parent)
    return render(
        request,
        'editor/moderacion_id.html',
        {
            'ediciones': ediciones,
            'original': original
        }
    )


@permission_required('editor.moderate_recorridos', login_url="/usuarios/login/", raise_exception=True)
@require_GET
def moderar_ediciones_uuid(request, uuid=None):
    ediciones = RecorridoProposed.objects.filter(uuid=uuid).order_by('-date_create')[:50]
    original = RecorridoProposed.objects.filter(uuid=ediciones[0].parent)
    if original:
        original = original[0]
    else:
        original = Recorrido.objects.get(id=ediciones[0].recorrido.id)
    return render(
        request,
        'editor/moderacion_id.html',
        {
            'ediciones': ediciones,
            'original': original
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def revision(request, id_revision=None):
    try:
        revision = RecorridoProposed.objects.get(uuid=id_revision)
        original = RecorridoProposed.objects.get(uuid=revision.parent)
        diffa = revision.ruta.difference(original.ruta)
        diffb = original.ruta.difference(revision.ruta)
        intersection = original.ruta.intersection(revision.ruta)
        return render(
            request,
            'editor/revision.html',
            {
                'revision': revision,
                'original': original,
                'diffa': diffa,
                'diffb': diffb,
                'intersection': intersection
            }
        )
    except (ValidationError, RecorridoProposed.DoesNotExist) as e:
        raise Http404


@permission_required('editor.moderate_recorridos', login_url="/usuarios/login/", raise_exception=True)
def moderar_ediciones_uuid_rechazar(request, uuid=None):
    RecorridoProposed.objects.get(uuid=uuid).logmoderacion_set.create(created_by=request.user,newStatus='N')
    return HttpResponseRedirect(request.GET.get("next"))


@permission_required('editor.moderate_recorridos', login_url="/usuarios/login/", raise_exception=True)
def moderar_ediciones_uuid_aprobar(request, uuid=None):
    proposed = RecorridoProposed.objects.get(uuid=uuid)
    proposed.aprobar(request.user)
    # crear_thumbs.spool(recorrido_id=str(proposed.recorrido.id))
    return HttpResponseRedirect(request.GET.get("next"))
