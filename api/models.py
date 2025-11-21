from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from PIL import Image


def validate_square_image(image):
    """정사각형 이미지인지 검증"""
    try:
        img = Image.open(image)
        width, height = img.size
        if width != height:
            raise ValidationError(
                f'이미지는 정사각형이어야 합니다. (현재: {width}x{height})'
            )
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError('올바른 이미지 파일이 아닙니다.')


class Game(models.Model):
    """게임 정보"""
    game_id = models.CharField(max_length=50, unique=True, verbose_name="게임 ID")  # 'maplestory'
    display_name = models.CharField(max_length=100, verbose_name="표시 이름")  # '메이플스토리'
    icon_url = models.URLField(blank=True, verbose_name="아이콘 URL (레거시)")
    icon_image = models.ImageField(
        upload_to='game_icons/',
        blank=True,
        null=True,
        validators=[validate_square_image],
        verbose_name="게임 아이콘 이미지"
    )
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "게임"
        verbose_name_plural = "게임 목록"
        ordering = ['display_name']

    def __str__(self):
        return self.display_name


class GameCategory(models.Model):
    """게임 카테고리 (공지사항, 업데이트, 이벤트 등)"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='categories', verbose_name="게임")
    name = models.CharField(max_length=50, verbose_name="카테고리명")  # '공지사항', '업데이트', '이벤트'
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "게임 카테고리"
        verbose_name_plural = "게임 카테고리 목록"
        unique_together = ('game', 'name')
        ordering = ['game', 'name']

    def __str__(self):
        return f"{self.game.display_name} - {self.name}"


class Subscription(models.Model):
    """사용자 게임 구독"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_subscriptions', verbose_name="사용자")
    game = models.ForeignKey(Game, on_delete=models.CASCADE, verbose_name="게임")
    category = models.CharField(max_length=50, verbose_name="카테고리")  # '공지사항', '업데이트', '이벤트'
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="구독일")

    class Meta:
        verbose_name = "게임 구독"
        verbose_name_plural = "게임 구독 목록"
        unique_together = ('user', 'game', 'category')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.game.display_name} ({self.category})"


class PushToken(models.Model):
    """푸시 알림 디바이스 토큰"""
    DEVICE_CHOICES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens', verbose_name="사용자")
    token = models.CharField(max_length=255, unique=True, verbose_name="FCM 토큰")
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, verbose_name="디바이스 타입")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "푸시 토큰"
        verbose_name_plural = "푸시 토큰 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.device_type}"


class UserProfile(models.Model):
    """사용자 프로필 확장 (Toss 인증용)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="사용자")
    toss_user_key = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name="토스 사용자 키")
    toss_access_token = models.TextField(blank=True, verbose_name="토스 액세스 토큰")
    toss_refresh_token = models.TextField(blank=True, verbose_name="토스 리프레시 토큰")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필 목록"

    def __str__(self):
        return self.user.username


class PremiumSubscription(models.Model):
    """프리미엄 구독 정보"""
    SUBSCRIPTION_TYPES = [
        ('free_ad', '광고 시청 무료 (7일)'),
        ('premium', '프리미엄 구독 (180일)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='premium_subscription', verbose_name="사용자")
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPES, verbose_name="구독 유형")
    expires_at = models.DateTimeField(verbose_name="만료일시")
    order_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="주문 ID")  # 인앱결제 주문 ID
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "프리미엄 구독"
        verbose_name_plural = "프리미엄 구독 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.get_subscription_type_display()} (만료: {self.expires_at})"

    @property
    def is_active(self):
        """현재 활성화된 구독인지 확인"""
        from django.utils import timezone
        return self.expires_at > timezone.now()
