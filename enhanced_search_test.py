#!/usr/bin/env python3
"""
쿼리 보강 검색 효과 테스트 스크립트

쿼리 보강 기법을 적용한 후 검색 결과의 유사도 변화를 비교 분석합니다.
"""

import sys
import json
from pathlib import Path
import argparse
from tabulate import tabulate
from colorama import init, Fore, Style
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Import required modules
from sapiens_engine.core.rag_manager import RAGManager
from sapiens_engine.core.query_enhancer import enhance_query

# Initialize colorama
init()

def run_search_test(
    query: str,
    enhancement_method: str = "hybrid",
    search_method: str = "semantic",
    k: int = 3,
    threshold: float = 0.3,
    save_results: bool = True,
    output_file: str = None,
):
    """
    쿼리 보강 후 검색을 수행하고 결과의 유사도를 비교 분석합니다.
    
    Args:
        query: 원본 쿼리
        enhancement_method: 쿼리 보강 방식
        search_method: 검색 방식
        k: 상위 k개 결과 검색
        threshold: 유사도 임계값
        save_results: 결과 저장 여부
        output_file: 저장할 파일 이름
    """
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== 쿼리 보강 및 검색 테스트 ==={Style.RESET_ALL}")
    print(f"원본 쿼리: {Style.BRIGHT}{query}{Style.RESET_ALL}")
    print(f"보강 방식: {enhancement_method}, 검색 방식: {search_method}, Top-k: {k}, 임계값: {threshold}\n")
    
    # 쿼리 보강
    print(f"{Fore.YELLOW}▶ 쿼리 보강 중...{Style.RESET_ALL}")
    enhanced_queries = enhance_query(query, method=enhancement_method)
    
    print(f"총 {len(enhanced_queries)} 개의 쿼리 생성됨:\n")
    for i, q in enumerate(enhanced_queries):
        if i == 0:
            print(f"{i}: {Fore.GREEN}(원본) {q}{Style.RESET_ALL}")
        else:
            print(f"{i}: {q}")
    
    # RAG 매니저 초기화
    rag_manager = RAGManager(db_path="./vectordb")
    
    # 결과 저장 컨테이너
    search_results = {
        "original_query": query,
        "enhancement_method": enhancement_method,
        "search_method": search_method,
        "timestamp": datetime.now().isoformat(),
        "results": []
    }
    
    # 각 쿼리로 검색 수행
    all_scores = []
    all_labels = []
    
    for i, enhanced_query in enumerate(enhanced_queries):
        print(f"\n{Fore.BLUE}▶ 쿼리 {i}{' (원본)' if i == 0 else ''} 검색 중...{Style.RESET_ALL}")
        print(f"쿼리: {enhanced_query}")
        
        # 검색 수행
        try:
            # 컬렉션 확인
            available_collections = rag_manager.client.list_collections()
            if not available_collections:
                print(f"{Fore.RED}사용 가능한 컬렉션이 없습니다.{Style.RESET_ALL}")
                return search_results
                
            collection_name = available_collections[0].name
            print(f"컬렉션 {collection_name}에서 검색합니다.")
            
            if search_method == "basic":
                results = rag_manager.simple_top_k_search(collection_name, enhanced_query, k=k)
            elif search_method == "semantic":
                results = rag_manager.semantic_window_search(collection_name, enhanced_query, k=k)
            elif search_method == "threshold":
                results = rag_manager.threshold_search(collection_name, enhanced_query, threshold=threshold, max_results=k)
            elif search_method == "window":
                results = rag_manager.semantic_window_search(collection_name, enhanced_query, k=k, window_size=5)
            elif search_method == "hybrid":
                results = rag_manager.hybrid_search(collection_name, enhanced_query, k=k)
            elif search_method == "mmr":
                results = rag_manager.mmr_search(collection_name, enhanced_query, k=k, lambda_param=0.7)
            elif search_method == "merged":
                results = rag_manager.merged_chunks_search(collection_name, enhanced_query, k=k)
            else:
                results = rag_manager.simple_top_k_search(collection_name, enhanced_query, k=k)
        except Exception as e:
            print(f"{Fore.RED}검색 중 오류 발생: {str(e)}{Style.RESET_ALL}")
            results = []
        
        # 결과에서 유사도 점수 추출
        scores = []
        for result in results:
            # 거리를 유사도로 변환 (1 - 거리)
            distance = result.get("distance", 0)
            score = 1.0 - distance if 0 <= distance <= 1 else 0
            scores.append(score)
            print(f"  {Fore.CYAN}[유사도: {score:.4f}]{Style.RESET_ALL} {result.get('text', '')[:150]}...")
            
            # 디버깅을 위한 추가 정보 출력
            if "distance" in result:
                print(f"    - 원본 거리: {distance:.6f}")
            else:
                print(f"    - 거리 정보 없음")
        
        # 평균 유사도 계산
        avg_score = sum(scores) / len(scores) if scores else 0
        print(f"{Fore.YELLOW}  평균 유사도: {avg_score:.4f}{Style.RESET_ALL}")
        
        # 결과 저장
        query_result = {
            "query": enhanced_query,
            "is_original": i == 0,
            "results": results,
            "scores": scores,
            "avg_score": avg_score
        }
        search_results["results"].append(query_result)
        
        # 시각화용 데이터 저장
        all_scores.append(avg_score)
        all_labels.append("원본" if i == 0 else f"강화 {i}")
    
    # 유사도 비교 테이블 출력
    print(f"\n{Style.BRIGHT}{Fore.CYAN}=== 유사도 비교 결과 ==={Style.RESET_ALL}")
    table_data = []
    for i, result in enumerate(search_results["results"]):
        label = "원본" if i == 0 else f"강화 {i}"
        query_text = result["query"]
        avg_score = result["avg_score"]
        improvement = "-" if i == 0 else f"{(avg_score - search_results['results'][0]['avg_score']) * 100:.2f}%"
        
        table_data.append([label, query_text[:50] + "..." if len(query_text) > 50 else query_text, f"{avg_score:.4f}", improvement])
    
    print(tabulate(table_data, headers=["쿼리", "내용", "평균 유사도", "향상도"], tablefmt="grid"))
    
    # 결과 저장
    if save_results:
        if output_file is None:
            output_file = f"enhanced_search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n검색 결과가 {output_file}에 저장되었습니다.")
    
    # 시각화
    try:
        plt.figure(figsize=(10, 6))
        bars = plt.bar(all_labels, all_scores, color=['green'] + ['skyblue'] * (len(all_scores) - 1))
        plt.axhline(y=all_scores[0], color='red', linestyle='--', alpha=0.5, label='원본 유사도')
        
        # 바 위에 값 표시
        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.4f}',
                    ha='center', va='bottom', fontsize=9)
        
        plt.xlabel('쿼리')
        plt.ylabel('평균 유사도')
        plt.title(f'쿼리 보강 방식({enhancement_method})에 따른 유사도 변화')
        plt.ylim(0, max(all_scores) * 1.2)
        plt.tight_layout()
        
        # 그래프 저장
        plt.savefig(f"similarity_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        print(f"유사도 비교 그래프가 저장되었습니다.")
        
    except Exception as e:
        print(f"그래프 생성 중 오류 발생: {str(e)}")
    
    return search_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='쿼리 보강 및 검색 테스트')
    parser.add_argument('-q', '--query', type=str, default="Transhumanism simplifies human existence into a technical problem",
                        help='원본 쿼리')
    parser.add_argument('-m', '--enhancement_method', type=str, default="hybrid",
                        choices=["paraphrasing", "keyword_extraction", "embedding_based", 
                                "query_to_question", "target_keyword", "keyword_expansion", "hybrid"],
                        help='쿼리 보강 방식')
    parser.add_argument('-s', '--search_method', type=str, default="semantic",
                        choices=["basic", "semantic", "threshold", "window", "hybrid", "mmr", "merged"],
                        help='검색 방식 (basic=단순검색, semantic=의미검색, threshold=임계값, window=윈도우검색, hybrid=하이브리드, mmr=다양성보존, merged=청크병합)')
    parser.add_argument('-k', '--top_k', type=int, default=3,
                        help='검색 결과 개수')
    parser.add_argument('-t', '--threshold', type=float, default=0.3,
                        help='유사도 임계값')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='결과 저장 파일명')
    
    args = parser.parse_args()
    
    run_search_test(
        query=args.query,
        enhancement_method=args.enhancement_method,
        search_method=args.search_method,
        k=args.top_k,
        threshold=args.threshold,
        save_results=True,
        output_file=args.output
    ) 