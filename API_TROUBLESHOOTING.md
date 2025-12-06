# API 트러블슈팅 가이드

## 목차
1. [CORS 오류](#1-cors-오류)
2. [데이터 파싱 오류](#2-데이터-파싱-오류)
3. [배포 관련](#3-배포-관련)

---

## 1. CORS 오류

### 증상
```
TypeError: Failed to fetch
Error object: {}
```
- 에러 객체가 비어있음
- 콘솔에서 `Failed to fetch` 외에 정보가 없음

### 원인
1. **Nginx와 Django에서 CORS 헤더 중복 설정**
   - Nginx에서 `add_header Access-Control-*` 설정
   - Django에서 `django-cors-headers` 미들웨어 사용
   - 둘 다 설정하면 헤더가 중복되어 브라우저가 거부

2. **Origin 도메인 미등록**
   - 앱인토스 도메인: `https://{앱이름}.private-apps.tossmini.com`
   - 이 도메인이 CORS 허용 목록에 없으면 차단됨

### 해결 방법

#### 방법 1: Django에서만 CORS 처리 (권장)
```python
# settings.py
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.private-apps\.tossmini\.com$",
    r"^https://.*\.apps-in-toss\.com$",
]
```

Nginx에서 CORS 헤더 제거:
```nginx
location /api/ {
    # CORS 헤더 설정하지 않음 - Django가 처리
    proxy_pass http://unix:/run/gunicorn.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

#### 방법 2: Nginx에서만 CORS 처리
Django `settings.py`에서 CORS 미들웨어 비활성화하고 Nginx에서만 설정.
(비권장 - Django의 유연한 설정을 활용할 수 없음)

### 디버깅 팁
프론트엔드에서 Origin 확인:
```typescript
throw new Error(`... (Origin: ${window.location.origin})`);
```

---

## 2. 데이터 파싱 오류

### 증상
```
TypeError: c.replace is not a function
```

### 원인
외부 API(KAMIS 등)에서 예상과 다른 타입 반환:
- 예상: `"12,345"` (문자열)
- 실제: `[]` (빈 배열) 또는 `null`

### 해결 방법
타입 체크를 강화한 파싱 함수:

```typescript
// Before (취약)
function parsePrice(priceStr: string): number {
  return parseInt(priceStr.replace(/,/g, ''), 10) || 0;
}

// After (안전)
function parsePrice(priceStr: string | unknown[] | undefined | null): number {
  // 빈 배열, null, undefined 처리
  if (!priceStr || Array.isArray(priceStr) || priceStr === '-') return 0;
  if (typeof priceStr !== 'string') return 0;
  return parseInt(priceStr.replace(/,/g, ''), 10) || 0;
}
```

### 교훈
- 외부 API 응답은 항상 불신하고 방어적으로 코딩
- TypeScript 타입과 실제 런타임 데이터는 다를 수 있음
- 콘솔에서 실제 데이터 구조 확인 필수

---

## 3. 배포 관련

### 서버 프로젝트 경로
```
/srv/course-repo/
```

### 배포 절차
```bash
# 1. 로컬에서 커밋 & 푸시
git add api/views.py api/urls.py
git commit -m "메시지"
git push origin main

# 2. 서버에서 풀
ssh ubuntu@saerong.com "cd /srv/course-repo && git pull origin main"

# 3. Gunicorn 재시작
ssh ubuntu@saerong.com "sudo systemctl restart gunicorn"
```

### Windows에서 curl 테스트 시 인코딩 문제
```bash
# Windows에서 한글 JSON 전송 시 인코딩 깨짐
curl -d '{"name":"패션"}' ...  # 실패

# 해결: 서버에서 직접 테스트
ssh ubuntu@saerong.com 'curl -X POST ... -d "{\"name\":\"fashion\"}"'
```

### Git 오류: `invalid path 'nul'`
Windows에서 `nul` 파일이 생성된 경우:
```bash
rm -f nul
git add <specific files>  # git add -A 대신 개별 파일 추가
```

---

## 체크리스트

### API 추가 시
- [ ] `views.py`에 함수 추가
- [ ] `urls.py`에 import 및 path 추가
- [ ] `python manage.py check` 로 문법 검증
- [ ] 서버 배포 후 `systemctl restart gunicorn`
- [ ] CORS 설정 확인 (새 도메인인 경우)

### 외부 API 연동 시
- [ ] 응답 데이터 타입 확인 (빈 배열, null 가능성)
- [ ] 타임아웃 설정
- [ ] 캐싱 적용 (API 호출 최소화)
- [ ] 에러 핸들링 (네트워크 오류, API 오류)

### 프론트엔드 디버깅
- [ ] 에러 메시지에 URL, Origin 포함
- [ ] 콘솔에 raw 데이터 로깅
- [ ] 네트워크 탭에서 실제 응답 확인
