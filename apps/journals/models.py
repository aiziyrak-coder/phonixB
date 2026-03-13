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
    
    # Antiplagiat & AI Detektor limits (bosh admin jurnal qo'shishda belgilaydi)
    # Plagiat: maqola plagiat % bu qiymatdan katta bo'lsa rad. Null = tekshiruv o'chiq.
    plagiarism_max_percent = models.FloatField(null=True, blank=True)
    # AI kontent: maqola AI % bu qiymatdan katta bo'lsa rad. Null = tekshiruv o'chiq.
    ai_content_max_percent = models.FloatField(null=True, blank=True)
    # Originalilik: maqola originalilik % bu qiymatdan kichik bo'lsa rad. Null = tekshiruv o'chiq.
    originality_min_percent = models.FloatField(null=True, blank=True)
    
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
    collection_file = models.FileField(upload_to='issues/collections/', blank=True, null=True)
    
    class Meta:
        ordering = ['-publication_date']
        unique_together = ['journal', 'issue_number']
    
    def __str__(self):
        return f"{self.journal.name} - Issue {self.issue_number}"


class ScientificField(models.Model):
    """Scientific fields for categorization"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Scientific Field"
        verbose_name_plural = "Scientific Fields"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Conference(models.Model):
    """Conferences with categories and fields"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    category = models.ForeignKey(JournalCategory, on_delete=models.CASCADE)
    scientific_field = models.ForeignKey(ScientificField, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    date = models.DateField(blank=True, null=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conference"
        verbose_name_plural = "Conferences"
        ordering = ['-date', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.category.name})"


class AuthorPublication(models.Model):
    """Author publications with categorization"""
    
    PUBLICATION_TYPE_CHOICES = [
        ('journal_local', 'Mahalliy OAK jurnali'),
        ('journal_international', 'Xalqaro OAK jurnali'),
        ('journal_local_general', 'Mahalliy jurnal'),
        ('journal_international_general', 'Xalqaro jurnal'),
        ('conference_local', 'Mahalliy konferensiya'),
        ('conference_international', 'Xalqaro konferensiya'),
        ('scopus_journal', 'Scopus jurnali'),
        ('scopus_conference', 'Scopus konferensiyasi'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=300)
    publication_type = models.CharField(max_length=30, choices=PUBLICATION_TYPE_CHOICES)
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True)
    conference = models.ForeignKey(Conference, on_delete=models.SET_NULL, null=True, blank=True)
    scientific_field = models.ForeignKey(ScientificField, on_delete=models.CASCADE)
    publication_date = models.DateField()
    doi = models.CharField(max_length=100, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    co_authors = models.TextField(blank=True, help_text="Mualliflar vergul bilan ajratilgan")
    abstract = models.TextField(blank=True)
    keywords = models.TextField(blank=True, help_text="Kalit so'zlar vergul bilan ajratilgan")
    file_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Author Publication"
        verbose_name_plural = "Author Publications"
        ordering = ['-publication_date', 'title']
    
    def __str__(self):
        return f"{self.title} - {self.author.get_full_name()}"
