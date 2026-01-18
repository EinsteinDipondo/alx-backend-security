import time
from django.utils.deprecation import MiddlewareMixin
from ipware import get_client_ip
from .models import RequestLog

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log basic request information:
    - IP address
    - Timestamp
    - Request path
    
    This middleware logs every incoming request to the RequestLog model.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def process_request(self, request):
        """
        Store the start time for calculating response time
        """
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Log request information after the response is processed
        """
        # Get client IP address using ipware
        client_ip, is_routable = get_client_ip(request)
        
        # If no IP found, use a default value
        if client_ip is None:
            client_ip = '0.0.0.0'
        
        # Log the request to database
        try:
            RequestLog.objects.create(
                ip_address=client_ip,
                path=request.path,
                timestamp=timezone.now()
            )
        except Exception as e:
            # Log error but don't break the request
            # In production, you might want to use proper logging
            pass
        
        return response