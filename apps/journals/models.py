from django.db import models
from django.conf import settings
import uuid


class JournalCategory(models.Model):
    """Journal category model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Journal Categories'
    
    def __str__(self):
        return self.name


class Journal(models.Model):
    """Journal model"""
    
    PAYMENT_MODEL_CHOICES = (
        ('pre-payment', 'Pre-Payment'),
        ('post-payment', 'Post-Payment'),
    )
    
    PRICING_TYPE_CHOICES = (
        ('fixed', 'Fixed Price'),
        ('per_page', 'Per Page'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    issn = models.CharField(max_length=20, unique=True)
    description = models.TextField()
    journal_admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_journals')
    category = models.ForeignKey(JournalCategory, on_delete=models.CASCADE, related_name='journals')
    rules = models.TextField(blank=True)
    image_url = models.ImageField(upload_to='journals/', blank=True, null=True)
    
    # Payment settings
    payment_model = models.CharField(max_length=20, choices=PAYMENT_MODEL_CHOICES, default='pre-payment')
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='fixed')
    publication_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_page = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional document config
    additional_doc_required = models.BooleanField(default=False)
    additional_doc_label = models.CharField(max_length=200, blank=True)
    additional_doc_type = models.CharField(max_length=20, choices=[('file', 'File'), ('link', 'Link')], default='file')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.issn})"


class Issue(models.Model):
    """Journal issue model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='issues')
    issue_number = models.CharField(max_length=50)
    publication_date = models.DateField()
    cover_image = models.ImageField(upload_to='issues/', blank=True, null=True)
    collection_url = models.URLField(blank=True)
    
    class Meta:
        ordering = ['-publication_date']
        unique_together = ['journal', 'issue_number']
    
    def __str__(self):
        return f"{self.journal.name} - Issue {self.issue_number}"
