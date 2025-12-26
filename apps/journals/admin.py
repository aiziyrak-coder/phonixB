from django.contrib import admin
from .models import Journal, JournalCategory, Issue


@admin.register(JournalCategory)
class JournalCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ['name', 'issn', 'category', 'journal_admin', 'payment_model']
    list_filter = ['category', 'payment_model', 'pricing_type']
    search_fields = ['name', 'issn']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['journal', 'issue_number', 'publication_date']
    list_filter = ['journal', 'publication_date']
    search_fields = ['journal__name', 'issue_number']
