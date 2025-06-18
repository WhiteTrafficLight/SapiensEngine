"""
대화 형식의 기본 인터페이스를 정의하는 추상 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

class BaseDialogue(ABC):
    """대화 형식의 기본 추상 클래스"""
    
    def __init__(self, room_id: str, room_data: Dict[str, Any] = None):
        """
        기본 대화 초기화
        
        Args:
            room_id: 채팅방 ID
            room_data: 채팅방 관련 데이터
        """
        self.room_id = room_id
        self.room_data = room_data or {}
        self.dialogue_type = "standard"  # 기본값
        logger.info(f"Initialized {self.__class__.__name__} for room {room_id}")
    
    @abstractmethod
    def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        사용자 메시지 처리
        
        Args:
            message: 사용자 메시지 내용
            user_id: 사용자 ID
            
        Returns:
            처리된 메시지 정보
        """
        pass
    
    @abstractmethod
    def generate_response(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        AI 응답 생성
        
        Args:
            context: 응답 생성에 필요한 컨텍스트
            
        Returns:
            생성된 응답 정보
        """
        pass
    
    @abstractmethod
    def get_next_speaker(self) -> Dict[str, Any]:
        """
        다음 발언자 결정 및 정보 반환
        
        Returns:
            다음 발언자 정보
        """
        pass
    
    def build_prompt(self, speaker_id: str, context: Dict[str, Any]) -> str:
        """
        주어진 화자와 컨텍스트에 맞는 프롬프트 생성
        
        Args:
            speaker_id: 화자 ID
            context: 프롬프트 생성 컨텍스트
            
        Returns:
            LLM에 전달할 프롬프트
        """
        # 기본 구현은 각 대화 형식에서 오버라이드해야 함
        return f"You are {speaker_id}. Respond to the latest message."
    
    def get_dialogue_state(self) -> Dict[str, Any]:
        """
        현재 대화 상태 반환
        
        Returns:
            대화 상태 정보
        """
        return {
            "room_id": self.room_id,
            "dialogue_type": self.dialogue_type,
            "additional_info": {}
        }
    
    def update_dialogue_state(self, state_update: Dict[str, Any]) -> None:
        """
        대화 상태 업데이트
        
        Args:
            state_update: 업데이트할 상태 정보
        """
        # 기본 구현이지만 실제로는 각 대화 형식에서 상태 관리를 구현해야 함
        logger.info(f"Updating dialogue state for room {self.room_id}: {state_update}") 