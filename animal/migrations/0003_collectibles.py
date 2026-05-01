from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0002_seed_members'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectibleItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('accessory', '장신구'), ('weapon', '무기'), ('cloth', '천 방어구'), ('leather', '가죽 방어구'), ('plate', '판금 방어구'), ('cape', '망토')], db_index=True, max_length=20, verbose_name='카테고리')),
                ('name', models.CharField(max_length=100, verbose_name='아이템명')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='정렬 순서')),
            ],
            options={
                'verbose_name': '컬렉용 아이템',
                'verbose_name_plural': '컬렉용 아이템',
                'ordering': ['category', 'order', 'id'],
                'unique_together': {('category', 'name')},
            },
        ),
        migrations.CreateModel(
            name='MemberCollectible',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owned', models.BooleanField(default=False, verbose_name='보유')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='holders', to='animal.collectibleitem')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collectibles', to='animal.guildmember')),
            ],
            options={
                'verbose_name': '길드원 컬렉 보유',
                'verbose_name_plural': '길드원 컬렉 보유',
                'unique_together': {('member', 'item')},
            },
        ),
    ]
