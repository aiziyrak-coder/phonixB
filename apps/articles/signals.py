"""
Maqola yaratilganda yoki Draft → Yangi o'tganda xodimlarga bildirishnoma (callback/sinxron o'tkazib yuborilgan holatlar uchun).
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Article
from .submission_notifications import (
    notify_article_draft_pending_payment,
    notify_article_submitted,
    _is_standalone_antiplagiat,
)

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Article)
def article_track_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        instance._previous_status = (
            Article.objects.filter(pk=instance.pk).values_list('status', flat=True).first()
        )
    except Exception:
        instance._previous_status = None


@receiver(post_save, sender=Article)
def article_notify_staff_on_submission(sender, instance, created, **kwargs):
    if _is_standalone_antiplagiat(instance):
        return

    prev = getattr(instance, '_previous_status', None)
    status = instance.status

    try:
        if created:
            if status == 'Yangi':
                notify_article_submitted(instance)
            elif status == 'Draft':
                notify_article_draft_pending_payment(instance)
            return

        if prev == status:
            return
        if status == 'Yangi' and prev in (None, 'Draft'):
            notify_article_submitted(instance)
        elif status == 'Draft' and prev is None:
            notify_article_draft_pending_payment(instance)
    except Exception as exc:
        logger.warning('article_notify_staff_on_submission failed %s: %s', instance.pk, exc)
