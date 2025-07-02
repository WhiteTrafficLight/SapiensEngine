"""
웹서치 성능 비교 모듈

Google API 직렬 검색 vs OpenAI 웹서치 툴 병렬 검색 성능 비교
"""

import time
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# 절대 import로 변경
from google_serial_search import GoogleSerialSearcher
from openai_parallel_search import OpenAIParallelSearcher

logger = logging.getLogger(__name__)

class WebSearchPerformanceComparison:
    """
    웹서치 성능 비교 클래스
    
    두 가지 웹서치 방법의 성능을 비교하고 분석 결과를 제공
    """
    
    def __init__(self, google_api_key: Optional[str] = None, google_cx: Optional[str] = None,
                 openai_api_key: Optional[str] = None):
        """
        성능 비교 도구 초기화
        
        Args:
            google_api_key: Google API 키
            google_cx: Google Custom Search CX
            openai_api_key: OpenAI API 키
        """
        self.google_searcher = None
        self.openai_searcher = None
        self.comparison_results = []
        
        # Google 검색기 초기화
        try:
            self.google_searcher = GoogleSerialSearcher(
                api_key=google_api_key, 
                cx=google_cx
            )
            logger.info("✅ Google Serial Searcher 준비 완료")
        except Exception as e:
            logger.warning(f"⚠️  Google Serial Searcher 초기화 실패: {str(e)}")
        
        # OpenAI 검색기 초기화
        try:
            self.openai_searcher = OpenAIParallelSearcher(api_key=openai_api_key)
            logger.info("✅ OpenAI Parallel Searcher 준비 완료")
        except Exception as e:
            logger.warning(f"⚠️  OpenAI Parallel Searcher 초기화 실패: {str(e)}")
    
    def run_ai_evolution_experiment(self, num_results: int = 5) -> Dict[str, Any]:
        """
        "AI가 인간의 새로운 진화이다" 주제에 대한 성능 비교 실험
        
        Args:
            num_results: 각 쿼리당 검색 결과 수
            
        Returns:
            비교 결과 딕셔너리
        """
        # AI 진화 관련 영어 쿼리 3개
        ai_evolution_queries = [
            "AI artificial intelligence human evolution next step technological enhancement",
            "machine learning augmented human capabilities cognitive enhancement future evolution",
            "artificial intelligence symbiosis human development evolutionary leap biological technology"
        ]
        
        logger.info("🧬 AI 인간 진화 주제 웹서치 성능 비교 실험 시작")
        logger.info(f"📋 테스트 쿼리 {len(ai_evolution_queries)}개:")
        for i, query in enumerate(ai_evolution_queries, 1):
            logger.info(f"   {i}. {query}")
        
        return self.compare_search_methods(ai_evolution_queries, num_results)
    
    def compare_search_methods(self, queries: List[str], num_results: int = 5) -> Dict[str, Any]:
        """
        두 검색 방법의 성능 비교
        
        Args:
            queries: 검색 쿼리 리스트
            num_results: 각 쿼리당 검색 결과 수
            
        Returns:
            비교 결과 딕셔너리
        """
        comparison_start_time = time.time()
        
        logger.info(f"🔬 웹서치 성능 비교 시작 ({len(queries)}개 쿼리)")
        
        # 결과 저장 딕셔너리
        comparison_result = {
            "experiment_info": {
                "queries": queries,
                "num_results_per_query": num_results,
                "timestamp": datetime.now().isoformat(),
                "total_queries": len(queries)
            },
            "google_serial_result": None,
            "openai_parallel_result": None,
            "performance_comparison": {},
            "error_info": {}
        }
        
        # 1. Google API 직렬 검색 실행
        if self.google_searcher:
            logger.info("🔍 Google API 직렬 검색 실행 중...")
            try:
                google_result = self.google_searcher.search_multiple_queries_serial(
                    queries, num_results
                )
                comparison_result["google_serial_result"] = google_result
                
                logger.info(f"✅ Google 직렬 검색 완료:")
                logger.info(f"   ⏱️  소요시간: {google_result.get('total_time', 0):.2f}초")
                logger.info(f"   📊 총 결과: {google_result.get('total_found', 0)}개")
                
            except Exception as e:
                logger.error(f"❌ Google 직렬 검색 실패: {str(e)}")
                comparison_result["error_info"]["google_error"] = str(e)
        else:
            logger.warning("⚠️  Google 검색기가 초기화되지 않았습니다.")
            comparison_result["error_info"]["google_error"] = "Google 검색기 초기화 실패"
        
        # 2. OpenAI 병렬 검색 실행
        if self.openai_searcher:
            logger.info("🚀 OpenAI 병렬 검색 실행 중...")
            try:
                openai_result = self.openai_searcher.search_multiple_queries_parallel_sync(
                    queries, context_size="low"
                )
                comparison_result["openai_parallel_result"] = openai_result
                
                logger.info(f"✅ OpenAI 병렬 검색 완료:")
                logger.info(f"   ⏱️  소요시간: {openai_result.get('total_time', 0):.2f}초")
                logger.info(f"   📊 총 결과: {openai_result.get('total_found', 0)}개")
                logger.info(f"   🚀 병렬 효율성: {openai_result.get('performance_stats', {}).get('parallel_efficiency', 0):.2f}")
                
            except Exception as e:
                logger.error(f"❌ OpenAI 병렬 검색 실패: {str(e)}")
                comparison_result["error_info"]["openai_error"] = str(e)
        else:
            logger.warning("⚠️  OpenAI 검색기가 초기화되지 않았습니다.")
            comparison_result["error_info"]["openai_error"] = "OpenAI 검색기 초기화 실패"
        
        # 3. 성능 비교 분석
        comparison_result["performance_comparison"] = self._analyze_performance(
            comparison_result["google_serial_result"],
            comparison_result["openai_parallel_result"]
        )
        
        comparison_end_time = time.time()
        comparison_result["total_experiment_time"] = comparison_end_time - comparison_start_time
        
        # 결과 히스토리에 추가
        self.comparison_results.append(comparison_result)
        
        # 결과 요약 출력
        self._print_comparison_summary(comparison_result)
        
        return comparison_result
    
    def _analyze_performance(self, google_result: Optional[Dict], openai_result: Optional[Dict]) -> Dict[str, Any]:
        """
        두 검색 결과의 성능 분석
        
        Args:
            google_result: Google 검색 결과
            openai_result: OpenAI 검색 결과
            
        Returns:
            성능 분석 결과
        """
        analysis = {
            "time_comparison": {},
            "result_count_comparison": {},
            "efficiency_metrics": {},
            "winner": None,
            "improvement_percentage": 0
        }
        
        if google_result and openai_result:
            google_time = google_result.get("total_time", 0)
            openai_time = openai_result.get("total_time", 0)
            
            google_count = google_result.get("total_found", 0)
            openai_count = len(openai_result.get("all_results", []))  # 쿼리 개수
            
            # 시간 비교
            analysis["time_comparison"] = {
                "google_total_time": google_time,
                "openai_total_time": openai_time,
                "time_difference": google_time - openai_time,
                "time_ratio": google_time / openai_time if openai_time > 0 else float('inf')
            }
            
            # 결과 수 비교
            analysis["result_count_comparison"] = {
                "google_total_results": google_count,
                "openai_total_results": openai_count,
                "result_difference": openai_count - google_count
            }
            
            # 효율성 메트릭
            analysis["efficiency_metrics"] = {
                "google_results_per_second": google_count / google_time if google_time > 0 else 0,
                "openai_results_per_second": openai_count / openai_time if openai_time > 0 else 0,
                "openai_parallel_efficiency": openai_result.get("performance_stats", {}).get("parallel_efficiency", 0)
            }
            
            # 승자 결정 (속도 기준)
            if openai_time < google_time:
                analysis["winner"] = "OpenAI Parallel"
                analysis["improvement_percentage"] = ((google_time - openai_time) / google_time) * 100 if google_time > 0 else 0
            else:
                analysis["winner"] = "Google Serial"
                analysis["improvement_percentage"] = ((openai_time - google_time) / openai_time) * 100 if openai_time > 0 else 0
        
        return analysis
    
    def _print_comparison_summary(self, result: Dict[str, Any]):
        """비교 결과 요약 출력"""
        logger.info("\n" + "="*70)
        logger.info("🏆 웹서치 성능 비교 결과 요약")
        logger.info("="*70)
        
        performance = result.get("performance_comparison", {})
        time_comp = performance.get("time_comparison", {})
        result_comp = performance.get("result_count_comparison", {})
        efficiency = performance.get("efficiency_metrics", {})
        
        if time_comp:
            logger.info(f"📊 시간 성능:")
            logger.info(f"   🔍 Google 직렬:    {time_comp.get('google_total_time', 0):.2f}초")
            logger.info(f"   🚀 OpenAI 병렬:    {time_comp.get('openai_total_time', 0):.2f}초")
            logger.info(f"   ⚡ 시간 차이:      {time_comp.get('time_difference', 0):.2f}초")
            logger.info(f"   📈 속도 비율:      {time_comp.get('time_ratio', 0):.2f}배")
        
        if result_comp:
            logger.info(f"\n📋 결과 수:")
            logger.info(f"   🔍 Google 결과:    {result_comp.get('google_total_results', 0)}개")
            logger.info(f"   🚀 OpenAI 결과:    {result_comp.get('openai_total_results', 0)}개")
        
        if efficiency:
            logger.info(f"\n⚡ 효율성:")
            logger.info(f"   🔍 Google 효율:    {efficiency.get('google_results_per_second', 0):.2f} 결과/초")
            logger.info(f"   🚀 OpenAI 효율:    {efficiency.get('openai_results_per_second', 0):.2f} 결과/초")
            logger.info(f"   🎯 병렬 효율성:    {efficiency.get('openai_parallel_efficiency', 0):.2f}")
        
        winner = performance.get("winner")
        improvement = performance.get("improvement_percentage", 0)
        
        if winner:
            logger.info(f"\n🏆 승자: {winner}")
            logger.info(f"📈 성능 향상: {improvement:.1f}%")
        
        logger.info("="*70 + "\n")
    
    def export_results_to_json(self, filename: Optional[str] = None) -> str:
        """결과를 JSON 파일로 내보내기"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"websearch_comparison_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 결과가 {filename}에 저장되었습니다.")
        return filename
    
    def get_detailed_results(self, result_index: int = -1) -> Dict[str, Any]:
        """상세 결과 반환 (기본적으로 최신 결과)"""
        if not self.comparison_results:
            return {"error": "비교 결과가 없습니다."}
        
        result = self.comparison_results[result_index]
        
        detailed = {
            "experiment_summary": result.get("experiment_info", {}),
            "performance_metrics": result.get("performance_comparison", {}),
            "google_detailed_results": self._extract_search_details(result.get("google_serial_result")),
            "openai_detailed_results": self._extract_search_details(result.get("openai_parallel_result")),
            "sample_search_results": self._extract_sample_results(result)
        }
        
        return detailed
    
    def _extract_search_details(self, search_result: Optional[Dict]) -> Dict[str, Any]:
        """검색 결과에서 세부 정보 추출"""
        if not search_result:
            return {"error": "검색 결과 없음"}
        
        return {
            "method": search_result.get("method", "unknown"),
            "total_time": search_result.get("total_time", 0),
            "total_found": search_result.get("total_found", 0),
            "average_time_per_query": search_result.get("average_time_per_query", 0),
            "individual_times": search_result.get("individual_times", []),
            "performance_stats": search_result.get("performance_stats", {}),
            "successful_queries": len([r for r in search_result.get("individual_results", []) if not r.get("error")])
        }
    
    def _extract_sample_results(self, comparison_result: Dict) -> Dict[str, Any]:
        """각 방법의 샘플 검색 결과 추출"""
        samples = {
            "google_samples": [],
            "openai_samples": []
        }
        
        # Google 샘플
        google_result = comparison_result.get("google_serial_result")
        if google_result and google_result.get("all_results"):
            samples["google_samples"] = google_result["all_results"][:3]  # 처음 3개
        
        # OpenAI 샘플 - 원본 구조 그대로
        openai_result = comparison_result.get("openai_parallel_result")
        if openai_result and openai_result.get("all_results"):
            # all_results가 이제 개별 검색 결과들의 배열
            samples["openai_samples"] = openai_result["all_results"][:3]  # 처음 3개 검색 결과
        
        return samples 