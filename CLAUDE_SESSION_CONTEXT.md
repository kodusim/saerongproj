# Claude 세션 인계 (saerongproj)

> 새 세션에서 첫 메시지로 이 문서를 읽어주세요.
> 이 문서는 사용자(전상기, saerong.com 운영자)의 작업 흐름을 끊김 없이 이어가기 위한 컨텍스트입니다.

## 1. 사용자 / 환경

- 사용자: **전상기 (sangki1298@gmail.com)** — saerong.com 단독 운영자
- 작업 디렉토리: `c:\workspace\saerongproj` (Windows 11, PowerShell)
- 가상환경: `./venv/Scripts/python.exe` (로컬, sklearn/openai 없음 — AST 파싱 수준 검증만)
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
- 웹서버: gunicorn (systemd `gunicorn` 서비스) + nginx
- **배포 패턴** (사용자가 별도 지시 없으면 매번 이 흐름):
  ```bash
  git add ... && git commit -m "..." && git push origin main
  ssh saerong-instance "cd /srv/course-repo && sudo git pull && sudo systemctl restart gunicorn && sleep 2 && sudo systemctl is-active gunicorn"
  curl -sS -o /dev/null -w "%{http_code}\n" https://saerong.com/...
  ```
- 호스트 라우팅: **`moscom.ai`** 도 같은 서버 — `saerong/host_routing.py` 가 `/mosquito-test/*`만 허용, 나머지는 404. `/tdmprediction/*` 등은 `moscom.ai` 에서 차단됨 (의도된 동작).

## 3. Django 앱 구조

- **`core`**: 메인 대시보드 / `/mosquito-test/` 전체 view 집합 (~3300줄 views.py)
- **`moscom`**: MOSCOM API 동기화 + 로컬 DB 모델 (Device, Collection, Region 등)
- **`tdm`**: **반코마이신 TDM 하이브리드 예측 (최신 작업)**
- **`animal`**: ❌ **삭제됨** (앱·템플릿·DB 테이블 11개 전부 drop, 2026-06-08)
- 기타: `api`, `analytics`, `collector`, `sources`

## 4. /mosquito-test/ (모기 감시)

- 인증: 세션 기반 `mosquito_admin` (별도 사용자 관리 — `moscom_users.json`)
- 외부 API: `https://api.moscom.co.kr` (JWT)
- 핵심 기능: 종합현황, 시간별 히트맵, 포집량 이상감지, 7일 추세, 방역 관리, AI 모기 예측, AI 위험도 예보, AI 행정 판단, 보고서 생성
- 주요 상수:
  - **51마리/일** = 전역 이상감지 임계값
  - **배터리 30% 미만** = 점검 대상
  - **새벽 5시 KST** = 영업일 경계 (`moscom.timeutil.business_today()`)
- AI 모델:
  - `core/predictor.py` + `moscom/ml/best_model_RandomForest.joblib` (+ MosquitoIndex)
  - 매일 새벽 5:10 자동 재학습 (Celery beat)
  - 4축 모기지수 = 0.5×count + 0.2×trend + 0.2×weather + 0.1×habitat
  - 등급: 쾌적/관심/주의/불쾌 (4단계, 모기지수 기준) — 마릿수 5단계와 다름
- 최근 수정: AI 행정 판단 기준일을 어제(측정완료)로, AI 예측 분석을 핵심 관측점 중심으로

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
- 권역 코드 (KH, GH서, HA, HY, BD, GS, SY, YS, 베트남 등) — 같은 시라도 권역 다르면 다른 그룹.
- 마이그레이션 / DB 변경 시 사용자에게 알릴 것.
- 보안/접근 차단 작업은 `AskUserQuestion` 로 명시 확인 (animal 삭제 시 했던 패턴).
- 모바일 반응형 중요 — 768px / 480px 분기.
- 이미 mosquito_test.html 에 한 패턴 (햄버거 메뉴, KPI 2열, 표 가로스크롤) 그대로 따라가기.

## 7. 외부 시스템 / 자격증명

- OpenAI: `OPENAI_API_KEY` (Django settings, gpt-4o-mini 사용)
- Kakao OAuth: 카카오톡 메시지 전송 통합 (`/mosquito-test/api/kakao/...`)
- Toss: 별도 서비스 (game_honey_alarm — saerongproj 안 하위, 이번 컨텍스트와 분리)
- Open-Meteo: 기상 (no key)

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

```bash
# AST 파싱만 (로컬 venv 패키지 부족 — sklearn/openai 등 없음)
./venv/Scripts/python.exe -c "import ast; ast.parse(open('FILE.py', encoding='utf-8').read()); print('OK')"

# Django 템플릿 컴파일
./venv/Scripts/python.exe -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saerong.settings')
django.setup()
from django.template.loader import get_template
get_template('PATH.html')
"

# 운영 사이트 스모크 (curl)
curl -sS -o /dev/null -w "%{http_code}\n" https://saerong.com/...
curl -sS -o /dev/null -w "%{http_code}\n" https://moscom.ai/...   # /mosquito-test/* 만 200, 나머지 404
```

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

## 11. 가장 최근 수정 (2026-06-08~10)

- TDM 입력 폼에서 진단 ID 제거 (8bc8f49)
- TDM 예측기 joblib/pt 번들 구조 처리 (2205d6a)
- /tdmprediction 페이지 최초 구현 (1dad51f)
- 모바일 일별 추세 차트 레이아웃 수정 (62f2872)
- AI 예측 모기지수 손실 버그 수정 (77eb71f)
- 동물의왕국 (animal) 앱 전체 삭제 (0c6bac3)
- AI 행정 판단 기준일을 어제로 + 예측을 핵심 관측점 중심 (e150ba7)
- 보고서 생성 강화 (51 임계·권역·매개체·기상생리학) (941c446)

## 12. 미해결 / 후속 가능 작업 (사용자 요청 시)

- TDM 페이지에 PDF 출력 / 배치 xlsx 업로드 (v2)
- extra_trees.joblib (103MB, 더 정확) 서버 추가 업로드
- TDM 예측 결과 → 카카오톡 전송 통합
- 매개체 위험 평가 GPT 신뢰도 향상

## 13. 코드 스타일 / 컨벤션

- 새 파일 만들 때 BOM 없는 UTF-8
- 모든 새 view 함수 위에 `@require_GET` / `@require_POST` / `@csrf_exempt` 명시
- Django 템플릿: 인라인 스타일 OK (이미 다 그렇게 작성됨)
- 한국어 주석 사용 자유
- DEBUG 로그는 `logger = logging.getLogger(__name__)` + `logger.exception()`

---

**새 세션에서 사용자가 "X 작업해줘" 라고 하면 → 이 문서 참조 후 위 패턴대로 바로 진행.**
