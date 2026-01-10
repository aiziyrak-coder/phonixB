"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
import hashlib
import time
import requests
import logging
from .models import Transaction

logger = logging.getLogger(__name__)


class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self):
        # Use settings with fallback to PHOENIX service defaults
        merchant_id_raw = settings.CLICK_MERCHANT_ID or '45730'
        service_id_raw = settings.CLICK_SERVICE_ID or '89248'
        secret_key_raw = settings.CLICK_SECRET_KEY or '08ClKUoBemAxyM'
        merchant_user_id_raw = settings.CLICK_MERCHANT_USER_ID or '72021'
        
        # Convert to string and strip whitespace
        self.merchant_id = str(merchant_id_raw).strip()
        self.service_id = str(service_id_raw).strip()
        self.secret_key = str(secret_key_raw).strip()
        self.merchant_user_id = str(merchant_user_id_raw).strip()
        self.api_url = "https://api.click.uz/v2/merchant"
        
        # Validate that all required fields are set (non-empty after strip)
        if not self.service_id:
            logger.error("CLICK_SERVICE_ID is empty, using default: 89248")
            self.service_id = '89248'
        if not self.merchant_user_id:
            logger.error("CLICK_MERCHANT_USER_ID is empty, using default: 72021")
            self.merchant_user_id = '72021'
        if not self.secret_key:
            logger.error("CLICK_SECRET_KEY is empty, using default")
            self.secret_key = '08ClKUoBemAxyM'
        if not self.merchant_id:
            logger.error("CLICK_MERCHANT_ID is empty, using default: 45730")
            self.merchant_id = '45730'
        
        logger.info(f"ClickPaymentService initialized - service_id: {self.service_id}, merchant_user_id: {self.merchant_user_id}, merchant_id: {self.merchant_id}")
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{timestamp}"
    
    def generate_signature(self, *args):
        """Generate signature for Click request
        According to Click API: sign_string = md5(args + secret_key)
        """
        # Concatenate all arguments as strings
        sign_string = ''.join(str(arg) for arg in args)
        # Append secret key
        sign_string += self.secret_key
        # Generate MD5 hash
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def create_invoice(self, service_id, amount, phone_number, merchant_trans_id):
        """Create invoice (sчет-фактура) via Click API"""
        url = f"{self.api_url}/invoice/create"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        # Ensure service_id is a valid integer string
        # Use provided service_id or fallback to self.service_id
        service_id_to_use = service_id if service_id else self.service_id
        
        try:
            # Convert to string, strip whitespace, then to int
            service_id_str = str(service_id_to_use).strip()
            if not service_id_str:
                logger.error(f"service_id is empty - provided: {service_id}, self.service_id: {self.service_id}")
                return {
                    'error_code': -1,
                    'error_note': 'service_id is empty or invalid',
                    'invoice_id': None,
                    'invoice_url': None
                }
            service_id_int = int(service_id_str)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid service_id: {service_id_to_use} (type: {type(service_id_to_use)}), error: {e}")
            return {
                'error_code': -1,
                'error_note': f'Invalid service_id: {service_id_to_use}',
                'invoice_id': None,
                'invoice_url': None
            }
        
        # Ensure phone_number is in correct format (998XXXXXXXXX) and not empty
        if not phone_number or phone_number.strip() == '':
            logger.error(f"Phone number is empty - cannot create invoice")
            return {
                'error_code': -1,
                'error_note': 'Phone number is required for invoice creation',
                'invoice_id': None,
                'invoice_url': None
            }
        
        # Phone number should be in format 998XXXXXXXXX (12 digits total)
        phone_str = str(phone_number).strip()
        phone_digits = ''.join(filter(str.isdigit, phone_str))
        
        if not phone_digits or len(phone_digits) < 9:
            logger.error(f"Invalid phone number format: {phone_number}")
            return {
                'error_code': -1,
                'error_note': f'Invalid phone number format: {phone_number}. Phone number must be in format 998XXXXXXXXX',
                'invoice_id': None,
                'invoice_url': None
            }
        
        # Ensure phone number is in 998XXXXXXXXX format
        if phone_digits.startswith('998') and len(phone_digits) == 12:
            formatted_phone = phone_digits
        elif phone_digits.startswith('9') and len(phone_digits) == 9:
            formatted_phone = '998' + phone_digits
        elif len(phone_digits) >= 9:
            formatted_phone = '998' + phone_digits[-9:]  # Take last 9 digits
        else:
            logger.error(f"Cannot format phone number: {phone_number}")
            return {
                'error_code': -1,
                'error_note': f'Cannot format phone number: {phone_number}',
                'invoice_id': None,
                'invoice_url': None
            }
        
        data = {
            'service_id': service_id_int,
            'amount': float(amount),
            'phone_number': formatted_phone,
            'merchant_trans_id': str(merchant_trans_id)
        }
        
        logger.info(f"Creating invoice with formatted phone number: {formatted_phone} (original: {phone_number})")
        
        logger.info(f"Creating invoice via Click API: URL={url}, Data={data}")
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            logger.info(f"Click API response status: {response.status_code}, content: {response.text[:500]}")
            
            # Try to parse JSON response
            try:
                result = response.json()
            except ValueError:
                # If response is not JSON, return error
                logger.error(f"Click API returned non-JSON response: {response.text}")
                return {
                    'error_code': -1,
                    'error_note': f'Invalid response from Click API: {response.text[:200]}',
                    'invoice_id': None,
                    'invoice_url': None
                }
            
            # Check response status code
            if response.status_code != 200:
                error_code = result.get('error_code') or result.get('error') or -1
                error_note = result.get('error_note') or result.get('error') or f'HTTP {response.status_code}'
                logger.error(f"Click API error: {error_code} - {error_note}")
                return {
                    'error_code': error_code,
                    'error_note': error_note,
                    'invoice_id': None,
                    'invoice_url': None
                }
            
            # Check if result has error
            if 'error_code' in result and result.get('error_code') != 0:
                error_code = result.get('error_code', -1)
                error_note = result.get('error_note') or result.get('error') or 'Unknown error'
                logger.error(f"Click API returned error: {error_code} - {error_note}")
                return {
                    'error_code': error_code,
                    'error_note': error_note,
                    'invoice_id': result.get('invoice_id'),
                    'invoice_url': None
                }
            
            logger.info(f"Invoice created successfully: {result}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error("Click API request timeout")
            return {
                'error_code': -1,
                'error_note': 'Request timeout: Click API did not respond in time',
                'invoice_id': None,
                'invoice_url': None
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Click API connection error: {str(e)}")
            return {
                'error_code': -1,
                'error_note': f'Connection error: Could not reach Click API - {str(e)}',
                'invoice_id': None,
                'invoice_url': None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Click API request exception: {str(e)}")
            return {
                'error_code': -1,
                'error_note': f'Request failed: {str(e)}',
                'invoice_id': None,
                'invoice_url': None
            }
        except Exception as e:
            logger.error(f"Unexpected error creating invoice: {str(e)}", exc_info=True)
            return {
                'error_code': -9,
                'error_note': f'Unexpected error: {str(e)}',
                'invoice_id': None,
                'invoice_url': None
            }
    
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
        """Prepare payment data for Click by creating invoice
        Returns payment data with payment_url that should be used to redirect user to payment page
        """
        # Ensure transaction has merchant_trans_id
        if not transaction.merchant_trans_id:
            transaction.merchant_trans_id = str(transaction.id)
            transaction.save()
        
        # Get user phone number from transaction user - format for Click (998XXXXXXXXX)
        phone_number = None
        if transaction.user and hasattr(transaction.user, 'phone'):
            phone_raw = transaction.user.phone
            if phone_raw:
                # Remove any non-digit characters and ensure format is correct (Click requires 998XXXXXXXXX format)
                phone_clean = ''.join(filter(str.isdigit, str(phone_raw)))
                if phone_clean and len(phone_clean) >= 9:
                    # If starts with 998, use as is, otherwise add 998 prefix
                    if phone_clean.startswith('998'):
                        phone_number = phone_clean
                    elif phone_clean.startswith('9'):
                        phone_number = '998' + phone_clean
                    else:
                        phone_number = '998' + phone_clean[-9:]  # Take last 9 digits and add 998
                else:
                    logger.warning(f"Invalid phone number format for user {transaction.user.id}: {phone_raw}")
        
        # Get service_id as integer
        try:
            service_id_int = int(self.service_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid service_id: {self.service_id}")
            return {
                'error_code': -1,
                'error_note': f'Invalid service_id: {self.service_id}',
                'payment_url': None
            }
        
        # If phone number is missing, try to use test phone number or create payment URL directly
        # Note: Click requires phone_number for invoice creation, but some services allow direct payment URLs
        if not phone_number:
            logger.warning(f"No valid phone number found for user {transaction.user.id if transaction.user else 'unknown'}")
            
            # Try to create invoice with a test phone number (Click may accept this for testing)
            # Test phone number: 998901234567 (Click test number)
            test_phone = '998901234567'
            logger.info(f"Attempting invoice creation with test phone number: {test_phone}")
            
            invoice_result_test = self.create_invoice(
                service_id=service_id_int,
                amount=float(transaction.amount),
                phone_number=test_phone,
                merchant_trans_id=str(transaction.id)
            )
            
            invoice_error_code_test = invoice_result_test.get('error_code')
            if invoice_error_code_test is not None:
                try:
                    invoice_error_code_test = int(invoice_error_code_test)
                except (ValueError, TypeError):
                    invoice_error_code_test = -1
            
            if invoice_error_code_test == 0:
                # Invoice created with test phone number
                invoice_id = invoice_result_test.get('invoice_id')
                payment_url = invoice_result_test.get('invoice_url') or invoice_result_test.get('payment_url')
                if not payment_url:
                    payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}"
                logger.info(f"Invoice created with test phone, payment URL: {payment_url}")
                return {
                    'error_code': 0,
                    'error_note': 'Success (invoice created with test phone number)',
                    'payment_url': payment_url,
                    'invoice_id': invoice_id,
                    'merchant_trans_id': str(transaction.id),
                    'amount': float(transaction.amount),
                    'service_id': service_id_int,
                    'warning': 'Invoice created with test phone number (998901234567). User should use their actual Click-registered phone number.'
                }
            
            # If test phone also fails, cannot proceed without invoice
            test_error_note = invoice_result_test.get('error_note') or invoice_result_test.get('error') or 'Failed to create invoice with test phone'
            logger.error("Invoice creation with test phone also failed. Cannot proceed without invoice.")
            logger.error(f"Test invoice error: {invoice_error_code_test} - {test_error_note}")
            logger.error(f"IMPORTANT: Invoice creation is REQUIRED for Click payments. User phone number is missing.")
            logger.error(f"IMPORTANT: User must provide a valid phone number that is registered in Click system.")
            logger.error(f"IMPORTANT: Ensure callback URLs are configured in Click merchant panel (merchant.click.uz)")
            logger.error(f"Callback URLs should be:")
            logger.error(f"  Prepare: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/")
            logger.error(f"  Complete: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/")
            
            # Return error - cannot proceed without invoice
            return {
                'error_code': invoice_error_code_test if invoice_error_code_test != -1 else -1,
                'error_note': f'Invoice yaratib bo\'lmadi. User\'ning telefon raqami kerak va u Click tizimida ro\'yxatdan o\'tgan bo\'lishi kerak. Xatolik: {test_error_note}',
                'payment_url': None,  # No payment URL without invoice
                'invoice_id': None,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int,
                'details': invoice_result_test,
                'user_message': 'To\'lov amalga oshirilmadi. Iltimos, telefon raqamingizni kiriting va u Click tizimida ro\'yxatdan o\'tgan bo\'lishi kerak.'
            }
        
        # Create invoice via Click API (recommended method)
        try:
            service_id_int = int(self.service_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid service_id: {self.service_id}")
            return {
                'error_code': -1,
                'error_note': f'Invalid service_id: {self.service_id}',
                'payment_url': None
            }
        
        # Create invoice via Click API
        invoice_result = self.create_invoice(
            service_id=service_id_int,
            amount=float(transaction.amount),
            phone_number=phone_number,
            merchant_trans_id=str(transaction.id)
        )
        
        logger.info(f"Invoice creation result: {invoice_result}")
        
        # Check if invoice was created successfully
        invoice_error_code = invoice_result.get('error_code')
        
        # Convert error_code to int for comparison
        if invoice_error_code is not None:
            try:
                invoice_error_code = int(invoice_error_code)
            except (ValueError, TypeError):
                invoice_error_code = -1
        
        if invoice_error_code == 0:
            # Invoice created successfully - use invoice_url or payment_url from response
            invoice_id = invoice_result.get('invoice_id')
            payment_url = invoice_result.get('invoice_url') or invoice_result.get('payment_url') or invoice_result.get('url')
            
            # If no payment URL in response, construct it manually based on Click documentation
            # Click payment URL format with invoice: https://my.click.uz/services/pay?service_id={service_id}&merchant_trans_id={merchant_trans_id}&invoice_id={invoice_id}
            # Or without invoice_id: https://my.click.uz/services/pay?service_id={service_id}&merchant_trans_id={merchant_trans_id}
            if not payment_url:
                if invoice_id:
                    payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}&invoice_id={invoice_id}"
                else:
                    payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}"
                logger.info(f"Constructed payment URL manually: {payment_url}")
            
            logger.info(f"Payment URL from invoice (success): {payment_url}, invoice_id: {invoice_id}")
            
            return {
                'error_code': 0,
                'error_note': 'Success',
                'payment_url': payment_url,
                'invoice_id': invoice_id,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int
            }
        else:
            # Invoice creation failed - cannot proceed without invoice
            error_note = invoice_result.get('error_note') or invoice_result.get('error') or invoice_result.get('error_msg') or 'Failed to create invoice'
            logger.error(f"Invoice creation failed: {invoice_error_code} - {error_note}")
            logger.error(f"Invoice creation is REQUIRED for Click payments. Cannot proceed without invoice.")
            logger.error(f"User phone number: {phone_number}, Transaction ID: {transaction.id}")
            logger.error(f"IMPORTANT: User must register their phone number ({phone_number}) in Click system before making payments.")
            logger.error(f"IMPORTANT: Ensure callback URLs are configured in Click merchant panel (merchant.click.uz)")
            logger.error(f"Callback URLs should be:")
            logger.error(f"  Prepare: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/")
            logger.error(f"  Complete: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/")
            
            # Return error - invoice creation failed, cannot proceed
            # Frontend should display error message to user
            return {
                'error_code': invoice_error_code if invoice_error_code != -1 else -514,  # Return actual error code or -514 (user not registered)
                'error_note': f'Invoice yaratib bo\'lmadi: {error_note}. User\'ning telefon raqami ({phone_number}) Click tizimida ro\'yxatdan o\'tgan bo\'lishi kerak.',
                'payment_url': None,  # No payment URL without invoice
                'invoice_id': None,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int,
                'details': invoice_result,
                'user_message': f'To\'lov amalga oshirilmadi. Iltimos, telefon raqamingizni ({phone_number}) Click tizimida ro\'yxatdan o\'tkazing. Xatolik: {error_note}'
            }
    
    def handle_prepare(self, data):
        """Handle Click prepare request
        According to Click API documentation:
        sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
        """
        try:
            click_trans_id = data.get('click_trans_id')
            service_id = data.get('service_id')
            merchant_trans_id = data.get('merchant_trans_id')
            amount = data.get('amount')
            action = data.get('action')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            # Verify signature - order is important!
            # sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
            expected_sign = self.generate_signature(
                click_trans_id, service_id, merchant_trans_id, amount, action, sign_time
            )
            
            if sign_string != expected_sign:
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction - merchant_trans_id is UUID string, need to convert
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except Transaction.DoesNotExist:
                # Try to find by merchant_trans_id field if UUID conversion fails
                try:
                    transaction = Transaction.objects.get(merchant_trans_id=merchant_trans_id)
                except Transaction.DoesNotExist:
                    return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Check amount - compare as floats to avoid precision issues
            if abs(float(amount) - float(transaction.amount)) > 0.01:
                return {'error': -2, 'error_note': f'Invalid amount: expected {transaction.amount}, got {amount}'}
            
            # Save Click transaction ID and prepare status
            transaction.click_trans_id = click_trans_id
            transaction.merchant_trans_id = str(transaction.id) if not transaction.merchant_trans_id else transaction.merchant_trans_id
            transaction.status = 'pending'  # Still pending until complete
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': str(transaction.id),
                'merchant_prepare_id': str(transaction.id),
                'error': 0,
                'error_note': 'Success'
            }
            
        except Exception as e:
            return {'error': -9, 'error_note': str(e)}
    
    def handle_complete(self, data):
        """Handle Click complete request
        According to Click API documentation:
        sign_string = md5(click_trans_id + merchant_trans_id + merchant_prepare_id + error + sign_time + secret_key)
        """
        try:
            click_trans_id = data.get('click_trans_id')
            merchant_trans_id = data.get('merchant_trans_id')
            merchant_prepare_id = data.get('merchant_prepare_id')
            error = data.get('error')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            # Verify signature for complete request
            # sign_string = md5(click_trans_id + merchant_trans_id + merchant_prepare_id + error + sign_time + secret_key)
            expected_sign = self.generate_signature(
                click_trans_id, merchant_trans_id, merchant_prepare_id, error, sign_time
            )
            
            if sign_string and sign_string != expected_sign:
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except Transaction.DoesNotExist:
                # Try to find by merchant_trans_id field
                try:
                    transaction = Transaction.objects.get(merchant_trans_id=merchant_trans_id)
                except Transaction.DoesNotExist:
                    return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Update transaction status based on error code
            if error == 0:
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.click_paydoc_id = data.get('click_paydoc_id', transaction.click_paydoc_id or '')
            else:
                transaction.status = 'failed'
            
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': str(transaction.id),
                'merchant_confirm_id': str(transaction.id),
                'error': 0,
                'error_note': 'Success'
            }
            
        except Transaction.DoesNotExist:
            return {'error': -5, 'error_note': 'Transaction not found'}
        except Exception as e:
            import traceback
            return {'error': -9, 'error_note': f'{str(e)}\n{traceback.format_exc()}'}