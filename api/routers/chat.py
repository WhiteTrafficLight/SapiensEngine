"""
실시간 토론 시스템 - Socket.IO 통합

Socket.IO를 사용하여 Next.js 서버와 통신
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import socketio
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

# ========================================================================
# Socket.IO 클라이언트 설정
# ========================================================================

# Socket.IO 클라이언트 인스턴스
sio = socketio.AsyncClient()

# Next.js 서버 URL (환경변수에서 읽기)
NEXTJS_SERVER_URL = os.getenv('NEXTJS_SERVER_URL', 'http://localhost:3000')

@sio.event
async def connect():
    logger.info("🔌 Socket.IO 클라이언트가 Next.js 서버에 연결되었습니다")

@sio.event
async def disconnect():
    logger.info("🔌 Socket.IO 클라이언트 연결이 해제되었습니다")

# 사용자 Socket.IO 연결 추적을 위한 추가 이벤트 핸들러
@sio.event
async def user_connected(data):
    """사용자 연결 시 처리"""
    try:
        user_id = data.get('user_id')
        room_id = data.get('room_id')
        
        if user_id and room_id:
            logger.info(f"👤 Socket user connected: {user_id} to room {room_id}")
            
            # 사용자 매핑 업데이트
            user_room_mapping[user_id] = room_id
            
            # 방 사용자 목록 업데이트
            if room_id not in room_user_mapping:
                room_user_mapping[room_id] = set()
            room_user_mapping[room_id].add(user_id)
            
            logger.info(f"✅ User {user_id} tracked in room {room_id}")
    except Exception as e:
        logger.error(f"❌ Error handling user_connected: {str(e)}")

@sio.event
async def user_disconnected(data):
    """사용자 연결 해제 시 자동 정리"""
    try:
        user_id = data.get('user_id')
        room_id = data.get('room_id')
        
        if user_id:
            # user_room_mapping에서 room_id 찾기
            if not room_id and user_id in user_room_mapping:
                room_id = user_room_mapping[user_id]
            
            if room_id:
                logger.info(f"🔌 Socket user disconnected: {user_id} from room {room_id}")
                await cleanup_user_from_room(user_id, room_id)
            else:
                logger.warning(f"⚠️ Socket disconnect: Could not find room for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error handling user_disconnected: {str(e)}")

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
# 확장 가능한 상태 관리 (Redis 기반)
# ========================================================================

# Redis 연결 설정
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # 연결 테스트
    redis_client.ping()
    USE_REDIS = True
    logger.info(f"✅ Redis connected: {REDIS_URL}")
except Exception as e:
    logger.warning(f"⚠️ Redis unavailable, using memory fallback: {str(e)}")
    redis_client = None
    USE_REDIS = False

class DebateStateManager:
    """Redis 기반 토론 상태 관리자 (다중 서버 지원)"""
    
    @staticmethod
    def create_room(room_id: str, room_data: dict, user_ids: List[str]) -> bool:
        """토론방 생성"""
        try:
            if USE_REDIS:
                # Redis에 저장
                redis_client.hset("active_debates", room_id, json.dumps(room_data))
                redis_client.expire(f"debate:{room_id}", 7200)  # 2시간 TTL
                
                # 사용자 매핑 저장
                for user_id in user_ids:
                    redis_client.hset("user_room_mapping", user_id, room_id)
                
                # 방 사용자 목록 저장
                redis_client.sadd(f"room_users:{room_id}", *user_ids)
                redis_client.expire(f"room_users:{room_id}", 7200)
                
                logger.info(f"✅ Room {room_id} created in Redis")
                return True
            else:
                # 기존 메모리 방식 (fallback)
                active_debates[room_id] = room_data
                for user_id in user_ids:
                    user_room_mapping[user_id] = room_id
                room_user_mapping[room_id] = set(user_ids)
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create room {room_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_room(room_id: str) -> Optional[dict]:
        """토론방 데이터 조회"""
        try:
            if USE_REDIS:
                data = redis_client.hget("active_debates", room_id)
                return json.loads(data) if data else None
            else:
                return active_debates.get(room_id)
        except Exception as e:
            logger.error(f"❌ Failed to get room {room_id}: {str(e)}")
            return None
    
    @staticmethod
    def delete_room(room_id: str) -> bool:
        """토론방 삭제"""
        try:
            if USE_REDIS:
                # 방 데이터 삭제
                redis_client.hdel("active_debates", room_id)
                
                # 해당 방의 사용자들 매핑 삭제
                users = redis_client.smembers(f"room_users:{room_id}")
                for user_id in users:
                    redis_client.hdel("user_room_mapping", user_id)
                
                # 방 사용자 목록 삭제
                redis_client.delete(f"room_users:{room_id}")
                
                logger.info(f"✅ Room {room_id} deleted from Redis")
                return True
            else:
                # 기존 메모리 방식
                if room_id in active_debates:
                    del active_debates[room_id]
                
                users_to_remove = [uid for uid, rid in user_room_mapping.items() if rid == room_id]
                for user_id in users_to_remove:
                    del user_room_mapping[user_id]
                
                if room_id in room_user_mapping:
                    del room_user_mapping[room_id]
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to delete room {room_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_user_room(user_id: str) -> Optional[str]:
        """사용자의 현재 토론방 조회"""
        try:
            if USE_REDIS:
                return redis_client.hget("user_room_mapping", user_id)
            else:
                return user_room_mapping.get(user_id)
        except Exception as e:
            logger.error(f"❌ Failed to get user room for {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_room_users(room_id: str) -> set:
        """토론방의 사용자 목록 조회"""
        try:
            if USE_REDIS:
                return redis_client.smembers(f"room_users:{room_id}")
            else:
                return room_user_mapping.get(room_id, set())
        except Exception as e:
            logger.error(f"❌ Failed to get room users for {room_id}: {str(e)}")
            return set()
    
    @staticmethod
    def get_all_rooms() -> List[str]:
        """모든 활성 토론방 목록 조회"""
        try:
            if USE_REDIS:
                return list(redis_client.hkeys("active_debates"))
            else:
                return list(active_debates.keys())
        except Exception as e:
            logger.error(f"❌ Failed to get all rooms: {str(e)}")
            return []
    
    @staticmethod
    def update_room_activity(room_id: str):
        """토론방 활동 시간 업데이트"""
        try:
            if USE_REDIS:
                redis_client.hset("room_activity", room_id, datetime.now().isoformat())
                redis_client.expire(f"room_activity", 86400)  # 1일 TTL
            else:
                room_last_activity[room_id] = datetime.now()
        except Exception as e:
            logger.error(f"❌ Failed to update activity for {room_id}: {str(e)}")

# ========================================================================
# 기존 전역 상태 (Redis 사용 불가능 시 fallback)
# ========================================================================

# 활성 토론 인스턴스들 (메모리 - Redis 미사용 시에만)
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

# ========================================================================
# 메모리 모니터링 및 자동 정리
# ========================================================================

def get_memory_usage() -> Dict[str, float]:
    """현재 메모리 사용량 조회"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_gb = memory_info.rss / (1024 ** 3)  # bytes to GB
        
        return {
            "used_gb": memory_gb,
            "available_gb": psutil.virtual_memory().available / (1024 ** 3),
            "usage_percent": psutil.virtual_memory().percent
        }
    except Exception as e:
        logger.error(f"❌ Memory usage check failed: {str(e)}")
        return {"used_gb": 0, "available_gb": 0, "usage_percent": 0}

async def check_memory_and_cleanup():
    """메모리 사용량 체크 및 필요 시 자동 정리"""
    try:
        memory_stats = get_memory_usage()
        current_rooms = len(active_debates)
        
        logger.info(f"💾 Memory: {memory_stats['used_gb']:.1f}GB, Rooms: {current_rooms}")
        
        # 메모리 부족 또는 방 개수 초과 시 정리
        should_cleanup = (
            memory_stats['used_gb'] > MAX_MEMORY_USAGE_GB or
            current_rooms > MAX_ACTIVE_ROOMS or
            memory_stats['usage_percent'] > 80
        )
        
        if should_cleanup:
            logger.warning(f"🚨 High resource usage detected - triggering cleanup")
            await emergency_cleanup_inactive_rooms()
        
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

def update_room_activity(room_id: str):
    """토론방 활동 시간 업데이트"""
    room_last_activity[room_id] = datetime.now()

# ========================================================================
# 정리 함수들
# ========================================================================

async def comprehensive_debate_cleanup(dialogue_instance) -> bool:
    """DebateDialogue 인스턴스의 포괄적 정리 (내장 cleanup_resources 보완)"""
    try:
        room_id = getattr(dialogue_instance, 'room_id', 'unknown')
        logger.info(f"🧹 Starting comprehensive cleanup for DebateDialogue {room_id}")
        
        # 0. 먼저 대화 중단 (새로운 작업 방지)
        dialogue_instance.playing = False
        logger.info(f"🛑 Stopped dialogue playing for {room_id}")
        
        # 1. 내장 cleanup_resources 호출 (기본 정리)
        if hasattr(dialogue_instance, 'cleanup_resources'):
            dialogue_instance.cleanup_resources()
            logger.info(f"✅ Built-in cleanup_resources called")
        
        # 2. Agents 개별 정리 (중요!) - 로깅 순서 수정
        agents_count = 0
        if hasattr(dialogue_instance, 'agents') and dialogue_instance.agents:
            agents_count = len(dialogue_instance.agents)
            logger.info(f"🤖 Found {agents_count} agents to clean up")
            
            for agent_id, agent in dialogue_instance.agents.items():
                try:
                    # 에이전트 내부 작업 강제 중단
                    if hasattr(agent, 'stop_all_tasks'):
                        agent.stop_all_tasks()
                        logger.info(f"🛑 Stopped all tasks for agent {agent_id}")
                    
                    if hasattr(agent, 'cleanup'):
                        agent.cleanup()
                        logger.info(f"✅ Agent {agent_id} cleaned up")
                    
                    # Agent 내부 속성들 명시적 정리
                    if hasattr(agent, 'llm_manager'):
                        agent.llm_manager = None
                    if hasattr(agent, 'vector_store'):
                        agent.vector_store = None
                    if hasattr(agent, 'conversation_history'):
                        agent.conversation_history = []
                    if hasattr(agent, 'analysis_tasks'):
                        agent.analysis_tasks = {}
                    if hasattr(agent, 'preparation_tasks'):
                        agent.preparation_tasks = {}
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning agent {agent_id}: {e}")
            
            dialogue_instance.agents.clear()
            logger.info(f"✅ All {agents_count} agents cleared")
        
        # 3. 모든 asyncio 작업 강제 취소 (강화된 버전)
        try:
            import asyncio
            import threading
            
            # 현재 실행 중인 모든 태스크 찾기
            current_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            room_related_tasks = []
            
            for task in current_tasks:
                task_name = str(task)
                if room_id in task_name or 'confucius' in task_name.lower() or 'debate' in task_name.lower():
                    room_related_tasks.append(task)
            
            if room_related_tasks:
                logger.info(f"🛑 Found {len(room_related_tasks)} room-related tasks to cancel")
                for task in room_related_tasks:
                    if not task.done():
                        task.cancel()
                        logger.info(f"✅ Cancelled task: {str(task)[:100]}...")
            
            # 데몬 스레드 정리 (DebateDialogue의 analysis_thread들)
            active_threads = threading.enumerate()
            room_related_threads = []
            
            for thread in active_threads:
                thread_name = str(thread.name).lower()
                if (room_id.lower() in thread_name or 
                    'analysis' in thread_name or 
                    'debate' in thread_name or
                    'confucius' in thread_name):
                    room_related_threads.append(thread)
            
            if room_related_threads:
                logger.info(f"🛑 Found {len(room_related_threads)} room-related threads")
                for thread in room_related_threads:
                    if thread.is_alive() and thread != threading.current_thread():
                        logger.info(f"⚠️ Found daemon thread: {thread.name} (cannot force stop)")
                        # 데몬 스레드는 강제 종료할 수 없지만, 
                        # dialogue.playing = False로 인해 내부에서 자연스럽게 종료될 것
            
        except Exception as e:
            logger.warning(f"⚠️ Error cancelling asyncio tasks: {e}")
        
        # 4. 백그라운드 준비 작업 정리
        if hasattr(dialogue_instance, 'background_preparation_tasks'):
            for task_id, task in dialogue_instance.background_preparation_tasks.items():
                try:
                    if hasattr(task, 'cancel') and not task.done():
                        task.cancel()
                        logger.info(f"✅ Background task {task_id} cancelled")
                except Exception as e:
                    logger.warning(f"⚠️ Error cancelling task {task_id}: {e}")
            dialogue_instance.background_preparation_tasks.clear()
        
        # 5. 사용자 참가자 정리
        if hasattr(dialogue_instance, 'user_participants'):
            for user_id, user_participant in dialogue_instance.user_participants.items():
                try:
                    if hasattr(user_participant, 'cleanup'):
                        user_participant.cleanup()
                        logger.info(f"✅ User participant {user_id} cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ Error cleaning user participant {user_id}: {e}")
            dialogue_instance.user_participants.clear()
        
        # 6. 스트리밍 리스너 정리
        if hasattr(dialogue_instance, 'streaming_listeners'):
            dialogue_instance.streaming_listeners.clear()
            logger.info(f"✅ Streaming listeners cleared")
        
        # 7. 대화 상태 정리 (메모리 절약)
        if hasattr(dialogue_instance, 'state'):
            # 큰 데이터 구조들 정리
            if 'speaking_history' in dialogue_instance.state:
                history_count = len(dialogue_instance.state['speaking_history'])
                dialogue_instance.state['speaking_history'].clear()
                logger.info(f"✅ Cleared {history_count} speaking history items")
                
            if 'analysis_tracking' in dialogue_instance.state:
                dialogue_instance.state['analysis_tracking'].clear()
                logger.info(f"✅ Cleared analysis tracking")
                
            if 'interactive_cycle_state' in dialogue_instance.state:
                dialogue_instance.state['interactive_cycle_state'].clear()
                logger.info(f"✅ Cleared interactive cycle state")
        
        # 8. 주요 인스턴스 참조 해제
        dialogue_instance.llm_manager = None
        dialogue_instance.vector_store = None
        dialogue_instance.event_stream = None
        dialogue_instance.rag_processor = None
        dialogue_instance.message_callback = None
        
        # 9. 캐시 데이터 정리
        if hasattr(dialogue_instance, 'cached_data'):
            dialogue_instance.cached_data = None
        if hasattr(dialogue_instance, 'stance_statements'):
            dialogue_instance.stance_statements.clear()
        
        # 10. 딕셔너리 구조들 정리
        if hasattr(dialogue_instance, 'participants'):
            dialogue_instance.participants.clear()
        
        # 11. 짧은 대기 후 최종 확인 (백그라운드 작업 완전 중단 확인)
        await asyncio.sleep(0.1)
        
        logger.info(f"🧹 Comprehensive cleanup completed for {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in comprehensive cleanup: {str(e)}")
        return False

async def cleanup_debate_room(room_id: str, reason: str = "manual"):
    """토론방 정리 - 인스턴스 삭제 및 상태 정리 (개선된 버전)"""
    try:
        logger.info(f"🧹 Starting cleanup for room {room_id} (reason: {reason})")
        
        # 토론 인스턴스 정리
        if room_id in active_debates:
            dialogue = active_debates[room_id]
            
            # 포괄적 정리 함수 호출
            cleanup_success = await comprehensive_debate_cleanup(dialogue)
            
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
    """특정 사용자를 방에서 제거하고, 방이 비어있으면 정리"""
    try:
        logger.info(f"👤 Removing user {user_id} from room {room_id}")
        
        # 사용자 매핑에서 제거
        if user_id in user_room_mapping and user_room_mapping[user_id] == room_id:
            del user_room_mapping[user_id]
            logger.info(f"✅ Removed user mapping for {user_id}")
        
        # 방 사용자 목록에서 제거
        if room_id in room_user_mapping:
            room_user_mapping[room_id].discard(user_id)
            
            # 방이 비어있으면 토론방 전체 정리
            if len(room_user_mapping[room_id]) == 0:
                logger.info(f"🏠 Room {room_id} is now empty, cleaning up...")
                await cleanup_debate_room(room_id, "room_empty")
                return True
        
        logger.info(f"👤 User {user_id} removed from room {room_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to remove user {user_id} from room {room_id}: {str(e)}")
        return False

# ========================================================================
# API 라우터
# ========================================================================

router = APIRouter(prefix="/chat")

# Socket.IO 클라이언트 초기화 (서버 시작 시)
@router.on_event("startup")
async def startup_event():
    """서버 시작 시 Socket.IO 클라이언트 초기화 및 백그라운드 모니터링 시작"""
    await init_socketio_client()
    await start_background_monitoring()

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
        
        # 인스턴스 생성만 하고 자동 메시지 생성은 하지 않음
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
    """다음 메시지 생성 및 WebSocket 전송 (활동 추적 포함)"""
    try:
        if room_id not in active_debates:
            raise HTTPException(status_code=404, detail="토론방을 찾을 수 없습니다")
        
        # 방 활동 시간 업데이트
        update_room_activity(room_id)
        
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

@router.delete("/debate/{room_id}")
async def cleanup_debate_room_endpoint(room_id: str):
    """토론방 정리 (기존 엔드포인트 개선)"""
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
        # 요청 본문에서 room_id 가져오기 (선택사항)
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
                "room_cleaned": room_id not in active_debates  # 방이 완전히 정리되었는지 표시
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 토론방 이탈 처리 중 오류 발생")
            
    except Exception as e:
        logger.error(f"❌ 사용자 토론방 이탈 처리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 토론방 이탈 처리 실패: {str(e)}")

@router.post("/cleanup/inactive-rooms")
async def cleanup_inactive_rooms():
    """비활성 토론방들 정리 (관리자용 또는 정기 정리용)"""
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
    """서버 종료 시 Socket.IO 클라이언트 정리 및 백그라운드 모니터링 중지"""
    await cleanup_socketio_client()
    await stop_background_monitoring()

# ========================================================================
# 백그라운드 작업 관리
# ========================================================================

# 백그라운드 작업 관리
background_tasks = {}

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