"""MOSCOM 데이터 로컬 저장 모델.

- Device: 장비 마스터 (MOSCOM /device/listAll 스냅샷)
- Collection: raw 포집 이벤트 (1행 = 1개 측정)
- SyncState: 동기화 진행 상태 (마지막 cursor)
- EditLog: 관리자 수정 이력
"""
from django.db import models


class Device(models.Model):
    """MOSCOM 장비. device_uuid가 자연 키. listAll에서 가져온 메타 + 최신 상태."""
    device_uuid = models.CharField('UUID', max_length=64, unique=True, db_index=True)
    device_id = models.IntegerField('MOSCOM device.id', null=True, blank=True, db_index=True)
    device_name = models.CharField('장비명', max_length=200, blank=True, default='')
    device_usim = models.CharField('USIM', max_length=64, blank=True, default='')

    address_sido = models.CharField('시도', max_length=50, blank=True, default='', db_index=True)
    address_gungu = models.CharField('군구', max_length=50, blank=True, default='', db_index=True)
    address_dong = models.CharField('동', max_length=50, blank=True, default='', db_index=True)
    address_detail = models.CharField('상세주소', max_length=200, blank=True, default='')

    latitude = models.FloatField('위도', default=0)
    longitude = models.FloatField('경도', default=0)

    mode = models.IntegerField('모드', default=0)
    on_time = models.CharField('가동 시간', max_length=50, blank=True, default='')
    co2_on_time = models.CharField('CO2 가동 시간', max_length=50, blank=True, default='')
    co2_period = models.IntegerField('CO2 주기', default=0)

    # 가장 최근 상태 (listAll 응답의 현재 값 — 표시용)
    current_mosquito_count = models.IntegerField('현재 포집량', default=0)
    current_battery = models.IntegerField('배터리', default=0)
    current_charge = models.IntegerField('충전', default=0)
    current_fan = models.IntegerField('팬', default=0)

    device_date = models.DateTimeField('장비 시각', null=True, blank=True)
    updated_date = models.DateTimeField('업데이트 시각', null=True, blank=True, db_index=True)
    created_date = models.DateTimeField('생성 시각', null=True, blank=True)

    last_offline_alert_date = models.DateTimeField('마지막 오프라인 알림', null=True, blank=True)
    last_battery_alert_date = models.DateTimeField('마지막 배터리 알림', null=True, blank=True)
    last_collection_alert_date = models.DateTimeField('마지막 포집 알림', null=True, blank=True)

    # 장비별 임계값 (deviceSetting)
    normal_min = models.IntegerField('정상 최소', default=0)
    normal_max = models.IntegerField('정상 최대', default=49)
    warning_min = models.IntegerField('경고 최소', default=50)
    warning_max = models.IntegerField('경고 최대', default=99)
    bad_min = models.IntegerField('위험 최소', default=100)
    bad_max = models.IntegerField('위험 최대', default=10000)

    # 로컬 메타
    is_active = models.BooleanField('활성', default=True)
    synced_at = models.DateTimeField('마지막 동기화', auto_now=True)

    # 날씨 (Open-Meteo 에서 가져와 캐싱, 1시간 주기 갱신)
    temperature = models.FloatField('기온(°C)', null=True, blank=True)
    humidity = models.FloatField('습도(%)', null=True, blank=True)
    precipitation = models.FloatField('강수량(mm)', null=True, blank=True)
    wind_speed = models.FloatField('풍속(m/s)', null=True, blank=True)
    weather_synced_at = models.DateTimeField('날씨 동기화', null=True, blank=True)

    # 권역 코드 (device_name prefix 에서 자동 추출 — 예: KH, GH서, BD, HY)
    region_code = models.CharField('권역 코드', max_length=20, blank=True, default='', db_index=True)

    # 2축 분류 (관리자 수동 지정 — 비어있으면 이름·주소 키워드로 자동 추정)
    # 지역: 농촌/구도심/도심/신도심 · 형태: 공원/주택가/수변부
    region_type = models.CharField('지역 분류', max_length=20, blank=True, default='')
    form_type = models.CharField('형태 분류', max_length=20, blank=True, default='')

    class Meta:
        ordering = ['address_sido', 'address_gungu', 'address_dong', 'device_name']
        verbose_name = 'MOSCOM 장비'
        verbose_name_plural = 'MOSCOM 장비'

    def __str__(self):
        return f'{self.device_name or self.device_uuid}'


class Collection(models.Model):
    """raw 포집 이벤트. MOSCOM의 /device/statisticsByDate aggregation=raw 응답 1건 = 1행."""
    # MOSCOM 원본 id — 중복 방지용 unique
    moscom_id = models.BigIntegerField('MOSCOM 원본 id', unique=True, db_index=True)
    device_uuid = models.CharField('장비 UUID', max_length=64, db_index=True)
    # device FK 는 일부러 안 만듦 — device_uuid 로 lazy join (Device 가 삭제돼도 Collection 보존)

    mosquito_count = models.IntegerField('포집량')
    reset = models.BooleanField('리셋', default=False)
    battery = models.IntegerField('배터리', default=0)
    charge = models.IntegerField('충전', default=0)
    fan = models.IntegerField('팬', default=0)

    created_date = models.DateTimeField('측정 시각', db_index=True)

    # 로컬 메타
    synced_at = models.DateTimeField('동기화 시각', auto_now_add=True)
    # 수정 표시 (관리자가 손댄 적 있는지)
    edited = models.BooleanField('수정됨', default=False, db_index=True)

    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['device_uuid', '-created_date']),
            models.Index(fields=['-created_date']),
        ]
        verbose_name = 'MOSCOM 포집 이벤트'
        verbose_name_plural = 'MOSCOM 포집 이벤트'

    def __str__(self):
        return f'{self.device_uuid} @ {self.created_date}: {self.mosquito_count}'


class SyncState(models.Model):
    """싱글톤. id=1만 사용. 마지막 동기화 cursor 저장."""
    id = models.SmallIntegerField(primary_key=True, default=1)
    devices_synced_at = models.DateTimeField('장비 마지막 동기화', null=True, blank=True)
    collections_synced_until = models.DateTimeField('포집 마지막 가져온 시각', null=True, blank=True)
    last_run_at = models.DateTimeField('마지막 실행', null=True, blank=True)
    last_status = models.CharField('마지막 상태', max_length=20, blank=True, default='')
    last_error = models.TextField('마지막 오류', blank=True, default='')

    class Meta:
        verbose_name = '동기화 상태'
        verbose_name_plural = '동기화 상태'

    def __str__(self):
        return f'last={self.last_run_at} status={self.last_status}'


class Region(models.Model):
    """권역 마스터. device_name prefix(code) → 사용자 친화적 이름(name) 매핑.
    sync 시 새 prefix 발견하면 자동 생성(name=code 기본값), 관리자가 name 수정.
    """
    code = models.CharField('코드', max_length=20, unique=True, db_index=True)
    name = models.CharField('표시명', max_length=80)
    # 종합현황 전국 참조 바 전용 표시명 (비면 name/code 사용)
    overview_name = models.CharField('종합현황 표시명', max_length=80, blank=True, default='')
    sort_order = models.IntegerField('정렬 순서', default=100)
    note = models.CharField('비고', max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'code']
        verbose_name = '권역'
        verbose_name_plural = '권역'

    def __str__(self):
        return f'{self.code} ({self.name})'


class EditLog(models.Model):
    """관리자 수정 이력. 어떤 모델/행/필드를 누가 언제 어떻게 바꿨는지."""
    table = models.CharField('테이블', max_length=50, db_index=True)
    row_id = models.BigIntegerField('행 ID', db_index=True)
    field = models.CharField('필드', max_length=50)
    old_value = models.TextField('변경 전', blank=True, default='')
    new_value = models.TextField('변경 후', blank=True, default='')
    edited_by = models.CharField('수정자', max_length=50, blank=True, default='')
    edited_at = models.DateTimeField('수정 시각', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-edited_at']
        verbose_name = 'MOSCOM 수정 이력'
        verbose_name_plural = 'MOSCOM 수정 이력'

    def __str__(self):
        return f'{self.table}#{self.row_id}.{self.field}: {self.old_value!r}→{self.new_value!r}'
