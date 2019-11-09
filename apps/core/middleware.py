"""Add user created_by and modified_by foreign key refs to any model automatically.
   Almost entirely taken from https://github.com/Atomidata/django-audit-log/blob/master/audit_log/middleware.py"""
from django.db.models import signals
# from django.utils.functional import curry
from django.db.models.fields import FieldDoesNotExist

from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware as DjangoAuthenticationMiddleware
import re


# class WhodidMiddleware(object):
#     def process_request(self, request):
#         if request.method not in ('HEAD', 'OPTIONS', 'TRACE'):
#             if hasattr(request, 'user') and request.user.is_authenticated:
#                 user = request.user
#             else:
#                 user = None

#             mark_whodid = curry(self.mark_whodid, user)
#             signals.pre_save.connect(mark_whodid, dispatch_uid=(self.__class__, request,), weak=False)

#     def process_response(self, request, response):
#         signals.pre_save.disconnect(dispatch_uid=(self.__class__, request,))
#         return response

#     def mark_whodid(self, user, sender, instance, **kwargs):
#         try:
#             instance._meta.get_field_by_name('created_by')
#             instance.created_by = user
#         except FieldDoesNotExist:
#             pass


class AuthenticationMiddleware(DjangoAuthenticationMiddleware):
    def process_request(self, request):
        path = request.get_full_path()
        for pattern in settings.IGNORE_AUTH_URL_PATTERNS:
            print(pattern, path)
            if re.compile(pattern).match(path):
                return None
        return super().process_request(request)
