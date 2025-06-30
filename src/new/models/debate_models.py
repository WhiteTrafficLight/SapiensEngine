"""
Fast Debate System Data Models

간소화되고 성능 최적화된 토론 시스템을 위한 데이터 모델들
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import time

class ModeratorStyle(Enum):
    CASUAL_YOUNG = "0"  # Jamie the Host
    ACADEMIC = "1"      # Dr. Lee  
    YOUTUBER = "2"      # Zuri Show
    SERIOUS = "3"       # Elias of the End
    EDUCATIONAL = "4"   # Miss Hana

class ContextType(Enum):
    TEXT = "text"
    URL = "url"
    PDF = "pdf"
    EMPTY = ""

class FastDebateRequest(BaseModel):
    """빠른 토론 생성 요청"""
    room_id: str
    title: str
    context: str = ""
    context_type: ContextType = ContextType.EMPTY
    pro_npcs: List[str]
    con_npcs: List[str]
    user_ids: List[str] = []
    user_side: str = "neutral"
    moderator_style: ModeratorStyle = ModeratorStyle.CASUAL_YOUNG
    
class StanceStatements(BaseModel):
    """찬반 입장 진술문"""
    pro: str = Field(..., description="찬성 입장 진술문")
    con: str = Field(..., description="반대 입장 진술문")

class ContextSummary(BaseModel):
    """컨텍스트 요약"""
    summary: str = Field(..., description="핵심 내용 요약") 
    key_points: List[str] = Field(default_factory=list, description="주요 포인트들")
    relevant_quotes: List[str] = Field(default_factory=list, description="관련 인용문들")

class PhilosopherProfile(BaseModel):
    """철학자 프로필 (간소화)"""
    id: str
    name: str
    key_ideas: List[str] = Field(default_factory=list)
    debate_style: str = ""

class DebatePackage(BaseModel):
    """완전한 토론 패키지 (단일 API 호출 결과)"""
    stance_statements: StanceStatements
    context_summary: Optional[ContextSummary] = None
    opening_message: str
    generation_time: float = Field(default_factory=time.time)
    system_version: str = "v2_fast"

class FastDebateResponse(BaseModel):
    """빠른 토론 생성 응답"""
    status: str = "success"
    room_id: str
    debate_package: DebatePackage
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    cache_hit: bool = False

class PerformanceMetrics(BaseModel):
    """성능 측정 데이터"""
    total_time: float
    api_call_time: float
    cache_check_time: float
    processing_time: float
    tokens_used: int = 0
    cost_estimate: float = 0.0
    system_version: str = "v2_fast" 