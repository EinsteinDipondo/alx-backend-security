"""
Production settings for PythonAnywhere
"""
import os
from .settings import *

# Security settings
DEBUG = False
ALLOWED_HOSTS = ['einstein.pythonanywhere.com', 'www.einstein.pythonanywhere.com']
CSRF_TRUSTED_ORIGINS = ['https://einstein.pythonanywhere.com', 'https://www.einstein.pythonanywhere.com']

# Database - PythonAnywhere provides MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'Einstein$alx_ip_tracking'),
        'USER': os.environ.get('DB_USER', 'Einstein'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'your-mysql-password'),
        'HOST': os.environ.get('DB_HOST', 'Einstein.mysql.pythonanywhere-services.com'),
        'PORT': '3306',
    }
}

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Email - use console backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Redis for Celery (PythonAnywhere doesn't allow Redis on free tier)
# We'll use database as broker for free tier
CELERY_BROKER_URL = 'django-db'
CELERY_RESULT_BACKEND = 'django-db'

# Disable geolocation APIs to avoid timeouts
IP_TRACKING_SETTINGS = {
    'GEOLOCATION_ENABLED': False,
    'ANOMALY_DETECTION_ENABLED': True,
    'AUTO_BLOCK_ENABLED': False,
}
