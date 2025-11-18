"""
토스 로그인 API 연동 및 JWT 인증 유틸리티
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


# ============================================
# mTLS 인증서 헬퍼
# ============================================

def _get_mtls_cert() -> Optional[Tuple[str, str]]:
    """
    mTLS 인증서 경로 가져오기

    Returns:
        (cert_path, key_path) 튜플 또는 None
    """
    if hasattr(settings, 'TOSS_MTLS_CERT_PATH') and hasattr(settings, 'TOSS_MTLS_KEY_PATH'):
        cert_path = settings.TOSS_MTLS_CERT_PATH
        key_path = settings.TOSS_MTLS_KEY_PATH
        if cert_path and key_path:
            return (cert_path, key_path)
    return None


# ============================================
# 토스 개인정보 복호화
# ============================================

def decrypt_toss_data(encrypted_text: str) -> str:
    """
    토스 API에서 받은 암호화된 개인정보를 복호화

    알고리즘: AES-256-GCM
    - 암호화된 데이터 앞 12바이트가 IV(Nonce)
    - 복호화 키와 AAD는 환경 변수에서 가져옴
    """
    try:
        IV_LENGTH = 12

        # Base64 디코딩
        decoded = base64.b64decode(encrypted_text)
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

def get_toss_access_token(authorization_code: str, referrer: str) -> Dict:
    """
    인가 코드로 토스 AccessToken 발급

    Args:
        authorization_code: appLogin()에서 받은 인가 코드
        referrer: "DEFAULT" 또는 "SANDBOX"

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
        cert=_get_mtls_cert(),
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


def refresh_toss_access_token(refresh_token: str) -> Dict:
    """
    RefreshToken으로 새 AccessToken 발급

    Args:
        refresh_token: 기존 RefreshToken

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
        cert=_get_mtls_cert(),
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


def get_toss_user_info(access_token: str) -> Dict:
    """
    AccessToken으로 토스 사용자 정보 조회

    Args:
        access_token: 토스 AccessToken

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
        cert=_get_mtls_cert(),
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

def get_or_create_user_from_toss(user_key: int, user_info: Dict) -> Tuple[User, bool]:
    """
    토스 userKey로 사용자 찾기 또는 생성

    Args:
        user_key: 토스 사용자 키
        user_info: 토스 사용자 정보 (암호화된 데이터 포함)

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
        # 새 사용자 생성
        username = f"toss_{user_key}"

        # 이름 복호화 (있으면)
        display_name = username
        if user_info.get('name'):
            try:
                display_name = decrypt_toss_data(user_info['name'])
            except:
                pass

        user = User.objects.create_user(
            username=username,
            first_name=display_name[:30]  # Django User 필드 길이 제한
        )

        # UserProfile 생성
        UserProfile.objects.create(
            user=user,
            toss_user_key=user_key
        )

        created = True

    return user, created
