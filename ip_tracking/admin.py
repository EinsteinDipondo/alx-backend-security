from django.contrib import admin
from django.utils import timezone
from .models import RequestLog, BlockedIP, GeolocationCache

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'location_display', 'path', 'timestamp')
    list_filter = ('country', 'city', 'timestamp')
    search_fields = ('ip_address', 'path', 'city', 'country')
    readonly_fields = ('ip_address', 'path', 'timestamp', 'get_location_display')
    fieldsets = (
        ('Request Information', {
            'fields': ('ip_address', 'path', 'timestamp')
        }),
        ('Geolocation Information', {
            'fields': ('country', 'city', 'region', 'latitude', 'longitude', 'timezone', 'isp')
        }),
        ('Metadata', {
            'fields': ('geolocation_updated', 'geolocation_source')
        }),
    )
    
    def location_display(self, obj):
        return obj.get_location_display()
    location_display.short_description = 'Location'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


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


@admin.register(GeolocationCache)
class GeolocationCacheAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'city', 'country', 'updated_at', 'expires_at', 'is_expired')
    list_filter = ('country', 'updated_at')
    search_fields = ('ip_address', 'city', 'country')
    readonly_fields = ('created_at', 'updated_at')
    
    def is_expired(self, obj):
        if obj.is_expired():
            return "❌ Expired"
        return "✅ Active"
    is_expired.short_description = 'Status'