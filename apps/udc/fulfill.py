"""
Fulfill UDK request after successful payment: AI determines UDK, then generate certificate PDF and notify user.
Supports: 1) article-based (maqola), 2) standalone (mavzu/fayl orqali).
"""
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)


def _suggest_udk_for_text(title, abstract, gemini, udc_services):
    """Teacode ierarxiyasi orqali aniq, tarmoqlangan UDK (masalan 332.055.2) taklif qilish."""
    code, desc = udc_services.get_specific_udk(title or '', abstract or '', gemini)
    if code and desc:
        return code, desc[:500]
    # Fallback: faqat root ro'yxatdan
    ref = udc_services.get_udc_reference_for_ai()
    result = gemini.suggest_udk(title or '', abstract or '', [], ref)
    if result and result.get('udk_code'):
        return result.get('udk_code', '').strip(), (result.get('udk_description') or '').strip()[:500]
    return None, None


def _do_article_udk(transaction, article, extra, udk_code, udk_description, gemini, udc_services):
    from apps.articles.models import Article
    from .pdf_generator import generate_udk_certificate_pdf
    from django.core.files.base import ContentFile
    from apps.notifications.models import Notification

    if not udk_code:
        udk_code, udk_description = _suggest_udk_for_text(
            article.title or '', article.abstract or '', gemini, udc_services
        )
        if not udk_code:
            keywords = article.keywords if isinstance(article.keywords, (list, tuple)) else []
            keywords = keywords[:20] if isinstance(keywords, list) else [str(article.keywords)] if article.keywords else []
            result = gemini.suggest_udk(article.title or '', article.abstract or '', keywords, udc_services.get_udc_reference_for_ai())
            if result and result.get('udk_code'):
                udk_code = result.get('udk_code', '').strip()
                udk_description = (result.get('udk_description') or '').strip()[:500]
        if not udk_code:
            from .services import get_fallback_udk
            udk_code, udk_description = get_fallback_udk()

    article.udk_code = udk_code
    article.udk_description = udk_description
    article.save(update_fields=['udk_code', 'udk_description'])

    try:
        author_name = article.author.get_full_name() if article.author else ''
        frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'https://ilmiyfaoliyat.uz').rstrip('/')
        verification_url = f"{frontend_base}/#/udk-verify?article_id={article.id}"
        from datetime import date
        buf = generate_udk_certificate_pdf(
            article_title=article.title,
            author_name=author_name,
            udk_code=udk_code,
            udk_description=udk_description,
            document_number=str(article.id),
            document_date=date.today().strftime('%d.%m.%Y'),
            verification_url=verification_url,
        )
        media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        upload_to = 'articles/udk_certificates'
        os.makedirs(os.path.join(media_root, upload_to), exist_ok=True)
        fname = f"udk_{article.id}.pdf"
        article.udk_certificate_path.save(fname, ContentFile(buf.read()), save=True)
        logger.info(f"UDK certificate saved for article {article.id}")
        Notification.notify(
            user=article.author,
            title="UDK ma'lumotnoma tayyor",
            message=f"\"{(article.title or '')[:50]}...\" maqolangiz uchun UDK tasdiqlangan ma'lumotnoma tayyor. UDK: {udk_code}. Profil yoki to'lov sahifasidan yuklab oling.",
            notification_type='system',
            link=f"/articles/{article.id}",
            metadata={'article_id': str(article.id), 'udk_code': udk_code},
        )
    except Exception as e:
        logger.error(f"Failed to generate UDK certificate for article {article.id}: {e}", exc_info=True)


def _do_standalone_udk(transaction, extra, gemini, udc_services):
    from .models import UDKCertificate
    from .pdf_generator import generate_udk_certificate_pdf
    from django.core.files.base import ContentFile
    from apps.notifications.models import Notification

    title = (extra.get('title') or '').strip()[:500]
    abstract = (extra.get('abstract') or '').strip()[:15000]
    if not title:
        logger.warning(f"Standalone UDK transaction {transaction.id} has no title")
        return

    udk_code, udk_description = _suggest_udk_for_text(title, abstract, gemini, udc_services)
    if not udk_code:
        udk_code, udk_description = udc_services.get_fallback_udk()

    author_name = (extra.get('author_name') or '').strip()[:300]
    if not author_name and transaction.user:
        author_name = transaction.user.get_full_name() or ''
    try:
        cert = UDKCertificate.objects.create(
            user=transaction.user,
            author_name=author_name,
            title=title,
            udk_code=udk_code,
            udk_description=udk_description,
            transaction=transaction,
        )
        frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'https://ilmiyfaoliyat.uz').rstrip('/')
        verification_url = f"{frontend_base}/#/udk-verify?id={cert.id}"
        from datetime import date
        buf = generate_udk_certificate_pdf(
            article_title=title,
            author_name=author_name,
            udk_code=udk_code,
            udk_description=udk_description,
            document_number=str(cert.id),
            document_date=date.today().strftime('%d.%m.%Y'),
            verification_url=verification_url,
        )
        fname = f"udk_standalone_{cert.id}.pdf"
        cert.certificate_path.save(fname, ContentFile(buf.read()), save=True)
        logger.info(f"UDK standalone certificate saved: {cert.id}")

        media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
        cert_url = f"{media_url}/{cert.certificate_path.name}" if cert.certificate_path else None
        link = "/udk-olish"  # sahifada "Mening ma'lumotnomalarim" bo'lishi mumkin
        Notification.notify(
            user=transaction.user,
            title="UDK ma'lumotnoma tayyor",
            message=f"\"{title[:50]}...\" uchun UDK tasdiqlangan ma'lumotnoma tayyor. UDK: {udk_code}. UDK Olish sahifasidan yuklab oling.",
            notification_type='system',
            link=link,
            metadata={'certificate_id': cert.id, 'udk_code': udk_code, 'certificate_url': cert_url},
        )
    except Exception as e:
        logger.error(f"Failed to generate standalone UDK certificate for transaction {transaction.id}: {e}", exc_info=True)


def fulfill_udk_request(transaction):
    """
    Called when a transaction with service_type='udk_request' is completed.
    - UdkRequest workflow: statusni 'submitted' ga o'zgartirib, taqrizchilarga xabar yuborish.
    - Article-based (eski): update article, generate PDF, save to article.udk_certificate_path, notify.
    - Standalone (eski): create UDKCertificate, generate PDF, save to certificate, notify.
    """
    if transaction.service_type != 'udk_request':
        return

    extra = getattr(transaction, 'extra_data', None) or {}
    
    # Yangi UdkRequest workflow
    udk_request_id = extra.get('udk_request_id')
    if udk_request_id:
        from .models import UdkRequest, UDK_REQUEST_STATUS_SUBMITTED
        try:
            udk_req = UdkRequest.objects.get(id=udk_request_id)
            if udk_req.status == 'pending_payment':
                udk_req.status = UDK_REQUEST_STATUS_SUBMITTED
                udk_req.save(update_fields=['status'])
                # Taqrizchilarga xabar yuborish
                from .views import _notify_reviewers_udk_request
                _notify_reviewers_udk_request(udk_req)
                logger.info(f"UdkRequest {udk_request_id} submitted to reviewers")
        except UdkRequest.DoesNotExist:
            logger.warning(f"UdkRequest {udk_request_id} not found")
        return
    
    # Eski workflow: article-based yoki standalone
    from apps.services import get_gemini_service
    from . import services as udc_services
    gemini = get_gemini_service()

    if transaction.article_id:
        from apps.articles.models import Article
        try:
            article = Article.objects.select_related('author').get(id=transaction.article_id)
        except Article.DoesNotExist:
            logger.warning(f"Article {transaction.article_id} not found for UDK request")
            return
        udk_code = (extra.get('udk_code') or '').strip()
        udk_description = (extra.get('udk_description') or '').strip()[:500]
        _do_article_udk(transaction, article, extra, udk_code, udk_description, gemini, udc_services)
        return

    if extra.get('standalone'):
        _do_standalone_udk(transaction, extra, gemini, udc_services)
        return

    logger.warning(f"UDK request transaction {transaction.id} has no article and no standalone data")
