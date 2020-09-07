from django import template
from django.conf import settings

from apps.catastro.management.commands.update_osm import kings
from apps.utils.get_lang import get_lang_from_qs

register = template.Library()

@register.simple_tag(takes_context=True)
def get_lang_list(context, obj=None):
    language_default = 'ar'
    if obj:
        language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == obj.country_code), 'en')
    else:
        request = context['request']
        cc = request.path.split('/')[0]
        if len(cc) != 2:
            cc = 'ar'
        language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), 'en')
    langs = []
    for l in settings.LANGUAGES:
        langs.append(l[:] + (l[0][:2] == language_default[:2], ))
    return langs

@register.filter()
def add_lang_qs(url, request):
    qlang = get_lang_from_qs(request)
    if qlang:
        return url + '?lang=' + qlang
    return url

@register.filter()
def i18name(obj, request):
    qlang = get_lang_from_qs(request)
    if qlang:
        attr = 'name:' + qlang
        if hasattr(obj, 'tags') and attr in obj.tags and obj.tags[attr]:
            return obj.tags[attr]
    if hasattr(obj, 'name'):
        return obj.name
    if hasattr(obj, 'nom'):
        return obj.nom
    return ''
