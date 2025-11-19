# Game Honey 앱 - 푸시 알림 수신 가이드

## 📌 개요

Game Honey 백엔드에서 **토스 메신저 API**를 통해 푸시 알림을 발송합니다.
React Native 앱에서는 **별도의 푸시 리스너 구현 없이** 토스 로그인만 하면 자동으로 푸시를 받을 수 있습니다.

---

## ✅ 현재 구현 상태

### 백엔드 (완료 ✓)

- ✅ 토스 메신저 API 연동 (`api/push_notifications.py`)
- ✅ 자동 푸시 알림 발송 (새 게임 뉴스 발견 시)
- ✅ 테스트 푸시 API (`/api/test/push/`)
- ✅ mTLS 인증서 설정

**발송 API 엔드포인트:**
```
POST https://toss.im/api/v1/apps-in-toss/push
```

**발송 데이터 형식:**
```json
{
  "userKeys": [123456789],
  "notification": {
    "title": "메이플스토리 공지사항",
    "body": "[공지] 정기점검 안내"
  },
  "data": {
    "gameId": "maplestory",
    "category": "공지사항",
    "url": "https://maplestory.nexon.com/..."
  }
}
```

---

## 📱 앱에서 해야 할 작업

### 1. 토스 로그인 (이미 구현됨 ✓)

현재 앱에서 이미 토스 로그인을 구현하셨습니다:
- `useAuth` 훅 사용
- JWT 토큰 관리
- `UserProfile.toss_user_key` 저장

**토스 로그인이 완료되면 푸시 알림은 자동으로 수신됩니다.**

---

### 2. 푸시 알림 수신 (자동 처리됨 ✓)

**중요:** Apps in Toss에서는 **별도의 푸시 리스너 구현이 필요 없습니다**.

#### 작동 방식

1. 백엔드에서 토스 메신저 API로 푸시 발송
2. **토스 앱**이 푸시 알림 수신 및 표시
3. 사용자가 토스 앱의 **"알림센터"** (우측 상단 종 아이콘)에서 확인

#### 푸시 알림 표시 위치

```
[토스 앱]
  ↓
[알림센터] (종 아이콘)
  ↓
[Game Honey 알림 목록]
  - 메이플스토리 공지사항
  - 로스트아크 업데이트
  - 발로란트 이벤트
  ...
```

---

### 3. 딥링크 처리 (선택 구현)

푸시 알림을 클릭했을 때 **Game Honey 앱으로 바로 이동**하려면 딥링크 핸들러를 구현해야 합니다.

#### 3-1. React Native Linking 설정

```typescript
// App.tsx 또는 _app.tsx
import { useEffect } from 'react';
import { Linking } from 'react-native';

function App() {
  useEffect(() => {
    // 앱이 종료된 상태에서 푸시를 클릭한 경우
    Linking.getInitialURL().then(url => {
      if (url) {
        handleDeepLink(url);
      }
    });

    // 앱이 실행 중일 때 푸시를 클릭한 경우
    const subscription = Linking.addEventListener('url', ({ url }) => {
      handleDeepLink(url);
    });

    return () => {
      subscription.remove();
    };
  }, []);

  const handleDeepLink = (url: string) => {
    console.log('Deep link received:', url);

    // URL 파싱
    // 예: gamehoney://news?gameId=maplestory&category=공지사항
    const route = parseDeepLink(url);

    if (route) {
      // React Navigation으로 화면 이동
      navigation.navigate(route.screen, route.params);
    }
  };

  // ... 나머지 코드
}
```

#### 3-2. URL Scheme 등록

**iOS (Info.plist):**
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>gamehoney</string>
    </array>
  </dict>
</array>
```

**Android (AndroidManifest.xml):**
```xml
<activity
  android:name=".MainActivity"
  android:launchMode="singleTask">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="gamehoney" />
  </intent-filter>
</activity>
```

#### 3-3. 백엔드에서 딥링크 포함

**현재 코드 (api/push_notifications.py):**
```python
def notify_subscribers(collected_data):
    # ...

    # 푸시 알림 발송 시 딥링크 추가
    data = {
        "gameId": game.game_id,
        "category": category,
        "url": news_url,  # 외부 URL (브라우저 열기)
        "deeplink": f"gamehoney://news?gameId={game.game_id}&category={category}"  # 앱 내 화면 이동
    }

    send_toss_push_notification(
        user_keys=user_keys,
        title=title,
        body=body,
        data=data
    )
```

#### 3-4. 딥링크 파싱 유틸리티

```typescript
// src/utils/deeplink.ts
export interface DeepLinkRoute {
  screen: string;
  params: any;
}

export function parseDeepLink(url: string): DeepLinkRoute | null {
  try {
    const urlObj = new URL(url);

    // gamehoney://news?gameId=maplestory&category=공지사항
    if (urlObj.protocol === 'gamehoney:' && urlObj.hostname === 'news') {
      const params = new URLSearchParams(urlObj.search);

      return {
        screen: 'NewsDetail',
        params: {
          gameId: params.get('gameId'),
          category: params.get('category'),
          url: params.get('url'),
        }
      };
    }

    return null;
  } catch (error) {
    console.error('Failed to parse deep link:', error);
    return null;
  }
}
```

---

## 🧪 테스트 방법

### 1. 토스 앱에서 푸시 확인

1. 토스 로그인된 상태로 Game Honey 앱 실행
2. 백엔드에서 테스트 푸시 발송:
   ```bash
   # 웹 브라우저에서
   https://saerong.com/api/guide/
   → "테스트 푸시 알림 보내기" 버튼 클릭

   # 또는 앱에서
   Settings 화면 → "테스트 푸시 알림 보내기" 버튼
   ```
3. **토스 앱**을 열어서 **알림센터** (우측 상단 종 아이콘) 확인
4. 푸시 알림이 표시되는지 확인

### 2. 자동 푸시 확인

1. Django 관리자에서 게임 구독
2. Celery 크롤링이 새 소식 발견 시 자동 푸시 발송
3. 토스 앱 알림센터에서 확인

---

## 📊 푸시 알림 플로우

```
[백엔드 크롤링]
    ↓
[새 뉴스 발견]
    ↓
[구독자 조회]
    ↓
[토스 메신저 API 호출]
    userKeys: [123456, 789456, ...]
    notification: { title, body }
    data: { gameId, category, url }
    ↓
[토스 서버]
    ↓
[토스 앱 - 푸시 알림 표시]
    ↓
[사용자 클릭]
    ↓
[토스 앱 - 알림센터]
    ↓
(선택) [딥링크로 Game Honey 앱 화면 이동]
```

---

## ❓ FAQ

### Q1. React Native 앱에서 FCM이나 APNs 설정이 필요한가요?

**A:** 아니요. **Apps in Toss**에서는 토스 앱이 푸시를 처리하므로, 별도의 FCM/APNs 설정이 **필요 없습니다**.

### Q2. 푸시가 안 오는 경우 어떻게 디버깅하나요?

**체크리스트:**
1. ✅ 토스 로그인이 정상적으로 되었는지 확인
2. ✅ `UserProfile.toss_user_key`가 저장되었는지 확인
3. ✅ 백엔드 로그에서 토스 API 호출 성공 여부 확인
4. ✅ 토스 앱의 **알림 권한**이 허용되었는지 확인
5. ✅ mTLS 인증서가 서버에 올바르게 설정되었는지 확인

### Q3. 푸시를 클릭했을 때 웹 브라우저가 열리나요, 앱이 열리나요?

**A:** 기본적으로는 **토스 앱의 알림센터**에 표시됩니다.
- `data.url` 필드에 웹 URL이 있으면 **웹 브라우저** 열기
- `data.deeplink` 필드에 앱 스킴이 있으면 **Game Honey 앱** 열기

### Q4. 백그라운드/종료 상태에서도 푸시를 받나요?

**A:** 네, 토스 앱이 설치되어 있고 **알림 권한**이 허용되어 있으면 받습니다.

### Q5. 푸시 알림 템플릿 승인이 필요한가요?

**A:** 토스 Apps in Toss의 마케팅 푸시를 사용하려면 **콘솔에서 템플릿 승인**이 필요합니다.
하지만 현재는 **서버 API**를 직접 호출하므로, 템플릿 승인 없이 **기능성 푸시**로 발송 가능합니다.

---

## 🚀 다음 단계

### 1단계: 현재 상태 확인
- [ ] 토스 로그인이 정상 작동하는지 확인
- [ ] 백엔드에서 테스트 푸시 발송 성공 확인
- [ ] 토스 앱 알림센터에서 푸시 수신 확인

### 2단계: (선택) 딥링크 구현
- [ ] URL Scheme 등록 (iOS/Android)
- [ ] React Native Linking 핸들러 구현
- [ ] 딥링크 파싱 로직 작성
- [ ] 백엔드에서 `data.deeplink` 필드 추가

### 3단계: QA
- [ ] 다양한 기기에서 푸시 수신 테스트
- [ ] 앱 상태별 테스트 (실행 중/백그라운드/종료)
- [ ] 딥링크 동작 테스트
- [ ] 여러 게임 구독 시 푸시 개수 확인

---

## 📞 문의

- 백엔드 API 관련: `game_honey_api.md` 참고
- 토스 Apps in Toss 문서: `app_in_toss_guide/` 폴더
- 푸시 알림 상세: `app_in_toss_guide/7.마케팅/푸시알림개발가이드.md`

**마지막 업데이트:** 2025-01-19
