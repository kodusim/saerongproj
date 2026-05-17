from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moscom', '0002_weather'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='region_code',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20, verbose_name='권역 코드'),
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=20, unique=True, verbose_name='코드')),
                ('name', models.CharField(max_length=80, verbose_name='표시명')),
                ('sort_order', models.IntegerField(default=100, verbose_name='정렬 순서')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='비고')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '권역',
                'verbose_name_plural': '권역',
                'ordering': ['sort_order', 'code'],
            },
        ),
    ]
