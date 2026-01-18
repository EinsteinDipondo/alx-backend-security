from django.core.management.base import BaseCommand
from django.utils import timezone
from ip_tracking.models import BlockedIP
from django.db.models import Q

class Command(BaseCommand):
    """
    Management command to list all blocked IP addresses.
    
    Usage:
        python manage.py list_blocked_ips
        python manage.py list_blocked_ips --active
        python manage.py list_blocked_ips --expired
    """
    
    help = 'List all blocked IP addresses'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--active',
            action='store_true',
            help='Show only active blocks (not expired)'
        )
        
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Show only expired blocks'
        )
    
    def handle(self, *args, **options):
        blocked_ips = BlockedIP.objects.all()
        
        if options['active']:
            blocked_ips = blocked_ips.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )
            self.stdout.write("Active Blocked IPs:")
        elif options['expired']:
            blocked_ips = blocked_ips.filter(expires_at__lt=timezone.now())
            self.stdout.write("Expired Blocked IPs:")
        else:
            self.stdout.write("All Blocked IPs:")
        
        if not blocked_ips:
            self.stdout.write(self.style.WARNING("No blocked IPs found"))
            return
        
        for blocked_ip in blocked_ips:
            status = "ACTIVE"
            if blocked_ip.expires_at and blocked_ip.expires_at < timezone.now():
                status = "EXPIRED"
            
            self.stdout.write(
                f"{blocked_ip.ip_address:<20} | "
                f"Reason: {blocked_ip.reason or 'N/A':<30} | "
                f"Created: {blocked_ip.created_at.strftime('%Y-%m-%d'):<12} | "
                f"Expires: {blocked_ip.expires_at.strftime('%Y-%m-%d') if blocked_ip.expires_at else 'Never':<12} | "
                f"Status: {status}"
            )