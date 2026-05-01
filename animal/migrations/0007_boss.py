from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('animal', '0006_seed_equip_slots'),
    ]

    operations = [
        migrations.CreateModel(
            name='Boss',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='보스명')),
                ('score', models.IntegerField(default=1, verbose_name='기본 점수')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='정렬')),
            ],
            options={
                'verbose_name': '보스',
                'verbose_name_plural': '보스',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='BossWeek',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='주차명')),
                ('start_date', models.DateField(verbose_name='시작일')),
                ('is_current', models.BooleanField(db_index=True, default=False, verbose_name='현재 주차')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='분배 종료')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': '주차',
                'verbose_name_plural': '주차',
                'ordering': ['-start_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='BossClear',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='날짜')),
                ('time', models.TimeField(verbose_name='시간')),
                ('boss_name_raw', models.CharField(max_length=80, verbose_name='입력 보스명')),
                ('score_override', models.IntegerField(blank=True, null=True, verbose_name='점수 보정')),
                ('note', models.CharField(blank=True, default='', max_length=200, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('boss', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clears', to='animal.boss')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clears', to='animal.bossweek')),
            ],
            options={
                'verbose_name': '보스 토벌',
                'verbose_name_plural': '보스 토벌',
                'ordering': ['-date', '-time'],
                'unique_together': {('week', 'date', 'time', 'boss_name_raw')},
            },
        ),
        migrations.CreateModel(
            name='BossClearParticipant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clear', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='animal.bossclear')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='boss_clears', to='animal.guildmember')),
            ],
            options={
                'verbose_name': '토벌 참여자',
                'verbose_name_plural': '토벌 참여자',
                'unique_together': {('clear', 'member')},
            },
        ),
    ]
