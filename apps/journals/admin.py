from django.contrib import admin
from .models import Journal, JournalCategory, Issue, ScientificField, Conference, AuthorPublication


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


@admin.register(ScientificField)
class ScientificFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']


@admin.register(Conference)
class ConferenceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'scientific_field', 'date', 'location']
    list_filter = ['category', 'scientific_field', 'date']
    search_fields = ['title', 'location']


@admin.register(AuthorPublication)
class AuthorPublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'publication_type', 'scientific_field', 'publication_date', 'is_verified']
    list_filter = ['publication_type', 'scientific_field', 'is_verified', 'publication_date']
    search_fields = ['title', 'author__first_name', 'author__last_name']
    date_hierarchy = 'publication_date'
