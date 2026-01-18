from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import RequestLog, BlockedIP
import time

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log basic request information.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Cache for blocked IPs to avoid hitting DB on every request
        self.blocked_ips_cache = None
        self.cache_timeout = 60  # Cache for 60 seconds
        self.last_cache_update = 0
    
    def get_client_ip(self, request):
        """
        Extract client IP address from request headers.
        Handles proxy headers (X-Forwarded-For) if present.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, the first one is the client
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip or '0.0.0.0'
    
    def get_blocked_ips(self):
        """
        Get blocked IPs from cache or database.
        Updates cache periodically to avoid hitting DB on every request.
        """
        current_time = time.time()
        
        # Return cached data if it's fresh
        if (self.blocked_ips_cache is not None and 
            current_time - self.last_cache_update < self.cache_timeout):
            return self.blocked_ips_cache
        
        # Update cache from database
        self.blocked_ips_cache = set(
            BlockedIP.objects.filter(
                expires_at__isnull=True
            ).values_list('ip_address', flat=True)
        )
        
        # Also include non-expired temporary blocks
        from django.db.models import Q
        active_blocks = BlockedIP.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).values_list('ip_address', flat=True)
        
        self.blocked_ips_cache = set(active_blocks)
        self.last_cache_update = current_time
        
        return self.blocked_ips_cache
    
    def is_ip_blocked(self, ip_address):
        """
        Check if an IP address is blocked.
        """
        blocked_ips = self.get_blocked_ips()
        return ip_address in blocked_ips
    
    def process_request(self, request):
        """
        Check if the client IP is blocked before processing the request.
        """
        client_ip = self.get_client_ip(request)
        
        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            # Log the blocked attempt
            RequestLog.objects.create(
                ip_address=client_ip,
                path=request.path,
                timestamp=timezone.now()
            )
            
            # Return 403 Forbidden response
            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>Your IP address ({}) has been blocked from accessing this site.</p>"
                "<p>If you believe this is an error, please contact the administrator.</p>"
                .format(client_ip)
            )
        
        return None
    
    def process_response(self, request, response):
        """
        Log request information to database (only for non-blocked requests).
        """
        # Skip logging if request was blocked (already logged in process_request)
        if hasattr(request, '_ip_blocked') and request._ip_blocked:
            return response
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Only log if IP is not blocked
        if not self.is_ip_blocked(client_ip):
            # Create log entry
            try:
                RequestLog.objects.create(
                    ip_address=client_ip,
                    path=request.path,
                    timestamp=timezone.now()
                )
            except Exception:
                # Silent failure - don't break the user's request
                pass
        
        return response