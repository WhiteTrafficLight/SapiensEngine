"""
Hybrid Progressive Strategy 토론 실험 패키지

기존 복잡한 멀티에이전트 시스템을 OpenAI Tool Calling으로 단순화한 실험
"""

from .debate_tools import PhilosophicalDebateTool, DebateExperiment, PhilosopherProfile, DebateContext
from .ai_vs_ai_debate import AIvsAIDebateExperiment
from .user_vs_ai_debate import UservsAIDebateExperiment

__version__ = "1.0.0"
__author__ = "Sapiens Engine"
__description__ = "Hybrid Progressive Strategy for Philosophical Debate using OpenAI Tools"

__all__ = [
    "PhilosophicalDebateTool",
    "DebateExperiment", 
    "PhilosopherProfile",
    "DebateContext",
    "AIvsAIDebateExperiment",
    "UservsAIDebateExperiment"
] 