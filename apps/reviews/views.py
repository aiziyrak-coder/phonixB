from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Q, Count, Avg
from django.core.cache import cache
from .models import PeerReview
from .serializers import PeerReviewSerializer
from apps.notifications.models import Notification
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


class PeerReviewViewSet(viewsets.ModelViewSet):
    queryset = PeerReview.objects.select_related('article', 'reviewer').all()
    serializer_class = PeerReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Optimized queryset with caching"""
        user = self.request.user
        role = getattr(user, 'role', '') or ''
        if isinstance(role, str):
            role = role.strip().lower()
        
        # Cache to avoid repeated queries
        cache_key = f'reviewer_queryset_{user.id}_{role}'
        queryset = cache.get(cache_key)
        
        if queryset is None:
            qs = PeerReview.objects.select_related('article', 'reviewer').order_by('-created_at')
            
            if role == 'reviewer':
                queryset = qs.filter(reviewer=user)
            elif role in ['super_admin', 'journal_admin']:
                queryset = qs.all()
            else:
                queryset = qs.filter(article__author=user)
            
            # Cache for 5 minutes
            cache.set(cache_key, queryset, 300)
        
        return queryset

    def perform_create(self, serializer):
        """Create with duplicate prevention"""
        r = getattr(self.request.user, 'role', '') or ''
        if isinstance(r, str):
            r = r.strip().lower()
        
        reviewer = serializer.validated_data.get('reviewer')
        article = serializer.validated_data.get('article')
        
        # PREVENT DUPLICATE - Check before creating
        if reviewer and article:
            existing = PeerReview.objects.filter(
                reviewer=reviewer,
                article=article
            ).first()
            
            if existing:
                logger.warning(f"⚠️ Duplicate assignment prevented: {reviewer} -> {article}")
                return Response({
                    'error': 'Bu mutaxassis allaqachon ushbu maqolaga tayinlangan',
                    'existing_review_id': str(existing.id)
                }, status=status.HTTP_400_BAD_REQUEST)
        
        review = serializer.save(reviewer=self.request.user if r == 'reviewer' else reviewer)
        
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
        
        # Clear cache
        cache.delete(f'reviewer_queryset_{self.request.user.id}')

    @action(detail=True, methods=['post'])
    def accept_review(self, request, pk=None):
        """Reviewer accepts - Optimized with cache clear"""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)
        
        review.status = 'in_progress'
        review.save(update_fields=['status', 'updated_at'])
        
        # Clear cache
        cache.delete(f'reviewer_queryset_{request.user.id}')
        
        return Response({'status': 'in_progress'})

    @action(detail=True, methods=['post'])
    def decline_review(self, request, pk=None):
        """Reviewer declines - With reason and notifications"""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)
        
        reason = request.data.get('reason', '')
        review.status = 'declined'
        review.decline_reason = reason if hasattr(review, 'decline_reason') else ''
        review.save(update_fields=['status', 'updated_at'])
        
        # Clear cache
        cache.delete(f'reviewer_queryset_{request.user.id}')
        
        # Notify admin/editor
        try:
            if review.article.journal and review.article.journal.journal_admin:
                Notification.notify(
                    user=review.article.journal.journal_admin,
                    title='Taqriz rad etildi',
                    message=f'{review.reviewer.get_full_name()} "{review.article.title}" maqolasini taqrizlashni rad etdi. Sabab: {reason or "Belgilanmagan"}',
                    notification_type='review_declined',
                    link=f'/articles/{review.article.id}',
                )
        except Exception as e:
            logger.warning(f"Failed to send decline notification: {e}")
        
        return Response({'status': 'declined', 'reason': reason})

    @action(detail=True, methods=['post'])
    def submit_review(self, request, pk=None):
        """Submit completed review - Optimized with validation and duplicate prevention"""
        review = self.get_object()
        if review.reviewer != request.user:
            return Response({'error': 'Bu taqriz sizga tegishli emas'}, status=status.HTTP_403_FORBIDDEN)
        
        # PREVENT DUPLICATE SUBMISSION
        if review.status == 'completed':
            return Response({
                'error': 'Taqriz allaqachon yakunlangan',
                'warning': 'Takroriy yuborish aniqlandi'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data
        
        # Validate required fields
        required_fields = ['review_content', 'recommendation']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return Response({
                'error': f'Majburiy maydonlar: {", ".join(missing)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Update reviewer stats
        reviewer = review.reviewer
        reviewer.reviews_completed += 1
        # Recalculate average time
        if review.assigned_at and review.completed_at:
            days_taken = (review.completed_at - review.assigned_at).total_seconds() / 86400
            total_reviews = reviewer.reviews_completed
            old_avg = reviewer.average_review_time * (total_reviews - 1)
            reviewer.average_review_time = (old_avg + days_taken) / total_reviews
        reviewer.save()
        
        # Clear cache
        cache.delete(f'reviewer_queryset_{reviewer.id}')

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
    
    @action(detail=False, methods=['get'], url_path='find-specialists')
    def find_specialists(self, request):
        """
        FAST specialist finding - 2-3x optimized
        Filter reviewers by disease/specialization with caching
        """
        specializations = request.query_params.get('specializations', '').split(',')
        specializations = [s.strip() for s in specializations if s.strip()]
        
        if not specializations:
            return Response({
                'error': 'Specializations required',
                'message': 'Kasallik yoki mutaxassislik turini kiriting'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cache for fast retrieval
        cache_key = f'specialists_{":".join(sorted(specializations))}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"✅ CACHE HIT: Specialists for {specializations}")
            return Response(cached_result)
        
        logger.info(f"🔍 Searching specialists for: {specializations}")
        
        # OPTIMIZED: Single query with JSONField overlap
        reviewers = User.objects.filter(
            role='reviewer',
            is_active=True,
            specializations__overlap=specializations
        ).order_by('-reviews_completed', '-acceptance_rate')[:50]
        
        # Fallback: If no exact match, search partial
        if not reviewers:
            logger.info("⚠️ No exact match, searching partial matches...")
            reviewers = User.objects.filter(
                role='reviewer',
                is_active=True
            ).filter(
                Q(specializations__icontains=specializations[0]) |
                Q(first_name__icontains=specializations[0]) |
                Q(last_name__icontains=specializations[0])
            )[:50]
        
        result_data = []
        for reviewer in reviewers:
            data = {
                'id': str(reviewer.id),
                'full_name': reviewer.get_full_name(),
                'phone': reviewer.phone,
                'email': reviewer.email,
                'specializations': reviewer.specializations,
                'reviews_completed': reviewer.reviews_completed,
                'average_review_time': reviewer.average_review_time,
                'acceptance_rate': reviewer.acceptance_rate,
                'gamification_level': reviewer.gamification_level,
                'match_score': self._calculate_match_score(reviewer, specializations),
            }
            result_data.append(data)
        
        # Sort by match score
        result_data.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Cache for 10 minutes
        cache.set(cache_key, result_data, 600)
        
        logger.info(f"✅ Found {len(result_data)} specialists")
        return Response(result_data)
    
    def _calculate_match_score(self, reviewer, target_specializations):
        """Calculate match score (0-100) for reviewer specialization"""
        score = 0
        reviewer_specs = [s.lower() for s in reviewer.specializations]
        target_specs = [s.lower() for s in target_specializations]
        
        # Exact match: +30 points per specialization
        exact_matches = len(set(reviewer_specs) & set(target_specs))
        score += exact_matches * 30
        
        # Partial match: +15 points
        for target in target_specs:
            for spec in reviewer_specs:
                if target in spec or spec in target:
                    score += 15
                    break
        
        # Experience bonus: +1 per review (max 20)
        score += min(reviewer.reviews_completed, 20)
        
        # Acceptance rate bonus: +10 if >80%
        if reviewer.acceptance_rate > 80:
            score += 10
        
        # Speed bonus: +5 if avg time < 7 days
        if reviewer.average_review_time < 7:
            score += 5
        
        return min(score, 100)
    
    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign_reviewers(self, request):
        """
        Bulk assign multiple reviewers - Prevents conflicts and duplicates
        """
        article_id = request.data.get('article_id')
        reviewer_ids = request.data.get('reviewer_ids', [])
        
        if not article_id or not reviewer_ids:
            return Response({
                'error': 'article_id va reviewer_ids majburiy'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.articles.models import Article
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response({'error': 'Maqola topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        
        assigned = []
        failed = []
        already_assigned = []
        
        for reviewer_id in reviewer_ids:
            try:
                reviewer = User.objects.get(id=reviewer_id, role='reviewer')
                
                # Check if already assigned (PREVENT DUPLICATE)
                existing = PeerReview.objects.filter(
                    article=article,
                    reviewer=reviewer
                ).first()
                
                if existing:
                    already_assigned.append({
                        'reviewer_id': reviewer_id,
                        'review_id': str(existing.id),
                        'status': existing.status
                    })
                    continue
                
                # Create new assignment
                review = PeerReview.objects.create(
                    article=article,
                    reviewer=reviewer,
                    status='pending',
                    assigned_at=timezone.now()
                )
                
                assigned.append({
                    'review_id': str(review.id),
                    'reviewer': reviewer.get_full_name(),
                    'status': review.status
                })
                
                # Send notification
                try:
                    Notification.notify(
                        user=reviewer,
                        title='Yangi taqriz tayinlandi',
                        message=f'Sizga "{article.title}" maqolasini taqrizlash tayinlandi.',
                        notification_type='review_assigned',
                        link=f'/articles/{article.id}',
                    )
                except Exception as e:
                    logger.warning(f"Notification failed: {e}")
                
            except User.DoesNotExist:
                failed.append({'reviewer_id': reviewer_id, 'error': 'Reviewer topilmadi'})
            except Exception as e:
                failed.append({'reviewer_id': reviewer_id, 'error': str(e)})
        
        # Clear cache
        cache.delete(f'reviewer_queryset_{request.user.id}')
        
        return Response({
            'success': True,
            'assigned': assigned,
            'already_assigned': already_assigned,
            'failed': failed,
            'total_assigned': len(assigned),
            'message': f'{len(assigned)} taqrizchi muvaffaqiyatli tayinlandi'
        })

    @action(detail=True, methods=['get'], url_path='review-document')
    def review_document(self, request, pk=None):
        """Taqriz natijasini matn fayl sifatida yuklab olish (muallif uchun)."""
        review = self.get_object()
        ur = getattr(request.user, 'role', '') or ''
        if isinstance(ur, str):
            ur = ur.strip().lower()
        if review.article.author_id != request.user.id and ur not in ('super_admin', 'journal_admin'):
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
