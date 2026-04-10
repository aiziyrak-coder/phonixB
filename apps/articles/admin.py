from django.contrib import admin
from .models import Article, ArticleVersion, ActivityLog, ArticleOperatorMessage


class ArticleVersionInline(admin.TabularInline):
    model = ArticleVersion
    extra = 0


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    extra = 0
    readonly_fields = ('timestamp', 'user', 'action', 'details')


class ArticleOperatorMessageInline(admin.TabularInline):
    model = ArticleOperatorMessage
    extra = 0
    readonly_fields = ('created_at', 'sender', 'body')
    can_delete = False


@admin.register(ArticleOperatorMessage)
class ArticleOperatorMessageAdmin(admin.ModelAdmin):
    list_display = ('article', 'sender', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('article__title', 'body', 'sender__email')
    readonly_fields = ('created_at',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'journal', 'status', 'submission_date', 'views_count']
    list_filter = ['status', 'journal', 'submission_date']
    search_fields = ['title', 'author__first_name', 'author__last_name', 'doi']
    readonly_fields = ['submission_date', 'views_count', 'downloads_count', 'citations_count']
    inlines = [ArticleVersionInline, ActivityLogInline, ArticleOperatorMessageInline]
    date_hierarchy = 'submission_date'
