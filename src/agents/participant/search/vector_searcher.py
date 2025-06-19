"""
벡터 검색 클래스

기존 RAG 벡터 저장소를 활용한 검색 기능을 제공합니다.
"""

from typing import Dict, List, Any
import logging
from .base_searcher import BaseSearcher

logger = logging.getLogger(__name__)


class VectorSearcher(BaseSearcher):
    """벡터 검색을 수행하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        벡터 검색 클래스 초기화
        
        Args:
            config: 벡터 검색 설정
        """
        super().__init__(config)
        self.db_path = config.get("db_path", "./vectordb")
        self.collection_name = config.get("collection_name", "default")
        self.embedding_model = config.get("embedding_model", "BAAI/bge-large-en-v1.5")
        self.search_algorithm = config.get("search_algorithm", "merged_chunks")
        
        # RAGManager 인스턴스 (지연 초기화)
        self.rag_manager = None
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        벡터 검색 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            self._initialize_rag_manager()
            
            # 검색 알고리즘에 따라 다른 메서드 호출
            if self.search_algorithm == "simple_top_k":
                results = self.rag_manager.simple_top_k_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results
                )
            elif self.search_algorithm == "threshold":
                results = self.rag_manager.threshold_search(
                    collection_name=self.collection_name,
                    query=query,
                    threshold=0.7,
                    max_results=self.max_results
                )
            elif self.search_algorithm == "mmr":
                results = self.rag_manager.mmr_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results
                )
            elif self.search_algorithm == "merged_chunks":
                results = self.rag_manager.merged_chunks_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results,
                    merge_threshold=0.8
                )
            elif self.search_algorithm == "hybrid":
                results = self.rag_manager.hybrid_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results,
                    semantic_weight=0.7
                )
            elif self.search_algorithm == "semantic_window":
                results = self.rag_manager.semantic_window_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results,
                    window_size=5,
                    window_threshold=0.6
                )
            else:
                # 기본값으로 merged_chunks 사용 (성능이 가장 좋음)
                results = self.rag_manager.merged_chunks_search(
                    collection_name=self.collection_name,
                    query=query,
                    k=self.max_results,
                    merge_threshold=0.8
                )
            
            # 결과를 표준 형식으로 변환
            formatted_results = self._convert_rag_results(results)
            self._log_search_attempt(query, len(formatted_results))
            return formatted_results
            
        except Exception as e:
            self._log_search_error(query, e)
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
                logger.error("[VECTOR] Failed to import RAGManager")
                raise
    
    def _convert_rag_results(self, rag_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        RAG 검색 결과를 표준 형식으로 변환
        
        Args:
            rag_results: RAG 매니저에서 반환된 결과
            
        Returns:
            표준화된 검색 결과
        """
        converted_results = []
        
        for result in rag_results:
            converted_result = {
                "title": result.get("metadata", {}).get("title", "Vector Document"),
                "content": result.get("document", result.get("text", "")),
                "url": result.get("metadata", {}).get("url", ""),
                "source_type": "vector",
                "relevance_score": 1 - result.get("distance", 0.0),  # 거리를 유사도로 변환
                "metadata": {
                    "search_algorithm": self.search_algorithm,
                    "collection": self.collection_name,
                    "chunk_id": result.get("metadata", {}).get("chunk_id"),
                    "original_distance": result.get("distance", 0.0)
                }
            }
            converted_results.append(converted_result)
        
        return converted_results
    
    def _get_source_type(self) -> str:
        """소스 타입 반환"""
        return "vector"
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        검색 통계 정보 반환
        
        Returns:
            검색 통계 딕셔너리
        """
        return {
            "search_type": "vector",
            "db_path": self.db_path,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model,
            "search_algorithm": self.search_algorithm,
            "max_results": self.max_results
        } 