"""
대화 상태 관리 모듈

대화 진행 상황, 참여자 정보, 컨텍스트 등 대화의 상태를 관리합니다.
"""

import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class DialogueStage(Enum):
    """대화 진행 단계"""
    INITIALIZATION = "initialization"
    INTRODUCTION = "introduction"
    MAIN_DISCUSSION = "main_discussion"
    CONCLUSION = "conclusion"
    SUMMARY = "summary"
    ENDED = "ended"


@dataclass
class Message:
    """대화 메시지 표현"""
    sender_id: str
    sender_name: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DialogueState:
    """
    대화 상태 관리 클래스
    
    모든 대화 관련 정보 및 상태를 추적하고 관리합니다.
    """
    
    def __init__(self, dialogue_id: str, dialogue_type: str, topic: str):
        """
        대화 상태 초기화
        
        Args:
            dialogue_id: 대화 세션 ID
            dialogue_type: 대화 유형 (debate, interview, etc.)
            topic: 대화 주제
        """
        self.dialogue_id = dialogue_id
        self.dialogue_type = dialogue_type
        self.topic = topic
        self.stage = DialogueStage.INITIALIZATION
        self.start_time = time.time()
        self.last_updated = self.start_time
        
        self.participants: Dict[str, Dict[str, Any]] = {}  # 참여자 정보
        self.message_history: List[Message] = []  # 메시지 기록
        self.context: Dict[str, Any] = {}  # 대화 컨텍스트
        self.agent_states: Dict[str, Dict[str, Any]] = {}  # 에이전트별 상태
        self.metadata: Dict[str, Any] = {}  # 기타 메타데이터
        
    def add_participant(self, participant_id: str, info: Dict[str, Any]) -> None:
        """
        참여자 추가
        
        Args:
            participant_id: 참여자 ID
            info: 참여자 정보
        """
        self.participants[participant_id] = info
        self.last_updated = time.time()
        
    def add_message(self, message: Message) -> None:
        """
        메시지 추가
        
        Args:
            message: 추가할 메시지
        """
        self.message_history.append(message)
        self.last_updated = time.time()
        
    def update_stage(self, new_stage: DialogueStage) -> None:
        """
        대화 단계 업데이트
        
        Args:
            new_stage: 새 대화 단계
        """
        self.stage = new_stage
        self.last_updated = time.time()
        
    def update_agent_state(self, agent_id: str, state_update: Dict[str, Any]) -> None:
        """
        에이전트 상태 업데이트
        
        Args:
            agent_id: 에이전트 ID
            state_update: 상태 업데이트 데이터
        """
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {}
            
        self.agent_states[agent_id].update(state_update)
        self.last_updated = time.time()
        
    def update_context(self, context_update: Dict[str, Any]) -> None:
        """
        대화 컨텍스트 업데이트
        
        Args:
            context_update: 컨텍스트 업데이트 데이터
        """
        self.context.update(context_update)
        self.last_updated = time.time()
        
    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """
        최근 메시지 조회
        
        Args:
            count: 반환할 메시지 수
            
        Returns:
            최근 메시지 목록
        """
        return self.message_history[-count:] if self.message_history else []
    
    def get_session_duration(self) -> float:
        """
        현재까지의 대화 세션 지속 시간 (초)
        
        Returns:
            세션 지속 시간
        """
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        상태 정보를 사전 형태로 변환
        
        Returns:
            상태 정보 사전
        """
        return {
            "dialogue_id": self.dialogue_id,
            "dialogue_type": self.dialogue_type,
            "topic": self.topic,
            "stage": self.stage.value,
            "start_time": self.start_time,
            "last_updated": self.last_updated,
            "duration": self.get_session_duration(),
            "participants": self.participants,
            "message_count": len(self.message_history),
            "context": self.context,
            "metadata": self.metadata
        } 