# Maqola namuna olish narxlari (1 bet) — foydalanuvchi talabiga ko'ra pasaytirildi.
from django.db import migrations


NEW_AMOUNTS = {
    'article_sample_quyi': 25_000,
    'article_sample_orta': 45_000,
    'article_sample_yuqori': 75_000,
}


def lower_prices(apps, schema_editor):
    ServicePrice = apps.get_model('udc', 'ServicePrice')
    for key, amount in NEW_AMOUNTS.items():
        ServicePrice.objects.filter(service_key=key).update(amount=amount)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('udc', '0006_seed_all_service_prices'),
    ]

    operations = [
        migrations.RunPython(lower_prices, noop),
    ]
