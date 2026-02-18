from django.db import models
from django.conf import settings
import uuid


class Notification(models.Model):
    """Notification model"""

    TYPE_CHOICES = (
        ('status_change', 'Status o\'zgarishi'),
        ('review_assigned', 'Taqriz tayinlandi'),
        ('review_completed', 'Taqriz yakunlandi'),
        ('payment', 'To\'lov'),
        ('plagiarism', 'Antiplagiat'),
        ('system', 'Tizim'),
        ('article', 'Maqola'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    title = models.CharField(max_length=255, default='Bildirishnoma')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    link = models.CharField(max_length=500, blank=True)
    read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.message[:50]}"

    @classmethod
    def notify(cls, user, title, message, notification_type='system', link='', metadata=None):
        """Helper to create a notification quickly."""
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            metadata=metadata or {},
        )
