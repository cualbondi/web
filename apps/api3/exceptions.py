import traceback
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import set_rollback


def default_exception_renderer(exc, is_api_exception):
    if is_api_exception:
        if isinstance(exc.detail, (list, dict)):
            return {'status': exc.status_code, 'message': 'Validation error', 'payload': exc.detail}
        else:
            return {'status': exc.status_code, 'message': exc.detail}
    return {'status': 500, 'message': str(exc)}


# copied and modified from https://github.com/encode/django-rest-framework/blob/master/rest_framework/views.py
def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.
    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.
    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        data = default_exception_renderer(exc, True)

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    traceback.print_exc()

    if 'text/html' in context['request'].headers.get('Accept', ''):
        return None
    else:
        data = default_exception_renderer(exc, False)
        return Response(data, status=500)
