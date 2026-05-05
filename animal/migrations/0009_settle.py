from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0008_visitlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='bossweek',
            name='settle_diamond',
            field=models.BigIntegerField(default=0, verbose_name='분배 다이아'),
        ),
        migrations.AddField(
            model_name='bossweek',
            name='settle_date',
            field=models.DateField(blank=True, null=True, verbose_name='정산일'),
        ),
    ]
