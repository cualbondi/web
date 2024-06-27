from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware as DjangoAuthenticationMiddleware
import re


class AuthenticationMiddleware(DjangoAuthenticationMiddleware):
    def process_request(self, request):
        path = request.get_full_path()
        for pattern in settings.IGNORE_AUTH_URL_PATTERNS:
            print(pattern, path)
            if re.compile(pattern).match(path):
                return None
        return super().process_request(request)
