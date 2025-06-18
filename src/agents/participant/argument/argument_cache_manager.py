"""
Argument caching and management module for debate participants.

Handles argument preparation, caching, and retrieval for efficient debate performance.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ArgumentCacheManager:
    """입론 캐싱 및 관리를 담당하는 클래스"""
    
    def __init__(self, agent_id: str):
        """
        ArgumentCacheManager 초기화
        
        Args:
            agent_id: 에이전트 ID
        """
        self.agent_id = agent_id
        
        # 캐시 관련 상태
        self.prepared_argument = ""
        self.argument_ready = False
        self.is_preparing = False
        self.last_context = None
        self.argument_preparation_task = None
        
        # 성능 추적
        self.preparation_start_time = None
        self.preparation_end_time = None
    
    def is_argument_ready(self) -> bool:
        """
        입론이 준비되었는지 확인
        
        Returns:
            입론 준비 완료 여부
        """
        return self.argument_ready and bool(self.prepared_argument)
    
    def is_currently_preparing(self) -> bool:
        """
        현재 입론을 준비 중인지 확인
        
        Returns:
            입론 준비 중 여부
        """
        return self.is_preparing
    
    def invalidate_argument_cache(self):
        """입론 캐시 무효화"""
        logger.info(f"[{self.agent_id}] Invalidating argument cache")
        self.prepared_argument = ""
        self.argument_ready = False
        self.last_context = None
        
        # 진행 중인 준비 작업이 있다면 취소
        if self.argument_preparation_task and not self.argument_preparation_task.done():
            self.argument_preparation_task.cancel()
            logger.info(f"[{self.agent_id}] Cancelled ongoing argument preparation task")
    
    def _is_same_context(self, context: Dict[str, Any]) -> bool:
        """
        컨텍스트가 이전과 동일한지 확인
        
        Args:
            context: 현재 컨텍스트
            
        Returns:
            컨텍스트 동일 여부
        """
        if self.last_context is None:
            return False
        
        # 주요 필드들만 비교
        key_fields = ['topic', 'stance_statement', 'debate_stage']
        
        for field in key_fields:
            if context.get(field) != self.last_context.get(field):
                return False
        
        return True
    
    async def prepare_argument_async(self, topic: str, stance_statement: str, 
                                   context: Dict[str, Any], 
                                   argument_generator, rag_enhancer) -> Dict[str, Any]:
        """
        비동기적으로 입론 준비
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 토론 컨텍스트
            argument_generator: ArgumentGenerator 인스턴스
            rag_enhancer: RAGArgumentEnhancer 인스턴스
            
        Returns:
            준비 결과
        """
        # 이미 같은 컨텍스트로 준비된 입론이 있다면 반환
        if self.is_argument_ready() and self._is_same_context(context):
            logger.info(f"[{self.agent_id}] Using cached argument for same context")
            return {
                "status": "cached",
                "argument": self.prepared_argument,
                "preparation_time": 0.0
            }
        
        # 이미 준비 중이라면 기다림
        if self.is_currently_preparing():
            logger.info(f"[{self.agent_id}] Argument preparation already in progress, waiting...")
            if self.argument_preparation_task:
                try:
                    return await self.argument_preparation_task
                except asyncio.CancelledError:
                    logger.warning(f"[{self.agent_id}] Previous preparation task was cancelled")
        
        # 새로운 준비 작업 시작
        self.argument_preparation_task = asyncio.create_task(
            self._prepare_argument_internal(topic, stance_statement, context, 
                                          argument_generator, rag_enhancer)
        )
        
        try:
            result = await self.argument_preparation_task
            return result
        except asyncio.CancelledError:
            logger.warning(f"[{self.agent_id}] Argument preparation was cancelled")
            return {
                "status": "cancelled",
                "argument": "",
                "preparation_time": 0.0
            }
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in async argument preparation: {str(e)}")
            return {
                "status": "error",
                "argument": "",
                "preparation_time": 0.0,
                "error": str(e)
            }
    
    async def _prepare_argument_internal(self, topic: str, stance_statement: str,
                                       context: Dict[str, Any],
                                       argument_generator, rag_enhancer) -> Dict[str, Any]:
        """
        내부 입론 준비 로직
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 토론 컨텍스트
            argument_generator: ArgumentGenerator 인스턴스
            rag_enhancer: RAGArgumentEnhancer 인스턴스
            
        Returns:
            준비 결과
        """
        self.preparation_start_time = datetime.now()
        self.is_preparing = True
        
        try:
            logger.info(f"[{self.agent_id}] Starting argument preparation for topic: {topic}")
            
            # 동기 함수를 비동기로 실행
            def prepare_sync():
                # ===== 기존 방식 (주석 처리) =====
                # 1. 핵심 주장 생성
                # core_arguments = argument_generator.generate_core_arguments(topic, stance_statement)
                
                # 2. RAG 쿼리 생성
                # core_arguments = rag_enhancer.generate_rag_queries_for_arguments(topic, core_arguments)
                
                # 3. RAG 검색으로 주장 강화
                # strengthened_arguments = rag_enhancer.strengthen_arguments_with_rag(core_arguments)
                
                # ===== 새로운 최적화 방식 =====
                # 1. 핵심 주장과 RAG 쿼리를 한 번에 생성 (LLM 호출 1회 절약)
                core_arguments_with_queries = argument_generator.generate_arguments_with_queries(topic, stance_statement)
                
                # 2. RAG 검색으로 주장 강화 (쿼리 생성 단계 스킵)
                strengthened_arguments = rag_enhancer.strengthen_arguments_with_rag(core_arguments_with_queries)
                
                # 3. 최종 입론 생성
                final_argument = argument_generator.generate_final_opening_argument(
                    topic, stance_statement, strengthened_arguments
                )
                
                return final_argument, strengthened_arguments
            
            # CPU 집약적 작업을 별도 스레드에서 실행
            loop = asyncio.get_event_loop()
            final_argument, strengthened_arguments = await loop.run_in_executor(
                None, prepare_sync
            )
            
            # 결과 저장
            self.prepared_argument = final_argument
            self.argument_ready = True
            self.last_context = context.copy()
            
            self.preparation_end_time = datetime.now()
            preparation_time = (self.preparation_end_time - self.preparation_start_time).total_seconds()
            
            logger.info(f"[{self.agent_id}] Argument preparation completed in {preparation_time:.2f}s")
            
            return {
                "status": "success",
                "argument": final_argument,
                "preparation_time": preparation_time,
                "core_arguments": strengthened_arguments
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error during argument preparation: {str(e)}")
            return {
                "status": "error",
                "argument": "",
                "preparation_time": 0.0,
                "error": str(e)
            }
        finally:
            self.is_preparing = False
    
    def get_prepared_argument_or_generate(self, topic: str, stance_statement: str,
                                        context: Dict[str, Any],
                                        argument_generator, rag_enhancer) -> Tuple[str, Dict[str, Any]]:
        """
        준비된 입론을 반환하거나 즉시 생성
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 토론 컨텍스트
            argument_generator: ArgumentGenerator 인스턴스
            rag_enhancer: RAGArgumentEnhancer 인스턴스
            
        Returns:
            (입론 텍스트, RAG 정보 포함 메타데이터)
        """
        # 캐시된 입론이 있고 컨텍스트가 같다면 반환
        if self.is_argument_ready() and self._is_same_context(context):
            logger.info(f"[{self.agent_id}] Returning cached argument")
            
            # 캐시된 경우에도 RAG 정보 추출 시도
            rag_info = self._extract_rag_info_from_enhancer(rag_enhancer)
            
            return self.prepared_argument, {
                "status": "cached",
                "preparation_time": 0.0,
                **rag_info  # RAG 정보 포함
            }
        
        # 캐시된 입론이 없거나 컨텍스트가 다르면 즉시 생성
        logger.info(f"[{self.agent_id}] No suitable cached argument, generating immediately")
        
        start_time = datetime.now()
        
        try:
            # ===== 기존 방식 (주석 처리) =====
            # 1. 핵심 주장 생성
            # core_arguments = argument_generator.generate_core_arguments(topic, stance_statement)
            
            # 2. RAG 쿼리 생성 (간소화)
            # core_arguments = rag_enhancer.generate_rag_queries_for_arguments(topic, core_arguments)
            
            # 3. RAG 검색으로 주장 강화 (제한적)
            # strengthened_arguments = rag_enhancer.strengthen_arguments_with_rag(core_arguments)
            
            # ===== 새로운 최적화 방식 =====
            # 1. 핵심 주장과 RAG 쿼리를 한 번에 생성 (LLM 호출 1회 절약)
            core_arguments_with_queries = argument_generator.generate_arguments_with_queries(topic, stance_statement)
            
            # 2. RAG 검색으로 주장 강화 (쿼리 생성 단계 스킵)
            strengthened_arguments = rag_enhancer.strengthen_arguments_with_rag(core_arguments_with_queries)
            
            # 3. 최종 입론 생성
            final_argument = argument_generator.generate_final_opening_argument(
                topic, stance_statement, strengthened_arguments
            )
            
            # 5. ✅ RAG 정보 추출
            rag_info = self._extract_rag_info_from_enhancer(rag_enhancer)
            
            # 결과 캐시
            self.prepared_argument = final_argument
            self.argument_ready = True
            self.last_context = context.copy()
            
            end_time = datetime.now()
            preparation_time = (end_time - start_time).total_seconds()
            
            logger.info(f"[{self.agent_id}] Immediate argument generation completed in {preparation_time:.2f}s")
            
            return final_argument, {
                "status": "generated",
                "preparation_time": preparation_time,
                "core_arguments": strengthened_arguments,
                **rag_info  # ✅ RAG 정보 포함
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in immediate argument generation: {str(e)}")
            
            # 실패 시 기본 입론 반환
            fallback_argument = f"As a philosopher, I believe {stance_statement} based on fundamental principles of reasoning and human nature."
            
            return fallback_argument, {
                "status": "fallback",
                "preparation_time": 0.0,
                "error": str(e),
                # 실패 시 기본 RAG 정보
                "rag_used": False,
                "rag_source_count": 0,
                "rag_sources": []
            }
    
    def _extract_rag_info_from_enhancer(self, rag_enhancer) -> Dict[str, Any]:
        """
        RAGArgumentEnhancer에서 RAG 정보 추출
        
        Args:
            rag_enhancer: RAGArgumentEnhancer 인스턴스
            
        Returns:
            RAG 정보 딕셔너리
        """
        try:
            # RAGArgumentEnhancer에서 rag_info 속성 확인
            if hasattr(rag_enhancer, 'rag_info') and rag_enhancer.rag_info:
                rag_info = rag_enhancer.rag_info
                return {
                    "rag_used": rag_info.get("rag_used", False),
                    "rag_source_count": rag_info.get("rag_source_count", 0),
                    "rag_sources": rag_info.get("rag_sources", [])
                }
            
            # 대안: RAGArgumentEnhancer의 다른 속성들 확인
            elif hasattr(rag_enhancer, 'search_results') and rag_enhancer.search_results:
                search_results = rag_enhancer.search_results
                return {
                    "rag_used": len(search_results) > 0,
                    "rag_source_count": len(search_results),
                    "rag_sources": search_results[:5]  # 상위 5개만
                }
            
            # 기본값 반환
            else:
                return {
                    "rag_used": False,
                    "rag_source_count": 0,
                    "rag_sources": []
                }
                
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Error extracting RAG info: {str(e)}")
            return {
                "rag_used": False,
                "rag_source_count": 0,
                "rag_sources": []
            }
    
    def get_preparation_status(self) -> Dict[str, Any]:
        """
        현재 준비 상태 반환
        
        Returns:
            준비 상태 정보
        """
        status = {
            "is_ready": self.is_argument_ready(),
            "is_preparing": self.is_currently_preparing(),
            "has_cached_argument": bool(self.prepared_argument),
            "last_context": self.last_context
        }
        
        if self.preparation_start_time and self.preparation_end_time:
            status["last_preparation_time"] = (
                self.preparation_end_time - self.preparation_start_time
            ).total_seconds()
        
        return status 