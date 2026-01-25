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
        # Optimize queries with select_related and prefetch_related
        base_queryset = Article.objects.select_related(
            'author', 'journal', 'journal__journal_admin', 'published_by'
        ).prefetch_related(
            'versions', 'activity_logs', 'peer_reviews'
        )
        
        if self.request.user.role == 'super_admin':
            return base_queryset.all()
        elif self.request.user.role == 'journal_admin':
            return base_queryset.filter(journal__journal_admin=self.request.user)
        elif self.request.user.role == 'author':
            return base_queryset.filter(author=self.request.user)
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
        
        # Permission check: only author, journal_admin, or super_admin can update status
        if article.author != request.user and request.user.role not in ['journal_admin', 'super_admin']:
            if request.user.role == 'journal_admin':
                # Journal admin can only update articles in their journals
                if article.journal.journal_admin != request.user:
                    return Response(
                        {'error': 'Siz faqat o\'z jurnalingizdagi maqolalarni yangilashingiz mumkin'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Siz bu maqolani yangilash huquqiga egasiz'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': 'Status kiritilishi shart'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status value
        valid_statuses = [choice[0] for choice in Article.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Noto\'g\'ri status. Ruxsat etilgan statuslar: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
    
    @action(detail=True, methods=['post'])
    def check_plagiarism(self, request, pk=None):
        """Check article for plagiarism"""
        article = self.get_object()
        
        # Permission check: only author, journal_admin, or super_admin can check plagiarism
        if article.author != request.user and request.user.role not in ['journal_admin', 'super_admin']:
            if request.user.role == 'journal_admin':
                if article.journal.journal_admin != request.user:
                    return Response(
                        {'error': 'Siz faqat o\'z jurnalingizdagi maqolalarni tekshirishingiz mumkin'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Siz bu maqolani tekshirish huquqiga egasiz'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check if file exists
        if not article.final_pdf_path:
            return Response(
                {'error': 'Plagiat tekshiruvi uchun maqola fayli kerak'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Use the Gemini service to perform plagiarism check
            gemini_service = get_gemini_service()
            
            # Extract content from PDF file (simplified - in production, use proper PDF extraction)
            # For now, we'll use the simulation method, but in production this should use real plagiarism detection
            if article.final_pdf_path:
                # In production, extract actual content from PDF
                # For now, use placeholder
                result = gemini_service.check_plagiarism("Document content would be extracted from the file here")
            else:
                result = gemini_service.check_plagiarism("Sample document content")
            
            plagiarism_percentage = result.get('plagiarism_percentage', 0)
            ai_content_percentage = result.get('ai_content_percentage', 0)
            
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
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking plagiarism: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Plagiat tekshiruvida xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )