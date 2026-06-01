from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from config.jwt_cookies import attach_jwt_cookies, clear_jwt_cookies
from django.db import DatabaseError
from django.db.models import Count, Q, Sum
from rest_framework.exceptions import ParseError
from django.conf import settings
from apps.articles.models import Article, ActivityLog, ArticleSampleRequest
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
        requester = getattr(self.request.user, 'role', None)
        if requester in ('super_admin', 'accountant', 'journal_admin'):
            qs = User.objects.all().order_by('-date_joined')
            role_param = self.request.query_params.get('role')
            if role_param:
                qs = qs.filter(role=role_param)
            return qs
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='privacy-export')
    def privacy_export(self, request):
        """Shaxsiy ma'lumotlar xulosasi (GDPR uslubida — to'liq fayl eksporti emas)."""
        u = request.user
        articles_n = Article.objects.filter(author=u).count()
        tx_n = Transaction.objects.filter(user=u).count()
        return Response(
            {
                'user_id': str(u.id),
                'phone': getattr(u, 'phone', None),
                'email': getattr(u, 'email', None) or '',
                'role': getattr(u, 'role', None),
                'date_joined': u.date_joined.isoformat() if getattr(u, 'date_joined', None) else None,
                'counts': {
                    'articles': articles_n,
                    'transactions': tx_n,
                },
                'note': "To'liq ma'lumotnoma uchun administratorga murojaat qiling.",
            }
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='archive')
    def archive(self, request):
        """
        Muallifning arxiv hujjatlari: maqolalar (PDF, UDK, sertifikat), standalone UDK ma'lumotnomalar,
        taqrizchi/jurnal admin yuborgan taqriz natijalari. Barcha hujjatlar avtomatik shu ro'yxatda.
        """
        from django.conf import settings
        from apps.udc.models import UDKCertificate

        user = request.user

        # To'lov tasdiqlangan, lekin maqola/DOI hali "kutilmoqda" — arxiv ochilganda tuzatish
        try:
            from apps.articles.fulfill_publication_fee import repair_publication_fee_articles_for_user
            from apps.articles.fulfill_doi import repair_doi_requests_for_user
            repair_publication_fee_articles_for_user(user)
            repair_doi_requests_for_user(user)
        except Exception as repair_err:
            import logging
            logging.getLogger(__name__).warning('Archive payment repair failed: %s', repair_err)

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

        # 1. Maqolalar: har qanday yuborilgan maqola arxivda ko'rinsin.
        # Avval faqat final_pdf_path bo'lsa chiqardi; natijada yangi yuborilgan maqola "yo'qolib" qolardi.
        # Endi doim ro'yxatga qo'shamiz: fayl bo'lsa download_url, bo'lmasa article view_url.
        articles = Article.objects.filter(author=user).select_related('journal').order_by('-submission_date')
        for art in articles:
            title = (art.title or '')[:200]
            date_str = art.submission_date.isoformat() if art.submission_date else None
            article_view_url = f"/articles/{art.id}"
            pdf_url = file_url(art.final_pdf_path) if art.final_pdf_path else None
            completed_pub_fee = Transaction.objects.filter(
                article_id=art.id,
                service_type='publication_fee',
                status='completed',
            ).exists()
            pending_pub_fee = Transaction.objects.filter(
                article_id=art.id,
                service_type='publication_fee',
                status='pending',
            ).exists()
            if art.status == 'Draft' and pending_pub_fee and not completed_pub_fee:
                status_label = "Maqola yuborish — to'lov kutilmoqda"
            elif art.status == 'Draft' and completed_pub_fee:
                status_label = 'Maqola yuborish — taqrizchida'
            elif art.status in ('Yangi', 'WithEditor', 'QabulQilingan', 'PlagiarismReview'):
                status_label = 'Maqola yuborish — taqrizchida'
            elif art.status == 'Published':
                status_label = 'Maqola nashr etilgan'
            elif pdf_url:
                status_label = 'Maqola PDF'
            else:
                status_label = 'Maqola yuborildi'
            items.append({
                'type': 'article_pdf',
                'id': str(art.id),
                'article_id': str(art.id),
                'title': title,
                'label': status_label,
                'date': date_str,
                'download_url': pdf_url,
                'view_url': article_view_url,
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

        # 2c. UDK so'rovi (alohida buyurtma: to'lov → taqrizchi). Oldin faqat UDKCertificate qo'shilardi —
        # sertifikat taqrizchi yakunlaganda yaratiladi, shuning uchun "to'lov bo'ldi, arxiv bo'sh" muammosi bo'lardi.
        try:
            from apps.udc.models import (
                UdkRequest,
                UDK_REQUEST_STATUS_PENDING_PAYMENT,
                UDK_REQUEST_STATUS_SUBMITTED,
                UDK_REQUEST_STATUS_COMPLETED,
                UDK_REQUEST_STATUS_REJECTED,
            )

            for req in (
                UdkRequest.objects.filter(user=user)
                .exclude(status=UDK_REQUEST_STATUS_REJECTED)
                .order_by('-created_at')
            ):
                cert = None
                if getattr(req, 'transaction_id', None):
                    cert = UDKCertificate.objects.filter(transaction_id=req.transaction_id).first()
                if req.status == UDK_REQUEST_STATUS_COMPLETED and cert and cert.certificate_path:
                    continue

                title_short = (req.title or '')[:200]
                date_str = req.created_at.isoformat() if req.created_at else None
                status_label = {
                    UDK_REQUEST_STATUS_PENDING_PAYMENT: "UDK buyurtmasi — to'lov kutilmoqda",
                    UDK_REQUEST_STATUS_SUBMITTED: "UDK buyurtmasi — taqrizchida",
                    UDK_REQUEST_STATUS_COMPLETED: "UDK buyurtmasi — yakunlangan (PDF kutilmoqda)",
                }.get(req.status, "UDK buyurtmasi")

                dl = None
                if cert and cert.certificate_path:
                    dl = f"{api_base}/udc/certificates/{cert.id}/download/"

                items.append({
                    'type': 'udk_request_order',
                    'id': f"udkreq-{req.id}",
                    'title': title_short,
                    'label': status_label,
                    'date': date_str,
                    'download_url': dl,
                    'view_url': '/udk-olish',
                    'extra': {
                        'status': req.status,
                        'udk_code': (req.udk_code or '')[:120],
                    },
                })
        except Exception:
            pass

        # 2b. DOI so'rovlari (muallif doim holatini ko'rsin; link bo'lsa ochadi)
        try:
            from apps.articles.models import DoiRequest
            doi_requests = DoiRequest.objects.filter(user=user).order_by('-created_at')
            for dr in doi_requests:
                status_label = {
                    'pending_payment': "DOI — to'lov kutilmoqda",
                    'submitted': "DOI — taqrizchida",
                    'completed': "DOI raqami tayyor",
                }.get(dr.status, "DOI so'rovi")
                has_link = bool((dr.doi_link or '').strip())
                items.append({
                    'type': 'doi_link',
                    'id': f"doi-{dr.id}",
                    'title': f"DOI — {dr.author_last_name} {dr.author_first_name}",
                    'label': "DOI raqami" if has_link else status_label,
                    'date': (
                        dr.completed_at.isoformat() if dr.completed_at else
                        (dr.created_at.isoformat() if dr.created_at else None)
                    ),
                    'download_url': None,
                    'view_url': dr.doi_link if has_link else '/doi-olish',
                    'extra': {'doi_link': dr.doi_link, 'status': dr.status},
                })
        except Exception:
            pass

        # 2d. Maqola yozish xizmati (Article sample) — buyurtma holatini arxivda ko'rsatish
        try:
            sample_requests = ArticleSampleRequest.objects.filter(user=user).order_by('-created_at')
            for sr in sample_requests:
                status_label = {
                    'pending_payment': "Maqola yozish — to'lov kutilmoqda",
                    'submitted': "Maqola yozish — taqrizchida",
                    'in_progress': "Maqola yozish — jarayonda",
                    'completed': "Maqola yozish — yakunlangan",
                    'cancelled': "Maqola yozish — bekor qilingan",
                }.get(sr.status, "Maqola yozish buyurtmasi")
                items.append({
                    'type': 'article_sample_order',
                    'id': f"sample-{sr.id}",
                    'title': (sr.topic or sr.requirements or "Maqola yozish buyurtmasi")[:200],
                    'label': status_label,
                    'date': sr.created_at.isoformat() if sr.created_at else None,
                    'download_url': None,
                    'view_url': '/maqola-namuna-olish',
                    'extra': {
                        'status': sr.status,
                        'quality_level': sr.quality_level,
                        'pages': sr.pages,
                        'amount': float(sr.amount or 0),
                    },
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
            new_submissions=Count('id', filter=Q(status__in=['Yangi', 'WithEditor', 'Draft'])),
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


def register_impl(request):
    """Register a new user (implementation)."""
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
                body = {
                    'user': UserSerializer(user, context={'request': request}).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
                if not getattr(settings, 'JWT_RETURN_TOKENS_IN_JSON', True):
                    body = {'user': body['user']}
                resp = Response(body, status=status.HTTP_201_CREATED)
                if getattr(settings, 'JWT_USE_HTTPONLY_COOKIES', False):
                    attach_jwt_cookies(resp, str(refresh.access_token), str(refresh))
                return resp
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
        
        logger.warning("Registration validation failed")
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


def login_impl(request):
    """Login user (implementation)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        try:
            payload = request.data
        except ParseError:
            return Response(
                {
                    'non_field_errors': [
                        'So\'rov JSON formatida bo\'lishi kerak. Content-Type: application/json tekshiring.',
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payload:
            logger.error("No data provided in login request")
            return Response({
                'detail': 'No data provided',
                'non_field_errors': ['Telefon raqam va parol kiritilishi shart']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_value = payload.get('phone', 'N/A')
        has_password = bool(payload.get('password'))
        logger.info("Login attempt - phone prefix present: %s", bool(phone_value and str(phone_value) != 'N/A'))
        
        serializer = LoginSerializer(data=payload, context={'request': request})
        try:
            is_ok = serializer.is_valid()
        except DatabaseError:
            logger.exception("Login: database error during credential check")
            return Response(
                {
                    'non_field_errors': [
                        'Ma\'lumotlar bazasiga vaqtincha ulanib bo\'lmadi. Bir necha daqiqadan keyin urinib ko\'ring.',
                    ],
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        
        if is_ok:
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            logger.info("Login successful for user phone ending: %s", str(user.phone)[-4:])
            body = {
                'user': UserSerializer(user, context={'request': request}).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            if not getattr(settings, 'JWT_RETURN_TOKENS_IN_JSON', True):
                body = {'user': body['user']}
            resp = Response(body)
            if getattr(settings, 'JWT_USE_HTTPONLY_COOKIES', False):
                attach_jwt_cookies(resp, str(refresh.access_token), str(refresh))
            return resp
        logger.warning("Login validation failed (bad credentials or format)")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
    except DatabaseError:
        logger.exception("Login: database error")
        return Response(
            {
                'non_field_errors': [
                    'Ma\'lumotlar bazasiga vaqtincha ulanib bo\'lmadi. Bir necha daqiqadan keyin urinib ko\'ring.',
                ],
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", exc_info=True)
        return Response({
            'non_field_errors': ['Tizimga kirishda xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.'],
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        return login_impl(request)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        return register_impl(request)


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh = None
        if hasattr(request, 'data') and request.data:
            refresh = request.data.get('refresh')
        if not refresh:
            refresh = request.COOKIES.get(getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'refresh'))
        if refresh:
            try:
                tok = RefreshToken(refresh)
                tok.blacklist()
            except Exception:
                pass
        resp = Response({'detail': 'Sessiya yakunlandi.'})
        clear_jwt_cookies(resp)
        return resp