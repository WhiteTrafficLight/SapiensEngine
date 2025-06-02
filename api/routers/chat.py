"""
실시간 토론 시스템 - 간단한 폴링 방식

기존 debate_test_transhumanism.py와 동일한 로직:
1. 백그라운드에서 dialogue.generate_response() 호출
2. 새 메시지 생성되면 즉시 웹소켓으로 전송
3. 콜백 없이 단순한 구조
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

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
# 전역 상태 관리
# ========================================================================

# 활성 토론 인스턴스들
active_debates: Dict[str, Any] = {}

# WebSocket 연결들 (room_id -> Set[WebSocket])
active_websockets: Dict[str, set] = {}

# 메시지 히스토리 추적 (room_id -> last_message_count)
message_trackers: Dict[str, int] = {}

# ========================================================================
# WebSocket 관리
# ========================================================================

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.connections:
            self.connections[room_id] = []
        self.connections[room_id].append(websocket)
        logger.info(f"🔌 WebSocket connected to room {room_id}")
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.connections:
            self.connections[room_id].remove(websocket)
            if not self.connections[room_id]:
                del self.connections[room_id]
        logger.info(f"🔌 WebSocket disconnected from room {room_id}")
    
    async def send_message_to_room(self, room_id: str, message: dict):
        """특정 방의 모든 연결된 클라이언트에게 메시지 전송"""
        if room_id not in self.connections:
            logger.warning(f"📤 No WebSocket connections for room {room_id}")
            return
            
        disconnected = []
        for websocket in self.connections[room_id]:
            try:
                await websocket.send_text(json.dumps(message))
                logger.info(f"📤 Message sent to room {room_id}: {message.get('speaker', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Failed to send message: {e}")
                disconnected.append(websocket)
        
        # 끊어진 연결 정리
        for ws in disconnected:
            self.disconnect(ws, room_id)

# 전역 WebSocket 매니저
websocket_manager = WebSocketManager()

# ========================================================================
# API 라우터
# ========================================================================

router = APIRouter(prefix="/chat")

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
            
            # 웹소켓으로 메시지 전송
            await send_message_to_websockets(room_id, {
                "event_type": "new_message",
                "speaker": speaker,
                "message": message,
                "stage": current_stage,
                "room_id": room_id
            })
            
            logger.info(f"📤 Message sent to WebSocket room {room_id}")
            
            return {
                "status": "success",
                "speaker": speaker,
                "message": message,
                "stage": current_stage
            }
            
        elif response.get("status") == "completed":
            logger.info(f"🏁 Debate completed for room {room_id}")
            
            # 토론 완료 알림
            await send_message_to_websockets(room_id, {
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

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """룸별 WebSocket 연결"""
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected to room {room_id}")
    
    # 룸에 WebSocket 추가
    if room_id not in active_websockets:
        active_websockets[room_id] = set()
    active_websockets[room_id].add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # 클라이언트에서 메시지 수신 시 처리 (필요시)
            logger.info(f"📨 Received from WebSocket in room {room_id}: {data}")
    except WebSocketDisconnect:
        # WebSocket 연결 해제
        active_websockets[room_id].discard(websocket)
        if not active_websockets[room_id]:
            del active_websockets[room_id]
        logger.info(f"🔌 WebSocket disconnected from room {room_id}")

@router.get("/debate/{room_id}/status")
async def get_debate_status(room_id: str):
    """토론 상태 조회"""
    if room_id not in active_debates:
        raise HTTPException(status_code=404, detail="토론방을 찾을 수 없습니다")
    
    dialogue = active_debates[room_id]
    speaking_history = dialogue.state.get("speaking_history", [])
    
    return {
        "room_id": room_id,
        "current_stage": dialogue.state.get("current_stage", "unknown"),
        "total_messages": len(speaking_history),
        "is_active": True
    }

@router.delete("/debate/{room_id}")
async def cleanup_debate_room(room_id: str):
    """토론방 정리"""
    try:
        if room_id in active_debates:
            del active_debates[room_id]
        
        if room_id in message_trackers:
            del message_trackers[room_id]
        
        if room_id in websocket_manager.connections:
            del websocket_manager.connections[room_id]
            
        return {"status": "success", "message": f"토론방 {room_id} 정리 완료"}
        
    except Exception as e:
        logger.error(f"❌ 토론방 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"토론방 정리 실패: {str(e)}")

# ========================================================================
# 백그라운드 자동 진행 (debate_test_transhumanism.py와 동일한 로직) - 주석처리
# ========================================================================

# async def auto_progress_debate(room_id: str):
#     """백그라운드에서 토론 자동 진행 - debate_test_transhumanism.py 로직 그대로"""
#     try:
#         logger.info(f"🚀 Auto-progress started for room {room_id}")
#         print(f"🚀 AUTO-PROGRESS: 토론방 {room_id} 자동 진행 시작")
#         
#         dialogue = active_debates.get(room_id)
#         
#         if not dialogue:
#             logger.error(f"❌ No dialogue found for room {room_id}")
#             print(f"❌ ERROR: 토론방 {room_id}를 찾을 수 없음")
#             return
#         
#         print(f"✅ DIALOGUE: 토론 인스턴스 확인됨 - {type(dialogue)}")
#         
#         # debate_test_transhumanism.py와 동일한 로직
#         max_turns = 15  # 최대 턴 수 제한
#         turn_count = 0
#         
#         while room_id in active_debates and turn_count < max_turns:
#             turn_count += 1
#             print(f"🎭 TURN {turn_count}: 시작")
#             
#             try:
#                 # 다음 발언자 확인 (debate_test_transhumanism.py와 동일)
#                 print(f"🔍 STEP 1: get_next_speaker() 호출")
#                 next_speaker_info = dialogue.get_next_speaker()
#                 print(f"🔍 NEXT_SPEAKER: {next_speaker_info}")
#                 
#                 if next_speaker_info.get("status") == "waiting":
#                     # 분석 대기 상태 (debate_test_transhumanism.py와 동일)
#                     speaker_id = next_speaker_info.get("speaker_id")
#                     logger.info(f"⏳ [{speaker_id}] 분석 완료 대기 중...")
#                     print(f"⏳ WAITING: {speaker_id} 분석 완료 대기 중...")
#                     
#                     # 분석 완료 강제 설정 (debate_test_transhumanism.py와 동일)
#                     if speaker_id in ["nietzsche", "hegel"]:  # marx → hegel로 변경
#                         print(f"force_analysis_completion 호출")
#                         dialogue.force_analysis_completion(speaker_id)
#                         logger.info(f"✅ [{speaker_id}] 분석 완료 처리")
#                         print(f"✅ FORCED: {speaker_id} 분석 완료 강제 처리됨")
#                     
#                     # ⭐ 핵심: waiting 상태라도 continue 하지 말고 generate_response() 호출
#                     # continue 제거!
#                 
#                 if not next_speaker_info.get("can_proceed", True):
#                     print(f"❌ 토론 진행 불가: {next_speaker_info}")
#                     break
#                 
#                 speaker_id = next_speaker_info.get("speaker_id")
#                 if not speaker_id:
#                     print(f"✅ 토론 완료!")
#                     break
#                 
#                 # ⭐ 핵심: 항상 generate_response() 호출 (debate_test_transhumanism.py와 동일)
#                 print(f"🔍 STEP 2: generate_response() 호출")
#                 response = await asyncio.to_thread(dialogue.generate_response)
#                 print(f"🔍 RESPONSE: {response.get('status')} - {response.get('speaker_id')}")
#                 
#                 if response.get("status") == "success":
#                     speaker = response.get("speaker_id", "unknown")
#                     message = response.get("message", "")
#                     current_stage = response.get("current_stage", "unknown")
#                     
#                     print(f"✅ SUCCESS: {speaker} 메시지 생성됨 (길이: {len(message)})")
#                     
#                     # 웹소켓으로 메시지 전송
#                     await send_message_to_websockets(room_id, {
#                         "event_type": "new_message",
#                         "speaker": speaker,
#                         "message": message,
#                         "stage": current_stage,
#                         "turn": turn_count
#                     })
#                     
#                     # 단계별 대기 시간 (debate_test_transhumanism.py와 동일)
#                     if current_stage in ["pro_argument", "con_argument"]:
#                         await asyncio.sleep(1)  # 입론 단계
#                     elif current_stage == "interactive_argument":
#                         await asyncio.sleep(0.5)  # 상호논증 단계
#                     else:
#                         await asyncio.sleep(0.5)  # 기타 단계
#                     
#                 elif response.get("status") == "completed":
#                     print(f"🏁 토론 완료!")
#                     await send_message_to_websockets(room_id, {
#                         "event_type": "debate_completed"
#                     })
#                     break
#                 else:
#                     print(f"❌ 응답 생성 실패: {response}")
#                     break
#                     
#             except Exception as e:
#                 print(f"❌ TURN {turn_count} 실패: {str(e)}")
#                 logger.error(f"Error in turn {turn_count}: {str(e)}")
#                 break
#         
#         print(f"🏁 AUTO-PROGRESS 완료: {turn_count} 턴 진행")
#         
#     except Exception as e:
#         logger.error(f"❌ Auto-progress failed for room {room_id}: {str(e)}")
#         print(f"❌ AUTO-PROGRESS 실패: {str(e)}")

async def send_message_to_websockets(room_id: str, message_data: Dict[str, Any]):
    """룸의 모든 WebSocket 연결에 메시지 전송"""
    if room_id in active_websockets:
        websockets_in_room = active_websockets[room_id].copy()
        for websocket in websockets_in_room:
            try:
                await websocket.send_text(json.dumps(message_data))
                logger.info(f"📤 Sent message to WebSocket in room {room_id}")
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {str(e)}")
                # 연결이 끊어진 WebSocket 제거
                active_websockets[room_id].discard(websocket) 