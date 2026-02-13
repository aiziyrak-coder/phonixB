import os
import django
from django.contrib.auth import get_user_model

def setup_database():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')
    django.setup()
    
    # Get the User model
    User = get_user_model()
    
    # Create superuser if it doesn't exist
    # NOTE: Test parollar olib tashlandi - production'da faqat haqiqiy parollar ishlatiladi
    if not User.objects.filter(phone='+998910574905').exists():
        # Production'da parol environment variable'dan olinishi kerak
        import os
        admin_password = os.environ.get('ADMIN_PASSWORD', 'changeme123!')
        User.objects.create_superuser(
            phone='+998910574905',
            email='admin@example.com',
            full_name='Admin User',
            password=admin_password,
            is_active=True,
            is_staff=True
        )
        print("Superuser created successfully!")
    else:
        print("Superuser already exists.")

if __name__ == "__main__":
    setup_db()
