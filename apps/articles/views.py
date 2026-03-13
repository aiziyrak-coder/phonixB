from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Article, ArticleVersion, ActivityLog, ArticleSampleRequest, DoiRequest
from .serializers import ArticleSerializer, ArticleListSerializer, CreateArticleSerializer, ArticleVersionSerializer, PublicArticleShareSerializer, DoiRequestSerializer, ArticleSampleRequestSerializer
from apps.notifications.models import Notification
from apps.payments.models import Transaction
from apps.journals.models import Journal
from django.utils import timezone
from apps.services import get_gemini_service
import logging
import os

logger = logging.getLogger(__name__)


def _check_plagiarism_thresholds(article):
    """
    Jurnal belgilangan limitlar bo'yicha tekshiruv.
    Returns: ('accept' | 'reject' | 'review', reason_message).
    - accept: barcha talablar bajarilgan, nashrga yuborish mumkin.
    - reject: uchala talab ham bajarilmagan, avtomatik rad.
    - review: 1 yoki 2 ta bajarilmagan — bosh admin qaror qiladi.
    """
    journal = article.journal
    if journal is None:
        return 'accept', ''
    pmax = getattr(journal, 'plagiarism_max_percent', None)
    amax = getattr(journal, 'ai_content_max_percent', None)
    omin = getattr(journal, 'originality_min_percent', None)
    if pmax is None and amax is None and omin is None:
        return 'accept', ''
    plag = getattr(article, 'plagiarism_percentage', 0) or 0
    ai = getattr(article, 'ai_content_percentage', 0) or 0
    orig = getattr(article, 'originality_percentage', None)
    if orig is None and article.plagiarism_checked_at:
        orig = max(0, 100 - plag)
    elif orig is None:
        orig = max(0, 100 - plag)
    pass_plag = (pmax is None or plag <= pmax)
    pass_ai = (amax is None or ai <= amax)
    pass_orig = (omin is None or orig >= omin)
    passed = sum([pass_plag, pass_ai, pass_orig])
    failed = 3 - passed
    if passed == 3:
        return 'accept', ''
    if failed == 3:
        return 'reject', (
            f'Plagiat: {plag:.1f}% (limit {pmax}%), AI: {ai:.1f}% (limit {amax}%), '
            f'Originalilik: {orig:.1f}% (min {omin}%). Uchala talab bajarilmadi.'
        )
    return 'review', (
        f'Plagiat: {plag:.1f}% (limit {pmax or "-"}), AI: {ai:.1f}% (limit {amax or "-"}), '
        f'Originalilik: {orig:.1f}% (min {omin or "-"}). Bosh administrator qarori kerak.'
    )


class ArticleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing articles"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """List articles with defensive error handling to avoid 500."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.exception("Article list failed: %s", e)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        # Optimize queries with select_related and prefetch_related
        base_queryset = Article.objects.select_related(
            'author', 'journal', 'journal__journal_admin', 'published_by'
        ).prefetch_related(
            'versions', 'activity_logs', 'peer_reviews'
        )
        role = getattr(self.request.user, 'role', None) or 'author'
        if role == 'super_admin':
            return base_queryset.all()
        elif role == 'journal_admin':
            return base_queryset.filter(journal__journal_admin=self.request.user)
        elif role == 'author':
            return base_queryset.filter(author=self.request.user)
        return Article.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateArticleSerializer
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleSerializer

    def create(self, request, *args, **kwargs):
        """For pre-payment journals, require a completed publication_fee transaction before creating article."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        journal_id = serializer.validated_data.get('journal')
        if journal_id:
            try:
                journal = Journal.objects.get(pk=journal_id)
                has_fee = (journal.publication_fee and float(journal.publication_fee) > 0) or (
                    journal.price_per_page and float(journal.price_per_page) > 0
                )
                if journal.payment_model == 'pre-payment' and has_fee:
                    tx_id = request.data.get('payment_transaction_id')
                    if not tx_id:
                        return Response(
                            {'detail': 'Ushbu jurnal oldindan to\'lov talab qiladi. To\'lovni amalga oshiring va to\'lovni tekshirish tugmasini bosing.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    try:
                        tx = Transaction.objects.get(id=tx_id)
                    except (Transaction.DoesNotExist, ValueError, TypeError):
                        return Response(
                            {'detail': 'To\'lov tranzaksiyasi topilmadi yoki noto\'g\'ri. To\'lovni qayta tekshiring.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    if tx.user_id != request.user.id:
                        return Response({'detail': 'Ushbu to\'lov sizga tegishli emas.'}, status=status.HTTP_400_BAD_REQUEST)
                    if tx.status != 'completed':
                        return Response(
                            {'detail': 'To\'lov hali tasdiqlanmagan. To\'lovni amalga oshiring va "To\'lovni tekshirish" tugmasini bosing.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    if tx.service_type != 'publication_fee':
                        return Response({'detail': 'Noto\'g\'ri to\'lov turi.'}, status=status.HTTP_400_BAD_REQUEST)
            except Journal.DoesNotExist:
                pass
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
            originality = result.get('originality', max(0, 100 - plagiarism_percentage))
            report = result.get('report', {})

            article.plagiarism_percentage = plagiarism_percentage
            article.ai_content_percentage = ai_content_percentage
            article.originality_percentage = originality
            article.plagiarism_checked_at = timezone.now()
            article.plagiarism_report = report
            article.save(update_fields=[
                'plagiarism_percentage', 'ai_content_percentage', 'originality_percentage',
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
        """Update article status. Author: own; super_admin: any; journal_admin: only own journal."""
        article = self.get_object()
        if article.author == request.user:
            pass
        elif request.user.role == 'super_admin':
            pass
        elif request.user.role == 'journal_admin':
            if article.journal.journal_admin_id != request.user.id:
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
        final_status = new_status
        # Antiplagiat tekshiruvi faqat jurnal admin "Nashrga yuborilgan" qilganda. Bosh admin qabul qilsa qayta tekshirilmaydi.
        if new_status == 'NashrgaYuborilgan' and getattr(request.user, 'role', None) != 'super_admin':
            article.journal.refresh_from_db()
            decision, reason = _check_plagiarism_thresholds(article)
            if decision == 'reject':
                final_status = 'Rejected'
                article.status = final_status
                article.save()
                ActivityLog.objects.create(
                    article=article,
                    user=request.user,
                    action='Status: NashrgaYuborilgan → Rejected (antipiagiat talablar bajarilmadi)',
                    details=reason or 'Plagiat / AI / originalilik bo\'yicha jurnal talablariga mos kelmadi.'
                )
                try:
                    Notification.notify(
                        user=article.author,
                        title='Maqola rad etildi',
                        message=f'"{article.title}" jurnal talablariga ko\'ra rad etildi: plagiat, AI kontent yoki originalilik chegarasiga mos kelmadi.',
                        notification_type='plagiarism',
                        link=f'/articles/{article.id}',
                        metadata={'article_id': str(article.id), 'reason': reason},
                    )
                except Exception as e:
                    logger.warning(f"Notify author reject: {e}")
                return Response({
                    'status': 'success',
                    'new_status': final_status,
                    'plagiarism_check': 'rejected',
                    'reason': reason,
                })
            if decision == 'review':
                final_status = 'PlagiarismReview'
                article.status = final_status
                article.save()
                ActivityLog.objects.create(
                    article=article,
                    user=request.user,
                    action='Status: Antiplagiat ko\'rib chiqish (bosh admin qarori kutilmoqda)',
                    details=reason or 'Qisman talablar bajarildi. Bosh administrator qabul/rad qiladi.'
                )
                from django.contrib.auth import get_user_model
                User = get_user_model()
                super_admins = list(User.objects.filter(role='super_admin'))
                journal_admin = getattr(article.journal, 'journal_admin', None)
                link = f'/articles/{article.id}'
                for u in super_admins:
                    try:
                        Notification.notify(
                            user=u,
                            title='Antiplagiat: bosh admin qarori kerak',
                            message=f'Maqola "{article.title}" — plagiat/AI/originalilik talablari qisman bajarildi. Qabul yoki rad qiling.',
                            notification_type='plagiarism',
                            link=link,
                            metadata={'article_id': str(article.id), 'reason': reason},
                        )
                    except Exception as e:
                        logger.warning(f"Notify super_admin: {e}")
                if journal_admin and journal_admin not in super_admins:
                    try:
                        Notification.notify(
                            user=journal_admin,
                            title='Antiplagiat ko\'rib chiqish',
                            message=f'Maqola "{article.title}" bosh administrator qaroriga yuborildi (plagiat/AI/originalilik).',
                            notification_type='article',
                            link=link,
                            metadata={'article_id': str(article.id)},
                        )
                    except Exception as e:
                        logger.warning(f"Notify journal_admin: {e}")
                return Response({
                    'status': 'success',
                    'new_status': final_status,
                    'plagiarism_check': 'review',
                    'reason': reason,
                })
            # decision == 'accept': final_status stays NashrgaYuborilgan

        article.status = final_status
        article.save()
        
        reason_text = request.data.get('reason', '') or ''
        ActivityLog.objects.create(
            article=article,
            user=request.user,
            action=f'Status changed from {old_status} to {final_status}',
            details=reason_text
        )

        status_labels = dict(Article.STATUS_CHOICES)
        new_label = status_labels.get(final_status, final_status)
        notif_metadata = {'article_id': str(article.id), 'old_status': old_status, 'new_status': final_status}
        if final_status == 'Revision' and reason_text:
            notif_metadata['revision_reason'] = reason_text
        if final_status == 'Rejected' and reason_text:
            notif_metadata['rejection_reason'] = reason_text
        if final_status == 'Revision':
            notif_title = 'Maqola tahrirga qaytarildi'
            notif_message = f'"{article.title}" maqolangiz tahrirga qaytarildi.'
            if reason_text:
                notif_message += f' Sabab: {reason_text}'
            else:
                notif_message += ' Tahrirlash uchun maqola sahifasidagi izohni ko\'ring.'
        elif final_status == 'Rejected':
            notif_title = 'Maqola rad etildi'
            notif_message = f'"{article.title}" maqolangiz rad etildi.'
            if reason_text:
                notif_message += f' Sabab: {reason_text}'
            else:
                notif_message += ' Batafsil maqola sahifasidagi izohni ko\'ring.'
        else:
            notif_title = 'Maqola holati yangilandi'
            notif_message = f'"{article.title}" maqolangiz holati "{new_label}" ga o\'zgartirildi.'
        try:
            Notification.notify(
                user=article.author,
                title=notif_title,
                message=notif_message,
                notification_type='status_change',
                link=f'/articles/{article.id}',
                metadata=notif_metadata,
            )
        except Exception as e:
            logger.warning(f"Failed to send status notification: {e}")
        
        return Response({'status': 'success', 'new_status': final_status})

    @action(detail=True, methods=['post'])
    def complete_publication(self, request, pk=None):
        """
        Nashr qilish: sertifikat faylini yuklash, statusni Published qilish, muallifga bildirishnoma.
        Only for journal_admin (own journal) or super_admin. Article must be Accepted.
        Expects multipart: certificate (file, PDF or JPG), optional issue_id.
        """
        article = self.get_object()
        if request.user.role == 'super_admin':
            pass
        elif request.user.role == 'journal_admin':
            if article.journal.journal_admin_id != request.user.id:
                return Response(
                    {'error': 'Siz faqat o\'z jurnalingizdagi maqolalarni nashr qilishingiz mumkin'},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'Siz bu maqolani nashr qilish huquqiga egasiz'},
                status=status.HTTP_403_FORBIDDEN
            )
        if article.status != 'Accepted':
            return Response(
                {'error': 'Faqat "Qabul qilingan" holatidagi maqolani nashr qilish mumkin'},
                status=status.HTTP_400_BAD_REQUEST
            )
        certificate_file = request.FILES.get('certificate')
        if not certificate_file:
            return Response(
                {'error': 'Sertifikat fayli (PDF yoki JPG) yuklanishi shart'},
                status=status.HTTP_400_BAD_REQUEST
            )
        allowed_content_types = (
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
        )
        if certificate_file.content_type not in allowed_content_types:
            return Response(
                {'error': 'Sertifikat faqat PDF yoki JPG (yoki PNG) formatida bo\'lishi kerak'},
                status=status.HTTP_400_BAD_REQUEST
            )
        issue_id = request.data.get('issue_id') or request.POST.get('issue_id')
        if issue_id:
            from apps.journals.models import Issue
            try:
                issue = Issue.objects.get(id=issue_id, journal=article.journal)
                article.issue = issue
            except Issue.DoesNotExist:
                pass
        publication_url = (request.data.get('publication_url') or request.POST.get('publication_url') or '').strip()
        if publication_url:
            article.publication_url = publication_url
        article.publication_certificate_path = certificate_file
        article.status = 'Published'
        article.published_by = request.user
        article.save()
        if article.publication_certificate_path:
            article.publication_certificate_url = article.publication_certificate_path.url
            article.save(update_fields=['publication_certificate_url'])
        ActivityLog.objects.create(
            article=article,
            user=request.user,
            action='Nashr qilindi — muallifga tayyor deb yuborildi',
            details='Sertifikat yuklandi, status: Nashr etilgan.'
        )
        try:
            Notification.notify(
                user=article.author,
                title='Maqolangiz tayyor',
                message=f'"{article.title}" maqolangiz nashr qilindi va tayyor. Sertifikatni maqola sahifasidan yuklab olishingiz mumkin.',
                notification_type='article',
                link=f'/articles/{article.id}',
                metadata={'article_id': str(article.id), 'status': 'Published'},
            )
        except Exception as e:
            logger.warning("Complete publication notify author failed: %s", e)
        return Response({
            'status': 'success',
            'new_status': 'Published',
            'message': 'Nashr qilindi. Muallifga bildirishnoma yuborildi.',
        })

    @action(detail=True, methods=['post'])
    def check_plagiarism(self, request, pk=None):
        """Check article for plagiarism. Requires a completed payment for this article (language_editing)."""
        logger.info(f"[CHECK_PLAGE] Starting plagiarism check for article {pk} by user {request.user.id if request.user else 'ANON'}")
        article = self.get_object()
        
        # Permission: author (own), super_admin (any), journal_admin (own journal only)
        if article.author != request.user and request.user.role != 'super_admin':
            if request.user.role == 'journal_admin':
                if article.journal.journal_admin_id != request.user.id:
                    return Response(
                        {'error': 'Siz faqat o\'z jurnalingizdagi maqolalarni tekshirishingiz mumkin'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Siz bu maqolani tekshirish huquqiga egasiz'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Require completed payment for plagiarism check (language_editing service type)
        has_paid = Transaction.objects.filter(
            article=article,
            user=request.user,
            status='completed',
            service_type='language_editing'
        ).exists()
        logger.info(f"[CHECK_PLAGE] Has paid transaction: {has_paid}, role: {request.user.role}")
        if not has_paid and request.user.role not in ('super_admin',):
            return Response(
                {'error': 'Antiplagiat tekshiruvi uchun to\'lov talab qilinadi. Iltimos, avval to\'lovni amalga oshiring.'},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
        
        # Check if file exists
        if not article.final_pdf_path:
            logger.warning(f"[CHECK_PLAGE] No PDF file for article {article.id}")
            return Response(
                {'error': 'Plagiat tekshiruvi uchun maqola fayli kerak'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Use the Gemini service to perform plagiarism check
            gemini_service = get_gemini_service()
            logger.info(f"[CHECK_PLAGE] Gemini service initialized")
            
            # Extract content from PDF file
            text_content = ""
            if article.final_pdf_path:
                try:
                    import os
                    from django.conf import settings
                    
                    # Get full file path
                    file_path = os.path.join(settings.MEDIA_ROOT, str(article.final_pdf_path))
                    logger.info(f"[CHECK_PLAGE] Checking file at: {file_path}")
                    
                    # Extract text from PDF
                    if os.path.exists(file_path):
                        text_content = gemini_service.extract_text_from_pdf(file_path)
                        logger.info(f"[CHECK_PLAGE] Extracted {len(text_content)} chars from PDF")
                    else:
                        # Try alternative path
                        if hasattr(article, 'main_file') and article.main_file:
                            file_path = article.main_file.path
                            if os.path.exists(file_path):
                                text_content = gemini_service.extract_text_from_pdf(file_path)
                                logger.info(f"[CHECK_PLAGE] Extracted {len(text_content)} chars from alternative file")
                        
                        if not text_content:
                            logger.warning(f"[CHECK_PLAGE] PDF file not found at {file_path}, using article abstract")
                            text_content = article.abstract or article.title or ""
                except Exception as e:
                    logger.error(f"[CHECK_PLAGE] Error extracting PDF content: {e}", exc_info=True)
                    # Fallback to article text
                    text_content = article.abstract or article.title or ""
            else:
                # Use article text as fallback
                text_content = article.abstract or article.title or ""
            
            logger.info(f"[CHECK_PLAGE] Final text length: {len(text_content) if text_content else 0}")
            
            # Perform plagiarism check
            if not text_content or len(text_content.strip()) < 50:
                logger.warning(f"[CHECK_PLAGE] Insufficient text for plagiarism check")
                return Response(
                    {'error': 'Plagiat tekshiruvi uchun maqola matni yetarli emas. Iltimos, PDF faylni yuklang.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = gemini_service.check_plagiarism(text_content)
            logger.info(f"[CHECK_PLAGE] Plagiarism result: {result}")
            
            plagiarism_percentage = result.get('plagiarism_percentage', 0)
            ai_content_percentage = result.get('ai_content_percentage', 0)
            originality = result.get('originality', max(0, 100 - plagiarism_percentage))
            report = result.get('report', {})
            
            article.plagiarism_percentage = plagiarism_percentage
            article.ai_content_percentage = ai_content_percentage
            article.originality_percentage = originality
            article.plagiarism_checked_at = timezone.now()
            article.plagiarism_report = report
            article.save(update_fields=[
                'plagiarism_percentage', 'ai_content_percentage', 'originality_percentage',
                'plagiarism_checked_at', 'plagiarism_report'
            ])
            
            ActivityLog.objects.create(
                article=article,
                user=request.user,
                action='Plagiarism check completed',
                details=f'Plagiarism: {plagiarism_percentage}%, AI Content: {ai_content_percentage}%, Originality: {originality}%'
            )
            
            return Response({
                'plagiarism': plagiarism_percentage,
                'ai_content': ai_content_percentage,
                'originality': originality,
                'checked_at': article.plagiarism_checked_at,
                'report': report,
                'sources': result.get('sources', report.get('sources', [])),
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[CHECK_PLAGE] Error checking plagiarism: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Plagiat tekshiruvida xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.', 'details': str(e)},
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


# ---------- Maqola namuna olish (taqrizchiga yuborish) ----------
def _article_sample_price_per_page(quality: str) -> int:
    from apps.udc.services import get_service_amount
    if quality == 'yuqori':
        return int(get_service_amount('article_sample_yuqori', 400000))
    if quality == 'orta':
        return int(get_service_amount('article_sample_orta', 250000))
    return int(get_service_amount('article_sample_quyi', 150000))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def article_sample_price(request):
    """1 bet narxlari: Narxlar sahifasida (ServicePrice) o'rnatiladi."""
    from apps.udc.services import get_service_amount
    quyi = int(get_service_amount('article_sample_quyi', 150000))
    orta = int(get_service_amount('article_sample_orta', 250000))
    yuqori = int(get_service_amount('article_sample_yuqori', 400000))
    return Response({
        'quyi': quyi,
        'orta': orta,
        'yuqori': yuqori,
        'currency': 'UZS',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def article_sample_request_create(request):
    """
    Maqola namuna so'rovi: talablar, sahifalar, mavzu, daraja, ism/familya.
    Tranzaksiya yaratiladi; to'lovdan keyin so'rov taqrizchiga yuboriladi.
    """
    data = getattr(request, 'data', None) or request.POST.dict()
    requirements = (data.get('requirements') or '').strip()
    topic = (data.get('topic') or '').strip()
    quality_level = (data.get('quality_level') or 'orta').strip().lower()
    author_first_name = (data.get('first_name') or data.get('author_first_name') or '').strip()
    author_last_name = (data.get('last_name') or data.get('author_last_name') or '').strip()

    if not requirements:
        return Response({'detail': 'Talablar (requirements) majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    if not topic:
        return Response({'detail': 'Maqola mavzusi (topic) majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    if quality_level not in ('quyi', 'orta', 'yuqori'):
        return Response({'detail': "Daraja quyi, orta yoki yuqori bo'lishi kerak."}, status=status.HTTP_400_BAD_REQUEST)
    if not author_first_name or not author_last_name:
        return Response({'detail': 'Ism va familya majburiy.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        pages = max(1, min(500, int(data.get('pages', 1))))
    except (TypeError, ValueError):
        pages = 1

    price_per_page = _article_sample_price_per_page(quality_level)
    amount = pages * price_per_page

    transaction = Transaction.objects.create(
        user=request.user,
        amount=amount,
        currency='UZS',
        service_type='article_sample',
        extra_data={
            'requirements': requirements[:10000],
            'pages': pages,
            'topic': topic[:500],
            'quality_level': quality_level,
            'first_name': author_first_name[:150],
            'last_name': author_last_name[:150],
        },
    )

    return Response({
        'transaction_id': str(transaction.id),
        'amount': float(amount),
        'currency': 'UZS',
        'pages': pages,
        'quality_level': quality_level,
        'price_per_page': price_per_page,
    }, status=status.HTTP_201_CREATED)


# ---------- DOI raqami olish ----------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def doi_price(request):
    """DOI xizmati narxi: Narxlar sahifasida (ServicePrice doi_request) o'rnatiladi."""
    from apps.udc.services import get_service_amount
    amount = int(get_service_amount('doi_request', 100000))
    return Response({
        'amount': amount,
        'currency': 'UZS',
        'payment_required': amount > 0,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def doi_request_create(request):
    """
    DOI so'rovi: ism, familya, maqola fayli (doc/pdf). Fayl yuklanadi, tranzaksiya yaratiladi.
    Narx 0 bo'lsa to'lovsiz taqrizchiga yuboriladi; aks holda to'lovdan keyin.
    """
    data = getattr(request, 'data', None) or request.POST
    if hasattr(data, 'dict'):
        data = data.dict()
    else:
        data = dict(data) if data else {}
    author_first_name = (data.get('first_name') or data.get('author_first_name') or '').strip()[:150]
    author_last_name = (data.get('last_name') or data.get('author_last_name') or '').strip()[:150]
    file_obj = request.FILES.get('file')
    if not author_first_name or not author_last_name:
        return Response({'detail': 'Ism va familya majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    if not file_obj:
        return Response({'detail': 'Maqola fayli (DOC yoki PDF) yuklanishi shart.'}, status=status.HTTP_400_BAD_REQUEST)
    allowed = ('.doc', '.docx', '.pdf')
    name = (file_obj.name or '').lower()
    if not any(name.endswith(ext) for ext in allowed):
        return Response({'detail': 'Faqat DOC, DOCX yoki PDF fayllar qabul qilinadi.'}, status=status.HTTP_400_BAD_REQUEST)

    from apps.udc.services import get_service_amount
    amount = int(get_service_amount('doi_request', 100000))
    doi_req = DoiRequest.objects.create(
        user=request.user,
        author_first_name=author_first_name,
        author_last_name=author_last_name,
        file=file_obj,
        status='pending_payment',
    )
    transaction = Transaction.objects.create(
        user=request.user,
        amount=amount,
        currency='UZS',
        service_type='doi_request',
        extra_data={'doi_request_id': str(doi_req.id)},
    )
    if amount <= 0:
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save(update_fields=['status', 'completed_at'])
        from .fulfill_doi import fulfill_doi_request
        fulfill_doi_request(transaction)
        return Response({
            'transaction_id': str(transaction.id),
            'amount': 0,
            'currency': 'UZS',
            'fulfilled': True,
            'message': 'So\'rov taqrizchiga yuborildi. DOI link tayyor bo\'lgach bildirishnoma orqali xabar beramiz.',
        }, status=status.HTTP_201_CREATED)
    return Response({
        'transaction_id': str(transaction.id),
        'amount': float(amount),
        'currency': 'UZS',
    }, status=status.HTTP_201_CREATED)


class DoiRequestViewSet(viewsets.ModelViewSet):
    """DOI so'rovlari: muallif o'zini ko'radi, taqrizchi barcha submitted ni ko'radi va doi_link kiritadi."""
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'patch', 'options']

    def get_queryset(self):
        role = getattr(self.request.user, 'role', None) or 'author'
        if role == 'reviewer' or role == 'super_admin':
            return DoiRequest.objects.filter(status='submitted').select_related('user').order_by('-created_at')
        return DoiRequest.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        return DoiRequestSerializer

    def partial_update(self, request, *args, **kwargs):
        """Faqat taqrizchi: doi_link yuklash, status=completed, muallifga bildirishnoma."""
        role = getattr(request.user, 'role', None)
        if role not in ('reviewer', 'super_admin'):
            return Response({'detail': 'Faqat taqrizchi DOI link kiritishi mumkin.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        if instance.status != 'submitted':
            return Response({'detail': 'Ushbu so\'rov allaqachon bajarilgan.'}, status=status.HTTP_400_BAD_REQUEST)
        doi_link = (request.data.get('doi_link') or '').strip()
        if not doi_link or not doi_link.startswith('http'):
            return Response({'detail': 'To\'g\'ri DOI link (URL) kiriting.'}, status=status.HTTP_400_BAD_REQUEST)
        instance.doi_link = doi_link[:500]
        instance.status = 'completed'
        instance.completed_at = timezone.now()
        instance.save(update_fields=['doi_link', 'status', 'completed_at'])
        try:
            Notification.notify(
                user=instance.user,
                title='DOI raqami tayyor',
                message=f'DOI so\'rovingiz bajarildi. Link: {instance.doi_link[:80]}...',
                notification_type='article',
                link='/arxiv',
                metadata={'doi_request_id': str(instance.id), 'doi_link': instance.doi_link},
            )
        except Exception as e:
            logger.warning("DOI notify author failed: %s", e)
        return Response(DoiRequestSerializer(instance).data)


class ArticleSampleRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """Maqola namuna so'rovlari: taqrizchi barchani ko'radi, muallif o'zini."""
    permission_classes = [IsAuthenticated]
    serializer_class = ArticleSampleRequestSerializer
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        role = getattr(self.request.user, 'role', None) or 'author'
        if role in ('reviewer', 'super_admin'):
            return ArticleSampleRequest.objects.select_related('user').order_by('-created_at')
        return ArticleSampleRequest.objects.filter(user=self.request.user).order_by('-created_at')