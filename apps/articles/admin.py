from django.contrib import admin
from .models import Article, ArticleVersion, ActivityLog


class ArticleVersionInline(admin.TabularInline):
    model = ArticleVersion
    extra = 0


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    extra = 0
    readonly_fields = ('timestamp', 'user', 'action', 'details')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'journal', 'status', 'submission_date', 'views_count']
    list_filter = ['status', 'journal', 'submission_date']
    search_fields = ['title', 'author__first_name', 'author__last_name', 'doi']
    readonly_fields = ['submission_date', 'views_count', 'downloads_count', 'citations_count']
    inlines = [ArticleVersionInline, ActivityLogInline]
    date_hierarchy = 'submission_date'
