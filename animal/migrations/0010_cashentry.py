from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0009_settle'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='항목명')),
                ('amount', models.BigIntegerField(verbose_name='금액 (음수=출금)')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='비고')),
                ('is_carryover', models.BooleanField(default=False, verbose_name='이월(적립시작금) 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cash_entries', to='animal.bossweek')),
            ],
            options={
                'verbose_name': '자금 출납',
                'verbose_name_plural': '자금 출납',
                'ordering': ['-is_carryover', 'created_at', 'id'],
            },
        ),
    ]
