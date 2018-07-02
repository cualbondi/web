from django.forms.forms import BoundField
from django.forms.widgets import CheckboxInput, RadioSelect
from django.template import Context
from django.template.loader import get_template
from django import template
from math import ceil

register = template.Library()


@register.filter
def as_bootstrap(form):
    template = get_template("bootstrap/form.html")
    c = Context({"form": form})
    return template.render(c)


@register.filter
def is_checkbox(value):
    if not isinstance(value, BoundField):
        return False
    return isinstance(value.field.widget, CheckboxInput)


@register.filter
def is_radio(value):
    if not isinstance(value, BoundField):
        return False
    return isinstance(value.field.widget, RadioSelect)


@register.filter
def dividir_columnas(lista, cantidad_columnas):
    try:
        cantidad_columnas = int(cantidad_columnas)
        lista = list(lista)
    except (ValueError, TypeError):
        return [lista]
    result = []
    tamano = len(lista) // (cantidad_columnas)
    if tamano * cantidad_columnas < len(lista):
        tamano = tamano + 1
    for i in range(cantidad_columnas):
        result.append(lista[i*tamano:(i+1)*tamano])
    return result


@register.filter
def partition_horizontal(thelist, n):
    """
    Break a list into ``n`` peices, but "horizontally." That is,
    ``partition_horizontal(range(10), 3)`` gives::

        [[1, 2, 3],
         [4, 5, 6],
         [7, 8, 9],
         [10]]

    Clear as mud?
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    newlists = [list() for i in range(int(ceil(len(thelist) / float(n))))]
    for i, val in enumerate(thelist):
        newlists[i//n].append(val)
    return newlists
