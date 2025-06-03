"""
사용자 참가자 클래스

실제 사용자가 대화에 참여할 때 사용되는 클래스
에이전트와 유사한 인터페이스를 제공하지만 실제 응답은 사용자 입력을 기다림
"""

import logging
import time
from typing import Dict, List, Any, Optional

from ..base.agent import Agent

logger = logging.getLogger(__name__)

class UserParticipant(Agent):
    """
    사용자 참가자 클래스
    
    실제 사용자가 대화에 참여할 때 사용되며,
    에이전트와 동일한 인터페이스를 제공하지만 실제 응답은 사용자 입력을 기다림
    """
    
    def __init__(self, user_id: str, username: str, config: Dict[str, Any] = None):
        """
        사용자 참가자 초기화
        
        Args:
            user_id: 사용자 고유 ID
            username: 사용자 표시 이름
            config: 사용자 설정 (선택사항)
        """
        super().__init__(user_id, username, config or {})
        
        # 사용자 기본 정보
        self.user_id = user_id
        self.username = username
        self.display_name = config.get("display_name", username)
        
        # 대화 참여 설정
        self.role = config.get("role", "neutral")  # pro, con, neutral
        self.participation_style = config.get("participation_style", "active")  # active, passive, observer
        self.notification_preferences = config.get("notification_preferences", {
            "turn_notifications": True,
            "stage_changes": True,
            "mentions": True
        })
        
        # 사용자 프로필 정보
        self.profile = config.get("profile", {})
        self.avatar_url = config.get("avatar_url", "")
        self.bio = config.get("bio", "")
        
        # 대화 참여 상태
        self.is_online = True
        self.last_seen = time.time()
        self.current_dialogue_id = None
        self.typing_status = False
        
        # 대화 기록 및 통계
        self.message_count = 0
        self.participation_history = []
        self.preferred_topics = config.get("preferred_topics", [])
        
        # 권한 및 제한
        self.permissions = config.get("permissions", {
            "can_speak": True,
            "can_moderate": False,
            "can_invite": False,
            "can_change_topic": False
        })
        
        # 사용자별 맞춤 설정
        self.preferences = config.get("preferences", {
            "language": "ko",
            "response_time_limit": 300,  # 5분
            "auto_skip_after_timeout": False,
            "debate_style_preference": "balanced"  # aggressive, balanced, collaborative
        })
        
        logger.info(f"UserParticipant initialized: {user_id} ({username})")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 입력 처리
        
        Args:
            input_data: 처리할 입력 데이터
            
        Returns:
            처리 결과 (사용자는 실제 응답 생성하지 않음)
        """
        action = input_data.get("action", "")
        
        if action == "check_turn":
            # 사용자의 발언 차례인지 확인
            return self._check_user_turn(input_data)
        
        elif action == "process_message":
            # 사용자가 보낸 메시지 처리
            return self._process_user_message(input_data)
        
        elif action == "analyze_opponent_arguments":
            # 상대방 논지 분석 요청 (사용자는 분석하지 않음)
            return self._handle_analyze_opponent_arguments(input_data)
        
        elif action == "get_status":
            # 사용자 상태 정보 반환
            return self._get_user_status()
        
        elif action == "update_preferences":
            # 사용자 설정 업데이트
            return self._update_user_preferences(input_data)
        
        elif action == "join_dialogue":
            # 대화 참여
            return self._join_dialogue(input_data)
        
        elif action == "leave_dialogue":
            # 대화 떠나기
            return self._leave_dialogue()
        
        else:
            return {
                "status": "waiting_for_user",
                "message": "사용자 입력을 기다리는 중입니다.",
                "user_id": self.user_id,
                "username": self.username
            }
    
    def _check_user_turn(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자의 발언 차례인지 확인"""
        dialogue_state = input_data.get("dialogue_state", {})
        next_speaker = dialogue_state.get("next_speaker")
        
        is_my_turn = (next_speaker == self.user_id)
        
        return {
            "is_my_turn": is_my_turn,
            "user_id": self.user_id,
            "next_speaker": next_speaker,
            "status": "ready" if is_my_turn else "waiting",
            "time_limit": self.preferences.get("response_time_limit", 300)
        }
    
    def _process_user_message(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자가 보낸 메시지 처리"""
        message = input_data.get("message", "")
        timestamp = input_data.get("timestamp", time.time())
        
        # 메시지 통계 업데이트
        self.message_count += 1
        self.last_seen = timestamp
        
        # 참여 기록 업데이트
        self.participation_history.append({
            "timestamp": timestamp,
            "message_length": len(message),
            "dialogue_id": self.current_dialogue_id,
            "stage": input_data.get("current_stage", "unknown")
        })
        
        # 최근 기록만 유지 (최대 100개)
        if len(self.participation_history) > 100:
            self.participation_history = self.participation_history[-100:]
        
        return {
            "status": "message_processed",
            "user_id": self.user_id,
            "username": self.username,
            "message": message,
            "timestamp": timestamp,
            "message_count": self.message_count
        }
    
    def _handle_analyze_opponent_arguments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        상대방 논지 분석 요청 처리 (사용자는 분석하지 않음)
        
        Args:
            input_data: 분석 요청 데이터
            
        Returns:
            성공 응답 (실제로는 아무것도 하지 않음)
        """
        opponent_response = input_data.get("opponent_response", "")
        speaker_id = input_data.get("speaker_id", "")
        
        # 사용자는 실제 분석을 하지 않고 단순히 성공 응답만 반환
        # 이는 AI 에이전트들이 유저의 논지를 분석할 수 있도록 하기 위함
        logger.info(f"👤 [UserParticipant {self.user_id}] 논지 분석 요청 수신 (상대방: {speaker_id}) - 사용자는 분석 안함")
        
        return {
            "status": "analysis_completed",
            "user_id": self.user_id,
            "opponent_id": speaker_id,
            "message": "사용자는 논지 분석을 수행하지 않습니다.",
            "arguments_analyzed": 0,
            "timestamp": time.time()
        }
    
    def _get_user_status(self) -> Dict[str, Any]:
        """사용자 상태 정보 반환"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "is_online": self.is_online,
            "last_seen": self.last_seen,
            "current_dialogue_id": self.current_dialogue_id,
            "typing_status": self.typing_status,
            "message_count": self.message_count,
            "participation_style": self.participation_style,
            "permissions": self.permissions,
            "preferences": self.preferences
        }
    
    def _update_user_preferences(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 설정 업데이트"""
        new_preferences = input_data.get("preferences", {})
        
        # 허용된 설정만 업데이트
        allowed_keys = [
            "language", "response_time_limit", "auto_skip_after_timeout",
            "debate_style_preference", "notification_preferences"
        ]
        
        for key, value in new_preferences.items():
            if key in allowed_keys:
                if key == "notification_preferences":
                    self.notification_preferences.update(value)
                else:
                    self.preferences[key] = value
        
        return {
            "status": "preferences_updated",
            "user_id": self.user_id,
            "updated_preferences": {k: v for k, v in new_preferences.items() if k in allowed_keys}
        }
    
    def _join_dialogue(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """대화 참여"""
        dialogue_id = input_data.get("dialogue_id")
        role = input_data.get("role", self.role)
        
        self.current_dialogue_id = dialogue_id
        self.role = role
        self.is_online = True
        self.last_seen = time.time()
        
        logger.info(f"User {self.user_id} joined dialogue {dialogue_id} as {role}")
        
        return {
            "status": "joined",
            "user_id": self.user_id,
            "username": self.username,
            "dialogue_id": dialogue_id,
            "role": role,
            "timestamp": self.last_seen
        }
    
    def _leave_dialogue(self) -> Dict[str, Any]:
        """대화 떠나기"""
        old_dialogue_id = self.current_dialogue_id
        self.current_dialogue_id = None
        self.typing_status = False
        
        logger.info(f"User {self.user_id} left dialogue {old_dialogue_id}")
        
        return {
            "status": "left",
            "user_id": self.user_id,
            "username": self.username,
            "dialogue_id": old_dialogue_id,
            "timestamp": time.time()
        }
    
    # === 상태 관리 메서드들 ===
    
    def set_online_status(self, is_online: bool) -> None:
        """온라인 상태 설정"""
        self.is_online = is_online
        if is_online:
            self.last_seen = time.time()
    
    def set_typing_status(self, is_typing: bool) -> None:
        """타이핑 상태 설정"""
        self.typing_status = is_typing
    
    def update_role(self, new_role: str) -> None:
        """역할 업데이트"""
        old_role = self.role
        self.role = new_role
        logger.info(f"User {self.user_id} role changed from {old_role} to {new_role}")
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        사용자 상태 업데이트 (Agent 추상 메서드 구현)
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        # 기본 상태 업데이트
        self.state.update(state_update)
        
        # 사용자별 특수 상태 업데이트 처리
        if 'is_online' in state_update:
            self.set_online_status(state_update['is_online'])
        
        if 'typing_status' in state_update:
            self.set_typing_status(state_update['typing_status'])
        
        if 'role' in state_update:
            self.update_role(state_update['role'])
        
        if 'current_dialogue_id' in state_update:
            self.current_dialogue_id = state_update['current_dialogue_id']
        
        if 'preferences' in state_update:
            self.preferences.update(state_update['preferences'])
        
        if 'permissions' in state_update:
            self.permissions.update(state_update['permissions'])
        
        logger.debug(f"Updated state for user {self.user_id}: {list(state_update.keys())}")
    
    def get_participation_stats(self) -> Dict[str, Any]:
        """참여 통계 반환"""
        if not self.participation_history:
            return {
                "total_messages": 0,
                "average_message_length": 0,
                "total_dialogues": 0,
                "last_activity": None
            }
        
        total_messages = len(self.participation_history)
        avg_length = sum(p["message_length"] for p in self.participation_history) / total_messages
        unique_dialogues = len(set(p["dialogue_id"] for p in self.participation_history if p["dialogue_id"]))
        last_activity = max(p["timestamp"] for p in self.participation_history)
        
        return {
            "total_messages": total_messages,
            "average_message_length": round(avg_length, 1),
            "total_dialogues": unique_dialogues,
            "last_activity": last_activity
        }
    
    def can_perform_action(self, action: str) -> bool:
        """특정 액션 수행 권한 확인"""
        permission_map = {
            "speak": "can_speak",
            "moderate": "can_moderate", 
            "invite": "can_invite",
            "change_topic": "can_change_topic"
        }
        
        permission_key = permission_map.get(action)
        if permission_key:
            return self.permissions.get(permission_key, False)
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """사용자 정보를 딕셔너리로 변환"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "participation_style": self.participation_style,
            "is_online": self.is_online,
            "last_seen": self.last_seen,
            "current_dialogue_id": self.current_dialogue_id,
            "message_count": self.message_count,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "permissions": self.permissions,
            "preferences": self.preferences,
            "participation_stats": self.get_participation_stats()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserParticipant':
        """딕셔너리에서 사용자 객체 생성"""
        user_id = data["user_id"]
        username = data["username"]
        
        config = {
            "display_name": data.get("display_name", username),
            "role": data.get("role", "neutral"),
            "participation_style": data.get("participation_style", "active"),
            "avatar_url": data.get("avatar_url", ""),
            "bio": data.get("bio", ""),
            "permissions": data.get("permissions", {}),
            "preferences": data.get("preferences", {}),
            "notification_preferences": data.get("notification_preferences", {})
        }
        
        user = cls(user_id, username, config)
        user.is_online = data.get("is_online", True)
        user.last_seen = data.get("last_seen", time.time())
        user.current_dialogue_id = data.get("current_dialogue_id")
        user.message_count = data.get("message_count", 0)
        
        return user 