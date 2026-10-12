# TDM 운영 구성

2026-10-10 사용자 요청으로 TDM 전용 버전을 saerong.com에 배포했다. 이후 서버 접근·배포·DB 마이그레이션·재시작·푸시는 별도 요청이 필요하다.

- [saerong.service](saerong.service): uvicorn 서비스 설정. 저장된 경로는 `/srv/course-repo`, 가상환경은 `/srv/venv`이다.
- [nginx-saerong.conf](nginx-saerong.conf): nginx에서 `127.0.0.1:8000`으로 전달하고 정적 파일을 제공한다.
- 모델 가중치와 `.env`는 기존 파일을 보존하며 Git에 추가하지 않는다.
- TDM은 `/tdm/`, 기존 `/tdmprediction/*` 요청은 308 리디렉션으로 유지한다.

이 파일들은 저장소의 구성 예시다. 실제 서버 설정과 동일한지는 다음 배포 전에 확인해야 한다. 기존 Alembic 리비전 이력을 보존하며, 현재 DB 상태를 확인하지 않고 `stamp`, `upgrade`, `downgrade`를 실행하지 않는다.

## 2026-10-10 배포 기록

- 이 PC의 SSH 별칭은 `saerong`이다. 컴퓨터 전용 공개키를 서버에 추가했고 기존 키는 유지했다. 개인키는 저장소 밖의 SSH 폴더에 보관한다.
- 배포 대상: `15.164.130.99`, `/srv/course-repo`, `saerong.service`, `/srv/venv`.
- 로컬 작업 파일을 묶어 직접 반영했다. Git 커밋·푸시·서버 pull은 수행하지 않았으므로 서버 HEAD는 배포 파일 버전과 다르다. 다음 배포 전에 서버 변경을 확인해야 한다.
- 반영 전 코드 백업: `/home/ubuntu/saerong-backup-20261010-200130.tar.gz`.
- `.env`와 모델 가중치의 해시가 유지됨을 확인했다. DB 마이그레이션·데이터 삭제·모델 추론은 실행하지 않았다.
- 앱을 재시작했고 실제 HTTPS에서 홈 이동·TDM 로그인·CSRF·로그아웃·미인증 API 차단·정적 파일·기존 URL 리디렉션·삭제 경로 404를 확인했다.
- 실제 nginx와 systemd 설정 파일은 교체하지 않았다. 저장소의 설정 예시 정리만 배포 파일에 포함했다.
