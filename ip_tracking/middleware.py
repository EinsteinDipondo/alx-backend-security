from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import RequestLog

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log basic request information.
    """
    
    def process_response(self, request, response):
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Log the request
        RequestLog.objects.create(
            ip_address=ip,
            path=request.path,
            timestamp=timezone.now()
        )
        
        return response
