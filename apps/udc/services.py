"""
UDC (Universal Decimal Classification) service.
Fetches hierarchy from teacode.com/online/udc/ and provides O'zbekiston-specific codes.
Supports UDK kitobi o'zbekchasi: load from data/udk_ozbek.json when available.
"""
import json
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

# UDK o'zbekcha kitobdan JSON (parse_udk_book management command bilan to'ldiriladi)
_UDK_OZBEK_CACHE = None
UDK_OZBEK_JSON_PATH = os.path.join(os.path.dirname(__file__), 'data', 'udk_ozbek.json')

UDC_BASE_URL = 'https://teacode.com/online/udc'
REQUEST_TIMEOUT = 15
REQUEST_HEADERS = {
    'User-Agent': 'Phoenix-Ilmiy/1.0 (UDC lookup; +https://ilmiyfaoliyat.uz)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'ru,uz;q=0.9,en;q=0.8',
}

# Top-level UDC from teacode.com main page (code, description, count)
UDC_ROOT = [
    ('00', 'Наука в целом (информационные технологии - 004)', 1082),
    ('1', 'Философия. Психология', 740),
    ('2', 'Религия. Теология', 993),
    ('30', 'Теория и методы общественных наук', 428),
    ('31', 'Демография. Социология. Статистика', 748),
    ('32', 'Политика', 328),
    ('33', 'Экономика. Народное хозяйство. Экономические науки', 2964),
    ('34', 'Право. Юридические науки', 4414),
    ('35', 'Государственное административное управление. Военное искусство. Военные науки', 2428),
    ('36', 'Обеспечение духовных и материальных жизненных потребностей. Социальное обеспечение', 1400),
    ('37', 'Народное образование. Воспитание. Обучение. Организация досуга', 1174),
    ('39', 'Этнография. Нравы. Обычаи. Жизнь народа. Фольклор', 308),
    ('50', 'Общие вопросы математических и естественных наук', 152),
    ('51', 'Математика', 3054),
    ('52', 'Астрономия. Геодезия', 1683),
    ('53', 'Физика', 3937),
    ('54', 'Химия. Кристаллография. Минералогия', 7642),
    ('55', 'Геология. Геологические и геофизические науки', 3179),
    ('56', 'Палеонтология', 1153),
    ('57', 'Биологические науки', 2788),
    ('58', 'Ботаника', 1963),
    ('59', 'Зоология', 3176),
    ('60', 'Прикладные науки. Общие вопросы', 8),
    ('61', 'Медицина. Охрана здоровья. Пожарное дело', 13058),
    ('62', 'Инженерное дело. Техника в целом', 21474),
    ('63', 'Сельское хозяйство. Лесное хозяйство. Охота. Рыбное хозяйство', 5995),
    ('64', 'Домоводство. Коммунальное хозяйство. Служба быта', 1862),
    ('65', 'Управление предприятиями. Организация производства, торговли и транспорта', 3977),
    ('66', 'Химическая технология. Химическая промышленность. Пищевая промышленность. Металлургия', 10167),
    ('67', 'Различные отрасли промышленности и ремесла. Механическая технология', 7822),
    ('68', 'Различные отрасли промышленности. Точная механика', 7215),
    ('69', 'Строительство. Строительные материалы. Строительно-монтажные работы', 1418),
    ('7', 'Искусство. Декоративно-прикладное искусство. Фотография. Музыка. Игры. Спорт', 5527),
    ('8', 'Языкознание. Филология. Художественная литература. Литературоведение', 1751),
    ('9', 'География. Биография. История', 433),
]

# O'zbekiston uchun maxsus UDK kodlari (UDC regional: 94(575.1) = O'zbekiston)
UDC_UZBEKISTAN = [
    ('94(575.1)', 'O\'zbekiston tarixi', 0),
    ('908(575.1)', 'O\'zbekiston geografiyasi. O\'rta Osiyo', 0),
    ('32(575.1)', 'O\'zbekiston siyosati', 0),
    ('33(575.1)', 'O\'zbekiston iqtisodiyoti', 0),
    ('34(575.1)', 'O\'zbekiston huquqi', 0),
    ('37(575.1)', 'O\'zbekistonda ta\'lim', 0),
    ('39(575.1)', 'O\'zbekiston etnografiyasi. Ma\'naviyat', 0),
    ('61(575.1)', 'O\'zbekistonda tibbiyot va salomatlik', 0),
    ('63(575.1)', 'O\'zbekiston qishloq xo\'jaligi', 0),
    ('82(575.1)', 'O\'zbek adabiyoti. O\'zbek tilida adabiyot', 0),
    ('94(575.1)(091)', 'O\'zbekiston tarixi (umumiy)', 0),
    ('94(575.1)"19"', 'O\'zbekiston XX asr tarixi', 0),
    ('94(575.1)"20"', 'O\'zbekiston XXI asr tarixi', 0),
]


def _parse_udc_table(html: str, base_path: str) -> list[dict]:
    """Parse UDC table from teacode HTML. Returns list of {code, description, has_children, path}."""
    results = []
    seen = set()
    # Pattern: <a href="...html">CODE</a> followed by description (next td or |...|)
    a_href = re.compile(
        r'<a\s+href="([^"]+\.html)">([^<]+)</a>\s*\|?\s*([^|<\n]+?)(?:\s*\|\s*[\d\s]*)?\s*\|',
        re.IGNORECASE | re.DOTALL
    )
    for m in a_href.finditer(html):
        href, code, desc = m.group(1), m.group(2).strip(), m.group(3).strip()
        desc = re.sub(r'\s+', ' ', desc).strip()
        if not code or len(code) > 30 or 'вверх' in desc.lower() or 'домой' in desc.lower():
            continue
        path = href.replace('.html', '').replace('../', '').strip('/')
        if not path.startswith('http'):
            if '/' not in path and base_path:
                path = f"{base_path}/{path}"
        if path in seen:
            continue
        seen.add(path)
        results.append({
            'code': code,
            'description': desc,
            'has_children': True,
            'path': path,
        })
    # Rows without link: | 619 | Сравнительная патология |
    no_link = re.compile(r'<td[^>]*>\s*(\d+[^<]*?)</td>\s*<td[^>]*>\s*([^<]+?)\s*</td>', re.IGNORECASE)
    for m in no_link.finditer(html):
        code_part, desc_part = m.group(1).strip(), m.group(2).strip()
        code = code_part.split()[0] if code_part else ''
        desc = re.sub(r'\s+', ' ', desc_part).strip()
        if not code or 'УДК' in desc or 'вверх' in desc.lower() or len(code) > 20:
            continue
        path = f"{base_path}/{code}" if base_path else code
        if path in seen:
            continue
        seen.add(path)
        results.append({
            'code': code,
            'description': desc,
            'has_children': False,
            'path': path,
        })
    return results


def get_root() -> list[dict]:
    """Return root-level UDC codes including O'zbekiston section."""
    items = []
    items.append({
        'code': "O'ZBEKISTON",
        'description': "O'zbekiston bo'yicha maxsus UDK kodlari",
        'has_children': True,
        'path': 'uz',
    })
    for code, desc, count in UDC_ROOT:
        items.append({
            'code': code,
            'description': desc,
            'has_children': True,
            'path': code,
            'count': count,
        })
    return items


def fetch_children(path: str) -> list[dict]:
    """
    Fetch child UDC codes from teacode.com for given path.
    path can be '61', '61/61', '61/616' etc.
    """
    if path.startswith('uz'):
        # O'zbekiston — return static list
        return [{'code': c, 'description': d, 'has_children': False, 'path': f"uz/{c}"} for c, d, _ in UDC_UZBEKISTAN]
    url = f"{UDC_BASE_URL}/{path}.html" if path else f"{UDC_BASE_URL}/index.html"
    try:
        r = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or 'utf-8'
        html = r.text
    except requests.RequestException as e:
        logger.warning(f"UDC fetch failed for {url}: {e}")
        return []
    items = _parse_udc_table(html, path)
    if not items:
        # Fallback: any <a href="*.html">CODE</a>
        for m in re.finditer(r'<a\s+href="([^"]*?([^/"]+)\.html)"[^>]*>([^<]+)</a>', html, re.IGNORECASE):
            href, code_from_url, code_text = m.group(1), m.group(2), m.group(3).strip()
            if not code_text or len(code_text) > 30 or code_text in ('вверх', 'домой'):
                continue
            path = href.replace('.html', '').replace('../', '').strip('/')
            if path and base_path and '/' not in path:
                path = f"{base_path}/{path}"
            items.append({
                'code': code_text,
                'description': '',
                'has_children': True,
                'path': path or code_text,
            })
    return items[:200]  # limit response size


def load_udk_ozbek():
    """Load UDK codes from o'zbekcha kitob JSON (data/udk_ozbek.json). Cached."""
    global _UDK_OZBEK_CACHE
    if _UDK_OZBEK_CACHE is not None:
        return _UDK_OZBEK_CACHE
    if not os.path.isfile(UDK_OZBEK_JSON_PATH):
        _UDK_OZBEK_CACHE = []
        return []
    try:
        with open(UDK_OZBEK_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get('items', data.get('codes', []))
        _UDK_OZBEK_CACHE = [x for x in items if isinstance(x, dict) and (x.get('code') or x.get('kod'))]
        return _UDK_OZBEK_CACHE
    except Exception as e:
        logger.warning(f"load_udk_ozbek failed: {e}")
        _UDK_OZBEK_CACHE = []
        return []


def get_fallback_udk():
    """
    Oddiy 33/9 o'rniga ishlatiladigan aniq kod.
    O'zbekcha kitobdan birinchi nuqta bor iqtisodiyot kodi (33...) yoki 330.1.
    """
    ozbek = load_udk_ozbek()
    for item in ozbek:
        code = (item.get('code') or item.get('kod') or '').strip()
        if not code or '.' not in code:
            continue
        if code.startswith('33') and code != '33':
            desc = (item.get('description') or item.get('tavsif') or item.get('desc') or '').strip()[:300]
            return code, desc or "Iqtisodiyot"
    return "330.1", "Iqtisodiyot. Umumiy masalalar"


def get_udc_reference_for_ai():
    """Build a single text listing UDK codes and descriptions for AI. Prefer o'zbekcha kitob when available."""
    ozbek = load_udk_ozbek()
    if ozbek:
        # Faqat aniq, tarmoqlangan kodlar (nuqta bor — 332.055.2, 001.892); oddiy 33, 9 kiritilmasin
        with_dot = [x for x in ozbek if '.' in ((x.get('code') or x.get('kod')) or '')]
        ordered = with_dot[:550] if with_dot else ozbek[:400]
        lines = []
        for item in ordered:
            code = (item.get('code') or item.get('kod') or '').strip()
            desc = (item.get('description') or item.get('tavsif') or item.get('desc') or '').strip()[:300]
            if code:
                lines.append(f"  {code} — {desc}")
        if lines:
            return "\n".join(lines)
    lines = []
    for code, desc, _ in UDC_UZBEKISTAN:
        lines.append(f"  {code} — {desc}")
    for code, desc, _ in UDC_ROOT:
        lines.append(f"  {code} — {desc}")
    return "\n".join(lines)


def _build_children_reference(children: list) -> str:
    """Build AI reference text from list of {code, description}."""
    lines = []
    for c in children[:100]:
        code = c.get('code', '').strip()
        desc = (c.get('description') or '').strip()[:200]
        if code:
            lines.append(f"  {code} — {desc}")
    return "\n".join(lines) if lines else ""


def get_specific_udk(title: str, abstract: str, gemini_service) -> tuple:
    """
    UDK kodini olish: agar o'zbekcha kitob (udk_ozbek.json) to'ldirilgan bo'lsa — shundan;
    aks holda teacode.com ierarxiyasi orqali (root + children).
    Returns (udk_code, udk_description) yoki (None, None).
    """
    title = (title or '').strip()[:500]
    abstract = (abstract or '').strip()[:15000]
    ref_text = get_udc_reference_for_ai()
    result = gemini_service.suggest_udk(title, abstract, [], ref_text)
    if not result:
        return None, None
    code = (result.get('udk_code') or '').strip()
    desc = (result.get('udk_description') or '').strip()[:500]
    if not code:
        return None, None
    # Oddiy kod (33, 9, 30) qaytarsa — rad etamiz, fallback dan aniq kod olamiz
    if '.' not in code and code in ('33', '9', '30', '31', '32', '34', '61', '0', '00', '1', '2'):
        return get_fallback_udk()
    # O'zbekcha kitobda ko'p kod bo'lsa — bitta AI javobi yetadi
    if len(load_udk_ozbek()) >= 30:
        return code, desc
    # O'zbekiston / maxsus kodlar — chuqurlashtirmaymiz
    if '(' in code or code.startswith('94') or code.startswith('908') or code.startswith('82'):
        return code, desc
    path = code
    for _ in range(2):  # 2 qo'shimcha daraja: 33 -> 332 -> 332.055.2
        children = fetch_children(path)
        if not children:
            break
        child_ref = _build_children_reference(children)
        if not child_ref:
            break
        result = gemini_service.suggest_udk(title, abstract, [], child_ref)
        if not result:
            break
        code = (result.get('udk_code') or '').strip()
        desc = (result.get('udk_description') or '').strip()[:500]
        if not code:
            break
        next_path = next((c.get('path') for c in children if (c.get('code') or '').strip() == code), None)
        if not next_path:
            break
        path = next_path
    return code, desc


def get_service_amount(service_key: str, default: float = 0.0) -> float:
    """Return platform xizmat narxi (so'm) by service_key. Super_admin Narxlar sahifasida o'zgartira oladi."""
    try:
        from .models import ServicePrice
        row = ServicePrice.objects.filter(service_key=service_key).first()
        if row is not None:
            return float(row.amount)
    except Exception:
        pass
    return default


def get_udk_service_amount():
    """Return UDK tasdiqlangan ma'lumotnoma service price (so'm)."""
    return get_service_amount('udk_request', 1000.0)


def search(query: str, limit: int = 50) -> list[dict]:
    """Simple search: filter root + Uzbekistan by query (description/code)."""
    q = (query or '').strip().lower()
    if not q:
        return []
    results = []
    for code, desc, _ in UDC_UZBEKISTAN:
        if q in code.lower() or q in desc.lower():
            results.append({'code': code, 'description': desc, 'path': f"uz/{code}"})
    for code, desc, _ in UDC_ROOT:
        if q in code.lower() or q in desc.lower():
            results.append({'code': code, 'description': desc, 'path': code})
    return results[:limit]
