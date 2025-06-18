"""
철학자 검색 클래스

철학자 작품 및 철학적 관점 검색 기능을 제공합니다.
"""

from typing import Dict, List, Any
import logging
from .base_searcher import BaseSearcher

logger = logging.getLogger(__name__)


class PhilosopherSearcher(BaseSearcher):
    """철학자 작품 검색을 수행하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        철학자 검색 클래스 초기화
        
        Args:
            config: 철학자 검색 설정
        """
        super().__init__(config)
        self.db_path = config.get("db_path", "./vectordb")
        self.philosopher_collection = config.get("philosopher_collection", "philosopher_works")
        self.fallback_collection = config.get("fallback_collection", "default")
        self.embedding_model = config.get("embedding_model", "BAAI/bge-large-en-v1.5")
        self.use_fallback = config.get("use_fallback", True)
        
        # RAGManager 인스턴스 (지연 초기화)
        self.rag_manager = None
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        철학자 작품 검색 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            self._initialize_rag_manager()
            
            # 먼저 철학자 전용 컬렉션에서 검색
            results = self._search_philosopher_collection(query)
            
            # 결과가 부족하면 일반 컬렉션에서 철학 관련 검색
            if len(results) < self.max_results and self.use_fallback:
                fallback_results = self._search_with_philosophy_context(query)
                results.extend(fallback_results)
            
            # 최대 결과 수로 제한
            results = results[:self.max_results]
            
            formatted_results = self._format_results(results)
            self._log_search_attempt(query, len(formatted_results))
            return formatted_results
            
        except Exception as e:
            self._log_search_error(query, e)
            return []
    
    def _search_philosopher_collection(self, query: str) -> List[Dict[str, Any]]:
        """
        철학자 전용 컬렉션에서 검색
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            results = self.rag_manager.simple_top_k_search(
                collection_name=self.philosopher_collection,
                query=query,
                k=self.max_results
            )
            
            # 철학자 검색 결과 형식으로 변환
            converted_results = []
            for result in results:
                converted_result = {
                    "title": f"Philosophical work: {query[:30]}...",
                    "content": result.get("document", result.get("text", "")),
                    "author": result.get("metadata", {}).get("author", "Relevant Philosopher"),
                    "work": result.get("metadata", {}).get("work", "Famous Work"),
                    "url": result.get("metadata", {}).get("url", ""),
                    "source_type": "philosopher",
                    "relevance_score": 1 - result.get("distance", 0.0),
                    "metadata": {
                        "search_type": "philosopher_collection",
                        "collection": self.philosopher_collection,
                        "original_distance": result.get("distance", 0.0)
                    }
                }
                converted_results.append(converted_result)
            
            return converted_results
            
        except Exception as e:
            logger.warning(f"[PHILOSOPHER] Philosopher collection search failed: {str(e)}")
            return []
    
    def _search_with_philosophy_context(self, query: str) -> List[Dict[str, Any]]:
        """
        일반 컬렉션에서 철학 맥락을 추가하여 검색
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 철학적 맥락을 추가한 쿼리
            philosophy_query = f"philosophy {query} philosophical perspective"
            
            results = self.rag_manager.simple_top_k_search(
                collection_name=self.fallback_collection,
                query=philosophy_query,
                k=min(self.max_results, 2)  # 폴백은 적게 가져오기
            )
            
            # 결과 형식 변환
            converted_results = []
            for result in results:
                converted_result = {
                    "title": f"Philosophical perspective: {query[:30]}...",
                    "content": result.get("document", result.get("text", "")),
                    "author": "Relevant Philosopher",
                    "work": "Academic Work",
                    "url": result.get("metadata", {}).get("url", ""),
                    "source_type": "philosopher",
                    "relevance_score": (1 - result.get("distance", 0.0)) * 0.8,  # 폴백은 점수 조금 낮춤
                    "metadata": {
                        "search_type": "philosophy_fallback",
                        "collection": self.fallback_collection,
                        "original_distance": result.get("distance", 0.0)
                    }
                }
                converted_results.append(converted_result)
            
            return converted_results
            
        except Exception as e:
            logger.warning(f"[PHILOSOPHER] Philosophy fallback search failed: {str(e)}")
            return []
    
    def _initialize_rag_manager(self):
        """RAG 매니저 초기화"""
        if self.rag_manager is None:
            try:
                from ....rag.retrieval.rag_manager import RAGManager
                self.rag_manager = RAGManager(
                    db_path=self.db_path,
                    embedding_model=self.embedding_model
                )
            except ImportError:
                logger.error("[PHILOSOPHER] Failed to import RAGManager")
                raise
    
    def _get_source_type(self) -> str:
        """소스 타입 반환"""
        return "philosopher"
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        검색 통계 정보 반환
        
        Returns:
            검색 통계 딕셔너리
        """
        return {
            "search_type": "philosopher",
            "db_path": self.db_path,
            "philosopher_collection": self.philosopher_collection,
            "fallback_collection": self.fallback_collection,
            "embedding_model": self.embedding_model,
            "use_fallback": self.use_fallback,
            "max_results": self.max_results
        } 