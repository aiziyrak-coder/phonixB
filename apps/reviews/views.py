from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.http import HttpResponse
from .models import PeerReview
from .serializers import PeerReviewSerializer
from apps.notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


class PeerReviewViewSet(viewsets.ModelViewSet):
    queryset = PeerReview.objects.select_related('article', 'reviewer').all()
    serializer_class = PeerReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = PeerReview.objects.select_related('article', 'reviewer')
        if self.request.user.role == 'reviewer':
            return qs.filter(reviewer=self.request.user)
        elif self.request.user.role in ['super_admin', 'journal_admin']:
            return qs.all()
        return qs.filter(article__author=self.request.user)

    def perform_create(self, serializer):
        review = serializer.save(reviewer=self.request.user if self.request.user.role == 'reviewer' else serializer.validated_data.get('reviewer'))
        # Notify reviewer if assigned by admin
        if review.reviewer != self.request.user:
            try:
                Notification.notify(
                    user=review.reviewer,
                    title='Yangi taqriz tayinlandi',
                    message=f'Sizga "{review.article.title}" maqolasini taqrizlash tayinlandi.',
                    notification_type='review_assigned',
                    link=f'/articles/{review.article.id}',
                    metadata={'review_id': str(review.id), 'article_id': str(review.article.id)},
                )
            except Exception as e:
                logger.warning(f"Failed to send review assignment notification: {e}")

    @action(detail=True, methods=['post'])
    def accept_review(self, request, pk=None):
        """Reviewer accepts the review assignment."""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)
        review.status = 'in_progress'
        review.save(update_fields=['status'])
        return Response({'status': 'in_progress'})

    @action(detail=True, methods=['post'])
    def decline_review(self, request, pk=None):
        """Reviewer declines the review assignment."""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)
        review.status = 'declined'
        review.save(update_fields=['status'])
        return Response({'status': 'declined'})

    @action(detail=True, methods=['post'])
    def submit_review(self, request, pk=None):
        """Reviewer submits the completed review with scores."""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        review.review_content = data.get('review_content', review.review_content)
        review.recommendation = data.get('recommendation', '')
        review.originality_score = int(data.get('originality_score', 0))
        review.methodology_score = int(data.get('methodology_score', 0))
        review.clarity_score = int(data.get('clarity_score', 0))
        review.significance_score = int(data.get('significance_score', 0))
        review.references_score = int(data.get('references_score', 0))
        review.strengths = data.get('strengths', '')
        review.weaknesses = data.get('weaknesses', '')
        review.comments_to_author = data.get('comments_to_author', '')
        review.comments_to_editor = data.get('comments_to_editor', '')
        review.rating = review.overall_score
        review.status = 'completed'
        review.completed_at = timezone.now()
        review.save()

        # Notify article author
        try:
            Notification.notify(
                user=review.article.author,
                title='Taqriz yakunlandi',
                message=f'"{review.article.title}" maqolangiz uchun taqriz yakunlandi.',
                notification_type='review_completed',
                link=f'/articles/{review.article.id}',
                metadata={'review_id': str(review.id), 'article_id': str(review.article.id)},
            )
        except Exception as e:
            logger.warning(f"Failed to send review completion notification: {e}")

        # Notify journal admin
        try:
            if review.article.journal and review.article.journal.journal_admin:
                Notification.notify(
                    user=review.article.journal.journal_admin,
                    title='Taqriz yakunlandi',
                    message=f'"{review.article.title}" maqolasi uchun taqriz yakunlandi. Tavsiya: {review.get_recommendation_display() if review.recommendation else "Belgilanmagan"}',
                    notification_type='review_completed',
                    link=f'/articles/{review.article.id}',
                    metadata={'review_id': str(review.id)},
                )
        except Exception as e:
            logger.warning(f"Failed to send admin review notification: {e}")

        return Response(PeerReviewSerializer(review).data)

    @action(detail=True, methods=['get'], url_path='review-document')
    def review_document(self, request, pk=None):
        """Taqriz natijasini matn fayl sifatida yuklab olish (muallif uchun)."""
        review = self.get_object()
        if review.article.author_id != request.user.id and request.user.role not in ('super_admin', 'journal_admin'):
            return Response({'error': 'Huquq yo\'q.'}, status=status.HTTP_403_FORBIDDEN)
        lines = [
            f"Maqola: {review.article.title}",
            f"Taqrizchi: {review.reviewer.get_full_name() if review.reviewer else ''}",
            f"Yakunlangan: {review.completed_at.strftime('%Y-%m-%d %H:%M') if review.completed_at else ''}",
            "",
            "--- Taqriz matni ---",
            review.review_content or "(yo'q)",
            "",
            "--- Muallifga izohlar ---",
            review.comments_to_author or "(yo'q)",
            "",
            "--- Kuchli tomonlar ---",
            review.strengths or "(yo'q)",
            "",
            "--- Zaif tomonlar ---",
            review.weaknesses or "(yo'q)",
            "",
            "--- Ballar ---",
            f"Originality: {review.originality_score}, Methodology: {review.methodology_score}",
            f"Clarity: {review.clarity_score}, Significance: {review.significance_score}, References: {review.references_score}",
            f"Umumiy: {review.rating}",
        ]
        if review.recommendation:
            rec_display = getattr(review, 'get_recommendation_display', lambda: review.recommendation)()
            lines.append(f"\nTavsiya: {rec_display}")
        text = "\n".join(lines)
        response = HttpResponse(text, content_type='text/plain; charset=utf-8')
        safe_title = "".join(c for c in (review.article.title or "")[:50] if c.isalnum() or c in " _-").strip() or "maqola"
        response['Content-Disposition'] = f'attachment; filename="taqriz_{safe_title}_{review.id}.txt"'
        return response
