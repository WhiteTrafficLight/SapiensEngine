"""
RAG 검색 매니저

다양한 검색 소스를 통합 관리하고 결과를 조합하는 클래스입니다.
"""

from typing import Dict, List, Any, Optional
import logging
from .base_searcher import BaseSearcher
from .web_searcher import WebSearcher
from .vector_searcher import VectorSearcher
from .philosopher_searcher import PhilosopherSearcher

logger = logging.getLogger(__name__)


class RAGSearchManager:
    """RAG 검색을 통합 관리하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        RAG 검색 매니저 초기화
        
        Args:
            config: 검색 설정
        """
        self.config = config
        self.max_total_results = config.get("max_total_results", 10)
        
        # 검색 소스별 가중치
        self.source_weights = config.get("source_weights", {
            "web": 0.4,
            "vector": 0.3,
            "philosopher": 0.2,
            "dialogue": 0.1
        })
        
        # 검색 클래스들 초기화
        self.searchers = {}
        self._initialize_searchers()
    
    def _initialize_searchers(self):
        """검색 클래스들 초기화"""
        try:
            # 웹 검색
            web_config = self.config.get("web_search", {})
            web_config.update({"max_results": 5})  # 개별 검색당 최대 결과 수
            self.searchers["web"] = WebSearcher(web_config)
            
            # 벡터 검색
            vector_config = self.config.get("vector_search", {})
            vector_config.update({"max_results": 5})
            self.searchers["vector"] = VectorSearcher(vector_config)
            
            # 철학자 검색
            philosopher_config = self.config.get("philosopher_search", {})
            philosopher_config.update({"max_results": 3})
            self.searchers["philosopher"] = PhilosopherSearcher(philosopher_config)
            
        except Exception as e:
            logger.error(f"[RAG_MANAGER] Failed to initialize searchers: {str(e)}")
    
    def search_all_sources(self, query: str, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        모든 소스에서 검색 수행
        
        Args:
            query: 검색 쿼리
            sources: 사용할 검색 소스 리스트 (None이면 모든 소스 사용)
            
        Returns:
            통합된 검색 결과 리스트
        """
        if sources is None:
            sources = list(self.searchers.keys())
        
        all_results = []
        
        for source in sources:
            if source in self.searchers:
                try:
                    results = self.searchers[source].search(query)
                    
                    # 소스별 가중치 적용
                    weight = self.source_weights.get(source, 1.0)
                    for result in results:
                        result["weighted_score"] = result.get("relevance_score", 0.0) * weight
                        result["search_source"] = source
                    
                    all_results.extend(results)
                    logger.info(f"[RAG_MANAGER] {source.upper()} search: {len(results)} results")
                    
                except Exception as e:
                    logger.error(f"[RAG_MANAGER] {source.upper()} search failed: {str(e)}")
        
        # 결과 정렬 및 제한
        sorted_results = self._rank_and_filter_results(all_results)
        
        logger.info(f"[RAG_MANAGER] Total combined results: {len(sorted_results)}")
        return sorted_results
    
    def search_web_only(self, query: str) -> List[Dict[str, Any]]:
        """
        웹 검색만 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            웹 검색 결과 리스트
        """
        if "web" in self.searchers:
            return self.searchers["web"].search(query)
        return []
    
    def search_vector_only(self, query: str) -> List[Dict[str, Any]]:
        """
        벡터 검색만 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            벡터 검색 결과 리스트
        """
        if "vector" in self.searchers:
            return self.searchers["vector"].search(query)
        return []
    
    def search_philosopher_only(self, query: str) -> List[Dict[str, Any]]:
        """
        철학자 검색만 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            철학자 검색 결과 리스트
        """
        if "philosopher" in self.searchers:
            return self.searchers["philosopher"].search(query)
        return []
    
    def search_with_fallback(self, query: str, primary_sources: List[str], 
                           fallback_sources: List[str], min_results: int = 3) -> List[Dict[str, Any]]:
        """
        우선 소스에서 검색하고, 결과가 부족하면 대체 소스 사용
        
        Args:
            query: 검색 쿼리
            primary_sources: 우선 검색 소스들
            fallback_sources: 대체 검색 소스들
            min_results: 최소 필요 결과 수
            
        Returns:
            검색 결과 리스트
        """
        # 우선 소스에서 검색
        results = self.search_all_sources(query, primary_sources)
        
        # 결과가 부족하면 대체 소스 사용
        if len(results) < min_results:
            logger.info(f"[RAG_MANAGER] Primary sources returned {len(results)} results, using fallback")
            fallback_results = self.search_all_sources(query, fallback_sources)
            
            # 중복 제거하면서 결합
            existing_urls = {r.get("url", "") for r in results}
            for result in fallback_results:
                if result.get("url", "") not in existing_urls:
                    results.append(result)
        
        return self._rank_and_filter_results(results)
    
    def _rank_and_filter_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색 결과 순위 매기기 및 필터링
        
        Args:
            results: 원본 검색 결과 리스트
            
        Returns:
            순위가 매겨지고 필터링된 결과 리스트
        """
        if not results:
            return []
        
        # 가중 점수로 정렬
        sorted_results = sorted(
            results, 
            key=lambda x: x.get("weighted_score", x.get("relevance_score", 0.0)), 
            reverse=True
        )
        
        # 중복 URL 제거
        unique_results = []
        seen_urls = set()
        
        for result in sorted_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
            elif not url:  # URL이 없는 경우 (예: 벡터 검색 결과)
                unique_results.append(result)
        
        # 최대 결과 수로 제한
        return unique_results[:self.max_total_results]
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        검색 통계 정보 반환
        
        Returns:
            검색 통계 딕셔너리
        """
        stats = {
            "available_searchers": list(self.searchers.keys()),
            "source_weights": self.source_weights,
            "max_total_results": self.max_total_results,
            "searcher_stats": {}
        }
        
        # 각 검색 클래스의 통계 정보 수집
        for source, searcher in self.searchers.items():
            if hasattr(searcher, "get_search_stats"):
                stats["searcher_stats"][source] = searcher.get_search_stats()
        
        return stats
    
    def update_source_weights(self, new_weights: Dict[str, float]):
        """
        소스별 가중치 업데이트
        
        Args:
            new_weights: 새로운 가중치 딕셔너리
        """
        self.source_weights.update(new_weights)
        logger.info(f"[RAG_MANAGER] Updated source weights: {self.source_weights}")
    
    def add_searcher(self, source_name: str, searcher: BaseSearcher, weight: float = 1.0):
        """
        새로운 검색 클래스 추가
        
        Args:
            source_name: 소스 이름
            searcher: 검색 클래스 인스턴스
            weight: 가중치
        """
        self.searchers[source_name] = searcher
        self.source_weights[source_name] = weight
        logger.info(f"[RAG_MANAGER] Added searcher: {source_name} (weight: {weight})")
    
    def remove_searcher(self, source_name: str):
        """
        검색 클래스 제거
        
        Args:
            source_name: 제거할 소스 이름
        """
        if source_name in self.searchers:
            del self.searchers[source_name]
            self.source_weights.pop(source_name, None)
            logger.info(f"[RAG_MANAGER] Removed searcher: {source_name}")


# 편의 함수들
def create_rag_search_manager(config: Dict[str, Any]) -> RAGSearchManager:
    """RAG 검색 매니저 생성 편의 함수"""
    return RAGSearchManager(config)


def search_for_debate_evidence(query: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """토론 증거 검색 편의 함수"""
    manager = RAGSearchManager(config)
    return manager.search_with_fallback(
        query=query,
        primary_sources=["web", "vector"],
        fallback_sources=["philosopher"],
        min_results=3
    ) 