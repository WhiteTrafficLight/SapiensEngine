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
    user_side: str = "neutral"  # "pro", "con", "neutral" 중 하나
    moderator_style: str = "Jamie the Host"
    moderator_style_id: str = "0"  # 모더레이터 스타일 ID 추가

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
                'pro': [],
                'con': [],
                'users': request.user_ids
            },
            'moderator': {
                'style': request.moderator_style,
                'style_id': request.moderator_style_id
            }
        }
        
        # NPC 배치
        for npc_id in request.pro_npcs:
            room_data['participants']['pro'].append({'character_id': npc_id})
        
        for npc_id in request.con_npcs:
            room_data['participants']['con'].append({'character_id': npc_id})
        
        # 사용자 배치 (테스트 파일과 동일한 구조)
        for user_id in request.user_ids:
            if request.user_side == "pro":
                room_data['participants']['pro'].append({
                    'id': user_id,
                    'name': '사용자',
                    'is_user': True
                })
            elif request.user_side == "con":
                room_data['participants']['con'].append({
                    'id': user_id,
                    'name': '사용자',
                    'is_user': True
                })
            # neutral인 경우는 별도 처리 없음 (users 배열에만 존재)
        
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
        logger.info(f"🎭 Getting next speaker info for room {room_id}")
        
        # 1. 먼저 다음 발언자 정보 가져오기
        next_speaker_info = dialogue.get_next_speaker()
        
        if next_speaker_info.get("speaker_id") is None:
            return {
                "status": "completed",
                "message": "토론이 완료되었습니다."
            }
        
        speaker_id = next_speaker_info.get("speaker_id")
        speaker_role = next_speaker_info.get("role")
        current_stage = dialogue.state["current_stage"]
        
        logger.info(f"🎯 Next speaker: {speaker_id} ({speaker_role}) in stage {current_stage}")
        
        # 2. 사용자 차례인지 확인
        user_participants = dialogue.user_participants if hasattr(dialogue, 'user_participants') else {}
        participants_data = dialogue.room_data.get('participants', {})
        user_ids = participants_data.get('users', [])
        
        logger.info(f"🔍 User participants: {list(user_participants.keys())}")
        logger.info(f"🔍 User IDs from room data: {user_ids}")
        logger.info(f"🔍 Speaker ID: {speaker_id}")
        
        # 사용자 차례 확인 - 두 가지 방법으로 체크
        is_user_turn = (speaker_id in user_participants) or (speaker_id in user_ids)
        
        logger.info(f"🔍 Is user turn? {is_user_turn}")
        
        if is_user_turn:
            # 사용자 차례인 경우 - 즉시 사용자 정보 반환 (테스트 파일과 동일한 로직)
            logger.info(f"👤 USER TURN DETECTED - {speaker_id} ({speaker_role})")
            return {
                "status": "success",
                "next_speaker": {
                    "speaker_id": speaker_id,
                    "role": speaker_role,
                    "is_user": True
                },
                "stage": current_stage,
                "message": f"현재 {speaker_id}의 차례입니다 - 사용자 입력 필요"
            }
        else:
            # AI 차례인 경우 - 기존 로직 (generating 상태 반환 후 백그라운드 생성)
            logger.info(f"🤖 AI TURN DETECTED - {speaker_id} ({speaker_role})")
            response_data = {
                "status": "generating",
                "speaker_id": speaker_id,
                "speaker_role": speaker_role,
                "stage": current_stage,
                "message": "메시지 생성 중..."
            }
            
            # 백그라운드에서 실제 메시지 생성 시작
            asyncio.create_task(generate_message_async(room_id, dialogue, speaker_id, speaker_role, current_stage))
            
            return response_data
            
    except Exception as e:
        logger.error(f"❌ Error getting next speaker info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"다음 발언자 정보 조회 실패: {str(e)}")

async def generate_message_async(room_id: str, dialogue, speaker_id: str, speaker_role: str, original_stage: str):
    """백그라운드에서 메시지 생성 및 Socket.IO 전송"""
    try:
        logger.info(f"🔄 Background message generation started for {speaker_id}")
        
        # generate_response() 호출
        response = dialogue.generate_response()
        
        if response.get("status") == "success":
            message = response.get("message", "")
            
            logger.info(f"✅ Message generated: {speaker_id} - {len(message)} chars")
            logger.info(f"📍 Message stage: {original_stage}")
            
            # RAG 정보 추출 (speaking_history의 마지막 메시지에서)
            rag_info = {}
            if hasattr(dialogue, 'state') and 'speaking_history' in dialogue.state:
                speaking_history = dialogue.state['speaking_history']
                if speaking_history:
                    last_message = speaking_history[-1]
                    if last_message.get('speaker_id') == speaker_id:
                        rag_info = {
                            "rag_used": last_message.get("rag_used", False),
                            "rag_source_count": last_message.get("rag_source_count", 0),
                            "rag_sources": last_message.get("rag_sources", [])
                        }
                        if rag_info["rag_used"]:
                            logger.info(f"🔍 RAG was used: {rag_info['rag_source_count']} sources")
            
            # Socket.IO로 완성된 메시지 전송
            message_payload = {
                "id": f"ai-{int(time.time() * 1000)}",  # 고유 ID 생성
                "text": message,
                "sender": speaker_id,
                "senderType": "npc",
                "isUser": False,
                "timestamp": datetime.now().isoformat(),
                "role": "moderator" if speaker_id == "moderator" else ("pro" if speaker_role == "pro" else "con"),
                "stage": original_stage,
                "metadata": {
                    "stage": original_stage,
                    "event_type": "debate_message_complete",  # 완성된 메시지임을 표시
                    **rag_info  # RAG 정보 포함
                }
            }
            
            await send_message_to_room(room_id, {
                "roomId": room_id,
                "message": message_payload
            })
            
            logger.info(f"📤 Completed message sent via Socket.IO to room {room_id}")
            
        elif response.get("status") == "completed":
            logger.info(f"🏁 Debate completed for room {room_id}")
            
            # 토론 완료 알림
            await send_message_to_room(room_id, {
                "event_type": "debate_completed",
                "message": "토론이 완료되었습니다."
            })
            
        else:
            logger.error(f"❌ Failed to generate message: {response}")
            # 오류 메시지 전송
            await send_message_to_room(room_id, {
                "event_type": "message_generation_error",
                "message": f"메시지 생성 실패: {response}"
            })
            
    except Exception as e:
        logger.error(f"❌ Error in background message generation: {str(e)}")
        # 오류 메시지 전송
        await send_message_to_room(room_id, {
            "event_type": "message_generation_error", 
            "message": f"메시지 생성 중 오류 발생: {str(e)}"
        })

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

@router.post("/debate/{room_id}/process-user-message")
async def process_user_message(room_id: str, request: dict):
    """사용자 메시지 처리 및 대화에 반영"""
    try:
        if room_id not in active_debates:
            raise HTTPException(status_code=404, detail="토론방을 찾을 수 없습니다")
        
        dialogue = active_debates[room_id]
        message = request.get("message", "")
        user_id = request.get("user_id", "")
        
        if not message or not user_id:
            raise HTTPException(status_code=400, detail="메시지와 사용자 ID가 필요합니다")
        
        logger.info(f"🎯 Processing user message from {user_id} in room {room_id}")
        logger.info(f"📝 Message: {message[:100]}...")
        
        # dialogue.process_message() 호출 (테스트 파일과 동일한 로직)
        result = dialogue.process_message(message, user_id)
        
        if result.get("status") == "success":
            logger.info(f"✅ User message processed successfully")
            
            # Socket.IO로 사용자 메시지 전송 (즉시)
            message_data = {
                "id": f"{user_id}-{int(time.time())}",
                "text": message,
                "sender": user_id,
                "isUser": True,
                "timestamp": time.time(),
                "role": result.get("role", "user"),
                "stage": result.get("stage", "unknown"),
                "skipAnimation": False,  # 사용자 메시지는 애니메이션 없이 즉시 표시
                "metadata": {
                    "event_type": "user_message",
                    "rag_used": False,  # 사용자 메시지는 RAG 사용 안함
                    "rag_source_count": 0,
                    "rag_sources": []
                }
            }
            
            await send_message_to_room(room_id, {
                "roomId": room_id,
                "message": message_data
            })
            
            logger.info(f"📤 User message sent via Socket.IO")
            
            return {
                "status": "success",
                "message": "사용자 메시지가 성공적으로 처리되었습니다",
                "speaker_id": user_id,
                "role": result.get("role"),
                "stage": result.get("stage"),
                "turn_count": result.get("turn_count")
            }
        
        elif result.get("status") == "paused":
            return {
                "status": "paused",
                "message": "토론이 일시정지 상태입니다"
            }
        
        elif result.get("status") == "error":
            error_reason = result.get("reason", "unknown")
            if error_reason == "not_your_turn":
                return {
                    "status": "error",
                    "reason": "not_your_turn",
                    "message": result.get("message", "현재 귀하의 차례가 아닙니다"),
                    "next_speaker": result.get("next_speaker")
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("message", "사용자 메시지 처리 중 오류가 발생했습니다")
                }
        
        else:
            return {
                "status": "error", 
                "message": "알 수 없는 처리 결과입니다"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing user message: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 메시지 처리 실패: {str(e)}")

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