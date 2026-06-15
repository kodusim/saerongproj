from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moscom', '0004_device_habitat'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='overview_name',
            field=models.CharField('종합현황 표시명', max_length=80, blank=True, default=''),
        ),
    ]
