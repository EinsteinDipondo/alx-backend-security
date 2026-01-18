# PythonAnywhere Deployment Guide

## Deployment Status
✅ Application deployed to: https://einstein.pythonanywhere.com

## Features Available
- ✅ IP Logging Middleware
- ✅ Rate Limiting
- ✅ IP Blacklisting
- ✅ Swagger Documentation at `/swagger/`
- ✅ Django Admin at `/admin/`
- ✅ REST API endpoints
- ⚠️ Celery Tasks (Limited on free tier)
- ⚠️ Geolocation (Disabled on free tier)

## Admin Credentials
- URL: https://einstein.pythonanywhere.com/admin/
- Username: admin
- Password: [set during deployment]

## API Documentation
- Swagger UI: https://einstein.pythonanywhere.com/swagger/
- ReDoc: https://einstein.pythonanywhere.com/redoc/

## API Endpoints
- `GET /api/test/` - Test endpoint (rate limited)
- `GET /api/logs/` - View request logs (admin only)
- `GET /api/blocked-ips/` - View blocked IPs (admin only)
- `GET /api/suspicious-ips/` - View suspicious IPs (admin only)
- `GET /api/analyze-ip/<ip>/` - Analyze IP behavior

## Limitations (Free Tier)
1. **No Redis**: Using database as Celery broker (slower)
2. **No external API calls**: Geolocation disabled
3. **Email**: Console backend only
4. **Sleeps when inactive**: Visit monthly to keep alive
5. **Limited MySQL connections**

## Keeping Site Alive
Visit monthly and click "Run until 1 month from today" button.

## Log Files
- Access log: `/var/log/einstein.pythonanywhere.com.access.log`
- Error log: `/var/log/einstein.pythonanywhere.com.error.log`
- Server log: `/var/log/einstein.pythonanywhere.com.server.log`

## Source Code
Path: `/home/Einstein/alx-backend-security`

## Database
MySQL database: `Einstein$alx_ip_tracking`
Host: `Einstein.mysql.pythonanywhere-services.com`

## Troubleshooting
1. **Site not loading**: Check error logs
2. **Database errors**: Verify MySQL is running
3. **Static files missing**: Run `python manage.py collectstatic`
4. **Admin not working**: Check migrations are applied

## Contact
For issues, check error logs or contact administrator.
