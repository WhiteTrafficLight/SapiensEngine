#!/usr/bin/env python3
"""
쿼리 보강 알고리즘 테스트 스크립트

다양한 쿼리 보강 알고리즘을 테스트하고 결과를 비교합니다.
"""

import sys
from pathlib import Path
import json
from tabulate import tabulate
from colorama import init, Fore, Style
import argparse

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(Path(__file__).parent.parent.parent.absolute())))

# Import the QueryEnhancer
try:
    from sapiens_engine.core.query_enhancer import enhance_query
except ImportError:
    print("Warning: Sapiens engine core modules not found. Using direct imports.")
    from core.query_enhancer import enhance_query

# Initialize colorama
init()

def test_query_enhancement(
    query: str, 
    methods: list = None, 
    display_format: str = "table",
    save_results: bool = False,
    output_file: str = "query_enhancement_results.json"
):
    """
    쿼리 보강 알고리즘 테스트

    Args:
        query: 테스트할 쿼리
        methods: 테스트할 보강 방법 목록
        display_format: 결과 표시 형식 ('table', 'text')
        save_results: 결과 저장 여부
        output_file: 결과 저장 파일 경로
    """
    # 모든 방법이 지정되지 않은 경우 기본 메소드 목록 사용
    if methods is None:
        methods = [
            "paraphrasing", 
            "keyword_extraction", 
            "embedding_based", 
            "query_to_question", 
            "target_keyword", 
            "keyword_expansion", 
            "hybrid"
        ]
    
    print(f"{Fore.GREEN}쿼리 보강 알고리즘 테스트{Style.RESET_ALL}")
    print(f"{Fore.GREEN}원본 쿼리:{Style.RESET_ALL} {query}\n")
    
    # 결과 저장용 딕셔너리
    results = {
        "original_query": query,
        "enhanced_queries": {}
    }
    
    for method in methods:
        print(f"{Fore.CYAN}▶ {method.upper()} 보강 실행 중...{Style.RESET_ALL}")
        
        # 쿼리 보강 실행
        enhanced_queries = enhance_query(query, method=method)
        
        # 결과 저장
        results["enhanced_queries"][method] = enhanced_queries
        
        # 결과 표시
        if display_format == "table":
            rows = []
            for i, q in enumerate(enhanced_queries):
                is_original = i == 0
                rows.append([
                    i,
                    f"{Fore.YELLOW}(원본){Style.RESET_ALL}" if is_original else "",
                    q
                ])
            
            headers = ["번호", "구분", "보강된 쿼리"]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            print(f"\n{Fore.MAGENTA}{method.upper()} 결과:{Style.RESET_ALL}")
            for i, q in enumerate(enhanced_queries):
                print(f"{i}. {q}")
        
        print()
    
    # 결과 저장
    if save_results:
        # 결과에서 컬러 코드 제거
        clean_results = {
            "original_query": query,
            "enhanced_queries": {}
        }
        
        for method, queries in results["enhanced_queries"].items():
            clean_results["enhanced_queries"][method] = queries
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(clean_results, f, ensure_ascii=False, indent=2)
        
        print(f"{Fore.GREEN}테스트 결과가 {output_file}에 저장되었습니다.{Style.RESET_ALL}")
    
    return results

def main():
    """메인 함수"""
    # 명령행 인자 파싱
    parser = argparse.ArgumentParser(description='쿼리 보강 알고리즘 테스트')
    parser.add_argument('-q', '--query', type=str, 
                        help='테스트할 쿼리 (없으면 예시 쿼리 목록에서 선택)')
    parser.add_argument('-m', '--method', type=str, 
                        help='특정 보강 방법만 테스트 (콤마로 구분)')
    parser.add_argument('-f', '--format', type=str, choices=['table', 'text'], default='table',
                        help='결과 표시 형식 (table, text)')
    parser.add_argument('-s', '--save', action='store_true',
                        help='결과 JSON 파일로 저장')
    parser.add_argument('-o', '--output', type=str, default='query_enhancement_results.json',
                        help='결과 저장 파일 경로')
    
    args = parser.parse_args()
    
    # 예시 쿼리 목록
    example_queries = [
        "Transhumanism simplifies human existence into a technical problem",
        "Human beings are inherently imperfect and limited",
        "Transhumanism denies the essential imperfection of humans",
        "The concept of Übermensch denies human essence and threatens human existence",
        "Artificial intelligence will eventually surpass human intelligence"
    ]
    
    # 테스트할 쿼리 선택
    query = args.query
    if not query:
        print(f"{Fore.YELLOW}테스트할 쿼리를 선택하세요:{Style.RESET_ALL}")
        for i, q in enumerate(example_queries, 1):
            print(f"{i}. {q}")
        print(f"{len(example_queries) + 1}. 직접 입력")
        
        try:
            choice = int(input("\n선택 (번호 입력): "))
            
            if 1 <= choice <= len(example_queries):
                query = example_queries[choice - 1]
                print(f"\n선택한 쿼리: {query}")
            elif choice == len(example_queries) + 1:
                query = input("\n쿼리를 입력하세요: ")
            else:
                raise ValueError()
        except ValueError:
            print(f"{Fore.RED}올바른 선택이 아닙니다. 첫 번째 예시 쿼리를 사용합니다.{Style.RESET_ALL}")
            query = example_queries[0]
    
    # 테스트할 방법 선택
    methods = None
    if args.method:
        methods = [m.strip() for m in args.method.split(',')]
    
    # 쿼리 보강 테스트 실행
    test_query_enhancement(
        query=query,
        methods=methods,
        display_format=args.format,
        save_results=args.save,
        output_file=args.output
    )

if __name__ == "__main__":
    main() 