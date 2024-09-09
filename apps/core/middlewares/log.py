from django.utils.deprecation import MiddlewareMixin


class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.get_full_path()
        user_agent = request.META.get("HTTP_USER_AGENT")
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        print(ip, user_agent, path)
