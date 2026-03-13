# Barcha xizmatlar uchun narxlarni yaratish (Narxlar sahifasida to'liq ro'yxat chiqishi uchun)
from django.db import migrations


SERVICE_PRICES = [
    ('udk_request', "UDK tasdiqlangan ma'lumotnoma", 50000),
    ('plagiarism_check', "Antiplagiat tekshiruv (to'liq hisobot)", 30000),
    ('doi_request', 'DOI raqami olish', 100000),
    ('article_sample_quyi', 'Maqola namuna olish (Quyi sifat)', 150000),
    ('article_sample_orta', "Maqola namuna olish (O'rta sifat)", 250000),
    ('article_sample_yuqori', 'Maqola namuna olish (Yuqori sifat)', 400000),
    ('translation_per_page', 'Tarjima xizmati (1 bet uchun)', 50000),
    ('book_publication_base', 'Kitob nashr qilish (Bazaviy narx)', 500000),
    ('fast_track', "Fast track (tezlashtirilgan ko'rib chiqish)", 200000),
    ('language_editing', 'Tahrir qilish xizmati', 100000),
    ('publication_fee', 'Nashr qilish to\'lovi', 150000),
]


def seed_all_prices(apps, schema_editor):
    ServicePrice = apps.get_model('udc', 'ServicePrice')
    for service_key, label, amount in SERVICE_PRICES:
        obj, created = ServicePrice.objects.get_or_create(
            service_key=service_key,
            defaults={'amount': amount, 'currency': 'UZS', 'label': label},
        )
        if not created and (obj.label != label or float(obj.amount) != amount):
            obj.label = label
            obj.amount = amount
            obj.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('udc', '0005_udkrequest'),
    ]

    operations = [
        migrations.RunPython(seed_all_prices, noop),
    ]
