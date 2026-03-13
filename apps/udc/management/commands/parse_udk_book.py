"""
PDF dan (UDK kitobi o'zbekchasi) UDK kodlari va tavsiflarini o'qib data/udk_ozbek.json ga yozadi.
Ishlatish: python manage.py parse_udk_book "C:\\Users\\...\\UDK kitobi o'zbekchasi.pdf"
"""
import json
import os
import re
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "UDK kitobi o'zbekchasi PDF dan kodlarni o'qib udk_ozbek.json ga yozadi"

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='PDF fayl yo\'li (masalan: UDK kitobi o\'zbekchasi.pdf)')

    def handle(self, *args, **options):
        pdf_path = options['pdf_path'].strip().strip('"')
        if not os.path.isfile(pdf_path):
            raise CommandError(f'Fayl topilmadi: {pdf_path}')

        self.stdout.write('PDF dan matn o\'qilmoqda...')
        try:
            from apps.services import get_gemini_service
            gemini = get_gemini_service()
            text = gemini.extract_text_from_pdf(pdf_path)
        except Exception as e:
            try:
                import PyPDF2
                text = ''
                with open(pdf_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ''
                        text += '\n'
            except Exception as e2:
                raise CommandError(f'PDF o\'qishda xatolik: {e}, {e2}')
        if not (text and text.strip()):
            raise CommandError('PDF da matn topilmadi.')

        # UDK kod: raqam va nuqta (masalan 33, 332.055.2, 94(575.1)), keyin bo'shliq, keyin tavsif
        code_desc_re = re.compile(
            r'^\s*(\d+(?:\.\d+)*(?:\([^)]+\))?(?:"[^"]*")?)\s+([^\n]{2,300})\s*$',
            re.MULTILINE
        )
        # Oddiy: raqam va nuqta boshida
        simple_re = re.compile(r'^\s*(\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)
        items = []
        seen = set()
        for m in code_desc_re.finditer(text):
            code, desc = m.group(1).strip(), m.group(2).strip()
            if code and len(code) <= 30 and code not in seen:
                seen.add(code)
                items.append({'code': code, 'description': desc[:500]})
        if not items:
            for m in simple_re.finditer(text):
                code, desc = m.group(1).strip(), m.group(2).strip()
                if code and len(code) <= 30 and code not in seen and len(desc) >= 2:
                    seen.add(code)
                    items.append({'code': code, 'description': desc[:500]})
        # Kod bo'yicha tartiblash
        items.sort(key=lambda x: (x['code'].replace('.', ' ').split()))

        out_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'udk_ozbek.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        # Cache ni tozalash
        import apps.udc.services as svc
        svc._UDK_OZBEK_CACHE = None
        self.stdout.write(self.style.SUCCESS(f'{len(items)} ta UDK kodi yozildi: {out_path}'))
        if items:
            self.stdout.write(f'Misol: {items[0]["code"]} — {items[0]["description"][:60]}...')
