"""
실시간 토론 시스템 - fastapi-sio 통합

Socket.IO 서버를 통한 실시간 브로드캐스트
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import psutil
import os
import redis

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

class SendMessageRequest(BaseModel):
    room_id: str
    user_id: str
    message: str
    side: str = "neutral"  # "pro", "con", "neutral"

# ========================================================================
# Socket.IO 브로드캐스트 함수
# ========================================================================

async def send_message_to_room(room_id: str, message_data: Dict[str, Any]):
    """Socket.IO를 통해 특정 방에 메시지 전송"""
    try:
        # main.py에서 정의된 함수를 import해서 사용
        from main import send_message_to_room as broadcast_func
        return await broadcast_func(room_id, message_data)
        
    except ImportError:
        logger.error("❌ Could not import send_message_to_room from main.py")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send message to room {room_id}: {e}")
        return False

# ========================================================================
# Socket.IO 이벤트 핸들러 등록 (main.py의 sio 서버와 연동)
# ========================================================================

def register_socketio_handlers():
    """main.py의 Socket.IO 서버에 chat 관련 이벤트 핸들러 등록"""
    try:
        # main.py의 sio 서버 import
        from main import sio
        
        @sio.event
        async def leave_room(sid, data):
            """사용자가 방을 떠날 때 처리 (chat.py에서 덮어쓰기)"""
            room_id = data.get('room_id')
            user_id = data.get('user_id')
            
            if not room_id or not user_id:
                return {"error": "room_id and user_id required"}
            
            logger.info(f"📤 [CHAT] User {user_id} leaving room {room_id} (chat.py handler)")
            logger.info(f"🔍 [CHAT] Active debates before cleanup: {list(active_debates.keys())}")
            logger.info(f"🔍 [CHAT] User room mapping before cleanup: {dict(user_room_mapping)}")
            
            # main.py의 Socket.IO 방 관리도 처리
            try:
                from main import room_users
                if room_id in room_users and user_id in room_users[room_id]:
                    room_users[room_id].remove(user_id)
                    if not room_users[room_id]:  # 방이 비어있으면 삭제
                        del room_users[room_id]
                
                # Socket.IO 방에서 떠나기
                await sio.leave_room(sid, room_id)
                logger.info(f"✅ [CHAT] Socket.IO room management completed")
            except Exception as e:
                logger.error(f"❌ [CHAT] Error in Socket.IO room management: {str(e)}")
            
            # chat.py의 상태를 직접 사용하여 정리
            success = await cleanup_user_from_room(user_id, room_id)
            
            logger.info(f"🔍 [CHAT] Active debates after cleanup: {list(active_debates.keys())}")
            logger.info(f"🔍 [CHAT] User room mapping after cleanup: {dict(user_room_mapping)}")
            
            # 방의 다른 사용자들에게 알림
            try:
                from main import room_users
                if room_id in room_users:
                    await sio.emit("user_left", {
                        "user_id": user_id,
                        "message": f"{user_id}님이 방을 떠났습니다",
                        "room_count": len(room_users[room_id])
                    }, room=room_id)
            except Exception as e:
                logger.error(f"❌ [CHAT] Error sending user_left notification: {str(e)}")
            
            if success:
                logger.info(f"✅ [CHAT] Successfully cleaned up user {user_id} from room {room_id}")
                return {"success": True, "message": f"Successfully left room {room_id}"}
            else:
                logger.warning(f"⚠️ [CHAT] Failed to clean up user {user_id} from room {room_id}")
                return {"success": False, "message": f"Failed to clean up user {user_id}"}
        
        @sio.event  
        async def user_disconnected(sid, data):
            """사용자 연결 해제 시 자동 정리 (chat.py에서 덮어쓰기)"""
            try:
                user_id = data.get('user_id')
                room_id = data.get('room_id')
                
                if user_id:
                    logger.info(f"🔌 [CHAT] User disconnected: {user_id} (chat.py handler)")
                    
                    # user_room_mapping에서 room_id 찾기 (chat.py 내부 상태 직접 사용)
                    if not room_id and user_id in user_room_mapping:
                        room_id = user_room_mapping[user_id]
                        logger.info(f"🔍 [CHAT] Found room_id from internal mapping: {room_id}")
                    
                    if room_id:
                        logger.info(f"🔍 [CHAT] Before auto-cleanup - Active debates: {list(active_debates.keys())}")
                        logger.info(f"🔍 [CHAT] Before auto-cleanup - User mapping: {dict(user_room_mapping)}")
                        
                        success = await cleanup_user_from_room(user_id, room_id)
                        
                        logger.info(f"🔍 [CHAT] After auto-cleanup - Active debates: {list(active_debates.keys())}")
                        logger.info(f"🔍 [CHAT] After auto-cleanup - User mapping: {dict(user_room_mapping)}")
                        
                        if success:
                            logger.info(f"✅ [CHAT] Auto-cleaned up disconnected user {user_id} from room {room_id}")
                        else:
                            logger.warning(f"⚠️ [CHAT] Failed to auto-clean up user {user_id}")
                    else:
                        logger.warning(f"⚠️ [CHAT] Could not find room for disconnected user {user_id}")
                else:
                    logger.warning(f"⚠️ [CHAT] user_disconnected called without user_id")
            except Exception as e:
                logger.error(f"❌ [CHAT] Error handling user disconnection: {str(e)}")
                import traceback
                logger.error(f"📋 [CHAT] Disconnect traceback: {traceback.format_exc()}")
        
        logger.info("✅ Chat Socket.IO handlers registered (overriding main.py handlers)")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import main.sio: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to register Socket.IO handlers: {str(e)}")
        return False

# ========================================================================
# 라우터 초기화
# ========================================================================

router = APIRouter()

# 서버 시작 시 백그라운드 모니터링 시작
@router.on_event("startup")
async def startup_event():
    """서버 시작 시 백그라운드 모니터링 시작"""
    await start_background_monitoring()
    
    # Socket.IO 이벤트 핸들러 등록 (중요!)
    register_success = register_socketio_handlers()
    if register_success:
        logger.info("✅ Socket.IO handlers registered for chat module")
    else:
        logger.error("❌ Failed to register Socket.IO handlers for chat module")

# 서버 종료 시 백그라운드 모니터링 중지
@router.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 백그라운드 모니터링 중지"""
    await stop_background_monitoring()

# ========================================================================
# Redis 연결 설정
# ========================================================================

try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD', None),
        decode_responses=True
    )
    # 연결 테스트
    redis_client.ping()
    logger.info("✅ Redis connection established")
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}")
    redis_client = None

# ========================================================================
# 확장 가능한 상태 관리
# ========================================================================

# 활성 토론 인스턴스들 (메모리)
active_debates: Dict[str, Any] = {}

# 메시지 히스토리 추적 (room_id -> last_message_count)
message_trackers: Dict[str, int] = {}

# 사용자별 활성 토론방 추적 (user_id -> room_id)
user_room_mapping: Dict[str, str] = {}

# 토론방별 사용자 목록 (room_id -> set of user_ids)
room_user_mapping: Dict[str, set] = {}

# 토론방 생성 시간 추적 (메모리 관리용)
room_creation_times: Dict[str, datetime] = {}

# 토론방 마지막 활동 시간 추적
room_last_activity: Dict[str, datetime] = {}

# 확장성 설정
MAX_ACTIVE_ROOMS = 50  # 최대 동시 토론방 수
MAX_INACTIVE_HOURS = 2  # 비활성 토론방 자동 정리 시간 (시간)
MEMORY_CHECK_INTERVAL = 10  # 메모리 체크 간격 (분)
MAX_MEMORY_USAGE_GB = 8  # 최대 메모리 사용량 (GB)

# 백그라운드 작업 관리
background_tasks = {}

# ========================================================================
# 메모리 모니터링 및 자동 정리
# ========================================================================

def get_memory_usage() -> Dict[str, float]:
    """현재 메모리 사용량 조회 (개선된 버전)"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_gb = memory_info.rss / (1024 ** 3)  # bytes to GB
        
        # 시스템 전체 메모리 정보
        virtual_memory = psutil.virtual_memory()
        
        return {
            "used_gb": memory_gb,
            "available_gb": virtual_memory.available / (1024 ** 3),
            "usage_percent": virtual_memory.percent,
            "total_gb": virtual_memory.total / (1024 ** 3)
        }
    except Exception as e:
        logger.error(f"❌ Memory usage check failed: {str(e)}")
        return {"used_gb": 0.1, "available_gb": 8.0, "usage_percent": 10.0, "total_gb": 8.0}  # 기본값 반환

def update_room_activity(room_id: str):
    """토론방 활동 시간 업데이트"""
    room_last_activity[room_id] = datetime.now()

# ========================================================================
# 정리 함수들
# ========================================================================

async def comprehensive_debate_cleanup(room_id: str):
    """토론방 완전 리소스 정리 (안전한 버전)"""
    logger.info(f"🧹 Starting safe cleanup for room {room_id}")
    
    try:
        # 1. 기본 정리
        if room_id in active_debates:
            debate_instance = active_debates[room_id]
            
            # 🛑 안전한 정지 시그널 전송
            if hasattr(debate_instance, 'force_stop_all_background_work'):
                try:
                    debate_instance.force_stop_all_background_work()
                    logger.info(f"✅ Safely stopped background work for room {room_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error in safe stop: {e}")
            
            # 🧹 기본 정리 호출 (async 처리 수정)
            if hasattr(debate_instance, 'cleanup_resources'):
                try:
                    cleanup_method = debate_instance.cleanup_resources
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
                    logger.info(f"✅ Basic cleanup completed for room {room_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error in basic cleanup: {e}")
            
            # active_debates에서 제거
            del active_debates[room_id]
            logger.info(f"✅ Removed debate instance for room {room_id}")
        
        # 2. Socket.IO 방 정리 (sio 변수 수정)
        try:
            # 글로벌 sio 가져오기
            from api.main import sio
            
            # 방의 모든 연결을 안전하게 정리
            if hasattr(sio, 'manager'):
                try:
                    # Socket.IO의 방 멤버들 확인
                    room_members = []
                    if hasattr(sio.manager, 'get_participants'):
                        room_members = await sio.manager.get_participants(sio.namespace, room_id)
                    logger.info(f"🔌 Found {len(room_members)} participants in room {room_id}")
                    
                    # 각 참가자를 안전하게 방에서 제거
                    for sid in room_members:
                        try:
                            await sio.leave_room(sid, room_id)
                            logger.info(f"✅ Safely removed session {sid} from room {room_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ Error removing session {sid}: {e}")
                            
                except Exception as e:
                    logger.warning(f"⚠️ Error getting room participants: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Error in Socket.IO cleanup: {e}")
        
        # 3. 매핑 정리
        if room_id in room_user_mapping:
            del room_user_mapping[room_id]
            logger.info(f"✅ Cleaned room user mapping for {room_id}")
        
        # 4. 안전한 메모리 정리
        try:
            import gc
            collected = gc.collect()
            logger.info(f"🧹 Collected {collected} objects during room cleanup")
        except Exception as e:
            logger.warning(f"⚠️ Error in memory cleanup: {e}")
        
        logger.info(f"✅ Safe cleanup completed for room {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in comprehensive cleanup for room {room_id}: {e}")
        return False

async def cleanup_debate_room(room_id: str, reason: str = "manual"):
    """토론방 정리 - 인스턴스 삭제 및 상태 정리 (개선된 로깅 버전)"""
    try:
        logger.info(f"🧹 Starting cleanup for room {room_id} (reason: {reason})")
        
        # 토론 인스턴스 정리
        if room_id in active_debates:
            dialogue = active_debates[room_id]
            
            # 포괄적 정리 함수 호출
            cleanup_success = await comprehensive_debate_cleanup(room_id)
            
            if cleanup_success:
                logger.info(f"✅ Comprehensive cleanup completed for {room_id}")
            else:
                logger.warning(f"⚠️ Some cleanup operations failed for {room_id}")
            
            # 인스턴스 삭제
            del active_debates[room_id]
            logger.info(f"✅ Removed debate instance for {room_id}")
        
        # 메시지 트래커 정리
        if room_id in message_trackers:
            del message_trackers[room_id]
            logger.info(f"✅ Removed message tracker for {room_id}")
        
        # 사용자 매핑 정리
        users_to_remove = []
        for user_id, mapped_room_id in user_room_mapping.items():
            if mapped_room_id == room_id:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del user_room_mapping[user_id]
            logger.info(f"✅ Removed user mapping for {user_id}")
        
        # 방 사용자 목록 정리
        if room_id in room_user_mapping:
            del room_user_mapping[room_id]
            logger.info(f"✅ Removed room user mapping for {room_id}")
        
        # 생성 시간 추적 정리
        if room_id in room_creation_times:
            del room_creation_times[room_id]
            logger.info(f"✅ Removed room creation time for {room_id}")
        
        # 활동 시간 추적 정리
        if room_id in room_last_activity:
            del room_last_activity[room_id]
            logger.info(f"✅ Removed room activity time for {room_id}")
        
        # 가비지 컬렉션 강제 실행 (메모리 정리 확실히)
        import gc
        gc.collect()
        logger.info(f"✅ Forced garbage collection for {room_id}")
        
        logger.info(f"🧹 Cleanup completed for room {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed for room {room_id}: {str(e)}")
        return False

async def cleanup_user_from_room(user_id: str, room_id: str):
    """특정 사용자를 방에서 제거하고, 방이 비어있으면 정리 (개선된 로깅 버전)"""
    try:
        logger.info(f"👤 Removing user {user_id} from room {room_id}")
        
        # 사용자 매핑에서 제거
        if user_id in user_room_mapping and user_room_mapping[user_id] == room_id:
            del user_room_mapping[user_id]
            logger.info(f"✅ Removed user mapping for {user_id}")
        
        # 방 사용자 목록에서 제거
        if room_id in room_user_mapping:
            room_user_mapping[room_id].discard(user_id)
            remaining_users = len(room_user_mapping[room_id])
            logger.info(f"📊 Room {room_id} now has {remaining_users} users remaining")
            
            # 방이 비어있으면 토론방 정리
            if remaining_users == 0:
                logger.info(f"🏠 Room {room_id} is now empty, cleaning up...")
                success = await cleanup_debate_room(room_id, "empty_room")
                if success:
                    logger.info(f"✅ Empty room {room_id} cleaned up successfully")
                else:
                    logger.warning(f"⚠️ Failed to clean up empty room {room_id}")
                return success
        
        logger.info(f"✅ User {user_id} removed from room {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to remove user {user_id} from room {room_id}: {str(e)}")
        return False

# ========================================================================
# 토론방 관리 함수들
# ========================================================================

def get_room_data(room_id: str) -> Dict[str, Any]:
    """Redis에서 방 데이터 가져오기"""
    if not redis_client:
        return {}
    
    try:
        room_data = redis_client.hgetall(f"room:{room_id}")
        if room_data:
            # JSON 문자열들을 파싱
            for key in ['pro_npcs', 'con_npcs', 'user_ids']:
                if key in room_data:
                    room_data[key] = json.loads(room_data[key])
        return room_data
    except Exception as e:
        logger.error(f"❌ Failed to get room data: {e}")
        return {}

def save_room_data(room_id: str, room_data: Dict[str, Any]) -> bool:
    """Redis에 방 데이터 저장"""
    if not redis_client:
        return False
    
    try:
        # 리스트들을 JSON 문자열로 변환
        save_data = room_data.copy()
        for key in ['pro_npcs', 'con_npcs', 'user_ids']:
            if key in save_data:
                save_data[key] = json.dumps(save_data[key])
        
        redis_client.hmset(f"room:{room_id}", save_data)
        redis_client.expire(f"room:{room_id}", 86400)  # 24시간 후 만료
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save room data: {e}")
        return False

def add_message_to_room(room_id: str, message_data: Dict[str, Any]) -> bool:
    """방에 메시지 추가"""
    if not redis_client:
        return False
    
    try:
        message_json = json.dumps(message_data)
        redis_client.lpush(f"room:{room_id}:messages", message_json)
        redis_client.expire(f"room:{room_id}:messages", 86400)  # 24시간 후 만료
        # 최대 1000개 메시지만 유지
        redis_client.ltrim(f"room:{room_id}:messages", 0, 999)
        return True
    except Exception as e:
        logger.error(f"❌ Failed to add message: {e}")
        return False

# ========================================================================
# API 엔드포인트들
# ========================================================================

async def check_memory_and_cleanup():
    """메모리 사용량 체크 및 필요 시 자동 정리 (개선된 로깅 버전)"""
    try:
        memory_stats = get_memory_usage()
        current_rooms = len(active_debates)
        
        logger.info(f"💾 Memory: {memory_stats['used_gb']:.2f}GB/{memory_stats['total_gb']:.1f}GB ({memory_stats['usage_percent']:.1f}%), Rooms: {current_rooms}")
        
        # 메모리 부족 또는 방 개수 초과 시 정리
        should_cleanup = (
            memory_stats['used_gb'] > MAX_MEMORY_USAGE_GB or
            current_rooms > MAX_ACTIVE_ROOMS or
            memory_stats['usage_percent'] > 80
        )
        
        if should_cleanup:
            logger.warning(f"🚨 High resource usage detected:")
            logger.warning(f"   - Memory: {memory_stats['used_gb']:.2f}GB > {MAX_MEMORY_USAGE_GB}GB: {memory_stats['used_gb'] > MAX_MEMORY_USAGE_GB}")
            logger.warning(f"   - Rooms: {current_rooms} > {MAX_ACTIVE_ROOMS}: {current_rooms > MAX_ACTIVE_ROOMS}")
            logger.warning(f"   - Memory %: {memory_stats['usage_percent']:.1f}% > 80%: {memory_stats['usage_percent'] > 80}")
            logger.warning(f"   - Triggering cleanup...")
            
            cleanup_count = await emergency_cleanup_inactive_rooms()
            logger.info(f"🧹 Cleanup completed: {cleanup_count} rooms cleaned")
        
        return memory_stats
        
    except Exception as e:
        logger.error(f"❌ Memory check failed: {str(e)}")
        return {}

async def emergency_cleanup_inactive_rooms():
    """긴급 메모리 정리 - 비활성 토론방 강제 정리"""
    try:
        current_time = datetime.now()
        rooms_to_cleanup = []
        
        # 1. 마지막 활동이 오래된 방 찾기
        for room_id in list(active_debates.keys()):
            last_activity = room_last_activity.get(room_id, current_time)
            inactive_hours = (current_time - last_activity).total_seconds() / 3600
            
            if inactive_hours > MAX_INACTIVE_HOURS:
                rooms_to_cleanup.append((room_id, inactive_hours))
        
        # 2. 비활성 시간 순으로 정렬 (가장 오래된 것부터)
        rooms_to_cleanup.sort(key=lambda x: x[1], reverse=True)
        
        # 3. 필요한 만큼 정리
        memory_stats = get_memory_usage()
        cleanup_count = 0
        
        for room_id, inactive_hours in rooms_to_cleanup:
            if (memory_stats['used_gb'] < MAX_MEMORY_USAGE_GB * 0.7 and 
                len(active_debates) < MAX_ACTIVE_ROOMS * 0.8):
                break  # 충분히 정리됨
                
            await cleanup_debate_room(room_id, f"emergency_cleanup_inactive_{inactive_hours:.1f}h")
            cleanup_count += 1
            
            # 메모리 재확인
            memory_stats = get_memory_usage()
        
        logger.info(f"🧹 Emergency cleanup: {cleanup_count} rooms cleaned")
        return cleanup_count
        
    except Exception as e:
        logger.error(f"❌ Emergency cleanup failed: {str(e)}")
        return 0

@router.post("/create-debate-room")
async def create_debate_room(request: CreateDebateRoomRequest):
    """토론방 생성 및 실시간 진행 시작 (확장성 개선 버전)"""
    try:
        room_id = request.room_id
        
        # 메모리 체크 및 필요 시 정리
        memory_stats = await check_memory_and_cleanup()
        
        # 최대 방 개수 제한 체크
        if len(active_debates) >= MAX_ACTIVE_ROOMS:
            logger.warning(f"🚨 Max rooms limit reached: {len(active_debates)}/{MAX_ACTIVE_ROOMS}")
            await emergency_cleanup_inactive_rooms()
            
            # 정리 후에도 제한 초과 시 거부
            if len(active_debates) >= MAX_ACTIVE_ROOMS:
                raise HTTPException(
                    status_code=503, 
                    detail=f"서버 용량 초과: 최대 {MAX_ACTIVE_ROOMS}개 토론방까지 지원"
                )
        
        # 중복 생성 방지
        if room_id in active_debates:
            raise HTTPException(status_code=400, detail=f"토론방 {room_id}이 이미 존재합니다")
        
        logger.info(f"🚀 Creating debate room {room_id} (Memory: {memory_stats.get('used_gb', 0):.1f}GB)")
        
        # DebateDialogue 임포트 및 생성
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        # room_data 구성
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
        
        # 사용자 배치
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
        
        # DebateDialogue 생성
        dialogue = DebateDialogue(
            room_id=room_id,
            room_data=room_data,
            use_async_init=False,
            enable_streaming=False
        )
        
        # 활성 토론에 추가
        active_debates[room_id] = dialogue
        message_trackers[room_id] = 0
        
        # 확장성 관리용 추적 정보 추가
        current_time = datetime.now()
        room_creation_times[room_id] = current_time
        room_last_activity[room_id] = current_time
        
        # 사용자 매핑 추가
        for user_id in request.user_ids:
            user_room_mapping[user_id] = room_id
        
        # 방 사용자 목록 초기화
        room_user_mapping[room_id] = set(request.user_ids)
        
        # 생성 후 메모리 상태 로깅
        post_memory = get_memory_usage()
        logger.info(f"✅ Room {room_id} created - Memory: {post_memory['used_gb']:.1f}GB, Total rooms: {len(active_debates)}")
        
        return {
            "status": "success",
            "room_id": room_id,
            "message": "토론방 생성 완료 - Next 버튼을 눌러 토론을 시작하세요",
            "debate_info": {
                "current_stage": "ready",
                "pro_participants": request.pro_npcs,
                "con_participants": request.con_npcs,
                "total_turns": 0
            },
            "system_info": {
                "memory_usage_gb": post_memory['used_gb'],
                "active_rooms": len(active_debates),
                "max_rooms": MAX_ACTIVE_ROOMS
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
        
        # 방 활동 시간 업데이트
        update_room_activity(room_id)
        
        dialogue = active_debates[room_id]
        logger.info(f"🎭 Getting next speaker info for room {room_id}")
        
        # 다음 발언자 정보 가져오기
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
        
        # 사용자 차례인지 확인
        user_participants = dialogue.user_participants if hasattr(dialogue, 'user_participants') else {}
        participants_data = dialogue.room_data.get('participants', {})
        user_ids = participants_data.get('users', [])
        
        is_user_turn = (speaker_id in user_participants) or (speaker_id in user_ids)
        
        if is_user_turn:
            # 사용자 차례인 경우
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
            # AI 차례인 경우
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
            
    except HTTPException:
        # 이미 의미 있는 상태코드가 설정된 HTTPException은 그대로 전달
        raise
    except Exception as e:
        logger.error(f"❌ Error getting next speaker info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"다음 발언자 정보 조회 실패: {str(e)}")

async def generate_message_async(room_id: str, dialogue, speaker_id: str, speaker_role: str, original_stage: str):
    """백그라운드에서 메시지 생성 및 Socket.IO 전송 (RAG 정보 포함)"""
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
                            "rag_sources": last_message.get("rag_sources", []),
                            "citations": last_message.get("citations", [])
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

@router.post("/debate/{room_id}/process-user-message")
async def process_user_message(room_id: str, request: dict):
    """사용자 메시지 처리 및 대화에 반영 (활동 추적 포함)"""
    try:
        if room_id not in active_debates:
            raise HTTPException(status_code=404, detail="토론방을 찾을 수 없습니다")
        
        # 방 활동 시간 업데이트
        update_room_activity(room_id)
        
        dialogue = active_debates[room_id]
        message = request.get("message", "")
        user_id = request.get("user_id", "")
        
        if not message or not user_id:
            raise HTTPException(status_code=400, detail="메시지와 사용자 ID가 필요합니다")
        
        logger.info(f"🎯 Processing user message from {user_id} in room {room_id}")
        logger.info(f"📝 Message: {message[:100]}...")
        
        # dialogue.process_message() 호출
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
                    "rag_sources": [],
                    "citations": []
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

@router.delete("/debate/{room_id}")
async def cleanup_debate_room_endpoint(room_id: str):
    """토론방 정리"""
    try:
        success = await cleanup_debate_room(room_id, "manual_delete")
        if success:
            return {"status": "success", "message": f"토론방 {room_id} 정리 완료"}
        else:
            raise HTTPException(status_code=500, detail="토론방 정리 중 오류 발생")
            
    except Exception as e:
        logger.error(f"❌ 토론방 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"토론방 정리 실패: {str(e)}")

@router.post("/user/{user_id}/leave-room")
async def user_leave_room(user_id: str, request: dict = None):
    """사용자가 토론방을 떠날 때 호출"""
    try:
        # 요청 본문에서 room_id 가져오기
        room_id = None
        if request and 'room_id' in request:
            room_id = request['room_id']
        else:
            # user_room_mapping에서 찾기
            room_id = user_room_mapping.get(user_id)
        
        if not room_id:
            return {"status": "success", "message": f"사용자 {user_id}는 활성 토론방이 없습니다"}
        
        logger.info(f"👋 User {user_id} leaving room {room_id}")
        
        success = await cleanup_user_from_room(user_id, room_id)
        
        if success:
            return {
                "status": "success", 
                "message": f"사용자 {user_id}가 토론방 {room_id}에서 나갔습니다",
                "room_cleaned": room_id not in active_debates
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 토론방 이탈 처리 중 오류 발생")
            
    except Exception as e:
        logger.error(f"❌ 사용자 토론방 이탈 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 토론방 이탈 처리 실패: {str(e)}")

@router.post("/cleanup/inactive-rooms")
async def cleanup_inactive_rooms():
    """비활성 토론방들 정리"""
    try:
        cleaned_rooms = []
        rooms_to_clean = list(active_debates.keys())
        
        for room_id in rooms_to_clean:
            # 방에 사용자가 없거나, 매핑이 없는 경우 정리
            if room_id not in room_user_mapping or len(room_user_mapping[room_id]) == 0:
                success = await cleanup_debate_room(room_id, "inactive_cleanup")
                if success:
                    cleaned_rooms.append(room_id)
        
        return {
            "status": "success",
            "message": f"{len(cleaned_rooms)}개의 비활성 토론방이 정리되었습니다",
            "cleaned_rooms": cleaned_rooms
        }
        
    except Exception as e:
        logger.error(f"❌ 비활성 토론방 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"비활성 토론방 정리 실패: {str(e)}")

# ========================================================================
# 백그라운드 메모리 모니터링
# ========================================================================

async def background_memory_monitor():
    """백그라운드에서 주기적으로 메모리 체크 및 정리"""
    while True:
        try:
            await asyncio.sleep(MEMORY_CHECK_INTERVAL * 60)  # 분 단위를 초로 변환
            await check_memory_and_cleanup()
        except Exception as e:
            logger.error(f"❌ Background memory monitor error: {str(e)}")

async def start_background_monitoring():
    """백그라운드 모니터링 시작"""
    try:
        if 'memory_monitor' not in background_tasks:
            task = asyncio.create_task(background_memory_monitor())
            background_tasks['memory_monitor'] = task
            logger.info(f"✅ Background memory monitoring started (interval: {MEMORY_CHECK_INTERVAL}min)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start background monitoring: {str(e)}")
        return False

async def stop_background_monitoring():
    """백그라운드 모니터링 중지"""
    try:
        if 'memory_monitor' in background_tasks:
            background_tasks['memory_monitor'].cancel()
            del background_tasks['memory_monitor']
            logger.info("✅ Background memory monitoring stopped")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to stop background monitoring: {str(e)}")
        return False

@router.get("/debug/active-rooms")
async def get_active_rooms_debug():
    """디버깅용: 현재 활성 토론방 상태 조회 (확장성 정보 포함)"""
    try:
        memory_stats = get_memory_usage()
        current_time = datetime.now()
        
        # 각 방의 상세 정보
        room_details = {}
        for room_id in active_debates.keys():
            creation_time = room_creation_times.get(room_id)
            last_activity = room_last_activity.get(room_id)
            
            room_details[room_id] = {
                "users": list(room_user_mapping.get(room_id, set())),
                "created_at": creation_time.isoformat() if creation_time else None,
                "last_activity": last_activity.isoformat() if last_activity else None,
                "age_hours": (current_time - creation_time).total_seconds() / 3600 if creation_time else None,
                "inactive_hours": (current_time - last_activity).total_seconds() / 3600 if last_activity else None
            }
        
        return {
            "active_debates": list(active_debates.keys()),
            "message_trackers": list(message_trackers.keys()),
            "user_room_mapping": dict(user_room_mapping),
            "room_user_mapping": {k: list(v) for k, v in room_user_mapping.items()},
            "room_details": room_details,
            "system_stats": {
                "total_active_rooms": len(active_debates),
                "max_rooms": MAX_ACTIVE_ROOMS,
                "memory_usage_gb": memory_stats['used_gb'],
                "memory_usage_percent": memory_stats['usage_percent'],
                "max_memory_gb": MAX_MEMORY_USAGE_GB,
                "max_inactive_hours": MAX_INACTIVE_HOURS
            },
            "background_monitoring": {
                "active": 'memory_monitor' in background_tasks,
                "interval_minutes": MEMORY_CHECK_INTERVAL
            }
        }
    except Exception as e:
        logger.error(f"❌ 활성 토론방 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"활성 토론방 상태 조회 실패: {str(e)}")

@router.get("/debug/resource-monitor")
async def get_detailed_resource_status():
    """실시간 리소스 상태 모니터링 (강화된 디버깅 버전)"""
    try:
        import threading
        import asyncio
        import gc
        import psutil
        import time
        from collections import defaultdict
        
        # 1. 스레드 상세 분석
        all_threads = threading.enumerate()
        thread_analysis = {
            "total_count": len(all_threads),
            "alive_count": len([t for t in all_threads if t.is_alive()]),
            "daemon_count": len([t for t in all_threads if t.daemon]),
            "normal_count": len([t for t in all_threads if not t.daemon]),
            "threads_detail": []
        }
        
        # 의심스러운 키워드들로 스레드 분류
        suspicious_keywords = [
            'analysis', 'background', 'argument', 'debate', 'strategy', 
            'opponent', 'attack', 'rag', 'vector', 'embedding', 'asyncio',
            'executor', 'threadpool', 'openai', 'llm'
        ]
        
        for i, thread in enumerate(all_threads):
            thread_name = str(thread.name).lower()
            thread_repr = str(thread).lower()
            
            is_suspicious = any(keyword in thread_name or keyword in thread_repr 
                              for keyword in suspicious_keywords)
            
            thread_analysis["threads_detail"].append({
                "index": i + 1,
                "name": thread.name,
                "alive": thread.is_alive(),
                "daemon": thread.daemon,
                "suspicious": is_suspicious,
                "ident": thread.ident,
                "repr": str(thread)[:100]
            })
        
        # 2. AsyncIO 태스크 분석
        task_analysis = {
            "total_tasks": 0,
            "running_tasks": 0,
            "done_tasks": 0,
            "cancelled_tasks": 0,
            "suspicious_tasks": [],
            "task_details": []
        }
        
        try:
            current_loop = asyncio.get_running_loop()
            all_tasks = asyncio.all_tasks(current_loop)
            task_analysis["total_tasks"] = len(all_tasks)
            
            for i, task in enumerate(all_tasks):
                task_repr = str(task)
                task_done = task.done()
                task_cancelled = task.cancelled() if task_done else False
                
                if not task_done:
                    task_analysis["running_tasks"] += 1
                elif task_cancelled:
                    task_analysis["cancelled_tasks"] += 1
                else:
                    task_analysis["done_tasks"] += 1
                
                # 의심스러운 태스크 식별
                is_suspicious = any(keyword in task_repr.lower() for keyword in suspicious_keywords)
                
                task_detail = {
                    "index": i + 1,
                    "done": task_done,
                    "cancelled": task_cancelled,
                    "suspicious": is_suspicious,
                    "repr": task_repr[:150]
                }
                
                task_analysis["task_details"].append(task_detail)
                
                if is_suspicious and not task_done:
                    task_analysis["suspicious_tasks"].append(task_detail)
        
        except RuntimeError:
            task_analysis = {"error": "No running event loop"}
        
        # 3. 메모리 사용량 분석
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_analysis = {
            "rss_mb": memory_info.rss / (1024 ** 2),
            "vms_mb": memory_info.vms / (1024 ** 2),
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 ** 2),
            "system_percent": psutil.virtual_memory().percent
        }
        
        # 4. 가비지 컬렉션 분석
        gc_stats = gc.get_stats()
        gc_analysis = {
            "collections": gc_stats,
            "tracked_objects": len(gc.get_objects()),
            "referrers_count": {}
        }
        
        # 의심스러운 객체 타입들 추적
        suspicious_types = ['DebateDialogue', 'Agent', 'Task', 'Thread', 'OpenAI']
        for obj_type in suspicious_types:
            matching_objects = [obj for obj in gc.get_objects() 
                              if obj_type.lower() in str(type(obj)).lower()]
            gc_analysis["referrers_count"][obj_type] = len(matching_objects)
        
        # 5. 토론방 상태 분석
        debate_analysis = {
            "active_debates_count": len(active_debates),
            "active_rooms": list(active_debates.keys()),
            "user_room_mappings": len(user_room_mapping),
            "room_user_mappings": len(room_user_mapping),
            "message_trackers": len(message_trackers)
        }
        
        # 각 토론방별 상세 정보
        for room_id, dialogue in active_debates.items():
            try:
                room_detail = {
                    "room_id": room_id,
                    "playing": getattr(dialogue, 'playing', None),
                    "agents_count": len(getattr(dialogue, 'agents', {})),
                    "force_stop_signal": getattr(dialogue, '_force_stop_signal', None),
                    "background_tasks": len(getattr(dialogue, 'background_preparation_tasks', {}))
                }
                debate_analysis[f"room_{room_id}_detail"] = room_detail
            except Exception as e:
                debate_analysis[f"room_{room_id}_error"] = str(e)
        
        # 6. 시스템 리소스 전반적 상태
        system_analysis = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "open_files": len(process.open_files()),
            "connections": len(process.connections()),
            "num_threads": process.num_threads(),
            "uptime_seconds": time.time() - process.create_time()
        }
        
        return {
            "timestamp": time.time(),
            "threads": thread_analysis,
            "asyncio_tasks": task_analysis,
            "memory": memory_analysis,
            "garbage_collection": gc_analysis,
            "debates": debate_analysis,
            "system": system_analysis,
            "summary": {
                "total_threads": thread_analysis["total_count"],
                "suspicious_threads": len([t for t in thread_analysis["threads_detail"] if t["suspicious"]]),
                "running_tasks": task_analysis.get("running_tasks", 0),
                "suspicious_tasks": len(task_analysis.get("suspicious_tasks", [])),
                "memory_mb": round(memory_analysis["rss_mb"], 1),
                "active_debates": len(active_debates)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in resource monitoring: {str(e)}")
        return {"error": str(e), "timestamp": time.time()}

@router.post("/debug/force-aggressive-cleanup")
async def force_aggressive_system_cleanup():
    """시스템 전체 공격적 정리 (디버깅용)"""
    try:
        import threading
        import asyncio
        import gc
        import time
        
        logger.info(f"🔥 Starting aggressive system cleanup")
        
        cleanup_report = {
            "before": {},
            "actions": [],
            "after": {},
            "success": False
        }
        
        # 정리 전 상태 기록
        cleanup_report["before"] = {
            "threads": len(threading.enumerate()),
            "daemon_threads": len([t for t in threading.enumerate() if t.daemon]),
            "active_debates": len(active_debates),
            "running_tasks": 0
        }
        
        try:
            loop = asyncio.get_running_loop()
            all_tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            cleanup_report["before"]["running_tasks"] = len(all_tasks)
        except RuntimeError:
            pass
        
        # 1. 모든 활성 토론방 강제 정리
        rooms_to_cleanup = list(active_debates.keys())
        for room_id in rooms_to_cleanup:
            try:
                success = await cleanup_debate_room(room_id, "aggressive_debug_cleanup")
                cleanup_report["actions"].append(f"Cleaned room {room_id}: {success}")
            except Exception as e:
                cleanup_report["actions"].append(f"Failed to clean room {room_id}: {str(e)}")
        
        # 2. 모든 의심스러운 asyncio 태스크 취소
        try:
            loop = asyncio.get_running_loop()
            all_tasks = asyncio.all_tasks(loop)
            
            suspicious_keywords = [
                'analysis', 'background', 'argument', 'debate', 'strategy', 
                'opponent', 'attack', 'rag', 'vector', 'embedding', 'openai'
            ]
            
            cancelled_count = 0
            for task in all_tasks:
                if not task.done():
                    task_repr = str(task).lower()
                    if any(keyword in task_repr for keyword in suspicious_keywords):
                        try:
                            task.cancel()
                            cancelled_count += 1
                        except Exception as e:
                            pass
            
            cleanup_report["actions"].append(f"Cancelled {cancelled_count} suspicious tasks")
            
            # 취소 완료 대기
            await asyncio.sleep(2.0)
            
        except Exception as e:
            cleanup_report["actions"].append(f"Task cleanup error: {str(e)}")
        
        # 3. 상태 딕셔너리들 강제 정리
        cleared_mappings = 0
        for mapping_dict in [user_room_mapping, room_user_mapping, message_trackers, 
                           room_creation_times, room_last_activity]:
            before_count = len(mapping_dict)
            mapping_dict.clear()
            cleared_mappings += before_count
        
        cleanup_report["actions"].append(f"Cleared {cleared_mappings} mapping entries")
        
        # 4. 강제 가비지 컬렉션 (여러 번)
        total_collected = 0
        for i in range(5):
            collected = gc.collect()
            total_collected += collected
            await asyncio.sleep(0.3)
        
        cleanup_report["actions"].append(f"Garbage collected {total_collected} objects")
        
        # 5. 정리 후 상태 기록
        await asyncio.sleep(1.0)
        
        cleanup_report["after"] = {
            "threads": len(threading.enumerate()),
            "daemon_threads": len([t for t in threading.enumerate() if t.daemon]),
            "active_debates": len(active_debates),
            "running_tasks": 0
        }
        
        try:
            loop = asyncio.get_running_loop()
            all_tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            cleanup_report["after"]["running_tasks"] = len(all_tasks)
        except RuntimeError:
            pass
        
        # 성공 여부 판단
        thread_reduction = cleanup_report["before"]["threads"] - cleanup_report["after"]["threads"]
        task_reduction = cleanup_report["before"]["running_tasks"] - cleanup_report["after"]["running_tasks"]
        
        cleanup_report["success"] = (
            cleanup_report["after"]["active_debates"] == 0 and
            thread_reduction >= 0 and
            task_reduction >= 0
        )
        
        cleanup_report["summary"] = {
            "thread_reduction": thread_reduction,
            "task_reduction": task_reduction,
            "debate_rooms_cleaned": len(rooms_to_cleanup)
        }
        
        logger.info(f"🔥 Aggressive cleanup completed: {cleanup_report['success']}")
        return cleanup_report
        
    except Exception as e:
        logger.error(f"❌ Error in aggressive cleanup: {str(e)}")
        return {"error": str(e), "success": False}

# ========================================================================
# 기존 엔드포인트들 (호환성 유지)
# ========================================================================

@router.post("/create-room")
async def create_debate_room_legacy(request: CreateDebateRoomRequest):
    """토론방 생성 (레거시 엔드포인트)"""
    return await create_debate_room(request)

@router.post("/send-message")
async def send_message(request: SendMessageRequest):
    """메시지 전송"""
    try:
        # 방 존재 확인
        room_data = get_room_data(request.room_id)
        if not room_data:
            raise HTTPException(status_code=404, detail="방을 찾을 수 없습니다")
        
        # 메시지 데이터 구성
        message_data = {
            "type": "user_message",
            "room_id": request.room_id,
            "user_id": request.user_id,
            "message": request.message,
            "side": request.side,
            "timestamp": datetime.now().isoformat()
        }
        
        # Redis에 메시지 저장
        add_message_to_room(request.room_id, message_data)
        
        # Socket.IO로 실시간 브로드캐스트
        success = await send_message_to_room(request.room_id, message_data)
        
        if success:
            logger.info(f"📨 Message sent: {request.user_id} -> {request.room_id}")
            return {
                "success": True,
                "message": "메시지가 전송되었습니다",
                "timestamp": message_data["timestamp"]
            }
        else:
            raise HTTPException(status_code=500, detail="메시지 전송에 실패했습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Message send failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/room/{room_id}")
async def get_room_info(room_id: str):
    """방 정보 조회"""
    try:
        room_data = get_room_data(room_id)
        if not room_data:
            raise HTTPException(status_code=404, detail="방을 찾을 수 없습니다")
        
        return {
            "success": True,
            "room_data": room_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get room info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/room/{room_id}/messages")
async def get_room_messages(room_id: str, limit: int = 50):
    """방의 메시지 히스토리 조회"""
    try:
        if not redis_client:
            return {"success": True, "messages": []}
        
        # Redis에서 메시지 목록 가져오기
        message_strings = redis_client.lrange(f"room:{room_id}:messages", 0, limit-1)
        messages = []
        
        for msg_str in message_strings:
            try:
                messages.append(json.loads(msg_str))
            except json.JSONDecodeError:
                continue
        
        # 시간순 정렬 (최신 메시지가 마지막)
        messages.reverse()
        
        return {
            "success": True,
            "messages": messages,
            "count": len(messages)
        }
        
    except Exception as e:
        logger.error(f"❌ Get messages failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/room/{room_id}")
async def delete_room(room_id: str):
    """방 삭제"""
    try:
        if not redis_client:
            raise HTTPException(status_code=500, detail="Redis 연결이 없습니다")
        
        # 방 데이터와 메시지 삭제
        redis_client.delete(f"room:{room_id}")
        redis_client.delete(f"room:{room_id}:messages")
        
        # 삭제 알림 브로드캐스트
        await send_message_to_room(room_id, {
            "type": "room_deleted",
            "room_id": room_id,
            "message": "방이 삭제되었습니다.",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"🗑️ Deleted room: {room_id}")
        
        return {
            "success": True,
            "message": "방이 성공적으로 삭제되었습니다"
        }
        
    except Exception as e:
        logger.error(f"❌ Delete room failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system-status")
async def get_chat_system_status():
    """채팅 시스템 상태 조회"""
    try:
        # Redis 연결 상태
        redis_status = "connected" if redis_client else "disconnected"
        if redis_client:
            try:
                redis_client.ping()
                redis_status = "healthy"
            except:
                redis_status = "error"
        
        # 시스템 리소스
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "redis": {
                "status": redis_status,
                "host": os.getenv('REDIS_HOST', 'localhost'),
                "port": os.getenv('REDIS_PORT', 6379)
            },
            "system": {
                "memory_usage": f"{memory.percent}%",
                "cpu_usage": f"{cpu_percent}%",
                "available_memory": f"{memory.available / (1024**3):.1f}GB"
            },
            "socket_io": "enabled via fastapi-sio",
            "active_debates": len(active_debates),
            "max_active_rooms": MAX_ACTIVE_ROOMS
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ System status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 