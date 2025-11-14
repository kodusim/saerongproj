# Toss Disconnect Callback API 가이드

배포가 완료되었습니다!

## 구현 완료 항목

### 1. Django 설정
- `settings.py`에 환경 변수 추가
- `TOSS_DISCONNECT_CALLBACK_USERNAME`
- `TOSS_DISCONNECT_CALLBACK_PASSWORD`

### 2. API View 구현 (`api/views.py`)
- `verify_basic_auth()`: Basic Auth 검증 함수
- `toss_disconnect_callback()`: 토스 콜백 처리 view

### 3. URL 라우팅 (`api/urls.py`)
- `POST /api/auth/disconnect-callback`

## 서버 배포 전 작업

### 1. 환경 변수 설정

**서버의 `.env` 파일에 추가:**
```bash
# 토스 연결 끊기 콜백 인증 정보
TOSS_DISCONNECT_CALLBACK_USERNAME=gamehoney
TOSS_DISCONNECT_CALLBACK_PASSWORD=<강력한_랜덤_비밀번호>
```

**비밀번호 생성 예시:**
```python
import secrets
print(secrets.token_urlsafe(32))  # 예: kJ9mP2xQ7vL4nR8wT3hZ1fX4qR9sW2vT
```

### 2. 토스 개발자센터 설정

**콜백 URL 설정:**
```
URL: https://saerong.com/api/auth/disconnect-callback
HTTP 메서드: POST
Basic Auth:
  - Username: gamehoney
  - Password: <위에서_설정한_비밀번호>
```

## API 테스트

### cURL로 테스트
```bash
# Basic Auth 인코딩
echo -n "gamehoney:YOUR_PASSWORD" | base64
# 출력: Z2FtZWhvbmV5OllPVVJfUEFTU1dPUkQ=

# API 호출
curl -X POST https://saerong.com/api/auth/disconnect-callback \
  -H "Authorization: Basic Z2FtZWhvbmV5OllPVVJfUEFTU1dPUkQ=" \
  -H "Content-Type: application/json" \
  -d '{"userKey": 1234567890}'
```

### 예상 응답
```json
{
  "success": true,
  "message": "User disconnected successfully"
}
```

## 작동 방식

1. 토스 서버가 `POST /api/auth/disconnect-callback` 호출
2. Basic Auth 검증
3. `userKey`로 `UserProfile` 찾기
4. 트랜잭션으로 데이터 삭제:
   - 구독 정보 (`Subscription`)
   - 푸시 토큰 (`PushToken`)
   - 프로필 (`UserProfile`)
   - 사용자 (`User`)
5. 성공 응답 반환

## 에러 처리

- **401 Unauthorized**: Basic Auth 실패
- **400 Bad Request**: userKey 누락
- **200 OK**: 성공 또는 사용자 이미 삭제됨
- **500 Internal Server Error**: 예상치 못한 에러

## 보안

- HTTPS 필수 (Basic Auth는 평문 전송)
- 강력한 랜덤 비밀번호 사용 (20자 이상)
- 환경 변수로만 관리 (코드에 하드코딩 금지)
- 로깅으로 모니터링
