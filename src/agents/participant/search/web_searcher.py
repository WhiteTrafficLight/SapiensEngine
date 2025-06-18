"""
웹 검색 클래스

Google 검색 API를 통한 웹 검색 기능을 제공합니다.
"""

from typing import Dict, List, Any
import logging
from .base_searcher import BaseSearcher

logger = logging.getLogger(__name__)


class WebSearcher(BaseSearcher):
    """웹 검색을 수행하는 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        웹 검색 클래스 초기화
        
        Args:
            config: 웹 검색 설정
        """
        super().__init__(config)
        self.web_crawling = config.get("web_crawling", False)
        self.search_provider = config.get("search_provider", "google")
        self.embedding_model = config.get("embedding_model", "all-MiniLM-L6-v2")
        self.cache_dir = config.get("cache_dir", "./.cache/web_search_debate")
        
        # WebSearchRetriever 인스턴스 (지연 초기화)
        self.web_retriever = None
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        웹 검색 수행
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            if self.web_crawling:
                return self._search_with_crawling(query)
            else:
                return self._search_snippet_only(query)
        except Exception as e:
            self._log_search_error(query, e)
            return []
    
    def _search_snippet_only(self, query: str) -> List[Dict[str, Any]]:
        """
        스니펫만 사용하는 웹 검색 (크롤링 없음)
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            self._initialize_web_retriever_basic()
            
            # 실제 웹 검색 수행
            web_results = self.web_retriever.search(query, self.max_results)
            
            if web_results:
                results = []
                for item in web_results:
                    result = {
                        "title": item.get("title", ""),
                        "content": item.get("snippet", ""),
                        "url": item.get("url", ""),
                        "source": "web",
                        "relevance_score": 0.85,
                        "metadata": {
                            "search_type": "snippet_only",
                            "provider": self.search_provider
                        }
                    }
                    results.append(result)
                
                formatted_results = self._format_results(results)
                self._log_search_attempt(query, len(formatted_results))
                return formatted_results
            else:
                logger.warning(f"[WEB] No results found for query: {query}")
                return []
                
        except Exception as e:
            logger.warning(f"[WEB] Snippet search failed: {str(e)}")
            return []
    
    def _search_with_crawling(self, query: str) -> List[Dict[str, Any]]:
        """
        크롤링을 포함한 웹 검색
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        try:
            self._initialize_web_retriever_advanced()
            
            # 실제 웹 검색 + 크롤링 + 청크화
            extracted_chunks = self.web_retriever.retrieve_and_extract(
                query=query,
                max_pages=3,
                chunk_size=500,
                chunk_overlap=50,
                rerank=True
            )
            
            if extracted_chunks:
                results = []
                # 각 쿼리당 최대 10개로 제한
                for chunk in extracted_chunks[:10]:
                    result = {
                        "title": chunk["metadata"].get("title", "Web Content"),
                        "content": chunk["text"],
                        "url": chunk["metadata"].get("url", ""),
                        "source": "web",
                        "relevance_score": chunk.get("similarity", 0.85),
                        "metadata": {
                            "search_type": "crawling",
                            "score": chunk.get("score", 0.85),
                            "domain": chunk["metadata"].get("domain", ""),
                            "word_count": chunk["metadata"].get("word_count", 0)
                        }
                    }
                    results.append(result)
                
                formatted_results = self._format_results(results)
                self._log_search_attempt(query, len(formatted_results))
                logger.info(f"[WEB] Retrieved {len(formatted_results)} web chunks (limited to 10)")
                return formatted_results
            else:
                logger.warning(f"[WEB] No web chunks retrieved for query: {query}")
                return []
                
        except Exception as e:
            logger.warning(f"[WEB] Crawling search failed: {str(e)}")
            return []
    
    def _initialize_web_retriever_basic(self):
        """기본 웹 검색 리트리버 초기화 (스니펫만)"""
        if self.web_retriever is None:
            try:
                from ....rag.retrieval.web_retriever import WebSearchRetriever
                self.web_retriever = WebSearchRetriever(
                    embedding_model=self.embedding_model,
                    search_provider=self.search_provider,
                    max_results=self.max_results
                )
            except ImportError:
                logger.error("[WEB] Failed to import WebSearchRetriever")
                raise
    
    def _initialize_web_retriever_advanced(self):
        """고급 웹 검색 리트리버 초기화 (크롤링 포함)"""
        if self.web_retriever is None:
            try:
                from ....rag.retrieval.web_retriever import WebSearchRetriever
                self.web_retriever = WebSearchRetriever(
                    search_provider=self.search_provider,
                    max_results=self.max_results,
                    cache_dir=self.cache_dir,
                    embedding_model="BAAI/bge-large-en-v1.5"
                )
            except ImportError:
                logger.error("[WEB] Failed to import advanced WebSearchRetriever")
                raise
    
    def _get_source_type(self) -> str:
        """소스 타입 반환"""
        return "web"
    
    def get_search_stats(self) -> Dict[str, Any]:
        """
        검색 통계 정보 반환
        
        Returns:
            검색 통계 딕셔너리
        """
        return {
            "search_type": "web",
            "crawling_enabled": self.web_crawling,
            "search_provider": self.search_provider,
            "max_results": self.max_results,
            "embedding_model": self.embedding_model
        } 