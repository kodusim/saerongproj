# AI Photo Studio - React Vite App

> AI 프로필 이미지 생성 웹 애플리케이션 (토스 인앱용)

React + TypeScript + Vite로 제작된 AI 프로필 생성 서비스입니다.
사용자가 사진을 선택하면 광고를 시청한 후 AI가 프로필 이미지를 생성해줍니다.

---

## 📚 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [기술 스택](#-기술-스택)
3. [프로젝트 구조](#-프로젝트-구조)
4. [주요 기능](#-주요-기능)
5. [광고 시스템](#-광고-시스템)
6. [설치 및 실행](#-설치-및-실행)
7. [환경 변수](#-환경-변수)
8. [빌드 및 배포](#-빌드-및-배포)
9. [문제 해결](#-문제-해결)
10. [개발 가이드](#-개발-가이드)

---

## 🎯 프로젝트 개요

### 무엇을 만들었나요?

사용자가 업로드한 사진으로 AI가 프로필 이미지를 생성해주는 웹 애플리케이션입니다.

### 사용자 플로우

```
1. 인트로 화면
   ↓ (사진 선택: 앨범/카메라/파일)

2. 로딩 화면 (광고 로드 대기)
   ↓

3. 광고 시청 (보상형 또는 전면형)
   ↓ (광고 완료)

4. 로딩 화면 (AI 프로필 생성)
   ↓

5. 결과 화면 (생성된 이미지 확인)
```

### 주요 특징

- ✅ **3가지 이미지 입력 방식**: 앨범, 카메라, 파일 선택
- ✅ **자동 이미지 압축**: 최대 1MB, 512px로 최적화
- ✅ **광고 연동**: 보상형/전면형 광고 지원
- ✅ **재시도 로직**: 광고 및 API 요청 실패 시 자동 재시도
- ✅ **에러 핸들링**: 모든 에러 상황에서 사용자 친화적 메시지 표시

---

## 🛠 기술 스택

### Core

- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안정성
- **Vite 5.4** - 빌드 도구 (빠른 개발 서버 & HMR)

### Libraries

- **@apps-in-toss/web-framework** - 토스 인앱 프레임워크
  - `GoogleAdMob` - 광고 SDK
  - `fetchAlbumPhotos` - 앨범 접근
  - `openCamera` - 카메라 접근
- **browser-image-compression** - 클라이언트 이미지 압축
- **react-simplikit** - 토스 디자인 시스템

### Development

- **ESLint** - 코드 품질
- **TypeScript ESLint** - TS 린팅

---

## 📁 프로젝트 구조

```
react-vite-app/
├── src/
│   ├── pages/
│   │   └── ProfilePage.tsx          # 메인 페이지 (핵심 로직)
│   │
│   ├── components/
│   │   ├── Intro.tsx                # 인트로 화면
│   │   ├── Loading.tsx              # 로딩 화면
│   │   ├── Result.tsx               # 결과 화면
│   │   └── ErrorState.tsx           # 에러 화면
│   │
│   ├── App.tsx                      # 앱 진입점
│   └── main.tsx                     # React 마운트
│
├── public/                          # 정적 파일
├── dist/                            # 빌드 결과물
│
├── package.json                     # 의존성 관리
├── vite.config.ts                   # Vite 설정
├── tsconfig.json                    # TypeScript 설정
├── granite.config.ts                # 토스 인앱 설정
└── README.md                        # 이 파일
```

---

## ✨ 주요 기능

### 1. 이미지 선택 (3가지 방식)

#### 📱 앨범에서 선택

```typescript
const pickFromAlbum = async () => {
  // 권한 확인
  const currentPermission = await fetchAlbumPhotos.getPermission?.();

  if (currentPermission === 'denied') {
    // 권한 요청
    await fetchAlbumPhotos.openPermissionDialog?.();
  }

  // 사진 선택
  const photos = await fetchAlbumPhotos({
    maxCount: 1,          // 1장만 선택
    maxWidth: 128,        // 썸네일 크기
    base64: true,         // Base64 형식으로
  });

  // 선택한 사진 저장
  imageRef.current = { dataUri: photos[0].dataUri };
  requestGeneration();
};
```

**특징:**
- 권한 거부 시 다이얼로그 표시
- 썸네일 크기 제한 (성능 최적화)
- Base64 형식으로 반환

#### 📷 카메라로 촬영

```typescript
const takePhoto = async () => {
  // 권한 확인 및 요청
  const currentPermission = await openCamera.getPermission?.();

  // 사진 촬영
  const photo = await openCamera({
    maxWidth: 512,        // 최대 크기
    base64: true,         // Base64 형식으로
  });

  // 촬영한 사진 저장
  imageRef.current = { dataUri: photo.dataUri };
  requestGeneration();
};
```

**특징:**
- 촬영 시 크기 제한 (512px)
- 즉시 압축된 형태로 반환

#### 📂 파일 선택 (Fallback)

```typescript
<input
  ref={fileInputRef}
  type="file"
  accept="image/*"
  onChange={handleFileChange}
  style={{ display: 'none' }}
/>
```

**용도:**
- 앨범/카메라 미지원 환경용
- 웹 브라우저에서 테스트 시

### 2. 이미지 압축

```typescript
const IMAGE_COMPRESSION_OPTIONS = {
  maxSizeMB: 1,                    // 최대 1MB
  maxWidthOrHeight: 512,           // 최대 512px
  useWebWorker: true,              // 별도 스레드 사용
} as const;

const compressImage = async (file: File): Promise<File> => {
  const compressed = await imageCompression(file, IMAGE_COMPRESSION_OPTIONS);

  // File 또는 Blob을 File 객체로 변환
  if (compressed instanceof File) {
    return compressed;
  }

  return new File([compressed], file.name, {
    type: compressed.type || file.type
  });
};
```

**왜 압축하나요?**
- 네트워크 비용 절감
- 업로드 속도 향상
- 서버 부하 감소

**압축 전략:**
- 크기: 1MB 이하로 제한
- 해상도: 512px 이하로 제한
- Web Worker: 메인 스레드 블로킹 방지

### 3. 광고 연동

자세한 내용은 [광고 시스템](#-광고-시스템) 섹션 참고

### 4. API 요청 (재시도 포함)

```typescript
/**
 * 타임아웃 기능이 있는 fetch
 */
const fetchWithTimeout = (url: string, options: RequestInit, timeout: number) => {
  return Promise.race([
    fetch(url, options),
    new Promise<Response>((_, reject) =>
      setTimeout(() => reject(new Error('REQUEST_TIMEOUT')), timeout)
    )
  ]);
};

/**
 * 재시도 로직이 포함된 API 요청
 */
const request = async (attempt: number): Promise<Response> => {
  const formData = new FormData();
  formData.append('image', imageData, fileName);

  try {
    return await fetchWithTimeout(apiUrl, {
      method: 'POST',
      body: formData
    }, timeoutMs);
  } catch (error) {
    // 타임아웃 발생 시 재시도
    if (attempt < retryLimit && error.message === 'REQUEST_TIMEOUT') {
      await sleep(retryDelay);
      return request(attempt + 1); // 재귀적 재시도
    }
    throw error;
  }
};
```

**재시도 설정:**
- 최대 재시도: 3회
- 타임아웃: 90초
- 재시도 간격: 3초

---

## 💰 광고 시스템

### 광고 타입

#### 1. 보상형 광고 (Rewarded Ad)

- **특징**: 끝까지 시청해야 보상 획득
- **보상**: 프로필 생성 진행
- **중도 종료**: 에러 메시지 표시 ("광고를 끝까지 시청해주세요")
- **광고 ID**: `ait-ad-test-rewarded-id` (테스트용)

#### 2. 전면형 광고 (Interstitial Ad)

- **특징**: 언제든 닫을 수 있음
- **닫기**: 바로 프로필 생성 진행
- **광고 ID**: `ait-ad-test-interstitial-id` (테스트용)

### 광고 전략 (Fallback)

```
1순위: 보상형 광고
   ↓ (로드 실패)
   재시도 (1초 후)
   ↓ (로드 실패)
   재시도 (3초 후)
   ↓ (로드 실패)
   재시도 (5초 후)
   ↓ (3회 모두 실패)

2순위: 전면형 광고
   ↓ (로드 실패)
   재시도 3회 (1초, 3초, 5초)
   ↓ (3회 모두 실패)

최종: 광고 없이 프로필 생성 진행
```

### 광고 ID 설정

#### 테스트용 광고 ID (기본값)

코드에 이미 설정되어 있습니다:

```typescript
// src/pages/ProfilePage.tsx (36-39번째 줄)
const AD_GROUP_IDS = {
  REWARDED: 'ait-ad-test-rewarded-id',      // 보상형 광고 (테스트)
  INTERSTITIAL: 'ait-ad-test-interstitial-id',  // 전면형 광고 (테스트)
} as const;
```

#### 실제 광고 ID로 변경하기

**1단계: 앱스인토스 콘솔에서 광고 유닛 생성**

1. [앱스인토스 콘솔](https://apps-in-toss.toss.im/) 접속
2. 앱 선택 → 광고 메뉴
3. 새 광고 유닛 생성:
   - **보상형 광고 유닛** 생성
   - **전면형 광고 유닛** 생성
4. 생성된 광고 ID 확인
   - 형식: `ait.live.xxxxx`

**2단계: 코드에서 광고 ID 교체**

[src/pages/ProfilePage.tsx](src/pages/ProfilePage.tsx) 파일의 36-39번째 줄:

```typescript
// 변경 전 (테스트용)
const AD_GROUP_IDS = {
  REWARDED: 'ait-ad-test-rewarded-id',
  INTERSTITIAL: 'ait-ad-test-interstitial-id',
} as const;

// 변경 후 (실제 광고 ID)
const AD_GROUP_IDS = {
  REWARDED: 'ait.live.eb562973a6ac4acb',        // 앱스인토스에서 발급받은 보상형 광고 ID
  INTERSTITIAL: 'ait.live.b4bb9bb706d84d11',    // 앱스인토스에서 발급받은 전면형 광고 ID
} as const;
```

**3단계: 재빌드**

```bash
npm run build
```

**주의사항:**
- ⚠️ Google AdMob ID(`ca-app-pub-xxxxx~xxxxx`)가 **아닙니다**
- ✅ 앱스인토스 콘솔에서 발급받은 `ait.live.xxxxx` 형식 사용
- ✅ 테스트 ID(`ait-ad-test-*`)는 개발 시에만 사용

### 광고 동작 흐름

#### 1. 앱 시작 시 (광고 로드)

```typescript
useEffect(() => {
  loadAd('rewarded'); // 보상형 광고 먼저 로드

  return () => {
    cleanupRef.current?.();  // cleanup
    clearAllTimers();        // 타이머 정리
  };
}, []);
```

**동작:**
- 백그라운드에서 광고 로드
- 사용자는 인트로 화면 탐색 가능
- 로드 실패 시 자동 재시도

#### 2. 사진 선택 시 (광고 표시)

```typescript
const requestGeneration = () => {
  // 광고가 아직 로드 중인 경우
  if (adLoaded === false) {
    setStep('loading');      // 로딩 화면 표시
    setWaitingForAd(true);   // 광고 대기 중 표시

    // 최대 10초 대기 후 광고 없이 진행
    setTimeout(() => {
      if (!adLoaded) {
        generateProfile(); // 광고 없이 진행
      }
    }, 10000);
    return;
  }

  // 광고가 이미 로드된 경우 바로 표시
  showAd();
};
```

**UX 개선 포인트:**
- 로딩 화면을 먼저 표시하여 화면이 멈춘 것처럼 보이지 않음
- 광고 로드 실패해도 최대 10초 후 서비스 이용 가능

#### 3. 광고 시청 완료

**보상형 광고:**
```typescript
case 'userEarnedReward':
  rewardEarnedRef.current = true; // 보상 획득
  break;

case 'dismissed':
  if (rewardEarnedRef.current) {
    generateProfile(); // 프로필 생성 진행
  } else {
    setError('광고를 끝까지 시청해주세요');
  }
  break;
```

**전면형 광고:**
```typescript
case 'dismissed':
  generateProfile(); // 바로 프로필 생성 진행
  break;
```

#### 4. 광고 이벤트

```typescript
GoogleAdMob.showAppsInTossAdMob({
  options: { adGroupId },
  onEvent: (event) => {
    switch (event.type) {
      case 'requested':       // 광고 표시 요청됨
      case 'show':            // 광고 컨텐츠 표시 시작
      case 'impression':      // 광고 노출 완료 (수익 발생)
      case 'clicked':         // 광고 클릭됨
      case 'userEarnedReward': // 보상 획득 (보상형만)
      case 'dismissed':       // 광고 닫힘
      case 'failedToShow':    // 광고 표시 실패
    }
  },
  onError: (error) => {
    // 광고 표시 에러 처리
  }
});
```

### 광고 동작 플로우 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                        앱 시작                               │
└────────────────────────┬────────────────────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  보상형 광고 로드     │
              │  (백그라운드)        │
              └──────────┬───────────┘
                         ↓
                    성공? ──→ 예 ──→ adLoaded = true
                         │
                         ↓ 아니오
                    재시도 (1초 후)
                         ↓
                    성공? ──→ 예 ──→ adLoaded = true
                         │
                         ↓ 아니오
                    재시도 (3초 후)
                         ↓
                    성공? ──→ 예 ──→ adLoaded = true
                         │
                         ↓ 아니오
              ┌──────────────────────┐
              │  전면형 광고 로드     │
              └──────────┬───────────┘
                         ↓
              재시도 3회 (1초, 3초, 5초)
                         ↓
              성공 → adLoaded = true
              실패 → 광고 없이 진행

┌─────────────────────────────────────────────────────────────┐
│                     사용자가 사진 선택                        │
└────────────────────────┬────────────────────────────────────┘
                         ↓
                   광고 로드됨?
                         │
         ┌───────────────┴───────────────┐
         ↓ 아니오                         ↓ 예
   로딩 화면 표시                    광고 표시
   (10초 대기)                          ↓
         │                    ┌──────────┴──────────┐
         ↓                    ↓                     ↓
   광고 로드 완료?        보상형 광고          전면형 광고
         │                    ↓                     ↓
         ↓ 타임아웃      끝까지 시청?            닫힘?
   광고 없이 진행              │                     │
                        ↓ 예    ↓ 아니오            ↓
                   프로필 생성  에러 표시      프로필 생성
```

---

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
# 프로젝트 루트로 이동
cd react-vite-app

# 패키지 설치
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 자동으로 열립니다: `http://localhost:5173`

**개발 모드 특징:**
- ⚡ Hot Module Replacement (HMR) 지원
- 🔄 파일 수정 시 자동 새로고침
- 🐛 소스맵 지원 (디버깅 용이)

### 3. 빌드

```bash
npm run build
```

**빌드 결과:**
- `dist/` 폴더에 최적화된 파일 생성
- `ai-photo-studio.ait` 파일 생성 (토스 앱 배포용)

### 4. 빌드 미리보기

```bash
npm run preview
```

프로덕션 빌드를 로컬에서 테스트할 수 있습니다.

---

## 🔧 환경 변수

`.env` 파일을 생성하여 설정을 변경할 수 있습니다.

### 환경 변수 목록

```env
# API 엔드포인트
VITE_API_URL=https://yourgooglecloud-xxxx.us-central1.run.app

# API 요청 타임아웃 (밀리초)
VITE_REQUEST_TIMEOUT_MS=90000

# API 재시도 설정
VITE_REQUEST_RETRY_LIMIT=3        # 최대 재시도 횟수
VITE_REQUEST_RETRY_DELAY_MS=3000  # 재시도 간격 (밀리초)
```

### 환경 변수 사용 예시

```typescript
// 환경 변수 읽기
const metaEnv = (import.meta as { env?: Record<string, string> }).env ?? {};
const apiUrl = metaEnv.VITE_API_URL || DEFAULT_API_URL;
const timeoutMs = parseNumberEnv(
  metaEnv.VITE_REQUEST_TIMEOUT_MS,
  DEFAULT_REQUEST_TIMEOUT_MS
);
```

**주의사항:**
- `VITE_` 접두사 필수 (Vite 규칙)
- `.env` 파일은 Git에 커밋하지 않음 (`.gitignore` 포함)
- 기본값이 코드에 정의되어 있어 `.env` 없이도 동작

---

## 📦 빌드 및 배포

### 프로덕션 빌드

```bash
npm run build
```

**빌드 프로세스:**
1. TypeScript 컴파일
2. 코드 번들링 및 최적화
3. CSS 압축
4. 이미지 및 정적 파일 복사
5. `dist/` 폴더에 결과물 생성
6. `ai-photo-studio.ait` 파일 생성 (토스 앱용)

### 빌드 결과물

```
dist/
├── index.html                    # 메인 HTML
├── assets/
│   ├── index-[hash].js          # 번들된 JavaScript (~1.15MB)
│   └── index-[hash].css         # 번들된 CSS (~0.13KB)
└── [기타 정적 파일]

ai-photo-studio.ait              # 토스 앱 배포 파일
```

### 토스 앱에 배포

**1단계: QR 코드 스캔**

빌드 완료 후 터미널에 QR 코드가 표시됩니다.

**2단계: 토스 앱에서 실행**

1. 토스 앱 실행
2. QR 코드 스캔
3. 앱이 토스 내에서 실행됨

**3단계: 테스트**

- 사진 선택 기능
- 광고 로드 및 표시
- 프로필 생성
- 에러 처리

### 프로덕션 체크리스트

배포 전 확인사항:

- [ ] 실제 광고 ID로 변경 (`AD_GROUP_IDS`)
- [ ] 광고 ID 형식 확인 (`ait.live.xxxxx`)
- [ ] API 엔드포인트 확인 (`.env` 또는 코드)
- [ ] 빌드 에러 없음
- [ ] 토스 앱에서 동작 확인
- [ ] 광고 노출 확인
- [ ] 에러 핸들링 테스트

---

## 🐛 문제 해결

### 광고 관련

#### Q1. 광고가 표시되지 않아요

**원인 1: 개발 환경**
- 로컬 브라우저에서는 광고가 표시되지 않을 수 있습니다
- 해결: 토스 앱에서 테스트

**원인 2: 광고 ID 오류**
- 잘못된 광고 ID 사용
- 해결: 테스트 ID 사용 (`ait-ad-test-rewarded-id`, `ait-ad-test-interstitial-id`)
- 또는 앱스인토스 콘솔에서 발급받은 `ait.live.xxxxx` 형식 ID 사용

**원인 3: 광고 인벤토리 부족**
- 앱스인토스에 광고가 없을 수 있음
- 해결: 앱은 광고 없이도 동작하도록 설계됨 (10초 후 자동 진행)

#### Q2. "광고 로드 실패" 에러가 계속 나와요

**해결:**
- 콘솔 로그 확인: `console.log('📥 [보상형] 광고 로드 시도 1회')`
- 재시도 로그 확인: `console.warn('⏱️ 1초 후 보상형 광고 재시도')`
- 3회 재시도 후 전면형으로 전환됨
- 전면형도 실패하면 광고 없이 진행

#### Q3. 광고 ID 형식이 헷갈려요

**앱스인토스 광고 ID:**
- ✅ 형식: `ait.live.xxxxx` 또는 `ait-ad-test-xxxxx`
- ✅ 예시: `ait.live.eb562973a6ac4acb`
- ✅ 발급처: [앱스인토스 콘솔](https://apps-in-toss.toss.im/)

**Google AdMob ID (사용하지 않음):**
- ❌ 형식: `ca-app-pub-xxxxx~xxxxx`
- ❌ 이 프로젝트에서는 **사용하지 않습니다**

### 이미지 관련

#### Q4. 이미지 압축이 너무 오래 걸려요

**원인:**
- 원본 이미지가 너무 큼 (10MB 이상)

**해결:**
```typescript
// IMAGE_COMPRESSION_OPTIONS 수정 (ProfilePage.tsx 49-53줄)
const IMAGE_COMPRESSION_OPTIONS = {
  maxSizeMB: 0.5,           // 1MB → 0.5MB로 감소
  maxWidthOrHeight: 256,    // 512px → 256px로 감소
  useWebWorker: true,       // Web Worker 사용 유지
} as const;
```

#### Q5. 이미지 품질이 떨어져요

**해결:**
```typescript
// 품질 설정 조정
const IMAGE_COMPRESSION_OPTIONS = {
  maxSizeMB: 2,             // 제한 완화
  maxWidthOrHeight: 1024,   // 해상도 증가
  useWebWorker: true,
  initialQuality: 0.9,      // 품질 추가 (0.9 = 90%)
} as const;
```

### API 관련

#### Q6. "요청 시간이 너무 오래 걸려 중단되었어요" 에러

**원인:**
- API 서버 응답 느림
- 네트워크 불안정

**해결:**
```env
# .env 파일에서 타임아웃 증가
VITE_REQUEST_TIMEOUT_MS=180000  # 90초 → 180초
```

#### Q7. API 요청이 계속 실패해요

**확인사항:**
1. API URL 확인
   ```typescript
   console.log('API URL:', apiUrl);
   ```
2. 네트워크 탭에서 요청 확인 (F12 → Network)
3. 서버 상태 확인

### 빌드 관련

#### Q8. 빌드 시 "chunks are larger than 500 kB" 경고

**해결:**
- 경고일 뿐, 동작에는 문제 없음
- 성능 최적화를 원하면 코드 스플리팅 고려

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom'],
          'compression': ['browser-image-compression'],
        }
      }
    }
  }
});
```

#### Q9. TypeScript 에러

**해결:**
```bash
# 타입 체크
npx tsc

# 특정 에러 무시 (권장하지 않음)
// @ts-ignore
```

### 기타

#### Q10. 개발 서버가 느려요

**해결:**
```bash
# 캐시 삭제
rm -rf node_modules/.vite

# 재시작
npm run dev
```

#### Q11. 뒤로가기 버튼이 작동하지 않아요

**설명:**
- 토스 앱의 네비게이션 바 백버튼은 항상 앱을 종료합니다
- 화면 간 이동은 각 화면의 버튼 사용:
  - 로딩 화면: "취소" 버튼
  - 결과 화면: "처음으로" 버튼

---

## 👨‍💻 개발 가이드

### 디버깅

#### 1. 콘솔 로그 활용

코드에 유용한 로그가 포함되어 있습니다:

```typescript
// 광고 로드
console.log('📥 [보상형] 광고 로드 시도 1회');
console.log('✅ 보상형 광고 로드 완료');

// 재시도
console.warn('⏱️ 1초 후 보상형 광고 재시도 (1/3)');

// 에러
console.error('❌ 보상형 광고 로드 실패', error);
```

브라우저 개발자 도구 (F12) → Console 탭에서 확인

#### 2. React DevTools

Chrome 확장 프로그램 설치:
- [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)

**사용법:**
- Components 탭: 컴포넌트 트리 및 Props/State 확인
- Profiler 탭: 렌더링 성능 측정

#### 3. 네트워크 디버깅

F12 → Network 탭:
- 이미지 업로드 요청 확인
- API 응답 시간 측정
- 에러 응답 내용 확인

### 코드 수정 가이드

#### 새로운 화면 추가하기

**1단계: Step 타입에 추가**
```typescript
type Step = 'intro' | 'loading' | 'result' | 'error' | 'preview'; // 'preview' 추가
```

**2단계: 컴포넌트 작성**
```typescript
// src/components/Preview.tsx
export default function Preview({ imageUrl, onConfirm, onCancel }) {
  return (
    <div>
      <img src={imageUrl} alt="Preview" />
      <button onClick={onConfirm}>확인</button>
      <button onClick={onCancel}>취소</button>
    </div>
  );
}
```

**3단계: 렌더링 로직 추가**
```typescript
if (step === 'preview') {
  return (
    <Preview
      imageUrl={previewUrl}
      onConfirm={() => setStep('loading')}
      onCancel={() => setStep('intro')}
    />
  );
}
```

#### 상태 추가하기

```typescript
// 새로운 상태 추가
const [previewUrl, setPreviewUrl] = useState('');

// 사용
const handleFileSelect = async (file: File) => {
  const url = URL.createObjectURL(file);
  setPreviewUrl(url);
  setStep('preview');
};
```

### 성능 최적화

#### 1. 이미지 최적화

```typescript
// 더 작은 썸네일 사용
const photos = await fetchAlbumPhotos({
  maxCount: 1,
  maxWidth: 64,  // 128 → 64로 감소
  base64: true,
});
```

#### 2. 메모이제이션

```typescript
import { useMemo, useCallback } from 'react';

// 값 메모이제이션
const compressedOptions = useMemo(() => ({
  maxSizeMB: 1,
  maxWidthOrHeight: 512,
}), []);

// 함수 메모이제이션
const handleFile = useCallback(async (file: File) => {
  // ...
}, []);
```

#### 3. 코드 스플리팅

```typescript
// 동적 import
const Result = lazy(() => import('./components/Result'));

// Suspense로 감싸기
<Suspense fallback={<Loading />}>
  <Result imageUrl={imageUrl} />
</Suspense>
```

### 테스트

#### 수동 테스트 체크리스트

- [ ] 앨범에서 사진 선택
- [ ] 카메라로 사진 촬영
- [ ] 파일 선택
- [ ] 광고 로드 및 시청
- [ ] 프로필 생성 성공
- [ ] 에러 처리 (네트워크 끊기)
- [ ] 뒤로가기 동작
- [ ] 여러 번 반복 사용

---

## 📚 참고 자료

### 공식 문서

- [React 공식 문서](https://react.dev)
- [TypeScript 핸드북](https://www.typescriptlang.org/docs/)
- [Vite 가이드](https://vitejs.dev/guide/)
- [앱스인토스 개발자 문서](https://developers-apps-in-toss.toss.im/)
- [앱스인토스 광고 SDK](https://static.toss.im/tossdev/sdk/apps-in-toss-web-sdk-docs/index.html)

### 주요 라이브러리

- [browser-image-compression](https://github.com/Donaldcwl/browser-image-compression)
- [React Simplikit](https://github.com/toss/react-simplikit)

### 학습 자료

전체 학습 가이드는 프로젝트 루트의 [README.md](../README.md)를 참고하세요.

---

## 🔑 핵심 파일

### 1. ProfilePage.tsx

메인 로직이 구현된 파일:
- 광고 로드 (`loadAd`)
- 광고 표시 (`requestGeneration`, `showAd`)
- 프로필 생성 (`generateProfile`)

### 2. IntroScreen.tsx

인트로 화면 컴포넌트:
- 사진 선택 버튼
- 에러 표시

### 3. Loading.tsx

로딩 화면 컴포넌트:
- 광고 로드 대기 중 표시
- 프로필 생성 중 표시
- 취소 버튼

### 4. ErrorState.tsx

에러 화면 컴포넌트:
- 광고 또는 생성 실패 시 표시

### 5. Result.tsx

결과 화면 컴포넌트:
- 생성된 프로필 표시
- 다운로드 기능
- "처음으로" 버튼

---

## 🤝 기여하기

버그 제보나 기능 제안은 Issue로 등록해주세요.

---

## 📄 라이센스

MIT License

---

## 📞 문의

기술 문의나 질문이 있으시면 Issue를 통해 연락주세요.
