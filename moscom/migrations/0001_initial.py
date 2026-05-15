from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_uuid', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='UUID')),
                ('device_id', models.IntegerField(blank=True, db_index=True, null=True, verbose_name='MOSCOM device.id')),
                ('device_name', models.CharField(blank=True, default='', max_length=200, verbose_name='장비명')),
                ('device_usim', models.CharField(blank=True, default='', max_length=64, verbose_name='USIM')),
                ('address_sido', models.CharField(blank=True, db_index=True, default='', max_length=50, verbose_name='시도')),
                ('address_gungu', models.CharField(blank=True, db_index=True, default='', max_length=50, verbose_name='군구')),
                ('address_dong', models.CharField(blank=True, db_index=True, default='', max_length=50, verbose_name='동')),
                ('address_detail', models.CharField(blank=True, default='', max_length=200, verbose_name='상세주소')),
                ('latitude', models.FloatField(default=0, verbose_name='위도')),
                ('longitude', models.FloatField(default=0, verbose_name='경도')),
                ('mode', models.IntegerField(default=0, verbose_name='모드')),
                ('on_time', models.CharField(blank=True, default='', max_length=50, verbose_name='가동 시간')),
                ('co2_on_time', models.CharField(blank=True, default='', max_length=50, verbose_name='CO2 가동 시간')),
                ('co2_period', models.IntegerField(default=0, verbose_name='CO2 주기')),
                ('current_mosquito_count', models.IntegerField(default=0, verbose_name='현재 포집량')),
                ('current_battery', models.IntegerField(default=0, verbose_name='배터리')),
                ('current_charge', models.IntegerField(default=0, verbose_name='충전')),
                ('current_fan', models.IntegerField(default=0, verbose_name='팬')),
                ('device_date', models.DateTimeField(blank=True, null=True, verbose_name='장비 시각')),
                ('updated_date', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='업데이트 시각')),
                ('created_date', models.DateTimeField(blank=True, null=True, verbose_name='생성 시각')),
                ('last_offline_alert_date', models.DateTimeField(blank=True, null=True, verbose_name='마지막 오프라인 알림')),
                ('last_battery_alert_date', models.DateTimeField(blank=True, null=True, verbose_name='마지막 배터리 알림')),
                ('last_collection_alert_date', models.DateTimeField(blank=True, null=True, verbose_name='마지막 포집 알림')),
                ('normal_min', models.IntegerField(default=0, verbose_name='정상 최소')),
                ('normal_max', models.IntegerField(default=49, verbose_name='정상 최대')),
                ('warning_min', models.IntegerField(default=50, verbose_name='경고 최소')),
                ('warning_max', models.IntegerField(default=99, verbose_name='경고 최대')),
                ('bad_min', models.IntegerField(default=100, verbose_name='위험 최소')),
                ('bad_max', models.IntegerField(default=10000, verbose_name='위험 최대')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성')),
                ('synced_at', models.DateTimeField(auto_now=True, verbose_name='마지막 동기화')),
            ],
            options={
                'verbose_name': 'MOSCOM 장비',
                'verbose_name_plural': 'MOSCOM 장비',
                'ordering': ['address_sido', 'address_gungu', 'address_dong', 'device_name'],
            },
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('moscom_id', models.BigIntegerField(db_index=True, unique=True, verbose_name='MOSCOM 원본 id')),
                ('device_uuid', models.CharField(db_index=True, max_length=64, verbose_name='장비 UUID')),
                ('mosquito_count', models.IntegerField(verbose_name='포집량')),
                ('reset', models.BooleanField(default=False, verbose_name='리셋')),
                ('battery', models.IntegerField(default=0, verbose_name='배터리')),
                ('charge', models.IntegerField(default=0, verbose_name='충전')),
                ('fan', models.IntegerField(default=0, verbose_name='팬')),
                ('created_date', models.DateTimeField(db_index=True, verbose_name='측정 시각')),
                ('synced_at', models.DateTimeField(auto_now_add=True, verbose_name='동기화 시각')),
                ('edited', models.BooleanField(db_index=True, default=False, verbose_name='수정됨')),
            ],
            options={
                'verbose_name': 'MOSCOM 포집 이벤트',
                'verbose_name_plural': 'MOSCOM 포집 이벤트',
                'ordering': ['-created_date'],
                'indexes': [
                    models.Index(fields=['device_uuid', '-created_date'], name='moscom_coll_device__cd6e6f_idx'),
                    models.Index(fields=['-created_date'], name='moscom_coll_created_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SyncState',
            fields=[
                ('id', models.SmallIntegerField(default=1, primary_key=True, serialize=False)),
                ('devices_synced_at', models.DateTimeField(blank=True, null=True, verbose_name='장비 마지막 동기화')),
                ('collections_synced_until', models.DateTimeField(blank=True, null=True, verbose_name='포집 마지막 가져온 시각')),
                ('last_run_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 실행')),
                ('last_status', models.CharField(blank=True, default='', max_length=20, verbose_name='마지막 상태')),
                ('last_error', models.TextField(blank=True, default='', verbose_name='마지막 오류')),
            ],
            options={
                'verbose_name': '동기화 상태',
                'verbose_name_plural': '동기화 상태',
            },
        ),
        migrations.CreateModel(
            name='EditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('table', models.CharField(db_index=True, max_length=50, verbose_name='테이블')),
                ('row_id', models.BigIntegerField(db_index=True, verbose_name='행 ID')),
                ('field', models.CharField(max_length=50, verbose_name='필드')),
                ('old_value', models.TextField(blank=True, default='', verbose_name='변경 전')),
                ('new_value', models.TextField(blank=True, default='', verbose_name='변경 후')),
                ('edited_by', models.CharField(blank=True, default='', max_length=50, verbose_name='수정자')),
                ('edited_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='수정 시각')),
            ],
            options={
                'verbose_name': 'MOSCOM 수정 이력',
                'verbose_name_plural': 'MOSCOM 수정 이력',
                'ordering': ['-edited_at'],
            },
        ),
    ]
