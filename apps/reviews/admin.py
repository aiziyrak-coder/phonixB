from django.contrib import admin
from .models import PeerReview


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ['article', 'reviewer', 'status', 'rating', 'assigned_at']
    list_filter = ['status', 'review_type', 'rating']
    search_fields = ['article__title', 'reviewer__first_name', 'reviewer__last_name']
