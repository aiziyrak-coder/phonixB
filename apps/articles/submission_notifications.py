"""
Maqola jurnalga yuborilganda bosh admin, jurnal admin va operatorlarga bildirishnoma.
"""
import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

# Faqat haqiqiy topshirilgan maqolalar (to'lovdan keyin Draft→Yangi ham shu ro'yxatda)
SUBMITTED_STATUSES = frozenset({'Yangi', 'WithEditor', 'QabulQilingan'})


def _is_standalone_antiplagiat(article) -> bool:
    title = (getattr(article, 'title', None) or '').strip().lower()
    if title.startswith('plagiarism check'):
        return True
    keywords = getattr(article, 'keywords', None) or []
    return any(str(k).lower() == 'plagiarism' for k in keywords)


def notify_article_submitted(article) -> None:
    """
    Muallif maqolani jurnalga yuborganida:
    - barcha super_admin (va is_superuser)
    - shu jurnalga biriktirilgan journal_admin
    - barcha operator (hisobot)
    """
    from .models import Article
    from apps.notifications.models import Notification

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

    journal = getattr(article, 'journal', None)
    journal_name = (journal.name if journal else None) or "Noma'lum jurnal"
    author = getattr(article, 'author', None)
    author_name = (author.get_full_name() if author else '').strip() or 'Muallif'
    title_short = (article.title or 'Maqola')[:120]
    link = f'/articles/{article.id}'
    metadata = {
        'article_id': str(article.id),
        'journal_id': str(article.journal_id) if article.journal_id else None,
        'author_id': str(article.author_id) if article.author_id else None,
    }

    notified_ids = set()

    def _notify(user, notif_title: str, message: str) -> None:
        if user is None or user.pk in notified_ids:
            return
        notified_ids.add(user.pk)
        try:
            Notification.notify(
                user=user,
                title=notif_title,
                message=message,
                notification_type='article',
                link=link,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning('notify_article_submitted user=%s: %s', user.pk, exc)

    base_msg = f'"{title_short}" — jurnal: {journal_name}. Muallif: {author_name}.'

    for admin in User.objects.filter(role='super_admin'):
        _notify(
            admin,
            'Yangi maqola yuborildi',
            f'{base_msg} Ko\'rib chiqish uchun maqola sahifasini oching.',
        )

    for admin in User.objects.filter(is_superuser=True).exclude(pk__in=notified_ids):
        _notify(
            admin,
            'Yangi maqola yuborildi',
            f'{base_msg} Ko\'rib chiqish uchun maqola sahifasini oching.',
        )

    journal_admin = getattr(journal, 'journal_admin', None) if journal else None
    if journal_admin:
        _notify(
            journal_admin,
            'Jurnalingizga yangi maqola',
            f'{base_msg} Jurnal administratori sifatida tekshiring.',
        )

    for operator in User.objects.filter(role='operator'):
        _notify(
            operator,
            'Yangi maqola (hisobot)',
            f'{base_msg} Operator paneli va hisobotlar uchun.',
        )

    logger.info(
        'Article %s submission notified (%s recipients)',
        article.id,
        len(notified_ids),
    )
