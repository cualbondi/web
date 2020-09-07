from django.conf import settings

def get_lang_from_qs(request):
    qlang = request.GET.get('lang', None)
    if qlang:
        lang = next((lang[0] for lang in settings.LANGUAGES if lang[0] == qlang), None)
        if lang:
            return lang
    return None

def transform_name_lang(objects, lang_code):
    if not objects or not lang_code:
        return objects

    attr = 'name' + ':' + lang_code
    try:
        for obj in objects:
            if hasattr(obj, 'tags') and attr in obj.tags and obj.tags[attr]:
                obj.name = obj.tags[attr]
        return objects
    except TypeError:
        obj = objects
        if hasattr(obj, 'tags') and attr in obj.tags and obj.tags[attr]:
            obj.name = obj.tags[attr]
        return obj
