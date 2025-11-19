#!/bin/bash

# Game Honey mTLS 인증서 서버 배포 스크립트

set -e  # 에러 발생 시 스크립트 중단

SERVER="saerong.com"
CERT_DIR="/etc/toss/certs"
LOCAL_MTLS_DIR="./mtls"

echo "🚀 Game Honey mTLS 인증서 배포 시작..."

# 1. 서버에 디렉토리 생성
echo "📁 서버에 인증서 디렉토리 생성 중..."
ssh $SERVER "sudo mkdir -p $CERT_DIR && sudo chown \$USER:\$USER $CERT_DIR"

# 2. 인증서 파일 업로드
echo "📤 인증서 파일 업로드 중..."
scp $LOCAL_MTLS_DIR/gamehoneyalarm_public.crt $SERVER:$CERT_DIR/client-cert.pem
scp $LOCAL_MTLS_DIR/gamehoneyalarm_private.key $SERVER:$CERT_DIR/client-key.pem

# 3. 파일 권한 설정
echo "🔒 파일 권한 설정 중..."
ssh $SERVER "sudo chmod 600 $CERT_DIR/client-cert.pem && sudo chmod 600 $CERT_DIR/client-key.pem"

# 4. .env 파일 업데이트 (백업 먼저)
echo "⚙️  .env 파일 업데이트 중..."
ssh $SERVER "cd /srv/course-repo && \
    sudo cp .env .env.backup && \
    if ! grep -q 'TOSS_CERT_PATH' .env; then \
        echo '' | sudo tee -a .env && \
        echo '# Toss mTLS 인증서' | sudo tee -a .env && \
        echo 'TOSS_CERT_PATH=/etc/toss/certs/client-cert.pem' | sudo tee -a .env && \
        echo 'TOSS_KEY_PATH=/etc/toss/certs/client-key.pem' | sudo tee -a .env; \
    else \
        echo '.env에 이미 TOSS_CERT_PATH가 설정되어 있습니다.'; \
    fi"

# 5. Gunicorn 재시작
echo "🔄 Gunicorn 재시작 중..."
ssh $SERVER "sudo systemctl restart gunicorn"

# 6. 상태 확인
echo "✅ 배포 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. https://saerong.com/api/guide/ 접속"
echo "2. '테스트 푸시 알림 보내기' 버튼 클릭"
echo "3. 토스 앱 알림센터에서 푸시 확인"
echo ""
echo "🔍 로그 확인:"
echo "   ssh $SERVER 'sudo tail -f /var/log/gunicorn/error.log'"
