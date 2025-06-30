"""
Fast Debate Opening Service

기존 55초 → 3초로 단축시키는 핵심 서비스
기존 chat.py와 호환되는 인터페이스 제공
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
import redis
import json
import hashlib

from ..models.debate_models import (
    FastDebateRequest, FastDebateResponse, DebatePackage,
    ModeratorStyle, ContextType, PerformanceMetrics
)
from .openai_service import OpenAIDebateService

logger = logging.getLogger(__name__)

class FastDebateOpeningService:
    """🚀 초고속 토론 오프닝 생성 서비스"""
    
    def __init__(self, use_cache: bool = True, use_fine_tuned: bool = False):
        self.openai_service = OpenAIDebateService(use_fine_tuned=use_fine_tuned)
        self.use_cache = use_cache
        
        # Redis 캐시 (선택적)
        try:
            if use_cache:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.cache_ttl = 24 * 60 * 60  # 24시간
            else:
                self.redis_client = None
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            self.redis_client = None
    
    async def create_fast_debate_room(self, 
                                    room_id: str,
                                    title: str, 
                                    context: str = "",
                                    pro_npcs: list = None,
                                    con_npcs: list = None,
                                    user_ids: list = None,
                                    user_side: str = "neutral",
                                    moderator_style: str = "0") -> FastDebateResponse:
        """🔥 기존 chat.py 호환 인터페이스 - 3초 목표"""
        
        total_start = time.time()
        
        # 요청 객체 생성
        request = FastDebateRequest(
            room_id=room_id,
            title=title,
            context=context,
            context_type=self._detect_context_type(context),
            pro_npcs=pro_npcs or [],
            con_npcs=con_npcs or [],
            user_ids=user_ids or [],
            user_side=user_side,
            moderator_style=ModeratorStyle(moderator_style)
        )
        
        # 1단계: 캐시 확인 (0.1초)
        cache_start = time.time()
        cached_package = await self._get_from_cache(request)
        cache_time = time.time() - cache_start
        
        if cached_package:
            logger.info(f"🎯 Cache HIT! Returning cached result in {cache_time:.3f}s")
            return FastDebateResponse(
                room_id=room_id,
                debate_package=cached_package,
                performance_metrics={
                    "total_time": time.time() - total_start,
                    "cache_hit": True,
                    "cache_time": cache_time
                },
                cache_hit=True
            )
        
        # 2단계: 빠른 생성 (2-3초)
        api_start = time.time()
        debate_package = await self.openai_service.generate_complete_debate_package(request)
        api_time = time.time() - api_start
        
        # 3단계: 캐시에 저장 (백그라운드)
        if self.redis_client:
            asyncio.create_task(self._save_to_cache(request, debate_package))
        
        total_time = time.time() - total_start
        
        # 성능 메트릭
        performance_metrics = PerformanceMetrics(
            total_time=total_time,
            api_call_time=api_time,
            cache_check_time=cache_time,
            processing_time=total_time - api_time - cache_time,
            system_version="v2_fast"
        )
        
        logger.info(f"✅ Fast debate created in {total_time:.2f}s (API: {api_time:.2f}s)")
        
        return FastDebateResponse(
            room_id=room_id,
            debate_package=debate_package,
            performance_metrics=performance_metrics.dict(),
            cache_hit=False
        )
    
    async def _get_from_cache(self, request: FastDebateRequest) -> Optional[DebatePackage]:
        """캐시에서 토론 패키지 조회"""
        
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(request)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                package_data = json.loads(cached_data)
                return DebatePackage(**package_data)
                
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    async def _save_to_cache(self, request: FastDebateRequest, package: DebatePackage):
        """캐시에 토론 패키지 저장 (백그라운드)"""
        
        if not self.redis_client:
            return
        
        try:
            cache_key = self._generate_cache_key(request)
            package_json = package.json()
            
            self.redis_client.setex(
                cache_key, 
                self.cache_ttl, 
                package_json
            )
            
            logger.info(f"💾 Cached debate package: {cache_key}")
            
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")
    
    def _generate_cache_key(self, request: FastDebateRequest) -> str:
        """캐시 키 생성"""
        
        # 중요한 필드들로 해시 생성
        key_data = {
            "title": request.title,
            "context": request.context[:100] if request.context else "",  # 컨텍스트는 처음 100자만
            "pro_npcs": sorted(request.pro_npcs),
            "con_npcs": sorted(request.con_npcs),
            "moderator_style": request.moderator_style.value
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"debate_package:{hash_key}"
    
    def _detect_context_type(self, context: str) -> ContextType:
        """컨텍스트 타입 자동 감지"""
        
        if not context.strip():
            return ContextType.EMPTY
        
        context_lower = context.lower().strip()
        
        if context_lower.startswith(('http://', 'https://', 'www.')):
            return ContextType.URL
        elif context_lower.endswith('.pdf') or 'pdf' in context_lower:
            return ContextType.PDF
        else:
            return ContextType.TEXT
    
    async def get_compatible_opening_data(self, request: FastDebateRequest) -> Dict[str, Any]:
        """기존 시스템과 호환되는 오프닝 데이터 반환"""
        
        response = await self.create_fast_debate_room(
            room_id=request.room_id,
            title=request.title,
            context=request.context,
            pro_npcs=request.pro_npcs,
            con_npcs=request.con_npcs,
            user_ids=request.user_ids,
            user_side=request.user_side,
            moderator_style=request.moderator_style.value
        )
        
        package = response.debate_package
        
        # 기존 시스템 형식으로 변환
        return {
            "stance_statements": {
                "pro": package.stance_statements.pro,
                "con": package.stance_statements.con
            },
            "opening_message": package.opening_message,
            "context_summary": package.context_summary.dict() if package.context_summary else None,
            "performance": {
                "generation_time": package.generation_time,
                "system_version": package.system_version,
                "cache_hit": response.cache_hit
            }
        }

    async def warm_popular_cache(self, popular_combinations: list):
        """인기 조합들을 미리 캐시에 저장"""
        
        logger.info(f"🔥 Warming cache for {len(popular_combinations)} popular combinations")
        
        tasks = []
        for combo in popular_combinations:
            request = FastDebateRequest(**combo)
            task = self.openai_service.generate_complete_debate_package(request)
            tasks.append((request, task))
        
        # 병렬 처리
        for request, task in tasks:
            try:
                package = await task
                await self._save_to_cache(request, package)
            except Exception as e:
                logger.error(f"Failed to warm cache for {request.title}: {e}")
        
        logger.info("✅ Cache warming completed")

    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 반환"""
        
        # 실제 운영에서는 메트릭을 추적하고 저장해야 함
        return {
            "system_version": "v2_fast",
            "target_time": "3 seconds",
            "cache_enabled": self.redis_client is not None,
            "fine_tuned_model": self.openai_service.use_fine_tuned
        }


# 기존 chat.py와의 통합을 위한 헬퍼 함수들
async def create_fast_debate_compatible(room_id: str, 
                                      title: str,
                                      context: str = "",
                                      pro_npcs: list = None,
                                      con_npcs: list = None,
                                      user_ids: list = None,
                                      user_side: str = "neutral", 
                                      moderator_style: str = "0") -> Dict[str, Any]:
    """🔥 기존 chat.py에서 직접 호출할 수 있는 함수"""
    
    service = FastDebateOpeningService(use_cache=True, use_fine_tuned=False)
    
    response = await service.create_fast_debate_room(
        room_id=room_id,
        title=title, 
        context=context,
        pro_npcs=pro_npcs or [],
        con_npcs=con_npcs or [],
        user_ids=user_ids or [],
        user_side=user_side,
        moderator_style=moderator_style
    )
    
    # 기존 형식으로 반환
    package = response.debate_package
    
    return {
        "status": "success",
        "room_id": room_id,
        "stance_statements": {
            "pro": package.stance_statements.pro,
            "con": package.stance_statements.con
        },
        "opening_message": package.opening_message,
        "context_summary": package.context_summary.dict() if package.context_summary else None,
        "philosopher_profiles": [p.dict() for p in package.philosopher_profiles],
        "performance": response.performance_metrics,
        "system_version": "v2_fast",
        "cache_hit": response.cache_hit
    }

async def test_vs_original_system(test_cases: list) -> Dict[str, Any]:
    """기존 시스템 vs 새 시스템 성능 비교"""
    
    service = FastDebateOpeningService()
    
    # 새 시스템 테스트
    new_system_results = []
    total_start = time.time()
    
    for case in test_cases:
        start = time.time()
        try:
            result = await service.create_fast_debate_room(**case)
            duration = time.time() - start
            new_system_results.append({
                "topic": case["title"],
                "time": duration,
                "success": True,
                "cache_hit": result.cache_hit
            })
        except Exception as e:
            new_system_results.append({
                "topic": case["title"], 
                "time": time.time() - start,
                "success": False,
                "error": str(e)
            })
    
    total_new_time = time.time() - total_start
    
    return {
        "new_system": {
            "total_time": total_new_time,
            "average_time": total_new_time / len(test_cases),
            "results": new_system_results
        },
        "estimated_original_time": len(test_cases) * 55,  # 기존 시스템 추정치
        "improvement": f"{((len(test_cases) * 55 - total_new_time) / (len(test_cases) * 55) * 100):.1f}%"
    } 