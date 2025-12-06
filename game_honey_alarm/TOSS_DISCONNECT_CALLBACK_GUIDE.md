# 토스 연결 끊기 콜백 구현 가이드

## 개요
사용자가 토스앱에서 "Game Honey" 앱과의 연결을 끊거나 회원 탈퇴를 할 때, 토스 서버에서 우리 백엔드로 알림을 보냅니다. 이 콜백을 받아서 사용자 데이터를 삭제하거나 비활성화해야 합니다.

---

## 1. 토스 설정 정보

### 콜백 URL 설정
```
콜백 URL: https://saerong.com/api/auth/disconnect-callback
HTTP 메서드: POST
Basic Auth: gamehoney:<강력한_랜덤_비밀번호>
```

**⚠️ 중요:**
- Basic Auth 비밀번호는 `farmhoney` 대신 **강력하고 랜덤한 비밀번호**로 변경하세요
- 예: `kJ9mP2xQ7vL4nR8wT3hZ` (20자 이상 권장)
- 이 비밀번호는 환경 변수에 저장하고 절대 코드에 하드코딩하지 마세요

---

## 2. 토스가 보내는 요청 형식

### HTTP 요청
```http
POST /api/auth/disconnect-callback HTTP/1.1
Host: saerong.com
Authorization: Basic Z2FtZWhvbmV5OmZhcm1ob25leQ==
Content-Type: application/json

{
  "userKey": 1234567890
}
```

### 요청 파라미터
- **userKey** (number, 필수): 연결을 끊는 사용자의 토스 userKey

### Authorization 헤더
- Basic Auth 형식: `Authorization: Basic <base64(username:password)>`
- username: `gamehoney`
- password: 토스 개발자센터에 설정한 비밀번호

---

## 3. Django 구현

### 3.1 환경 변수 설정

**.env 파일에 추가:**
```bash
# 토스 연결 끊기 콜백 인증 정보
TOSS_DISCONNECT_CALLBACK_USERNAME=gamehoney
TOSS_DISCONNECT_CALLBACK_PASSWORD=<여기에_강력한_랜덤_비밀번호_입력>
```

**settings.py에 추가:**
```python
# Toss Disconnect Callback
TOSS_DISCONNECT_CALLBACK_USERNAME = env('TOSS_DISCONNECT_CALLBACK_USERNAME')
TOSS_DISCONNECT_CALLBACK_PASSWORD = env('TOSS_DISCONNECT_CALLBACK_PASSWORD')
```

---

### 3.2 View 구현

**apps/auth/views.py:**
```python
import base64
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


def verify_basic_auth(request):
    """
    Basic Auth 검증
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Basic '):
        return False

    try:
        # "Basic " 제거하고 base64 디코딩
        encoded_credentials = auth_header[6:]
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)

        # 환경 변수와 비교
        expected_username = settings.TOSS_DISCONNECT_CALLBACK_USERNAME
        expected_password = settings.TOSS_DISCONNECT_CALLBACK_PASSWORD

        return username == expected_username and password == expected_password
    except Exception as e:
        print(f"Basic Auth verification failed: {e}")
        return False


@api_view(['POST'])
@permission_classes([AllowAny])
def toss_disconnect_callback(request):
    """
    토스 연결 끊기 콜백

    사용자가 토스앱에서 Game Honey 연결을 끊거나 회원 탈퇴할 때 호출됨
    """
    # 1. Basic Auth 검증
    if not verify_basic_auth(request):
        return Response(
            {'error': 'Unauthorized'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # 2. userKey 추출
    user_key = request.data.get('userKey')
    if not user_key:
        return Response(
            {'error': 'userKey is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 3. 사용자 찾기
        user = User.objects.get(toss_user_key=user_key)

        # 4. 트랜잭션으로 모든 데이터 삭제
        with transaction.atomic():
            # 4-1. 구독 정보 삭제
            user.subscriptions.all().delete()

            # 4-2. 푸시 토큰 삭제
            user.push_tokens.all().delete()

            # 4-3. 토큰 삭제 (RefreshToken 모델이 있다면)
            # user.refresh_tokens.all().delete()

            # 4-4. 사용자 삭제 또는 비활성화 (선택)
            # 방법 1: 완전 삭제
            user.delete()

            # 방법 2: 비활성화 (나중에 복구 가능하도록)
            # user.is_active = False
            # user.toss_user_key = None  # userKey 연결 해제
            # user.save()

        # 5. 로깅
        print(f"User {user_key} disconnected from Toss successfully")

        # 6. 성공 응답
        return Response(
            {'success': True, 'message': 'User disconnected successfully'},
            status=status.HTTP_200_OK
        )

    except User.DoesNotExist:
        # 사용자가 이미 삭제되었거나 존재하지 않는 경우
        # 토스 입장에서는 성공으로 처리
        print(f"User {user_key} not found, but returning success")
        return Response(
            {'success': True, 'message': 'User not found but considered as disconnected'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        # 예상치 못한 에러
        print(f"Error in toss_disconnect_callback: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

---

### 3.3 URL 설정

**apps/auth/urls.py:**
```python
from django.urls import path
from . import views

urlpatterns = [
    # 기존 URL들...
    path('login', views.login, name='login'),
    path('me', views.get_user_info, name='me'),
    path('refresh', views.refresh_token, name='refresh'),
    path('logout', views.logout, name='logout'),

    # 토스 연결 끊기 콜백 추가
    path('disconnect-callback', views.toss_disconnect_callback, name='toss-disconnect-callback'),
]
```

---

### 3.4 User 모델 확인

**User 모델에 toss_user_key 필드가 있는지 확인:**
```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    toss_user_key = models.BigIntegerField(
        unique=True,
        null=True,
        blank=True,
        db_index=True  # 빠른 조회를 위한 인덱스
    )
    # 기타 필드...
```

---

## 4. 테스트

### 4.1 로컬 테스트 (cURL)

```bash
# Basic Auth 생성 (username:password를 base64로 인코딩)
echo -n "gamehoney:YOUR_PASSWORD" | base64
# 출력: Z2FtZWhvbmV5OllPVVJfUEFTU1dPUkQ=

# 테스트 요청
curl -X POST https://saerong.com/api/auth/disconnect-callback \
  -H "Authorization: Basic Z2FtZWhvbmV5OllPVVJfUEFTU1dPUkQ=" \
  -H "Content-Type: application/json" \
  -d '{"userKey": 1234567890}'
```

**예상 응답:**
```json
{
  "success": true,
  "message": "User disconnected successfully"
}
```

---

### 4.2 Django Shell에서 테스트

```python
python manage.py shell

from django.contrib.auth import get_user_model
from apps.subscriptions.models import Subscription
from apps.notifications.models import PushToken

User = get_user_model()

# 테스트 사용자 생성
user = User.objects.create(
    username='test_user',
    toss_user_key=1234567890
)

# 구독 및 푸시 토큰 생성
Subscription.objects.create(user=user, game_id='maplestory', category='공지사항')
PushToken.objects.create(user=user, token='test-token', device_type='ios')

# 콜백 호출 후 확인
User.objects.filter(toss_user_key=1234567890).exists()  # False여야 함
```

---

### 4.3 Postman으로 테스트

**설정:**
1. Method: POST
2. URL: `https://saerong.com/api/auth/disconnect-callback`
3. Authorization 탭:
   - Type: Basic Auth
   - Username: `gamehoney`
   - Password: `<설정한_비밀번호>`
4. Body 탭:
   - Type: raw / JSON
   ```json
   {
     "userKey": 1234567890
   }
   ```

---

## 5. 보안 고려사항

### 5.1 Basic Auth 비밀번호 강도
- 최소 20자 이상
- 대소문자, 숫자, 특수문자 혼합
- 절대 코드에 하드코딩하지 말 것
- 환경 변수로만 관리

### 5.2 HTTPS 필수
- 프로덕션 환경에서는 반드시 HTTPS 사용
- HTTP는 Basic Auth가 평문으로 전송되어 위험

### 5.3 로깅
```python
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def toss_disconnect_callback(request):
    # IP 로깅 (보안 모니터링용)
    client_ip = request.META.get('REMOTE_ADDR')
    logger.info(f"Disconnect callback received from IP: {client_ip}")

    # 나머지 로직...
```

### 5.4 Rate Limiting (선택)
```python
from rest_framework.throttling import AnonRateThrottle

class DisconnectCallbackThrottle(AnonRateThrottle):
    rate = '100/hour'  # 시간당 100회로 제한

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([DisconnectCallbackThrottle])
def toss_disconnect_callback(request):
    # 로직...
```

---

## 6. 에러 처리 체크리스트

- [ ] Basic Auth 실패 → 401 Unauthorized
- [ ] userKey 누락 → 400 Bad Request
- [ ] 사용자 없음 → 200 OK (토스 입장에서는 성공)
- [ ] 데이터베이스 에러 → 500 Internal Server Error
- [ ] 모든 에러는 로깅

---

## 7. 배포 전 체크리스트

### 환경 변수 확인
- [ ] `.env` 파일에 `TOSS_DISCONNECT_CALLBACK_PASSWORD` 설정
- [ ] 강력한 랜덤 비밀번호 사용 (20자 이상)
- [ ] 프로덕션과 스테이징 환경 각각 다른 비밀번호 사용

### 토스 개발자센터 설정
- [ ] 콜백 URL: `https://saerong.com/api/auth/disconnect-callback`
- [ ] HTTP 메서드: POST
- [ ] Basic Auth: `gamehoney:<실제_비밀번호>`

### 코드 확인
- [ ] View 구현 완료
- [ ] URL 라우팅 설정
- [ ] Basic Auth 검증 로직 추가
- [ ] 트랜잭션으로 데이터 삭제
- [ ] 에러 처리 및 로깅

### 테스트
- [ ] cURL로 로컬 테스트
- [ ] Postman으로 API 테스트
- [ ] 실제 사용자 데이터로 삭제 확인
- [ ] 로그 확인

---

## 8. 모니터링 및 유지보수

### 로그 모니터링
```python
# 정기적으로 로그 확인
# 비정상적인 요청 패턴 감지
# 실패한 요청 분석
```

### 메트릭 수집 (선택)
```python
from django.core.cache import cache

def toss_disconnect_callback(request):
    # 콜백 호출 횟수 카운트
    cache.incr('toss_disconnect_callback_count', 1)
    # 로직...
```

---

## 참고 자료

- 토스 개발자센터: https://developers.toss.im
- Django REST Framework 문서: https://www.django-rest-framework.org/
- Basic Authentication RFC: https://tools.ietf.org/html/rfc7617

---

## 문의
- 이메일: farmhoney1298@naver.com
