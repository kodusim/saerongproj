## AI Photo Studio 통합 가이드

AI Photo Studio는 사용자가 업로드한 셀피를 Google Gemini를 활용해 고품질의 프로필 사진으로 변환하는 서비스입니다. 이 문서는 프론트엔드(`react-vite-app/`)와 GCP 백엔드(`ai-photo-studio-backend/`)를 하나의 제품으로 운영하기 위한 구조, 배포, 운영 전략을 정리합니다.

---

### 프로젝트 개요
- **목표**: 토스 인앱 환경에서 동작하는 AI 기반 프로필 사진 생성 서비스 제공
- **구성**: React + Vite로 구현된 프론트엔드와 Google Cloud Functions 기반의 Node.js 백엔드
- **주요 기능**
  - 이미지 선택(앨범/카메라/파일) 및 압축 후 업로드
  - 광고 시청 플로우(보상형/전면형) 연동
  - GCP 백엔드에 이미지 전송 → Gemini 모델로 프로필 이미지 생성 → Base64 URL 반환

---

### 프론트엔드 개요 (`react-vite-app/`)
- **기술 스택**: React 18, TypeScript, Vite 5, Toss In-App SDK
- **주요 진입점**: `src/pages/ProfilePage.tsx`
  - 이미지 선택, 광고 로딩, AI 요청, 결과 화면까지의 전 플로우 관리
  - `GoogleAdMob`을 통해 광고 로드 및 이벤트 처리
- **AI 호출 방식**
  - `FormData`로 이미지 파일 업로드 → `VITE_API_URL` 환경 변수 기반으로 백엔드 호출
  - 타임아웃 및 재시도 로직 내장 (기본 90초, 3회 재시도)
- **빌드 산출물**: `dist/` 및 `ai-photo-studio.ait`
  - 토스 앱 배포 시 `ai-photo-studio.ait` 파일을 업로드

---

### 백엔드 개요 (`ai-photo-studio-backend/`)
- **런타임**: Node.js 20 이상, Express
- **핵심 파일**
  - `index.js`: Cloud Functions 진입점(`module.exports.helloHttp`)과 앱 로직
  - `package.json`: 필수 의존성 및 `npm start` 스크립트(로컬 디버깅용)
- **주요 엔드포인트**
  - `POST /api/generate`: multipart/form-data로 이미지 업로드 → Gemini API 호출 → Base64 Data URI 응답
  - `GET /health`: 상태 확인용
- **Gemini 통합**
  - `@google/genai` SDK 사용, `GEMINI_API_KEY` 환경 변수 필요
  - `gemini-2.5-flash-image` 모델과 3:4 비율 설정 활용
- **배포 형태**
  - GCP Cloud Functions(HTTP 트리거)에서 index.js와 package.json을 그대로 붙여넣어 실행 가능

---

### 프로젝트 구조
```
ai-photo-studio/
├── README.md                         # 통합 가이드 (현재 문서)
├── react-vite-app/                   # 프론트엔드 소스
│   ├── src/
│   │   ├── pages/ProfilePage.tsx     # 서비스 메인 화면 및 로직
│   │   ├── components/               # 화면 단위 컴포넌트
│   │   └── ...
│   ├── granite.config.ts             # Toss 인앱 설정
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
└── ai-photo-studio-backend/          # GCP Cloud Functions 백엔드
    ├── index.js                      # Express 앱 및 함수 핸들러
    ├── package.json                  # 백엔드 의존성
    └── ...
```

---

### 로컬 개발 워크플로
1. **프론트엔드 준비**
   ```bash
   cd react-vite-app
   npm install
   npm run dev
   ```
   - 기본 개발 서버: `http://localhost:5173`
   - Toss 인앱 기능 테스트 시 실제 디바이스 또는 Toss 개발 환경 필요

2. **백엔드 준비 (선택적 로컬 테스트)**
   - Cloud Functions 특성상 `index.js`가 서버를 직접 기동하지 않으므로 `functions-framework`를 사용합니다.
   ```bash
   cd ai-photo-studio-backend
   npm install
   npx functions-framework --target=helloHttp --port=8080
   ```
   - 로컬 실행 시 환경 변수 `GEMINI_API_KEY`를 셸에서 설정하고 실행하세요.

3. **프론트엔드 ↔ 백엔드 연동**
   - `react-vite-app/.env`에 로컬 함수 주소 지정: `VITE_API_URL=http://localhost:8080`
   - 프론트엔드에서 이미지 업로드 시 로컬 백엔드를 호출해 흐름 검증 가능

---

### GCP(Google Cloud) 배포 전략
1. **Cloud Functions (HTTP) 배포**
   - 콘솔 > Cloud Functions > 함수 만들기
   - **트리거**: HTTP
   - **런타임**: Node.js
   - **소스 코드**: 인라인 편집기 선택 후 `index.js`, `package.json` 내용을 각각 붙여넣기
   - **엔트리 포인트**: `helloHttp`
   - **환경 변수**: `GEMINI_API_KEY` 설정
   - 배포 완료 후 생성된 HTTPS URL을 프론트엔드 `.env`의 `VITE_API_URL`로 사용

2. **Toss 인앱 배포**
   - 프론트엔드에서 `npm run build` → `ai-photo-studio.ait` 산출물 업로드
   - 광고 ID를 실환경 값(`ait.live.*`)으로 교체 후 배포

---

### 환경 변수 및 보안 설정
- **프론트엔드** (`react-vite-app/.env`)
  - `VITE_API_URL`: Cloud Functions/Run 배포 주소 (예: `https://<region>-<project>.cloudfunctions.net/helloHttp`)
  - `VITE_REQUEST_TIMEOUT_MS`, `VITE_REQUEST_RETRY_LIMIT`, `VITE_REQUEST_RETRY_DELAY_MS`: 요청 제어 파라미터
- **백엔드** (`ai-photo-studio-backend`)
  - `GEMINI_API_KEY`: Google AI Studio에서 발급받은 API 키 (필수)
  - GCP 콘솔 > 함수 설정 > 환경 변수에 안전하게 저장
- **보안 권장사항**
  - API 키는 Secret Manager를 사용해 관리하고 함수에는 비공개 변수를 참조시키는 것을 권장
  - CORS 허용 오리진은 실제 배포 도메인으로 최소화

---

### 데이터 플로우
1. 사용자가 프론트엔드에서 사진을 선택하고 광고 시청을 완료합니다.
2. 선택된 이미지는 브라우저에서 1MB/512px 이하로 압축됩니다.
3. 프론트엔드가 `POST /api/generate` 요청을 보냅니다.
4. 백엔드는 Busboy로 이미지를 파싱하고, MIME 타입과 크기를 검증합니다.
5. `@google/genai` SDK를 통해 Gemini 모델에 프롬프트와 이미지를 전달합니다.
6. 스트리밍 응답에서 Base64 인라인 이미지를 추출해 `data:image/jpeg;base64,...` 형식으로 반환합니다.
7. 프론트엔드는 결과 이미지를 표시하고, 사용자가 다운로드/재시도를 선택할 수 있습니다.

---

### 테스트 및 점검 체크리스트
- **프론트엔드**
  - [ ] 이미지 선택 3종(앨범/카메라/파일) 정상 동작
  - [ ] 광고 로드 및 시청 후 AI 요청 진행
  - [ ] 네트워크 장애 시 재시도/에러 UI 출력
- **백엔드**
  - [ ] `/health` 응답 확인
  - [ ] 大용량 이미지(>10MB) 업로드 차단 확인
  - [ ] 지원되지 않는 MIME 타입 업로드 시 415 응답 확인
  - [ ] Gemini API 오류 시 500 응답 및 로그 확인
- **통합**
  - [ ] 실제 Cloud Functions URL과 연동 테스트
  - [ ] 프로필 이미지가 Base64로 반환되어 UI에 표시되는지 확인
  - [ ] 광고 ID를 실환경 값으로 바꾼 뒤 QA 진행

---

### 트러블슈팅
- **경고: "Some chunks are larger than 500 kB" (Vite 빌드)**
  - 성능 최적화를 위해 `vite.config.ts`에서 `manualChunks` 설정 고려
  - 경고만으로 배포에는 영향 없음
- **이미지 업로드 실패**
  - 프론트엔드 콘솔에서 `REQUEST_TIMEOUT` 로그 확인 후 백엔드 로그 검토
  - Cloud Functions 로그에서 `Generation error` 레코드 확인
- **Gemini API 키 미설정**
  - 함수 배포 시 `GEMINI_API_KEY` 환경 변수가 누락되면 500 에러 발생
  - Secret Manager와 연동해 자동 주입 가능
- **CORS 오류**
  - `index.js`의 `getAllowedOrigins()` 목록에 실제 프론트엔드 도메인을 추가

---

### 부록: 주요 명령어 정리
- 프론트엔드 개발 서버
  ```bash
  cd react-vite-app
  npm run dev
  ```
- 프론트엔드 빌드/미리보기
  ```bash
  npm run build
  npm run preview
  ```
- 백엔드 로컬 실행 (Functions Framework)
  ```bash
  cd ai-photo-studio-backend
  npm install
  npx functions-framework --target=helloHttp --port=8080
  ```
- Cloud Functions 배포(Cloud SDK 사용 예시)
  ```bash
  gcloud functions deploy ai-photo-studio \
    --region=asia-northeast3 \
    --runtime=nodejs20 \
    --entry-point=helloHttp \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars GEMINI_API_KEY=YOUR_KEY
  ```

이 가이드를 기반으로 프론트엔드와 백엔드를 일관성 있게 관리하고, GCP 환경에 안정적으로 배포할 수 있습니다. 추가 질문이나 개선사항은 프로젝트 이슈 트래커를 통해 공유해주세요.
