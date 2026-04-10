import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('USE_SQLITE', 'true')
os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-pytest-only')
