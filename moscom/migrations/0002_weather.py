from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moscom', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='temperature',
            field=models.FloatField(blank=True, null=True, verbose_name='기온(°C)'),
        ),
        migrations.AddField(
            model_name='device',
            name='humidity',
            field=models.FloatField(blank=True, null=True, verbose_name='습도(%)'),
        ),
        migrations.AddField(
            model_name='device',
            name='precipitation',
            field=models.FloatField(blank=True, null=True, verbose_name='강수량(mm)'),
        ),
        migrations.AddField(
            model_name='device',
            name='wind_speed',
            field=models.FloatField(blank=True, null=True, verbose_name='풍속(m/s)'),
        ),
        migrations.AddField(
            model_name='device',
            name='weather_synced_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='날씨 동기화'),
        ),
    ]
