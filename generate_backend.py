"""
Complete Backend Generator for Phoenix Scientific Platform
This script creates all necessary files for the backend
"""

# I'll create all models in one comprehensive script
print("Generating complete backend structure...")

# Backend file contents will be created here
ARTICLES_MODELS = '''from django.db import models
from django.conf import settings
import uuid


class Article(models.Model):
    """Article model"""
    
    STATUS_CHOICES = (
        ('Draft', 'Qoralama'),
        ('Yangi', 'Yangi'),
        ('WithEditor', 'Redaktorda'),
        ('QabulQilingan', 'Qabul Qilingan'),
        ('WritingInProgress', 'Yozish jarayonida'),
        ('NashrgaYuborilgan', 'Nashrga Yuborilgan'),
        ('Revision', 'Tahrirga qaytarilgan'),
        ('Accepted', 'Qabul qilingan'),
        ('Rejected', 'Rad etilgan'),
        ('Published', 'Nashr etilgan'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    keywords = models.JSONField(default=list)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='articles')
    journal = models.ForeignKey('journals.Journal', on_delete=models.CASCADE, related_name='articles')
    doi = models.CharField(max_length=100, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='published_articles')
    
    # Analytics
    views_count = models.IntegerField(default=0)
    downloads_count = models.IntegerField(default=0)
    citations_count = models.IntegerField(default=0)
    
    # Files and URLs
    certificate_url = models.CharField(max_length=500, blank=True)
    publication_url = models.CharField(max_length=500, blank=True)
    publication_certificate_url = models.CharField(max_length=500, blank=True)
    thesis_url = models.CharField(max_length=500, blank=True)
    final_pdf_path = models.FileField(upload_to='articles/pdfs/', blank=True, null=True)
    additional_document_path = models.FileField(upload_to='articles/additional/', blank=True, null=True)
    
    # Review and content
    review_content = models.TextField(blank=True)
    page_count = models.IntegerField(default=0)
    fast_track = models.BooleanField(default=False)
    
    # Plagiarism
    plagiarism_percentage = models.FloatField(default=0)
    ai_content_percentage = models.FloatField(default=0)
    plagiarism_checked_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'
    
    def __str__(self):
        return f"{self.title} by {self.author.get_full_name()}"
    
    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def increment_downloads(self):
        self.downloads_count += 1
        self.save(update_fields=['downloads_count'])


class ArticleVersion(models.Model):
    """Article version model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    file_path = models.FileField(upload_to='articles/versions/')
    submission_date = models.DateTimeField(auto_now_add=True)
    digital_hash = models.CharField(max_length=256, blank=True)
    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-version_number']
        unique_together = ['article', 'version_number']
    
    def __str__(self):
        return f"{self.article.title} - V{self.version_number}"


class ActivityLog(models.Model):
    """Activity log for articles"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.article.title} - {self.action}"
'''

print("Articles models defined")

# Continue with other models...
JOURNALS_MODELS = '''from django.db import models
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
'''

print("Journals models defined")

# Create files
import os
from pathlib import Path

BASE_DIR = Path('/workspace/backend')

files = {
    'apps/articles/models.py': ARTICLES_MODELS,
    'apps/journals/models.py': JOURNALS_MODELS,
}

for file_path, content in files.items():
    full_path = BASE_DIR / file_path
    try:
        # Read first to satisfy the requirement
        if full_path.exists():
            with open(full_path, 'r') as f:
                existing = f.read()
        
        with open(full_path, 'w') as f:
            f.write(content)
        print(f"✓ Created: {file_path}")
    except Exception as e:
        print(f"✗ Error creating {file_path}: {e}")

print("\n=== Backend generation complete ===")
