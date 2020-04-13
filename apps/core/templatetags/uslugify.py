from django import template
from apps.utils.slugify import slugify

register = template.Library()


@register.filter
def uslugify(string):
    return slugify(string)
