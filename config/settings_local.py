"""Local development settings for Phoenix Scientific Platform"""

# Import all settings from the main settings file
from .settings import *

# Override database settings for SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Disable SSL for local development
DATABASES['default']['OPTIONS'] = {}

# Disable SSL for PostgreSQL if used
for db in DATABASES.values():
    if 'OPTIONS' in db and 'sslmode' in db['OPTIONS']:
        del db['OPTIONS']['sslmode']

# Allow all hosts for local development
ALLOWED_HOSTS = ['*']

# Enable debug mode
DEBUG = True

# Disable HTTPS for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Enable CORS for local development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
