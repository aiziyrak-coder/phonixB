"""
Nashr to'lovi (publication_fee) tasdiqlanganda bog'langan maqolani faol holatga o'tkazadi.
"""
import logging

logger = logging.getLogger(__name__)


def fulfill_publication_fee(transaction):
    """
    Click/Payme complete callbackida chaqiriladi.
    Tranzaksiyaga bog'langan maqola Draft bo'lsa → Yangi (taqrizga yuborilgan).
    """
    if getattr(transaction, 'service_type', None) != 'publication_fee':
        return

    from .models import Article

    article = getattr(transaction, 'article', None)
    if article is None:
        extra = getattr(transaction, 'extra_data', None) or {}
        article_id = extra.get('article_id')
        if article_id:
            article = Article.objects.filter(pk=article_id).first()
            if article:
                transaction.article = article
                transaction.save(update_fields=['article'])

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
