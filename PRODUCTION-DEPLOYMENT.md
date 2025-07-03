# 🚀 Sapiens Engine - 프로덕션 배포 완전 가이드

## 📋 목차
1. [서버 준비](#서버-준비)
2. [도메인 구매 및 DNS 설정](#도메인-구매-및-dns-설정)
3. [서버 배포](#서버-배포)
4. [CI/CD 설정](#cicd-설정)
5. [모니터링 설정](#모니터링-설정)
6. [운영 가이드](#운영-가이드)

---

## 🖥️ 서버 준비

### 1. 클라우드 서버 선택
추천 사양:
- **CPU**: 4 vCPU 이상
- **Memory**: 16GB 이상
- **Storage**: 100GB SSD 이상
- **OS**: Ubuntu 22.04 LTS

#### AWS EC2 설정
```bash
# 인스턴스 타입: t3.xlarge 또는 m5.xlarge
# Security Group 포트 개방: 22, 80, 443
```

#### Google Cloud Platform 설정
```bash
# 머신 타입: e2-standard-4
# 방화벽 규칙: allow-http, allow-https
```

#### Azure 설정
```bash
# VM 크기: Standard_D4s_v3
# 네트워크 보안 그룹: HTTP, HTTPS 허용
```

### 2. 초기 서버 설정
```bash
# 서버 접속
ssh root@your-server-ip

# 시스템 업데이트
apt update && apt upgrade -y

# 기본 패키지 설치
apt install -y curl wget git htop tree jq bc ufw fail2ban

# 사용자 생성 및 권한 설정
adduser deploy
usermod -aG sudo deploy
su - deploy
```

---

## 🌐 도메인 구매 및 DNS 설정

### 1. 도메인 구매
- **추천**: Namecheap, Cloudflare, GoDaddy
- 예시: `sapiens-chat.com`

### 2. DNS 설정
DNS 레코드를 다음과 같이 설정:

```
Type    Name    Value               TTL
A       @       your-server-ip      3600
A       www     your-server-ip      3600
A       api     your-server-ip      3600
CNAME   *       sapiens-chat.com    3600
```

### 3. Cloudflare 설정 (선택사항)
```bash
# Cloudflare를 사용하면 추가 보안 및 CDN 제공
# SSL/TLS: Full (strict)
# Always Use HTTPS: On
# Auto Minify: HTML, CSS, JS
```

---

## 🚀 서버 배포

### 1. 자동 배포 (추천)
```bash
# 서버에서 실행
wget https://raw.githubusercontent.com/yourusername/sapiens_engine/main/scripts/deploy.sh
chmod +x deploy.sh

# 환경 변수 설정
export DOMAIN="sapiens-chat.com"
export EMAIL="admin@sapiens-chat.com"

# 배포 실행
sudo ./deploy.sh
```

### 2. 수동 배포
```bash
# 1. 애플리케이션 다운로드
cd /opt
sudo git clone https://github.com/yourusername/sapiens_engine.git
sudo chown -R deploy:deploy sapiens_engine
cd sapiens_engine

# 2. 환경 변수 설정
cp production.env.example .env
nano .env  # 실제 값으로 수정

# 3. Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker deploy
sudo systemctl enable docker

# 4. Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. 서비스 시작
docker-compose -f docker-compose.prod.yml up -d
```

### 3. SSL 인증서 설정
```bash
# Let's Encrypt 인증서 자동 발급
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  --email admin@sapiens-chat.com \
  --agree-tos --no-eff-email \
  -d sapiens-chat.com -d www.sapiens-chat.com

# Nginx 재시작
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## ⚙️ CI/CD 설정

### 1. GitHub Repository 설정
```bash
# GitHub Secrets 설정 (Settings > Secrets and variables > Actions)
PRODUCTION_HOST=your-server-ip
PRODUCTION_USER=deploy
PRODUCTION_SSH_KEY=your-private-ssh-key
DOMAIN=sapiens-chat.com
SLACK_WEBHOOK_URL=your-slack-webhook-url
GRAFANA_PASSWORD=your-grafana-password
```

### 2. SSH Key 설정
```bash
# 로컬에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "deployment@sapiens-chat.com"

# 공개키를 서버에 복사
ssh-copy-id -i ~/.ssh/id_rsa.pub deploy@your-server-ip

# 비밀키를 GitHub Secrets에 추가 (PRODUCTION_SSH_KEY)
cat ~/.ssh/id_rsa
```

### 3. 자동 배포 테스트
```bash
# main 브랜치에 푸시하면 자동 배포
git add .
git commit -m "Deploy to production"
git push origin main
```

---

## 📊 모니터링 설정

### 1. Grafana 대시보드 설정
```bash
# 모니터링 서비스 시작
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# Grafana 접속: https://sapiens-chat.com:3001
# 기본 계정: admin / (env에서 설정한 비밀번호)
```

### 2. 자동 모니터링 스크립트 설정
```bash
# Cron job 설정
sudo crontab -e

# 다음 라인 추가:
# 매 5분마다 헬스체크
*/5 * * * * /opt/sapiens_engine/scripts/monitor.sh

# 매일 자정 백업
0 0 * * * /opt/sapiens_engine/scripts/backup.sh

# 매주 일요일 시스템 정리
0 2 * * 0 docker system prune -f
```

### 3. Slack 알림 설정
```bash
# Slack App 생성 후 Webhook URL 발급
# 환경 변수에 SLACK_WEBHOOK_URL 설정
```

---

## 🛠️ 운영 가이드

### 📈 성능 모니터링
```bash
# 시스템 상태 확인
./scripts/monitor.sh

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f api

# 실시간 리소스 모니터링
docker stats

# 토론방 상태 확인
curl https://sapiens-chat.com/api/chat/debug/active-rooms
```

### 🔄 업데이트 방법
```bash
# 1. 코드 업데이트 (자동 - GitHub push)
git push origin main

# 2. 수동 업데이트
cd /opt/sapiens_engine
git pull origin main
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### 💾 백업 및 복구
```bash
# 백업 실행
./scripts/backup.sh

# 복구 실행
# 1. 서비스 중지
docker-compose -f docker-compose.prod.yml down

# 2. 데이터 복구
docker cp /opt/backups/redis_dump_YYYYMMDD_HHMMSS.rdb sapiens-redis:/data/dump.rdb

# 3. 서비스 재시작
docker-compose -f docker-compose.prod.yml up -d
```

### 🚨 장애 대응
```bash
# 1. 긴급 재시작
docker-compose -f docker-compose.prod.yml restart

# 2. 메모리 정리
curl -X POST https://sapiens-chat.com/api/chat/cleanup/inactive-rooms

# 3. 로그 분석
docker-compose -f docker-compose.prod.yml logs --since="1h" api | grep -i error

# 4. 서비스 롤백 (이전 이미지로)
docker tag sapiens-engine:latest sapiens-engine:backup
docker-compose -f docker-compose.prod.yml down
# 이전 이미지로 변경 후
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🌟 최종 확인 체크리스트

### ✅ 배포 완료 체크
- [ ] 도메인 연결 확인: https://sapiens-chat.com
- [ ] API 문서 접근: https://sapiens-chat.com/docs
- [ ] SSL 인증서 정상 작동
- [ ] 헬스체크 통과: https://sapiens-chat.com/health
- [ ] 토론방 생성 테스트
- [ ] 모니터링 대시보드 접근
- [ ] 백업 스크립트 정상 작동
- [ ] CI/CD 파이프라인 정상 작동

### 🎯 성능 최적화
```bash
# 1. Redis 튜닝
# redis/redis.conf 설정 조정

# 2. Nginx 캐싱 설정
# nginx/conf.d/sapiens.conf 에 캐시 규칙 추가

# 3. 로그 로테이션 확인
logrotate -d /etc/logrotate.d/sapiens-engine

# 4. 방화벽 최종 확인
ufw status verbose
```

---

## 📞 지원 및 문의

- **개발팀 이메일**: dev@sapiens-chat.com
- **GitHub Issues**: https://github.com/yourusername/sapiens_engine/issues
- **Slack 채널**: #sapiens-support

---

## 🔗 유용한 링크

- [API 문서](https://sapiens-chat.com/docs)
- [GitHub Repository](https://github.com/yourusername/sapiens_engine)
- [모니터링 대시보드](https://sapiens-chat.com:3001)
- [백업 위치](/opt/backups)

---

**배포 완료!** 🎉

이제 사용자들이 https://sapiens-chat.com 에서 AI 철학자들과 토론을 즐길 수 있습니다! 