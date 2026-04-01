# Tarjima: har bir so'z narxi (translation_per_word), default 100 so'm
from django.db import migrations


def add_translation_per_word(apps, schema_editor):
    ServicePrice = apps.get_model('udc', 'ServicePrice')
    ServicePrice.objects.update_or_create(
        service_key='translation_per_word',
        defaults={
            'label': "Tarjima xizmati (1 so'z)",
            'amount': 100,
            'currency': 'UZS',
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('udc', '0007_lower_article_sample_prices'),
    ]

    operations = [
        migrations.RunPython(add_translation_per_word, noop),
    ]
