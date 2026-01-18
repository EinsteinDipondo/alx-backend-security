from django.db import models
from django.utils import timezone
from django.core.validators import validate_ipv46_address

class RequestLog(models.Model):
    """
    Model to store basic request information including IP address,
    timestamp, and path.
    """
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    path = models.CharField(max_length=500)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
    
    def __str__(self):
        return f"{self.ip_address} - {self.path} - {self.timestamp}"


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
    
    def save(self, *args, **kwargs):
        """Override save to handle expiration"""
        from django.utils import timezone
        if self.expires_at and timezone.now() > self.expires_at:
            # Don't save if already expired
            return
        super().save(*args, **kwargs)