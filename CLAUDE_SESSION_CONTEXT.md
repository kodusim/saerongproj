# Claude 세션 인계 (saerongproj)

> 새 세션에서 첫 메시지로 이 문서를 읽어주세요.
> 이 문서는 사용자(전상기, saerong.com 운영자)의 작업 흐름을 끊김 없이 이어가기 위한 컨텍스트입니다.

## 1. 사용자 / 환경

- 사용자: **전상기 (sangki1298@gmail.com)** — saerong.com 단독 운영자
- 작업 디렉토리: `c:\workspace\saerongproj` (Windows 11, PowerShell)
- 로컬 가상환경 없음 — 로컬 검증은 AST 파싱 수준까지만. 실제 검증은 서버에서 한다 (9장 참고).
- Git: `origin = https://github.com/kodusim/saerongproj.git` (push 시 redirect 안내)
- 사용자 스타일: 한국어, 짧고 직설적, 허락 받지 않고 바로 작업 진행 선호 (`"내가 ok 계속 누르기 귀찮은데 허락없이 그냥 다해주면안돼?"`)

## 2. 서버 / 배포

- 서버: **`saerong-instance`** (SSH 별칭, ~/.ssh/config)
  - HostName 15.164.130.99, User ubuntu, AWS EC2
  - Sudo 패스워드 없이 가능 (NOPASSWD 설정됨)
- 프로젝트 경로: **`/srv/course-repo`**
- 가상환경: **`/srv/venv/bin/python`** (sklearn 1.6.1, joblib 1.4.2, numpy 2.2.4, torch 2.7.0+cpu 설치됨)
- DB: PostgreSQL, **`saerong`** DB, user `saerong_user`
  - 접근: `sudo -u postgres psql -d saerong`
- 웹서버: **uvicorn (systemd `saerong` 서비스, 워커 1개) + nginx**
  - `gunicorn` 서비스는 disable 됨 (Django 시절 유물)
  - nginx 설정은 저장소에서 관리: `deploy/nginx-saerong.conf`, `deploy/nginx-websocket.conf`
  - `sites-enabled/default` 는 이제 `sites-available/default` 심볼릭 링크 (전에는 실제 파일이라
    sites-available 만 고쳐도 반영이 안 됐다 — 함정)
- **배포 패턴** (사용자가 별도 지시 없으면 매번 이 흐름):
  ```bash
  git add ... && git commit -m "..." && git push origin main
  ssh saerong-instance "cd /srv/course-repo && sudo git pull \
    && sudo /srv/venv/bin/python -c 'import app.main' \
    && sudo systemctl restart saerong && sleep 2 && systemctl is-active saerong"
  curl -sS -o /dev/null -w "%{http_code}\n" https://saerong.com/healthz
  ```
- **워커는 1개로 고정.** TDM 모델이 워커당 약 470MB (측정값: django 45 → +ML 330 → +torch 95)
  이고, 채팅 WebSocket 브로드캐스트가 프로세스 내부에서 일어난다. 늘리려면 Redis pub/sub 필요.
- 호스트 라우팅: 없음. **`moscom.ai` 는 별도 서버(43.201.131.25) / 별도 저장소로 분리됨** — 이 저장소와 무관.

## 3. 구조 (FastAPI)

**2026-08-24: Django → FastAPI 이전 완료.** 남은 기능은 TDM 과 Work 둘뿐이고 서로 독립적이다.

| 경로 | 라우터 | 내용 |
|---|---|---|
| `/` | `app/main.py` | 랜딩 (`templates/landing.html`) |
| `/tdmprediction/` | `app/routers/tdm.py` | 반코마이신 TDM 하이브리드 예측 |
| `/tdmprediction/logs/` | 〃 | 예측 감사 로그 (Django admin 대체, 읽기전용) |
| `/work/` | `app/routers/work.py` | 실시간 채팅 · 게시판 |
| `/healthz` | `app/main.py` | 헬스체크 |

- **Django admin 은 없다.** `/admin/` 은 404. PredictionLog 는 `/tdmprediction/logs/` 에서 본다.
- 세션: Starlette `SessionMiddleware` (서명 쿠키). CSRF: `csrftoken` 쿠키 + `X-CSRFToken` 헤더
  double-submit — Django 와 호환되게 만들어서 기존 JS 를 안 고쳤다 (`app/security.py`).
- DB 테이블 이름은 Django 것 그대로 (`tdm_predictionlog`, `work_workchatmessage`, `work_workpost`).
  Alembic baseline `0001` 은 **stamp 만** 했다 (테이블이 이미 있으므로).
- **2026-08-26: 구글 스칼라 검색 기능을 통째로 제거했다** (`app/services/scholar.py`,
  `static/js/work/scholar.js`, `static/css/scholar.css`, `/work/api/scholar/`, 좌우 분할
  리사이즈(`resize.js`)까지 함께). `chat-pane` 이 이제 `work-wrap` 전체 폭을 쓴다.

### 프런트 (빌드 도구 없음)

템플릿은 마크업만, CSS/JS 는 `static/` 에서 nginx 가 그대로 서빙한다.

- `static/js/work/` — `main.js`(엔트리) · `state.js`(공유 상태 + 테마/내비 구독) ·
  `chat.js` · `board.js` · `theme.js` · `nav.js` · `unread.js` · `lightbox.js`,
  공용은 `static/js/lib/{dom,api}.js`
- **인라인 `onclick` 금지** — `type="module"` 은 함수를 전역에 노출하지 않는다.
  이벤트는 모듈 안에서 `addEventListener` 로 바인딩할 것 (tdm predict 에서 실제로 깨졌던 부분).
- **초기화 순서 주의** — `main.js` 에서 구독자(chat/board/nav)를 모두 등록한 뒤
  마지막에 `initTheme()` 이 첫 렌더를 트리거한다.
- `/work` 은 그룹웨어 / VS Code 두 테마 DOM 을 둘 다 문서에 두고 한쪽만 보여준다.
  상태는 한 벌, 렌더는 두 벌 — 테마를 바꿔도 화면 상태가 유지되는 이유.
  화면은 넷: `docs`(채팅) · `board`(자료실) · `schedule`(일정 달력) · `notice`(공지사항).
  `nav.js` 의 `TARGETS` 에 [그룹웨어 본문, VS Code 섹션, 그룹웨어 탭, VS Code 탭, VS Code 트리]
  다섯 쌍으로 묶여 있다 — 화면을 추가하려면 여기 한 줄과 DOM 두 벌만 만들면 된다.
- **게시판은 `board.js` 하나를 인스턴스 두 개로 돌린다** (`archiveBoard` / `noticeBoard`).
  DOM id 는 접두사 규칙(`bd-*` / `nt-*`, VS Code 는 `vc-` 붙임)으로 생성하므로,
  새 게시판을 늘리려면 같은 규칙의 DOM 을 만들고 `createBoard()` 를 한 번 더 부르면 된다.
  서버도 테이블을 나누지 않고 `work_workpost.board` 값으로만 가른다.
- **미니게임은 테마별 DOM 을 두 벌 만들지 않는다.** 상태와 타이머를 들고 돌아서
  두 벌에 동시에 그리면 낭비가 크다. `games/index.js` 가 **지금 보이는 테마의 root**
  (`gm-root` / `vc-gm-root`)에만 그리고, 테마가 바뀌면 그쪽으로 remount 한다.
  게임 화면을 떠날 때 `nav.js` 가 `suspendGames()` 로 타이머를 정리한다 —
  안 하면 다른 탭에 가 있어도 게임이 계속 돈다.
  게임을 추가하려면 `games/` 에 `{id, name, icon, desc, create(ctx)}` 를 default export
  하는 파일을 만들고 `index.js` 의 `GAMES` 에 넣으면 된다.
  `persistent: true` 를 주면 '최고 점수'와 '다시 하기'를 감춘다 (농장이 그렇다).
- **`games/stardew/` 는 캔버스 타일 게임**이다. 그래픽은 이미지 파일이 아니라
  `art.js` 가 문자 격자 + 팔레트로 정의해 오프스크린 캔버스에 구운 픽셀아트다.
  **스프라이트 행은 반드시 16칸**이어야 한다 (짧으면 조용히 잘려 그려진다).
  손으로 세지 말고 `repeat()` 로 조립하거나 검사 스크립트를 돌릴 것.
  저장은 `work_gamesave` (owner_ip, game, data) 공용 슬롯을 쓰고, 이 저장만은
  **클라이언트를 믿는다** — 이동·타일 시뮬을 서버에서 돌리는 건 비현실적이라서.
  순위가 걸린 `work_workfarm` 은 여전히 서버가 계산하므로 영향이 없다.
- **농장 게임의 규칙은 전부 서버**(`app/services/farm.py`)에 있다. 시간과 돈 계산을
  클라이언트에 두면 조작이 너무 쉬워서다. 프런트는 상태를 받아 그리고 행동만 보낸다.
  작물은 심은 시각만 저장하고 다 자랐는지는 그때그때 계산한다 — 배치 작업이 없다.
- **`inet` 컬럼을 WHERE 로 비교할 땐 `cast(ip, INET)` 이 필요하다.** PostgreSQL 에
  `inet = varchar` 연산자가 없다. 파이썬 쪽 비교도 asyncpg 가 ipaddress 객체를
  돌려주므로 `str()` 로 맞춰야 한다 (농장 조회가 500 나던 원인).
- **일정은 월 달력**이다. 두 테마가 **같은 마크업**을 쓰고 CSS 로만 스킨을 바꾼다
  (`.sc-cal-*`, VS Code 는 `.vc-calendar` 가 감싸서 덮어쓴다). 달력은 구조가 같아도
  어색하지 않아서 게시판처럼 마크업을 두 벌 만들지 않았다.
- **표 열 너비는 `.gw-table-wrap` 의 CSS 변수(`--w-*`)** 다. 행마다 인라인 스타일을 주면
  재렌더링에 날아가므로 이렇게 했다. `columns.js` 가 헤더에 손잡이를 붙이고 변수만 바꾼다.
  새 열을 추가할 땐 ① CSS 에 변수 정의 ② `.col-x { flex: 0 0 var(--w-x) }` ③ 헤더 span
  ④ 행 렌더 ⑤ `initColumnResize` 의 `cols` 다섯 곳을 모두 손봐야 한다.
- **문서번호는 저장하지 않는다.** `사업기록-00001` 은 messages 배열의 인덱스로 그때그때
  만든다(하단=가장 오래된 글=1번). 메시지를 지우면 번호가 밀린다 — 표시용 일련번호다.
- 채팅은 **WebSocket** (`/work/ws`). 끊기면 2초 폴링으로 강등되고 재연결 시 HTTP 로
  놓친 구간을 따라잡는다. 전송은 이미지 multipart 때문에 HTTP POST 유지.
- `/static` 은 `Cache-Control: no-cache` — ES 모듈이라 옛/새 모듈이 섞이면 깨진다.
- **로컬·서버에 JS 런타임이 없다** (node 없음). JS 는 구문 검사를 못 돌리므로
  import 경로·named export·element ID 존재 여부를 grep 으로 확인하고 브라우저에서 눈으로 볼 것.

### 삭제된 앱 (전부 DB 테이블은 유지 — drop 하지 않음, `git revert` 로 복구 가능)

- **`animal`** (2026-06-08) — 유일하게 DB 테이블 11개까지 drop 했음
- **`moscom`** + `core` 의 `/mosquito-test/` 뷰 집합 (2026-08-24) — moscom.ai 를 별도 서버(43.201.131.25)/별도 저장소로 분리
- **`common`, `core`, `sources`, `collector`, `analytics`, `api`** (2026-08-24) — 서로 연계 없는 독립 프로젝트라 일괄 정리
- **`game_honey_alarm/`** (토스 미니앱 프론트), **`app_in_toss_guide/`**, 각종 `*_GUIDE.md` / `api_guide.md` / `*.sh` 스크립트

### 같이 걷어낸 것

- **Celery 전체** — `saerong/celery.py`, `saerong/__init__.py` 의 celery_app, `CELERY_*` 설정, `django_celery_beat`.
  크롤러(`collector`)용이었고 남은 앱은 쓰지 않는다. 서버 celery/celerybeat 서비스는 원래 inactive 였다.
- `rest_framework`, `corsheaders`, `django_filters`, `django_summernote` (전부 `api` 전용이었음)
- `REST_FRAMEWORK` / `CORS_*` / `TOSS_*` / `JWT_*` / `OPENAI_API_KEY` / `KAMIS_*` / `NAVER_*` / `SUMMERNOTE_CONFIG` 설정
- `static/`, `templates/base.html`, `templates/core/`, `STATICFILES_DIRS`

## 4. ~~/mosquito-test/ (모기 감시)~~ — 제거됨 (2026-08-24)

이 저장소에서 완전히 삭제. moscom.ai 서비스는 **별도 서버(43.201.131.25) / 별도 git 저장소**에서
계속 운영 중이며, 그쪽 작업은 이 저장소가 아니라 해당 저장소에서 진행할 것.

## 5. /tdmprediction/ (반코마이신 TDM — 최신 작업)

**상태: 가동 중. 진단 ID 입력 폼에서 제거 완료.**

- URL: https://saerong.com/tdmprediction/
- 로그인: `tdm` / `tdm1234` (settings.py `TDM_AUTH_USER` / `TDM_AUTH_PASSWORD`)
- 출처: `C:/Users/USER/OneDrive/농도예측_특허/Hybrid_model_2cm_bs_pipet/`
- 구조:
  - **1단계 ML**: 17 covariate → ns_peak/trough 1~5 (sklearn Pipeline, random_forest joblib 66MB)
  - **2단계 DL**: event seq + ML pred → 시간별 농도 곡선 + steady endpoint (LSTM, 140KB .pt)
- 모델 파일: `tdm/ml_artifacts/` (gitignore — 서버에 별도 scp 업로드)
  - 서버: `/srv/course-repo/tdm/ml_artifacts/random_forest.joblib`, `best_lstm_ml-extra_trees.pt`
  - extra_trees.joblib (103MB, RMSE 3.86) 은 미업로드 — 필요 시 scp
- 모델 번들 구조:
  - ML joblib: `{'model': Pipeline, 'feature_cols': [...], 'target_cols': [...], 'args': dict}`
  - DL .pt: `{'state_dict': ..., 'feature_cols': [...], 'stats': {'mean':{}, 'std':{}}, 'input_dim': N, 'args': dict}`
- 입력 폼 필드: age, sex(0/1), height, weight, Serum_Cr, CrCL(자동), Albumin, AST, ALT, WBC, Platelet, hs-CRP, dose_mg, q_hr, n_doses
  - **diagnosis_id 는 폼에서 제거** — 학습 시 51개 카테고리(0~50) 인코딩이라 사용자가 알 수 없음. 백엔드에서 기본값 `31` (학습 데이터의 "기타" 버킷) 자동 사용.
- CrCL: 빈칸이면 Cockcroft-Gault 자동 계산
- 결과: Chart.js 곡선 (목표 trough 15~20 음영) + 사이클별 ML 표 + KPI 4종
- 면책: "연구·참고용, 임상 판단은 처방의 검토 필수" 명시
- 감사 로그: `tdm.PredictionLog` (모든 요청 JSON 저장)
- 특허: 출원 진행 중

## 6. 핵심 사용자 선호 / 피드백 (학습된 규칙)

- **허락 없이 작업 진행** — 매번 "이렇게 할까요?" 묻지 말고 바로 실행. 큰 결정만 `AskUserQuestion`.
- **다음 단계 짧은 요약**으로 마무리. 장황한 설명/광고문 금지.
- **한국어로 답변**, 코드 주석은 한국어 또는 영어 자유.
- 마이그레이션 / DB 변경 시 사용자에게 알릴 것.
- 보안/접근 차단 작업은 `AskUserQuestion` 로 명시 확인 (animal 삭제 시 했던 패턴).
- 모바일 반응형 중요 — 768px / 480px 분기.
- 대시보드 UI 패턴 (햄버거 메뉴, KPI 2열, 표 가로스크롤) 유지 — 현재는 `templates/tdm/`, `templates/work/` 참고.

## 7. 외부 시스템 / 자격증명

남은 앱이 쓰는 외부 시스템은 없다.
OpenAI / Toss / Kakao / KAMIS / 네이버 / Open-Meteo 연동은 2026-08-24 대청소 때 해당 앱과 함께 전부 제거됐고,
구글 스칼라 스크래핑(`work/scholar.py`)도 2026-08-26 에 기능째 제거됐다.

## 8. 자주 쓰는 SSH/Bash 패턴 모음

```bash
# 서버 패키지 확인
ssh saerong-instance "/srv/venv/bin/python -c 'import sklearn; print(sklearn.__version__)'"

# 서버 패키지 설치 (CPU torch 등)
ssh saerong-instance "sudo /srv/venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.0"

# 서버 DB 직접 쿼리
ssh saerong-instance "sudo -u postgres psql -d saerong -c '\\dt tdm_*'"

# 큰 파일 업로드 (모델 가중치 등)
scp c:/workspace/saerongproj/tdm/ml_artifacts/X.joblib saerong-instance:/srv/course-repo/tdm/ml_artifacts/

# 배포 1-liner
ssh saerong-instance "cd /srv/course-repo && sudo git pull && sudo systemctl restart gunicorn && sleep 2 && sudo systemctl is-active gunicorn"

# 마이그레이션
ssh saerong-instance "cd /srv/course-repo && sudo /srv/venv/bin/python manage.py migrate <app>"
```

## 9. 검증 패턴

로컬에는 패키지가 없다 (venv 없음). 실제 검증은 서버에서 한다.

```bash
# 로컬: AST 파싱만
python -c "import ast; ast.parse(open('FILE.py', encoding='utf-8').read()); print('OK')"

# 서버: import 검증 (배포 전 필수 — restart 전에 돌릴 것)
ssh saerong-instance "cd /srv/course-repo && sudo /srv/venv/bin/python -c 'import app.main'"

# 서버: 8001 포트로 띄워서 확인 후 전환 (운영 건드리지 않음)
ssh saerong-instance "cd /srv/course-repo && sudo nohup /srv/venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/uv8001.log 2>&1 &"

# CSRF 가 필요한 POST 검증 (쿠키 → 헤더로 되돌려줘야 한다)
curl -sS -c cj.txt -o /dev/null https://saerong.com/work/
TOK=$(awk '/csrftoken/{print $7}' cj.txt)
curl -sS -b cj.txt -H "X-CSRFToken: $TOK" -X POST -F 'body=test' https://saerong.com/work/api/send/

# 운영 사이트 스모크
curl -sS -o /dev/null -w "%{http_code}\n" https://saerong.com/healthz
```

**주의**: Git Bash 의 curl 은 URL 의 한글을 CP949 로 인코딩한다. 한글 파일명 미디어를
테스트할 때는 UTF-8 퍼센트 인코딩을 직접 넣어야 한다 (안 그러면 멀쩡한데 404 로 보인다).

## 10. OneDrive 작업 폴더 (특허 관련)

- `C:/Users/USER/OneDrive/농도예측_특허/`
  - `Hybrid_model_2cm_bs_pipet/` — 학습 코드/모델/결과
    - `model_result/machine_learning/*.joblib` — extra_trees, random_forest, gradient_boosting
    - `model_result/deep_learning/*.pt` — lstm/rnn/transformer × ml 조합
    - `preprocess/hybrid_cycle_features.csv` — ML 학습 데이터 (4192 cycles)
    - `preprocess/hybrid_event_data.csv` — DL event seq
  - `data/data.xlsx` — 원본 (서울아산병원 TDM 데이터)
  - `[draft] 발명제안서_특허, 실용신안, 디자인_260602.docx` — 특허 제안서 초안
  - `특허도면_하이브리드TDM예측_4종.pptx` — 도면

## 11. 가장 최근 수정

- **저장소 대청소 — tdm/work 만 남기고 전부 삭제 (2026-08-24)**
- moscom 관련 코드 전체 제거 (a41a220, 2026-08-24)
- tdm ML 표 제거 / 농도 곡선 단순화 (cef371c, b5e3c4c)
- 사이클→투여횟수 개념 수정 + 랜드마크 재구성 곡선 복원 (842629e)
- TDM 입력 폼에서 진단 ID 제거 (8bc8f49)
- TDM 예측기 joblib/pt 번들 구조 처리 (2205d6a)
- /tdmprediction 페이지 최초 구현 (1dad51f)

## 12. 미해결 / 후속 가능 작업 (사용자 요청 시)

- TDM 페이지에 PDF 출력 / 배치 xlsx 업로드 (v2)
- extra_trees.joblib (103MB, 더 정확) 서버 추가 업로드
- 서버 정리: 삭제된 앱들의 DB 테이블(`moscom_*`, `core_*`, `collector_*`, `sources_*`, `api_*` 등)이 남아 있음.
  코드는 없으니 무해하지만, 확실해지면 drop 할 수 있음.
- 서버 정리: celery / celerybeat systemd 유닛, redis 가 아직 설치돼 있을 수 있음 (현재 inactive).

## 13. 코드 스타일 / 컨벤션

- 새 파일 만들 때 BOM 없는 UTF-8
- 모든 새 view 함수 위에 `@require_GET` / `@require_POST` / `@csrf_exempt` 명시
- Django 템플릿: 인라인 스타일 OK (이미 다 그렇게 작성됨)
- 한국어 주석 사용 자유
- DEBUG 로그는 `logger = logging.getLogger(__name__)` + `logger.exception()`

---

**새 세션에서 사용자가 "X 작업해줘" 라고 하면 → 이 문서 참조 후 위 패턴대로 바로 진행.**
