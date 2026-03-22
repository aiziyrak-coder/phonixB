"""
Muallifning barcha maqolalari bo'yicha PDF ma'lumotnoma (QR skaner — to'g'ridan-to'g'ri PDF).
Imzoli havola: JWT emas, Django TimestampSigner (cheklangan muddat).
"""
import io
import logging
from urllib.parse import quote

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)

SIGNER_SALT = 'author-malumotnoma-v1'
# QR chop etilguncha amal qiladi
MAX_AGE_SECONDS = 60 * 60 * 24 * 90  # 90 kun


def _status_label_uz(status: str) -> str:
    mapping = {
        'Draft': 'Qoralama',
        'Yangi': 'Yangi',
        'WithEditor': 'Redaktorda',
        'QabulQilingan': 'Qabul Qilingan',
        'WritingInProgress': 'Yozish jarayonida',
        'NashrgaYuborilgan': 'Nashrga Yuborilgan',
        'PlagiarismReview': 'Antiplagiat ko\'rib chiqish',
        'Revision': 'Tahrirga qaytarilgan',
        'Accepted': 'Qabul qilingan',
        'Rejected': 'Rad etilgan',
        'Published': 'Nashr etilgan',
        'PaymentCompleted': 'To\'lov yakunlandi',
        'ContractProcessing': 'Shartnoma rasmiylashtirilmoqda',
        'IsbnProcessing': 'ISBN olinmoqda',
        'AuthorDataVerified': 'Muallif ma\'lumotlari tasdiqlandi',
    }
    return mapping.get(status, status)


def _build_pdf_buffer(user, articles_qs):
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleUz',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        alignment=1,
    )
    normal = ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=9, leading=11)

    story = []
    story.append(Paragraph('BARCHA MAQOLALAR BO\'YICHA MA\'LUMOTNOMA', title_style))
    story.append(Paragraph(
        f"Hujjat sanasi: {timezone.now().strftime('%d.%m.%Y')}",
        ParagraphStyle(name='Sub', parent=styles['Normal'], fontSize=9, alignment=1),
    ))
    story.append(Spacer(1, 0.4 * cm))

    full_name = user.get_full_name() or user.email or str(user.id)
    story.append(Paragraph(f"<b>Muallif:</b> {full_name}", normal))
    if getattr(user, 'affiliation', None):
        story.append(Paragraph(f"<b>Tashkilot:</b> {user.affiliation}", normal))
    story.append(Spacer(1, 0.5 * cm))

    table_data = [
        [
            Paragraph('<b>№</b>', normal),
            Paragraph('<b>Sarlavha</b>', normal),
            Paragraph('<b>Jurnal</b>', normal),
            Paragraph('<b>Sana</b>', normal),
            Paragraph('<b>Holati</b>', normal),
        ],
    ]

    for idx, art in enumerate(articles_qs, start=1):
        jname = '-'
        try:
            if art.journal_id and art.journal:
                jname = art.journal.name or '-'
        except Exception:
            jname = '-'
        sdate = art.submission_date.strftime('%d.%m.%Y') if art.submission_date else '-'
        table_data.append([
            Paragraph(str(idx), normal),
            Paragraph(escape((art.title or '-')[:500]), normal),
            Paragraph(escape(jname[:200]), normal),
            Paragraph(escape(sdate), normal),
            Paragraph(escape(_status_label_uz(art.status)), normal),
        ])

    tw = [1 * cm, 6 * cm, 4 * cm, 2.2 * cm, 2.8 * cm]
    t = Table(table_data, colWidths=tw, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f766e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            f"Jami: {articles_qs.count()} ta maqola. Phoenix Ilmiy Nashrlar Markazi — ilmiyfaoliyat.uz",
            ParagraphStyle(name='Foot', parent=styles['Normal'], fontSize=8, textColor=colors.grey),
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def author_ma_lumotnoma_signed_url(request):
    """Muallif uchun PDF ochiladigan imzoli havola (QR kodda ishlatiladi)."""
    from django.urls import reverse

    signer = TimestampSigner(salt=SIGNER_SALT)
    sig = signer.sign(str(request.user.pk))
    rel = reverse('author_ma_lumotnoma_pdf')
    base = request.build_absolute_uri(rel)
    sep = '&' if '?' in base else '?'
    url = f"{base}{sep}sig={quote(sig, safe='')}"
    return Response({'url': url, 'expires_in_seconds': MAX_AGE_SECONDS})


@api_view(['GET'])
@permission_classes([AllowAny])
def author_ma_lumotnoma_pdf(request):
    """
    Imzoli havola orqali PDF — brauzerda application/pdf (skaner uchun Authorization kerak emas).
    """
    sig = request.GET.get('sig') or ''
    if not sig:
        return HttpResponseBadRequest('sig parametri kerak')

    signer = TimestampSigner(salt=SIGNER_SALT)
    try:
        user_id = signer.unsign(sig, max_age=MAX_AGE_SECONDS)
    except SignatureExpired:
        return HttpResponseBadRequest('Havola muddati tugagan. Yangi QR yarating.')
    except BadSignature:
        return HttpResponseBadRequest('Noto\'g\'ri havola.')

    from apps.users.models import User
    from .models import Article

    user = User.objects.filter(pk=user_id).first()
    if not user:
        raise Http404()

    articles = (
        Article.objects.filter(author=user)
        .select_related('journal')
        .order_by('-submission_date')
    )

    try:
        buffer = _build_pdf_buffer(user, articles)
    except Exception as e:
        logger.exception('author_ma_lumotnoma_pdf: %s', e)
        return HttpResponseBadRequest('PDF yaratishda xatolik.')

    filename = f"maqolalar-malumotnoma-{timezone.now().strftime('%Y%m%d')}.pdf"
    resp = FileResponse(buffer, as_attachment=False, filename=filename, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp
