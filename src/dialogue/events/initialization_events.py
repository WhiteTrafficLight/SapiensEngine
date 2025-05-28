"""
토론 초기화 이벤트 시스템

실시간으로 초기화 진행 상황을 추적하고 스트리밍할 수 있는 이벤트 시스템
"""

import asyncio
import time
from typing import Dict, Any, List, Callable, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class InitializationEventType(Enum):
    """초기화 이벤트 타입"""
    STARTED = "initialization_started"
    PROGRESS = "initialization_progress"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SUBTASK_PROGRESS = "subtask_progress"
    COMPLETED = "initialization_completed"
    FAILED = "initialization_failed"

class InitializationEvent:
    """초기화 이벤트 데이터"""
    
    def __init__(self, event_type: InitializationEventType, data: Dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = time.time()
        self.event_id = f"{event_type.value}_{int(self.timestamp * 1000)}"

class InitializationEventStream:
    """초기화 이벤트 스트림 관리자"""
    
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.listeners: List[Callable[[InitializationEvent], None]] = []
        self.event_history: List[InitializationEvent] = []
        self.current_progress = 0.0
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = None
        self.is_active = False
        
    def add_listener(self, listener: Callable[[InitializationEvent], None]):
        """이벤트 리스너 추가"""
        self.listeners.append(listener)
        logger.info(f"Added event listener for room {self.room_id}")
    
    def remove_listener(self, listener: Callable[[InitializationEvent], None]):
        """이벤트 리스너 제거"""
        if listener in self.listeners:
            self.listeners.remove(listener)
            logger.info(f"Removed event listener for room {self.room_id}")
    
    def emit_event(self, event_type: InitializationEventType, data: Dict[str, Any]):
        """이벤트 발생"""
        event = InitializationEvent(event_type, data)
        self.event_history.append(event)
        
        # 진행률 업데이트
        self._update_progress(event)
        
        # 모든 리스너에게 이벤트 전달
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in event listener: {str(e)}")
        
        logger.debug(f"Emitted event {event_type.value} for room {self.room_id}")
    
    def _update_progress(self, event: InitializationEvent):
        """진행률 업데이트"""
        if event.event_type == InitializationEventType.STARTED:
            self.start_time = event.timestamp
            self.is_active = True
            self.total_tasks = event.data.get('total_tasks', 0)
            self.current_progress = 0.0
            
        elif event.event_type == InitializationEventType.TASK_COMPLETED:
            self.completed_tasks += 1
            if self.total_tasks > 0:
                self.current_progress = (self.completed_tasks / self.total_tasks) * 100
                
        elif event.event_type == InitializationEventType.TASK_FAILED:
            self.failed_tasks += 1
            if self.total_tasks > 0:
                # 실패한 작업도 완료된 것으로 간주하여 진행률 계산
                self.current_progress = ((self.completed_tasks + self.failed_tasks) / self.total_tasks) * 100
                
        elif event.event_type in [InitializationEventType.COMPLETED, InitializationEventType.FAILED]:
            self.current_progress = 100.0
            self.is_active = False
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """현재 진행 상황 요약"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            "room_id": self.room_id,
            "progress_percentage": self.current_progress,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "elapsed_time": elapsed_time,
            "is_active": self.is_active,
            "estimated_remaining_time": self._estimate_remaining_time(elapsed_time)
        }
    
    def _estimate_remaining_time(self, elapsed_time: float) -> Optional[float]:
        """남은 시간 추정"""
        if self.current_progress <= 0:
            return None
        
        if self.current_progress >= 100:
            return 0.0
        
        # 현재 진행률을 바탕으로 남은 시간 추정
        time_per_percent = elapsed_time / self.current_progress
        remaining_percent = 100 - self.current_progress
        return time_per_percent * remaining_percent
    
    def get_event_history(self) -> List[Dict[str, Any]]:
        """이벤트 히스토리 반환"""
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "data": event.data
            }
            for event in self.event_history
        ]

class TaskProgressTracker:
    """개별 작업 진행 상황 추적기"""
    
    def __init__(self, task_name: str, event_stream: InitializationEventStream):
        self.task_name = task_name
        self.event_stream = event_stream
        self.start_time = None
        self.subtasks = []
        self.completed_subtasks = 0
        
    def start(self, subtasks: List[str] = None):
        """작업 시작"""
        self.start_time = time.time()
        self.subtasks = subtasks or []
        self.completed_subtasks = 0
        
        self.event_stream.emit_event(
            InitializationEventType.TASK_STARTED,
            {
                "task_name": self.task_name,
                "subtasks": self.subtasks,
                "start_time": self.start_time
            }
        )
    
    def update_subtask(self, subtask_name: str, status: str, details: Dict[str, Any] = None):
        """서브태스크 진행 상황 업데이트"""
        if status == "completed":
            self.completed_subtasks += 1
        
        progress_percentage = 0
        if self.subtasks:
            progress_percentage = (self.completed_subtasks / len(self.subtasks)) * 100
        
        self.event_stream.emit_event(
            InitializationEventType.SUBTASK_PROGRESS,
            {
                "task_name": self.task_name,
                "subtask_name": subtask_name,
                "status": status,
                "progress_percentage": progress_percentage,
                "details": details or {}
            }
        )
    
    def complete(self, result: Dict[str, Any]):
        """작업 완료"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        self.event_stream.emit_event(
            InitializationEventType.TASK_COMPLETED,
            {
                "task_name": self.task_name,
                "elapsed_time": elapsed_time,
                "result": result
            }
        )
    
    def fail(self, error: str, details: Dict[str, Any] = None):
        """작업 실패"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        self.event_stream.emit_event(
            InitializationEventType.TASK_FAILED,
            {
                "task_name": self.task_name,
                "elapsed_time": elapsed_time,
                "error": error,
                "details": details or {}
            }
        )

# 전역 이벤트 스트림 관리자
_event_streams: Dict[str, InitializationEventStream] = {}

def get_event_stream(room_id: str) -> InitializationEventStream:
    """방 ID에 대한 이벤트 스트림 가져오기"""
    if room_id not in _event_streams:
        _event_streams[room_id] = InitializationEventStream(room_id)
    return _event_streams[room_id]

def cleanup_event_stream(room_id: str):
    """이벤트 스트림 정리"""
    if room_id in _event_streams:
        del _event_streams[room_id]
        logger.info(f"Cleaned up event stream for room {room_id}")

# 편의 함수들
def create_console_listener() -> Callable[[InitializationEvent], None]:
    """콘솔 출력용 리스너 생성"""
    def console_listener(event: InitializationEvent):
        event_type = event.event_type.value
        data = event.data
        
        if event_type == "initialization_started":
            print(f"🚀 초기화 시작: {data.get('total_tasks', 0)}개 작업")
        elif event_type == "task_started":
            print(f"📋 작업 시작: {data.get('task_name', 'Unknown')}")
        elif event_type == "subtask_progress":
            task_name = data.get('task_name', 'Unknown')
            subtask_name = data.get('subtask_name', 'Unknown')
            status = data.get('status', 'Unknown')
            progress = data.get('progress_percentage', 0)
            print(f"   ⚡ {task_name} > {subtask_name}: {status} ({progress:.1f}%)")
        elif event_type == "task_completed":
            task_name = data.get('task_name', 'Unknown')
            elapsed = data.get('elapsed_time', 0)
            print(f"✅ 작업 완료: {task_name} ({elapsed:.2f}초)")
        elif event_type == "task_failed":
            task_name = data.get('task_name', 'Unknown')
            error = data.get('error', 'Unknown error')
            print(f"❌ 작업 실패: {task_name} - {error}")
        elif event_type == "initialization_completed":
            total_time = data.get('total_time', 0)
            print(f"🎉 초기화 완료! 총 {total_time:.2f}초")
        elif event_type == "initialization_failed":
            error = data.get('error', 'Unknown error')
            print(f"💥 초기화 실패: {error}")
    
    return console_listener

def create_web_listener(websocket_send_func: Callable) -> Callable[[InitializationEvent], None]:
    """웹소켓 전송용 리스너 생성"""
    def web_listener(event: InitializationEvent):
        try:
            message = {
                "type": "initialization_event",
                "event_type": event.event_type.value,
                "timestamp": event.timestamp,
                "data": event.data
            }
            websocket_send_func(message)
        except Exception as e:
            logger.error(f"Error sending websocket message: {str(e)}")
    
    return web_listener 