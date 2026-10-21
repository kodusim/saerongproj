# saerongproj — 새롱 데이터 스튜디오 · TDM

## 2026-10-21 여행 서비스 재설계·배포

공개 메인과 `/travel`을 실제 여행 기록 탐색 화면으로 재구성하고 사용자 요청으로 운영에 배포했다. AI허브 2023 네 권역 CSV를 집계한 2,483개 장소의 검색·지도·표본/만족도 비교·브라우저 여행 노트를 제공한다. 원본과 집계 카탈로그는 Git에서 제외되므로 다른 PC에서는 데이터를 별도로 준비해야 한다. [조사·설계·데이터 재생성 방법](docs/TRAVEL_REDESIGN.md)을 참고한다.

다른 PC에서 작업을 이어갈 때는 [인계 문서](docs/HANDOFF.md)와 [로컬 환경 설정 예시](deploy/local.env.example)를 먼저 확인한다. 비밀키·메일 설정·관리자 접속정보·원본 데이터는 GitHub에 포함하지 않는다.

반코마이신 혈중 농도를 예측하는 FastAPI 애플리케이션이다. 2026-10-09 사용자 요청으로 TDM 외 서비스 코드와 제품·브랜드 문서를 정리했고, 2026-10-10 사용자 요청으로 saerong.com에 배포했다.

2026-10-21 사업 소개, 여행 탐색 서비스, 포트폴리오와 비공개 문의 접수 기능을 saerong.com에 배포했다. 각 메뉴는 별도 URL에서 서버 렌더링한다. 포트폴리오는 제공된 작업 자료의 주제를 바탕으로 재구성했으며 화면은 합성 데이터를 사용한다. 문의는 먼저 비공개 SQLite에 저장하고 SMTP로 알린다. 관리자 인증은 TDM과 분리한다.

여행 서비스는 AI허브 네 권역 **원본 CSV의 장소별 집계**와 자체 작성한 지역 가이드를 제공한다. 만족도는 과거 관측 통계이며 학습 모델의 예측이 아니다. 운영 사이트에도 동일한 집계 카탈로그를 연결했다.

## 경로

| 경로 | 기능 |
|---|---|
| `/` | 공개서비스 메인 |
| `/portfolio/` | 외주 포트폴리오 |
| `/services/` | 데이터 분석·웹서비스 개발 소개 |
| `/travel` | 여행 취향 선택·권역 필터·저장·비교·공유 |
| `/travel/{slug}` | 여행지별 가이드와 공식 정보 링크 |
| `/portfolio/{slug}/` | 사례 설명과 합성 데이터 대시보드 |
| `/contact/` | 문의 내용 확인 후 비공개 접수·메일 알림 |
| `/admin/` | 전용 관리자 로그인 후 문의 조회·처리·삭제 |
| `/privacy/`, `/terms/`, `/about/` | 정책·이용안내·소개 |
| `/ads.txt`, `/robots.txt`, `/sitemap.xml` | 광고·검색 설정 |
| `/tdm/` | 로그인 후 ML + DL 예측 화면 |
| `/tdm/login/`, `/tdm/logout/` | 세션 인증 |
| `/tdm/api/predict/` | 예측 API와 감사 로그 저장 |
| `/tdm/logs/` | 최근 200개 감사 로그 조회 |
| `/tdmprediction/*` | 요청 메서드를 유지하는 308 리디렉션 |
| `/healthz` | 헬스체크 |

## 구성과 실행

- `app/routers/site.py`: 공개 페이지, 문의 API, 관리자 인증
- `app/services/site_content.py`: 공개 여행 가이드·통계·포트폴리오 콘텐츠
- `templates/site/`, `static/css/public.css`, `static/js/{public,travel,dashboard}.js`: 실제 배포 화면
- `preview/`, `templates/home.html`, `static/css/site.css`, `static/js/site.js`: 초기 로컬 시안; 현재 라우트에서는 사용하지 않음
- `app/services/inquiries.py`: 문의 보관·알림·남용 제한, TDM DB와 분리
- `.site.env`, `private_data/`: 비공개 설정·런타임 데이터, Git/배포 아카이브 제외

- `app/routers/tdm.py`: TDM 라우터
- `app/services/predictor.py`: ML + DL 추론
- `app/models.py`: 기존 `tdm_predictionlog` 테이블 매핑
- `app/security.py`: 세션 인증과 CSRF
- `templates/tdm/`, `static/css/tdm-*`, `static/js/tdm/`: TDM 화면
- `ml_artifacts/`: 모델 파일과 메타데이터. 가중치는 Git 추적에서 제외한다.

Python 가상환경에서 다음 명령으로 설치하고 실행한다.

```sh
pip install -r requirements.txt
pip install -r requirements/dev.txt
uvicorn app.main:app --reload
```

기존 `.env`에서 DB 연결·세션·TDM 인증 설정을 읽는다. 로컬 개발 시 `DEBUG=True`이면 정적 파일과 `/api/docs`를 앱이 제공한다. 운영에서는 nginx가 정적 파일을 제공한다. PyTorch CPU 빌드는 `requirements/common.txt`의 설치 안내를 참고한다.

## 데이터와 검증

TDM 모델·인증 설정·DB·업로드 및 기존 로컬 데이터는 초기화하지 않았다. 기존 DB의 리비전 연결을 깨뜨리지 않도록 `migrations/versions/` 이력은 유지한다. 과거 비TDM 테이블은 현재 ORM에서 제외했으며 Alembic 자동 생성 시 삭제 대상으로 잡히지 않도록 필터링한다. 기존 마이그레이션에는 과거 테이블 생성 코드가 남아 있다.

```sh
python -m pytest -q -p no:cacheprovider
git diff --check
```

라우트 테스트는 DB 의존성을 대체하며 실제 DB 연결이나 모델 추론을 실행하지 않는다. 운영 관련 사항은 [deploy/README.md](deploy/README.md), 작업 지침은 [AGENTS.md](AGENTS.md)를 참고한다.

문의 테스트는 임시 SQLite와 발송을 하지 않는 격리 설정을 사용한다. 문의 및 로그인 남용 제한, CSRF, 전용 관리자 인증, 입력 검증, 중복 접수 방지, HTML 이스케이프와 SMTP 실패 시 보존을 검증한다.

## 광고와 원본 데이터 연결 상태

- 공개서비스(`/`, `/travel`, 여행 상세)에는 제공받은 AdSense 스크립트와 소유권 메타 태그를 적용했다. 관리자·문의·포트폴리오에는 광고를 삽입하지 않는다.
- AdSense 사이트 재검토, 자동광고 활성화와 Google 인증 CMP 메시지 게시 등 **계정 측 설정은 미완료**다. 광고 승인·노출·수익을 검증 완료로 주장하지 않는다.
- AI허브는 실시간 추천 API가 아니라 승인 후 파일을 내려받는 API를 제공한다. `scripts/aihub_file_catalog.py`는 네 데이터셋 파일 목록만 조회하며 비밀키를 받거나 데이터를 다운로드하지 않는다.
- 승인받은 CSV를 로컬에 확보하고 장소 단위 기술통계를 연결했다. 재생성은 `scripts/download_travel_data.py`, `scripts/build_travel_catalog.py`를 사용한다. 개인별 추천 모델은 아직 학습하지 않았다.
