# Phoenix Scientific Platform - Backend

Django REST Framework backend for Phoenix Scientific Platform.

## Monitoring

- `GET /health/` yoki `GET /health/live/` — liveness (versiya, Python/Django haqida JSON).
- `GET /health/ready/` — PostgreSQL + `REDIS_URL` bo‘lsa Redis (503 agar kritik tekshiruv yiqilsa).
- `GET /metrics/` — Prometheus matn formati (`phoenix_up`, `phoenix_uptime_seconds`, `phoenix_info`). Maxfiy qilish uchun `.env` da `METRICS_SECRET` — so‘rov sarlavhasi `X-Metrics-Key`.
- Har bir API javobida `X-Request-ID`; so‘rov loglari `phoenix.request` logger orqali (`MONITORING_LOG_REQUESTS`, `MONITORING_LOG_JSON`).
- Sentry: `SENTRY_DSN`, ixtiyoriy `SENTRY_PROFILES_SAMPLE_RATE`, `APP_VERSION` / `GIT_REVISION` — `release` maydoni uchun.
- Gunicorn: `gunicorn.conf.py` — access log stdout, `WEB_CONCURRENCY` bilan worker soni.

## Features

- User authentication and authorization (JWT)
- Article management
- Journal management
- Payment integration (Click.uz)
- Translation services
- Notification system
- Review system
- Statistics and analytics

## Technology Stack

- Django 5.2.8
- Django REST Framework
- PostgreSQL/SQLite
- JWT Authentication
- Click.uz Payment Gateway

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env` file):
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
CLICK_MERCHANT_ID=45730
CLICK_SERVICE_ID=89248
CLICK_SECRET_KEY=<REDACTED_CLICK_SECRET>
CLICK_MERCHANT_USER_ID=72021
```

3. Run migrations:
```bash
python manage.py migrate
```

4. Create superuser:
```bash
python manage.py createsuperuser
```

5. Run development server:
```bash
python manage.py runserver 8000
```

## API Endpoints

- `/api/v1/auth/` - Authentication
- `/api/v1/articles/` - Articles
- `/api/v1/journals/` - Journals
- `/api/v1/payments/` - Payments
- `/api/v1/translations/` - Translation services
- `/api/v1/notifications/` - Notifications
- `/api/v1/reviews/` - Reviews

## Click Payment Integration

The platform integrates with Click.uz payment gateway. Ensure:
- Callback URLs are configured in Click merchant panel
- Server IP is whitelisted
- Service is activated in Click merchant panel
