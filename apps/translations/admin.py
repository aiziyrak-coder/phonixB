from django.contrib import admin
from .models import TranslationRequest


@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'source_language', 'target_language', 'submission_date']
    list_filter = ['status', 'source_language', 'target_language']
    search_fields = ['title', 'author__first_name', 'author__last_name']
