"""
새로운 구조의 Sapiens Engine API Server
- 라우터 기반 모듈화된 구조  
- 도메인별 엔드포인트 분리
- python-socketio를 통한 실제 Socket.IO 통합
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio
from pydantic import BaseModel
import logging
import os

# 라우터 임포트
from routers import debug, philosophers, chat, npc, upload

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
fastapi_app = FastAPI(
    title="Sapiens Engine API (New Structure)",
    description="철학자 AI와의 대화 및 토론 시스템 - 리팩토링된 구조",
    version="2.0.0"
)

# CORS 설정
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 오리진으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO 서버 생성 - 프로토콜 버전 명시적 지정
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi',
    logger=False,  # ping/pong 로그 비활성화
    engineio_logger=False,  # engine.io 로그 비활성화
    # Engine.IO 설정 명시적 지정
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    allow_upgrades=True,
    transports=['polling', 'websocket']
)

# Socket.IO ASGI 앱 생성
sio_app = socketio.ASGIApp(sio, fastapi_app)

# Socket.IO 데이터 저장
room_users = {}  # room_id -> set of user_ids

# ========================================================================
# Socket.IO 이벤트 핸들러 (chat.py에서 일부 덮어쓸 예정)
# ========================================================================

@sio.event
async def connect(sid, environ):
    """클라이언트 연결 시 처리"""
    logger.info(f"🔌 Client {sid} connected")

@sio.event
async def disconnect(sid):
    """클라이언트 연결 해제 시 처리 - 전체 정리"""
    logger.info(f"🔌 Client {sid} disconnected")
    
    # 해당 sid와 연결된 사용자/방 정보가 있다면 정리
    # (실제로는 프론트엔드에서 명시적으로 user_disconnected를 호출해야 함)

@sio.event
async def join_room(sid, data):
    """사용자가 방에 참여할 때 처리"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    
    if not room_id or not user_id:
        return {"error": "room_id and user_id required"}
    
    # 방에 사용자 추가
    if room_id not in room_users:
        room_users[room_id] = set()
    room_users[room_id].add(user_id)
    
    # Socket.IO 방에 참여
    await sio.enter_room(sid, room_id)
    
    logger.info(f"📥 User {user_id} joined room {room_id}")
    logger.info(f"📊 Room {room_id} now has {len(room_users[room_id])} users")
    
    # 방의 다른 사용자들에게 알림
    await sio.emit("user_joined", {
        "user_id": user_id,
        "message": f"{user_id}님이 방에 참여했습니다",
        "room_count": len(room_users[room_id])
    }, room=room_id, skip_sid=sid)
    
    return {"success": True, "message": f"Successfully joined room {room_id}"}

# ========================================================================
# 아래 핸들러들은 chat.py에서 덮어쓸 예정이므로 주석 처리
# ========================================================================

# @sio.event
# async def leave_room(sid, data):
#     """사용자가 방을 떠날 때 처리 - chat.py에서 덮어쓸 예정"""
#     # chat.py의 register_socketio_handlers()에서 이 핸들러를 덮어씁니다
#     pass

# @sio.event
# async def user_disconnected(sid, data):
#     """사용자 연결 해제 시 자동 정리 - chat.py에서 덮어쓸 예정"""
#     # chat.py의 register_socketio_handlers()에서 이 핸들러를 덮어씁니다
#     pass

@sio.event
async def send_message(sid, data):
    """메시지 전송 처리"""
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    message = data.get('message')
    
    if not all([room_id, user_id, message]):
        return {"error": "room_id, user_id, and message required"}
    
    logger.info(f"📨 Message from {user_id} in room {room_id}: {message[:50]}...")
    
    # 방의 모든 사용자에게 메시지 브로드캐스트
    await sio.emit("new_message", {
        "roomId": room_id,
        "message": {
            "id": f"msg_{sid}_{len(message)}",
            "text": message,
            "sender": user_id,
            "timestamp": "now",
            "isUser": True
        }
    }, room=room_id)
    
    return {"success": True, "message": "Message sent"}

# ========================================================================
# Socket.IO 브로드캐스트 함수 (chat.py에서 사용)
# ========================================================================

async def send_message_to_room(room_id: str, message_data: dict):
    """Socket.IO를 통해 특정 방에 메시지 전송"""
    try:
        # 방에 있는 클라이언트 수 확인
        client_count = len(room_users.get(room_id, set()))
        
        logger.info(f"📢 Broadcasting to room {room_id}: new_message")
        logger.info(f"📢 Clients in room: {client_count}")
        
        # Socket.IO emit
        await sio.emit("new_message", message_data, room=room_id)
        
        logger.info(f"✅ Message sent to room {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send message to room {room_id}: {e}")
        return False

# ========================================================================
# FastAPI 라우터 등록
# ========================================================================

# 정적 파일 서빙 설정 (portraits 폴더)
fastapi_app.mount("/portraits", StaticFiles(directory="../portraits"), name="portraits")

# 라우터 등록
fastapi_app.include_router(debug.router, prefix="/debug", tags=["debug"])
fastapi_app.include_router(philosophers.router, prefix="/api/philosophers", tags=["philosophers"])
fastapi_app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
fastapi_app.include_router(npc.router, prefix="/api/npc", tags=["npc"])
fastapi_app.include_router(upload.router, prefix="/api/upload", tags=["upload"])

@fastapi_app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "socket_io": "enabled",
        "active_rooms": len(room_users),
        "total_users": sum(len(users) for users in room_users.values())
    }

# ========================================================================
# ASGI 앱 - Socket.IO와 FastAPI 통합
# ========================================================================

# Socket.IO와 FastAPI를 통합한 ASGI 앱
app = sio_app

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Sapiens Engine API with python-socketio")
    logger.info("📚 Available at: http://localhost:8000")
    logger.info("📖 API Docs: http://localhost:8000/docs")
    logger.info("🔌 Socket.IO: http://localhost:8000/socket.io/")
    
    # Socket.IO와 통합된 앱 실행
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 