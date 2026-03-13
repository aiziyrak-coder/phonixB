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
        ('PlagiarismReview', 'Antiplagiat ko\'rib chiqish (bosh admin qarori)'),
        ('Revision', 'Tahrirga qaytarilgan'),
        ('Accepted', 'Qabul qilingan'),
        ('Rejected', 'Rad etilgan'),
        ('Published', 'Nashr etilgan'),
        # Book-specific workflow statuses
        ('ContractProcessing', 'Shartnoma rasmiylashtirilmoqda'),
        ('IsbnProcessing', 'ISBN olinmoqda'),
        ('AuthorDataVerified', 'Muallif ma`lumotlari tasdiqlandi'),
        ('PaymentCompleted', 'To`lov jarayoni yakunlandi'),
        ('SentToPrint', 'Bosmaga berildi'),
        ('Printing', 'Chop etilmoqda'),
        ('Ready', 'Tayyor'),
        ('Packaging', 'Qadoqlanmoqda'),
        ('Shipping', 'Yuborilmoqda (pochta)'),
        ('Delivered', 'Yetkazildi'),
        ('ProcessPaused', 'Jarayon to`xtatildi'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    keywords = models.JSONField(default=list)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='articles')
    journal = models.ForeignKey('journals.Journal', on_delete=models.CASCADE, related_name='articles')
    issue = models.ForeignKey('journals.Issue', on_delete=models.SET_NULL, null=True, blank=True, related_name='articles')
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
    publication_certificate_path = models.FileField(upload_to='articles/publication_certificates/', blank=True, null=True)
    thesis_url = models.CharField(max_length=500, blank=True)
    final_pdf_path = models.FileField(upload_to='articles/pdfs/', blank=True, null=True)
    additional_document_path = models.FileField(upload_to='articles/additional/', blank=True, null=True)
    
    # UDK (Universal Decimal Classification) — ilmiy ish uchun klassifikator kodi (teacode.com/online/udc)
    udk_code = models.CharField(max_length=100, blank=True)
    udk_description = models.CharField(max_length=500, blank=True)
    udk_certificate_path = models.FileField(upload_to='articles/udk_certificates/', blank=True, null=True)
    
    # Review and content
    review_content = models.TextField(blank=True)
    page_count = models.IntegerField(default=0)
    fast_track = models.BooleanField(default=False)
    
    # Plagiarism & AI Detection (advanced report)
    plagiarism_percentage = models.FloatField(default=0)
    ai_content_percentage = models.FloatField(default=0)
    originality_percentage = models.FloatField(default=0)
    plagiarism_checked_at = models.DateTimeField(null=True, blank=True)
    plagiarism_report = models.JSONField(default=dict, blank=True)
    
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


# Narx 1 bet uchun (so'm)
ARTICLE_SAMPLE_PRICE_QUYI = 15_000   # Quyi sifatli
ARTICLE_SAMPLE_PRICE_ORTA = 20_000   # O'rta sifatli
ARTICLE_SAMPLE_PRICE_YUQORI = 25_000  # Yuqori sifatli


class ArticleSampleRequest(models.Model):
    """Maqola namuna olish so'rovi — muallif talablarini yozadi, to'lov qiladi, taqrizchiga yuboriladi."""
    QUALITY_CHOICES = (
        ('quyi', 'Quyi sifatli'),
        ('orta', "O'rta sifatli"),
        ('yuqori', 'Yuqori sifatli'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='article_sample_requests')
    transaction = models.OneToOneField(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='article_sample_request'
    )
    requirements = models.TextField(help_text='Maqola bo\'yicha talablar')
    pages = models.PositiveIntegerField(default=1)
    topic = models.CharField(max_length=500)
    quality_level = models.CharField(max_length=20, choices=QUALITY_CHOICES)
    author_first_name = models.CharField(max_length=150)
    author_last_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default='submitted')  # submitted, in_progress, completed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Maqola namuna so\'rovi'
        verbose_name_plural = 'Maqola namuna so\'rovlari'

    def __str__(self):
        return f"{self.topic[:50]} — {self.get_quality_level_display()}"


# DOI raqami olish so'rovi — muallif fayl yuklaydi, to'lov qiladi, taqrizchi DOI link kiritadi
DOI_REQUEST_STATUS_SUBMITTED = 'submitted'
DOI_REQUEST_STATUS_COMPLETED = 'completed'


class DoiRequest(models.Model):
    """DOI raqami olish so'rovi: muallif ism/familya va fayl yuboradi, to'lovdan keyin taqrizchiga boradi."""
    STATUS_CHOICES = (
        ('pending_payment', 'To\'lov kutilmoqda'),
        (DOI_REQUEST_STATUS_SUBMITTED, 'Taqrizchida'),
        (DOI_REQUEST_STATUS_COMPLETED, 'Yakunlangan'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doi_requests')
    transaction = models.OneToOneField(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doi_request'
    )
    author_first_name = models.CharField(max_length=150)
    author_last_name = models.CharField(max_length=150)
    file = models.FileField(upload_to='doi_requests/%Y/%m/', blank=False)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_payment')
    doi_link = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'DOI so\'rovi'
        verbose_name_plural = 'DOI so\'rovlari'

    def __str__(self):
        return f"{self.author_last_name} {self.author_first_name} — {self.get_status_display()}"
