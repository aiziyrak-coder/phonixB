"""
Nashr to'lovi (publication_fee) tasdiqlanganda bog'langan maqolani faol holatga o'tkazadi.
"""
import logging

logger = logging.getLogger(__name__)


def _resolve_article_for_publication_fee(transaction):
    from .models import Article

    article = getattr(transaction, 'article', None)
    if article is None:
        extra = getattr(transaction, 'extra_data', None) or {}
        article_id = extra.get('article_id')
        if article_id:
            article = Article.objects.filter(pk=article_id).first()
            if article and not transaction.article_id:
                transaction.article = article
                transaction.save(update_fields=['article'])
    return article


def fulfill_publication_fee(transaction):
    """
    Click/Payme complete callbackida chaqiriladi.
    Tranzaksiyaga bog'langan maqola Draft bo'lsa → Yangi (taqrizga yuborilgan).
    """
    if getattr(transaction, 'service_type', None) != 'publication_fee':
        return
    if getattr(transaction, 'status', None) != 'completed':
        return

    article = _resolve_article_for_publication_fee(transaction)
    if article is None:
        logger.warning('publication_fee fulfill: no article for transaction %s', transaction.id)
        return

    if str(article.author_id) != str(transaction.user_id):
        logger.warning('publication_fee fulfill: article user mismatch tx=%s', transaction.id)
        return

    if article.status == 'Draft':
        article.status = 'Yangi'
        article.save(update_fields=['status'])
        logger.info('Article %s: Draft → Yangi after publication_fee payment', article.id)
        try:
            from .submission_notifications import notify_article_submitted
            notify_article_submitted(article)
        except Exception as exc:
            logger.warning('publication_fee fulfill notify failed: %s', exc)


def repair_publication_fee_articles_for_user(user):
    """
    To'lov tasdiqlangan, lekin maqola hali Draft qolgan holatlarni tuzatish (arxiv / sinxron tekshiruv).
    """
    from apps.payments.models import Transaction

    txs = (
        Transaction.objects.filter(
            user=user,
            service_type='publication_fee',
            status='completed',
        )
        .select_related('article')
        .order_by('-completed_at', '-created_at')
    )
    for tx in txs:
        fulfill_publication_fee(tx)
