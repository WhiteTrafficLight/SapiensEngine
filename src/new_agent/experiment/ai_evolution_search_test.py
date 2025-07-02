#!/usr/bin/env python3
"""
AI 진화 주제 웹서치 성능 비교 테스트

"AI가 인간의 새로운 진화이다"라는 주제에 대해
Google API 직렬 검색 vs OpenAI 웹서치 툴 병렬 검색의 성능을 비교하는 실제 테스트
"""

import os
import sys
import time
import logging
import json
from datetime import datetime
from typing import Dict, Any

# 현재 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'websearch_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """메인 테스트 실행 함수"""
    
    print("🧬 AI 인간 진화 주제 웹서치 성능 비교 테스트")
    print("=" * 60)
    print("주제: AI가 인간의 새로운 진화이다")
    print("비교 대상: Google API 직렬 검색 vs OpenAI 웹서치 툴 병렬 검색")
    print("=" * 60)
    
    # 환경 변수 확인
    print("\n📋 환경 설정 확인:")
    
    google_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("SEARCH_API_KEY")
    google_cx = os.environ.get("GOOGLE_SEARCH_CX")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    print(f"   Google API Key: {'✅ 설정됨' if google_api_key else '❌ 없음'}")
    print(f"   Google CX:      {'✅ 설정됨' if google_cx else '❌ 없음'}")
    print(f"   OpenAI API Key: {'✅ 설정됨' if openai_api_key else '❌ 없음'}")
    
    if not google_api_key or not google_cx:
        print("\n⚠️  Warning: Google API 설정이 부족합니다.")
        print("   환경변수 설정: GOOGLE_API_KEY, GOOGLE_SEARCH_CX")
    
    if not openai_api_key:
        print("\n⚠️  Warning: OpenAI API 키가 설정되지 않았습니다.")
        print("   환경변수 설정: OPENAI_API_KEY")
    
    if not (google_api_key and google_cx and openai_api_key):
        print("\n❌ 필수 API 키가 설정되지 않았습니다. 테스트를 중단합니다.")
        return
    
    print("\n🚀 테스트 시작...")
    
    try:
        # 절대 import로 변경
        from performance_comparison import WebSearchPerformanceComparison
        
        # 성능 비교 도구 초기화
        comparator = WebSearchPerformanceComparison(
            google_api_key=google_api_key,
            google_cx=google_cx,
            openai_api_key=openai_api_key
        )
        
        # AI 진화 실험 실행
        print("\n🧬 AI 진화 주제 실험 실행 중...")
        
        start_time = time.time()
        
        result = comparator.run_ai_evolution_experiment(num_results=5)
        
        end_time = time.time()
        total_test_time = end_time - start_time
        
        print(f"\n✅ 테스트 완료! (총 소요시간: {total_test_time:.2f}초)")
        
        # 상세 결과 출력
        print_detailed_results(result)
        
        # 검색 결과 샘플 출력
        print_search_samples(result)
        
        # 결과를 JSON 파일로 저장
        filename = comparator.export_results_to_json()
        
        print(f"\n💾 결과 저장 완료: {filename}")
        
        # 최종 요약
        print_final_summary(result, total_test_time)
        
    except ImportError as e:
        logger.error(f"모듈 import 실패: {str(e)}")
        print(f"\n❌ 모듈 import 실패: {str(e)}")
        print("실행 중인 디렉토리가 올바른지 확인해주세요.")
        print(f"현재 디렉토리: {os.getcwd()}")
        print(f"스크립트 위치: {current_dir}")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {str(e)}")
        print(f"\n❌ 테스트 실행 중 오류: {str(e)}")

def print_detailed_results(result: Dict[str, Any]):
    """상세 결과 출력"""
    print("\n" + "="*70)
    print("📊 상세 성능 분석 결과")
    print("="*70)
    
    performance = result.get("performance_comparison", {})
    
    if performance:
        time_comp = performance.get("time_comparison", {})
        result_comp = performance.get("result_count_comparison", {})
        efficiency = performance.get("efficiency_metrics", {})
        
        print("⏱️  시간 성능 비교:")
        if time_comp:
            print(f"   Google 직렬 검색:     {time_comp.get('google_total_time', 0):.2f}초")
            print(f"   OpenAI 병렬 검색:     {time_comp.get('openai_total_time', 0):.2f}초")
            print(f"   시간 차이:           {time_comp.get('time_difference', 0):.2f}초")
            print(f"   속도 비율:           {time_comp.get('time_ratio', 0):.2f}배")
        
        print("\n📋 검색 결과 수 비교:")
        if result_comp:
            print(f"   Google 검색 결과:     {result_comp.get('google_total_results', 0)}개")
            print(f"   OpenAI 검색 결과:     {result_comp.get('openai_total_results', 0)}개")
            print(f"   결과 수 차이:        {result_comp.get('result_difference', 0)}개")
        
        print("\n⚡ 효율성 메트릭:")
        if efficiency:
            print(f"   Google 효율성:       {efficiency.get('google_results_per_second', 0):.2f} 결과/초")
            print(f"   OpenAI 효율성:       {efficiency.get('openai_results_per_second', 0):.2f} 결과/초")
            print(f"   OpenAI 병렬 효율:    {efficiency.get('openai_parallel_efficiency', 0):.2f}")
        
        winner = performance.get("winner")
        improvement = performance.get("improvement_percentage", 0)
        
        if winner:
            print(f"\n🏆 성능 우승자: {winner}")
            print(f"📈 성능 향상률: {improvement:.1f}%")

def print_search_samples(result: Dict[str, Any]):
    """검색 결과 샘플 출력"""
    print("\n" + "="*70)
    print("🔍 검색 결과 샘플")
    print("="*70)
    
    # Google 결과 샘플
    google_result = result.get("google_serial_result")
    if google_result and google_result.get("all_results"):
        print("\n🔍 Google API 검색 결과 샘플 (상위 3개):")
        for i, item in enumerate(google_result["all_results"][:3], 1):
            print(f"   {i}. {item.get('title', 'No title')}")
            print(f"      URL: {item.get('url', 'No URL')}")
            print(f"      요약: {item.get('snippet', 'No snippet')[:100]}...")
            print()
    
    # OpenAI 결과 샘플 - 원본 구조 표시
    openai_result = result.get("openai_parallel_result")
    if openai_result and openai_result.get("all_results"):
        print("🚀 OpenAI 웹서치 결과 샘플 (상위 2개 쿼리):")
        for i, search_result in enumerate(openai_result["all_results"][:2], 1):
            print(f"\n   [{i}] 쿼리: {search_result.get('query', 'Unknown')}")
            print(f"       출력 텍스트 (일부): {search_result.get('output_text', '')[:200]}...")
            
            # 원본 응답 구조 일부 표시
            raw_output = search_result.get('raw_openai_output', [])
            if raw_output:
                print(f"       원본 응답 항목 수: {len(raw_output)}개")
                for j, output_item in enumerate(raw_output[:2]):  # 처음 2개만 표시
                    item_type = output_item.get('type', 'unknown') if isinstance(output_item, dict) else 'unknown'
                    print(f"         - 항목 {j+1}: {item_type}")
            print()

def print_final_summary(result: Dict[str, Any], total_test_time: float):
    """최종 요약 출력"""
    print("\n" + "="*70)
    print("🎯 최종 테스트 요약")
    print("="*70)
    
    experiment_info = result.get("experiment_info", {})
    performance = result.get("performance_comparison", {})
    
    print(f"🧬 테스트 주제: AI 인간 진화")
    print(f"📅 실행 시간: {experiment_info.get('timestamp', 'Unknown')}")
    print(f"🔍 총 쿼리 수: {experiment_info.get('total_queries', 0)}개")
    print(f"⏱️  전체 테스트 시간: {total_test_time:.2f}초")
    
    # 성능 요약
    time_comp = performance.get("time_comparison", {})
    if time_comp:
        google_time = time_comp.get("google_total_time", 0)
        openai_time = time_comp.get("openai_total_time", 0)
        
        print(f"\n📊 성능 비교:")
        print(f"   Google 직렬: {google_time:.2f}초")
        print(f"   OpenAI 병렬: {openai_time:.2f}초")
        
        if openai_time < google_time:
            speedup = ((google_time - openai_time) / google_time) * 100
            print(f"   🚀 OpenAI가 {speedup:.1f}% 더 빠름")
        elif google_time < openai_time:
            speedup = ((openai_time - google_time) / openai_time) * 100
            print(f"   🔍 Google이 {speedup:.1f}% 더 빠름")
        else:
            print("   ⚖️  비슷한 성능")
    
    # 에러 정보
    error_info = result.get("error_info", {})
    if error_info:
        print(f"\n⚠️  오류 정보:")
        for key, error in error_info.items():
            print(f"   {key}: {error}")
    
    print("\n✅ 테스트 완료! 위 결과를 참고하여 웹서치 방법을 선택하세요.")
    print("="*70)

if __name__ == "__main__":
    main() 