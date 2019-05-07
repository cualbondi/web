from django.contrib.auth import logout
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User

from apps.editor.models import LogModeracion, RecorridoProposed
from apps.core.models import Linea


def cerrar_sesion(request):
    logout(request)
    return redirect("/")


def ver_perfil(request, username):
    usuario = get_object_or_404(User, username=username)
    # perfil = PerfilUsuario.objects.get(usuario=usuario)
    ediciones = RecorridoProposed.objects.order_by('-date_update').defer('ruta')
    ediciones = ediciones.prefetch_related(Prefetch('linea', Linea.objects.defer('envolvente')))
    ediciones = ediciones.prefetch_related(Prefetch('logmoderacion_set', LogModeracion.objects.order_by('-date_create')))
    ediciones = ediciones.filter(logmoderacion__created_by=usuario)
    return render(
        request,
        'usuarios/perfil.html',
        {
            'usuario': usuario,
            'ediciones': ediciones,
        }
    )
