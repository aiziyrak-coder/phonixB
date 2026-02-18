from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Article, ArticleVersion, ActivityLog
from .serializers import ArticleSerializer, CreateArticleSerializer, ArticleVersionSerializer, PublicArticleShareSerializer
from apps.notifications.models import Notification
from django.utils import timezone
from apps.services import get_gemini_service
import logging
import os

logger = logging.getLogger(__name__)


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

    def perform_create(self, serializer):
        article = serializer.save()
        self._run_initial_plagiarism_check(article)

    def _run_initial_plagiarism_check(self, article):
        """Run advanced plagiarism/AI check right after article is created (best-effort)."""
        if not article.final_pdf_path:
            return

        try:
            gemini_service = get_gemini_service()

            try:
                file_path = article.final_pdf_path.path
            except Exception:
                from django.conf import settings
                file_path = os.path.join(settings.MEDIA_ROOT, str(article.final_pdf_path))

            if not os.path.exists(file_path):
                logger.warning(f"Plagiarism auto-check skipped: file not found at {file_path}")
                return

            text_content = gemini_service.extract_text_from_pdf(file_path)
            if not text_content or len(text_content.strip()) < 50:
                text_content = article.abstract or article.title or ""

            if not text_content or len(text_content.strip()) < 50:
                logger.warning(f"Plagiarism auto-check skipped: insufficient text for article {article.id}")
                return

            result = gemini_service.check_plagiarism(text_content)
            plagiarism_percentage = result.get('plagiarism_percentage', 0)
            ai_content_percentage = result.get('ai_content_percentage', 0)
            report = result.get('report', {})

            article.plagiarism_percentage = plagiarism_percentage
            article.ai_content_percentage = ai_content_percentage
            article.plagiarism_checked_at = timezone.now()
            article.plagiarism_report = report
            article.save(update_fields=[
                'plagiarism_percentage', 'ai_content_percentage',
                'plagiarism_checked_at', 'plagiarism_report'
            ])

            ActivityLog.objects.create(
                article=article,
                user=self.request.user,
                action='Plagiarism check completed',
                details=f'Plagiarism: {plagiarism_percentage}%, AI Content: {ai_content_percentage}%'
            )
        except Exception as e:
            logger.error(f"Auto plagiarism check failed for article {article.id}: {str(e)}", exc_info=True)
    
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

        # Auto-notify author about status change
        status_labels = dict(Article.STATUS_CHOICES)
        new_label = status_labels.get(new_status, new_status)
        try:
            Notification.notify(
                user=article.author,
                title='Maqola holati yangilandi',
                message=f'"{article.title}" maqolangiz holati "{new_label}" ga o\'zgartirildi.',
                notification_type='status_change',
                link=f'/articles/{article.id}',
                metadata={'article_id': str(article.id), 'old_status': old_status, 'new_status': new_status},
            )
        except Exception as e:
            logger.warning(f"Failed to send status notification: {e}")
        
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
            
            # Extract content from PDF file
            text_content = ""
            if article.final_pdf_path:
                try:
                    import os
                    from django.conf import settings
                    
                    # Get full file path
                    file_path = os.path.join(settings.MEDIA_ROOT, str(article.final_pdf_path))
                    
                    # Extract text from PDF
                    if os.path.exists(file_path):
                        text_content = gemini_service.extract_text_from_pdf(file_path)
                    else:
                        # Try alternative path
                        if hasattr(article, 'main_file') and article.main_file:
                            file_path = article.main_file.path
                            if os.path.exists(file_path):
                                text_content = gemini_service.extract_text_from_pdf(file_path)
                        
                        if not text_content:
                            logger.warning(f"PDF file not found at {file_path}, using article abstract")
                            text_content = article.abstract or article.title or ""
                except Exception as e:
                    logger.error(f"Error extracting PDF content: {e}", exc_info=True)
                    # Fallback to article text
                    text_content = article.abstract or article.title or ""
            else:
                # Use article text as fallback
                text_content = article.abstract or article.title or ""
            
            # Perform plagiarism check
            if not text_content or len(text_content.strip()) < 50:
                return Response(
                    {'error': 'Plagiat tekshiruvi uchun maqola matni yetarli emas. Iltimos, PDF faylni yuklang.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = gemini_service.check_plagiarism(text_content)
            
            plagiarism_percentage = result.get('plagiarism_percentage', 0)
            ai_content_percentage = result.get('ai_content_percentage', 0)
            report = result.get('report', {})
            
            article.plagiarism_percentage = plagiarism_percentage
            article.ai_content_percentage = ai_content_percentage
            article.plagiarism_checked_at = timezone.now()
            article.plagiarism_report = report
            article.save(update_fields=[
                'plagiarism_percentage', 'ai_content_percentage',
                'plagiarism_checked_at', 'plagiarism_report'
            ])
            
            ActivityLog.objects.create(
                article=article,
                user=request.user,
                action='Plagiarism check completed',
                details=f'Plagiarism: {plagiarism_percentage}%, AI Content: {ai_content_percentage}%'
            )
            
            return Response({
                'plagiarism': plagiarism_percentage,
                'ai_content': ai_content_percentage,
                'originality': result.get('originality', 0),
                'checked_at': article.plagiarism_checked_at,
                'report': report,
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking plagiarism: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Plagiat tekshiruvida xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([AllowAny])
def public_article_detail(request, pk):
    """Public endpoint for shared published article details."""
    article = Article.objects.select_related('author', 'journal').filter(
        pk=pk,
        status='Published'
    ).first()

    if not article:
        return Response({'detail': 'Maqola topilmadi yoki hali nashr etilmagan.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PublicArticleShareSerializer(article, context={'request': request})
    return Response(serializer.data)