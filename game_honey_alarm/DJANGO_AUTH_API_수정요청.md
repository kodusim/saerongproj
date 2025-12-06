# Django 인증 API 수정 요청사항

## 개요
현재 구현된 Django 인증 API를 프론트엔드 스펙(DJANGO_API_GUIDE.md)에 맞춰서 수정해주세요.

---

## 🔴 수정 필요한 부분

### 1. API 엔드포인트 경로 변경

**현재:** `POST /api/auth/toss/login`
**수정:** `POST /api/auth/login`

경로에서 `toss`를 제거해주세요.

---

### 2. Request/Response 필드명을 카멜 케이스로 변경

Django는 기본적으로 스네이크 케이스를 사용하지만, 프론트엔드는 JavaScript 컨벤션에 따라 카멜 케이스를 사용합니다.

#### 2-1. POST /api/auth/login

**Request Body (이미 올바름):**
```json
{
  "authorizationCode": "string",
  "referrer": "string"
}
```

**Response (수정 필요):**

현재:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user": {...}
}
```

수정 후:
```json
{
  "accessToken": "...",
  "refreshToken": "...",
  "user": {
    "userKey": 123456,
    "name": "홍길동",
    "email": "user@example.com"
  }
}
```

**중요:** `user` 객체를 응답에 포함해주세요! 그러면 프론트엔드에서 별도로 `/api/auth/me`를 호출하지 않아도 됩니다.

---

#### 2-2. POST /api/auth/refresh

**Request Body (수정 필요):**

현재:
```json
{
  "refresh_token": "..."
}
```

수정 후:
```json
{
  "refreshToken": "..."
}
```

**Response (수정 필요):**

현재:
```json
{
  "access_token": "...",
  "refresh_token": "..."
}
```

수정 후:
```json
{
  "accessToken": "...",
  "refreshToken": "..."
}
```

---

#### 2-3. GET /api/auth/me

**Response (이미 올바름):**
```json
{
  "userKey": 123456,
  "name": "홍길동",
  "email": "user@example.com"
}
```

---

### 3. 푸시 토큰 등록 API

**Request Body (수정 필요):**

현재:
```json
{
  "token": "...",
  "device_type": "ios"
}
```

수정 후:
```json
{
  "token": "...",
  "deviceType": "ios"
}
```

---

## ✅ Django에서 카멜 케이스 적용 방법

### 방법 1: djangorestframework-camel-case 패키지 사용 (권장)

```bash
pip install djangorestframework-camel-case
```

**settings.py:**
```python
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
    ),
}
```

이렇게 설정하면:
- 프론트엔드에서 `accessToken`으로 보내면 → Django에서 `access_token`으로 받음
- Django에서 `access_token`으로 보내면 → 프론트엔드에서 `accessToken`으로 받음

---

### 방법 2: Serializer에서 수동으로 변환

```python
from rest_framework import serializers

class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(source='accessToken')
    refresh_token = serializers.CharField(source='refreshToken')
    user = UserSerializer()
```

---

## 📋 수정 체크리스트

### API 엔드포인트
- [ ] `/api/auth/toss/login` → `/api/auth/login`으로 변경

### Request/Response 필드명
- [ ] `POST /api/auth/login` 응답: `access_token` → `accessToken`
- [ ] `POST /api/auth/login` 응답: `refresh_token` → `refreshToken`
- [ ] `POST /api/auth/login` 응답에 `user` 객체 포함
- [ ] `POST /api/auth/refresh` 요청: `refresh_token` → `refreshToken`
- [ ] `POST /api/auth/refresh` 응답: `access_token` → `accessToken`
- [ ] `POST /api/auth/refresh` 응답: `refresh_token` → `refreshToken`
- [ ] `POST /api/push-tokens/` 요청: `device_type` → `deviceType`

### 패키지 설치 및 설정
- [ ] `djangorestframework-camel-case` 설치
- [ ] `settings.py`에 카멜 케이스 renderer/parser 설정
- [ ] `requirements.txt` 업데이트

### 테스트
- [ ] Postman으로 모든 API 테스트
- [ ] 프론트엔드와 연동 테스트

---

## 🧪 테스트 예시

### POST /api/auth/login

**Request:**
```bash
curl -X POST https://saerong.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "authorizationCode": "test-auth-code",
    "referrer": "DEFAULT"
  }'
```

**Expected Response:**
```json
{
  "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refreshToken": "xNEYPASwWw0n1AxZUHU9K...",
  "user": {
    "userKey": 443731104,
    "name": "홍길동",
    "email": "user@example.com"
  }
}
```

---

### POST /api/auth/refresh

**Request:**
```bash
curl -X POST https://saerong.com/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refreshToken": "xNEYPASwWw0n1AxZUHU9K..."
  }'
```

**Expected Response:**
```json
{
  "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refreshToken": "새로운_리프레시_토큰..."
}
```

---

## 📌 참고 자료

- **프론트엔드 API 가이드:** `DJANGO_API_GUIDE.md`
- **토스 로그인 가이드:** `guide/4.개발/토스로그인개발하기.md`
- **djangorestframework-camel-case:** https://github.com/vbabiy/djangorestframework-camel-case

---

## ❓ 질문이 있다면

- farmhoney1298@naver.com
- 프론트엔드 타입 정의: `src/types/index.ts`
- 프론트엔드 API 호출 코드: `src/api/services.ts`
