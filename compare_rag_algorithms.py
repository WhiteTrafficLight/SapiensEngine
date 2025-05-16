#!/usr/bin/env python3
"""
RAG 알고리즘 비교 스크립트

다양한 RAG 검색 알고리즘의 결과를 비교합니다.
"""

import os
import sys
from sapiens_engine.core.rag_manager import RAGManager
from sapiens_engine.core.context_manager import ContextManager
import argparse
from tabulate import tabulate
from colorama import init, Fore, Style
import textwrap

# 컬러 출력 초기화
init()

def format_result(result, max_width=100):
    """검색 결과를 깔끔하게 포맷팅"""
    text = result['text']
    
    # 텍스트 줄바꿈
    wrapped_text = textwrap.fill(text, width=max_width)
    
    # 메타데이터 정보
    metadata = result.get('metadata', {})
    source = metadata.get('source', 'N/A')
    chunk_id = metadata.get('chunk_id', 'N/A')
    
    # 유사도 점수 (거리는 작을수록 유사, 유사도는 1-거리)
    similarity = 1 - result['distance']
    
    # 특수 플래그 확인
    is_neighbor = result.get('is_neighbor', False)
    is_window = result.get('is_window', False)
    is_merged = result.get('merged', False)
    
    # 상태 태그 생성
    tags = []
    if is_neighbor:
        tags.append("인접")
    if is_window:
        tags.append("윈도우")
    if is_merged:
        tags.append("병합")
    
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    
    # 결과 포맷팅
    formatted = (
        f"{Fore.CYAN}유사도: {similarity:.4f}{tag_str}{Style.RESET_ALL}\n"
        f"{Fore.YELLOW}출처: {source} (청크 ID: {chunk_id}){Style.RESET_ALL}\n"
        f"{Fore.WHITE}{wrapped_text}{Style.RESET_ALL}\n"
    )
    
    return formatted

def compare_rag_algorithms(query, collection_name=None, db_path="./vectordb", k=3):
    """다양한 RAG 알고리즘의 결과를 비교"""
    # RAG 관리자 초기화
    rag = RAGManager(db_path=db_path)
    
    # 컬렉션 목록 가져오기
    if collection_name is None:
        collections = rag.client.list_collections()
        if not collections:
            print(f"{Fore.RED}사용 가능한 컬렉션이 없습니다. 먼저 컨텍스트를 추가해주세요.{Style.RESET_ALL}")
            return
        collection_name = collections[0].name
        print(f"{Fore.GREEN}컬렉션 '{collection_name}'을 사용합니다.{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}쿼리: {query}{Style.RESET_ALL}\n")
    
    # 알고리즘 목록과 설명
    algorithms = [
        {"name": "simple_top_k", "func": rag.simple_top_k_search, "params": {"collection_name": collection_name, "query": query, "k": k}, "desc": "기본 Top-K 검색"},
        {"name": "threshold", "func": rag.threshold_search, "params": {"collection_name": collection_name, "query": query, "threshold": 0.6, "max_results": 10}, "desc": "임계값 기반 검색 (유사도 0.6 이상)"},
        {"name": "adjacent_chunks", "func": rag.adjacent_chunks_search, "params": {"collection_name": collection_name, "query": query, "k": k, "include_neighbors": True, "neighbor_threshold": 0.5}, "desc": "인접 청크 포함 검색"},
        {"name": "merged_chunks", "func": rag.merged_chunks_search, "params": {"collection_name": collection_name, "query": query, "k": k, "merge_threshold": 0.7}, "desc": "청크 병합 검색"},
        {"name": "semantic_window", "func": rag.semantic_window_search, "params": {"collection_name": collection_name, "query": query, "k": k, "window_size": 5, "window_threshold": 0.6}, "desc": "의미적 윈도우 검색"},
        {"name": "hybrid", "func": rag.hybrid_search, "params": {"collection_name": collection_name, "query": query, "k": k, "semantic_weight": 0.7}, "desc": "하이브리드 검색 (벡터 + 키워드)"},
        {"name": "mmr", "func": rag.mmr_search, "params": {"collection_name": collection_name, "query": query, "k": k, "lambda_param": 0.7, "initial_results": 20}, "desc": "MMR 검색 (다양성 고려)"}
    ]
    
    # 결과 비교 테이블
    comparison_table = []
    
    # 각 알고리즘 실행 및 결과 저장
    for algo in algorithms:
        print(f"\n{Fore.GREEN}=== {algo['desc']} ({algo['name']}) ==={Style.RESET_ALL}\n")
        
        try:
            results = algo["func"](**algo["params"])
            
            # 결과 수 및 평균 유사도 계산
            result_count = len(results)
            avg_similarity = sum(1 - r['distance'] for r in results) / max(1, result_count)
            
            # 비교 테이블에 추가
            comparison_table.append([
                algo["name"], 
                algo["desc"], 
                result_count, 
                f"{avg_similarity:.4f}"
            ])
            
            # 결과 출력
            for i, result in enumerate(results):
                print(f"{Fore.CYAN}[결과 {i+1}]{Style.RESET_ALL}\n{format_result(result)}\n{'-' * 80}")
                
        except Exception as e:
            print(f"{Fore.RED}오류 발생: {str(e)}{Style.RESET_ALL}")
            comparison_table.append([algo["name"], algo["desc"], 0, "오류"])
    
    # 비교 테이블 출력
    print(f"\n{Fore.GREEN}=== 알고리즘 비교 결과 ==={Style.RESET_ALL}\n")
    print(tabulate(comparison_table, headers=["알고리즘", "설명", "결과 수", "평균 유사도"], tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="RAG 알고리즘 비교 도구")
    parser.add_argument("--query", "-q", default="니체가 트랜스휴머니즘을 찬성하는 근거는 무엇인가?", help="검색 쿼리")
    parser.add_argument("--collection", "-c", help="컬렉션 이름")
    parser.add_argument("--db-path", "-d", default="./vectordb", help="벡터 DB 경로")
    parser.add_argument("--results", "-k", type=int, default=3, help="결과 수")
    
    args = parser.parse_args()
    
    compare_rag_algorithms(args.query, args.collection, args.db_path, args.results)

if __name__ == "__main__":
    main() 