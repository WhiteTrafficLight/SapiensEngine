"""
토론 대화를 위한 컨텍스트 관리 모듈

이 패키지는 토론 대화에서 사용될 컨텍스트(기사, 논문 등)를 
효과적으로 관리하고 요약하는 기능을 제공합니다.
"""

from .debate_context_manager import DebateContextManager
from .summary_templates import SummaryTemplates

__all__ = ["DebateContextManager", "SummaryTemplates"] 