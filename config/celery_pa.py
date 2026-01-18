import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using database as broker
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules
app.autodiscover_tasks()

# Configure beat schedule
app.conf.beat_schedule = {
    'detect-anomalies-daily': {
        'task': 'ip_tracking.tasks.detect_anomalies',
        'schedule': 86400.0,  # Daily on PythonAnywhere (hourly might be too frequent)
    },
    'generate-weekly-report': {
        'task': 'ip_tracking.tasks.generate_daily_report',
        'schedule': 604800.0,  # Weekly
    },
}