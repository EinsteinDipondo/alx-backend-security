from django.db import models
from django.utils import timezone
from django.core.validators import validate_ipv46_address
from django.contrib.auth.models import User
from datetime import timedelta

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
    
    # Anomaly detection flag
    is_suspicious = models.BooleanField(default=False)
    anomaly_reason = models.CharField(max_length=200, blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['city']),
            models.Index(fields=['timestamp', 'country']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['is_suspicious']),
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


class SuspiciousIP(models.Model):
    """
    Model to store suspicious IP addresses detected by anomaly detection.
    """
    ip_address = models.GenericIPAddressField()
    reason = models.CharField(
        max_length=200,
        choices=[
            ('high_frequency', 'High request frequency (>100/hr)'),
            ('sensitive_paths', 'Accessing sensitive paths'),
            ('multiple_errors', 'Multiple error responses'),
            ('unusual_pattern', 'Unusual access pattern'),
            ('brute_force', 'Possible brute force attack'),
        ]
    )
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    request_count = models.IntegerField(default=0)
    first_detected = models.DateTimeField(auto_now_add=True)
    last_detected = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    auto_blocked = models.BooleanField(default=False)
    
    # Additional details
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Suspicious IP'
        verbose_name_plural = 'Suspicious IPs'
        ordering = ['-last_detected']
        unique_together = ['ip_address', 'reason']
        indexes = [
            models.Index(fields=['ip_address', 'is_active']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} - {self.get_reason_display()} - {self.severity}"
    
    def get_related_logs(self, hours=24):
        """Get related request logs for this IP"""
        from .models import RequestLog
        time_threshold = timezone.now() - timedelta(hours=hours)
        return RequestLog.objects.filter(
            ip_address=self.ip_address,
            timestamp__gte=time_threshold
        ).order_by('-timestamp')
    
    def mark_as_resolved(self):
        """Mark this suspicious activity as resolved"""
        self.is_active = False
        self.save()


class RateLimitLog(models.Model):
    """
    Model to track rate limiting events.
    """
    ip_address = models.GenericIPAddressField()
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    path = models.CharField(max_length=500)
    limit_type = models.CharField(max_length=50)  # 'anonymous', 'authenticated', 'login', etc.
    exceeded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Rate Limit Log'
        verbose_name_plural = 'Rate Limit Logs'
        ordering = ['-exceeded_at']
    
    def __str__(self):
        return f"{self.ip_address} - {self.limit_type} - {self.exceeded_at}"


class AnomalyDetectionConfig(models.Model):
    """
    Configuration for anomaly detection rules.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Rule parameters
    enabled = models.BooleanField(default=True)
    threshold = models.IntegerField(default=100, help_text="Requests per hour threshold")
    time_window_hours = models.IntegerField(default=1, help_text="Time window in hours")
    
    # Path patterns to monitor
    sensitive_paths = models.TextField(
        blank=True,
        help_text="Comma-separated list of sensitive paths (e.g., /admin, /login)"
    )
    
    # Detection criteria
    check_frequency = models.BooleanField(default=True, help_text="Check request frequency")
    check_sensitive_paths = models.BooleanField(default=True, help_text="Check access to sensitive paths")
    check_error_rate = models.BooleanField(default=False, help_text="Check error response rate")
    
    # Actions
    auto_block = models.BooleanField(default=False, help_text="Automatically block IP")
    severity_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Anomaly Detection Config'
        verbose_name_plural = 'Anomaly Detection Configs'
    
    def __str__(self):
        return f"{self.name} - {self.threshold} reqs/{self.time_window_hours}hr"
    
    def get_sensitive_paths_list(self):
        """Convert comma-separated paths to list"""
        if not self.sensitive_paths:
            return []
        return [path.strip() for path in self.sensitive_paths.split(',') if path.strip()]