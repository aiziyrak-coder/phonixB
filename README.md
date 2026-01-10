# Phoenix Scientific Platform - Backend

Django REST Framework backend for Phoenix Scientific Platform.

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
CLICK_SECRET_KEY=08ClKUoBemAxyM
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
