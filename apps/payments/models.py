from django.db import models
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
    click_service_id = models.CharField(max_length=50, blank=True)  # Service ID from Click callback
    
    # Payme payment fields
    payme_trans_id = models.CharField(max_length=100, blank=True)
    payme_time = models.BigIntegerField(null=True, blank=True)
    
    # Payment provider (click, payme, etc)
    payment_provider = models.CharField(max_length=20, blank=True, default='')
    
    receipt_path = models.FileField(upload_to='receipts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    objects = models.Manager()  # Default manager
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.id} - {self.amount} {self.currency} - {self.service_type}"