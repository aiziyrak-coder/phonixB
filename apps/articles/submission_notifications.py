"""
Maqola jurnalga yuborilganda bosh admin, jurnal admin va operatorlarga bildirishnoma.
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()

SUBMITTED_STATUSES = frozenset({'Yangi', 'WithEditor', 'QabulQilingan'})
DRAFT_PENDING_STATUSES = frozenset({'Draft'})

STAFF_ROLES_NOTIFY = frozenset({'super_admin', 'journal_admin', 'operator', 'accountant'})


def _is_standalone_antiplagiat(article) -> bool:
    title = (getattr(article, 'title', None) or '').strip().lower()
    if title.startswith('plagiarism check'):
        return True
    keywords = getattr(article, 'keywords', None) or []
    return any(str(k).lower() == 'plagiarism' for k in keywords)


def _article_link(article) -> str:
    return f'/articles/{article.id}'


def _log_submission_activity(article, *, action: str, details: str) -> None:
    from .models import ActivityLog

    try:
        ActivityLog.objects.create(
            article=article,
            user=getattr(article, 'author', None),
            action=action,
            details=details,
        )
    except Exception as exc:
        logger.warning('submission activity log failed: %s', exc)


def _already_notified(user, article_id, stage: str) -> bool:
    from apps.notifications.models import Notification

    since = timezone.now() - timedelta(hours=48)
    return Notification.objects.filter(
        user=user,
        created_at__gte=since,
        metadata__article_id=str(article_id),
        metadata__submission_stage=stage,
    ).exists()


def _notify_recipients(article, *, notif_title: str, message: str, stage: str) -> int:
    """super_admin, is_superuser, jurnal admini, operator, accountant (hisobot)."""
    from apps.notifications.models import Notification

    journal = getattr(article, 'journal', None)
    journal_name = (journal.name if journal else None) or "Noma'lum jurnal"
    author = getattr(article, 'author', None)
    author_name = (author.get_full_name() if author else '').strip() or 'Muallif'
    title_short = (article.title or 'Maqola')[:120]
    link = _article_link(article)
    metadata = {
        'article_id': str(article.id),
        'journal_id': str(article.journal_id) if article.journal_id else None,
        'author_id': str(article.author_id) if article.author_id else None,
        'submission_stage': stage,
    }
    notified_ids = set()

    def _notify(user, msg_title: str, msg_body: str) -> None:
        if user is None or user.pk in notified_ids:
            return
        if _already_notified(user, article.id, stage):
            notified_ids.add(user.pk)
            return
        notified_ids.add(user.pk)
        try:
            Notification.notify(
                user=user,
                title=msg_title,
                message=msg_body,
                notification_type='article',
                link=link,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning('article notification user=%s: %s', user.pk, exc)

    base_msg = f'"{title_short}" — jurnal: {journal_name}. Muallif: {author_name}.'

    for admin in User.objects.filter(role='super_admin', is_active=True):
        _notify(admin, notif_title, f'{base_msg} {message}')

    for admin in User.objects.filter(is_superuser=True, is_active=True).exclude(pk__in=notified_ids):
        _notify(admin, notif_title, f'{base_msg} {message}')

    journal_admin = getattr(journal, 'journal_admin', None) if journal else None
    if journal_admin and getattr(journal_admin, 'is_active', True):
        _notify(journal_admin, notif_title, f'{base_msg} {message}')

    for staff in User.objects.filter(role__in=STAFF_ROLES_NOTIFY - {'super_admin', 'journal_admin'}, is_active=True):
        _notify(staff, notif_title, f'{base_msg} {message}')

    if len(notified_ids) == 0:
        logger.error(
            'Article %s: hech qanday xodimga bildirishnoma yuborilmadi (stage=%s). '
            'super_admin / jurnal admin / operator hisoblarini tekshiring.',
            article.id,
            stage,
        )
    else:
        logger.info('Article %s notified %s staff (stage=%s)', article.id, len(notified_ids), stage)

    return len(notified_ids)


def notify_article_draft_pending_payment(article) -> None:
    """Oldindan to'lov kutilayotgan qoralama — admin/operator darhol ko'radi."""
    from .models import Article

    if article is None:
        return
    try:
        article = (
            Article.objects.select_related('journal', 'author', 'journal__journal_admin')
            .get(pk=article.pk)
        )
    except Article.DoesNotExist:
        return
    if article.status not in DRAFT_PENDING_STATUSES:
        return
    if _is_standalone_antiplagiat(article):
        return

    _log_submission_activity(
        article,
        action="Maqola qoralama (to'lov kutilmoqda)",
        details='Bosh admin, jurnal admin va operatorlarga yuborildi.',
    )
    _notify_recipients(
        article,
        notif_title="Yangi maqola (to'lov kutilmoqda)",
        message="Muallif maqolani yubordi. Nashr to'lovi tasdiqlangach «Yangi kelganlar» bo'limida ko'ring.",
        stage='draft_payment',
    )


def notify_article_submitted(article) -> None:
    """
    Muallif maqolani jurnalga yuborganida (Yangi):
    - barcha super_admin (va is_superuser)
    - shu jurnalga biriktirilgan journal_admin
    - operator va accountant (hisobot)
    """
    from .models import Article

    if article is None:
        return

    try:
        article = (
            Article.objects.select_related('journal', 'author', 'journal__journal_admin')
            .get(pk=article.pk)
        )
    except Article.DoesNotExist:
        return

    if article.status not in SUBMITTED_STATUSES:
        return
    if _is_standalone_antiplagiat(article):
        return

    _log_submission_activity(
        article,
        action='Maqola yuborildi',
        details='Bosh admin, jurnal admin va operatorlarga bildirishnoma yuborildi.',
    )
    _notify_recipients(
        article,
        notif_title='Yangi maqola yuborildi',
        message="Ko'rib chiqish uchun «Maqolalar» → «Yangi kelganlar» bo'limini oching.",
        stage='submitted',
    )
