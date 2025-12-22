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


# ============================================
# 냉장고요리사 (Refrigerator Chef) 모델
# ============================================

class CarrotBalance(models.Model):
    """당근 잔액 (냉장고요리사용)"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='carrot_balance',
        verbose_name="사용자"
    )
    balance = models.IntegerField(default=0, verbose_name="당근 잔액")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "당근 잔액"
        verbose_name_plural = "당근 잔액 목록"

    def __str__(self):
        return f"{self.user.username} - {self.balance}개"

    def add_carrots(self, amount: int, transaction_type: str, order_id: str = None):
        """당근 추가 (광고 보상, 구매 등)"""
        self.balance += amount
        self.save()
        CarrotTransaction.objects.create(
            user=self.user,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            order_id=order_id
        )
        return self.balance

    def use_carrots(self, amount: int, transaction_type: str) -> bool:
        """당근 사용 (레시피 추천 등). 성공 시 True, 잔액 부족 시 False"""
        if self.balance < amount:
            return False
        self.balance -= amount
        self.save()
        CarrotTransaction.objects.create(
            user=self.user,
            transaction_type=transaction_type,
            amount=-amount,
            balance_after=self.balance
        )
        return True


class CarrotTransaction(models.Model):
    """당근 거래 내역"""
    TRANSACTION_TYPES = [
        ('welcome_bonus', '첫 로그인 보너스'),
        ('ad_reward', '광고 시청 보상'),
        ('recipe_recommend', '요리 추천'),
        ('recipe_another', '다른 요리 추천'),
        ('purchase_100', '당근 100개 구매'),
        ('purchase_1000', '당근 1000개 구매'),
        ('purchase_5000', '당근 5000개 구매'),
        ('purchase_10000', '당근 10000개 구매'),
        ('admin_grant', '관리자 지급'),
        ('admin_deduct', '관리자 차감'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='carrot_transactions',
        verbose_name="사용자"
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
        verbose_name="거래 유형"
    )
    amount = models.IntegerField(verbose_name="변동량")  # +면 획득, -면 사용
    balance_after = models.IntegerField(verbose_name="거래 후 잔액")
    order_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="주문 ID"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="거래일시")

    class Meta:
        verbose_name = "당근 거래 내역"
        verbose_name_plural = "당근 거래 내역 목록"
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.user.username} - {self.get_transaction_type_display()} ({sign}{self.amount})"


class SavedRecipe(models.Model):
    """저장된 레시피 (냉장고요리사용)"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_recipes',
        verbose_name="사용자"
    )
    recipe_id = models.CharField(max_length=100, verbose_name="레시피 ID")  # 프론트에서 생성한 UUID
    name = models.CharField(max_length=100, verbose_name="요리명")
    description = models.CharField(max_length=200, verbose_name="설명")
    difficulty = models.CharField(max_length=20, verbose_name="난이도")
    time = models.IntegerField(verbose_name="조리시간(분)")
    servings = models.CharField(max_length=20, verbose_name="인분")
    # JSON 필드로 복잡한 데이터 저장
    ingredients = models.JSONField(default=list, verbose_name="재료 목록")  # [{name, amount}, ...]
    steps = models.JSONField(default=list, verbose_name="조리 단계")  # [{step, description}, ...]
    tips = models.JSONField(default=list, verbose_name="요리 팁")  # [string, ...]
    used_ingredients = models.JSONField(default=list, verbose_name="사용 재료")  # [string, ...]
    additional_ingredients = models.JSONField(default=list, verbose_name="추가 재료")  # [string, ...]
    saved_at = models.DateTimeField(auto_now_add=True, verbose_name="저장일시")

    class Meta:
        verbose_name = "저장된 레시피"
        verbose_name_plural = "저장된 레시피 목록"
        unique_together = ('user', 'recipe_id')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"


# ============================================
# 이슈모아 (IssueMoa) 모델
# ============================================

class IssueCategory(models.Model):
    """이슈 카테고리"""
    category_id = models.CharField(max_length=50, unique=True, verbose_name="카테고리 ID")  # 'entertainment', 'game', 'economy'
    name = models.CharField(max_length=50, verbose_name="카테고리명")  # '연예', '게임', '경제'
    icon = models.CharField(max_length=10, default='📰', verbose_name="아이콘")  # 이모지
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    class Meta:
        verbose_name = "이슈 카테고리"
        verbose_name_plural = "이슈 카테고리 목록"
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class Issue(models.Model):
    """이슈 게시글"""
    category = models.ForeignKey(
        IssueCategory,
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name="카테고리"
    )
    title = models.CharField(max_length=200, verbose_name="제목")
    content = models.TextField(verbose_name="내용")  # Summernote HTML 저장
    preview = models.CharField(max_length=100, blank=True, verbose_name="미리보기")  # 자동 생성 가능
    view_count = models.IntegerField(default=0, verbose_name="조회수")
    weekly_view_count = models.IntegerField(default=0, verbose_name="주간 조회수")  # 인기순 정렬용
    is_published = models.BooleanField(default=True, verbose_name="공개")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "이슈"
        verbose_name_plural = "이슈 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category.name}] {self.title}"

    def save(self, *args, **kwargs):
        # 미리보기 자동 생성 (HTML 태그 제거 후 100자)
        if not self.preview and self.content:
            import re
            clean_text = re.sub(r'<[^>]+>', '', self.content)
            self.preview = clean_text[:100].strip()
        super().save(*args, **kwargs)

    def increment_view(self):
        """조회수 증가"""
        self.view_count += 1
        self.weekly_view_count += 1
        self.save(update_fields=['view_count', 'weekly_view_count'])
