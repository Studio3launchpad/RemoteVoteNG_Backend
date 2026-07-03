import threading
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()

def get_current_user():
    """
    Returns the user performing the current request, stored in thread-local storage.
    """
    return getattr(_thread_locals, 'user', None)

def get_current_ip():
    """
    Returns the client IP address of the current request.
    """
    return getattr(_thread_locals, 'ip', None)


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to capture the current authenticated user and request IP address,
    storing them in thread-local storage for use by database signals.
    """
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            _thread_locals.user = request.user
        else:
            _thread_locals.user = None
            
        # Extract IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        _thread_locals.ip = ip

    def process_response(self, request, response):
        # Clean up thread-local variables to prevent leakages
        _thread_locals.user = None
        _thread_locals.ip = None
        return response
