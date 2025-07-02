"""
OpenAI 웹서치 툴을 이용한 병렬 웹서치 구현

새로운 OpenAI Responses API의 웹서치 기능을 사용하여 병렬 검색 구현
"""

import os
import time
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai

logger = logging.getLogger(__name__)

class OpenAIParallelSearcher:
    """
    OpenAI 웹서치 툴을 사용한 병렬 웹 검색기
    
    OpenAI Responses API의 web_search_preview 도구를 활용하여
    여러 쿼리를 동시에 병렬로 처리
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        OpenAI 병렬 검색기 초기화
        
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델 (기본: gpt-4o)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. OPENAI_API_KEY 환경변수를 설정해주세요.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.search_history = []
        
        logger.info(f"OpenAI Parallel Searcher 초기화 완료 (모델: {model})")
    
    async def search_single_query_async(self, query: str, context_size: str = "low") -> Dict[str, Any]:
        """
        단일 쿼리 비동기 검색
        
        Args:
            query: 검색 쿼리
            context_size: 검색 컨텍스트 크기 ("low", "medium", "high")
            
        Returns:
            검색 결과 딕셔너리
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 OpenAI 웹서치 시작: '{query}'")
            
            # OpenAI Responses API 호출
            response = await asyncio.to_thread(
                self.client.responses.create,
                model=self.model,
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": context_size
                }],
                input=query
            )
            
            # 원본 응답을 그대로 저장 - 변환하지 않음
            raw_output = []
            output_text = ""
            
            if hasattr(response, 'output') and response.output:
                # 원본 output을 그대로 저장
                for output_item in response.output:
                    if hasattr(output_item, 'model_dump'):
                        raw_output.append(output_item.model_dump())
                    elif hasattr(output_item, '__dict__'):
                        raw_output.append(output_item.__dict__)
                    else:
                        raw_output.append(str(output_item))
            
            # output_text 추출 (편의를 위해)
            if hasattr(response, 'output_text'):
                output_text = response.output_text
            
            end_time = time.time()
            search_time = end_time - start_time
            
            # 원본 응답 구조 그대로 반환
            search_result = {
                "query": query,
                "raw_openai_output": raw_output,  # 원본 output 그대로
                "output_text": output_text,       # 텍스트만 따로 (편의용)
                "search_time": search_time,
                "timestamp": datetime.now().isoformat(),
                "source": "openai_web_search_raw",
                "context_size": context_size,
                "model": self.model
            }
            
            self.search_history.append(search_result)
            
            logger.info(f"✅ OpenAI 웹서치 완료: 원본 응답 저장 ({search_time:.2f}초)")
            
            return search_result
            
        except Exception as e:
            end_time = time.time()
            search_time = end_time - start_time
            
            logger.error(f"❌ OpenAI 웹서치 실패: {str(e)}")
            
            error_result = {
                "query": query,
                "raw_openai_output": [],
                "output_text": "",
                "search_time": search_time,
                "timestamp": datetime.now().isoformat(),
                "source": "openai_web_search_raw",
                "context_size": context_size,
                "model": self.model,
                "error": str(e)
            }
            
            self.search_history.append(error_result)
            return error_result
    
    async def search_multiple_queries_parallel(self, queries: List[str], context_size: str = "low") -> Dict[str, Any]:
        """
        여러 쿼리를 병렬로 검색 (새로운 방식)
        
        Args:
            queries: 검색 쿼리 리스트
            context_size: 검색 컨텍스트 크기
            
        Returns:
            전체 검색 결과 딕셔너리
        """
        overall_start_time = time.time()
        
        logger.info(f"🔥 OpenAI 병렬 웹서치 시작: {len(queries)}개 쿼리")
        
        # 모든 쿼리를 비동기 태스크로 생성
        tasks = []
        for i, query in enumerate(queries, 1):
            logger.info(f"  [{i}/{len(queries)}] 태스크 생성: '{query}'")
            task = self.search_single_query_async(query, context_size)
            tasks.append(task)
        
        # 모든 태스크를 병렬로 실행
        logger.info(f"⚡ {len(tasks)}개 검색 태스크 병렬 실행 중...")
        
        try:
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"병렬 검색 실행 중 오류: {str(e)}")
            all_results = []
        
        overall_end_time = time.time()
        total_time = overall_end_time - overall_start_time
        
        # 결과 정리
        successful_results = []
        individual_times = []
        
        for i, result in enumerate(all_results):
            if isinstance(result, Exception):
                logger.error(f"쿼리 {i+1} 실행 중 예외: {str(result)}")
                error_result = {
                    "query": queries[i] if i < len(queries) else f"query_{i}",
                    "raw_openai_output": [],
                    "output_text": "",
                    "search_time": 0,
                    "timestamp": datetime.now().isoformat(),
                    "source": "openai_web_search_raw",
                    "context_size": context_size,
                    "model": self.model,
                    "error": str(result)
                }
                successful_results.append(error_result)
                individual_times.append(0)
            else:
                successful_results.append(result)
                individual_times.append(result.get("search_time", 0))
        
        # 결과 통합
        all_search_results = []
        total_found = 0
        
        for result in successful_results:
            # 원본 응답을 그대로 유지
            all_search_results.append(result)
            total_found += len(result.get("raw_openai_output", []))
        
        final_result = {
            "method": "openai_web_search_parallel",
            "queries": queries,
            "total_queries": len(queries),
            "all_results": all_search_results,  # 개별 검색 결과들을 그대로 저장
            "total_found": total_found,
            "individual_results": successful_results,
            "individual_times": individual_times,
            "total_time": total_time,
            "average_time_per_query": total_time / len(queries) if queries else 0,
            "timestamp": datetime.now().isoformat(),
            "context_size": context_size,
            "model": self.model,
            "performance_stats": {
                "fastest_query": min(individual_times) if individual_times else 0,
                "slowest_query": max(individual_times) if individual_times else 0,
                "total_requests": len(queries),
                "successful_requests": len([r for r in successful_results if not r.get("error")]),
                "parallel_efficiency": (sum(individual_times) / total_time) if total_time > 0 else 0  # 병렬 효율성
            }
        }
        
        logger.info(f"🏁 OpenAI 병렬 웹서치 완료:")
        logger.info(f"   📊 총 {len(queries)}개 쿼리, {total_found}개 결과")
        logger.info(f"   ⏱️  총 소요시간: {total_time:.2f}초")
        logger.info(f"   📈 쿼리당 평균: {final_result['average_time_per_query']:.2f}초")
        logger.info(f"   🚀 병렬 효율성: {final_result['performance_stats']['parallel_efficiency']:.2f}")
        
        return final_result
    
    def search_multiple_queries_parallel_sync(self, queries: List[str], context_size: str = "low") -> Dict[str, Any]:
        """
        동기적 래퍼 함수 - 병렬 검색을 동기 함수에서 호출
        
        Args:
            queries: 검색 쿼리 리스트
            context_size: 검색 컨텍스트 크기
            
        Returns:
            전체 검색 결과 딕셔너리
        """
        try:
            # 새로운 이벤트 루프 생성하여 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.search_multiple_queries_parallel(queries, context_size)
                )
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"동기 래퍼에서 오류 발생: {str(e)}")
            return {
                "method": "openai_web_search_parallel",
                "queries": queries,
                "total_queries": len(queries),
                "all_results": [],
                "total_found": 0,
                "individual_results": [],
                "individual_times": [],
                "total_time": 0,
                "average_time_per_query": 0,
                "timestamp": datetime.now().isoformat(),
                "context_size": context_size,
                "model": self.model,
                "error": str(e)
            }
    
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