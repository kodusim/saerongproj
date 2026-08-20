from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0002_chat_ip_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('novel', '소설'), ('essay', '수필'), ('etc', '기타')], default='novel', max_length=16)),
                ('title', models.CharField(max_length=200)),
                ('author_name', models.CharField(default='익명', max_length=32)),
                ('author_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('body', models.TextField(blank=True, default='')),
                ('views', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
