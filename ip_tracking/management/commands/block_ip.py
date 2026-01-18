from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta
from ip_tracking.models import BlockedIP
import ipaddress

class Command(BaseCommand):
    """
    Management command to add IP addresses to the block list.
    
    Usage:
        python manage.py block_ip <ip_address> [--reason REASON] [--expires EXPIRES]
    
    Examples:
        python manage.py block_ip 192.168.1.100
        python manage.py block_ip 192.168.1.100 --reason "Spam bot"
        python manage.py block_ip 192.168.1.100 --expires "2024-12-31 23:59:59"
        python manage.py block_ip 192.168.1.100 --expires "+7d"  # 7 days from now
    """
    
    help = 'Add an IP address to the block list'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'ip_address',
            type=str,
            help='IP address to block'
        )
        
        parser.add_argument(
            '--reason',
            type=str,
            default='',
            help='Reason for blocking the IP'
        )
        
        parser.add_argument(
            '--expires',
            type=str,
            default=None,
            help='Expiration date (format: YYYY-MM-DD HH:MM:SS or +Nd for N days)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update if IP already exists in block list'
        )
    
    def handle(self, *args, **options):
        ip_address = options['ip_address']
        reason = options['reason']
        expires = options['expires']
        force = options['force']
        
        # Validate IP address
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise CommandError(f"Invalid IP address: {ip_address}")
        
        # Parse expiration date
        expires_at = None
        if expires:
            if expires.startswith('+'):
                # Relative time (e.g., +7d for 7 days)
                try:
                    days = int(expires[1:-1])
                    if expires.endswith('d'):
                        expires_at = timezone.now() + timedelta(days=days)
                    else:
                        raise CommandError("Relative time must end with 'd' (days)")
                except (ValueError, IndexError):
                    raise CommandError("Invalid relative time format. Use '+Nd' (e.g., '+7d')")
            else:
                # Absolute time
                try:
                    expires_at = datetime.strptime(expires, '%Y-%m-%d %H:%M:%S')
                    expires_at = timezone.make_aware(expires_at)
                except ValueError:
                    try:
                        expires_at = datetime.strptime(expires, '%Y-%m-%d')
                        expires_at = timezone.make_aware(expires_at)
                    except ValueError:
                        raise CommandError(
                            "Invalid date format. Use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'"
                        )
        
        # Check if IP already exists
        try:
            blocked_ip = BlockedIP.objects.get(ip_address=ip_address)
            
            if not force:
                raise CommandError(
                    f"IP {ip_address} is already blocked. "
                    f"Reason: {blocked_ip.reason}. "
                    f"Use --force to update."
                )
            
            # Update existing entry
            blocked_ip.reason = reason or blocked_ip.reason
            blocked_ip.expires_at = expires_at
            blocked_ip.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated block for IP: {ip_address}"
                )
            )
            
        except BlockedIP.DoesNotExist:
            # Create new block entry
            BlockedIP.objects.create(
                ip_address=ip_address,
                reason=reason,
                expires_at=expires_at
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully blocked IP: {ip_address}"
                )
            )
        
        # Display block information
        blocked_ip = BlockedIP.objects.get(ip_address=ip_address)
        self.stdout.write(f"IP Address: {blocked_ip.ip_address}")
        self.stdout.write(f"Reason: {blocked_ip.reason or 'Not specified'}")
        self.stdout.write(f"Created: {blocked_ip.created_at}")
        if blocked_ip.expires_at:
            self.stdout.write(f"Expires: {blocked_ip.expires_at}")
        else:
            self.stdout.write("Expires: Never (permanent block)")