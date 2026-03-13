import os
import tempfile
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny

from . import services
from .models import UdkRequest, UDKCertificate, UDK_REQUEST_STATUS_SUBMITTED, UDK_REQUEST_STATUS_COMPLETED, ServicePrice


# ============ UdkRequest Serializer ============
class UdkRequestSerializer(serializers.ModelSerializer):
    """UDK so'rovi serializer: taqrizchi va muallif uchun."""
    file_url = serializers.SerializerMethodField()
    author_short = serializers.SerializerMethodField()

    class Meta:
        model = UdkRequest
        fields = (
            'id', 'author_first_name', 'author_last_name', 'author_middle_name', 'author_short',
            'title', 'abstract', 'file', 'file_url', 'udk_code', 'udk_description',
            'status', 'reject_reason', 'created_at', 'completed_at',
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return str(obj.file.url) if obj.file else None

    def get_author_short(self, obj):
        parts = [obj.author_last_name, obj.author_first_name]
        if obj.author_middle_name:
            parts.append(obj.author_middle_name)
        return ' '.join(parts)


# ============ ServicePrice Serializer ============
class ServicePriceSerializer(serializers.ModelSerializer):
    """Platform xizmat narxlari serializer."""
    
    class Meta:
        model = ServicePrice
        fields = '__all__'


# ============ ServicePrice ViewSet ============
class ServicePriceViewSet(ModelViewSet):
    """
    Platform xizmat narxlarini boshqarish.
    - GET /api/v1/service-prices/ - Barcha narxlar ro'yxati
    - POST /api/v1/service-prices/ - Yangi narx yaratish
    - PUT/PATCH /api/v1/service-prices/{id}/ - Narxni yangilash
    - DELETE /api/v1/service-prices/{id}/ - Narxni o'chirish
    
    Faqat super_admin huquqi bor.
    """
    queryset = ServicePrice.objects.all()
    serializer_class = ServicePriceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Barcha narxlarni qaytarish."""
        return ServicePrice.objects.all().order_by('service_key')
    
    def perform_create(self, serializer):
        """Yangi narx yaratish."""
        serializer.save()
    
    def perform_update(self, serializer):
        """Narxni yangilash."""
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        """Narxni o'chirish."""
        instance = self.get_object()
        return super().destroy(request, *args, **kwargs)


# ============ UDK Request Views ============
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def udk_request_create(request):
    """
    UDK so'rovi yaratish: muallif ism/familya, mavzu, abstract va fayl yuboradi.
    To'lovdan keyin status 'submitted' ga o'zgaradi va taqrizchiga boradi.
    """
    from apps.payments.models import Transaction
    
    data = request.data if hasattr(request, 'data') else request.POST.dict()
    
    author_first_name = (data.get('author_first_name') or '').strip()
    author_last_name = (data.get('author_last_name') or '').strip()
    author_middle_name = (data.get('author_middle_name') or '').strip()
    title = (data.get('title') or '').strip()
    abstract = (data.get('abstract') or '').strip()[:15000]
    
    if not author_first_name or not author_last_name:
        return Response({'detail': 'Ism va familya majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    if not title:
        return Response({'detail': 'Mavzu (sarlavha) majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    if not abstract:
        return Response({'detail': 'Annotatsiya majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES.get('file') if request.FILES else None
    
    udk_payment_enabled = getattr(settings, 'UDK_PAYMENT_ENABLED', True)
    amount = 0 if not udk_payment_enabled else services.get_udk_service_amount()
    
    # UdkRequest yaratish
    udk_req = UdkRequest.objects.create(
        user=request.user,
        author_first_name=author_first_name,
        author_last_name=author_last_name,
        author_middle_name=author_middle_name,
        title=title,
        abstract=abstract,
        file=uploaded_file,
        status='pending_payment',
    )
    
    # Tranzaksiya yaratish
    transaction = Transaction.objects.create(
        user=request.user,
        amount=amount,
        currency='UZS',
        service_type='udk_request',
        extra_data={'udk_request_id': str(udk_req.id)},
    )
    udk_req.transaction = transaction
    udk_req.save(update_fields=['transaction'])
    
    if amount == 0:
        # To'lov talab qilinmasa - darhol taqrizchiga yuborish
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save(update_fields=['status', 'completed_at'])
        udk_req.status = UDK_REQUEST_STATUS_SUBMITTED
        udk_req.save(update_fields=['status'])
        _notify_reviewers_udk_request(udk_req)
        return Response({
            'udk_request_id': str(udk_req.id),
            'transaction_id': str(transaction.id),
            'amount': 0,
            'currency': 'UZS',
            'submitted': True,
            'message': "UDK so'rovi taqrizchiga yuborildi.",
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'udk_request_id': str(udk_req.id),
        'transaction_id': str(transaction.id),
        'amount': amount,
        'currency': 'UZS',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udk_request_list(request):
    """
    UDK so'rovlari ro'yxati:
    - Taqrizchi/super_admin: barcha submitted so'rovlar
    - Oddiy foydalanuvchi: faqat o'zining so'rovlari
    """
    user = request.user
    role = getattr(user, 'role', None)
    
    if role in ['reviewer', 'super_admin']:
        # Taqrizchi barcha submitted va completed so'rovlarni ko'radi
        qs = UdkRequest.objects.all().order_by('-created_at')[:100]
    else:
        # Muallif faqat o'zini ko'radi
        qs = UdkRequest.objects.filter(user=user).order_by('-created_at')[:50]
    
    serializer = UdkRequestSerializer(qs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def udk_request_complete(request, pk):
    """
    UDK so'rovini yakunlash: taqrizchi UDK kod va description kiritadi.
    """
    user = request.user
    role = getattr(user, 'role', None)
    
    if role not in ['reviewer', 'super_admin']:
        return Response({'detail': 'Faqat taqrizchi bu amalni bajarishi mumkin.'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        udk_req = UdkRequest.objects.get(id=pk)
    except UdkRequest.DoesNotExist:
        return Response({'detail': 'UDK so\'rovi topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
    
    if udk_req.status == UDK_REQUEST_STATUS_COMPLETED:
        return Response({'detail': 'Bu so\'rov allaqachon yakunlangan.'}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data if hasattr(request, 'data') else request.POST.dict()
    udk_code = (data.get('udk_code') or '').strip()
    udk_description = (data.get('udk_description') or '').strip()
    
    if not udk_code:
        return Response({'detail': 'UDK kodi majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    
    udk_req.udk_code = udk_code
    udk_req.udk_description = udk_description
    udk_req.status = UDK_REQUEST_STATUS_COMPLETED
    udk_req.completed_at = timezone.now()
    udk_req.save(update_fields=['udk_code', 'udk_description', 'status', 'completed_at'])
    
    # UDKCertificate yaratish
    cert = UDKCertificate.objects.create(
        user=udk_req.user,
        author_name=f"{udk_req.author_last_name} {udk_req.author_first_name} {udk_req.author_middle_name}".strip(),
        title=udk_req.title,
        udk_code=udk_code,
        udk_description=udk_description,
        transaction=udk_req.transaction,
    )
    
    # PDF generatsiya
    try:
        from .pdf_generator import generate_udk_certificate_pdf
        pdf_path = generate_udk_certificate_pdf(cert)
        if pdf_path:
            cert.certificate_path = pdf_path
            cert.save(update_fields=['certificate_path'])
    except Exception as e:
        print(f"[UDK] PDF generation error: {e}")
    
    # Muallifga bildirishnoma yuborish
    _notify_author_udk_completed(udk_req, cert)
    
    return Response({
        'message': 'UDK so\'rovi yakunlandi va muallifga xabar yuborildi.',
        'certificate_id': cert.id,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def udk_request_reject(request, pk):
    """
    UDK so'rovini rad etish: taqrizchi sabab kiritadi.
    """
    user = request.user
    role = getattr(user, 'role', None)
    
    if role not in ['reviewer', 'super_admin']:
        return Response({'detail': 'Faqat taqrizchi bu amalni bajarishi mumkin.'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        udk_req = UdkRequest.objects.get(id=pk)
    except UdkRequest.DoesNotExist:
        return Response({'detail': 'UDK so\'rovi topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
    
    if udk_req.status == UDK_REQUEST_STATUS_COMPLETED:
        return Response({'detail': 'Bu so\'rov allaqachon yakunlangan.'}, status=status.HTTP_400_BAD_REQUEST)
    
    data = request.data if hasattr(request, 'data') else request.POST.dict()
    reject_reason = (data.get('reject_reason') or '').strip()
    
    udk_req.status = 'rejected'
    udk_req.reject_reason = reject_reason
    udk_req.save(update_fields=['status', 'reject_reason'])
    
    # Muallifga bildirishnoma yuborish
    _notify_author_udk_rejected(udk_req)
    
    return Response({'message': 'UDK so\'rovi rad etildi.'})


def _notify_reviewers_udk_request(udk_req):
    """Taqrizchilarga yangi UDK so'rovi haqida xabar yuborish."""
    try:
        from apps.notifications.models import Notification
        from apps.users.models import User
        
        reviewers = User.objects.filter(role__in=['reviewer', 'super_admin'], is_active=True)
        for reviewer in reviewers:
            Notification.objects.create(
                user=reviewer,
                title="Yangi UDK so'rovi",
                message=f"Yangi UDK so'rovi keldi: {udk_req.title[:50]}... — {udk_req.author_last_name} {udk_req.author_first_name}",
                type='udk_request',
            )
        print(f"[UDK] Notified {reviewers.count()} reviewers about UDK request {udk_req.id}")
    except Exception as e:
        print(f"[UDK] Failed to notify reviewers: {e}")


def _notify_author_udk_completed(udk_req, cert):
    """Muallifga UDK tayyor bo'lgani haqida xabar yuborish."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=udk_req.user,
            title="UDK ma'lumotnoma tayyor",
            message=f"Sizning \"{udk_req.title[:40]}...\" uchun UDK ma'lumotnomasi tayyor. UDK: {udk_req.udk_code}. 'UDK Olish' bo'limidan yuklab oling.",
            type='udk_completed',
        )
    except Exception as e:
        print(f"[UDK] Failed to notify author: {e}")


def _notify_author_udk_rejected(udk_req):
    """Muallifga UDK rad etilgani haqida xabar yuborish."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=udk_req.user,
            title="UDK so'rovi rad etildi",
            message=f"Sizning \"{udk_req.title[:40]}...\" uchun UDK so'rovi rad etildi. Sabab: {udk_req.reject_reason or 'Ko\'rsatilmagan'}",
            type='udk_rejected',
        )
    except Exception as e:
        print(f"[UDK] Failed to notify author about rejection: {e}")


def _get_request_data(request):
    """Get POST/JSON data; supports both form and JSON."""
    if hasattr(request, 'data') and request.data:
        return request.data
    return request.POST.dict() if request.POST else {}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udc_price(request):
    """UDK tasdiqlangan ma'lumotnoma narxi. To'lov o'chirilgan bo'lsa 0 qaytariladi."""
    if not getattr(settings, 'UDK_PAYMENT_ENABLED', True):
        return Response({'amount': 0, 'currency': 'UZS', 'payment_required': False})
    amount = services.get_udk_service_amount()
    return Response({'amount': amount, 'currency': 'UZS', 'payment_required': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def udc_request_document(request):
    """
    UDK tasdiqlangan ma'lumotnoma so'rovi: tranzaksiya yaratadi.
    Ikki rejim:
    1) article_id — mavjud maqola uchun; UDK ni to'lovdan keyin AI aniqlaydi.
    2) Standalone: title (majburiy) + abstract (ixtiyoriy) + file (ixtiyoriy PDF).
       Maqola yuklanmagan bo'lsa ham mavzu/fayl orqali UDK buyurtma berish mumkin.
    """
    data = _get_request_data(request)
    article_id = data.get('article_id')
    udk_code = (data.get('udk_code') or '').strip()
    udk_description = (data.get('udk_description') or '').strip()[:500]

    from apps.articles.models import Article
    from apps.payments.models import Transaction

    udk_payment_enabled = getattr(settings, 'UDK_PAYMENT_ENABLED', True)
    amount = 0 if not udk_payment_enabled else services.get_udk_service_amount()

    if article_id:
        # Mavjud maqola uchun
        try:
            article = Article.objects.get(id=article_id)
        except Article.DoesNotExist:
            return Response({'detail': 'Maqola topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        if article.author_id != request.user.id:
            return Response({'detail': 'Faqat o\'z maqolangiz uchun so\'rov yuborishingiz mumkin.'}, status=status.HTTP_403_FORBIDDEN)
        extra_data = {}
        if udk_code:
            extra_data = {'udk_code': udk_code, 'udk_description': udk_description}
        transaction = Transaction.objects.create(
            user=request.user,
            article=article,
            amount=amount,
            currency='UZS',
            service_type='udk_request',
            extra_data=extra_data,
        )
        if amount == 0:
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save(update_fields=['status', 'completed_at'])
            from .fulfill import fulfill_udk_request
            fulfill_udk_request(transaction)
            return Response({
                'transaction_id': str(transaction.id),
                'amount': 0,
                'currency': 'UZS',
                'fulfilled': True,
                'article_id': str(article.id),
                'message': "UDK ma'lumotnoma tayyor. Maqola sahifasidan yuklab oling.",
            }, status=status.HTTP_201_CREATED)
        return Response({
            'transaction_id': str(transaction.id),
            'amount': amount,
            'currency': 'UZS',
        }, status=status.HTTP_201_CREATED)

    # Standalone: mavzu, annotatsiya va muallif (ism, familya, otchestva) majburiy
    title = (data.get('title') or '').strip()
    if not title:
        return Response({'detail': 'Mavzu (title) majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    abstract = (data.get('abstract') or '').strip()[:15000]
    if not abstract:
        return Response({'detail': 'Annotatsiya (qisqa mazmun) majburiy.'}, status=status.HTTP_400_BAD_REQUEST)
    author_name = (data.get('author_name') or '').strip()[:300]
    if not author_name:
        return Response({'detail': 'Muallif: ism, familya, otchestva majburiy.'}, status=status.HTTP_400_BAD_REQUEST)

    uploaded_file = request.FILES.get('file') if request.FILES else None
    if uploaded_file:
        fname = getattr(uploaded_file, 'name', '') or ''
        suffix = (os.path.splitext(fname)[1] or '.pdf').lower()
        allowed = ('.pdf', '.doc', '.docx')
        if suffix not in allowed:
            return Response(
                {'detail': f'Faqat PDF, DOC yoki DOCX qabul qilinadi. Sizning fayl: {suffix}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                if suffix == '.pdf':
                    from apps.services import get_gemini_service
                    gemini = get_gemini_service()
                    extracted = gemini.extract_text_from_pdf(tmp_path)
                else:
                    import docx2txt
                    extracted = docx2txt.process(tmp_path) or ''
                if extracted and extracted.strip():
                    abstract = (abstract + '\n\n' + extracted.strip()).strip()[:15000]
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as e:
            return Response(
                {'detail': f'Fayldan matn o\'qishda xatolik: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    transaction = Transaction.objects.create(
        user=request.user,
        article=None,
        amount=amount,
        currency='UZS',
        service_type='udk_request',
        extra_data={
            'standalone': True,
            'title': title[:500],
            'abstract': abstract,
            'author_name': author_name,
        },
    )
    if amount == 0:
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save(update_fields=['status', 'completed_at'])
        from .fulfill import fulfill_udk_request
        fulfill_udk_request(transaction)
        from .models import UDKCertificate
        cert = UDKCertificate.objects.filter(transaction=transaction).first()
        media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
        cert_url = f"{media_url}/{cert.certificate_path.name}" if cert and cert.certificate_path else None
        return Response({
            'transaction_id': str(transaction.id),
            'amount': 0,
            'currency': 'UZS',
            'fulfilled': True,
            'certificate_id': cert.id if cert else None,
            'certificate_url': cert_url,
            'message': "UDK ma'lumotnoma tayyor. 'Mening UDK ma'lumotnomalarim' bo'limidan yuklab oling.",
        }, status=status.HTTP_201_CREATED)
    return Response({
        'transaction_id': str(transaction.id),
        'amount': amount,
        'currency': 'UZS',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udc_root(request):
    """Root-level UDC codes (including O'zbekiston)."""
    items = services.get_root()
    return Response({'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udc_children(request):
    """Child UDC codes for a given path (from teacode.com)."""
    path = (request.query_params.get('path') or '').strip()
    if not path:
        return Response({'items': []})
    items = services.fetch_children(path)
    return Response({'items': items})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udc_search(request):
    """Search UDC by keyword (code or description)."""
    q = (request.query_params.get('q') or '').strip()
    limit = min(100, max(10, int(request.query_params.get('limit', 50))))
    items = services.search(q, limit=limit)
    return Response({'items': items})


@api_view(['GET'])
def udk_verify(request):
    """
    Ma'lumotnoma haqiqiyligini tekshirish (QR orqali ochiladi). Auth kerak emas.
    ?id=<certificate_id> — standalone; ?article_id=<uuid> — maqola.
    """
    from .models import UDKCertificate
    cert_id = request.query_params.get('id')
    article_id = request.query_params.get('article_id')
    if cert_id:
        try:
            cert = UDKCertificate.objects.get(id=int(cert_id))
        except (UDKCertificate.DoesNotExist, ValueError):
            return Response({'valid': False, 'detail': 'Ma\'lumotnoma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'valid': True,
            'document_number': str(cert.id),
            'document_date': cert.created_at.strftime('%d.%m.%Y') if cert.created_at else None,
            'author_name': (cert.author_name or (cert.user.get_full_name() if cert.user else '')),
            'title': cert.title,
            'udk_code': cert.udk_code,
            'udk_description': cert.udk_description or '',
        })
    if article_id:
        from apps.articles.models import Article
        try:
            article = Article.objects.get(id=article_id)
        except (Article.DoesNotExist, ValueError):
            return Response({'valid': False, 'detail': 'Ma\'lumotnoma topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        if not article.udk_code:
            return Response({'valid': False, 'detail': 'Ushbu maqolada UDK ma\'lumotnomasi yo\'q.'}, status=status.HTTP_404_NOT_FOUND)
        author_name = article.author.get_full_name() if article.author else ''
        return Response({
            'valid': True,
            'document_number': str(article.id),
            'document_date': None,
            'author_name': author_name,
            'title': article.title or '',
            'udk_code': article.udk_code,
            'udk_description': article.udk_description or '',
        })
    return Response({'valid': False, 'detail': 'id yoki article_id kerak.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_udk_certificates(request):
    """Foydalanuvchining standalone UDK ma'lumotnomalari ro'yxati."""
    from .models import UDKCertificate
    media_url = (getattr(settings, 'MEDIA_URL', '/media/') or '/media/').rstrip('/')
    certs = UDKCertificate.objects.filter(user=request.user).order_by('-created_at')[:100]
    return Response({
        'results': [
            {
                'id': c.id,
                'title': c.title,
                'udk_code': c.udk_code,
                'udk_description': c.udk_description or '',
                'certificate_url': f"{media_url}/{c.certificate_path.name}" if c.certificate_path else None,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in certs
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def udk_certificate_download(request, certificate_id):
    """Standalone UDK ma'lumotnomani yuklab olish (faqat o'zining)."""
    from .models import UDKCertificate
    from django.http import HttpResponse, Http404
    try:
        cert = UDKCertificate.objects.get(id=certificate_id, user=request.user)
    except UDKCertificate.DoesNotExist:
        raise Http404("Ma'lumotnoma topilmadi.")
    if not cert.certificate_path:
        raise Http404("Fayl mavjud emas.")
    path = cert.certificate_path.path
    if not os.path.isfile(path):
        raise Http404("Fayl topilmadi.")
    with open(path, 'rb') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="udk_malumotnoma_{cert.id}.pdf"'
    return response
