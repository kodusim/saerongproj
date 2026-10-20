# saerongproj — TDM

반코마이신 혈중 농도를 예측하는 FastAPI 애플리케이션이다. 2026-10-09 사용자 요청으로 TDM 외 서비스 코드와 제품·브랜드 문서를 정리했고, 2026-10-10 사용자 요청으로 saerong.com에 배포했다.

## 경로

| 경로 | 기능 |
|---|---|
| `/` | `/tdm/`으로 이동 |
| `/tdm/` | 로그인 후 ML + DL 예측 화면 |
| `/tdm/login/`, `/tdm/logout/` | 세션 인증 |
| `/tdm/api/predict/` | 예측 API와 감사 로그 저장 |
| `/tdm/logs/` | 최근 200개 감사 로그 조회 |
| `/tdmprediction/*` | 요청 메서드를 유지하는 308 리디렉션 |
| `/healthz` | 헬스체크 |

## 구성과 실행

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
