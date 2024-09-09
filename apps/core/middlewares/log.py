from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied


class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.get_full_path()
        ua = request.META.get("HTTP_USER_AGENT")
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        blockuas = [
            'Bytespider',
            'DataForSeoBot',
            'ImagesiftBot',
            'petalsearch',
            'SemrushBot',
            'proximic',
            'FriendlyCrawler',
            'opensiteexplorer',
            'CriteoBot',
            'Qwantbot',
            'Amazonbot',
            # 'meta-externalagent', # facebook for AI
        ]
        for blockua in blockuas:
            if blockua in ua:
                print('[BLOCK]', ip, ua, path)
                raise PermissionDenied("Forbidden user agent")

        print('[-> OK]', ip, ua, path)
