from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q, Sum
from django.conf import settings
from apps.articles.models import Article, ActivityLog
from apps.payments.models import Transaction
from apps.journals.models import Journal
from apps.translations.models import TranslationRequest
from apps.reviews.models import PeerReview
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, UserProfileSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users. List/retrieve/update/delete only for super_admin."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        role = getattr(self.request.user, 'role', None)
        if role in ('super_admin', 'accountant', 'journal_admin'):
            return User.objects.all().order_by('-date_joined')
        return User.objects.filter(id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        role = getattr(request.user, 'role', None)
        if role not in ('super_admin', 'accountant', 'journal_admin'):
            return Response({'detail': 'Faqat bosh administrator, buxgalter yoki jurnal administratori foydalanuvchilar ro\'yxatini ko\'rishi mumkin.'}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'super_admin':
            return Response({'detail': 'Faqat bosh administrator yangi foydalanuvchi qo\'sha oladi.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'super_admin' and str(kwargs.get('pk')) != str(request.user.id):
            return Response({'detail': 'Huquq yo\'q.'}, status=status.HTTP_403_FORBIDDEN)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'super_admin' and str(kwargs.get('pk')) != str(request.user.id):
            return Response({'detail': 'Faqat o\'z profilingizni tahrirlashingiz mumkin.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'super_admin':
            return Response({'detail': 'Faqat bosh administrator foydalanuvchini o\'chira oladi.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == 'profile':
            return UserProfileSerializer
        return UserSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Get current user profile"""
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update current user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='archive')
    def archive(self, request):
        """
        Muallifning arxiv hujjatlari: maqolalar (PDF, UDK, sertifikat), standalone UDK ma'lumotnomalar,
        taqrizchi/jurnal admin yuborgan taqriz natijalari. Barcha hujjatlar avtomatik shu ro'yxatda.
        """
        from django.conf import settings
        from apps.udc.models import UDKCertificate

        user = request.user
        items = []
        media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
        base_url = request.build_absolute_uri('/').rstrip('/')
        if not base_url.endswith('/api/v1'):
            api_base = base_url + '/api/v1'
        else:
            api_base = base_url

        def file_url(field):
            if not field:
                return None
            try:
                return request.build_absolute_uri(field.url)
            except Exception:
                path = str(field).lstrip('/')
                return f"{base_url.replace('/api/v1', '')}{media_url}/{path}" if path else None

        # 1. Maqolalar: PDF, UDK ma'lumotnoma, nashr sertifikati
        articles = Article.objects.filter(author=user).select_related('journal').order_by('-submission_date')
        for art in articles:
            title = (art.title or '')[:200]
            date_str = art.submission_date.isoformat() if art.submission_date else None
            if art.final_pdf_path:
                items.append({
                    'type': 'article_pdf',
                    'id': str(art.id),
                    'article_id': str(art.id),
                    'title': title,
                    'label': 'Maqola PDF',
                    'date': date_str,
                    'download_url': file_url(art.final_pdf_path),
                    'extra': {'journal': art.journal.name if art.journal else None, 'status': art.status},
                })
            if art.udk_certificate_path:
                items.append({
                    'type': 'udk_certificate',
                    'id': f"art-udk-{art.id}",
                    'article_id': str(art.id),
                    'title': title,
                    'label': "UDK ma'lumotnoma",
                    'date': date_str,
                    'download_url': file_url(art.udk_certificate_path),
                    'extra': {'udk_code': art.udk_code},
                })
            cert_url = art.publication_certificate_url or art.certificate_url
            if cert_url:
                if not cert_url.startswith('http'):
                    cert_url = cert_url if cert_url.startswith('/') else f"/{cert_url}"
                    cert_url = base_url.replace('/api/v1', '') + cert_url
                items.append({
                    'type': 'publication_certificate',
                    'id': f"art-cert-{art.id}",
                    'article_id': str(art.id),
                    'title': title,
                    'label': "Nashr sertifikati",
                    'date': date_str,
                    'download_url': cert_url,
                    'extra': {},
                })

        # 2. Standalone UDK ma'lumotnomalar (auth talab qilinadigan download endpoint)
        try:
            udk_certs = UDKCertificate.objects.filter(user=user).order_by('-created_at')
            for c in udk_certs:
                url = f"{api_base}/udc/certificates/{c.id}/download/" if c.certificate_path else None
                items.append({
                    'type': 'udk_standalone',
                    'id': f"udk-{c.id}",
                    'certificate_id': c.id,
                    'title': (c.title or '')[:200],
                    'label': "UDK ma'lumotnoma",
                    'date': c.created_at.isoformat() if c.created_at else None,
                    'download_url': url,
                    'extra': {'udk_code': c.udk_code, 'document_number': getattr(c, 'document_number', None)},
                })
        except Exception:
            pass

        # 2b. DOI so'rovlari (tugallangan — muallif o'z DOI linkini ko'radi)
        try:
            from apps.articles.models import DoiRequest
            doi_requests = DoiRequest.objects.filter(user=user, status='completed').order_by('-completed_at')
            for dr in doi_requests:
                if dr.doi_link:
                    items.append({
                        'type': 'doi_link',
                        'id': f"doi-{dr.id}",
                        'title': f"DOI — {dr.author_last_name} {dr.author_first_name}",
                        'label': "DOI raqami",
                        'date': dr.completed_at.isoformat() if dr.completed_at else None,
                        'download_url': None,
                        'view_url': dr.doi_link,
                        'extra': {'doi_link': dr.doi_link},
                    })
        except Exception:
            pass

        # 3. Taqriz natijalari (taqrizchi/jurnal admin yuborgan — muallifning maqolalari uchun)
        reviews = PeerReview.objects.filter(
            article__author=user,
            status='completed'
        ).select_related('article', 'reviewer').order_by('-completed_at')
        for r in reviews:
            art_title = (r.article.title or '')[:150]
            items.append({
                'type': 'review_result',
                'id': f"review-{r.id}",
                'review_id': str(r.id),
                'article_id': str(r.article_id),
                'title': f"{art_title} — Taqriz natijasi",
                'label': "Taqriz natijasi",
                'date': r.completed_at.isoformat() if r.completed_at else None,
                'download_url': f"{api_base}/reviews/{r.id}/review-document/",
                'view_url': f"/articles/{r.article_id}",
                'extra': {
                    'reviewer_name': r.reviewer.get_full_name() if r.reviewer else '',
                    'recommendation': getattr(r, 'recommendation', '') or '',
                },
            })

        # Sana bo'yicha kamayish
        items.sort(key=lambda x: (x['date'] or ''), reverse=True)

        return Response({
            'items': items,
            'total': len(items),
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get platform statistics for super admin dashboard"""
        if request.user.role != 'super_admin':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Optimize queries - use select_related and prefetch_related where possible
        # Get user statistics (optimized with single query)
        user_stats = User.objects.aggregate(
            total=Count('id'),
            authors=Count('id', filter=Q(role='author')),
            reviewers=Count('id', filter=Q(role='reviewer'))
        )
        total_users = user_stats['total'] or 0
        authors_count = user_stats['authors'] or 0
        reviewers_count = user_stats['reviewers'] or 0
        
        # Get article statistics (optimized with single query)
        article_stats = Article.objects.aggregate(
            total=Count('id'),
            new_submissions=Count('id', filter=Q(status__in=['Yangi', 'WithEditor'])),
            in_review=Count('id', filter=Q(status='QabulQilingan')),
            published=Count('id', filter=Q(status='Published')),
            rejected=Count('id', filter=Q(status='Rejected'))
        )
        total_articles = article_stats['total'] or 0
        new_submissions = article_stats['new_submissions'] or 0
        in_review = article_stats['in_review'] or 0
        published = article_stats['published'] or 0
        rejected = article_stats['rejected'] or 0
        
        # Get financial statistics (optimized)
        financial_stats = Transaction.objects.filter(
            status='completed'
        ).exclude(
            service_type='top_up'
        ).aggregate(
            total_revenue=Sum('amount'),
            total_count=Count('id')
        )
        total_revenue = abs(float(financial_stats['total_revenue'] or 0))
        total_transactions = financial_stats['total_count'] or 0

        # Book publication order statistics
        book_orders_qs = Transaction.objects.filter(service_type='book_publication')
        book_orders_total = book_orders_qs.count()
        book_orders_completed = book_orders_qs.filter(status='completed').count()
        book_orders_pending = book_orders_qs.filter(status='pending').count()
        book_orders_failed = book_orders_qs.filter(status='failed').count()
        book_revenue_stats = book_orders_qs.filter(status='completed').aggregate(
            total_revenue=Sum('amount')
        )
        book_total_revenue = abs(float(book_revenue_stats['total_revenue'] or 0))
        
        # Get journal admin statistics (optimized with select_related)
        journal_admins = User.objects.filter(role='journal_admin').select_related()
        journal_admin_stats = []
        for admin in journal_admins:
            # Use optimized query with select_related
            published_count = Article.objects.filter(
                journal__journal_admin=admin,
                status='Published'
            ).count()
            journal_admin_stats.append({
                'id': str(admin.id),
                'first_name': admin.first_name or '',
                'last_name': admin.last_name or '',
                'avatar_url': admin.avatar_url.url if (admin.avatar_url and hasattr(admin.avatar_url, 'url')) else None,
                'published_count': published_count
            })
        
        stats_data = {
            'users': {
                'total': total_users,
                'authors': authors_count,
                'reviewers': reviewers_count
            },
            'articles': {
                'total': total_articles,
                'new_submissions': new_submissions,
                'in_review': in_review,
                'published': published,
                'rejected': rejected
            },
            'finance': {
                'total_revenue': total_revenue,
                'total_transactions': total_transactions,
                'book_orders_total': book_orders_total,
                'book_orders_completed': book_orders_completed,
                'book_orders_pending': book_orders_pending,
                'book_orders_failed': book_orders_failed,
                'book_total_revenue': book_total_revenue,
            },
            'journal_admins': journal_admin_stats
        }
        
        return Response(stats_data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def activity(self, request, pk=None):
        """Get user activity, stats and history (super_admin only)."""
        if getattr(request.user, 'role', None) != 'super_admin':
            return Response({'detail': 'Faqat bosh administrator foydalanuvchi faoliyatini ko\'rishi mumkin.'}, status=status.HTTP_403_FORBIDDEN)
        target = self.get_object()

        # Articles (as author)
        articles_qs = Article.objects.filter(author=target).order_by('-submission_date')
        articles_by_status = dict(articles_qs.values('status').annotate(c=Count('id')).values_list('status', 'c'))
        articles_total = articles_qs.count()
        recent_articles = []
        for a in articles_qs[:15]:
            recent_articles.append({
                'id': str(a.id),
                'title': a.title,
                'status': a.status,
                'submission_date': a.submission_date.isoformat() if a.submission_date else None,
            })

        # Translations (as author)
        trans_qs = TranslationRequest.objects.filter(author=target).order_by('-submission_date')
        translations_total = trans_qs.count()
        recent_translations = []
        for t in trans_qs[:15]:
            recent_translations.append({
                'id': str(t.id),
                'title': t.title,
                'status': t.status,
                'source_language': t.source_language,
                'target_language': t.target_language,
                'submission_date': t.submission_date.isoformat() if t.submission_date else None,
            })

        # Peer reviews (as reviewer)
        reviews_qs = PeerReview.objects.filter(reviewer=target).select_related('article').order_by('-assigned_at')
        reviews_total = reviews_qs.count()
        reviews_by_status = dict(reviews_qs.values('status').annotate(c=Count('id')).values_list('status', 'c'))
        recent_reviews = []
        for r in reviews_qs[:15]:
            recent_reviews.append({
                'id': str(r.id),
                'article_title': r.article.title if r.article_id else None,
                'article_id': str(r.article_id) if r.article_id else None,
                'status': r.status,
                'assigned_at': r.assigned_at.isoformat() if r.assigned_at else None,
            })

        # Transactions (payments / xizmatlar)
        tx_qs = Transaction.objects.filter(user=target).order_by('-created_at')
        transactions_total = tx_qs.count()
        tx_by_service = dict(tx_qs.values('service_type').annotate(c=Count('id')).values_list('service_type', 'c'))
        tx_by_status = dict(tx_qs.values('status').annotate(c=Count('id')).values_list('status', 'c'))
        recent_transactions = []
        for tx in tx_qs[:15]:
            recent_transactions.append({
                'id': str(tx.id),
                'service_type': tx.service_type,
                'status': tx.status,
                'amount': float(tx.amount),
                'currency': tx.currency,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
            })

        # Activity log (user's actions on articles)
        activity_logs_qs = ActivityLog.objects.filter(user=target).select_related('article').order_by('-timestamp')[:50]
        activity_timeline = []
        for log in activity_logs_qs:
            activity_timeline.append({
                'id': str(log.id),
                'action': log.action,
                'details': log.details or '',
                'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                'article_title': log.article.title if log.article_id else None,
                'article_id': str(log.article_id) if log.article_id else None,
            })

        return Response({
            'stats': {
                'articles_total': articles_total,
                'articles_by_status': articles_by_status,
                'translations_total': translations_total,
                'reviews_total': reviews_total,
                'reviews_by_status': reviews_by_status,
                'transactions_total': transactions_total,
                'transactions_by_service': tx_by_service,
                'transactions_by_status': tx_by_status,
            },
            'recent_articles': recent_articles,
            'recent_translations': recent_translations,
            'recent_reviews': recent_reviews,
            'recent_transactions': recent_transactions,
            'activity_timeline': activity_timeline,
        })


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def register(request):
    """Register a new user"""
    import logging
    import json
    logger = logging.getLogger(__name__)
    
    try:
        # Log incoming request data
        logger.info(f"=== Registration request received ===")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Method: {request.method}")
        logger.info(f"Has request.data: {hasattr(request, 'data')}")
        
        # Parse request data - DRF should handle this, but ensure it works
        data = None
        if hasattr(request, 'data') and request.data:
            data = request.data
            logger.info(f"Using request.data with keys: {list(data.keys()) if hasattr(data, 'keys') else 'non-dict payload'}")
        elif hasattr(request, 'body') and request.body:
            try:
                data = json.loads(request.body.decode('utf-8'))
                logger.info(f"Parsed request body with keys: {list(data.keys()) if isinstance(data, dict) else 'non-dict payload'}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"JSON decode error: {e}, body: {request.body[:200]}")
                return Response({'detail': 'Invalid JSON format', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            logger.error("No request data found - both request.data and request.body are empty")
            return Response({'detail': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not data:
            logger.error("Data is None or empty after parsing")
            return Response({'detail': 'No data provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"Processing registration with data: {list(data.keys())}")
        serializer = RegisterSerializer(data=data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                logger.info(f"✅ User registered successfully: {user.phone}, {user.email}")
                return Response({
                    'user': UserSerializer(user, context={'request': request}).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }, status=status.HTTP_201_CREATED)
            except Exception as db_error:
                import traceback
                from django.db import IntegrityError
                error_trace = traceback.format_exc()
                logger.error(f"❌ Database error during registration: {str(db_error)}")
                logger.error(f"Traceback: {error_trace}")
                
                # Handle unique constraint violations
                if isinstance(db_error, IntegrityError):
                    error_msg = str(db_error)
                    if 'phone' in error_msg.lower() or 'users_user.phone' in error_msg:
                        return Response({
                            'phone': ['Bu telefon raqam allaqachon ro\'yxatdan o\'tgan']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    elif 'email' in error_msg.lower() or 'users_user.email' in error_msg:
                        return Response({
                            'email': ['Bu email allaqachon ro\'yxatdan o\'tgan']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({
                            'detail': 'Bu ma\'lumotlar allaqachon mavjud',
                            'error': error_msg
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Don't expose internal error details to user
                    logger.error(f"Database error (non-IntegrityError): {str(db_error)}")
                    return Response({
                        'detail': 'Ro\'yxatdan o\'tishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.warning(f"Registration validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Registration exception: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        # Don't expose internal error details to user
        return Response({
            'detail': 'Ro\'yxatdan o\'tishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def login(request):
    """Login user"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # DRF automatically parses request.data for JSON requests
        # Check if data exists
        if not request.data:
            logger.error("No data provided in login request")
            return Response({
                'detail': 'No data provided',
                'non_field_errors': ['Telefon raqam va parol kiritilishi shart']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log the incoming data for debugging
        phone_value = request.data.get('phone', 'N/A')
        has_password = bool(request.data.get('password'))
        logger.info(f"Login attempt - phone: {str(phone_value)[:15]}..., has password: {has_password}")
        
        # Use DRF's standard serializer validation
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info(f"Login successful for user: {user.phone}")
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            logger.warning(f"Login validation failed: {serializer.errors}")
            # Return detailed validation errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", exc_info=True)
        return Response({
            'non_field_errors': ['Tizimga kirishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'],
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)