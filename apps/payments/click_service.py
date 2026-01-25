"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import hashlib
import time
import requests
import json
import logging
import os
from .models import Transaction

# Set up logging
logger = logging.getLogger(__name__)

class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self):
        # Load settings directly from environment variables with fallback to hardcoded values
        self.merchant_id = os.getenv('CLICK_MERCHANT_ID') or getattr(settings, 'CLICK_MERCHANT_ID', '45730')
        self.service_id = os.getenv('CLICK_SERVICE_ID') or getattr(settings, 'CLICK_SERVICE_ID', '82154')
        self.secret_key = os.getenv('CLICK_SECRET_KEY') or getattr(settings, 'CLICK_SECRET_KEY', 'XZC6u3JBBh')
        self.merchant_user_id = os.getenv('CLICK_MERCHANT_USER_ID') or getattr(settings, 'CLICK_MERCHANT_USER_ID', '63536')
        self.api_url = "https://api.click.uz/v2/merchant"
        
        # If any of the required settings are empty, use hardcoded values
        if not self.merchant_id:
            self.merchant_id = '45730'
        if not self.service_id:
            self.service_id = '82154'
        if not self.secret_key:
            self.secret_key = 'XZC6u3JBBh'
        if not self.merchant_user_id:
            self.merchant_user_id = '63536'
        
        logger.info(f"ClickPaymentService initialized with: merchant_id={self.merchant_id}, service_id={self.service_id}, merchant_user_id={self.merchant_user_id}")
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        auth_header = f"{self.merchant_user_id}:{digest}:{timestamp}"
        logger.info(f"Generated auth header: {auth_header}")
        return auth_header
    
    def create_invoice(self, service_id, amount, phone_number, merchant_trans_id):
        """Create invoice for payment"""
        url = f"{self.api_url}/invoice/create"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        payload = {
            "service_id": service_id,
            "amount": float(amount),
            "phone_number": phone_number,
            "merchant_trans_id": merchant_trans_id
        }
        
        logger.info(f"Sending request to {url} with payload: {payload}")
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            logger.info(f"Response status: {response.status_code}, content: {response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {"error_code": -1, "error_note": str(e)}
    
    def generate_signature(self, *args):
        """Generate signature for Click request"""
        # Click uses MD5 hash for signature generation
        # According to documentation: sign_string = args + secret_key
        sign_string = ''.join(str(arg) for arg in args) + self.secret_key
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def prepare_payment(self, transaction):
        """Prepare payment data for Click"""
        # Bu metod endi create_invoice metodidan foydalanadi
        return self.create_invoice(
            service_id=self.service_id,
            amount=float(transaction.amount),
            phone_number=getattr(transaction.user, 'phone', ''),
            merchant_trans_id=str(transaction.id)
        )
    
    def handle_prepare(self, data):
        """Handle Click prepare request
        According to Click API documentation:
        If click_paydoc_id exists:
            sign_string = md5(click_trans_id + service_id + click_paydoc_id + merchant_trans_id + amount + action + sign_time + secret_key)
        Otherwise:
            sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
        """
        try:
            click_trans_id = data.get('click_trans_id')
            service_id = data.get('service_id')
            click_paydoc_id = data.get('click_paydoc_id')  # May be present in prepare callback
            merchant_trans_id = data.get('merchant_trans_id')
            amount = data.get('amount')
            action = data.get('action')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            logger.info(f"Handling prepare request with data: click_trans_id={click_trans_id}, service_id={service_id}, click_paydoc_id={click_paydoc_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}, sign_string={sign_string}")
            
            # Verify signature according to Click documentation
            # If click_paydoc_id exists, include it in signature
            if click_paydoc_id:
                # sign_string = md5(click_trans_id + service_id + click_paydoc_id + merchant_trans_id + amount + action + sign_time + secret_key)
                expected_sign = self.generate_signature(
                    click_trans_id, service_id, click_paydoc_id, merchant_trans_id, amount, action, sign_time
                )
                logger.info(f"Prepare signature with click_paydoc_id: click_trans_id={click_trans_id}, service_id={service_id}, click_paydoc_id={click_paydoc_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}")
            else:
                # sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
                expected_sign = self.generate_signature(
                    click_trans_id, service_id, merchant_trans_id, amount, action, sign_time
                )
                logger.info(f"Prepare signature without click_paydoc_id: click_trans_id={click_trans_id}, service_id={service_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}")
            
            logger.info(f"Expected signature: {expected_sign}, received signature: {sign_string}")
            
            if sign_string != expected_sign:
                logger.error(f"Signature mismatch! Expected: {expected_sign}, Got: {sign_string}")
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except ObjectDoesNotExist:
                logger.error("Transaction not found")
                return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Check amount
            if float(amount) != float(transaction.amount):
                logger.error("Invalid amount")
                return {'error': -2, 'error_note': 'Invalid amount'}
            
            # Save Click transaction ID
            transaction.click_trans_id = click_trans_id
            if click_paydoc_id:
                transaction.click_paydoc_id = str(click_paydoc_id)
            transaction.merchant_trans_id = merchant_trans_id
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'merchant_prepare_id': transaction.id,
                'error': 0,
                'error_note': 'Success'
            }
            
        except Exception as e:
            logger.error(f"Error in handle_prepare: {str(e)}")
            return {'error': -9, 'error_note': str(e)}
    
    def handle_complete(self, data):
        """Handle Click complete request"""
        try:
            click_trans_id = data.get('click_trans_id')
            merchant_trans_id = data.get('merchant_trans_id')
            merchant_prepare_id = data.get('merchant_prepare_id')
            error = data.get('error')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            logger.info(f"Handling complete request with data: click_trans_id={click_trans_id}, merchant_trans_id={merchant_trans_id}, merchant_prepare_id={merchant_prepare_id}, error={error}, sign_time={sign_time}, sign_string={sign_string}")
            
            # Verify signature for complete request
            # sign_string = md5(click_trans_id + merchant_trans_id + merchant_prepare_id + error + sign_time + secret_key)
            expected_sign = self.generate_signature(
                click_trans_id, merchant_trans_id, merchant_prepare_id, error, sign_time
            )
            
            logger.info(f"Expected signature: {expected_sign}, received signature: {sign_string}")
            
            if sign_string != expected_sign:
                logger.error("Invalid signature in complete request")
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            transaction = Transaction.objects.get(id=merchant_trans_id)
            
            if error == 0:
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.click_paydoc_id = data.get('click_paydoc_id', '')
            else:
                transaction.status = 'failed'
            
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': transaction.id,
                'error': 0,
                'error_note': 'Success'
            }
            
        except ObjectDoesNotExist:
            logger.error("Transaction not found in handle_complete")
            return {'error': -5, 'error_note': 'Transaction not found'}
        except Exception as e:
            logger.error(f"Error in handle_complete: {str(e)}")
            return {'error': -9, 'error_note': str(e)}