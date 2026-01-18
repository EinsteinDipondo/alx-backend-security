from django.core.management.base import BaseCommand, CommandError
from ip_tracking.models import BlockedIP

class Command(BaseCommand):
    """
    Management command to remove IP addresses from the block list.
    
    Usage:
        python manage.py unblock_ip <ip_address>
    
    Examples:
        python manage.py unblock_ip 192.168.1.100
    """
    
    help = 'Remove an IP address from the block list'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'ip_address',
            type=str,
            help='IP address to unblock'
        )
    
    def handle(self, *args, **options):
        ip_address = options['ip_address']
        
        try:
            blocked_ip = BlockedIP.objects.get(ip_address=ip_address)
            blocked_ip.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully unblocked IP: {ip_address}"
                )
            )
            
        except BlockedIP.DoesNotExist:
            raise CommandError(f"IP {ip_address} is not in the block list")