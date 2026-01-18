from django.contrib import admin
from .models import RequestLog, BlockedIP
from django.utils import timezone

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'path', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('ip_address', 'path')
    readonly_fields = ('ip_address', 'path', 'timestamp')
    
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