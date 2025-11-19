# Game Honey API 가이드

## 📋 목차
1. [인증 API](#인증-api)
2. [게임 API](#게임-api)
3. [구독 API](#구독-api)
4. [프리미엄 구독 API](#프리미엄-구독-api)
5. [알림 API](#알림-api)
6. [테스트 API](#테스트-api)

---

## 🔐 인증 API

### 1. 토스 로그인
**Endpoint:** `POST /api/auth/login`

토스 appLogin()으로 받은 authorizationCode를 전송하여 JWT 토큰을 발급받습니다.

**Request:**
```json
{
  "authorizationCode": "abc123...",
  "referrer": "DEFAULT"  // "DEFAULT" 또는 "SANDBOX"
}
```

**Response:**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "user": {
    "id": 1,
    "username": "toss_443731104",
    "tossUserKey": 443731104,
    "name": "홍길동",
    "isNew": true
  }
}
```

### 2. 토큰 갱신
**Endpoint:** `POST /api/auth/refresh`

**Request:**
```json
{
  "refreshToken": "eyJ..."
}
```

**Response:**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ..."
}
```

### 3. 현재 사용자 정보
**Endpoint:** `GET /api/auth/me`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "id": 1,
  "username": "toss_443731104",
  "tossUserKey": 443731104,
  "name": "홍길동"
}
```

### 4. 로그아웃
**Endpoint:** `POST /api/auth/logout`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 🎮 게임 API

### 1. 게임 목록 조회
**Endpoint:** `GET /api/games/`

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "gameId": "maplestory",
      "displayName": "메이플스토리",
      "iconUrl": "https://...",
      "isActive": true,
      "categories": ["공지사항", "업데이트", "이벤트"],
      "createdAt": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

## 🔔 구독 API

### 1. 내 구독 목록 조회
**Endpoint:** `GET /api/subscriptions/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "game": 1,
      "gameId": "maplestory",
      "gameName": "메이플스토리",
      "category": "공지사항",
      "createdAt": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### 2. 게임 구독
**Endpoint:** `POST /api/subscriptions/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request:**
```json
{
  "gameId": "maplestory",
  "category": "공지사항"
}
```

**Response:**
```json
{
  "id": 1,
  "game": 1,
  "gameId": "maplestory",
  "gameName": "메이플스토리",
  "category": "공지사항",
  "createdAt": "2025-01-01T00:00:00Z"
}
```

**에러 응답:**
```json
// 프리미엄 구독권 없음
{
  "error": "구독하려면 광고를 시청하거나 프리미엄을 구매해주세요."
}

// 광고 구독자가 이미 1개 게임 구독 중
{
  "error": "광고 구독은 1개 게임만 구독할 수 있습니다. 프리미엄을 구매하면 무제한으로 구독할 수 있어요."
}

// 이미 구독 중
{
  "error": "이미 구독 중입니다."
}
```

### 3. 구독 취소
**Endpoint:** `DELETE /api/subscriptions/{id}/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:**
```
204 No Content
```

---

## 💎 프리미엄 구독 API

### 1. 프리미엄 구독 상태 조회
**Endpoint:** `GET /api/premium/status/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Response:**
```json
{
  "isPremium": true,
  "expiresAt": "2025-12-26T00:00:00Z",
  "subscriptionType": "free_ad",  // "free_ad" (7일) 또는 "premium" (30일)
  "maxGames": 1,                   // free_ad: 1, premium: null (무제한)
  "subscribedGamesCount": 0,
  "canSubscribeMore": true
}
```

**비구독자 응답:**
```json
{
  "isPremium": false,
  "expiresAt": null,
  "subscriptionType": null,
  "maxGames": null,
  "subscribedGamesCount": 0,
  "canSubscribeMore": false
}
```

### 2. 프리미엄 구독권 부여
**Endpoint:** `POST /api/premium/grant/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request:**
```json
{
  "subscriptionType": "free_ad",  // "free_ad" (광고 시청) 또는 "premium" (인앱결제)
  "orderId": "uuid-v7"             // premium인 경우 필수 (인앱결제 주문 ID)
}
```

**Response:**
```json
{
  "expiresAt": "2025-12-26T00:00:00Z"
}
```

**구독 기간:**
- `free_ad`: 7일
- `premium`: 30일

**자동 연장:**
- 기존 활성 구독이 있으면 만료일에서 연장
- 만료된 구독이 있으면 현재 시각부터 시작

---

## 📬 알림 API

### 1. 알림 피드 조회
**Endpoint:** `GET /api/notifications/?limit=20`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `limit`: 조회할 개수 (기본값: 20)

**Response:**
```json
[
  {
    "game": "메이플스토리",
    "gameId": "maplestory",
    "category": "공지사항",
    "title": "[공지] 정기점검 안내",
    "url": "https://maplestory.nexon.com/...",
    "date": "2025-01-15",
    "collectedAt": "2025-01-15T10:30:00Z"
  }
]
```

### 2. 푸시 토큰 등록
**Endpoint:** `POST /api/push-tokens/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request:**
```json
{
  "token": "FCM_TOKEN_HERE",
  "deviceType": "android"  // "android" 또는 "ios"
}
```

**Response:**
```json
{
  "id": 1,
  "token": "FCM_TOKEN_HERE",
  "deviceType": "android",
  "createdAt": "2025-01-01T00:00:00Z",
  "updatedAt": "2025-01-01T00:00:00Z"
}
```

---

## 🧪 테스트 API

### 테스트 푸시 알림 발송
**Endpoint:** `POST /api/test/push/`

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request:**
```json
{
  "title": "테스트 제목",
  "body": "테스트 본문"  // optional
}
```

**Response (성공):**
```json
{
  "success": true,
  "message": "푸시 알림 발송 완료",
  "userKey": 123456789,
  "title": "테스트 제목",
  "body": "테스트 본문"
}
```

**Response (실패):**
```json
{
  "success": false,
  "error": "푸시 알림 발송 실패 (토스 API 에러 또는 인증서 미설정)"
}
```

**에러:**
```json
// 토스 로그인 안 한 경우
{
  "error": "토스 로그인이 필요합니다. (user_key 없음)"
}
```

**사용 방법:**
1. 토스 로그인하여 accessToken 받기
2. 위 API 호출
3. 토스 앱에서 푸시 알림 확인

**주의사항:**
- 토스 메신저 API mTLS 인증서가 서버에 설정되어 있어야 합니다
- `settings.py`에 `TOSS_CERT_PATH`, `TOSS_KEY_PATH` 필요

---

## 🔧 서버 설정

### 필수 환경 변수 (`.env`)
```bash
# Django 기본 설정
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=saerong.com

# 데이터베이스
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# 토스 인증
TOSS_CERT_PATH=/path/to/client-cert.pem
TOSS_KEY_PATH=/path/to/client-key.pem

# 토스 연결 끊기 콜백
TOSS_DISCONNECT_CALLBACK_USERNAME=gamehoney
TOSS_DISCONNECT_CALLBACK_PASSWORD=강력한_랜덤_비밀번호
```

---

## 🚀 자동 푸시 알림 시스템

### 동작 방식
1. **크롤링** (Celery Beat - 설정된 시간마다)
   - 메이플스토리 공지사항, 이벤트, 업데이트 등 자동 크롤링

2. **새 소식 발견**
   - CollectedData 생성 (중복 체크)

3. **자동 매핑**
   - SubCategory.slug ("maplestory") → Game.game_id ("maplestory")
   - DataSource.name ("공지사항") → Subscription.category

4. **구독자 찾기**
   - 해당 게임/카테고리 구독한 사용자 조회

5. **푸시 알림 발송**
   - 토스 메신저 API 호출 (mTLS 인증)
   - 각 구독자에게 푸시 전송

### 새 게임 추가 방법

**1. Game 추가**
```python
Game.objects.create(
    game_id='lostark',
    display_name='로스트아크',
    icon_url='https://...'
)
```

**2. SubCategory 추가** (slug = game_id)
```python
SubCategory.objects.create(
    category=게임_카테고리,
    name='로스트아크',
    slug='lostark'  # ← Game.game_id와 동일하게!
)
```

**3. DataSource 추가** (name = category)
```python
DataSource.objects.create(
    subcategory=로스트아크_SubCategory,
    name='공지사항',  # ← Subscription.category와 동일!
    url='https://lostark.game.onstove.com/News/Notice/List',
    crawler_type='selenium',
    crawl_interval=5  # 5분마다 크롤링
)
```

**끝! 코드 수정 없이 바로 작동합니다!** 🎉

---

## 📱 앱 개발 가이드

### 1. 토스 로그인 플로우
```typescript
// 1. 토스 로그인 실행
const result = await tossLogin.appLogin();

// 2. authorizationCode로 JWT 토큰 받기
const response = await fetch('https://saerong.com/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    authorizationCode: result.authorizationCode,
    referrer: 'DEFAULT'
  })
});

const { accessToken, refreshToken, user } = await response.json();

// 3. 토큰 저장
await AsyncStorage.setItem('accessToken', accessToken);
await AsyncStorage.setItem('refreshToken', refreshToken);
```

### 2. API 호출 (인증 필요)
```typescript
const accessToken = await AsyncStorage.getItem('accessToken');

const response = await fetch('https://saerong.com/api/subscriptions/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
```

### 3. 구독 등급 확인
```typescript
// 프리미엄 상태 조회
const status = await fetch('https://saerong.com/api/premium/status/', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
}).then(r => r.json());

if (!status.isPremium) {
  // 광고 시청 또는 프리미엄 구매 유도
} else if (status.subscriptionType === 'free_ad' && !status.canSubscribeMore) {
  // 이미 1개 게임 구독 중 - 프리미엄 구매 유도
}
```

### 4. 테스트 푸시 알림
```typescript
const response = await fetch('https://saerong.com/api/test/push/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: '테스트 제목',
    body: '테스트 본문'
  })
});

const result = await response.json();
console.log(result); // { success: true, message: "푸시 알림 발송 완료", ... }
```

---

## 🐛 디버깅

### 로그 확인
```bash
# Django 로그
sudo tail -f /var/log/gunicorn/error.log

# Celery 로그
sudo tail -f /var/log/celery/worker.log
sudo tail -f /var/log/celery/beat.log
```

### 크롤링 상태 확인
```python
# Django shell
python manage.py shell

from collector.models import CrawlLog
CrawlLog.objects.order_by('-started_at')[:5]
```

### 푸시 알림 테스트
```bash
# cURL
curl -X POST https://saerong.com/api/test/push/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"테스트 제목","body":"테스트 본문"}'
```

---

## 📞 문의

- 버그 리포트: GitHub Issues
- 문의: developer@saerong.com

**마지막 업데이트:** 2025-01-19
