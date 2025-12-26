import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables for Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Import Django after setting the environment
import django
django.setup()

# Now run migrations
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    print("Running migrations with the following settings:")
    print(f"USE_SQLITE: {os.getenv('USE_SQLITE')}")
    print(f"DATABASES: {os.getenv('DATABASES')}")
    
    # Run migrations
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Create superuser if needed
    if input("Create superuser? (y/n): ").lower() == 'y':
        execute_from_command_line(['manage.py', 'createsuperuser'])
