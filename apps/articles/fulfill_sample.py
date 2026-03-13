"""To'lov tasdiqlangach maqola namuna so'rovini yaratish va taqrizchilarga xabar."""
import logging

logger = logging.getLogger(__name__)


def fulfill_article_sample(transaction):
    """
    Tranzaksiya service_type='article_sample' va status='completed' bo'lganda chaqiladi.
    ArticleSampleRequest yaratadi va taqrizchilarga bildirishnoma yuborishi mumkin.
    """
    if getattr(transaction, 'service_type', None) != 'article_sample':
        return
    extra = getattr(transaction, 'extra_data', None) or {}
    from .models import ArticleSampleRequest

    ArticleSampleRequest.objects.create(
        user=transaction.user,
        transaction=transaction,
        requirements=extra.get('requirements', '')[:10000],
        pages=max(1, int(extra.get('pages', 1))),
        topic=(extra.get('topic') or '')[:500],
        quality_level=extra.get('quality_level', 'orta'),
        author_first_name=(extra.get('first_name') or '')[:150],
        author_last_name=(extra.get('last_name') or '')[:150],
        amount=transaction.amount,
        status='submitted',
    )
    logger.info(f"Article sample request created for transaction {transaction.id}")

    try:
        from apps.notifications.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        reviewers = User.objects.filter(role='reviewer')[:20]
        topic_short = (extra.get('topic') or '')[:80]
        for rev in reviewers:
            Notification.notify(
                user=rev,
                title='Yangi maqola namuna so\'rovi',
                message=f'Muallif so\'rovi: "{topic_short}" — daraja: {extra.get("quality_level", "")}. Taqrizchilar panelida ko\'ring.',
                notification_type='article',
                link='/article-sample-requests',
                metadata={'transaction_id': str(transaction.id)},
            )
    except Exception as e:
        logger.warning(f"Article sample notify reviewers failed: {e}")
