from django.db import models
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
