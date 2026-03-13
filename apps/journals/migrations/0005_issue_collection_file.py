# Generated manually for collection file upload

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journals', '0004_plagiarism_ai_thresholds'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='collection_file',
            field=models.FileField(blank=True, null=True, upload_to='issues/collections/'),
        ),
    ]
