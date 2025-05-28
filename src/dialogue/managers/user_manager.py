"""
사용자 관리자 클래스

대화 시스템에서 사용자의 생명주기, 인증, 세션 관리를 담당
"""

import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from ...agents.participant.user_participant import UserParticipant

logger = logging.getLogger(__name__)

@dataclass
class UserSession:
    """사용자 세션 정보"""
    user_id: str
    username: str
    session_id: str
    start_time: float
    last_activity: float
    current_dialogue_id: Optional[str] = None
    is_active: bool = True
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class UserManager:
    """
    사용자 관리자 클래스
    
    사용자 등록, 인증, 세션 관리, 권한 관리 등을 담당
    """
    
    def __init__(self):
        """사용자 관리자 초기화"""
        # 활성 사용자들 (user_id -> UserParticipant)
        self.active_users: Dict[str, UserParticipant] = {}
        
        # 사용자 세션들 (session_id -> UserSession)
        self.user_sessions: Dict[str, UserSession] = {}
        
        # 사용자 ID -> 세션 ID 매핑
        self.user_to_session: Dict[str, str] = {}
        
        # 대화별 참가자 목록 (dialogue_id -> Set[user_id])
        self.dialogue_participants: Dict[str, Set[str]] = {}
        
        # 사용자 설정 캐시 (user_id -> config)
        self.user_configs: Dict[str, Dict[str, Any]] = {}
        
        # 세션 정리를 위한 설정
        self.session_timeout = 3600  # 1시간
        self.cleanup_interval = 300  # 5분마다 정리
        self.last_cleanup = time.time()
        
        logger.info("UserManager initialized")
    
    def create_user_session(self, user_id: str, username: str, 
                           session_id: str = None, **kwargs) -> UserSession:
        """
        새로운 사용자 세션 생성
        
        Args:
            user_id: 사용자 ID
            username: 사용자명
            session_id: 세션 ID (없으면 자동 생성)
            **kwargs: 추가 세션 정보
            
        Returns:
            생성된 사용자 세션
        """
        if not session_id:
            session_id = f"session_{user_id}_{int(time.time())}"
        
        # 기존 세션이 있으면 종료
        if user_id in self.user_to_session:
            old_session_id = self.user_to_session[user_id]
            self.end_user_session(old_session_id)
        
        # 새 세션 생성
        session = UserSession(
            user_id=user_id,
            username=username,
            session_id=session_id,
            start_time=time.time(),
            last_activity=time.time(),
            ip_address=kwargs.get('ip_address'),
            user_agent=kwargs.get('user_agent')
        )
        
        # 세션 등록
        self.user_sessions[session_id] = session
        self.user_to_session[user_id] = session_id
        
        logger.info(f"Created session for user {user_id}: {session_id}")
        return session
    
    def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """세션 ID로 사용자 세션 조회"""
        return self.user_sessions.get(session_id)
    
    def get_user_session_by_user_id(self, user_id: str) -> Optional[UserSession]:
        """사용자 ID로 세션 조회"""
        session_id = self.user_to_session.get(user_id)
        if session_id:
            return self.user_sessions.get(session_id)
        return None
    
    def update_user_activity(self, user_id: str) -> bool:
        """사용자 활동 시간 업데이트"""
        session = self.get_user_session_by_user_id(user_id)
        if session:
            session.last_activity = time.time()
            return True
        return False
    
    def end_user_session(self, session_id: str) -> bool:
        """사용자 세션 종료"""
        session = self.user_sessions.get(session_id)
        if not session:
            return False
        
        user_id = session.user_id
        
        # 활성 대화에서 제거
        if session.current_dialogue_id:
            self.remove_user_from_dialogue(user_id, session.current_dialogue_id)
        
        # 활성 사용자에서 제거
        if user_id in self.active_users:
            del self.active_users[user_id]
        
        # 세션 정보 제거
        del self.user_sessions[session_id]
        if user_id in self.user_to_session:
            del self.user_to_session[user_id]
        
        logger.info(f"Ended session for user {user_id}: {session_id}")
        return True
    
    def create_user_participant(self, user_id: str, username: str, 
                               config: Dict[str, Any] = None) -> UserParticipant:
        """
        UserParticipant 객체 생성 및 등록
        
        Args:
            user_id: 사용자 ID
            username: 사용자명
            config: 사용자 설정
            
        Returns:
            생성된 UserParticipant 객체
        """
        # 기존 사용자가 있으면 반환
        if user_id in self.active_users:
            logger.info(f"User {user_id} already active, returning existing participant")
            return self.active_users[user_id]
        
        # 사용자 설정 로드 (캐시에서 또는 기본값)
        user_config = config or self.user_configs.get(user_id, {})
        
        # UserParticipant 객체 생성
        user_participant = UserParticipant(user_id, username, user_config)
        
        # 활성 사용자로 등록
        self.active_users[user_id] = user_participant
        
        # 설정 캐시 업데이트
        if config:
            self.user_configs[user_id] = config
        
        logger.info(f"Created UserParticipant for {user_id} ({username})")
        return user_participant
    
    def get_user_participant(self, user_id: str) -> Optional[UserParticipant]:
        """사용자 ID로 UserParticipant 객체 조회"""
        return self.active_users.get(user_id)
    
    def add_user_to_dialogue(self, user_id: str, dialogue_id: str) -> bool:
        """사용자를 대화에 추가"""
        # 사용자 세션 업데이트
        session = self.get_user_session_by_user_id(user_id)
        if session:
            session.current_dialogue_id = dialogue_id
        
        # 대화 참가자 목록에 추가
        if dialogue_id not in self.dialogue_participants:
            self.dialogue_participants[dialogue_id] = set()
        
        self.dialogue_participants[dialogue_id].add(user_id)
        
        # UserParticipant 객체 업데이트
        user_participant = self.active_users.get(user_id)
        if user_participant:
            user_participant.process({
                "action": "join_dialogue",
                "dialogue_id": dialogue_id
            })
        
        logger.info(f"Added user {user_id} to dialogue {dialogue_id}")
        return True
    
    def remove_user_from_dialogue(self, user_id: str, dialogue_id: str) -> bool:
        """사용자를 대화에서 제거"""
        # 대화 참가자 목록에서 제거
        if dialogue_id in self.dialogue_participants:
            self.dialogue_participants[dialogue_id].discard(user_id)
            
            # 참가자가 없으면 대화 목록에서 제거
            if not self.dialogue_participants[dialogue_id]:
                del self.dialogue_participants[dialogue_id]
        
        # 사용자 세션 업데이트
        session = self.get_user_session_by_user_id(user_id)
        if session and session.current_dialogue_id == dialogue_id:
            session.current_dialogue_id = None
        
        # UserParticipant 객체 업데이트
        user_participant = self.active_users.get(user_id)
        if user_participant:
            user_participant.process({"action": "leave_dialogue"})
        
        logger.info(f"Removed user {user_id} from dialogue {dialogue_id}")
        return True
    
    def get_dialogue_participants(self, dialogue_id: str) -> Set[str]:
        """특정 대화의 참가자 목록 반환"""
        return self.dialogue_participants.get(dialogue_id, set()).copy()
    
    def get_user_current_dialogue(self, user_id: str) -> Optional[str]:
        """사용자가 현재 참여 중인 대화 ID 반환"""
        session = self.get_user_session_by_user_id(user_id)
        if session:
            return session.current_dialogue_id
        return None
    
    def update_user_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """사용자 설정 업데이트"""
        # 캐시 업데이트
        if user_id not in self.user_configs:
            self.user_configs[user_id] = {}
        
        self.user_configs[user_id].update(config)
        
        # 활성 사용자 객체 업데이트
        user_participant = self.active_users.get(user_id)
        if user_participant:
            user_participant.process({
                "action": "update_preferences",
                "preferences": config
            })
        
        logger.info(f"Updated config for user {user_id}")
        return True
    
    def get_user_config(self, user_id: str) -> Dict[str, Any]:
        """사용자 설정 조회"""
        return self.user_configs.get(user_id, {}).copy()
    
    def is_user_online(self, user_id: str) -> bool:
        """사용자 온라인 상태 확인"""
        session = self.get_user_session_by_user_id(user_id)
        if not session:
            return False
        
        # 세션 타임아웃 확인
        if time.time() - session.last_activity > self.session_timeout:
            return False
        
        return session.is_active
    
    def get_online_users(self) -> List[str]:
        """온라인 사용자 목록 반환"""
        online_users = []
        current_time = time.time()
        
        for user_id, session_id in self.user_to_session.items():
            session = self.user_sessions.get(session_id)
            if session and session.is_active:
                if current_time - session.last_activity <= self.session_timeout:
                    online_users.append(user_id)
        
        return online_users
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """사용자 통계 정보 반환"""
        user_participant = self.active_users.get(user_id)
        session = self.get_user_session_by_user_id(user_id)
        
        stats = {
            "user_id": user_id,
            "is_online": self.is_user_online(user_id),
            "current_dialogue": self.get_user_current_dialogue(user_id),
            "session_duration": 0,
            "participation_stats": {}
        }
        
        if session:
            stats["session_duration"] = time.time() - session.start_time
            stats["username"] = session.username
        
        if user_participant:
            stats["participation_stats"] = user_participant.get_participation_stats()
            stats["message_count"] = user_participant.message_count
        
        return stats
    
    def cleanup_expired_sessions(self) -> int:
        """만료된 세션들 정리"""
        current_time = time.time()
        
        # 정리 간격 확인
        if current_time - self.last_cleanup < self.cleanup_interval:
            return 0
        
        expired_sessions = []
        
        # 만료된 세션 찾기
        for session_id, session in self.user_sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        # 만료된 세션들 제거
        for session_id in expired_sessions:
            self.end_user_session(session_id)
        
        self.last_cleanup = current_time
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """시스템 전체 통계 반환"""
        return {
            "total_active_users": len(self.active_users),
            "total_sessions": len(self.user_sessions),
            "total_dialogues": len(self.dialogue_participants),
            "online_users": len(self.get_online_users()),
            "last_cleanup": self.last_cleanup,
            "session_timeout": self.session_timeout
        }
    
    def shutdown(self) -> None:
        """사용자 관리자 종료 처리"""
        logger.info("Shutting down UserManager...")
        
        # 모든 세션 종료
        session_ids = list(self.user_sessions.keys())
        for session_id in session_ids:
            self.end_user_session(session_id)
        
        # 데이터 정리
        self.active_users.clear()
        self.user_sessions.clear()
        self.user_to_session.clear()
        self.dialogue_participants.clear()
        self.user_configs.clear()
        
        logger.info("UserManager shutdown complete")

# 전역 사용자 관리자 인스턴스
_user_manager_instance = None

def get_user_manager() -> UserManager:
    """전역 사용자 관리자 인스턴스 반환"""
    global _user_manager_instance
    if _user_manager_instance is None:
        _user_manager_instance = UserManager()
    return _user_manager_instance 