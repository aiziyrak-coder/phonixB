"""To'lov tasdiqlangach DOI so'rovini taqrizchilarga yuborish."""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def fulfill_doi_request(transaction):
    """
    Tranzaksiya service_type='doi_request' va status='completed' bo'lganda chaqiladi.
    DoiRequest ni tranzaksiyaga ulaydi, status=submitted qiladi va taqrizchilarga bildirishnoma yuboradi.
    """
    if getattr(transaction, 'service_type', None) != 'doi_request':
        return
    extra = getattr(transaction, 'extra_data', None) or {}
    doi_request_id = extra.get('doi_request_id')
    if not doi_request_id:
        logger.warning("doi_request_id not found in transaction extra_data")
        return
    from .models import DoiRequest
    try:
        doi_req = DoiRequest.objects.get(id=doi_request_id)
    except DoiRequest.DoesNotExist:
        logger.warning(f"DoiRequest {doi_request_id} not found")
        return
    if doi_req.user_id != transaction.user_id:
        logger.warning("DoiRequest user mismatch")
        return
    doi_req.transaction = transaction
    doi_req.status = 'submitted'
    doi_req.save(update_fields=['transaction', 'status'])
    logger.info(f"DOI request {doi_req.id} submitted, notifying reviewers")

    try:
        from apps.notifications.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        reviewers = User.objects.filter(role='reviewer')[:20]
        author_short = f"{doi_req.author_last_name} {doi_req.author_first_name}"
        for rev in reviewers:
            Notification.notify(
                user=rev,
                title='Yangi DOI so\'rovi',
                message=f'Muallif: {author_short}. DOI raqami olish uchun taqrizchi panelida ko\'ring.',
                notification_type='article',
                link='/doi-requests',
                metadata={'doi_request_id': str(doi_req.id)},
            )
    except Exception as e:
        logger.warning("DOI notify reviewers failed: %s", e)
