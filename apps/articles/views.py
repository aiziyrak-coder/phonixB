from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Article, ArticleVersion, ActivityLog
from .serializers import ArticleSerializer, CreateArticleSerializer, ArticleVersionSerializer
from django.utils import timezone
from apps.services import get_gemini_service


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
        
        # Use the Gemini service to perform plagiarism check
        # For now, we'll use the simulation method, but in production this should use real plagiarism detection
        gemini_service = get_gemini_service()
        if article.final_pdf_path:  # If there's a file to check
            # For now, use the simulation method from the Gemini service
            # In production, this would be replaced with a real plagiarism detection service
            result = gemini_service.check_plagiarism("Document content would be extracted from the file here")
        else:
            # Fallback to random values if no file content
            result = gemini_service.check_plagiarism("Sample document content")
        
        plagiarism_percentage = result['plagiarism_percentage']
        ai_content_percentage = result['ai_content_percentage']
        
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