from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ip_tracking.models import RequestLog, GeolocationCache
from ip_tracking.middleware import BasicIPLoggingMiddleware
import sys

class Command(BaseCommand):
    """
    Management command to update geolocation data for existing logs.
    
    Usage:
        python manage.py update_geolocation --all
        python manage.py update_geolocation --recent
        python manage.py update_geolocation --ip 192.168.1.100
    """
    
    help = 'Update geolocation data for request logs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Update geolocation for all logs'
        )
        
        parser.add_argument(
            '--recent',
            action='store_true',
            help='Update geolocation for recent logs (last 7 days)'
        )
        
        parser.add_argument(
            '--ip',
            type=str,
            help='Update geolocation for a specific IP'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit the number of updates (default: 100)'
        )
    
    def handle(self, *args, **options):
        middleware = BasicIPLoggingMiddleware(None)
        
        if options['ip']:
            # Update specific IP
            self.update_ip_geolocation(middleware, options['ip'])
        
        elif options['all']:
            # Update all logs without geolocation
            logs = RequestLog.objects.filter(
                country__isnull=True
            ).order_by('-timestamp')[:options['limit']]
            
            self.stdout.write(f"Updating {len(logs)} logs without geolocation...")
            self.update_logs_geolocation(middleware, logs)
        
        elif options['recent']:
            # Update recent logs
            week_ago = timezone.now() - timedelta(days=7)
            logs = RequestLog.objects.filter(
                timestamp__gte=week_ago
            ).order_by('-timestamp')[:options['limit']]
            
            self.stdout.write(f"Updating {len(logs)} recent logs...")
            self.update_logs_geolocation(middleware, logs)
        
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please specify --all, --recent, or --ip <ip_address>"
                )
            )
    
    def update_ip_geolocation(self, middleware, ip_address):
        """Update geolocation for a specific IP"""
        self.stdout.write(f"Updating geolocation for IP: {ip_address}")
        
        geolocation_data = middleware.get_geolocation_data(ip_address)
        
        if geolocation_data:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Location: {geolocation_data.get('city', 'Unknown')}, "
                    f"{geolocation_data.get('country', 'Unknown')}"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("Failed to get geolocation"))
    
    def update_logs_geolocation(self, middleware, logs):
        """Update geolocation for multiple logs"""
        updated_count = 0
        
        for log in logs:
            geolocation_data = middleware.get_geolocation_data(log.ip_address)
            
            if geolocation_data and geolocation_data.get('source') not in ['private_ip', 'failed']:
                log.country = geolocation_data.get('country')
                log.country_code = geolocation_data.get('country_code')
                log.city = geolocation_data.get('city')
                log.region = geolocation_data.get('region')
                log.latitude = geolocation_data.get('latitude')
                log.longitude = geolocation_data.get('longitude')
                log.timezone = geolocation_data.get('timezone')
                log.isp = geolocation_data.get('isp')
                log.geolocation_updated = timezone.now()
                log.geolocation_source = geolocation_data.get('source')
                
                log.save()
                updated_count += 1
                
                # Show progress
                if updated_count % 10 == 0:
                    self.stdout.write(f"Updated {updated_count} logs...")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated {updated_count} logs with geolocation data"
            )
        )