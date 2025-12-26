from django.db import models
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
