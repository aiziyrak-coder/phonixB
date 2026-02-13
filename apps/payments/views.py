from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
import json
from django.http import JsonResponse
from django.views import View
import logging

from .models import Transaction
from .serializers import TransactionSerializer, CreateTransactionSerializer
from .services import ClickPaymentService
from .payme_service import PaymeService, PaymeError

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transactions"""
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use CreateTransactionSerializer for create action"""
        if self.action == 'create':
            return CreateTransactionSerializer
        return TransactionSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        """Filter transactions by user"""
        if self.request.user.is_superuser:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user automatically when creating transaction"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to return full transaction data including ID"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Return full transaction data using TransactionSerializer
        transaction = serializer.instance
        full_serializer = TransactionSerializer(transaction, context=self.get_serializer_context())
        return Response(full_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def prepare_payment(self, request, pk=None):
        """Prepare payment for transaction"""
        transaction = self.get_object()
        service = ClickPaymentService()
        result = service.prepare_payment(transaction)
        logger.info(f"Prepare payment result: {result}")
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def check_status(self, request, pk=None):
        """Check payment status"""
        transaction = self.get_object()
        service = ClickPaymentService()
        
        if transaction.click_paydoc_id:
            result = service.check_payment_status(service.service_id, transaction.click_paydoc_id)
        else:
            result = {'error': -1, 'error_note': 'Payment not completed yet'}
        
        logger.info(f"Check status result: {result}")
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for transaction - creates invoice and returns payment URL
        
        Query params:
            provider: 'click' or 'payme' (default: 'click')
        """
        transaction = self.get_object()
        provider = request.query_params.get('provider', 'click').lower()
        
        try:
            # Select payment provider
            if provider == 'payme':
                service = PaymeService()
                # Generate Payme payment link
                payment_result = service.generate_pay_link(transaction)
                # Mark transaction as payme
                transaction.payment_provider = 'payme'
                transaction.save()
                
                # Return Payme payment URL
                return Response({
                    'success': True,
                    'payment_url': payment_result['payment_url'],
                    'provider': 'payme',
                    'merchant_id': payment_result['merchant_id'],
                    'merchant_trans_id': str(transaction.id),
                    'amount': float(transaction.amount),
                    'currency': transaction.currency,
                    'error_code': 0,
                    'error_note': 'Success'
                }, status=status.HTTP_200_OK)
            
            else:  # Default to Click
                service = ClickPaymentService()
                # Mark transaction as click
                transaction.payment_provider = 'click'
                transaction.save()
            
            # Prepare payment - creates payment URL directly WITHOUT invoice (OSON TO'LOV)
            # use_invoice=False - invoice yaratmasdan, to'g'ridan-to'g'ri payment URL yaratadi
            payment_result = service.prepare_payment(transaction, use_invoice=False)
            logger.info(f"Payment preparation result: {payment_result}")
            logger.info(f"Payment result type - error_code: {type(payment_result.get('error_code'))}, value: {payment_result.get('error_code')}, payment_url: {payment_result.get('payment_url')}")
            
            # Check if payment was prepared successfully
            # Check error_code explicitly - 0 or None means success
            error_code = payment_result.get('error_code')
            payment_url = payment_result.get('payment_url')
            
            # Convert error_code to int for comparison (in case it's a string)
            error_code_int = None
            if error_code is not None:
                try:
                    error_code_int = int(error_code)
                except (ValueError, TypeError):
                    error_code_int = None
            
            # Check if payment was successful - payment_url existence is the primary indicator
            # Even if invoice creation failed, if we have payment_url, consider it success
            has_payment_url = payment_url is not None and payment_url != ''
            is_error_code_success = (error_code_int == 0 or error_code is None)
            
            # If payment_url exists, consider it success (even if invoice creation had issues)
            is_success = has_payment_url and (is_error_code_success or payment_result.get('warning'))
            
            logger.info(f"Payment success check - error_code: {error_code}, error_code_int: {error_code_int}, payment_url exists: {has_payment_url}, is_success: {is_success}")
            logger.info(f"Payment result keys: {list(payment_result.keys())}")
            logger.info(f"Payment URL value: {payment_url}")
            
            if is_success or has_payment_url:
                # Payment prepared successfully (even if invoice creation had warnings)
                invoice_id = payment_result.get('invoice_id')
                warning = payment_result.get('warning')
                
                logger.info(f"Payment URL created successfully: {payment_url}")
                if warning:
                    logger.warning(f"Payment URL created with warning: {warning}")
                
                return Response({
                    'success': True,
                    'payment_url': payment_url,
                    'invoice_id': invoice_id,
                    'merchant_trans_id': str(transaction.id),
                    'amount': float(transaction.amount),
                    'currency': transaction.currency,
                    'error_code': 0,
                    'error_note': payment_result.get('error_note', 'Success'),
                    'warning': warning  # Include warning if exists
                }, status=status.HTTP_200_OK)
            else:
                # Payment preparation failed - no payment URL
                final_error_code = error_code_int if error_code_int is not None else (error_code if error_code is not None else -1)
                error_note = payment_result.get('error_note') or payment_result.get('error') or payment_result.get('error_msg') or 'Payment preparation failed'
                logger.error(f"Failed to prepare payment. Error code: {final_error_code}, Error note: {error_note}, Payment URL: {payment_url}, Full response: {payment_result}")
                
                # Don't expose full payment_result details to user
                logger.error(f"Payment preparation failed. Full response: {payment_result}")
                return Response({
                    'success': False,
                    'error_code': final_error_code,
                    'error': error_note,
                    'error_note': error_note,
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}", exc_info=True)
            # Don't expose internal error details to user
            return Response({
                'success': False,
                'error_code': -9,
                'error': 'To\'lovni amalga oshirishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
                'error_note': 'To\'lovni amalga oshirishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def click_prepare_view(request):
    """Handle Click prepare requests (callback from Click after user initiates payment)"""
    # Handle GET requests (for URL validation by Click merchant panel)
    if request.method == 'GET':
        logger.info(f"Click prepare GET request received (URL validation) from {request.META.get('REMOTE_ADDR', 'unknown')}")
        return JsonResponse({'status': 'ok', 'message': 'Prepare endpoint is active'}, status=200)
    
    # Handle POST requests (actual callbacks)
    if request.method != 'POST':
        return JsonResponse({'error': -1, 'error_note': 'Method not allowed'}, status=405)
    
    try:
        # Log request details for debugging
        logger.info(f"Click prepare POST request received from {request.META.get('REMOTE_ADDR', 'unknown')}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Request body: {request.body[:500] if request.body else 'Empty'}")
        
        # Click sends data as form data (application/x-www-form-urlencoded) or JSON
        data = {}
        if request.content_type and 'application/json' in request.content_type:
            import json
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
                logger.info(f"Parsed JSON data: {data}")
        else:
            # Form data (Click typically sends form data)
            if request.POST:
                data = request.POST.dict()
                logger.info(f"Parsed form data: {data}")
            elif request.body:
                # Try to parse as form-encoded
                from urllib.parse import parse_qs
                parsed = parse_qs(request.body.decode('utf-8'))
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                logger.info(f"Parsed form-encoded data: {data}")
        
        if not data:
            logger.warning("No data received in Click prepare request")
            return JsonResponse({'error': -1, 'error_note': 'No data provided'}, status=400)
        
        logger.info(f"Click prepare request data: {data}")
        service = ClickPaymentService()
        result = service.handle_prepare(data)
        logger.info(f"Click prepare result: {result}")
        
        # Return response in format Click expects
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error in click_prepare_view: {str(e)}", exc_info=True)
        return JsonResponse({'error': -9, 'error_note': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def click_complete_view(request):
    """Handle Click complete requests (callback from Click after payment is completed)"""
    # Handle GET requests (for URL validation by Click merchant panel)
    if request.method == 'GET':
        logger.info(f"Click complete GET request received (URL validation) from {request.META.get('REMOTE_ADDR', 'unknown')}")
        return JsonResponse({'status': 'ok', 'message': 'Complete endpoint is active'}, status=200)
    
    # Handle POST requests (actual callbacks)
    if request.method != 'POST':
        return JsonResponse({'error': -1, 'error_note': 'Method not allowed'}, status=405)
    
    try:
        # Log request details for debugging
        logger.info(f"Click complete POST request received from {request.META.get('REMOTE_ADDR', 'unknown')}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Request body: {request.body[:500] if request.body else 'Empty'}")
        
        # Click sends data as form data (application/x-www-form-urlencoded) or JSON
        data = {}
        if request.content_type and 'application/json' in request.content_type:
            import json
            if request.body:
                data = json.loads(request.body.decode('utf-8'))
                logger.info(f"Parsed JSON data: {data}")
        else:
            # Form data (Click typically sends form data)
            if request.POST:
                data = request.POST.dict()
                logger.info(f"Parsed form data: {data}")
            elif request.body:
                # Try to parse as form-encoded
                from urllib.parse import parse_qs
                parsed = parse_qs(request.body.decode('utf-8'))
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
                logger.info(f"Parsed form-encoded data: {data}")
        
        if not data:
            logger.warning("No data received in Click complete request")
            return JsonResponse({'error': -1, 'error_note': 'No data provided'}, status=400)
        
        logger.info(f"Click complete request data: {data}")
        service = ClickPaymentService()
        result = service.handle_complete(data)
        logger.info(f"Click complete result: {result}")
        
        # Return response in format Click expects
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error in click_complete_view: {str(e)}", exc_info=True)
        return JsonResponse({'error': -9, 'error_note': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ClickPaymentView(View):
    """Handle Click payment system callbacks"""
    
    def post(self, request):
        """Handle Click payment callbacks"""
        try:
            # Get JSON data from request
            data = json.loads(request.body)
            logger.info(f"Click payment callback received: {data}")
            
            # Initialize Click service
            click_service = ClickPaymentService()
            
            # Process payment based on callback data
            # This is where you would update your transaction records
            # based on the payment status from Click
            
            return JsonResponse({
                'success': True,
                'message': 'Payment callback processed successfully'
            })
            
        except Exception as e:
            logger.error(f"Error processing Click payment callback: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def payme_callback_view(request):
    """Handle Payme JSON-RPC callbacks
    
    Payme uses JSON-RPC 2.0 protocol for all callbacks
    """
    try:
        # Log request details
        logger.info(f"Payme callback received from {request.META.get('REMOTE_ADDR', 'unknown')}")
        logger.info(f"Authorization: {request.META.get('HTTP_AUTHORIZATION', 'N/A')[:20]}...")
        
        # Parse JSON-RPC request
        try:
            data = json.loads(request.body.decode('utf-8'))
            logger.info(f"Payme request data: {data}")
        except json.JSONDecodeError:
            return JsonResponse({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32700,
                    'message': 'Parse error'
                },
                'id': None
            })
        
        # Extract JSON-RPC fields
        jsonrpc_version = data.get('jsonrpc')
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        # Validate JSON-RPC version
        if jsonrpc_version != '2.0':
            return JsonResponse({
                'jsonrpc': '2.0',
                'error': {
                    'code': -32600,
                    'message': 'Invalid Request'
                },
                'id': request_id
            })
        
        # Initialize Payme service
        service = PaymeService()
        
        # Check authorization
        try:
            authorization = request.META.get('HTTP_AUTHORIZATION', '')
            service.check_authorization(authorization)
        except PaymeError as e:
            return JsonResponse({
                'jsonrpc': '2.0',
                'error': e.to_dict(),
                'id': request_id
            })
        
        # Handle method
        try:
            if method == 'CheckPerformTransaction':
                result = service.check_perform_transaction(params)
            elif method == 'CreateTransaction':
                result = service.create_transaction(params)
            elif method == 'PerformTransaction':
                result = service.perform_transaction(params)
            elif method == 'CancelTransaction':
                result = service.cancel_transaction(params)
            elif method == 'CheckTransaction':
                result = service.check_transaction(params)
            elif method == 'GetStatement':
                result = service.get_statement(params)
            else:
                raise PaymeError(-32601, f"Method not found: {method}")
            
            logger.info(f"Payme {method} successful: {result}")
            
            return JsonResponse({
                'jsonrpc': '2.0',
                'result': result,
                'id': request_id
            })
            
        except PaymeError as e:
            logger.error(f"Payme error in {method}: {e.message}")
            return JsonResponse({
                'jsonrpc': '2.0',
                'error': e.to_dict(),
                'id': request_id
            })
        
    except Exception as e:
        logger.error(f"Unexpected error in payme_callback_view: {str(e)}", exc_info=True)
        return JsonResponse({
            'jsonrpc': '2.0',
            'error': {
                'code': -31008,
                'message': 'Internal server error'
            },
            'id': request.id if hasattr(request, 'id') else None
        }, status=500)