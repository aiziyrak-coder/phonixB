from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError
from django.db.models import Prefetch, Q, Count
from .models import Journal, JournalCategory, Issue, ScientificField, Conference, AuthorPublication
from .serializers import JournalSerializer, JournalCategorySerializer, IssueSerializer
from apps.articles.models import Article


class JournalCategoryViewSet(viewsets.ModelViewSet):
    queryset = JournalCategory.objects.all()
    serializer_class = JournalCategorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Optimize query
        return JournalCategory.objects.prefetch_related('journals').all()


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        # Optimize queries with select_related. Journal admin sees only their assigned journals.
        base = Journal.objects.select_related(
            'journal_admin', 'category'
        ).prefetch_related(
            'issues'
        )
        role = getattr(self.request.user, 'role', None) if self.request.user.is_authenticated else None
        if role == 'journal_admin':
            return base.filter(journal_admin=self.request.user)
        return base.all()
    
    def create(self, request, *args, **kwargs):
        # Only super_admin and journal_admin can create journals
        if request.user.role not in ['super_admin', 'journal_admin']:
            return Response(
                {'error': 'Siz jurnal yaratish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        # Only super_admin and journal owner can update
        journal = self.get_object()
        if request.user.role != 'super_admin' and journal.journal_admin != request.user:
            return Response(
                {'error': 'Siz bu jurnalni yangilash huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        # Only super_admin can delete journals
        if request.user.role != 'super_admin':
            return Response(
                {'error': 'Siz jurnalni o\'chirish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class IssueViewSet(viewsets.ModelViewSet):
    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Optimize queries. Journal admin sees only issues of their assigned journals.
        base = Issue.objects.select_related('journal', 'journal__journal_admin').prefetch_related('articles')
        role = getattr(self.request.user, 'role', None) if self.request.user.is_authenticated else None
        if role == 'journal_admin':
            return base.filter(journal__journal_admin=self.request.user)
        return base.all()
    
    def _assign_articles_to_issue(self, issue, article_ids):
        """Set issue on published articles of this journal; clear issue for others in this issue."""
        if not isinstance(article_ids, list):
            article_ids = []
        article_ids = [a for a in article_ids if a]
        # Only assign articles that belong to this issue's journal and are Published
        Article.objects.filter(
            id__in=article_ids, journal=issue.journal, status='Published'
        ).update(issue=issue)
        # Remove from this issue any articles no longer in the list
        Article.objects.filter(issue=issue).exclude(id__in=article_ids).update(issue=None)

    def _save_collection_file(self, issue, request):
        """Save uploaded collection file (PDF/DOC) to issue if present in request.FILES."""
        f = request.FILES.get('collection_file') if hasattr(request, 'FILES') else None
        if f:
            issue.collection_file = f
            issue.save(update_fields=['collection_file'])

    def _issue_serializer_data(self, request_data, exclude=None):
        """Build dict with only Issue model fields so serializer does not get 400 for unknown keys (e.g. articles, collection_file)."""
        import json
        allowed = {'journal', 'issue_number', 'publication_date', 'cover_image', 'collection_url'}
        exclude = exclude or set()
        # Prefer request_data; for FormData, request_data is QueryDict (POST + FILES)
        data = request_data.copy() if hasattr(request_data, 'copy') else dict(request_data)
        # Normalize: QueryDict can return lists for some keys; take first element for scalars
        def get_val(d, key):
            v = d.get(key) if hasattr(d, 'get') else (d[key] if key in d else None)
            if isinstance(v, list) and len(v) > 0:
                return v[0]
            return v
        articles_raw = get_val(data, 'articles')
        if isinstance(articles_raw, str):
            try:
                article_ids = json.loads(articles_raw or '[]')
            except Exception:
                article_ids = []
        else:
            article_ids = list(articles_raw) if articles_raw else []
        if hasattr(data, 'pop'):
            data.pop('articles', None)
        serializer_data = {}
        for k in allowed:
            if k in exclude:
                continue
            if k not in data:
                continue
            v = get_val(data, k)
            serializer_data[k] = v
        # FormData: ensure required fields from request.POST if missing (QueryDict sometimes)
        request = getattr(self, 'request', None)
        if request and hasattr(request, 'POST'):
            for req in ('journal', 'issue_number', 'publication_date'):
                if req not in serializer_data and req not in exclude:
                    fallback = request.POST.get(req) if hasattr(request.POST, 'get') else None
                    if fallback is not None:
                        serializer_data[req] = fallback
        return serializer_data, article_ids

    def create(self, request, *args, **kwargs):
        if request.user.role not in ['super_admin', 'journal_admin']:
            return Response(
                {'error': 'Siz jurnal sonini yaratish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        source = request.POST if request.content_type and 'multipart' in request.content_type and request.POST else request.data
        serializer_data, article_ids = self._issue_serializer_data(source)
        journal_id = serializer_data.get('journal')
        issue_number = serializer_data.get('issue_number')
        # Upsert: check BEFORE validation so we don't get unique_together 400
        if journal_id and issue_number:
            existing = Issue.objects.filter(journal_id=journal_id, issue_number=str(issue_number)).first()
            if existing:
                update_serializer = self.get_serializer(existing, data=serializer_data, partial=True)
                if not update_serializer.is_valid():
                    return Response(update_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                self.perform_update(update_serializer)
                self._save_collection_file(existing, request)
                self._assign_articles_to_issue(existing, article_ids)
                return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data=serializer_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        self._save_collection_file(serializer.instance, request)
        self._assign_articles_to_issue(serializer.instance, article_ids)
        headers = self.get_success_headers(serializer.data)
        return Response(self.get_serializer(serializer.instance).data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        issue = self.get_object()
        if request.user.role != 'super_admin' and issue.journal.journal_admin != request.user:
            return Response(
                {'error': 'Siz bu jurnal sonini yangilash huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        source = request.POST if request.content_type and 'multipart' in request.content_type and request.POST else request.data
        serializer_data, article_ids = self._issue_serializer_data(source)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(issue, data=serializer_data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        self._save_collection_file(issue, request)
        self._assign_articles_to_issue(issue, article_ids)
        return Response(self.get_serializer(issue).data)
    
    def destroy(self, request, *args, **kwargs):
        # Only super_admin and journal owner can delete
        issue = self.get_object()
        if request.user.role != 'super_admin' and issue.journal.journal_admin != request.user:
            return Response(
                {'error': 'Siz jurnal sonini o\'chirish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny], url_path='public')
    def public_issue(self, request, pk=None):
        """Public data for share link: journal name, issue number, download (collection_file_url or collection_url)."""
        from django.conf import settings
        issue = Issue.objects.filter(pk=pk).select_related('journal').first()
        if not issue:
            return Response({'detail': 'To\'plam topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        collection_file_url = None
        if issue.collection_file:
            if request:
                collection_file_url = request.build_absolute_uri(issue.collection_file.url)
            else:
                base = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
                collection_file_url = f"{base}{issue.collection_file.url}"
        data = {
            'id': str(issue.id),
            'journal_name': issue.journal.name,
            'issue_number': issue.issue_number,
            'publication_date': str(issue.publication_date),
            'collection_url': issue.collection_url or '',
            'collection_file_url': collection_file_url,
        }
        return Response(data)


# New ViewSets for categorization system

class ScientificFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScientificField
        fields = ['id', 'name', 'description', 'is_active', 'created_at']


class ConferenceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    scientific_field_name = serializers.CharField(source='scientific_field.name', read_only=True)
    
    class Meta:
        model = Conference
        fields = ['id', 'title', 'category', 'category_name', 'scientific_field', 'scientific_field_name',
                  'description', 'location', 'date', 'website', 'is_active', 'created_at', 'updated_at']


class AuthorPublicationSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    publication_type_display = serializers.CharField(source='get_publication_type_display', read_only=True)
    scientific_field_name = serializers.CharField(source='scientific_field.name', read_only=True)
    journal_name = serializers.CharField(source='journal.name', read_only=True)
    conference_name = serializers.CharField(source='conference.title', read_only=True)
    
    # Nested journal and conference data
    journal = serializers.SerializerMethodField()
    conference = serializers.SerializerMethodField()
    
    class Meta:
        model = AuthorPublication
        fields = ['id', 'author', 'author_name', 'title', 'publication_type', 'publication_type_display',
                  'journal', 'journal_name', 'conference', 'conference_name', 'scientific_field',
                  'scientific_field_name', 'publication_date', 'doi', 'pages', 'co_authors', 'abstract',
                  'keywords', 'file_url', 'is_verified', 'created_at', 'updated_at']
        read_only_fields = ['author', 'is_verified', 'created_at', 'updated_at']
    
    def get_journal(self, obj):
        if obj.journal:
            return {
                'id': str(obj.journal.id),
                'name': obj.journal.name,
                'image_url': obj.journal.image_url.url if obj.journal.image_url else None,
                'issn': obj.journal.issn
            }
        return None
    
    def get_conference(self, obj):
        if obj.conference:
            return {
                'id': str(obj.conference.id),
                'title': obj.conference.title,
                'location': obj.conference.location,
                'date': obj.conference.date.isoformat() if obj.conference.date else None
            }
        return None


class ScientificFieldViewSet(viewsets.ModelViewSet):
    """Scientific fields CRUD operations"""
    queryset = ScientificField.objects.filter(is_active=True)
    serializer_class = ScientificFieldSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


class ConferenceViewSet(viewsets.ModelViewSet):
    """Conferences CRUD operations"""
    queryset = Conference.objects.filter(is_active=True)
    serializer_class = ConferenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'scientific_field', 'is_active']
    search_fields = ['title', 'description', 'location']
    ordering = ['-date', 'title']


class AuthorPublicationViewSet(viewsets.ModelViewSet):
    """Author publications CRUD operations"""
    serializer_class = AuthorPublicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['publication_type', 'scientific_field', 'is_verified']
    search_fields = ['title', 'co_authors', 'keywords']
    ordering = ['-publication_date', 'title']
    
    def get_queryset(self):
        """Filter by current user for non-superusers"""
        if self.request.user.is_superuser:
            return AuthorPublication.objects.all()
        return AuthorPublication.objects.filter(author=self.request.user)
    
    def perform_create(self, serializer):
        """Set author to current user"""
        serializer.save(author=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_publications(self, request):
        """Get current user's publications"""
        publications = self.get_queryset()
        serializer = self.get_serializer(publications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def publication_types(self, request):
        """Get all publication types with labels"""
        types = AuthorPublication.PUBLICATION_TYPE_CHOICES
        return Response([
            {'value': value, 'label': label}
            for value, label in types
        ])
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get publication statistics for current user"""
        queryset = self.get_queryset()
        
        stats = {
            'total_publications': queryset.count(),
            'verified_publications': queryset.filter(is_verified=True).count(),
            'by_type': {},
            'by_field': {}
        }
        
        # By publication type
        for value, label in AuthorPublication.PUBLICATION_TYPE_CHOICES:
            count = queryset.filter(publication_type=value).count()
            if count > 0:
                stats['by_type'][value] = {
                    'label': label,
                    'count': count
                }
        
        # By scientific field
        fields = queryset.values('scientific_field__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats['by_field'] = [
            {
                'name': field['scientific_field__name'],
                'count': field['count']
            }
            for field in fields
        ]
        
        return Response(stats)
