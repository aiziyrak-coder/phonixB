from django.db import models
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
