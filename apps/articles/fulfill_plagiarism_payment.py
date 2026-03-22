"""
Antiplagiat to'lovi (Transaction.service_type='language_editing') tasdiqlanganda
maqolani Draft holatidan PaymentCompleted ga o'tkazadi — muallif "Maqolalarim"da
to'lovdan keyin ham "Qoralama" ko'rmasin.
"""
import logging

logger = logging.getLogger(__name__)


def fulfill_language_editing_payment(transaction):
    """
    Click/Payme complete callbackida chaqiriladi.
    Faqat antiplagiat/plagiat to'lovi (frontend language_editing sifatida) uchun.
    """
    if getattr(transaction, 'service_type', None) != 'language_editing':
        return
    article = getattr(transaction, 'article', None)
    if article is None:
        return
    if article.status != 'Draft':
        return
    article.status = 'PaymentCompleted'
    article.save(update_fields=['status'])
    logger.info(
        'Article %s: Draft → PaymentCompleted (language_editing payment confirmed)',
        article.id,
    )
