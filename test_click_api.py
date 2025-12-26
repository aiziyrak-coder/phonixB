"""
Test script to verify Click API connectivity
"""
import os
import django
from django.conf import settings

# Set environment variables directly
os.environ['CLICK_MERCHANT_ID'] = '45730'
os.environ['CLICK_SERVICE_ID'] = '82154'
os.environ['CLICK_SECRET_KEY'] = 'XZC6u3JBBh'
os.environ['CLICK_MERCHANT_USER_ID'] = '63536'

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')
django.setup()

# Print environment variables
print("Environment variables:")
print(f"CLICK_MERCHANT_ID: {os.getenv('CLICK_MERCHANT_ID')}")
print(f"CLICK_SERVICE_ID: {os.getenv('CLICK_SERVICE_ID')}")
print(f"CLICK_SECRET_KEY: {os.getenv('CLICK_SECRET_KEY')}")
print(f"CLICK_MERCHANT_USER_ID: {os.getenv('CLICK_MERCHANT_USER_ID')}")

# Print Django settings
print("\nDjango settings:")
print(f"CLICK_MERCHANT_ID: {getattr(settings, 'CLICK_MERCHANT_ID', 'NOT SET')}")
print(f"CLICK_SERVICE_ID: {getattr(settings, 'CLICK_SERVICE_ID', 'NOT SET')}")
print(f"CLICK_SECRET_KEY: {getattr(settings, 'CLICK_SECRET_KEY', 'NOT SET')}")
print(f"CLICK_MERCHANT_USER_ID: {getattr(settings, 'CLICK_MERCHANT_USER_ID', 'NOT SET')}")

from apps.payments.services import ClickPaymentService

def test_click_api():
    """Test Click API connectivity"""
    print("\nTesting Click API connectivity...")
    
    # Initialize service with direct settings
    service = ClickPaymentService()
    
    print(f"Merchant ID: {service.merchant_id}")
    print(f"Service ID: {service.service_id}")
    print(f"Merchant User ID: {service.merchant_user_id}")
    print(f"API URL: {service.api_url}")
    
    # Test auth header generation
    auth_header = service.generate_auth_header()
    print(f"Auth header: {auth_header}")
    
    # Test create invoice
    print("\nTesting create invoice...")
    result = service.create_invoice(
        service_id=service.service_id,
        amount=10000,
        phone_number="998901234567",
        merchant_trans_id="test_transaction_123"
    )
    print(f"Invoice result: {result}")

if __name__ == "__main__":
    test_click_api()