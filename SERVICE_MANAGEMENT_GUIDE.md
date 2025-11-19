# 게임 하니 서비스 운영 가이드

## 📋 목차
1. [Django Admin 안전하게 사용하기](#1-django-admin-안전하게-사용하기)
2. [데이터 무결성 보장](#2-데이터-무결성-보장)
3. [에러 모니터링](#3-에러-모니터링)
4. [백업 및 복구](#4-백업-및-복구)
5. [배포 프로세스](#5-배포-프로세스)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. Django Admin 안전하게 사용하기

### ⚠️ 절대 하지 말아야 할 것

```
❌ UserProfile 함부로 삭제
❌ User 계정 삭제 (구독 정보도 함께 삭제됨)
❌ PremiumSubscription 직접 삭제 (만료일 지나면 자동 삭제)
❌ 프로덕션 DB에서 직접 SQL 실행
```

### ✅ 대신 이렇게 하세요

#### 사용자 비활성화 (삭제 대신)
```python
# Django Admin에서
User.is_active = False  # 로그인 차단
User.save()
```

#### 테스트 데이터 정리
```python
# 테스트 사용자만 삭제 (username에 'test_' 포함)
User.objects.filter(username__startswith='test_').delete()
```

#### 프리미엄 만료 처리
```python
# 자동으로 처리되므로 수동 삭제 불필요
# GET /api/premium/status/ 호출 시 자동으로 만료된 구독 삭제
```

### 🔒 Admin 보호 기능 (이미 적용됨)

- **삭제 권한 제한**: 슈퍼유저만 UserProfile 삭제 가능
- **경고 메시지**: 삭제 시 영향 범위 표시
- **프리미엄 상태**: Admin 목록에서 한눈에 확인

---

## 2. 데이터 무결성 보장

### User ↔ UserProfile 관계

**문제:** UserProfile 삭제 시 User는 남아있어서 로그인 실패

**해결 (이미 구현됨):**
```python
# api/toss_auth.py:308-324
# UserProfile 없으면 자동 재생성
# User 있으면 재사용, 없으면 새로 생성
```

### User ↔ PremiumSubscription 관계

**CASCADE 설정:**
```python
# api/models.py
class PremiumSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # User 삭제 시 PremiumSubscription도 함께 삭제됨
```

**권장사항:**
- User 삭제 대신 `is_active=False` 설정
- 프리미엄 만료는 자동 처리

### Subscription ↔ Game 관계

**PROTECT 설정 권장:**
```python
# 추후 추가 권장
class Subscription(models.Model):
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    # Game 삭제 시 구독이 있으면 삭제 차단
```

---

## 3. 에러 모니터링

### 로그 파일 위치

```bash
# 서버 접속
ssh saerong.com

# Django 로그
sudo journalctl -u gunicorn -f

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log

# 애플리케이션 로그
tail -f /srv/course-repo/logs/django.log
```

### 주요 에러 패턴

#### 1. UserProfile.DoesNotExist
```
원인: Admin에서 UserProfile 삭제
해결: 자동 재생성 로직이 작동함 (재로그인 시)
```

#### 2. PremiumSubscription.DoesNotExist
```
원인: 프리미엄 만료 또는 삭제
해결: 정상 동작 (무료 사용자로 처리)
```

#### 3. 500 Internal Server Error
```
원인: 백엔드 코드 에러
조치:
1. journalctl -u gunicorn -n 100 --no-pager
2. 에러 로그 확인 후 수정
3. git commit & push
4. 서버에서 git pull && sudo systemctl restart gunicorn
```

### Sentry 연동 (권장)

```python
# settings.py에 추가
import sentry_sdk

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)
```

**장점:**
- 실시간 에러 알림
- 스택 트레이스 자동 수집
- 에러 발생 빈도 추적

---

## 4. 백업 및 복구

### DB 백업 (매일 자동화 권장)

```bash
# 백업 스크립트 생성
sudo nano /srv/backup_db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/srv/backups/db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL 백업
sudo -u postgres pg_dump gamehoney > $BACKUP_DIR/gamehoney_$DATE.sql

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/gamehoney_$DATE.sql"
```

```bash
# 실행 권한
sudo chmod +x /srv/backup_db.sh

# Cron 등록 (매일 새벽 3시)
sudo crontab -e
0 3 * * * /srv/backup_db.sh
```

### 복구 방법

```bash
# 백업 파일로 복구
sudo -u postgres psql gamehoney < /srv/backups/db/gamehoney_20251119_030000.sql
```

### 코드 백업

```bash
# Git 원격 저장소가 백업 역할
git push origin main

# 태그로 릴리즈 버전 관리
git tag -a v1.0.0 -m "프리미엄 시스템 출시"
git push origin v1.0.0
```

---

## 5. 배포 프로세스

### 개발 환경 (로컬)

```bash
# 1. 코드 수정
# 2. 테스트
python manage.py test

# 3. 커밋
git add .
git commit -m "메시지"

# 4. 푸시
git push origin main
```

### 프로덕션 배포

```bash
# 서버 접속
ssh saerong.com

# 1. 코드 업데이트
cd /srv/course-repo
git pull origin main

# 2. 의존성 업데이트 (필요시)
source venv/bin/activate
pip install -r requirements.txt

# 3. DB 마이그레이션 (필요시)
python manage.py migrate

# 4. 정적 파일 수집 (필요시)
python manage.py collectstatic --noinput

# 5. 서비스 재시작
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 6. 로그 확인
sudo journalctl -u gunicorn -n 50 --no-pager
```

### 롤백 방법

```bash
# 이전 버전으로 되돌리기
cd /srv/course-repo
git log --oneline -n 10  # 커밋 확인
git reset --hard <커밋해시>
sudo systemctl restart gunicorn
```

---

## 6. 트러블슈팅

### 문제: "로그인에 실패했습니다"

**원인 확인:**
```bash
# 1. 서버 로그 확인
sudo journalctl -u gunicorn -n 100 --no-pager | grep ERROR

# 2. 앱 디버그 콘솔 확인
# 앱에서 F12 → Console 탭
```

**일반적인 원인:**
- UserProfile 삭제 (자동 재생성됨)
- 토스 API 응답 지연 (timeout 증가 필요)
- 인증서 만료 (mTLS 인증서 갱신)

### 문제: "구독에 실패했습니다"

**원인:**
```python
# 프리미엄 없음 (정상)
# 광고권 1개 제한 초과 (정상)
# 서버 에러 (로그 확인 필요)
```

**조치:**
```bash
# 에러 로그 확인
sudo journalctl -u gunicorn -n 100 | grep subscriptions
```

### 문제: "푸시 알림이 안 와요"

**체크리스트:**
```
✅ 프리미엄 구독권이 활성화되어 있나요?
✅ 해당 게임/카테고리를 구독했나요?
✅ mTLS 인증서가 유효한가요? (/srv/toss-certs/)
✅ 크롤링이 정상 작동하나요? (새 데이터가 수집되었나요?)
```

**푸시 테스트:**
```bash
# Admin 페이지에서 "테스트 푸시 알림 보내기" 클릭
# 또는 API 직접 호출
curl -X POST https://saerong.com/api/test/push/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "테스트", "body": "테스트 메시지"}'
```

### 문제: "서버가 응답하지 않아요"

**1단계: 서비스 상태 확인**
```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
```

**2단계: 재시작**
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

**3단계: 포트 확인**
```bash
sudo netstat -tlnp | grep :8000  # Gunicorn
sudo netstat -tlnp | grep :80    # Nginx
```

### 문제: "메모리 부족"

```bash
# Swap 확인
free -h

# Swap 추가 (4GB)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📊 정기 점검 체크리스트

### 매일
- [ ] 서버 로그 확인 (에러 없는지)
- [ ] 푸시 알림 정상 발송 확인
- [ ] 크롤링 작동 확인

### 매주
- [ ] DB 백업 확인
- [ ] 디스크 용량 확인 (`df -h`)
- [ ] 사용자 피드백 확인

### 매월
- [ ] mTLS 인증서 만료일 확인
- [ ] 프리미엄 구독 통계 확인
- [ ] 의존성 패키지 업데이트 검토

### 필요시
- [ ] Django 버전 업그레이드
- [ ] PostgreSQL 업그레이드
- [ ] 서버 스케일업/아웃

---

## 🔗 주요 명령어 모음

```bash
# 서버 접속
ssh saerong.com

# 로그 확인
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/nginx/error.log

# 서비스 재시작
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# DB 백업
sudo -u postgres pg_dump gamehoney > backup.sql

# 배포
cd /srv/course-repo
git pull origin main
sudo systemctl restart gunicorn

# 디스크 용량
df -h

# 메모리 사용량
free -h

# 프로세스 확인
ps aux | grep gunicorn
```

---

## 📞 긴급 연락처

- **Django 개발자**: [연락처]
- **앱 개발자**: [연락처]
- **서버 관리자**: [연락처]
- **토스 기술 지원**: developers@toss.im

---

## 📚 참고 문서

- [Django Admin 문서](https://docs.djangoproject.com/en/stable/ref/contrib/admin/)
- [PostgreSQL 백업 가이드](https://www.postgresql.org/docs/current/backup.html)
- [Gunicorn 설정](https://docs.gunicorn.org/en/stable/settings.html)
- [토스 앱인토스 개발자 문서](https://developers-apps-in-toss.toss.im/)
