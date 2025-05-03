from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import random

class FortuneType(models.Model):
    """운세 유형 모델 (일일, 주간, 월간, 사주, 타로, 별자리, 띠별 등)"""
    name = models.CharField(_("유형명"), max_length=50)
    slug = models.SlugField(_("슬러그"), unique=True, help_text="URL에 사용될 이름")
    description = models.TextField(_("설명"), blank=True)
    image = models.ImageField(_("이미지"), upload_to="misc/fortune/types/", blank=True, null=True)
    order = models.PositiveIntegerField(_("순서"), default=0)
    is_active = models.BooleanField(_("활성화"), default=True)
    is_ready = models.BooleanField(_("서비스 준비됨"), default=False)

    class Meta:
        ordering = ['order']
        verbose_name = _("운세 유형")
        verbose_name_plural = _("운세 유형 관리")

    def __str__(self):
        return self.name

class FortuneCategory(models.Model):
    """운세 카테고리 (종합운, 금전운, 애정운, 건강운 등)"""
    name = models.CharField(_("카테고리명"), max_length=50)
    description = models.TextField(_("설명"), blank=True)
    order = models.PositiveIntegerField(_("순서"), default=0)
    is_active = models.BooleanField(_("활성화"), default=True)

    class Meta:
        ordering = ['order']
        verbose_name = _("운세 카테고리")
        verbose_name_plural = _("운세 카테고리 관리")

    def __str__(self):
        return self.name

class FortuneContent(models.Model):
    """운세 내용 모델"""
    fortune_type = models.ForeignKey(FortuneType, verbose_name=_("운세 유형"), on_delete=models.CASCADE, related_name="contents")
    category = models.ForeignKey(FortuneCategory, verbose_name=_("카테고리"), on_delete=models.CASCADE, related_name="contents")
    level = models.IntegerField(_("운세 등급"), default=3, help_text="1(매우 나쁨) ~ 5(매우 좋음)")
    content = models.TextField(_("내용"))
    advice = models.TextField(_("조언"), blank=True)
    is_active = models.BooleanField(_("활성화"), default=True)
    
    class Meta:
        verbose_name = _("운세 내용")
        verbose_name_plural = _("운세 내용 관리")
    
    def __str__(self):
        return f"{self.fortune_type.name} - {self.category.name} (Level {self.level})"

class UserFortune(models.Model):
    """사용자별 운세 결과 저장 모델"""
    user = models.ForeignKey('accounts.User', verbose_name=_("사용자"), on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(_("세션 ID"), max_length=100, blank=True)  # 비로그인 사용자용
    fortune_type = models.ForeignKey(FortuneType, verbose_name=_("운세 유형"), on_delete=models.CASCADE)
    date = models.DateField(_("날짜"))
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        unique_together = [['user', 'fortune_type', 'date'], ['session_id', 'fortune_type', 'date']]
        verbose_name = _("사용자 운세 결과")
        verbose_name_plural = _("사용자 운세 결과 관리")

    def __str__(self):
        user_info = self.user.username if self.user else self.session_id[:10]
        return f"{user_info} - {self.fortune_type.name} ({self.date})"

class UserFortuneResult(models.Model):
    """사용자 운세 결과의 세부 내용"""
    user_fortune = models.ForeignKey(UserFortune, verbose_name=_("사용자 운세"), on_delete=models.CASCADE, related_name="results")
    category = models.ForeignKey(FortuneCategory, verbose_name=_("카테고리"), on_delete=models.CASCADE)
    content = models.ForeignKey(FortuneContent, verbose_name=_("운세 내용"), on_delete=models.CASCADE)
    
    class Meta:
        unique_together = [['user_fortune', 'category']]
        verbose_name = _("사용자 운세 세부 결과")
        verbose_name_plural = _("사용자 운세 세부 결과 관리")
    
    def __str__(self):
        return f"{self.user_fortune} - {self.category.name}"