"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
import hashlib
import time
import requests
from .models import Transaction


class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self):
        self.merchant_id = settings.CLICK_MERCHANT_ID
        self.service_id = settings.CLICK_SERVICE_ID
        self.secret_key = settings.CLICK_SECRET_KEY
        self.merchant_user_id = settings.CLICK_MERCHANT_USER_ID
        self.api_url = "https://api.click.uz/v2/merchant"
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{timestamp}"
    
    def generate_signature(self, *args):
        """Generate signature for Click request"""
        sign_string = ''.join(str(arg) for arg in args)
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def create_invoice(self, service_id, amount, phone_number, merchant_trans_id):
        """Create invoice (sчет-фактура)"""
        url = f"{self.api_url}/invoice/create"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'amount': amount,
            'phone_number': phone_number,
            'merchant_trans_id': merchant_trans_id
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def check_invoice_status(self, service_id, invoice_id):
        """Check invoice status"""
        url = f"{self.api_url}/invoice/status/{service_id}/{invoice_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def check_payment_status(self, service_id, payment_id):
        """Check payment status"""
        url = f"{self.api_url}/payment/status/{service_id}/{payment_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def check_payment_status_by_mti(self, service_id, merchant_trans_id, date):
        """Check payment status by merchant_trans_id"""
        url = f"{self.api_url}/payment/status_by_mti/{service_id}/{merchant_trans_id}/{date}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def reverse_payment(self, service_id, payment_id):
        """Reverse (cancel) payment"""
        url = f"{self.api_url}/payment/reversal/{service_id}/{payment_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.delete(url, headers=headers)
        return response.json()
    
    def request_card_token(self, service_id, card_number, expire_date, temporary=1):
        """Request card token"""
        url = f"{self.api_url}/card_token/request"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        data = {
            'service_id': service_id,
            'card_number': card_number,
            'expire_date': expire_date,
            'temporary': temporary
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def verify_card_token(self, service_id, card_token, sms_code):
        """Verify card token"""
        url = f"{self.api_url}/card_token/verify"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'card_token': card_token,
            'sms_code': sms_code
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def pay_with_card_token(self, service_id, card_token, amount, merchant_trans_id):
        """Pay with card token"""
        url = f"{self.api_url}/card_token/payment"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'card_token': card_token,
            'amount': amount,
            'merchant_trans_id': merchant_trans_id
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def delete_card_token(self, service_id, card_token):
        """Delete card token"""
        url = f"{self.api_url}/card_token/{service_id}/{card_token}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.delete(url, headers=headers)
        return response.json()
    
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
        """Handle Click prepare request"""
        try:
            click_trans_id = data.get('click_trans_id')
            service_id = data.get('service_id')
            merchant_trans_id = data.get('merchant_trans_id')
            amount = data.get('amount')
            action = data.get('action')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            # Verify signature
            expected_sign = self.generate_signature(
                click_trans_id, service_id, self.secret_key,
                merchant_trans_id, amount, action, sign_time
            )
            
            if sign_string != expected_sign:
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except Transaction.DoesNotExist:
                return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Check amount
            if float(amount) != float(transaction.amount):
                return {'error': -2, 'error_note': 'Invalid amount'}
            
            # Save Click transaction ID
            transaction.click_trans_id = click_trans_id
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
            return {'error': -9, 'error_note': str(e)}
    
    def handle_complete(self, data):
        """Handle Click complete request"""
        try:
            click_trans_id = data.get('click_trans_id')
            merchant_trans_id = data.get('merchant_trans_id')
            merchant_prepare_id = data.get('merchant_prepare_id')
            error = data.get('error')
            
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
            
        except Transaction.DoesNotExist:
            return {'error': -5, 'error_note': 'Transaction not found'}
        except Exception as e:
            return {'error': -9, 'error_note': str(e)}