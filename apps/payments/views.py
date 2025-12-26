from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
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
    
    def get_queryset(self):
        """Filter transactions by user"""
        if self.request.user.is_superuser:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)
    
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


@api_view(['POST'])
@permission_classes([AllowAny])
def click_prepare_view(request):
    """Handle Click prepare requests"""
    logger.info(f"Click prepare request received: {request.data}")
    service = ClickPaymentService()
    result = service.handle_prepare(request.data)
    logger.info(f"Click prepare result: {result}")
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def click_complete_view(request):
    """Handle Click complete requests"""
    logger.info(f"Click complete request received: {request.data}")
    service = ClickPaymentService()
    result = service.handle_complete(request.data)
    logger.info(f"Click complete result: {result}")
    return Response(result)


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