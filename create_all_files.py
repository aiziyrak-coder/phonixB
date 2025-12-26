#!/usr/bin/env python
"""
Comprehensive Backend File Generator
Creates all necessary files for Phoenix Scientific Platform backend
"""

import os
from pathlib import Path

BASE_DIR = Path('/workspace/backend')

# ============================================================================
# APPS CONFIGURATION FILES
# ============================================================================

APPS_CONFIGS = {
    'articles': '''from django.apps import AppConfig

class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.articles'
    verbose_name = 'Articles'
''',
    'journals': '''from django.apps import AppConfig

class JournalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.journals'
    verbose_name = 'Journals'
''',
    'payments': '''from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Payments'
''',
    'translations': '''from django.apps import AppConfig

class TranslationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.translations'
    verbose_name = 'Translations'
''',
    'reviews': '''from django.apps import AppConfig

class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reviews'
    verbose_name = 'Reviews'
''',
    'notifications': '''from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notifications'
''',
}

# ============================================================================
# PAYMENTS APP
# ============================================================================

PAYMENTS_MODELS = '''from django.db import models
from django.conf import settings
import uuid


class Transaction(models.Model):
    """Payment transaction model"""
    
    SERVICE_TYPES = (
        ('fast-track', 'Fast Track'),
        ('publication_fee', 'Publication Fee'),
        ('language_editing', 'Language Editing'),
        ('top_up', 'Top Up'),
        ('book_publication', 'Book Publication'),
        ('translation', 'Translation'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    translation_request = models.ForeignKey('translations.TranslationRequest', on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='UZS')
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Click payment fields
    click_trans_id = models.CharField(max_length=100, blank=True)
    click_paydoc_id = models.CharField(max_length=100, blank=True)
    merchant_trans_id = models.CharField(max_length=100, blank=True)
    
    receipt_path = models.FileField(upload_to='receipts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} {self.currency} - {self.service_type}"
'''

PAYMENTS_SERIALIZERS = '''from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'completed_at', 'user')
    
    def get_user_name(self, obj):
        return obj.user.get_full_name()


class CreateTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('article', 'translation_request', 'amount', 'service_type')
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
'''

PAYMENTS_VIEWS = '''from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Transaction
from .serializers import TransactionSerializer, CreateTransactionSerializer
from .services import ClickPaymentService
import json


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transactions"""
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateTransactionSerializer
        return TransactionSerializer
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment via Click"""
        transaction = self.get_object()
        service = ClickPaymentService()
        result = service.prepare_payment(transaction)
        return Response(result)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def click_prepare(request):
    """Click prepare endpoint"""
    service = ClickPaymentService()
    return Response(service.handle_prepare(request.data))


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def click_complete(request):
    """Click complete endpoint"""
    service = ClickPaymentService()
    return Response(service.handle_complete(request.data))
'''

PAYMENTS_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    path('click/prepare/', views.click_prepare, name='click_prepare'),
    path('click/complete/', views.click_complete, name='click_complete'),
    path('', include(router.urls)),
]
'''

PAYMENTS_SERVICES = '''"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
import hashlib
import requests
from .models import Transaction


class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self):
        self.merchant_id = settings.CLICK_MERCHANT_ID
        self.service_id = settings.CLICK_SERVICE_ID
        self.secret_key = settings.CLICK_SECRET_KEY
        self.merchant_user_id = settings.CLICK_MERCHANT_USER_ID
    
    def generate_signature(self, *args):
        """Generate signature for Click request"""
        sign_string = ''.join(str(arg) for arg in args)
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def prepare_payment(self, transaction):
        """Prepare payment data for Click"""
        return {
            'merchant_id': self.merchant_id,
            'service_id': self.service_id,
            'transaction_param': str(transaction.id),
            'amount': str(transaction.amount),
            'return_url': settings.CORS_ALLOWED_ORIGINS[0] + '/payment/success',
            'cancel_url': settings.CORS_ALLOWED_ORIGINS[0] + '/payment/cancel',
        }
    
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
'''

PAYMENTS_ADMIN = '''from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'currency', 'service_type', 'status', 'created_at']
    list_filter = ['status', 'service_type', 'created_at']
    search_fields = ['user__email', 'user__phone', 'click_trans_id']
    readonly_fields = ['created_at', 'completed_at']
    date_hierarchy = 'created_at'
'''

# ============================================================================
# TRANSLATIONS APP
# ============================================================================

TRANSLATIONS_MODELS = '''from django.db import models
from django.conf import settings
import uuid


class TranslationRequest(models.Model):
    """Translation request model"""
    
    STATUS_CHOICES = (
        ('Yangi', 'Yangi'),
        ('Jarayonda', 'Jarayonda'),
        ('Bajarildi', 'Bajarildi'),
        ('BekorQilindi', 'Bekor Qilindi'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='translation_requests')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_translations')
    
    title = models.CharField(max_length=500)
    source_language = models.CharField(max_length=50)
    target_language = models.CharField(max_length=50)
    source_file_path = models.FileField(upload_to='translations/source/')
    translated_file_path = models.FileField(upload_to='translations/translated/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Yangi')
    word_count = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    submission_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submission_date']
    
    def __str__(self):
        return f"{self.title} - {self.source_language} to {self.target_language}"
'''

# ============================================================================
# REVIEWS APP
# ============================================================================

REVIEWS_MODELS = '''from django.db import models
from django.conf import settings
import uuid


class PeerReview(models.Model):
    """Peer review model"""
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
    )
    
    REVIEW_TYPE_CHOICES = (
        ('open', 'Open'),
        ('single_blind', 'Single Blind'),
        ('double_blind', 'Double Blind'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE, related_name='peer_reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='peer_reviews')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    review_content = models.TextField(blank=True)
    rating = models.IntegerField(default=0)
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES, default='double_blind')
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.get_full_name()} for {self.article.title}"
'''

# ============================================================================
# NOTIFICATIONS APP
# ============================================================================

NOTIFICATIONS_MODELS = '''from django.db import models
from django.conf import settings
import uuid


class Notification(models.Model):
    """Notification model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.message[:50]}"
'''

# Dictionary of all files to create
FILES_TO_CREATE = {
    # Apps configs
    'apps/articles/apps.py': APPS_CONFIGS['articles'],
    'apps/journals/apps.py': APPS_CONFIGS['journals'],
    'apps/payments/apps.py': APPS_CONFIGS['payments'],
    'apps/translations/apps.py': APPS_CONFIGS['translations'],
    'apps/reviews/apps.py': APPS_CONFIGS['reviews'],
    'apps/notifications/apps.py': APPS_CONFIGS['notifications'],
    
    # Payments app
    'apps/payments/models.py': PAYMENTS_MODELS,
    'apps/payments/serializers.py': PAYMENTS_SERIALIZERS,
    'apps/payments/views.py': PAYMENTS_VIEWS,
    'apps/payments/urls.py': PAYMENTS_URLS,
    'apps/payments/services.py': PAYMENTS_SERVICES,
    'apps/payments/admin.py': PAYMENTS_ADMIN,
    
    # Translations app
    'apps/translations/models.py': TRANSLATIONS_MODELS,
    
    # Reviews app
    'apps/reviews/models.py': REVIEWS_MODELS,
    
    # Notifications app
    'apps/notifications/models.py': NOTIFICATIONS_MODELS,
}

# Create all files
def create_files():
    for file_path, content in FILES_TO_CREATE.items():
        full_path = BASE_DIR / file_path
        
        try:
            # Read existing file if it exists
            if full_path.exists():
                with open(full_path, 'r') as f:
                    _ = f.read()
            
            # Write new content
            with open(full_path, 'w') as f:
                f.write(content)
            
            print(f"✓ Created: {file_path}")
        except Exception as e:
            print(f"✗ Error creating {file_path}: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("Creating backend files for Phoenix Scientific Platform")
    print("=" * 60)
    create_files()
    print("\\n✓ All files created successfully!")
