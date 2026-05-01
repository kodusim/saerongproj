from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0004_seed_collectibles'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipSlot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(choices=[('equip', '장비 내판'), ('mount', '탈것 내판'), ('special', '특수컬렉')], db_index=True, max_length=20, verbose_name='섹션')),
                ('name', models.CharField(max_length=100, verbose_name='슬롯명')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='정렬 순서')),
            ],
            options={
                'verbose_name': '장비 슬롯',
                'verbose_name_plural': '장비 슬롯',
                'ordering': ['section', 'order', 'id'],
                'unique_together': {('section', 'name')},
            },
        ),
        migrations.CreateModel(
            name='MemberEquip',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('none', '미소유'), ('owned_in', '소유 (내판O)'), ('owned_out', '소유 (내판X)'), ('passed', '내림')], default='none', max_length=20, verbose_name='상태')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='holders', to='animal.equipslot')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equips', to='animal.guildmember')),
            ],
            options={
                'verbose_name': '길드원 장비 내판',
                'verbose_name_plural': '길드원 장비 내판',
                'unique_together': {('member', 'slot')},
            },
        ),
    ]
