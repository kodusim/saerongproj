# Django Backend API 개발 가이드

## 개요
Game Honey 앱의 백엔드 API를 Django로 구현하기 위한 명세서입니다.

---

## 필요한 API 엔드포인트

### 1. 인증 API

#### 1.1 토스 로그인 (Authorization Code 교환)
```
POST /api/auth/login
```

**Request Body:**
```json
{
  "authorizationCode": "string",
  "referrer": "string"
}
```

**Response:**
```json
{
  "accessToken": "string",
  "refreshToken": "string"
}
```

**구현 해야 할 것:**
- Toss API에 mTLS 요청하여 `authorizationCode`를 `accessToken`으로 교환
- `accessToken`을 DB에 저장 (또는 Redis)
- 사용자 정보를 조회하여 User 모델에 저장/업데이트

---

#### 1.2 사용자 정보 조회
```
GET /api/auth/me
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "userKey": 123456,
  "name": "홍길동",
  "email": "user@example.com"
}
```

**구현 해야 할 것:**
- 요청 헤더의 `accessToken` 검증
- Toss API에서 사용자 정보 조회
- 복호화 키를 사용하여 암호화된 정보 복호화
- `userKey` 반환

---

#### 1.3 토큰 갱신
```
POST /api/auth/refresh
```

**Request Body:**
```json
{
  "refreshToken": "string"
}
```

**Response:**
```json
{
  "accessToken": "string",
  "refreshToken": "string"
}
```

---

#### 1.4 로그아웃
```
POST /api/auth/logout
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "success": true
}
```

**구현 해야 할 것:**
- Toss API에 로그아웃 요청
- DB에서 토큰 삭제

---

### 2. 게임 API

#### 2.1 게임 목록 조회
```
GET /api/games/
```

**Response:**
```json
[
  {
    "id": "maplestory",
    "name": "maplestory",
    "displayName": "메이플스토리",
    "icon": "https://...",
    "categories": ["공지사항", "업데이트", "이벤트"]
  }
]
```

**구현 해야 할 것:**
- DB에서 활성화된 게임 목록 조회
- 각 게임의 카테고리 정보 포함

---

#### 2.2 게임 데이터 조회 (기존 API 유지)
```
GET /api/{gameId}/
예: GET /api/maplestory/
```

**Response:** (현재와 동일)
```json
{
  "subcategory": "메이플스토리",
  "category": "게임",
  "data": {
    "공지사항": [
      {
        "title": "제목",
        "url": "https://...",
        "date": "2024-01-01",
        "collected_at": "2024-01-01T12:00:00Z"
      }
    ],
    "업데이트": [...],
    "이벤트": [...]
  }
}
```

---

### 3. 구독 API

#### 3.1 내 구독 목록 조회
```
GET /api/subscriptions/
Authorization: Bearer {accessToken}
```

**Response:**
```json
[
  {
    "id": 1,
    "game_id": "maplestory",
    "category": "공지사항",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "id": 2,
    "game_id": "maplestory",
    "category": "업데이트",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

**구현 해야 할 것:**
- 현재 로그인한 사용자의 구독 목록 반환

---

#### 3.2 구독 추가
```
POST /api/subscriptions/
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "game_id": "maplestory",
  "category": "공지사항"
}
```

**Response:**
```json
{
  "id": 1,
  "game_id": "maplestory",
  "category": "공지사항",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**구현 해야 할 것:**
- 중복 구독 방지 (unique constraint)
- 사용자 ID + game_id + category로 구독 생성

---

#### 3.3 구독 취소
```
DELETE /api/subscriptions/{id}/
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "success": true
}
```

**구현 해야 할 것:**
- 본인의 구독만 삭제할 수 있도록 권한 확인

---

### 4. 알림 API

#### 4.1 알림 피드 조회
```
GET /api/notifications/
Authorization: Bearer {accessToken}
```

**Response:**
```json
[
  {
    "game": "메이플스토리",
    "game_id": "maplestory",
    "category": "공지사항",
    "title": "1월 업데이트 안내",
    "url": "https://...",
    "date": "2024-01-01",
    "collected_at": "2024-01-01T12:00:00Z"
  }
]
```

**구현 해야 할 것:**
- 현재 사용자가 구독한 게임+카테고리의 최신 소식만 반환
- 최신순 정렬
- 페이지네이션 (선택)

---

#### 4.2 푸시 토큰 등록
```
POST /api/push-tokens/
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "token": "fcm_device_token_here"
}
```

**Response:**
```json
{
  "success": true
}
```

**구현 해야 할 것:**
- 사용자별 디바이스 토큰 저장
- 같은 토큰이 이미 있으면 업데이트

---

## Django 모델 예시

### User 모델 (Django 기본 User 확장)
```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    toss_user_key = models.BigIntegerField(unique=True, null=True, blank=True)
    # 다른 필요한 필드 추가
```

### Game 모델
```python
class Game(models.Model):
    game_id = models.CharField(max_length=50, unique=True)  # 'maplestory'
    display_name = models.CharField(max_length=100)  # '메이플스토리'
    icon_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### GameCategory 모델
```python
class GameCategory(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=50)  # '공지사항', '업데이트', '이벤트'

    class Meta:
        unique_together = ('game', 'name')
```

### Subscription 모델
```python
class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    category = models.CharField(max_length=50)  # '공지사항', '업데이트', '이벤트'
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'game', 'category')
```

### PushToken 모델
```python
class PushToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=[('ios', 'iOS'), ('android', 'Android')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 토스 인증 구현 가이드

### 1. mTLS 클라이언트 설정

```python
import requests
from pathlib import Path

class TossAPIClient:
    def __init__(self):
        self.cert_path = Path(__file__).parent / 'mtls' / 'public.crt'
        self.key_path = Path(__file__).parent / 'mtls' / 'private.key'
        self.base_url = 'https://toss-auth-api.com'  # 실제 Toss API URL로 변경

    def post(self, endpoint, data=None, headers=None):
        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url,
            json=data,
            headers=headers,
            cert=(str(self.cert_path), str(self.key_path)),
            verify=True
        )
        return response.json()

    def get(self, endpoint, headers=None):
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=headers,
            cert=(str(self.cert_path), str(self.key_path)),
            verify=True
        )
        return response.json()
```

### 2. 사용자 정보 복호화

```python
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

def decrypt_user_info(encrypted_data, decryption_key_base64, aad):
    """
    Toss에서 받은 암호화된 사용자 정보 복호화
    """
    # Base64 디코딩
    key = base64.b64decode(decryption_key_base64)
    encrypted_bytes = base64.b64decode(encrypted_data)

    # AESGCM 복호화
    aesgcm = AESGCM(key)

    # nonce는 암호화된 데이터의 처음 12바이트
    nonce = encrypted_bytes[:12]
    ciphertext = encrypted_bytes[12:]

    # 복호화
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad.encode())

    return plaintext.decode('utf-8')
```

### 3. 환경 변수 설정 (.env)

```
# Toss 인증
TOSS_AUTH_API_BASE_URL=https://...
TOSS_DECRYPTION_KEY=zVIViRMJ4SOi+bdnKtP7n6/IAyxNGmltZeG3jtEXn6w=
TOSS_AAD=TOSS

# mTLS 인증서 경로
MTLS_CERT_PATH=mtls/public.crt
MTLS_KEY_PATH=mtls/private.key
```

---

## 푸시 알림 구현 가이드

### 1. Firebase Cloud Messaging (FCM) 설정

1. Firebase 콘솔에서 프로젝트 생성
2. 서비스 계정 키 JSON 파일 다운로드
3. Django settings.py에 경로 설정

```python
# settings.py
FIREBASE_CREDENTIALS_PATH = BASE_DIR / 'firebase-adminsdk.json'
```

### 2. FCM 푸시 전송 함수

```python
import firebase_admin
from firebase_admin import credentials, messaging

# Firebase 초기화
cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)

def send_push_notification(tokens, title, body, data=None):
    """
    여러 디바이스에 푸시 알림 전송

    Args:
        tokens: List[str] - FCM 디바이스 토큰 리스트
        title: str - 알림 제목
        body: str - 알림 내용
        data: dict - 추가 데이터 (선택)
    """
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    response = messaging.send_multicast(message)
    print(f'Successfully sent {response.success_count} messages')

    return response
```

### 3. 크롤링 후 푸시 발송 로직

```python
from apps.notifications.models import Subscription, PushToken
from apps.games.models import GameData  # 크롤링 데이터 모델

def send_notifications_for_new_data(game_id, category, new_items):
    """
    새로운 게임 데이터가 수집되면 구독자들에게 푸시 발송

    Args:
        game_id: str - 게임 ID ('maplestory')
        category: str - 카테고리 ('공지사항', '업데이트', '이벤트')
        new_items: List[dict] - 새로 수집된 데이터
    """
    # 해당 게임+카테고리를 구독한 사용자 조회
    subscriptions = Subscription.objects.filter(
        game__game_id=game_id,
        category=category
    ).select_related('user')

    # 사용자들의 푸시 토큰 조회
    user_ids = [sub.user.id for sub in subscriptions]
    tokens = PushToken.objects.filter(
        user_id__in=user_ids
    ).values_list('token', flat=True)

    if not tokens:
        return

    # 푸시 알림 내용 생성
    title = f"{game_id} {category}"
    body = new_items[0]['title']  # 첫 번째 아이템의 제목

    # 푸시 발송
    send_push_notification(
        tokens=list(tokens),
        title=title,
        body=body,
        data={
            'game_id': game_id,
            'category': category,
            'url': new_items[0]['url']
        }
    )
```

### 4. 크롤링 스케줄러 예시

```python
# Celery Beat 스케줄러 사용 예시
from celery import shared_task
from .crawlers import crawl_maplestory_data
from .utils import send_notifications_for_new_data

@shared_task
def crawl_and_notify_maplestory():
    """
    메이플스토리 데이터를 크롤링하고 새 데이터가 있으면 푸시 발송
    """
    # 크롤링 실행
    new_data = crawl_maplestory_data()

    # 카테고리별로 새 데이터 확인
    for category, items in new_data.items():
        if items:  # 새 데이터가 있으면
            send_notifications_for_new_data(
                game_id='maplestory',
                category=category,
                new_items=items
            )
```

---

## 체크리스트

### Django 백엔드 개발
- [ ] User 모델 확장 (toss_user_key 추가)
- [ ] Game, GameCategory, Subscription, PushToken 모델 생성
- [ ] Toss mTLS 클라이언트 구현
- [ ] 복호화 함수 구현
- [ ] 인증 API 엔드포인트 구현 (login, me, refresh, logout)
- [ ] 게임 API 구현 (games 목록 조회)
- [ ] 구독 API 구현 (CRUD)
- [ ] 알림 피드 API 구현
- [ ] 푸시 토큰 등록 API 구현

### 푸시 알림 개발
- [ ] Firebase 프로젝트 생성 및 설정
- [ ] FCM 서비스 계정 키 다운로드
- [ ] Django에 firebase-admin 설치
- [ ] 푸시 발송 함수 구현
- [ ] 크롤링 → 푸시 발송 로직 연결
- [ ] Celery Beat 스케줄러 설정 (선택)

### 배포 및 테스트
- [ ] 환경 변수 설정 (.env)
- [ ] mTLS 인증서 경로 확인
- [ ] 로컬 테스트
- [ ] 프론트엔드와 연동 테스트
- [ ] 푸시 알림 실제 디바이스 테스트

---

## 다음 단계

1. **Django 모델 생성 및 마이그레이션**
2. **Toss 인증 API 연동 구현**
3. **구독 관리 API 구현**
4. **푸시 알림 시스템 구축**
5. **프론트엔드와 통합 테스트**

---

**문의:** farmhoney1298@naver.com
