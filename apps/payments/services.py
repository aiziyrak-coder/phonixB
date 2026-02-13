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
        secret_key_raw = settings.CLICK_SECRET_KEY or '08CIKUoBemAxyM'
        merchant_user_id_raw = settings.CLICK_MERCHANT_USER_ID or '72021'
        
        # Convert to string and strip whitespace
        self.merchant_id = str(merchant_id_raw).strip()
        self.service_id = str(service_id_raw).strip()
        self.secret_key = str(secret_key_raw).strip()
        self.merchant_user_id = str(merchant_user_id_raw).strip()
        self.api_url = "https://api.click.uz/v2/merchant"
        
        # Service-specific secret keys (Click'dan kelgan service_id ga mos)
        # Service 82154 uchun (Ilmiyfaoliyat.uz - Click bergan kalitlar)
        # Service 82155 uchun (Phoenix publication - Click bergan kalitlar)
        # Service 89248 uchun (yangi PHOENIX service)
        self.service_secret_keys = {
            '82154': getattr(settings, 'CLICK_SERVICE_82154_SECRET_KEY', 'XZC6u3JBBh'),  # Ilmiyfaoliyat.uz
            '82155': getattr(settings, 'CLICK_SERVICE_82155_SECRET_KEY', 'icHbYQnMBx'),  # Phoenix publication
            '89248': getattr(settings, 'CLICK_SERVICE_89248_SECRET_KEY', '08CIKUoBemAxyM'),  # Yangi PHOENIX service
        }
        
        # Default secret key (asosiy service uchun)
        if not self.secret_key:
            logger.error("CLICK_SECRET_KEY is empty, using default")
            self.secret_key = '08CIKUoBemAxyM'
        
        # Validate that all required fields are set (non-empty after strip)
        if not self.service_id:
            logger.error("CLICK_SERVICE_ID is empty, using default: 89248")
            self.service_id = '89248'
        if not self.merchant_user_id:
            logger.error("CLICK_MERCHANT_USER_ID is empty, using default: 72021")
            self.merchant_user_id = '72021'
        if not self.merchant_id:
            logger.error("CLICK_MERCHANT_ID is empty, using default: 45730")
            self.merchant_id = '45730'
        
        logger.info(f"ClickPaymentService initialized - service_id: {self.service_id}, merchant_user_id: {self.merchant_user_id}, merchant_id: {self.merchant_id}")
    
    def get_secret_key_for_service(self, service_id):
        """Get secret key for specific service_id
        
        Click'dan kelgan service_id ga mos secret key qaytaradi
        """
        service_id_str = str(service_id).strip()
        if service_id_str in self.service_secret_keys:
            return self.service_secret_keys[service_id_str]
        # Default secret key
        return self.secret_key
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{timestamp}"
    
    def generate_signature(self, *args):
        """Generate signature for Click request
        According to Click API: sign_string = md5(args + secret_key)
        Uses default secret key
        """
        # Concatenate all arguments as strings
        sign_string = ''.join(str(arg) for arg in args)
        # Append secret key
        sign_string += self.secret_key
        # Generate MD5 hash
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def generate_signature_with_key(self, secret_key, *args):
        """Generate signature with specific secret key
        
        Args:
            secret_key: Secret key to use for this signature
            *args: Arguments to include in signature
        """
        # Concatenate all arguments as strings
        sign_string = ''.join(str(arg) for arg in args)
        # Append secret key
        sign_string += secret_key
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
    
    def create_direct_payment_url(self, transaction, use_invoice=False):
        """Create direct payment URL without invoice (OSON TO'LOV)
        
        Args:
            transaction: Transaction object
            use_invoice: If True, try to create invoice first. If False, create direct URL.
        
        Returns:
            dict with payment_url
        """
        # Ensure transaction has merchant_trans_id
        if not transaction.merchant_trans_id:
            transaction.merchant_trans_id = str(transaction.id)
            transaction.save()
        
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
        
        # If use_invoice is False, create direct payment URL without invoice
        if not use_invoice:
            # Direct payment URL - invoice yaratmasdan
            # Click'da to'g'ridan-to'g'ri payment URL yaratish mumkin
            payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}"
            
            logger.info(f"Direct payment URL created (without invoice): {payment_url}")
            
            return {
                'error_code': 0,
                'error_note': 'Success',
                'payment_url': payment_url,
                'invoice_id': None,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int,
                'direct_payment': True  # Invoice yaratilmadi, to'g'ridan-to'g'ri URL
            }
        
        # If use_invoice is True, try to create invoice (old method)
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
        
        # If phone number is missing, return direct payment URL
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
            
            # If test phone also fails, use direct payment URL (invoice yaratmasdan)
            test_error_note = invoice_result_test.get('error_note') or invoice_result_test.get('error') or 'Failed to create invoice with test phone'
            logger.warning(f"Invoice creation failed: {test_error_note}")
            logger.info("Using direct payment URL instead (without invoice)")
            
            # Create direct payment URL without invoice
            payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}"
            
            return {
                'error_code': 0,
                'error_note': 'Success (direct payment URL, invoice yaratilmadi)',
                'payment_url': payment_url,
                'invoice_id': None,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int,
                'direct_payment': True,
                'warning': 'Invoice yaratilmadi, lekin to\'g\'ridan-to\'g\'ri to\'lov URL yaratildi. User Click sahifasida karta ma\'lumotlarini kiritishi mumkin.'
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
            
            # Invoice creation failed - use direct payment URL instead
            logger.warning(f"Invoice creation failed: {invoice_error_code} - {error_note}")
            logger.info("Using direct payment URL instead (without invoice)")
            
            # Create direct payment URL without invoice
            payment_url = f"https://my.click.uz/services/pay?service_id={service_id_int}&merchant_trans_id={str(transaction.id)}"
            
            return {
                'error_code': 0,
                'error_note': 'Success (direct payment URL, invoice yaratilmadi)',
                'payment_url': payment_url,
                'invoice_id': None,
                'merchant_trans_id': str(transaction.id),
                'amount': float(transaction.amount),
                'service_id': service_id_int,
                'direct_payment': True,
                'warning': f'Invoice yaratilmadi ({error_note}), lekin to\'g\'ridan-to\'g\'ri to\'lov URL yaratildi. User Click sahifasida karta ma\'lumotlarini kiritishi mumkin.'
            }
    
    def prepare_payment(self, transaction, use_invoice=False):
        """Prepare payment data for Click (OSON TO'LOV - invoice yaratmasdan)
        
        Args:
            transaction: Transaction object
            use_invoice: If True, try to create invoice. If False, create direct payment URL (default: False)
        
        Returns:
            dict with payment_url
        """
        return self.create_direct_payment_url(transaction, use_invoice=use_invoice)
    
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
            
            # Get secret key for this specific service_id (Click'dan kelgan)
            service_secret_key = self.get_secret_key_for_service(service_id)
            logger.info(f"Using secret key for service_id={service_id}")
            
            # Verify signature - order is important!
            # If click_paydoc_id exists, include it in signature
            if click_paydoc_id:
                # sign_string = md5(click_trans_id + service_id + click_paydoc_id + merchant_trans_id + amount + action + sign_time + secret_key)
                # Use service-specific secret key
                expected_sign = self.generate_signature_with_key(
                    service_secret_key, click_trans_id, service_id, click_paydoc_id, merchant_trans_id, amount, action, sign_time
                )
                logger.info(f"Prepare signature with click_paydoc_id: click_trans_id={click_trans_id}, service_id={service_id}, click_paydoc_id={click_paydoc_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}")
            else:
                # sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
                # Use service-specific secret key
                expected_sign = self.generate_signature_with_key(
                    service_secret_key, click_trans_id, service_id, merchant_trans_id, amount, action, sign_time
                )
                logger.info(f"Prepare signature without click_paydoc_id: click_trans_id={click_trans_id}, service_id={service_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}")
            
            logger.info(f"Expected signature: {expected_sign}, Received signature: {sign_string}")
            
            if sign_string != expected_sign:
                logger.error(f"Signature mismatch! Expected: {expected_sign}, Got: {sign_string}")
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
            if click_paydoc_id:
                transaction.click_paydoc_id = str(click_paydoc_id)
            transaction.merchant_trans_id = str(transaction.id) if not transaction.merchant_trans_id else transaction.merchant_trans_id
            # Save service_id for complete callback (complete'da service_id kelmaydi)
            transaction.click_service_id = str(service_id)
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
            logger.error(f"Error in handle_prepare: {str(e)}", exc_info=True)
            return {'error': -9, 'error_note': f'Server xatolik: {str(e)}'}
    
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
            
            # Find transaction first to get service_id
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except Transaction.DoesNotExist:
                # Try to find by merchant_trans_id field
                try:
                    transaction = Transaction.objects.get(merchant_trans_id=merchant_trans_id)
                except Transaction.DoesNotExist:
                    return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Get service_id from transaction (saved during prepare) or use default
            # Complete'da service_id kelmaydi, lekin prepare'da saqlangan bo'lishi mumkin
            # Yoki click_trans_id orqali topish mumkin
            # Hozircha default secret key ishlatamiz, lekin agar transaction'da service_id bo'lsa, uni ishlatamiz
            service_id_for_complete = getattr(transaction, 'click_service_id', None) or self.service_id
            
            # Get secret key for this service
            service_secret_key = self.get_secret_key_for_service(service_id_for_complete)
            logger.info(f"Complete: Using secret key for service_id={service_id_for_complete}")
            
            # Verify signature for complete request
            # sign_string = md5(click_trans_id + merchant_trans_id + merchant_prepare_id + error + sign_time + secret_key)
            expected_sign = self.generate_signature_with_key(
                service_secret_key, click_trans_id, merchant_trans_id, merchant_prepare_id, error, sign_time
            )
            
            logger.info(f"Complete signature: Expected={expected_sign}, Received={sign_string}")
            
            if sign_string and sign_string != expected_sign:
                logger.error(f"Complete signature mismatch! Expected: {expected_sign}, Got: {sign_string}")
                return {'error': -1, 'error_note': 'Invalid signature'}
            
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
            logger.error(f"Transaction not found in handle_complete: merchant_trans_id={merchant_trans_id}")
            return {'error': -5, 'error_note': 'Transaction not found'}
        except Exception as e:
            import traceback
            logger.error(f"Error in handle_complete: {str(e)}", exc_info=True)
            return {'error': -9, 'error_note': f'Server xatolik: {str(e)}'}