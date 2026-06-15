from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moscom', '0003_region'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='region_type',
            field=models.CharField('지역 분류', max_length=20, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='device',
            name='form_type',
            field=models.CharField('형태 분류', max_length=20, blank=True, default=''),
        ),
    ]
