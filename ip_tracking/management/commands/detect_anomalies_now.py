from django.core.management.base import BaseCommand
from ip_tracking.tasks import detect_anomalies

class Command(BaseCommand):
    help = 'Run anomaly detection immediately'
    
    def handle(self, *args, **options):
        self.stdout.write("Running anomaly detection...")
        result = detect_anomalies.delay()
        self.stdout.write(self.style.SUCCESS(f"Task started with ID: {result.id}"))