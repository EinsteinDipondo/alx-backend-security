from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.core.cache import cache
from .models import RequestLog, BlockedIP, GeolocationCache
import requests
import time
from datetime import timedelta

class BasicIPLoggingMiddleware(MiddlewareMixin):
    """
    Enhanced middleware with geolocation capabilities.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Cache for blocked IPs
        self.blocked_ips_cache = None
        self.cache_timeout = 60
        self.last_cache_update = 0
        
        # Geolocation settings
        self.geolocation_enabled = True
        self.geolocation_cache_ttl = 24 * 60 * 60  # 24 hours in seconds
        self.geolocation_services = [
            self._get_ipapi_location,
            self._get_ipinfo_location,
        ]
    
    def get_client_ip(self, request):
        """
        Extract client IP address from request headers.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip or '0.0.0.0'
    
    def get_blocked_ips(self):
        """
        Get blocked IPs from cache or database.
        """
        current_time = time.time()
        
        if (self.blocked_ips_cache is not None and 
            current_time - self.last_cache_update < self.cache_timeout):
            return self.blocked_ips_cache
        
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
    
    def get_geolocation_data(self, ip_address):
        """
        Get geolocation data for an IP address with caching.
        """
        # Skip geolocation for private/local IPs
        if self._is_private_ip(ip_address):
            return {
                'country': 'Local',
                'country_code': 'LOCAL',
                'city': 'Local Network',
                'region': 'Local Network',
                'source': 'private_ip',
            }
        
        # Check in-memory cache first
        cache_key = f"geolocation:{ip_address}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            cached_data['source'] = 'memory_cache'
            return cached_data
        
        # Check database cache if GeolocationCache model exists
        db_cached = None
        try:
            # Try to use the GeolocationCache model if it exists
            db_cached = self._get_db_cached_location(ip_address)
        except Exception:
            # If model doesn't exist or has issues, skip database cache
            pass
        
        if db_cached:
            # Also store in memory cache
            cache.set(cache_key, db_cached, self.geolocation_cache_ttl)
            return db_cached
        
        # Get from external API (try multiple services)
        geolocation_data = None
        for service in self.geolocation_services:
            try:
                geolocation_data = service(ip_address)
                if geolocation_data:
                    geolocation_data['source'] = service.__name__
                    break
            except Exception as e:
                continue
        
        if not geolocation_data:
            geolocation_data = {
                'country': 'Unknown',
                'country_code': '??',
                'city': 'Unknown',
                'region': 'Unknown',
                'source': 'failed',
            }
        
        # Cache the results
        if geolocation_data.get('source') not in ['private_ip', 'failed']:
            try:
                # Try to cache in database
                self._set_db_cached_location(ip_address, geolocation_data)
            except Exception:
                # If database caching fails, just use memory cache
                pass
            
            # Cache in memory
            cache.set(cache_key, geolocation_data, self.geolocation_cache_ttl)
        
        return geolocation_data
    
    def _get_db_cached_location(self, ip_address):
        """Get geolocation data from database cache"""
        try:
            cache_entry = GeolocationCache.objects.get(ip_address=ip_address)
            if not cache_entry.is_expired():
                return {
                    'country': cache_entry.country,
                    'country_code': cache_entry.country_code,
                    'city': cache_entry.city,
                    'region': cache_entry.region,
                    'latitude': float(cache_entry.latitude) if cache_entry.latitude else None,
                    'longitude': float(cache_entry.longitude) if cache_entry.longitude else None,
                    'timezone': cache_entry.timezone,
                    'isp': cache_entry.isp,
                    'source': 'cache',
                }
            else:
                # Delete expired cache entry
                cache_entry.delete()
                return None
        except GeolocationCache.DoesNotExist:
            return None
        except Exception:
            # If any error occurs (e.g., table doesn't exist), return None
            return None
    
    def _set_db_cached_location(self, ip_address, data, ttl_hours=24):
        """Cache geolocation data in database"""
        from datetime import timedelta
        
        expires_at = timezone.now() + timedelta(hours=ttl_hours)
        
        GeolocationCache.objects.update_or_create(
            ip_address=ip_address,
            defaults={
                'country': data.get('country'),
                'country_code': data.get('country_code'),
                'city': data.get('city'),
                'region': data.get('region'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timezone': data.get('timezone'),
                'isp': data.get('isp'),
                'expires_at': expires_at,
            }
        )
    
    def _is_private_ip(self, ip_address):
        """
        Check if IP is private/local.
        """
        private_ranges = [
            ('10.0.0.0', '10.255.255.255'),
            ('172.16.0.0', '172.31.255.255'),
            ('192.168.0.0', '192.168.255.255'),
            ('127.0.0.0', '127.255.255.255'),
            ('169.254.0.0', '169.254.255.255'),  # Link-local
        ]
        
        # Convert IP to integer for comparison
        try:
            ip_int = self._ip_to_int(ip_address)
        except (ValueError, AttributeError):
            return False
        
        for start_str, end_str in private_ranges:
            try:
                start_int = self._ip_to_int(start_str)
                end_int = self._ip_to_int(end_str)
                if start_int <= ip_int <= end_int:
                    return True
            except (ValueError, AttributeError):
                continue
        
        return False
    
    def _ip_to_int(self, ip):
        """
        Convert IP string to integer.
        """
        octets = ip.split('.')
        return (int(octets[0]) << 24) + (int(octets[1]) << 16) + \
               (int(octets[2]) << 8) + int(octets[3])
    
    def _get_ipapi_location(self, ip_address):
        """
        Get location data from ipapi.co (free tier: 1000 requests/month).
        """
        try:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/',
                timeout=3,
                headers={'User-Agent': 'Django IP Tracking Middleware'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('country_name'),
                    'country_code': data.get('country_code'),
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'latitude': float(data.get('latitude')) if data.get('latitude') else None,
                    'longitude': float(data.get('longitude')) if data.get('longitude') else None,
                    'timezone': data.get('timezone'),
                    'isp': data.get('org'),
                }
        except Exception:
            pass
        
        return None
    
    def _get_ipinfo_location(self, ip_address):
        """
        Get location data from ipinfo.io (free tier: 50,000 requests/month).
        """
        try:
            response = requests.get(
                f'https://ipinfo.io/{ip_address}/json',
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse location coordinates if available
                latitude = longitude = None
                loc = data.get('loc', '')
                if loc and ',' in loc:
                    try:
                        lat_lon = loc.split(',')
                        latitude = float(lat_lon[0].strip())
                        longitude = float(lat_lon[1].strip())
                    except (ValueError, IndexError):
                        pass
                
                return {
                    'country': data.get('country'),
                    'country_code': data.get('country'),
                    'city': data.get('city'),
                    'region': data.get('region'),
                    'latitude': latitude,
                    'longitude': longitude,
                    'timezone': data.get('timezone'),
                    'isp': data.get('org'),
                }
        except Exception:
            pass
        
        return None
    
    def process_request(self, request):
        """
        Check if the client IP is blocked before processing the request.
        """
        client_ip = self.get_client_ip(request)
        
        if self.is_ip_blocked(client_ip):
            # Log the blocked attempt (without geolocation)
            try:
                RequestLog.objects.create(
                    ip_address=client_ip,
                    path=request.path,
                    timestamp=timezone.now(),
                    country='Blocked',
                    city='N/A',
                )
            except Exception:
                # If logging fails, still block the request
                pass
            
            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>Your IP address ({}) has been blocked from accessing this site.</p>"
                .format(client_ip)
            )
        
        return None
    
    def process_response(self, request, response):
        """
        Log request information with geolocation data.
        """
        client_ip = self.get_client_ip(request)
        
        # Skip if IP is blocked (already logged in process_request)
        if self.is_ip_blocked(client_ip):
            return response
        
        # Get geolocation data
        geolocation_data = {}
        if self.geolocation_enabled:
            try:
                geolocation_data = self.get_geolocation_data(client_ip)
            except Exception:
                geolocation_data = {}
        
        # Create log entry
        try:
            RequestLog.objects.create(
                ip_address=client_ip,
                path=request.path,
                timestamp=timezone.now(),
                country=geolocation_data.get('country'),
                country_code=geolocation_data.get('country_code'),
                city=geolocation_data.get('city'),
                region=geolocation_data.get('region'),
                latitude=geolocation_data.get('latitude'),
                longitude=geolocation_data.get('longitude'),
                timezone=geolocation_data.get('timezone'),
                isp=geolocation_data.get('isp'),
                geolocation_updated=timezone.now() if geolocation_data.get('source') not in ['private_ip', 'failed'] else None,
                geolocation_source=geolocation_data.get('source'),
            )
        except Exception as e:
            # Fallback: log without geolocation
            try:
                RequestLog.objects.create(
                    ip_address=client_ip,
                    path=request.path,
                    timestamp=timezone.now(),
                )
            except Exception:
                # If even basic logging fails, just continue
                pass
        
        return response