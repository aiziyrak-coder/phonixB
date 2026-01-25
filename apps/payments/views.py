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
        """Process payment for transaction - creates invoice and returns payment URL"""
        transaction = self.get_object()
        service = ClickPaymentService()
        
        try:
            # Prepare payment - creates payment URL directly
            payment_result = service.prepare_payment(transaction)
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
        logger.info(f"Click prepare GET request received (URL validation)")
        return JsonResponse({'status': 'ok', 'message': 'Prepare endpoint is active'}, status=200)
    
    # Handle POST requests (actual callbacks)
    if request.method != 'POST':
        return JsonResponse({'error': -1, 'error_note': 'Method not allowed'}, status=405)
    
    try:
        # Click sends data as form data or JSON
        if request.content_type and 'application/json' in request.content_type:
            import json
            data = json.loads(request.body) if request.body else {}
        else:
            data = request.POST.dict()
        
        logger.info(f"Click prepare request received: {data}")
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
        logger.info(f"Click complete GET request received (URL validation)")
        return JsonResponse({'status': 'ok', 'message': 'Complete endpoint is active'}, status=200)
    
    # Handle POST requests (actual callbacks)
    if request.method != 'POST':
        return JsonResponse({'error': -1, 'error_note': 'Method not allowed'}, status=405)
    
    try:
        # Click sends data as form data or JSON
        if request.content_type and 'application/json' in request.content_type:
            import json
            data = json.loads(request.body) if request.body else {}
        else:
            data = request.POST.dict()
        
        logger.info(f"Click complete request received: {data}")
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