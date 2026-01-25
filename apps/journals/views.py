from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Prefetch
from .models import Journal, JournalCategory, Issue
from .serializers import JournalSerializer, JournalCategorySerializer, IssueSerializer


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
        # Optimize queries with select_related
        return Journal.objects.select_related(
            'journal_admin', 'category'
        ).prefetch_related(
            'issues'
        ).all()
    
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
        # Optimize queries
        return Issue.objects.select_related('journal', 'journal__journal_admin').all()
    
    def create(self, request, *args, **kwargs):
        # Only journal_admin and super_admin can create issues
        if request.user.role not in ['super_admin', 'journal_admin']:
            return Response(
                {'error': 'Siz jurnal sonini yaratish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        # Only journal owner and super_admin can update
        issue = self.get_object()
        if request.user.role != 'super_admin' and issue.journal.journal_admin != request.user:
            return Response(
                {'error': 'Siz bu jurnal sonini yangilash huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        # Only super_admin and journal owner can delete
        issue = self.get_object()
        if request.user.role != 'super_admin' and issue.journal.journal_admin != request.user:
            return Response(
                {'error': 'Siz jurnal sonini o\'chirish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
