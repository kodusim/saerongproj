from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0007_boss'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(db_index=True, max_length=200, verbose_name='경로')),
                ('ip', models.CharField(blank=True, default='', max_length=64, verbose_name='IP')),
                ('user_agent', models.CharField(blank=True, default='', max_length=300, verbose_name='User-Agent')),
                ('referer', models.CharField(blank=True, default='', max_length=300, verbose_name='Referer')),
                ('is_admin', models.BooleanField(default=False, verbose_name='관리자')),
                ('ts', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='시각')),
            ],
            options={
                'verbose_name': '방문 로그',
                'verbose_name_plural': '방문 로그',
                'ordering': ['-ts'],
            },
        ),
    ]
