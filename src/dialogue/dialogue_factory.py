"""
대화 형식 팩토리 모듈
- 대화 타입에 따라 적절한 대화 객체를 생성
- 새로운 대화 형식을 쉽게 추가할 수 있는 확장성 제공
"""

import logging
from typing import Dict, Optional, Any, Type

from .types.base_dialogue import BaseDialogue
from .types.simple_dialogue import SimpleDialogue
from .types.debate_dialogue import DebateDialogue

logger = logging.getLogger(__name__)

class DialogueFactory:
    """대화 형식 생성을 위한 팩토리 클래스"""
    
    # 대화 형식 타입별 클래스 매핑
    _dialogue_types = {
        "simple": SimpleDialogue,
        "debate": DebateDialogue,
        # 추가 대화 형식을 여기에 등록
    }
    
    @classmethod
    def register_dialogue_type(cls, dialogue_type: str, dialogue_class: Type[BaseDialogue]) -> None:
        """
        새로운 대화 형식 등록
        
        Args:
            dialogue_type: 대화 형식 식별자
            dialogue_class: 대화 형식 클래스
        """
        cls._dialogue_types[dialogue_type] = dialogue_class
        logger.info(f"Registered dialogue type: {dialogue_type}")
    
    @classmethod
    def create_dialogue(cls, dialogue_type: str, room_id: str, room_data: Optional[Dict[str, Any]] = None) -> BaseDialogue:
        """
        대화 형식에 맞는 객체 생성
        
        Args:
            dialogue_type: 대화 형식 타입
            room_id: 채팅방 ID
            room_data: 채팅방 데이터
            
        Returns:
            생성된 대화 객체
            
        Raises:
            ValueError: 지원하지 않는 대화 형식일 경우
        """
        dialogue_class = cls._dialogue_types.get(dialogue_type)
        
        if not dialogue_class:
            logger.warning(f"Unsupported dialogue type: {dialogue_type}, falling back to simple")
            dialogue_class = SimpleDialogue
        
        logger.info(f"Creating dialogue of type '{dialogue_type}' for room {room_id}")
        return dialogue_class(room_id, room_data)
    
    @classmethod
    def get_available_types(cls) -> Dict[str, str]:
        """
        사용 가능한 대화 형식 목록 반환
        
        Returns:
            대화 형식 이름과 설명 매핑
        """
        return {
            "simple": "기본 대화",
            "debate": "찬반 토론",
            # 추가 대화 형식 설명
        } 