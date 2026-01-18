from django.core.management.base import BaseCommand
from ip_tracking.tasks import analyze_ip_behavior
import json

class Command(BaseCommand):
    help = 'Analyze behavior of a specific IP address'
    
    def add_arguments(self, parser):
        parser.add_argument('ip_address', type=str, help='IP address to analyze')
        parser.add_argument('--hours', type=int, default=24, help='Time window in hours')
    
    def handle(self, *args, **options):
        ip_address = options['ip_address']
        hours = options['hours']
        
        self.stdout.write(f"Analyzing IP {ip_address} (last {hours} hours)...")
        
        result = analyze_ip_behavior.delay(ip_address, hours)
        analysis = result.get(timeout=10)  # Wait for result
        
        if 'error' in analysis:
            self.stdout.write(self.style.ERROR(analysis['error']))
        else:
            self.stdout.write(json.dumps(analysis, indent=2))
            
            if analysis.get('suspicious'):
                self.stdout.write(self.style.WARNING("⚠️  This IP shows suspicious behavior!"))