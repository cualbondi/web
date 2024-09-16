from django.conf import settings
from django.contrib.sitemaps import GenericSitemap
from django.db.models.base import Model
from requests import get
from apps.core.models import Recorrido, Linea, Parada
from apps.catastro.models import Poi, AdministrativeArea
from apps.catastro.management.commands.update_osm import kings


def get_alternates(loc, sitemap_lang_code):
    alternates = []
    for (lang_code, lang_name) in settings.LANGUAGES:
        cc = loc.split('/')[3]
        if len(cc) != 2:
            cc = 'ar'
        language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), 'en')
        if lang_code[:2] != sitemap_lang_code:
            # only add as alternate if this url is not the sitemap_lang_code
            # (if this url is the sitemap_lang_code, then it goes directly in <loc></loc> (not alternate))
            if language_default[:2] == lang_code[:2]:
                alternates.append({'location': loc, 'lang_code': lang_code})
                # alternates.append({'location': loc, 'lang_code': 'x-default'})
            alternates.append({'location': loc + '?lang=' + lang_code, 'lang_code': lang_code})
        else:
            if language_default[:2] == lang_code[:2]:
                alternates.append({'location': loc, 'lang_code': lang_code})
                # alternates.append({'location': loc, 'lang_code': 'x-default'})
    return alternates


def get_loc(loc, sitemap_lang_code):
    cc = loc.split('/')[3]
    if len(cc) != 2:
        cc = 'ar'
    language_default = next((v['lang'] for k,v in kings.items() if v['country_code'] == cc), 'en')
    if language_default[:2] == sitemap_lang_code[:2]:
        return loc
    return loc + '?lang=' + sitemap_lang_code

def get_item_lang(item):
    return next((v['lang'] for k,v in kings.items() if v['country_code'] == item.country_code), 'en')

class CBSitemap(GenericSitemap):

    priority = None
    changefreq = None
    limit = 10000

    def __get(self, name, obj, default=None):
        try:
            attr = getattr(self, name)
        except AttributeError:
            return default
        if callable(attr):
            return attr(obj)
        return attr

    def _urls(self, page, protocol, domain):
        urls = []
        latest_lastmod = None
        all_items_lastmod = True  # track if all items have a lastmod

        paginator_page = self.paginator.page(page)
        for item in paginator_page.object_list:
            loc = self.__get('location', item)
            priority = self.__get('priority', item)
            lastmod = self.__get('lastmod', item)
        
            if all_items_lastmod:
                all_items_lastmod = lastmod is not None
                if (all_items_lastmod and
                        (latest_lastmod is None or lastmod > latest_lastmod)):
                    latest_lastmod = lastmod
            url_info = {
                'item': item,
                'location': get_loc(loc, get_item_lang(item)),
                'lastmod': lastmod,
                'changefreq': self.__get('changefreq', item),
                'priority': str(priority if priority is not None else ''),
                'alternates': get_alternates(loc, get_item_lang(item)),
            }
            if domain in loc:
                urls.append(url_info)
        if all_items_lastmod and latest_lastmod:
            self.latest_lastmod = latest_lastmod
        return urls

sitemaps = {
    'lineas': CBSitemap({
        'queryset': Linea.objects.order_by('id').defer('envolvente'),
    }, priority=0.6),
    'recorridos': CBSitemap({
        'queryset': Recorrido.objects.order_by('id').defer('ruta', 'ruta_simple'),
    }, priority=0.6),
    'paradas': CBSitemap({
        'queryset': Parada.objects.order_by('id').defer('latlng'),
    }, priority=0.4),
    'pois': CBSitemap({
        'queryset': Poi.objects.order_by('id').defer('latlng'),
    }, priority=0.6),
    'administrativeareas': CBSitemap({
        'queryset': AdministrativeArea.objects.order_by('id').defer('geometry', 'geometry_simple'),
    }, priority=0.6),
}
