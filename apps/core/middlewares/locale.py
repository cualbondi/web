from django.conf import settings
from django.conf.urls.i18n import is_language_prefix_patterns_used, get_resolver
from django.http import HttpResponseRedirect
from django.urls import get_script_prefix, is_valid_path
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from apps.catastro.management.commands.update_osm import kings
from re import compile as re_compile

language_code_prefix_re = re_compile(r'^/([a-z][a-z])/')


class LocaleMiddleware(MiddlewareMixin):
    """
    Parse a request and decide what translation object to install in the
    current thread context. This allows pages to be dynamically translated to
    the language the user desires (if the language is available, of course).
    """

    def process_request(self, request):
        country_code = 'ar'
        regex_match = language_code_prefix_re.match(request.path_info)
        if regex_match:
            print(regex_match)
            country_code = regex_match.group(1)
        language = next((v['lang'] for k,v in kings.items() if v['country_code'] == country_code), 'es')
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        language = translation.get_language()
        response.setdefault('Content-Language', language)
        return response
