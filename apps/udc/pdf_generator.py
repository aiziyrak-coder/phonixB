"""
UDK HAQIDA MA'LUMOTNOMA — 2-rasmadagi professional dizayn:
fon rang, burchaklarda diagonal shakllar, ikki rangli sarlavha, vertikal chiziq, QR tasdiqlash.
"""
import logging
import os
import tempfile
from io import BytesIO
from datetime import date
from django.conf import settings

logger = logging.getLogger(__name__)

COLOR_DARK = '#1a365d'
COLOR_MID = '#2c5282'
COLOR_TEAL = '#0d9488'
COLOR_LIGHT_TEAL = '#5eead4'
COLOR_LIGHT = '#e0f2f1'
COLOR_BG = '#f1f5f9'
COLOR_TEXT = '#1e293b'


def _make_qr_image(verification_url: str, size_mm: float = 26):
    """QR kod PNG — vaqtincha faylga yoziladi. Returns (path, cleanup_func) yoki (None, None)."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        fd, path = tempfile.mkstemp(suffix='.png')
        try:
            img.save(path, format='PNG')
            return path, (lambda: os.unlink(path) if os.path.isfile(path) else None)
        except Exception:
            os.unlink(path)
            return None, None
    except Exception as e:
        logger.warning("QR code generation failed: %s", e)
        return None, None


def _draw_reference_design(canvas, doc):
    """Referens: fon, yuqori o'ng/pastki chap diagonal shakllar, emblem, dafna, Phoenix logo, vertikal chiziq."""
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors

    pw, ph = landscape(A4)
    m = 18 * mm
    dark = colors.HexColor(COLOR_DARK)
    teal = colors.HexColor(COLOR_TEAL)
    light_teal = colors.HexColor(COLOR_LIGHT_TEAL)
    light = colors.HexColor(COLOR_LIGHT)
    bg = colors.HexColor(COLOR_BG)

    canvas.saveState()
    # 1. Butun sahifa yengil kulrang fon
    canvas.setFillColor(bg)
    canvas.rect(0, 0, pw, ph, fill=1, stroke=0)

    # 2. Yuqori o'ng burchak: diagonal paralellogramlar (bir nechta qatlam)
    canvas.setFillColor(light)
    canvas.translate(pw - 52 * mm, ph - 22 * mm)
    canvas.rotate(-22)
    canvas.rect(0, 0, 38 * mm, 14 * mm, fill=1, stroke=0)
    canvas.rotate(22)
    canvas.translate(-(pw - 52 * mm), -(ph - 22 * mm))
    canvas.setFillColor(teal)
    canvas.translate(pw - 45 * mm, ph - 30 * mm)
    canvas.rotate(-18)
    canvas.rect(0, 0, 32 * mm, 11 * mm, fill=1, stroke=0)
    canvas.rotate(18)
    canvas.translate(-(pw - 45 * mm), -(ph - 30 * mm))
    canvas.setFillColor(dark)
    canvas.translate(pw - 38 * mm, ph - 38 * mm)
    canvas.rotate(-14)
    canvas.rect(0, 0, 26 * mm, 9 * mm, fill=1, stroke=0)
    canvas.rotate(14)
    canvas.translate(-(pw - 38 * mm), -(ph - 38 * mm))

    # 3. Pastki chap burchak: diagonal shakllar
    canvas.setFillColor(light_teal)
    canvas.translate(12 * mm, 20 * mm)
    canvas.rotate(28)
    canvas.rect(0, 0, 42 * mm, 15 * mm, fill=1, stroke=0)
    canvas.rotate(-28)
    canvas.translate(-12 * mm, -20 * mm)
    canvas.setFillColor(teal)
    canvas.translate(20 * mm, 28 * mm)
    canvas.rotate(22)
    canvas.rect(0, 0, 35 * mm, 12 * mm, fill=1, stroke=0)
    canvas.rotate(-22)
    canvas.translate(-20 * mm, -28 * mm)
    canvas.setFillColor(light)
    canvas.translate(28 * mm, 36 * mm)
    canvas.rotate(16)
    canvas.rect(0, 0, 28 * mm, 10 * mm, fill=1, stroke=0)
    canvas.rotate(-16)
    canvas.translate(-28 * mm, -36 * mm)

    # 4. Yuqori o'ng: dumaloq emblem (halqalar + qush silueti)
    cx, cy = pw - 28 * mm, ph - 28 * mm
    canvas.setFillColor(light_teal)
    canvas.setStrokeColor(teal)
    canvas.setLineWidth(0.5)
    canvas.circle(cx, cy, 14 * mm, fill=1, stroke=1)
    canvas.setFillColor(teal)
    canvas.circle(cx, cy, 11 * mm, fill=1, stroke=0)
    canvas.setFillColor(light_teal)
    canvas.circle(cx, cy, 8 * mm, fill=1, stroke=0)
    # Qush: bosh (ellips) + tanasi (ellips) — teal fon ustida
    canvas.setFillColor(colors.HexColor('#0d9488'))
    canvas.saveState()
    canvas.translate(cx, cy)
    canvas.rotate(-25)
    canvas.ellipse(-4 * mm, -2.5 * mm, 4 * mm, 2.5 * mm, fill=1, stroke=0)
    canvas.ellipse(-6 * mm, -3 * mm, 2 * mm, 3 * mm, fill=1, stroke=0)
    canvas.restoreState()

    # 5. Pastki chap: dafna gulchambar (teal yoylar)
    canvas.setStrokeColor(teal)
    canvas.setLineWidth(2.5)
    canvas.setFillColor(colors.white)
    lx, ly = 32 * mm, 38 * mm
    canvas.ellipse(lx - 14 * mm, ly - 9 * mm, lx + 14 * mm, ly + 9 * mm, fill=0, stroke=1)
    canvas.ellipse(lx - 10 * mm, ly - 11 * mm, lx + 10 * mm, ly + 11 * mm, fill=0, stroke=1)

    # 6. Pastki o'r: Phoenix logo (teal qush silueti)
    px, py = pw / 2, 32 * mm
    canvas.setFillColor(teal)
    canvas.translate(px, py)
    canvas.ellipse(-6 * mm, -4 * mm, 6 * mm, 4 * mm, fill=1, stroke=0)
    canvas.ellipse(-8 * mm, -2 * mm, 0, 4 * mm, fill=1, stroke=0)
    canvas.ellipse(0, -2 * mm, 8 * mm, 4 * mm, fill=1, stroke=0)
    canvas.translate(-px, -py)

    # 7. Kontent zonasida vertikal teal chiziq
    canvas.setStrokeColor(teal)
    canvas.setLineWidth(1.5)
    canvas.line(m + 26 * mm, 55 * mm, m + 26 * mm, ph - 50 * mm)
    canvas.restoreState()


def generate_udk_certificate_pdf(
    article_title: str,
    author_name: str,
    udk_code: str,
    udk_description: str,
    document_number: str = '',
    document_date: str = None,
    verification_url: str = '',
) -> BytesIO:
    """UDK HAQIDA MA'LUMOTNOMA — 2-rasmadagi dizayn."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            Image as RLImage,
        )
        from reportlab.lib import colors
    except ImportError as e:
        logger.error("reportlab not installed: %s", e)
        raise RuntimeError("reportlab is required for UDK certificate generation")

    if not document_date:
        document_date = date.today().strftime('%d.%m.%Y')
    buffer = BytesIO()
    margin = 18 * mm
    pw, ph = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=margin,
        leftMargin=margin,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    dark = colors.HexColor(COLOR_DARK)
    teal = colors.HexColor(COLOR_TEAL)
    mid = colors.HexColor(COLOR_MID)
    text = colors.HexColor(COLOR_TEXT)

    # Label — teal (2-rasmadagi chap ustun rangi)
    label_style = ParagraphStyle(
        name='Label', parent=styles['Normal'], fontSize=10, textColor=teal,
        fontName='Helvetica-Bold', spaceAfter=2,
    )
    value_style = ParagraphStyle(
        name='Value', parent=styles['Normal'], fontSize=10, textColor=text,
        spaceAfter=6, leftIndent=0,
    )
    # Sarlavha: "UDK HAQIDA" teal, "MA'LUMOTNOMA" qora ko'k
    title_teal = ParagraphStyle(
        name='TitleTeal', parent=styles['Heading1'], fontSize=16, textColor=teal,
        fontName='Helvetica-Bold', alignment=1, spaceAfter=0,
    )
    title_dark = ParagraphStyle(
        name='TitleDark', parent=styles['Heading1'], fontSize=16, textColor=dark,
        fontName='Helvetica-Bold', alignment=1, spaceAfter=10 * mm,
    )
    small_style = ParagraphStyle(
        name='Small', parent=styles['Normal'], fontSize=8, textColor=mid, alignment=0,
    )

    story = []

    # Yuqori teal chiziq (2-rasmadagi yuqori band)
    band = Table(
        [[Paragraph('', ParagraphStyle('E', parent=styles['Normal'], fontSize=1))]],
        colWidths=[pw - 2 * margin],
        rowHeights=[5 * mm],
    )
    band.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), teal),
        ('BOX', (0, 0), (-1, -1), 0, colors.white),
    ]))
    story.append(band)
    story.append(Spacer(1, 5 * mm))

    # HUJJAT RAQAMI (chap), HUJJAT SANASI (o'ng) — qora ko'k
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, textColor=dark, fontName='Helvetica-Bold')
    header_row = [
        Paragraph(f'HUJJAT RAQAMI: {document_number or "—"}', header_style),
        Paragraph(f'HUJJAT SANASI: {document_date}', header_style),
    ]
    t_header = Table([header_row], colWidths=[85 * mm, 85 * mm])
    t_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 6 * mm))

    # Ikki rangli sarlavha: UDK HAQIDA (teal) + MA'LUMOTNOMA (qora ko'k)
    story.append(Paragraph("UDK HAQIDA", title_teal))
    story.append(Paragraph("MA'LUMOTNOMA", title_dark))

    # Asosiy kontent: chapda label (teal), o'ngda qiymat; vertikal chiziq canvas da
    web_site = getattr(settings, 'FRONTEND_BASE_URL', 'https://ilmiyfaoliyat.uz').replace('http://', '').replace('https://', '').rstrip('/') or 'www.ilmiyfaoliyat.uz'
    udk_desc_text = (udk_description or '').strip().replace('&', '&amp;')[:220]
    if not udk_desc_text:
        udk_desc_text = '—'
    rows = [
        [Paragraph('MUALLIF', label_style), Paragraph((author_name or '—').replace('&', '&amp;'), value_style)],
        [Paragraph('ISH NOMI', label_style), Paragraph((article_title or '—').replace('&', '&amp;')[:200], value_style)],
        [Paragraph('UDK RAQAMI', label_style), Paragraph(f'<b>{udk_code or "—"}</b>', value_style)],
        [Paragraph('', label_style), Paragraph(udk_desc_text, small_style)],
        [Paragraph('WEB-SAYT', label_style), Paragraph(web_site, value_style)],
    ]
    t_content = Table(rows, colWidths=[26 * mm, 98 * mm])
    t_content.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 8),
        ('LINEAFTER', (0, 0), (0, -1), 2, teal),
        ('TOPPADDING', (1, 3), (1, 3), 2),
    ]))
    story.append(t_content)
    story.append(Spacer(1, 12 * mm))

    # Pastki qism: chapda "dafna" emblem (teal doira), QR, matn; o'ngda Phoenix Nashriyoti
    qr_cleanup = None
    qr_path, qr_cleanup = _make_qr_image(verification_url or 'https://ilmiyfaoliyat.uz')
    qr_flowable = None
    if qr_path and os.path.isfile(qr_path):
        try:
            qr_flowable = RLImage(qr_path, width=24 * mm, height=24 * mm)
        except Exception as e:
            logger.warning("QR Image load failed: %s", e)
    if qr_flowable is None:
        qr_flowable = Paragraph('<i>QR</i>', small_style)

    verify_text = Paragraph(
        '<b>TEKSHIRISH UCHUN QR KODDAN FOYDALANING</b><br/>'
        '<font size="8">Ma\'lumotnoma haqiqiyligini tekshirish uchun telefon yoki planshetda QR kodni skanerlang.</font>',
        ParagraphStyle(name='V', parent=small_style, fontSize=9, textColor=teal, alignment=0),
    )
    t_footer = Table(
        [
            [qr_flowable, verify_text, Paragraph('Phoenix<br/><font size="9" color="#0d9488">NASHRIYOTI</font>', ParagraphStyle('P', parent=small_style, alignment=1))],
        ],
        colWidths=[24 * mm, 75 * mm, 45 * mm],
        rowHeights=[28 * mm],
    )
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('LEFTPADDING', (1, 0), (1, 0), 10),
    ]))
    story.append(t_footer)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(
        "Ushbu ma'lumotnoma asar mavzusiga mos UDK raqamini tasdiqlaydi. Phoenix Ilmiy Nashrlar Markazi platformasi tomonidan berilgan.",
        ParagraphStyle(name='F', parent=small_style, fontSize=8, alignment=1, textColor=mid),
    ))
    story.append(Paragraph("© Phoenix Ilmiy Nashrlar Markazi", ParagraphStyle(name='F2', parent=small_style, fontSize=8, alignment=1, textColor=dark)))

    # Har sahifada (birinchi ham) referens dizayn: fon, diagonal shakllar, emblem, dafna, logo
    from reportlab.pdfgen import canvas as pdfgen_canvas
    class _CertCanvas(pdfgen_canvas.Canvas):
        def _startPage(self):
            super()._startPage()
            _draw_reference_design(self, None)
    doc.build(story, canvasmaker=_CertCanvas)
    if qr_cleanup:
        try:
            qr_cleanup()
        except Exception:
            pass
    buffer.seek(0)
    return buffer
