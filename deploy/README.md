# 새롱 공개 사이트 · TDM 운영 구성

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

## 2026-10-21 공개 사이트 배포

사용자가 여행 서비스·포트폴리오·문의·AdSense 설정과 배포를 명시적으로 요청했다.

- 새 공개 페이지: `/`, `/travel`, `/portfolio/`, `/services/`, `/contact/`, 정책·소개 페이지.
- 여행: 12개 자체 가이드, 취향 태그 비교, 권역별 필터, 브라우저 저장, 최대 3곳 비교, 공유. AI허브 네 권역 공개 소개 통계만 반영했고 원본 CSV·모델 학습은 미연결이다.
- 포트폴리오: 원본 자료에서 확인한 6개 주제를 합성 데이터 대시보드로 재구성. 개인·고객 정보나 확인되지 않은 성과를 게시하지 않았다.
- 문의: `/api/inquiries`에서 SQLite 저장 후 메일 알림. 보관 위치 `/srv/course-repo/private_data/inquiries.sqlite3`, 보관 기간 180일. 문의 데이터는 TDM PostgreSQL과 분리.
- 관리자: `/admin/`, 전용 계정. 비밀번호는 PBKDF2 해시만 서버 `.site.env`에 보관. 이 PC의 접속 안내는 Git에서 제외된 `private_data/admin-access.txt`에 보관한다.
- SMTP 설정은 기존 로컬 설정에서 읽어 SSH 표준입력으로 전달했다. 메일 주소·비밀번호는 배포 아카이브와 공개 소스에 포함하지 않았다.
- `ubuntu` crontab에 문의 보존기간 정리 작업을 등록했다. 매일 서버 시각 03:17에 `scripts/prune_site_inquiries.py`를 실행한다. 기존 cron 항목은 보존했다.
- 공개서비스에만 AdSense 스크립트 및 소유권 메타 태그 적용. `/ads.txt`, `/robots.txt`, `/sitemap.xml`, canonical·OG·WebPage 구조화 데이터 제공. Google 계정의 재검토·자동광고·CMP 게시 작업은 미완료다.
- 운영 `.env`, TDM 설정·보안·라우터·추론 코드와 모델 등 보호 파일 10개의 체크섬을 배포 전후 비교해 동일함을 확인했다. DB 마이그레이션이나 모델 추론은 실행하지 않았다.
- 초기 교체 전 백업: `/home/ubuntu/saerong-public-backup-20261020-150219.tar.gz` (UTC 명명). 관리자 전용 인증 반영 전 백업: `/home/ubuntu/saerong-public-backup-20261020-150438.tar.gz`.
- 공개 사이트 27개 릴리스 파일만 직접 전송했다. 기존 운영 수정 파일 전체를 덮어쓰거나 Git 커밋·푸시를 하지 않았다. nginx 설정도 변경하지 않았다.
- 검증: 로컬 테스트 22개, 3개 화면 폭의 브라우저 점검, HTTPS 페이지·정적 자산, 운영 문의 접수·SMTP 발송 성공, 전용 관리자 조회·상태 변경·삭제·로그아웃, 비공개 경로 404, 기존 TDM 로그인·CSRF·로그아웃·미인증 추론 차단과 구 URL 308.
- 운영 점검용 합성 문의 1건은 발송 확인 후 관리자 API로 삭제했다. 실사용자 데이터는 삭제하지 않았다.

### 다시 배포할 때

`scripts/deploy_public_site.py`는 대상 파일 체크섬, 보호 파일 해시, 기존 파일 백업, 앱 import, 재시작·헬스체크를 수행한다. 초기 배포는 `origin/main`의 TDM 메인 파일과 서버가 일치하는지 확인한다. `--update-public-release`는 현재 로컬 `app/main.py`가 서버와 일치할 때만 후속 반영한다. **main.py 자체를 수정한 후에는 서버 기준 파일을 별도로 검토해야 하며 검사를 임의로 우회하지 않는다.**

실패 시 이전 파일을 백업에서 복구한다. 서버 자격 증명은 `.site.env`에 있고 서비스 사용자만 읽도록 0600 권한을 설정했다. 백업에도 비공개 설정이 포함될 수 있으므로 공개 디렉터리로 옮기지 않는다.

## 2026-10-21 여행 탐색 재설계 배포

- 사용자 요청으로 기능 커밋 `9c00d2c`를 GitHub `main`에 푸시하고 https://saerong.com 과 `/travel`에 배포했다.
- 기존 서버 Git HEAD는 과거 상태이며 운영 수정사항이 많아 서버 `git pull`을 사용하지 않았다. 대상 파일은 이전 공개 릴리스 `cf133a4`와 정규화된 체크섬이 일치함을 확인한 뒤 교체했다.
- `scripts/deploy_travel_release.py`로 코드·템플릿·정적 자산·집계 JSON 총 14개 파일을 반영했다. 원본 CSV와 API 키는 전송하지 않았다.
- 집계 파일: `/srv/course-repo/private_data/travel/catalog.json`, 2,483개 장소. 서비스 사용자 `ubuntu` 소유, 파일 0600·디렉터리 0700.
- 백업: `/home/ubuntu/saerong-travel-backup-20261021-095926.tar.gz` (UTC 명명, 0600).
- `.env`, `.site.env`, TDM 라우터·인증·추론, 모델 가중치, DB 코드, 마이그레이션 등 보호 파일 32개가 배포 전후 동일함을 확인했다. nginx·SMTP·cron·DB는 변경하지 않았다.
- 서비스 import와 집계 로드를 확인한 후 `saerong`을 재시작했다. 헬스체크와 2,483개 장소 조회를 확인했다.
- 검증: 로컬 테스트 26개, JavaScript 구문 검사·diff 검사. 실제 HTTPS의 메인/여행/상세/기존 페이지, 검색 필터, 집계 CSV, 정적 파일 체크섬, 비공개 파일 차단, TDM 로그인 페이지·CSRF 차단·미인증 추론 차단·기존 URL 308. 운영 DB를 이용한 테스트·모델 추론·문의 접수·메일 발송은 하지 않았다.
- Edge에서 운영 데스크톱·모바일 화면, 검색, 상세의 분포 표시를 확인했고 JavaScript 오류가 없었다. 광고 계정 승인·자동광고·CMP는 이번 검증 대상이 아니다.

후속 여행 배포는 `deploy_travel_release.py --host <SSH대상> --identity <개인키경로> --baseline <현재배포코드커밋> --catalog-baseline-sha256 <검토한기존집계파일SHA256> --check`로 먼저 검증한다. 사용자 배포 요청이 있을 때 `--check`를 `--deploy`로 바꿔 수행한다. 기존 집계 파일은 Git에 없으므로 체크섬을 별도로 명시한다. 불일치하면 덮어쓰지 않고 중단하며, 교체 후 실패하면 백업 파일을 복구하고 새 파일을 제거한 뒤 재시작한다.
