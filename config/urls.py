from django.contrib import admin
from django.urls import path
from ip_tracking import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('sensitive-data/', views.SensitiveDataView.as_view(), name='sensitive_data'),
    path('api/test/', views.APIView.as_view(), name='api_test'),
    path('rate-limit-test/', views.RateLimitTestView.as_view(), name='rate_limit_test'),
]
