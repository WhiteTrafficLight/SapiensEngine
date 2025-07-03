# Sapiens Engine - 토론 채팅 애플리케이션 배포 가이드

## 개요

이 프로젝트는 AI 철학자들과의 실시간 토론을 지원하는 채팅 애플리케이션입니다. conda agora 환경을 기반으로 Docker를 통해 배포할 수 있습니다.

## 시스템 요구사항

- Docker 20.10+
- Docker Compose 2.0+
- 최소 8GB RAM
- 최소 20GB 디스크 공간

## 배포 방법

### 1. 기본 배포 (API + Redis)

```bash
# 프로젝트 클론
git clone <repository-url>
cd sapiens_engine

# Docker 이미지 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api
```

### 2. 모니터링 포함 배포

```bash
# Redis Insight 포함 실행
docker-compose --profile monitoring up -d
```

## 서비스 엔드포인트

- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **Redis**: localhost:6379
- **Redis Insight** (모니터링 프로필): http://localhost:8001

## 주요 API 엔드포인트

### 토론방 관리
- `POST /api/chat/create-debate-room` - 토론방 생성
- `POST /api/chat/debate/{room_id}/next-message` - 다음 메시지 생성
- `DELETE /api/chat/debate/{room_id}` - 토론방 정리

### 사용자 관리
- `POST /api/chat/user/{user_id}/leave-room` - 사용자 퇴장
- `POST /api/chat/debate/{room_id}/process-user-message` - 사용자 메시지 처리

### 시스템 관리
- `GET /api/chat/debug/active-rooms` - 활성 토론방 상태
- `POST /api/chat/cleanup/inactive-rooms` - 비활성 토론방 정리

## 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `REDIS_URL` | `redis://redis:6379` | Redis 연결 URL |
| `NEXTJS_SERVER_URL` | `http://localhost:3000` | Next.js 서버 URL |
| `MAX_ACTIVE_ROOMS` | `50` | 최대 동시 토론방 수 |
| `MAX_MEMORY_USAGE_GB` | `8` | 최대 메모리 사용량 (GB) |
| `MEMORY_CHECK_INTERVAL` | `10` | 메모리 체크 간격 (분) |

## 확장성 설정

### 단일 서버 배포 (현재 설정)
- ~500 동시 사용자
- ~50 동시 토론방
- 8GB 메모리 제한

### 다중 서버 배포 (향후 확장)
- Redis Cluster 구성
- Load Balancer 추가
- 상태 동기화 강화

## 모니터링

### 헬스체크
```bash
curl http://localhost:8000/health
```

### 메모리 사용량 확인
```bash
curl http://localhost:8000/api/chat/debug/active-rooms
```

### 로그 확인
```bash
# API 서버 로그
docker-compose logs -f api

# Redis 로그
docker-compose logs -f redis
```

## 트러블슈팅

### 1. 메모리 부족
```bash
# 비활성 토론방 수동 정리
curl -X POST http://localhost:8000/api/chat/cleanup/inactive-rooms
```

### 2. Redis 연결 문제
```bash
# Redis 재시작
docker-compose restart redis
```

### 3. API 서버 재시작
```bash
# API 서버만 재시작
docker-compose restart api
```

## 백업 및 복구

### Redis 데이터 백업
```bash
# 백업
docker exec sapiens-redis redis-cli BGSAVE
docker cp sapiens-redis:/data/dump.rdb ./backup/

# 복구
docker cp ./backup/dump.rdb sapiens-redis:/data/
docker-compose restart redis
```

## 보안 설정

### 1. 프로덕션 환경
- CORS 설정을 특정 도메인으로 제한
- Redis AUTH 설정
- SSL/TLS 인증서 설정

### 2. 방화벽 설정
```bash
# 필요한 포트만 개방
ufw allow 8000/tcp  # API 서버
ufw allow 6379/tcp  # Redis (내부 통신만)
```

## 성능 최적화

### 1. Docker 설정
- 컨테이너별 리소스 제한 설정
- 로그 로테이션 구성

### 2. Redis 설정
- 메모리 정책 최적화
- 지속성 설정 조정

## 업데이트 방법

```bash
# 코드 업데이트
git pull origin main

# 이미지 재빌드 및 재배포
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 지원

문제가 발생하거나 질문이 있으시면 개발팀에 문의해주세요. 