#!/bin/bash

echo "Setting up Django IP Tracking Project..."

# Navigate to project directory
cd C:/Users/Einstein/OneDrive/Desktop/alx-backend-security

# Install Django
echo "Installing Django..."
pip install django

# Install other required packages
echo "Installing django-ratelimit..."
pip install django-ratelimit

echo "Installing requests..."
pip install requests

echo "Installing django-ipware..."
pip install django-ipware

echo "Installing geoip2 (optional for geolocation)..."
pip install geoip2

# Create requirements.txt
echo "Creating requirements.txt..."
cat > requirements.txt << 'REQEOF'
Django>=4.0,<5.0
django-ratelimit>=3.0
requests>=2.28
django-ipware>=5.0
REQEOF

# Temporarily simplify files to run migrations
echo "Creating minimal setup for migrations..."

# Create minimal models.py if needed
if [ ! -f "ip_tracking/models.py" ]; then
    cat > ip_tracking/models.py << 'MODEOF'
from django.db import models
from django.utils import timezone

class RequestLog(models.Model):
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    path = models.CharField(max_length=500)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.ip_address} - {self.path} - {self.timestamp}"
MODEOF
fi

# Create minimal views.py
cat > ip_tracking/views.py << 'VIEWEOF'
from django.http import HttpResponse

def home(request):
    return HttpResponse("IP Tracking Demo - Home")
VIEWEOF

# Update urls.py
cat > config/urls.py << 'URLSEOF'
from django.contrib import admin
from django.urls import path
from ip_tracking.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
]
URLSEOF

# Run migrations
echo "Running migrations..."
python manage.py makemigrations ip_tracking
python manage.py migrate

echo "Setup complete!"
echo "Now you can restore the full project files."
