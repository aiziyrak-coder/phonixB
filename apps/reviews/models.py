from django.db import models
from django.conf import settings
import uuid


class PeerReview(models.Model):
    """Peer review model"""
    
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('accepted', 'Qabul qilindi'),
        ('declined', 'Rad etildi'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Yakunlandi'),
    )
    
    REVIEW_TYPE_CHOICES = (
        ('open', 'Ochiq'),
        ('single_blind', 'Bir tomonlama'),
        ('double_blind', 'Ikki tomonlama'),
    )

    RECOMMENDATION_CHOICES = (
        ('accept', 'Qabul qilish'),
        ('minor_revision', 'Kichik tuzatish'),
        ('major_revision', 'Katta tuzatish'),
        ('reject', 'Rad etish'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE, related_name='peer_reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='peer_reviews')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    review_content = models.TextField(blank=True)
    rating = models.IntegerField(default=0)
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES, default='double_blind')
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, blank=True)
    
    # Detailed scoring (1-10 scale)
    originality_score = models.IntegerField(default=0)
    methodology_score = models.IntegerField(default=0)
    clarity_score = models.IntegerField(default=0)
    significance_score = models.IntegerField(default=0)
    references_score = models.IntegerField(default=0)
    
    # Structured feedback
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    comments_to_author = models.TextField(blank=True)
    comments_to_editor = models.TextField(blank=True)
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.get_full_name()} for {self.article.title}"

    @property
    def overall_score(self):
        scores = [self.originality_score, self.methodology_score, self.clarity_score,
                  self.significance_score, self.references_score]
        valid = [s for s in scores if s > 0]
        return round(sum(valid) / len(valid), 1) if valid else 0
