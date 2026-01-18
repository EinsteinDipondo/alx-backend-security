# At the top, add:
import os
from dotenv import load_dotenv

load_dotenv()

# Replace DATABASES section with:
if os.environ.get('PYTHONANYWHERE_DOMAIN'):
    # Production database for PythonAnywhere
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'Einstein$alx_ip_tracking'),
            'USER': os.environ.get('DB_USER', 'Einstein'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'Einstein.mysql.pythonanywhere-services.com'),
            'PORT': '3306',
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            }
        }
    }
else:
    # Development database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Update ALLOWED_HOSTS
ALLOWED_HOSTS = ['einstein.pythonanywhere.com', 'localhost', '127.0.0.1']

# Celery configuration for PythonAnywhere (using database as broker)
CELERY_BROKER_URL = 'django-db'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

INSTALLED_APPS += [
    'django_celery_results',
    'django_celery_beat',
]

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ADMIN_EMAILS = ['your-email@example.com']