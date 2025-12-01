"""
토스 로그인 API 연동 및 JWT 인증 유틸리티

멀티 앱 지원:
- app_id를 기반으로 TossApp 설정을 조회
- app_id가 없으면 'game_honey'를 기본값으로 사용 (하위 호환)
"""
import base64
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import jwt

User = get_user_model()

# 기본 앱 ID (하위 호환용)
DEFAULT_APP_ID = 'game_honey'


# ============================================
# TossApp 설정 조회
# ============================================

def get_toss_app(app_id: str = None):
    """
    app_id로 TossApp 설정 조회

    Args:
        app_id: 앱 ID (없으면 'game_honey')

    Returns:
        TossApp 객체

    Raises:
        ValueError: 앱을 찾을 수 없거나 비활성화된 경우
    """
    from common.models import TossApp

    if not app_id:
        app_id = DEFAULT_APP_ID

    try:
        app = TossApp.objects.get(app_id=app_id)
        if not app.is_active:
            raise ValueError(f"App '{app_id}' is not active")
        return app
    except TossApp.DoesNotExist:
        # 앱이 없고 game_honey인 경우 settings에서 폴백 (마이그레이션 전 호환)
        if app_id == DEFAULT_APP_ID:
            return None  # 레거시 모드로 처리
        raise ValueError(f"App '{app_id}' not found")


def _get_mtls_cert_for_app(app=None) -> Optional[Tuple[str, str]]:
    """
    앱별 mTLS 인증서 경로 가져오기

    Args:
        app: TossApp 객체 (None이면 settings에서 가져옴)

    Returns:
        (cert_path, key_path) 튜플 또는 None
    """
    if app and app.cert_path and app.key_path:
        return (app.cert_path, app.key_path)

    # 레거시: settings에서 가져오기
    cert_path = getattr(settings, 'TOSS_CERT_PATH', None)
    key_path = getattr(settings, 'TOSS_KEY_PATH', None)

    if not (cert_path and key_path):
        cert_path = getattr(settings, 'TOSS_MTLS_CERT_PATH', None)
        key_path = getattr(settings, 'TOSS_MTLS_KEY_PATH', None)

    if cert_path and key_path:
        return (cert_path, key_path)

    return None


# 레거시 함수 (하위 호환)
def _get_mtls_cert() -> Optional[Tuple[str, str]]:
    """
    mTLS 인증서 경로 가져오기 (레거시 - 하위 호환용)
    """
    return _get_mtls_cert_for_app(None)


# ============================================
# 토스 개인정보 복호화
# ============================================

def decrypt_toss_data(encrypted_text: str, app=None) -> str:
    """
    토스 API에서 받은 암호화된 개인정보를 복호화

    알고리즘: AES-256-GCM
    - 암호화된 데이터 앞 12바이트가 IV(Nonce)
    - 복호화 키와 AAD는 TossApp 또는 환경 변수에서 가져옴

    Args:
        encrypted_text: 암호화된 텍스트
        app: TossApp 객체 (None이면 settings에서 가져옴)
    """
    try:
        IV_LENGTH = 12

        # Base64 디코딩
        decoded = base64.b64decode(encrypted_text)

        # 앱별 설정 또는 레거시 settings
        if app and app.toss_decrypt_key:
            key_bytes = base64.b64decode(app.toss_decrypt_key)
            aad = (app.toss_decrypt_aad or 'TOSS').encode('utf-8')
        else:
            key_bytes = base64.b64decode(settings.TOSS_DECRYPT_KEY)
            aad = settings.TOSS_DECRYPT_AAD.encode('utf-8')

        # IV 추출
        iv = decoded[:IV_LENGTH]
        ciphertext = decoded[IV_LENGTH:]

        # 복호화
        aesgcm = AESGCM(key_bytes)
        plaintext = aesgcm.decrypt(iv, ciphertext, aad)

        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")
        raise ValueError(f"Failed to decrypt data: {str(e)}")


# ============================================
# 토스 API 호출
# ============================================

def get_toss_access_token(authorization_code: str, referrer: str, app=None) -> Dict:
    """
    인가 코드로 토스 AccessToken 발급

    Args:
        authorization_code: appLogin()에서 받은 인가 코드
        referrer: "DEFAULT" 또는 "SANDBOX"
        app: TossApp 객체 (None이면 settings 사용)

    Returns:
        {
            "accessToken": "...",
            "refreshToken": "...",
            "expiresIn": 3599,
            "tokenType": "Bearer",
            "scope": "user_ci user_name ..."
        }
    """
    url = f"{settings.TOSS_LOGIN_BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/generate-token"

    response = requests.post(
        url,
        json={
            "authorizationCode": authorization_code,
            "referrer": referrer
        },
        headers={"Content-Type": "application/json"},
        cert=_get_mtls_cert_for_app(app),
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('resultType') == 'SUCCESS':
            return data['success']
        else:
            error = data.get('error', {})
            raise ValueError(f"Toss API error: {error.get('errorCode')} - {error.get('reason')}")
    else:
        raise ValueError(f"Toss API request failed: {response.status_code} - {response.text}")


def refresh_toss_access_token(refresh_token: str, app=None) -> Dict:
    """
    RefreshToken으로 새 AccessToken 발급

    Args:
        refresh_token: 기존 RefreshToken
        app: TossApp 객체 (None이면 settings 사용)

    Returns:
        {
            "accessToken": "...",
            "refreshToken": "...",
            "expiresIn": 3599,
            "tokenType": "Bearer",
            "scope": "..."
        }
    """
    url = f"{settings.TOSS_LOGIN_BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/refresh-token"

    response = requests.post(
        url,
        json={"refreshToken": refresh_token},
        headers={"Content-Type": "application/json"},
        cert=_get_mtls_cert_for_app(app),
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('resultType') == 'SUCCESS':
            return data['success']
        else:
            error = data.get('error', {})
            raise ValueError(f"Toss API error: {error.get('errorCode')} - {error.get('reason')}")
    else:
        raise ValueError(f"Toss API request failed: {response.status_code} - {response.text}")


def get_toss_user_info(access_token: str, app=None) -> Dict:
    """
    AccessToken으로 토스 사용자 정보 조회

    Args:
        access_token: 토스 AccessToken
        app: TossApp 객체 (None이면 settings 사용)

    Returns:
        {
            "userKey": 443731104,
            "scope": "user_ci user_name ...",
            "agreedTerms": ["terms_tag1", "terms_tag2"],
            "name": "ENCRYPTED_VALUE",
            "phone": "ENCRYPTED_VALUE",
            "ci": "ENCRYPTED_VALUE",
            ...
        }
    """
    url = f"{settings.TOSS_LOGIN_BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/login-me"

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        cert=_get_mtls_cert_for_app(app),
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('resultType') == 'SUCCESS':
            return data['success']
        else:
            error = data.get('error', {})
            raise ValueError(f"Toss API error: {error.get('errorCode')} - {error.get('reason')}")
    else:
        raise ValueError(f"Toss API request failed: {response.status_code} - {response.text}")


# ============================================
# JWT 토큰 관리
# ============================================

def create_jwt_token(user_id: int, token_type: str = 'access') -> str:
    """
    JWT 토큰 생성

    Args:
        user_id: User ID
        token_type: 'access' 또는 'refresh'

    Returns:
        JWT 토큰 문자열
    """
    if token_type == 'access':
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    else:  # refresh
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        'user_id': user_id,
        'type': token_type,
        'exp': expire,
        'iat': datetime.utcnow()
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_jwt_token(token: str) -> Dict:
    """
    JWT 토큰 검증 및 디코딩

    Args:
        token: JWT 토큰 문자열

    Returns:
        디코딩된 payload

    Raises:
        jwt.ExpiredSignatureError: 토큰 만료
        jwt.InvalidTokenError: 유효하지 않은 토큰
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def get_user_from_token(token: str) -> Optional[User]:
    """
    JWT 토큰에서 사용자 가져오기

    Args:
        token: JWT 토큰 문자열

    Returns:
        User 객체 또는 None
    """
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get('user_id')

        if not user_id:
            return None

        user = User.objects.get(id=user_id)
        return user
    except (ValueError, User.DoesNotExist):
        return None


# ============================================
# 사용자 생성/조회
# ============================================

def get_or_create_user_from_toss(user_key: int, user_info: Dict, app=None) -> Tuple[User, bool]:
    """
    토스 userKey로 사용자 찾기 또는 생성

    Args:
        user_key: 토스 사용자 키
        user_info: 토스 사용자 정보 (암호화된 데이터 포함)
        app: TossApp 객체 (복호화에 사용)

    Returns:
        (User 객체, 생성 여부)
    """
    from api.models import UserProfile

    try:
        # 기존 사용자 찾기
        profile = UserProfile.objects.get(toss_user_key=user_key)
        user = profile.user
        created = False

        # 토스 토큰 업데이트 (필요시)
        # profile.toss_access_token = ...
        # profile.save()

    except UserProfile.DoesNotExist:
        # 새 사용자 생성 또는 기존 User에 Profile 재생성
        username = f"toss_{user_key}"

        # 이름 복호화 (있으면)
        display_name = username
        if user_info.get('name'):
            try:
                display_name = decrypt_toss_data(user_info['name'], app)
            except:
                pass

        # User가 이미 존재하는지 확인 (Profile만 삭제된 경우)
        try:
            user = User.objects.get(username=username)
            created = False
        except User.DoesNotExist:
            # 완전히 새로운 사용자 생성
            user = User.objects.create_user(
                username=username,
                first_name=display_name[:30]  # Django User 필드 길이 제한
            )
            created = True

        # UserProfile 생성 (없으면)
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'toss_user_key': user_key}
        )

    return user, created


def save_app_user_token(user, app, toss_access_token: str, toss_refresh_token: str):
    """
    앱별 사용자 토큰 저장

    Args:
        user: User 객체
        app: TossApp 객체
        toss_access_token: Toss Access Token
        toss_refresh_token: Toss Refresh Token
    """
    from common.models import AppUserToken

    if not app:
        # 레거시: UserProfile에 저장
        user.profile.toss_access_token = toss_access_token
        user.profile.toss_refresh_token = toss_refresh_token
        user.profile.save()
        return

    # 앱별 토큰 저장
    AppUserToken.objects.update_or_create(
        user=user,
        app=app,
        defaults={
            'toss_access_token': toss_access_token,
            'toss_refresh_token': toss_refresh_token,
        }
    )
