"""
베이스 검색 클래스

모든 검색 클래스의 공통 기능과 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseSearcher(ABC):
    """모든 검색 클래스의 베이스 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        베이스 검색 클래스 초기화
        
        Args:
            config: 검색 설정
        """
        self.config = config
        self.max_results = config.get("max_results", 5)
        self.timeout = config.get("timeout", 30)
    
    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        검색 수행 (추상 메서드)
        
        Args:
            query: 검색 쿼리
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색 결과를 표준 형식으로 포맷팅
        
        Args:
            results: 원본 검색 결과
            
        Returns:
            표준화된 검색 결과
        """
        formatted_results = []
        
        for result in results:
            formatted_result = {
                "title": result.get("title", "No title"),
                "content": result.get("content", result.get("snippet", "")),
                "url": result.get("url", result.get("link", "")),
                "source_type": self._get_source_type(),
                "relevance_score": result.get("relevance_score", 0.0),
                "metadata": result.get("metadata", {})
            }
            formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _get_source_type(self) -> str:
        """
        검색 소스 타입 반환
        
        Returns:
            소스 타입 문자열
        """
        return self.__class__.__name__.replace("Searcher", "").lower()
    
    def _extract_key_data(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        컨텐츠에서 핵심 데이터 추출
        
        Args:
            content: 원본 컨텐츠
            metadata: 메타데이터
            
        Returns:
            추출된 핵심 데이터
        """
        # 기본 구현: 컨텐츠를 적절한 길이로 자르기
        max_length = self.config.get("max_content_length", 500)
        
        if len(content) <= max_length:
            return content
        
        # 문장 단위로 자르기
        sentences = content.split('. ')
        result = ""
        
        for sentence in sentences:
            if len(result + sentence) <= max_length:
                result += sentence + ". "
            else:
                break
        
        return result.strip()
    
    def _calculate_relevance_score(self, result: Dict[str, Any], query: str) -> float:
        """
        검색 결과의 관련성 점수 계산
        
        Args:
            result: 검색 결과
            query: 검색 쿼리
            
        Returns:
            관련성 점수 (0.0 ~ 1.0)
        """
        # 기본 구현: 키워드 매칭 기반
        query_words = set(query.lower().split())
        content = (result.get("title", "") + " " + result.get("content", "")).lower()
        content_words = set(content.split())
        
        if not query_words:
            return 0.0
        
        # 교집합 비율 계산
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def _log_search_attempt(self, query: str, result_count: int):
        """
        검색 시도 로깅
        
        Args:
            query: 검색 쿼리
            result_count: 결과 개수
        """
        source_type = self._get_source_type()
        logger.info(f"[{source_type.upper()}] 검색 완료: '{query}' -> {result_count}개 결과")
    
    def _log_search_error(self, query: str, error: Exception):
        """
        검색 오류 로깅
        
        Args:
            query: 검색 쿼리
            error: 발생한 오류
        """
        source_type = self._get_source_type()
        logger.error(f"[{source_type.upper()}] 검색 실패: '{query}' - {str(error)}")


class SearchResult:
    """검색 결과를 나타내는 데이터 클래스"""
    
    def __init__(self, title: str, content: str, url: str = "", 
                 source_type: str = "", relevance_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        self.title = title
        self.content = content
        self.url = url
        self.source_type = source_type
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "source_type": self.source_type,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        } 