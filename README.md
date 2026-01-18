# Django IP Tracking System

A comprehensive IP tracking, security, and analytics system for Django applications.  
Provides request logging, geolocation enrichment, rate limiting, blacklisting, anomaly detection, alerting, and admin tooling to help secure and analyze traffic.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Django](https://img.shields.io/badge/Django-4.x-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

Table of contents
- Features
- Quick start
- Configuration
- Project structure
- Usage examples
- Models overview
- Security & analytics
- Scheduled tasks
- Privacy & compliance
- Troubleshooting
- Testing
- Contributing
- License
- Acknowledgments

---

## Features

The project is split into incremental "Tasks" to make functionality and progression clear:

- ✅ Task 0 — Basic IP logging
  - `RequestLog` model: ip address, timestamp, request path
  - Middleware to log incoming requests automatically
  - Django admin configuration to view & filter logs

- ✅ Task 1 — IP blacklisting
  - `BlockedIP` model with reason and optional expiration
  - Middleware blocks blacklisted IPs (HTTP 403)
  - Management commands: `block_ip`, `unblock_ip`, `list_blocked_ips`
  - Redis caching for fast lookups

- ✅ Task 2 — Geolocation enrichment
  - RequestLog extended with `country`, `city`, `region`, `latitude`, `longitude`, `isp`
  - Multi-source geolocation (ipapi.co, ipinfo.io) with fallback
  - 24-hour caching (in-memory + DB) via `GeolocationCache` model

- ✅ Task 3 — Rate limiting
  - Integration with `django-ratelimit`
  - Differential limits: authenticated (10/min), anonymous (5/min)
  - Login protection: 3 attempts / 5 minutes
  - `RateLimitLog` model to record rate-limit events

- ✅ Task 4 — Anomaly detection
  - `SuspiciousIP` model for flagged IPs
  - Hourly Celery tasks to detect anomalies
  - Rules: e.g. >100 reqs/hour, access to sensitive paths, >50% error rate
  - Configurable auto-blocking + email alerts and daily reports

---

## Quick start

Prerequisites
- Python 3.8+
- Django 4.x+
- Redis (cache + Celery broker)
- PostgreSQL (recommended) or SQLite

1. Clone and setup
```bash
git clone https://github.com/your-username/alx-backend-security.git
cd alx-backend-security
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment
```bash
cp .env.example .env
# Edit .env with SECRET_KEY, DB settings, Redis URL, email settings, etc.
```

3. Database setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Start services (recommended in separate terminals)
```bash
# Terminal 1: Django dev server
python manage.py runserver

# Terminal 2: Redis server
redis-server

# Terminal 3: Celery worker
celery -A config worker --loglevel=info

# Terminal 4: Celery beat (scheduled tasks)
celery -A config beat --loglevel=info
```

---

## Configuration

Key settings in `config/settings.py` (examples)

```python
# Rate limiting
RATELIMIT_CONFIG = {
    'anonymous': {'rate': '5/m', 'block': True},
    'authenticated': {'rate': '10/m', 'block': True},
    'login': {'rate': '3/5m', 'block': True},
}

# Celery
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'detect-anomalies-hourly': {
        'task': 'ip_tracking.tasks.detect_anomalies',
        'schedule': 3600.0,
    },
}

# Cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

Anomaly detection is configurable via an `AnomalyDetectionConfig` model (editable in admin or via management commands).

---

## Project structure

```
alx-backend-security/
├── config/                 # Django project settings & celery
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── __init__.py
├── ip_tracking/            # App: models, middleware, tasks, views, admin, management
│   ├── models.py
│   ├── middleware.py
│   ├── tasks.py
│   ├── views.py
│   ├── admin.py
│   ├── management/commands/
│   └── templates/
├── requirements.txt
└── README.md
```

---

## Usage examples

Block an IP
```bash
# Block permanently
python manage.py block_ip 192.168.1.100 --reason "Spam bot"

# Block with expiration (e.g. +7 days)
python manage.py block_ip 192.168.1.101 --expires "+7d" --reason "Temporary block"

# List blocked IPs
python manage.py list_blocked_ips
```

Analyze an IP's recent behavior
```bash
python manage.py analyze_ip 192.168.1.100 --hours 24
```
Output includes totals, requests/hour, error rate, sensitive path hits, suspicious flags.

Run anomaly detection manually
```bash
python manage.py detect_anomalies_now
```

Access the web interface
- Home: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- Login (rate-limited): http://localhost:8000/login/
- Rate-limit test: http://localhost:8000/rate-limit-test/

---

## Models overview

- RequestLog
  - ip_address, timestamp, path
  - country, city, region, latitude, longitude, isp
  - is_suspicious (flag)

- BlockedIP
  - ip_address, reason, expires_at, created_at

- SuspiciousIP
  - ip_address, reason (high_frequency, sensitive_paths, etc.)
  - severity (low|medium|high|critical)
  - request_count, details (JSON)

- RateLimitLog
  - ip_address, endpoint, timestamp, limit, action

- GeolocationCache
  - ip_address, data (JSON), last_updated

- AnomalyDetectionConfig
  - threshold, sensitive_paths, auto_block, severity_level

---

## Security & analytics

- IP blacklisting: block requests at middleware level, backed by `BlockedIP` model and Redis cache.
- Rate limiting: configurable per-user-type limits and endpoint-specific rules via `django-ratelimit`.
- Anomaly detection: scheduled scans for spikes, sensitive path access, high error rates; configurable auto-blocking and severity handling.
- Geolocation analytics: visualize traffic origins using IP->location mappings (with caching to reduce API usage).
- Alerts: email notifications for critical detections and auto-block events (configure SMTP settings in `settings.py`).

---

## Scheduled tasks

- Hourly: anomaly detection (`ip_tracking.tasks.detect_anomalies`)
- Daily: cleanup old suspicious IPs, generate anomaly reports
- On-demand: geolocation refreshes / rechecks

Celery Beat schedules are in `CELERY_BEAT_SCHEDULE`.

---

## Privacy & compliance

- GDPR features:
  - IP anonymization options available in settings
  - Configurable data retention policies
  - Admin controls to delete or export user-related logs
- Opt-out: per-user or per-region tracking opt-out mechanisms available
- Transparency: logs clearly record tracking activity; use responsibly and display appropriate privacy notices in your app

---

## Troubleshooting

Common issues
- Migrations fail: make sure all dependencies are installed and DB credentials are correct
- Celery not running: verify Redis is running and reachable
- Geolocation failing: check internet access and API quotas for ipapi/ipinfo
- Rate limiting too strict: adjust `RATELIMIT_CONFIG` in settings

Helpful commands
```bash
python manage.py check
python manage.py migrate
python manage.py shell
# Inspect recent logs
>>> from ip_tracking.models import RequestLog
>>> RequestLog.objects.order_by('-timestamp')[:10]
```

Test geolocation snippet
```python
from ip_tracking.middleware import BasicIPLoggingMiddleware
middleware = BasicIPLoggingMiddleware(get_response=None)
print(middleware.get_geolocation_data('8.8.8.8'))
```

---

## Testing

Run the test suite
```bash
python manage.py test ip_tracking
# Specific tests
python manage.py test ip_tracking.tests.test_middleware
python manage.py test ip_tracking.tests.test_anomaly_detection
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/awesome`
3. Add tests and documentation
4. Open a pull request describing your changes

Please follow the project's code style and add tests for new functionality.

---

## License

MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Django community
- ipapi.co and ipinfo.io for geolocation services
- ALX Backend Security program for project guidance

If you'd like, I can:
- add badges for CI or PyPI,
- generate a shorter "quickstart" for a Docker-based setup,
- or produce a CONTRIBUTING.md and CHANGELOG.md next. Which would you prefer?  
```
