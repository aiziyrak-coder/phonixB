from django.db import migrations


def create_udk_price(apps, schema_editor):
    ServicePrice = apps.get_model('udc', 'ServicePrice')
    if not ServicePrice.objects.filter(service_key='udk_request').exists():
        ServicePrice.objects.create(
            service_key='udk_request',
            amount=1000,
            currency='UZS',
            label="UDK tasdiqlangan ma'lumotnoma (so'm)",
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('udc', '0001_service_price'),
    ]

    operations = [
        migrations.RunPython(create_udk_price, noop),
    ]
