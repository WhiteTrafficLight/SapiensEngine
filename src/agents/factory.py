"""
에이전트 팩토리 모듈

대화 유형에 따라 필요한 에이전트 조합을 생성하는 팩토리 패턴 구현
"""

import os
import yaml
from typing import Dict, Any, List, Type, Optional

from src.agents.base.agent import Agent


class AgentRegistry:
    """
    에이전트 등록 관리 클래스
    
    등록된 에이전트 유형을 관리하고 인스턴스화합니다.
    """
    _registry: Dict[str, Type[Agent]] = {}
    
    @classmethod
    def register(cls, agent_type: str, agent_class: Type[Agent]) -> None:
        """
        에이전트 유형 등록
        
        Args:
            agent_type: 에이전트 유형 식별자 
            agent_class: 에이전트 클래스
        """
        cls._registry[agent_type] = agent_class
        
    @classmethod
    def get_agent_class(cls, agent_type: str) -> Optional[Type[Agent]]:
        """
        에이전트 클래스 조회
        
        Args:
            agent_type: 에이전트 유형 식별자
            
        Returns:
            에이전트 클래스 또는 None
        """
        return cls._registry.get(agent_type)


class AgentFactory:
    """
    에이전트 생성 팩토리
    
    대화 유형에 따라 필요한 에이전트 조합 생성
    """
    
    def __init__(self, config_dir: str = "src/agents/configs"):
        """
        에이전트 팩토리 초기화
        
        Args:
            config_dir: 에이전트 설정 파일 디렉토리
        """
        self.config_dir = config_dir
        
    def load_dialogue_config(self, dialogue_type: str) -> Dict[str, Any]:
        """
        대화 유형별 에이전트 구성 로드
        
        Args:
            dialogue_type: 대화 유형 (debate, interview 등)
            
        Returns:
            대화 구성 설정
        """
        config_path = os.path.join(self.config_dir, f"{dialogue_type}_agents.yaml")
        
        if not os.path.exists(config_path):
            raise ValueError(f"Unknown dialogue type: {dialogue_type}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def create_agents(self, dialogue_type: str) -> Dict[str, Agent]:
        """
        대화 유형에 필요한 에이전트 집합 생성
        
        Args:
            dialogue_type: 대화 유형
            
        Returns:
            에이전트 인스턴스 사전 (역할별)
        """
        config = self.load_dialogue_config(dialogue_type)
        agents = {}
        
        for role, agent_config in config.get("agents", {}).items():
            agent_type = agent_config.get("type")
            agent_class = AgentRegistry.get_agent_class(agent_type)
            
            if not agent_class:
                raise ValueError(f"Unknown agent type: {agent_type}")
                
            agent_id = f"{dialogue_type}_{role}_{agent_config.get('id', '001')}"
            agent_name = agent_config.get("name", role.capitalize())
            
            agents[role] = agent_class(
                agent_id=agent_id,
                name=agent_name,
                config=agent_config
            )
            
        return agents 