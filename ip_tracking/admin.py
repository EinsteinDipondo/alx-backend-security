from django.contrib import admin
from django.utils import timezone
from .models import (
    RequestLog, BlockedIP, GeolocationCache, 
    SuspiciousIP, AnomalyDetectionConfig, RateLimitLog
)
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'location_display', 'path', 'timestamp', 'is_suspicious')
    list_filter = ('country', 'city', 'timestamp', 'is_suspicious')
    search_fields = ('ip_address', 'path', 'city', 'country')
    readonly_fields = ('ip_address', 'path', 'timestamp', 'get_location_display', 'anomaly_details')
    fieldsets = (
        ('Request Information', {
            'fields': ('ip_address', 'path', 'timestamp')
        }),
        ('Geolocation Information', {
            'fields': ('country', 'city', 'region', 'latitude', 'longitude', 'timezone', 'isp')
        }),
        ('Anomaly Detection', {
            'fields': ('is_suspicious', 'anomaly_reason', 'anomaly_details')
        }),
    )
    
    def location_display(self, obj):
        return obj.get_location_display()
    location_display.short_description = 'Location'
    
    def anomaly_details(self, obj):
        if obj.is_suspicious:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ {}</span>',
                obj.anomaly_reason or "Suspicious activity detected"
            )
        return "Normal"
    anomaly_details.short_description = 'Anomaly Status'


@admin.register(BlockedIP)
class BlockedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'created_at', 'expires_at', 'is_active')
    list_filter = ('created_at',)
    search_fields = ('ip_address', 'reason')
    fields = ('ip_address', 'reason', 'expires_at')
    
    def is_active(self, obj):
        if obj.expires_at and timezone.now() > obj.expires_at:
            return "❌ Expired"
        return "✅ Active"
    is_active.short_description = 'Status'


@admin.register(SuspiciousIP)
class SuspiciousIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'reason', 'severity', 'request_count', 
                   'first_detected', 'last_detected', 'is_active', 'actions')
    list_filter = ('reason', 'severity', 'is_active', 'first_detected')
    search_fields = ('ip_address', 'reason')
    readonly_fields = ('first_detected', 'last_detected', 'details_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('ip_address', 'reason', 'severity', 'request_count')
        }),
        ('Status', {
            'fields': ('is_active', 'auto_blocked', 'first_detected', 'last_detected')
        }),
        ('Details', {
            'fields': ('details_display',)
        }),
    )
    
    def details_display(self, obj):
        if obj.details:
            details_html = "<ul>"
            for key, value in obj.details.items():
                details_html += f"<li><strong>{key}:</strong> {value}</li>"
            details_html += "</ul>"
            return mark_safe(details_html)
        return "No details"
    details_display.short_description = 'Detection Details'
    
    def actions(self, obj):
        return format_html(
            '<a href="{}" class="button">Analyze</a> '
            '<a href="{}" class="button" style="background-color: #dc3545;">Block</a>',
            reverse('admin:analyze_ip_action', args=[obj.id]),
            reverse('admin:block_ip_action', args=[obj.id])
        )
    actions.short_description = 'Actions'


@admin.register(AnomalyDetectionConfig)
class AnomalyDetectionConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'enabled', 'threshold', 'time_window_hours', 
                   'severity_level', 'auto_block')
    list_filter = ('enabled', 'severity_level', 'auto_block')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'enabled')
        }),
        ('Detection Rules', {
            'fields': ('threshold', 'time_window_hours', 'sensitive_paths')
        }),
        ('Detection Criteria', {
            'fields': ('check_frequency', 'check_sensitive_paths', 'check_error_rate')
        }),
        ('Actions', {
            'fields': ('auto_block', 'severity_level')
        }),
    )


# Register other models
admin.site.register(GeolocationCache)
admin.site.register(RateLimitLog)