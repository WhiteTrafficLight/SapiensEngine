"""
표준 대화 형식을 구현하는 클래스
- 일반적인 순차적 대화 모델
- 기존 시스템의 동작 방식을 유지하면서 새로운 인터페이스로 통합
"""

import logging
import random
from typing import Dict, List, Optional, Any, Union

from .base_dialogue import BaseDialogue

logger = logging.getLogger(__name__)

class StandardDialogue(BaseDialogue):
    """표준 대화 형식 구현"""
    
    def __init__(self, room_id: str, room_data: Dict[str, Any] = None):
        """
        표준 대화 초기화
        
        Args:
            room_id: 채팅방 ID
            room_data: 채팅방 관련 데이터
        """
        super().__init__(room_id, room_data)
        self.dialogue_type = "standard"
        self.participants = self._get_participants_from_room_data()
        logger.info(f"Standard dialogue initialized for room {room_id} with {len(self.participants)} participants")
    
    def _get_participants_from_room_data(self) -> List[str]:
        """채팅방 데이터에서 참가자 목록 추출"""
        participants = []
        if self.room_data and 'participants' in self.room_data:
            if 'npcs' in self.room_data['participants']:
                participants.extend(self.room_data['participants']['npcs'])
        return participants
    
    def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        사용자 메시지 처리
        
        Args:
            message: 사용자 메시지 내용
            user_id: 사용자 ID
            
        Returns:
            처리된 메시지 정보
        """
        logger.info(f"Processing message from user {user_id} in room {self.room_id}: {message[:50]}...")
        
        return {
            "processed": True,
            "user_id": user_id,
            "message": message,
            "dialogue_type": self.dialogue_type
        }
    
    def generate_response(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        AI 응답 생성
        
        Args:
            context: 응답 생성에 필요한 컨텍스트
            
        Returns:
            생성된 응답 정보
        """
        context = context or {}
        next_speaker = self.get_next_speaker()
        speaker_id = next_speaker.get("speaker_id")
        
        # 실제 API 서버에서는 LLM을 호출하지만, 여기서는 스켈레톤만 구현
        prompt = self.build_prompt(speaker_id, context)
        
        logger.info(f"Generating response from {speaker_id} in room {self.room_id}")
        
        return {
            "speaker_id": speaker_id,
            "prompt": prompt,
            "dialogue_type": self.dialogue_type
        }
    
    def get_next_speaker(self) -> Dict[str, Any]:
        """
        다음 발언자 결정
        
        Returns:
            다음 발언자 정보
        """
        # 표준 대화에서는 참가자 중 랜덤으로 선택
        if not self.participants:
            logger.warning(f"No participants found in room {self.room_id}")
            return {"speaker_id": None, "status": "error", "reason": "no_participants"}
        
        # 실제 구현에서는 이전 발언자, 대화 컨텍스트 등 고려 필요
        next_speaker = random.choice(self.participants)
        
        return {
            "speaker_id": next_speaker,
            "dialogue_type": self.dialogue_type,
            "status": "ready"
        }
    
    def build_prompt(self, speaker_id: str, context: Dict[str, Any]) -> str:
        """
        주어진 화자와 컨텍스트에 맞는 프롬프트 생성
        
        Args:
            speaker_id: 화자 ID
            context: 프롬프트 생성 컨텍스트
            
        Returns:
            LLM에 전달할 프롬프트
        """
        # 기존 시스템의 프롬프트 생성 로직을 여기로 이전
        # 실제 구현에서는 더 복잡한 템플릿 및 컨텍스트 처리가 필요
        
        recent_messages = context.get('recent_messages', [])
        recent_messages_text = "\n".join([f"{msg.get('sender', 'Unknown')}: {msg.get('text', '')}" for msg in recent_messages[-5:]])
        
        prompt = f"""You are {speaker_id}. Respond to the conversation in the way that {speaker_id} would talk.

Recent messages:
{recent_messages_text}

Your response:"""
        
        return prompt 