"""
새로운 최적화된 토론 에이전트 패키지

기존 멀티 모듈 구조를 통합하고 OpenAI의 최신 기능들을 활용하여
성능을 대폭 개선한 에이전트들

주요 개선사항:
- OpenAI Function Calling 기반 통합 처리
- LangChain 워크플로우 활용
- CrewAI 협업 에이전트
- OpenAI Assistant API 활용
- 웹 검색 API 통합
"""

from .unified_debate_agent import UnifiedDebateAgent
from .langchain_debate_agent import LangChainDebateAgent  
from .crewai_debate_agent import CrewAIDebateAgent
from .assistant_api_agent import AssistantAPIDebateAgent

__all__ = [
    'UnifiedDebateAgent',
    'LangChainDebateAgent', 
    'CrewAIDebateAgent',
    'AssistantAPIDebateAgent'
] 