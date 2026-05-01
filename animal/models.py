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
