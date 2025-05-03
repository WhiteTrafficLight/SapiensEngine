# 서버 관리 가이드

이 문서는 Sapiens Engine 서버 관리에 관한 가이드입니다.

## 서버 구조

이 프로젝트는 두 개의 서버로 구성되어 있습니다:

1. **Python API 서버 (FastAPI)**: LLM 관련 작업과 철학적 대화 생성을 담당
   - 위치: `/Users/jihoon/sapiens_engine/api_server.py`
   - 포트: 8000

2. **Next.js 서버**: 웹 프론트엔드와 MongoDB 데이터 관리를 담당
   - 위치: `/Users/jihoon/sapiens_engine/agoramind`
   - 포트: 3000

## 서버 관리 스크립트

### 서버 시작/재시작

서버를 시작하거나 재시작하려면 다음 스크립트를 실행합니다:

```bash
cd /Users/jihoon/sapiens_engine
./restart_servers.sh
```

이 스크립트는 다음 작업을 수행합니다:
- 실행 중인 서버들을 종료
- Python API 서버를 백그라운드로 시작
- Next.js 서버를 백그라운드로 시작
- 로그 파일 경로 안내

### 서버 종료

서버를 종료하려면 다음 스크립트를 실행합니다:

```bash
cd /Users/jihoon/sapiens_engine
./stop_servers.sh
```

## 로그 확인

### 실시간 로그 확인

**Python API 서버 로그:**
```bash
tail -f /Users/jihoon/sapiens_engine/python_api.log
```

**Next.js 서버 로그:**
```bash
tail -f /Users/jihoon/sapiens_engine/agoramind/nextjs.log
```

### 최근 로그 일부 확인

**Python API 서버:**
```bash
tail -n 100 /Users/jihoon/sapiens_engine/python_api.log
```

**Next.js 서버:**
```bash
tail -n 100 /Users/jihoon/sapiens_engine/agoramind/nextjs.log
```

## 서버 상태 확인

실행 중인 서버 프로세스를 확인하려면:

```bash
ps aux | grep -E "uvicorn|npm run dev"
```

## 서버 간 통신 구조

1. **NPC 정보 조회 흐름**:
   - Python API서버는 `/api/npc/get?id={id}` 엔드포인트를 통해 Next.js 서버에서 NPC 정보를 가져옵니다.
   - 캐싱 시스템을 통해 반복적인 요청을 최소화합니다(TTL: 10분).
   - 첫 번째 시도 실패 시 `/api/npc/get-by-backend-id?id={id}` 엔드포인트로 대체 요청합니다.

2. **메시지 저장 흐름**:
   - Python API서버는 생성된 메시지를 Next.js API의 `/api/rooms?id={room_id}` 엔드포인트를 통해 저장합니다.
   - 저장 성공 후 `/api/socket` 엔드포인트에 브로드캐스트 요청을 보내 실시간 업데이트가 이루어집니다.

## 문제 해결

### 서버 재시작이 필요한 상황

다음과 같은 상황에서는 서버 재시작이 필요할 수 있습니다:
- NPC 정보 조회 실패가 반복될 때
- 자동 대화가 정상적으로 진행되지 않을 때
- 메시지가 실시간으로 업데이트되지 않을 때

### 로그 분석 포인트

문제 발생 시 로그에서 확인할 핵심 포인트:
- "🔍 Cache hit" - NPC 정보 캐시 적중 확인
- "✅ Retrieved custom NPC data" - NPC 정보 조회 성공
- "❌ Failed to get custom NPC" - NPC 정보 조회 실패
- "📣 Custom NPC 추가 특성 포함" - NPC 특성이 프롬프트에 반영됨 