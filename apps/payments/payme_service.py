"""
Payme Payment Integration Service
https://developer.help.paycom.uz/
"""
import base64
import hashlib
import time
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Transaction

logger = logging.getLogger(__name__)


class PaymeError(Exception):
    """Payme error exception"""
    
    ERRORS = {
        -32504: "Недостаточно привилегий для выполнения метода",
        -31008: "Неизвестная ошибка",
        -31050: "Заказ не найден",
        -31051: "Неверная сумма заказа",
        -31052: "Заказ уже оплачен",
        -31099: "Невозможно выполнить операцию",
    }
    
    def __init__(self, code, message=None, data=None):
        self.code = code
        self.message = message or self.ERRORS.get(code, "Unknown error")
        self.data = data
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert error to Payme JSON-RPC format"""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data:
            error["data"] = self.data
        return error


class PaymeService:
    """Service for Payme payment integration"""
    
    # Payme transaction states
    STATE_CREATED = 1
    STATE_COMPLETED = 2
    STATE_CANCELLED = -1
    STATE_CANCELLED_AFTER_COMPLETE = -2
    
    # Payme reasons for cancellation
    REASON_RECEIVERS_NOT_FOUND = 1
    REASON_PROCESSING_EXECUTION_FAILED = 2
    REASON_EXECUTION_FAILED = 3
    REASON_CANCELLED_BY_TIMEOUT = 4
    REASON_FUND_RETURNED = 5
    REASON_UNKNOWN = 10
    
    def __init__(self):
        # Load from settings
        self.merchant_id = getattr(settings, 'PAYME_MERCHANT_ID', '')
        self.merchant_key = getattr(settings, 'PAYME_MERCHANT_KEY', '')
        self.test_key = getattr(settings, 'PAYME_TEST_KEY', '')
        self.endpoint = getattr(settings, 'PAYME_ENDPOINT', 'https://checkout.paycom.uz')
        self.is_test = getattr(settings, 'PAYME_IS_TEST', True)
        
        # Validate settings
        if not self.merchant_id or not self.merchant_key:
            logger.warning("Payme merchant credentials not configured!")
        
        logger.info(f"PaymeService initialized - merchant_id: {self.merchant_id}, is_test: {self.is_test}")
    
    def check_authorization(self, authorization_header):
        """Check authorization header from Payme
        
        Payme sends Basic Auth: base64(merchant_id:key)
        """
        if not authorization_header:
            raise PaymeError(-32504, "Authorization header missing")
        
        try:
            # Extract credentials from Authorization header
            # Format: "Basic base64(merchant_id:key)"
            auth_type, credentials = authorization_header.split(' ')
            
            if auth_type.lower() != 'basic':
                raise PaymeError(-32504, "Invalid authorization type")
            
            # Decode base64
            decoded = base64.b64decode(credentials).decode('utf-8')
            merchant_id, key = decoded.split(':')
            
            # Verify merchant_id and key
            expected_key = self.test_key if self.is_test else self.merchant_key
            
            if merchant_id != self.merchant_id or key != expected_key:
                logger.error(f"Invalid credentials: merchant_id={merchant_id}, key={key[:5]}...")
                raise PaymeError(-32504, "Invalid credentials")
            
            return True
            
        except (ValueError, UnicodeDecodeError) as e:
            logger.error(f"Authorization parsing error: {str(e)}")
            raise PaymeError(-32504, "Invalid authorization format")
    
    def generate_pay_link(self, transaction):
        """Generate Payme payment link
        
        Args:
            transaction: Transaction object
        
        Returns:
            dict: Payment link and merchant data
        """
        # Amount in tiyin (1 UZS = 100 tiyin)
        amount_tiyin = int(float(transaction.amount) * 100)
        
        # Encode merchant data
        # m - merchant_id
        # ac - account (transaction_id)
        # a - amount in tiyin
        merchant_data = f"m={self.merchant_id};ac.transaction_id={transaction.id};a={amount_tiyin}"
        
        # Base64 encode
        encoded_data = base64.b64encode(merchant_data.encode('utf-8')).decode('utf-8')
        
        # Generate payment URL
        payment_url = f"{self.endpoint}/{encoded_data}"
        
        logger.info(f"Generated Payme payment link for transaction {transaction.id}: {payment_url}")
        
        return {
            'payment_url': payment_url,
            'merchant_id': self.merchant_id,
            'amount': amount_tiyin,
            'transaction_id': str(transaction.id)
        }
    
    def check_perform_transaction(self, params):
        """CheckPerformTransaction method
        
        Payme calls this before creating transaction to check if it's possible
        """
        # Extract account from params
        account = params.get('account', {})
        transaction_id = account.get('transaction_id')
        amount = params.get('amount')
        
        if not transaction_id:
            raise PaymeError(-31050, "Transaction ID not provided")
        
        try:
            transaction = Transaction.objects.get(id=transaction_id)
        except Transaction.DoesNotExist:
            raise PaymeError(-31050, "Transaction not found")
        
        # Check amount (amount is in tiyin, convert to UZS)
        expected_amount = int(float(transaction.amount) * 100)
        if amount != expected_amount:
            raise PaymeError(-31051, f"Invalid amount. Expected: {expected_amount}, got: {amount}")
        
        # Check if already paid
        if transaction.status == 'completed':
            raise PaymeError(-31052, "Transaction already completed")
        
        return {
            'allow': True
        }
    
    def create_transaction(self, params):
        """CreateTransaction method
        
        Payme creates transaction before payment
        """
        # Extract params
        transaction_id = params.get('id')  # Payme transaction ID
        time_param = params.get('time')
        account = params.get('account', {})
        amount = params.get('amount')
        
        merchant_trans_id = account.get('transaction_id')
        
        if not merchant_trans_id:
            raise PaymeError(-31050, "Merchant transaction ID not provided")
        
        try:
            transaction = Transaction.objects.get(id=merchant_trans_id)
        except Transaction.DoesNotExist:
            raise PaymeError(-31050, "Transaction not found")
        
        # Check amount
        expected_amount = int(float(transaction.amount) * 100)
        if amount != expected_amount:
            raise PaymeError(-31051, f"Invalid amount")
        
        # Check if already has payme transaction
        if hasattr(transaction, 'payme_trans_id') and transaction.payme_trans_id:
            # Transaction already created, return existing
            return {
                'create_time': int(transaction.created_at.timestamp() * 1000),
                'transaction': str(transaction.id),
                'state': self.STATE_CREATED
            }
        
        # Save Payme transaction ID
        transaction.payme_trans_id = transaction_id
        transaction.payme_time = time_param
        transaction.status = 'pending'
        transaction.save()
        
        logger.info(f"Payme transaction created: {transaction_id} for {transaction.id}")
        
        return {
            'create_time': int(transaction.created_at.timestamp() * 1000),
            'transaction': str(transaction.id),
            'state': self.STATE_CREATED
        }
    
    def perform_transaction(self, params):
        """PerformTransaction method
        
        Payme confirms payment
        """
        payme_trans_id = params.get('id')
        
        # Find transaction by payme_trans_id
        try:
            transaction = Transaction.objects.get(payme_trans_id=payme_trans_id)
        except Transaction.DoesNotExist:
            raise PaymeError(-31050, "Transaction not found")
        
        # Check if already completed
        if transaction.status == 'completed':
            return {
                'transaction': str(transaction.id),
                'perform_time': int(transaction.completed_at.timestamp() * 1000) if transaction.completed_at else int(time.time() * 1000),
                'state': self.STATE_COMPLETED
            }
        
        # Complete transaction
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        logger.info(f"Payme transaction performed: {payme_trans_id} for {transaction.id}")
        
        return {
            'transaction': str(transaction.id),
            'perform_time': int(transaction.completed_at.timestamp() * 1000),
            'state': self.STATE_COMPLETED
        }
    
    def cancel_transaction(self, params):
        """CancelTransaction method
        
        Payme cancels transaction
        """
        payme_trans_id = params.get('id')
        reason = params.get('reason')
        
        try:
            transaction = Transaction.objects.get(payme_trans_id=payme_trans_id)
        except Transaction.DoesNotExist:
            raise PaymeError(-31050, "Transaction not found")
        
        # Determine state based on current status
        if transaction.status == 'completed':
            state = self.STATE_CANCELLED_AFTER_COMPLETE
        else:
            state = self.STATE_CANCELLED
        
        # Cancel transaction
        transaction.status = 'cancelled'
        transaction.save()
        
        logger.info(f"Payme transaction cancelled: {payme_trans_id}, reason: {reason}")
        
        return {
            'transaction': str(transaction.id),
            'cancel_time': int(time.time() * 1000),
            'state': state
        }
    
    def check_transaction(self, params):
        """CheckTransaction method
        
        Payme checks transaction status
        """
        payme_trans_id = params.get('id')
        
        try:
            transaction = Transaction.objects.get(payme_trans_id=payme_trans_id)
        except Transaction.DoesNotExist:
            raise PaymeError(-31050, "Transaction not found")
        
        # Determine state
        if transaction.status == 'completed':
            state = self.STATE_COMPLETED
        elif transaction.status == 'cancelled':
            state = self.STATE_CANCELLED
        else:
            state = self.STATE_CREATED
        
        result = {
            'create_time': int(transaction.created_at.timestamp() * 1000),
            'transaction': str(transaction.id),
            'state': state
        }
        
        if transaction.status == 'completed' and transaction.completed_at:
            result['perform_time'] = int(transaction.completed_at.timestamp() * 1000)
        
        if transaction.status == 'cancelled':
            result['cancel_time'] = int(timezone.now().timestamp() * 1000)
            result['reason'] = self.REASON_UNKNOWN
        
        return result
    
    def get_statement(self, params):
        """GetStatement method
        
        Payme requests statement of transactions
        """
        from_time = params.get('from')
        to_time = params.get('to')
        
        # Convert milliseconds to datetime
        from_dt = timezone.datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
        to_dt = timezone.datetime.fromtimestamp(to_time / 1000, tz=timezone.utc)
        
        # Get transactions in time range
        transactions = Transaction.objects.filter(
            created_at__gte=from_dt,
            created_at__lte=to_dt,
            payme_trans_id__isnull=False
        )
        
        result = []
        for transaction in transactions:
            # Determine state
            if transaction.status == 'completed':
                state = self.STATE_COMPLETED
            elif transaction.status == 'cancelled':
                state = self.STATE_CANCELLED
            else:
                state = self.STATE_CREATED
            
            item = {
                'id': transaction.payme_trans_id,
                'time': int(transaction.created_at.timestamp() * 1000),
                'amount': int(float(transaction.amount) * 100),
                'account': {
                    'transaction_id': str(transaction.id)
                },
                'create_time': int(transaction.created_at.timestamp() * 1000),
                'transaction': str(transaction.id),
                'state': state
            }
            
            if transaction.status == 'completed' and transaction.completed_at:
                item['perform_time'] = int(transaction.completed_at.timestamp() * 1000)
            
            if transaction.status == 'cancelled':
                item['cancel_time'] = int(timezone.now().timestamp() * 1000)
                item['reason'] = self.REASON_UNKNOWN
            
            result.append(item)
        
        return {
            'transactions': result
        }
