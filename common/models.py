from django.db import models
from django.contrib.auth.models import User


class TossApp(models.Model):
    """
    Toss 앱 등록 정보

    각 Apps in Toss 앱별로 별도의 Toss API 설정을 관리합니다.
    Admin에서 새 앱을 등록하면 코드 수정 없이 앱 추가가 가능합니다.
    """
    app_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="앱 ID",
        help_text="영문 소문자와 언더스코어만 사용 (예: game_honey, paljalog)"
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name="앱 이름",
        help_text="사용자에게 표시되는 앱 이름 (예: 게임 하니, 팔자로그)"
    )

    # Toss API 설정
    toss_client_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Toss Client ID",
        help_text="Toss 개발자센터에서 발급받은 Client ID"
    )
    toss_decrypt_key = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Toss 복호화 키",
        help_text="Base64 인코딩된 AES-256-GCM 복호화 키"
    )
    toss_decrypt_aad = models.CharField(
        max_length=50,
        default='TOSS',
        verbose_name="Toss AAD",
        help_text="Additional Authenticated Data (기본값: TOSS)"
    )

    # mTLS 인증서 경로
    cert_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="인증서 경로",
        help_text="mTLS 인증서 파일 경로 (예: mtls/game_honey/cert.pem)"
    )
    key_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="키 경로",
        help_text="mTLS 키 파일 경로 (예: mtls/game_honey/key.pem)"
    )

    # Toss 연결 끊기 콜백 인증
    disconnect_callback_username = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="콜백 Username",
        help_text="Toss 연결 끊기 콜백 Basic Auth Username"
    )
    disconnect_callback_password = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="콜백 Password",
        help_text="Toss 연결 끊기 콜백 Basic Auth Password"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화",
        help_text="비활성화하면 해당 앱으로 로그인할 수 없습니다"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "Toss 앱"
        verbose_name_plural = "Toss 앱 목록"
        ordering = ['display_name']

    def __str__(self):
        return f"{self.display_name} ({self.app_id})"

    def get_mtls_cert(self):
        """mTLS 인증서 경로 튜플 반환"""
        if self.cert_path and self.key_path:
            return (self.cert_path, self.key_path)
        return None


class AppUserToken(models.Model):
    """
    앱별 사용자 토큰

    사용자가 여러 앱에 로그인할 수 있으므로, 앱별로 Toss 토큰을 저장합니다.
    같은 사용자라도 앱마다 별도의 토큰을 가집니다.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='app_tokens',
        verbose_name="사용자"
    )
    app = models.ForeignKey(
        TossApp,
        on_delete=models.CASCADE,
        related_name='user_tokens',
        verbose_name="앱"
    )
    toss_access_token = models.TextField(
        blank=True,
        verbose_name="Toss Access Token"
    )
    toss_refresh_token = models.TextField(
        blank=True,
        verbose_name="Toss Refresh Token"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "앱별 사용자 토큰"
        verbose_name_plural = "앱별 사용자 토큰 목록"
        unique_together = ('user', 'app')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.app.display_name}"
