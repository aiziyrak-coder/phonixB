#!/usr/bin/env python
"""
Create remaining files for all apps
"""
import os
from pathlib import Path

BASE_DIR = Path('/workspace/backend')

# ============================================================================
# ARTICLES APP - Serializers, Views, URLs, Admin
# ============================================================================

ARTICLES_SERIALIZERS = '''from rest_framework import serializers
from .models import Article, ArticleVersion, ActivityLog
from apps.users.serializers import UserSerializer


class ArticleVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleVersion
        fields = '__all__'


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ActivityLog
        fields = '__all__'
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


class ArticleSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    journal_name = serializers.SerializerMethodField()
    versions = ArticleVersionSerializer(many=True, read_only=True)
    activity_logs = ActivityLogSerializer(many=True, read_only=True)
    analytics = serializers.SerializerMethodField()
    
    class Meta:
        model = Article
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'views_count', 'downloads_count', 'citations_count')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_journal_name(self, obj):
        return obj.journal.name
    
    def get_analytics(self, obj):
        return {
            'views': obj.views_count,
            'downloads': obj.downloads_count,
            'citations': obj.citations_count
        }


class CreateArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('title', 'abstract', 'keywords', 'journal', 'final_pdf_path', 
                  'additional_document_path', 'page_count', 'fast_track')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        validated_data['status'] = 'Draft'
        return super().create(validated_data)
'''

ARTICLES_VIEWS = '''from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Article, ArticleVersion, ActivityLog
from .serializers import ArticleSerializer, CreateArticleSerializer, ArticleVersionSerializer
from django.utils import timezone


class ArticleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing articles"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'super_admin':
            return Article.objects.all()
        elif self.request.user.role == 'journal_admin':
            return Article.objects.filter(journal__journal_admin=self.request.user)
        elif self.request.user.role == 'author':
            return Article.objects.filter(author=self.request.user)
        return Article.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateArticleSerializer
        return ArticleSerializer
    
    @action(detail=True, methods=['post'])
    def increment_views(self, request, pk=None):
        """Increment article views"""
        article = self.get_object()
        article.increment_views()
        return Response({'views': article.views_count})
    
    @action(detail=True, methods=['post'])
    def increment_downloads(self, request, pk=None):
        """Increment article downloads"""
        article = self.get_object()
        article.increment_downloads()
        return Response({'downloads': article.downloads_count})
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update article status"""
        article = self.get_object()
        new_status = request.data.get('status')
        
        if new_status:
            old_status = article.status
            article.status = new_status
            article.save()
            
            # Log activity
            ActivityLog.objects.create(
                article=article,
                user=request.user,
                action=f'Status changed from {old_status} to {new_status}',
                details=request.data.get('reason', '')
            )
            
            return Response({'status': 'success', 'new_status': new_status})
        return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def check_plagiarism(self, request, pk=None):
        """Check article for plagiarism"""
        article = self.get_object()
        
        # Simulate plagiarism check (integrate real service here)
        plagiarism_percentage = request.data.get('plagiarism', 15.5)
        ai_content_percentage = request.data.get('ai_content', 8.3)
        
        article.plagiarism_percentage = plagiarism_percentage
        article.ai_content_percentage = ai_content_percentage
        article.plagiarism_checked_at = timezone.now()
        article.save()
        
        ActivityLog.objects.create(
            article=article,
            user=request.user,
            action='Plagiarism check completed',
            details=f'Plagiarism: {plagiarism_percentage}%, AI Content: {ai_content_percentage}%'
        )
        
        return Response({
            'plagiarism': plagiarism_percentage,
            'ai_content': ai_content_percentage,
            'checked_at': article.plagiarism_checked_at
        })
'''

ARTICLES_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.ArticleViewSet, basename='article')

urlpatterns = [
    path('', include(router.urls)),
]
'''

ARTICLES_ADMIN = '''from django.contrib import admin
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
'''

# ============================================================================
# JOURNALS APP - Serializers, Views, URLs, Admin
# ============================================================================

JOURNALS_SERIALIZERS = '''from rest_framework import serializers
from .models import Journal, JournalCategory, Issue


class JournalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalCategory
        fields = '__all__'


class IssueSerializer(serializers.ModelSerializer):
    journal_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Issue
        fields = '__all__'
    
    def get_journal_name(self, obj):
        return obj.journal.name


class JournalSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    admin_name = serializers.SerializerMethodField()
    issues = IssueSerializer(many=True, read_only=True)
    additional_document_config = serializers.SerializerMethodField()
    
    class Meta:
        model = Journal
        fields = '__all__'
    
    def get_category_name(self, obj):
        return obj.category.name
    
    def get_admin_name(self, obj):
        return obj.journal_admin.get_full_name()
    
    def get_additional_document_config(self, obj):
        if obj.additional_doc_required:
            return {
                'required': obj.additional_doc_required,
                'label': obj.additional_doc_label,
                'type': obj.additional_doc_type
            }
        return None
'''

JOURNALS_VIEWS = '''from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Journal, JournalCategory, Issue
from .serializers import JournalSerializer, JournalCategorySerializer, IssueSerializer


class JournalCategoryViewSet(viewsets.ModelViewSet):
    queryset = JournalCategory.objects.all()
    serializer_class = JournalCategorySerializer
    permission_classes = [AllowAny]


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [AllowAny]


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
'''

JOURNALS_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.JournalCategoryViewSet, basename='category')
router.register('journals', views.JournalViewSet, basename='journal')
router.register('issues', views.IssueViewSet, basename='issue')

urlpatterns = [
    path('', include(router.urls)),
]
'''

JOURNALS_ADMIN = '''from django.contrib import admin
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
'''

# ============================================================================
# TRANSLATIONS APP - Serializers, Views, URLs, Admin
# ============================================================================

TRANSLATIONS_SERIALIZERS = '''from rest_framework import serializers
from .models import TranslationRequest


class TranslationRequestSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TranslationRequest
        fields = '__all__'
        read_only_fields = ('id', 'submission_date', 'author')
    
    def get_author_name(self, obj):
        return obj.author.get_full_name()
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name() if obj.reviewer else None
'''

TRANSLATIONS_VIEWS = '''from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import TranslationRequest
from .serializers import TranslationRequestSerializer


class TranslationRequestViewSet(viewsets.ModelViewSet):
    queryset = TranslationRequest.objects.all()
    serializer_class = TranslationRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['super_admin', 'reviewer']:
            return TranslationRequest.objects.all()
        return TranslationRequest.objects.filter(author=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
'''

TRANSLATIONS_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.TranslationRequestViewSet, basename='translation')

urlpatterns = [
    path('', include(router.urls)),
]
'''

TRANSLATIONS_ADMIN = '''from django.contrib import admin
from .models import TranslationRequest


@admin.register(TranslationRequest)
class TranslationRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status', 'source_language', 'target_language', 'submission_date']
    list_filter = ['status', 'source_language', 'target_language']
    search_fields = ['title', 'author__first_name', 'author__last_name']
'''

# ============================================================================
# REVIEWS APP - Serializers, Views, URLs, Admin
# ============================================================================

REVIEWS_SERIALIZERS = '''from rest_framework import serializers
from .models import PeerReview


class PeerReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    article_title = serializers.SerializerMethodField()
    
    class Meta:
        model = PeerReview
        fields = '__all__'
        read_only_fields = ('id', 'assigned_at', 'reviewer')
    
    def get_reviewer_name(self, obj):
        return obj.reviewer.get_full_name()
    
    def get_article_title(self, obj):
        return obj.article.title
'''

REVIEWS_VIEWS = '''from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import PeerReview
from .serializers import PeerReviewSerializer


class PeerReviewViewSet(viewsets.ModelViewSet):
    queryset = PeerReview.objects.all()
    serializer_class = PeerReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role == 'reviewer':
            return PeerReview.objects.filter(reviewer=self.request.user)
        elif self.request.user.role in ['super_admin', 'journal_admin']:
            return PeerReview.objects.all()
        return PeerReview.objects.filter(article__author=self.request.user)
'''

REVIEWS_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.PeerReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]
'''

REVIEWS_ADMIN = '''from django.contrib import admin
from .models import PeerReview


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ['article', 'reviewer', 'status', 'rating', 'assigned_at']
    list_filter = ['status', 'review_type', 'rating']
    search_fields = ['article__title', 'reviewer__first_name', 'reviewer__last_name']
'''

# ============================================================================
# NOTIFICATIONS APP - Serializers, Views, URLs, Admin
# ============================================================================

NOTIFICATIONS_SERIALIZERS = '''from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'user')
'''

NOTIFICATIONS_VIEWS = '''from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response({'status': 'success'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        self.get_queryset().update(read=True)
        return Response({'status': 'success'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notifications count"""
        count = self.get_queryset().filter(read=False).count()
        return Response({'count': count})
'''

NOTIFICATIONS_URLS = '''from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
'''

NOTIFICATIONS_ADMIN = '''from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'read', 'created_at']
    list_filter = ['read', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'message']
'''

# Dictionary of all files
FILES = {
    'apps/articles/serializers.py': ARTICLES_SERIALIZERS,
    'apps/articles/views.py': ARTICLES_VIEWS,
    'apps/articles/urls.py': ARTICLES_URLS,
    'apps/articles/admin.py': ARTICLES_ADMIN,
    
    'apps/journals/serializers.py': JOURNALS_SERIALIZERS,
    'apps/journals/views.py': JOURNALS_VIEWS,
    'apps/journals/urls.py': JOURNALS_URLS,
    'apps/journals/admin.py': JOURNALS_ADMIN,
    
    'apps/translations/serializers.py': TRANSLATIONS_SERIALIZERS,
    'apps/translations/views.py': TRANSLATIONS_VIEWS,
    'apps/translations/urls.py': TRANSLATIONS_URLS,
    'apps/translations/admin.py': TRANSLATIONS_ADMIN,
    
    'apps/reviews/serializers.py': REVIEWS_SERIALIZERS,
    'apps/reviews/views.py': REVIEWS_VIEWS,
    'apps/reviews/urls.py': REVIEWS_URLS,
    'apps/reviews/admin.py': REVIEWS_ADMIN,
    
    'apps/notifications/serializers.py': NOTIFICATIONS_SERIALIZERS,
    'apps/notifications/views.py': NOTIFICATIONS_VIEWS,
    'apps/notifications/urls.py': NOTIFICATIONS_URLS,
    'apps/notifications/admin.py': NOTIFICATIONS_ADMIN,
}

def create_files():
    for file_path, content in FILES.items():
        full_path = BASE_DIR / file_path
        
        try:
            if full_path.exists():
                with open(full_path, 'r') as f:
                    _ = f.read()
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            print(f"✓ {file_path}")
        except Exception as e:
            print(f"✗ {file_path}: {e}")

if __name__ == '__main__':
    print("Creating remaining files...")
    create_files()
    print("\\nDone!")
