from django.db import models
from django.utils import timezone
from django.core.validators import validate_ipv46_address

class RequestLog(models.Model):
    """
    Enhanced model to store request information with geolocation data.
    """
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    path = models.CharField(max_length=500)
    
    # Geolocation fields
    country = models.CharField(max_length=100, blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True, 
        null=True
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True, 
        null=True
    )
    timezone = models.CharField(max_length=50, blank=True, null=True)
    isp = models.CharField(max_length=200, blank=True, null=True)
    
    # Geolocation metadata
    geolocation_updated = models.DateTimeField(blank=True, null=True)
    geolocation_source = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['city']),
            models.Index(fields=['timestamp', 'country']),
        ]
    
    def __str__(self):
        location = f"{self.city}, {self.country}" if self.city and self.country else "Unknown"
        return f"{self.ip_address} - {location} - {self.path}"
    
    def get_location_display(self):
        """Get formatted location string"""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.region and self.region != self.city:
            parts.append(self.region)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts) if parts else "Location unknown"


class BlockedIP(models.Model):
    """
    Model to store blocked IP addresses.
    """
    ip_address = models.GenericIPAddressField(
        unique=True,
        help_text="IP address to block"
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Reason for blocking this IP"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for the block"
    )
    
    class Meta:
        verbose_name = 'Blocked IP'
        verbose_name_plural = 'Blocked IPs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ip_address} - {self.reason or 'No reason provided'}"
    
    def is_expired(self):
        """Check if the block has expired"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False


class GeolocationCache(models.Model):
    """
    Cache for geolocation data to reduce API calls.
    """
    ip_address = models.GenericIPAddressField(unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    isp = models.CharField(max_length=200, blank=True, null=True)
    
    # Cache metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        verbose_name = 'Geolocation Cache'
        verbose_name_plural = 'Geolocation Cache'
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.city or 'Unknown'}"
    
    def is_expired(self):
        """Check if cache entry has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @classmethod
    def get_cached_location(cls, ip_address):
        """Get cached geolocation data for an IP"""
        try:
            cache_entry = cls.objects.get(ip_address=ip_address)
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
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def set_cached_location(cls, ip_address, data, ttl_hours=24):
        """Cache geolocation data for an IP"""
        from django.utils import timezone
        from datetime import timedelta
        
        expires_at = timezone.now() + timedelta(hours=ttl_hours)
        
        cls.objects.update_or_create(
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