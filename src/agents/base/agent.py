"""
기본 에이전트 인터페이스 및 추상 클래스

모든 에이전트가 공통적으로 구현해야 하는 핵심 메서드와 속성을 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Agent(ABC):
    """
    에이전트 추상 기본 클래스
    
    모든 에이전트는 이 클래스를 상속받아 구현해야 합니다.
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        에이전트 초기화
        
        Args:
            agent_id: 고유 식별자
            name: 에이전트 이름
            config: 설정 매개변수
        """
        self.agent_id = agent_id
        self.name = name
        self.config = config
        self.state = {}
        
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 데이터 처리 및 응답 생성
        
        Args:
            input_data: 처리할 입력 데이터
            
        Returns:
            처리 결과
        """
        pass
    
    @abstractmethod
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        에이전트 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """
        현재 에이전트 상태 반환
        
        Returns:
            현재 상태
        """
        return self.state 