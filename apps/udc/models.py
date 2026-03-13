from django.conf import settings
from django.db import models
import uuid


# UDK so'rovi statuslari
UDK_REQUEST_STATUS_PENDING_PAYMENT = 'pending_payment'
UDK_REQUEST_STATUS_SUBMITTED = 'submitted'
UDK_REQUEST_STATUS_COMPLETED = 'completed'
UDK_REQUEST_STATUS_REJECTED = 'rejected'


class UdkRequest(models.Model):
    """UDK raqami olish so'rovi: muallif mavzu va fayl yuboradi, to'lovdan keyin taqrizchiga boradi."""
    STATUS_CHOICES = (
        (UDK_REQUEST_STATUS_PENDING_PAYMENT, 'To\'lov kutilmoqda'),
        (UDK_REQUEST_STATUS_SUBMITTED, 'Taqrizchida'),
        (UDK_REQUEST_STATUS_COMPLETED, 'Yakunlangan'),
        (UDK_REQUEST_STATUS_REJECTED, 'Rad etilgan'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='udk_requests')
    transaction = models.OneToOneField(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='udk_request'
    )
    # Muallif ma'lumotlari
    author_first_name = models.CharField(max_length=150)
    author_last_name = models.CharField(max_length=150)
    author_middle_name = models.CharField(max_length=150, blank=True)
    # Ish ma'lumotlari
    title = models.CharField(max_length=500)
    abstract = models.TextField(blank=True)
    file = models.FileField(upload_to='udk_requests/%Y/%m/', blank=True, null=True)
    # Natija (taqrizchi tomonidan to'ldiriladi)
    udk_code = models.CharField(max_length=100, blank=True)
    udk_description = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=UDK_REQUEST_STATUS_PENDING_PAYMENT)
    reject_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'UDK so\'rovi'
        verbose_name_plural = 'UDK so\'rovlari'

    def __str__(self):
        return f"{self.author_last_name} {self.author_first_name} — {self.get_status_display()}"


class UDKCertificate(models.Model):
    """Standalone UDK ma'lumotnoma (maqolaga bog'lanmagan: mavzu/fayl orqali buyurtma)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='udk_certificates'
    )
    author_name = models.CharField(max_length=300, blank=True)
    title = models.CharField(max_length=500)
    udk_code = models.CharField(max_length=50)
    udk_description = models.TextField(blank=True)
    certificate_path = models.FileField(upload_to='udc/certificates/', blank=True, null=True)
    transaction = models.OneToOneField(
        'payments.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='udk_certificate'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "UDK ma'lumotnoma (standalone)"
        verbose_name_plural = "UDK ma'lumotnomalar (standalone)"

    def __str__(self):
        return f"{self.title[:50]} — {self.udk_code}"


class ServicePrice(models.Model):
    """Platform xizmat narxlari (super_admin admin panelda tahrirlaydi)."""
    service_key = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='UZS')
    label = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Xizmat narxi'
        verbose_name_plural = 'Xizmat narxlari'

    def __str__(self):
        return f"{self.service_key}: {self.amount} {self.currency}"
