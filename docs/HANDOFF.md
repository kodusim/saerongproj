# 새 PC에서 이어서 작업하기

## 추가 작업 — 여행 탐색 재설계 (로컬, 운영 미반영)

2026-10-21 사용자 요청으로 공개 메인과 여행 서비스를 재설계했다. `AIHUB_API_KEY`를 확인했고 네 권역 CSV 다운로드에 성공했다. 아래의 이전 “승인 대기” 기록은 해소됐다. 현재 로컬은 방문 기록 140,555건을 집계한 2,483개 장소를 연결한다. 검색·지도·비교·여행 노트·집계 CSV 내보내기를 제공하며 AI 모델 추천으로 표현하지 않는다.

새 PC에서는 `private_data/travel/catalog.json`을 별도로 옮기거나 [재생성 절차](TRAVEL_REDESIGN.md)를 따른다. 원본과 키를 Git에 넣지 않는다. 기존 운영 사이트는 아래 배포 당시 상태이며 이번 변경의 푸시·배포는 아직 수행하지 않았다.

기준: 2026-10-21. 실제 운영 사이트는 https://saerong.com 이다.

## 코드 받기와 로컬 실행

```sh
git clone https://github.com/kodusim/saerongproj.git
cd saerongproj
git switch main
python -m venv .venv
```

Windows PowerShell에서는 `.venv\Scripts\Activate.ps1`, macOS/Linux에서는 `source .venv/bin/activate`로 가상환경을 활성화한다.

```sh
pip install -r requirements/dev.txt
```

`deploy/local.env.example`을 루트 `.env`로 복사한 뒤 실행한다. 이 예시는 실제 DB에 연결하지 않도록 설정되어 있다.

```sh
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest -q -p no:cacheprovider
git diff --check
```

`http://127.0.0.1:8000`에서 공개 페이지를 확인한다. 여행 탐색·포트폴리오·문의 보관함은 TDM DB와 모델 없이 실행할 수 있다. TDM의 실제 추론은 별도로 전달받은 모델과 개발용 DB가 필요하며 운영 DB로 테스트하지 않는다.

새 PC의 `.env`에 SMTP 정보를 설정하지 않으면 메일은 발송되지 않고 문의만 로컬 `private_data/inquiries.sqlite3`에 저장된다. `DEBUG=true`이고 관리자 해시 설정이 없는 로컬 모드에서는 예시의 TDM 계정으로 `/admin/`에 로그인할 수 있다. 운영에서는 이 대체 로그인이 차단된다.

## 기존 운영 구현 (이번 로컬 재설계 전)

- `/`: 공개서비스 메인, 중앙 메뉴, 로컬 Pretendard 폰트.
- `/travel`: 12개 여행 가이드, 취향 태그 비교, 4권역 필터, 브라우저 저장, 최대 3곳 비교, 조건 공유.
- `/travel/{slug}`: 지역별 가이드와 공식 관광 정보·지도 링크.
- `/portfolio/`: 기존 자료의 6개 주제를 개인정보 없이 재구성. 상세 페이지는 합성 데이터 대시보드·CSV 다운로드 제공.
- `/services/`: 제공 범위·진행 과정·FAQ.
- `/contact/`: 확인 후 접수, 서버 입력 검증·CSRF·중복 방지·횟수 제한, 비공개 저장 후 SMTP 알림.
- `/admin/`: 전용 비밀번호 해시와 별도 세션, 문의 조회·상태 변경·삭제.
- AdSense 코드·소유권 메타 태그·ads.txt·사이트맵·canonical·OG·구조화 데이터.
- 기존 `/tdm/`과 `/tdmprediction/*` 리디렉션 유지.

현재 소스는 `app/routers/site.py`, `app/services/{site_content,inquiries}.py`, `templates/site/`, `static/css/public.css`, `static/js/{public,travel,dashboard}.js`다. `preview/`와 `templates/home.html`, `static/css/site.css`, `static/js/site.js`는 이전 시안이며 운영 라우트에서 사용하지 않는다.

## 이어서 해야 할 일

### 1. AI허브 원본 연결 — 로컬 연결 완료, 운영 반영 대기

키 이름은 **`AIHUB_API_KEY`**다. 과거 기록의 `AI_HUB_API_KEY` 이름도 다운로드 스크립트에서 호환하지만, 현재 PC에서 확인한 이름은 전자다. 키 값은 GitHub에 올리지 않는다. 이전 승인 안내 오류는 해결됐고 네 권역 CSV를 다운로드·집계했다.

| 권역 | 데이터셋 | 학습 CSV filekey | 검증 CSV filekey |
|---|---|---|---|
| 수도권 | 71776 | 539784 | 539787 |
| 동부권 | 71778 | 539795 | 539798 |
| 서부권 | 71779 | 539804 | 539807 |
| 제주·도서 | 71780 | 541667 | 541670 |

파일 번호는 변경될 수 있으므로 `python scripts/aihub_file_catalog.py`로 다시 확인한다. API가 HTTP 502와 함께 유효한 목록 또는 승인 안내 본문을 반환하는 현상도 확인했다. 상태 코드만으로 파일 저장 성공을 판단하지 말고 형식·응답 본문을 검증해야 한다.

CSV만 선택 다운로드했으며 원본은 `private_data/travel/raw/`에 보관한다. 사진·GPS 전체는 다운로드하지 않았다. 로컬 서비스는 원본 집계 기반 탐색이며 운영 사이트는 아직 편집 태그 비교 방식이다. 어느 쪽도 개인별 AI 예측으로 표현하지 않는다. 재생성·품질 기준은 `TRAVEL_REDESIGN.md`를 따른다.

### 2. AdSense 계정 설정

웹 코드와 `/ads.txt`는 배포했으나 Google 계정의 사이트 재검토 요청·자동광고 활성화·인증 CMP 메시지 게시 여부는 확인하지 못했다. 광고 승인·노출·수익을 검증 완료로 주장하지 않는다. 관리자·문의 페이지에는 광고를 넣지 않는다.

### 3. 운영 보안

운영 문의 관리자 계정은 새로 만들었으며 TDM과 분리돼 있다. 기존 TDM 인증 설정은 보존했다. TDM의 기존 계정 보안 검토와 비밀번호 교체는 사용자와 조율한다.

## GitHub에 없는 것

- `.env`, `.site.env`, AI허브 키, SMTP 비밀번호.
- `private_data/admin-access.txt`, `private_data/admin.env`, 문의 SQLite.
- 원본 포트폴리오, 개인 문서, 로컬 출력물, 모델 가중치와 업로드.
- SSH 개인키와 PC별 `saerong` SSH 별칭 설정.

새 장비로 필요한 설정·자격 증명을 이동할 때에는 비밀번호 관리자 등 별도 안전한 수단을 사용한다. Git, 공개 이슈, PR 설명이나 대화 로그에 값을 붙이지 않는다. 운영 문의 DB는 서버에 그대로 있으며 개발을 위해 복사할 필요가 없다.

## 배포와 검증

운영 배포 기록·백업 경로·주의사항은 `deploy/README.md`에 있다. 다음 배포는 사용자의 별도 요청이 필요하다. 서버는 Git HEAD와 실제 배포 파일이 다를 수 있으므로 무작정 `git pull`하지 않는다.

로컬 테스트 22개와 모바일·데스크톱 브라우저 동작, 운영 HTTPS, 문의 메일 발송, 관리자 처리, 기존 TDM 인증·CSRF·리디렉션을 확인했다. 배포 점검용 합성 문의는 확인 후 삭제했으며 실제 사용자 데이터와 TDM DB는 변경하지 않았다.
