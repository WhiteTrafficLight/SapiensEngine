"""
Google API를 이용한 직렬 웹서치 구현

기존 방식의 순차적인 웹서치를 구현하여 성능 비교 기준으로 사용
"""

import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)

class GoogleSerialSearcher:
    """
    Google API를 사용한 직렬 웹 검색기
    
    기존 방식의 순차적 검색을 구현하여 성능 비교 기준으로 사용
    """
    
    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None):
        """
        Google 직렬 검색기 초기화
        
        Args:
            api_key: Google API 키
            cx: Google Custom Search Engine ID
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("SEARCH_API_KEY")
        self.cx = cx or os.environ.get("GOOGLE_SEARCH_CX")
        
        if not self.api_key:
            raise ValueError("Google API 키가 설정되지 않았습니다. GOOGLE_API_KEY 환경변수를 설정해주세요.")
        
        if not self.cx:
            raise ValueError("Google Custom Search CX가 설정되지 않았습니다. GOOGLE_SEARCH_CX 환경변수를 설정해주세요.")
        
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.search_history = []
        
        logger.info("Google Serial Searcher 초기화 완료")
    
    def search_single_query(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        단일 쿼리 검색
        
        Args:
            query: 검색 쿼리
            num_results: 검색 결과 수
            
        Returns:
            검색 결과 딕셔너리
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Google API 검색 시작: '{query}'")
            
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": min(10, num_results)  # Google API 제한: 최대 10개
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 결과 파싱
            results = []
            if "items" in data:
                for item in data["items"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""), 
                        "snippet": item.get("snippet", ""),
                        "source": "google_api",
                        "domain": self._extract_domain(item.get("link", "")),
                        "position": len(results) + 1
                    }
                    results.append(result)
            
            end_time = time.time()
            search_time = end_time - start_time
            
            search_result = {
                "query": query,
                "results": results,
                "total_found": len(results),
                "search_time": search_time,
                "timestamp": datetime.now().isoformat(),
                "source": "google_api_serial"
            }
            
            self.search_history.append(search_result)
            
            logger.info(f"✅ Google API 검색 완료: {len(results)}개 결과 ({search_time:.2f}초)")
            
            return search_result
            
        except Exception as e:
            end_time = time.time()
            search_time = end_time - start_time
            
            logger.error(f"❌ Google API 검색 실패: {str(e)}")
            
            error_result = {
                "query": query,
                "results": [],
                "total_found": 0,
                "search_time": search_time,
                "timestamp": datetime.now().isoformat(),
                "source": "google_api_serial",
                "error": str(e)
            }
            
            self.search_history.append(error_result)
            return error_result
    
    def search_multiple_queries_serial(self, queries: List[str], num_results: int = 5) -> Dict[str, Any]:
        """
        여러 쿼리를 순차적으로 검색 (기존 방식)
        
        Args:
            queries: 검색 쿼리 리스트
            num_results: 각 쿼리당 검색 결과 수
            
        Returns:
            전체 검색 결과 딕셔너리
        """
        overall_start_time = time.time()
        
        logger.info(f"🎯 Google API 직렬 검색 시작: {len(queries)}개 쿼리")
        
        all_results = []
        individual_times = []
        
        for i, query in enumerate(queries, 1):
            logger.info(f"  [{i}/{len(queries)}] 검색 중: '{query}'")
            
            result = self.search_single_query(query, num_results)
            all_results.append(result)
            individual_times.append(result.get("search_time", 0))
            
            # Rate limiting을 위한 짧은 지연
            if i < len(queries):
                time.sleep(0.1)  # 100ms 지연
        
        overall_end_time = time.time()
        total_time = overall_end_time - overall_start_time
        
        # 결과 통합
        all_search_results = []
        total_found = 0
        
        for result in all_results:
            all_search_results.extend(result.get("results", []))
            total_found += result.get("total_found", 0)
        
        final_result = {
            "method": "google_api_serial",
            "queries": queries,
            "total_queries": len(queries),
            "all_results": all_search_results,
            "total_found": total_found,
            "individual_results": all_results,
            "individual_times": individual_times,
            "total_time": total_time,
            "average_time_per_query": total_time / len(queries) if queries else 0,
            "timestamp": datetime.now().isoformat(),
            "performance_stats": {
                "fastest_query": min(individual_times) if individual_times else 0,
                "slowest_query": max(individual_times) if individual_times else 0,
                "total_requests": len(queries),
                "successful_requests": len([r for r in all_results if not r.get("error")])
            }
        }
        
        logger.info(f"🏁 Google API 직렬 검색 완료:")
        logger.info(f"   📊 총 {len(queries)}개 쿼리, {total_found}개 결과")
        logger.info(f"   ⏱️  총 소요시간: {total_time:.2f}초")
        logger.info(f"   📈 쿼리당 평균: {final_result['average_time_per_query']:.2f}초")
        
        return final_result
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return "unknown"
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """검색 히스토리 반환"""
        return self.search_history
    
    def clear_history(self):
        """검색 히스토리 삭제"""
        self.search_history = []
        logger.info("검색 히스토리가 삭제되었습니다.")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 통계 반환"""
        if not self.search_history:
            return {"message": "검색 히스토리가 없습니다."}
        
        times = [h.get("search_time", 0) for h in self.search_history if "search_time" in h]
        
        return {
            "total_searches": len(self.search_history),
            "successful_searches": len([h for h in self.search_history if not h.get("error")]),
            "average_time": sum(times) / len(times) if times else 0,
            "fastest_search": min(times) if times else 0,
            "slowest_search": max(times) if times else 0,
            "total_results_found": sum(h.get("total_found", 0) for h in self.search_history)
        } 