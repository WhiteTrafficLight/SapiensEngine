"""
실시간 토론 시스템 - Socket.IO 통합

Socket.IO를 사용하여 Next.js 서버와 통신
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import socketio

logger = logging.getLogger(__name__)

# ========================================================================
# 데이터 모델
# ========================================================================

class CreateDebateRoomRequest(BaseModel):
    room_id: str
    title: str
    context: str = ""
    pro_npcs: List[str]
    con_npcs: List[str] 
    user_ids: List[str]
    moderator_style: str = "Jamie the Host"

# ========================================================================
# Socket.IO 클라이언트 설정
# ========================================================================

# Socket.IO 클라이언트 인스턴스
sio = socketio.AsyncClient()

# Next.js 서버 URL
NEXTJS_SERVER_URL = "http://localhost:3000"

@sio.event
async def connect():
    logger.info("🔌 Socket.IO 클라이언트가 Next.js 서버에 연결되었습니다")

@sio.event
async def disconnect():
    logger.info("🔌 Socket.IO 클라이언트 연결이 해제되었습니다")

async def init_socketio_client():
    """Socket.IO 클라이언트 초기화"""
    try:
        if not sio.connected:
            await sio.connect(
                url=NEXTJS_SERVER_URL,
                socketio_path="/api/socket/io"
            )
            logger.info("✅ Socket.IO 클라이언트 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"❌ Socket.IO 클라이언트 초기화 실패: {str(e)}")
        return False

async def send_message_to_room(room_id: str, message_data: Dict[str, Any]):
    """Socket.IO를 통해 특정 방에 메시지 전송"""
    try:
        # Socket.IO 클라이언트가 연결되어 있는지 확인
        if not sio.connected:
            await init_socketio_client()
        
        # Next.js Socket.IO 서버에 브로드캐스트 요청
        await sio.emit('broadcast-to-room', {
            'room_id': room_id,
            'event': 'new-message',
            'data': message_data
        })
        
        logger.info(f"📤 Socket.IO로 메시지 전송 완료: {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Socket.IO 메시지 전송 실패: {str(e)}")
        return False

# ========================================================================
# 전역 상태 관리
# ========================================================================

# 활성 토론 인스턴스들
active_debates: Dict[str, Any] = {}

# 메시지 히스토리 추적 (room_id -> last_message_count)
message_trackers: Dict[str, int] = {}

# ========================================================================
# API 라우터
# ========================================================================

router = APIRouter(prefix="/chat")

# Socket.IO 클라이언트 초기화 (서버 시작 시)
@router.on_event("startup")
async def startup_event():
    """서버 시작 시 Socket.IO 클라이언트 초기화"""
    await init_socketio_client()

@router.post("/create-debate-room")
async def create_debate_room(request: CreateDebateRoomRequest):
    """토론방 생성 및 실시간 진행 시작"""
    try:
        room_id = request.room_id
        
        # 중복 생성 방지
        if room_id in active_debates:
            raise HTTPException(status_code=400, detail=f"토론방 {room_id}이 이미 존재합니다")
        
        logger.info(f"🚀 Creating debate room {room_id}")
        
        # DebateDialogue 임포트 및 생성
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        # room_data 구성 (DebateDialogue가 기대하는 형식으로 수정)
        room_data = {
            'title': request.title,
            'context': request.context,
            'dialogueType': 'debate',
            'participants': {
                'pro': [{'character_id': npc_id} for npc_id in request.pro_npcs],
                'con': [{'character_id': npc_id} for npc_id in request.con_npcs],
                'users': request.user_ids  # user_id로 감싸지 않고 직접 리스트 전달
            },
            'moderator': {
                'style': request.moderator_style,
                'style_id': '0'
            }
        }
        
        print(f"🔍 ROOM_DATA: {room_data}")
        print(f"🔍 PRO_NPCS: {request.pro_npcs}")
        print(f"🔍 CON_NPCS: {request.con_npcs}")
        print(f"🔍 USER_IDS: {request.user_ids}")
        
        # DebateDialogue 생성 (기존 인터페이스 사용)
        dialogue = DebateDialogue(
            room_id=room_id,
            room_data=room_data,
            use_async_init=False,
            enable_streaming=False
        )
        
        # 활성 토론에 추가
        active_debates[room_id] = dialogue
        message_trackers[room_id] = 0
        
        # 인스턴스 생성만 하고 자동 메시지 생성은 하지 않음
        logger.info(f"✅ Debate room {room_id} created successfully")
        
        return {
            "status": "success",
            "room_id": room_id,
            "message": "토론방 생성 완료 - Next 버튼을 눌러 토론을 시작하세요",
            "debate_info": {
                "current_stage": "ready",
                "pro_participants": request.pro_npcs,
                "con_participants": request.con_npcs,
                "total_turns": 0
            }
        }
        
    except Exception as e:
        logger.error(f"❌ 토론방 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"토론방 생성 실패: {str(e)}")

@router.post("/debate/{room_id}/next-message")
async def get_next_message(room_id: str):
    """다음 메시지 생성 및 WebSocket 전송"""
    try:
        if room_id not in active_debates:
            raise HTTPException(status_code=404, detail="토론방을 찾을 수 없습니다")
        
        dialogue = active_debates[room_id]
        logger.info(f"🎭 Generating next message for room {room_id}")
        
        # generate_response() 호출
        response = dialogue.generate_response()
        
        if response.get("status") == "success":
            speaker = response.get("speaker_id", "unknown")
            message = response.get("message", "")
            current_stage = response.get("current_stage", "unknown")
            
            logger.info(f"✅ Message generated: {speaker} - {len(message)} chars")
            
            # Socket.IO로 메시지 전송 - 프론트엔드 형태에 맞게 수정
            message_payload = {
                "id": f"ai-{int(time.time() * 1000)}",  # 고유 ID 생성
                "text": message,
                "sender": speaker,
                "senderType": "npc",
                "isUser": False,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "stage": current_stage,
                    "event_type": "debate_message"
                }
            }
            
            await send_message_to_room(room_id, {
                "roomId": room_id,  # room_id -> roomId로 변경
                "message": message_payload
            })
            
            logger.info(f"📤 Message sent via Socket.IO to room {room_id}")
            
            return {
                "status": "success",
                "speaker": speaker,
                "message": message,
                "stage": current_stage
            }
            
        elif response.get("status") == "completed":
            logger.info(f"🏁 Debate completed for room {room_id}")
            
            # 토론 완료 알림
            await send_message_to_room(room_id, {
                "event_type": "debate_completed",
                "message": "토론이 완료되었습니다."
            })
            
            return {
                "status": "completed",
                "message": "토론이 완료되었습니다."
            }
            
        else:
            logger.error(f"❌ Failed to generate message: {response}")
            raise HTTPException(status_code=500, detail=f"메시지 생성 실패: {response}")
            
    except Exception as e:
        logger.error(f"❌ Error generating next message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"메시지 생성 실패: {str(e)}")

@router.delete("/debate/{room_id}")
async def cleanup_debate_room(room_id: str):
    """토론방 정리"""
    try:
        if room_id in active_debates:
            del active_debates[room_id]
        
        if room_id in message_trackers:
            del message_trackers[room_id]
            
        return {"status": "success", "message": f"토론방 {room_id} 정리 완료"}
        
    except Exception as e:
        logger.error(f"❌ 토론방 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"토론방 정리 실패: {str(e)}")

# ========================================================================
# Socket.IO 정리 함수
# ========================================================================

async def cleanup_socketio_client():
    """Socket.IO 클라이언트 정리"""
    try:
        if sio.connected:
            await sio.disconnect()
            logger.info("🔌 Socket.IO 클라이언트 연결 해제됨")
    except Exception as e:
        logger.error(f"❌ Socket.IO 클라이언트 정리 실패: {str(e)}")

@router.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 Socket.IO 클라이언트 정리"""
    await cleanup_socketio_client() 