from django.db import models


class GuildMember(models.Model):
    """길드원. 연번은 order 필드 기준으로 1부터 자동 부여."""
    nickname = models.CharField('닉네임', max_length=50, unique=True)
    power = models.BigIntegerField('전투력', default=0)
    weapon = models.CharField('무기', max_length=100, blank=True, default='')
    order = models.PositiveIntegerField('정렬 순서', default=0, db_index=True)
    active = models.BooleanField('활성', default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = '길드원'
        verbose_name_plural = '길드원'

    def __str__(self):
        return f'{self.nickname} (#{self.order})'


class CollectibleItem(models.Model):
    CATEGORY_CHOICES = [
        ('accessory', '장신구'),
        ('weapon', '무기'),
        ('cloth', '천 방어구'),
        ('leather', '가죽 방어구'),
        ('plate', '판금 방어구'),
        ('cape', '망토'),
    ]
    category = models.CharField('카테고리', max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    name = models.CharField('아이템명', max_length=100)
    order = models.PositiveIntegerField('정렬 순서', default=0, db_index=True)

    class Meta:
        ordering = ['category', 'order', 'id']
        unique_together = [('category', 'name')]
        verbose_name = '컬렉용 아이템'
        verbose_name_plural = '컬렉용 아이템'

    def __str__(self):
        return f'[{self.get_category_display()}] {self.name}'


class MemberCollectible(models.Model):
    member = models.ForeignKey(GuildMember, on_delete=models.CASCADE, related_name='collectibles')
    item = models.ForeignKey(CollectibleItem, on_delete=models.CASCADE, related_name='holders')
    owned = models.BooleanField('보유', default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('member', 'item')]
        verbose_name = '길드원 컬렉 보유'
        verbose_name_plural = '길드원 컬렉 보유'

    def __str__(self):
        return f'{self.member.nickname} - {self.item.name}: {"O" if self.owned else "X"}'


class EquipSlot(models.Model):
    SECTION_CHOICES = [
        ('equip', '장비 내판'),
        ('mount', '탈것 내판'),
        ('special', '특수컬렉'),
    ]
    section = models.CharField('섹션', max_length=20, choices=SECTION_CHOICES, db_index=True)
    name = models.CharField('슬롯명', max_length=100)
    order = models.PositiveIntegerField('정렬 순서', default=0, db_index=True)

    class Meta:
        ordering = ['section', 'order', 'id']
        unique_together = [('section', 'name')]
        verbose_name = '장비 슬롯'
        verbose_name_plural = '장비 슬롯'

    def __str__(self):
        return f'[{self.get_section_display()}] {self.name}'


class MemberEquip(models.Model):
    STATUS_CHOICES = [
        ('none', '미소유'),
        ('owned_in', '소유 (내판O)'),
        ('owned_out', '소유 (내판X)'),
        ('passed', '내림'),
    ]
    member = models.ForeignKey(GuildMember, on_delete=models.CASCADE, related_name='equips')
    slot = models.ForeignKey(EquipSlot, on_delete=models.CASCADE, related_name='holders')
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default='none')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('member', 'slot')]
        verbose_name = '길드원 장비 내판'
        verbose_name_plural = '길드원 장비 내판'

    def __str__(self):
        return f'{self.member.nickname} - {self.slot.name}: {self.get_status_display()}'


class Boss(models.Model):
    """보스 마스터. 이름 → 기본 점수."""
    name = models.CharField('보스명', max_length=50, unique=True)
    score = models.IntegerField('기본 점수', default=1)
    order = models.PositiveIntegerField('정렬', default=0, db_index=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = '보스'
        verbose_name_plural = '보스'

    def __str__(self):
        return f'{self.name} ({self.score}점)'


class BossWeek(models.Model):
    """주차. 이름은 관리자가 직접 입력. 길이는 가변."""
    name = models.CharField('주차명', max_length=50, unique=True)
    start_date = models.DateField('시작일')
    is_current = models.BooleanField('현재 주차', default=False, db_index=True)
    closed_at = models.DateTimeField('분배 종료', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-id']
        verbose_name = '주차'
        verbose_name_plural = '주차'

    def __str__(self):
        return self.name


class BossClear(models.Model):
    """보스 토벌 1건. 항상 어떤 주차에 소속됨."""
    week = models.ForeignKey(BossWeek, on_delete=models.CASCADE, related_name='clears')
    date = models.DateField('날짜')
    time = models.TimeField('시간')
    boss_name_raw = models.CharField('입력 보스명', max_length=80)  # "베나투스1" 등 원본
    boss = models.ForeignKey(Boss, on_delete=models.SET_NULL, null=True, blank=True, related_name='clears')
    score_override = models.IntegerField('점수 보정', null=True, blank=True)
    note = models.CharField('메모', max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-time']
        unique_together = [('week', 'date', 'time', 'boss_name_raw')]
        verbose_name = '보스 토벌'
        verbose_name_plural = '보스 토벌'

    @property
    def effective_score(self):
        if self.score_override is not None:
            return self.score_override
        return self.boss.score if self.boss else 0

    def __str__(self):
        return f'{self.date} {self.time} {self.boss_name_raw}'


class BossClearParticipant(models.Model):
    clear = models.ForeignKey(BossClear, on_delete=models.CASCADE, related_name='participants')
    member = models.ForeignKey(GuildMember, on_delete=models.CASCADE, related_name='boss_clears')

    class Meta:
        unique_together = [('clear', 'member')]
        verbose_name = '토벌 참여자'
        verbose_name_plural = '토벌 참여자'

    def __str__(self):
        return f'{self.clear} - {self.member.nickname}'


class VisitLog(models.Model):
    """/animal/ 페이지 방문 로그. 7일 후 자동 삭제."""
    path = models.CharField('경로', max_length=200, db_index=True)
    ip = models.CharField('IP', max_length=64, blank=True, default='')
    user_agent = models.CharField('User-Agent', max_length=300, blank=True, default='')
    referer = models.CharField('Referer', max_length=300, blank=True, default='')
    is_admin = models.BooleanField('관리자', default=False)
    ts = models.DateTimeField('시각', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-ts']
        verbose_name = '방문 로그'
        verbose_name_plural = '방문 로그'

    def __str__(self):
        return f'{self.ts} {self.path} {self.ip}'
