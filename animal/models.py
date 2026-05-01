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
