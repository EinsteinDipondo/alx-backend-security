#!/bin/bash
echo "Starting Django IP Tracking System on PythonAnywhere..."

# Set environment
export PYTHONANYWHERE_DOMAIN=einstein.pythonanywhere.com
export DB_NAME=Einstein$alx_ip_tracking
export DB_USER=Einstein
export DB_PASSWORD=$(cat ~/.mysql_password)

# Run migrations if needed
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Celery worker (runs in background)
nohup celery -A config worker --loglevel=info > celery.log 2>&1 &

# Start Celery beat (runs in background)
nohup celery -A config beat --loglevel=info > celery_beat.log 2>&1 &

echo "Application started!"
echo "Check logs: tail -f celery.log"
