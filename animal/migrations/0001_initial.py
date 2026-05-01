from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='GuildMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nickname', models.CharField(max_length=50, unique=True, verbose_name='닉네임')),
                ('power', models.BigIntegerField(default=0, verbose_name='전투력')),
                ('weapon', models.CharField(blank=True, default='', max_length=100, verbose_name='무기')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='정렬 순서')),
                ('active', models.BooleanField(default=True, verbose_name='활성')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '길드원',
                'verbose_name_plural': '길드원',
                'ordering': ['order', 'id'],
            },
        ),
    ]
