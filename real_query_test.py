#!/usr/bin/env python3
"""
실제 PDF 데이터를 이용한 RAG 검색 테스트

PDF에서 추출한 실제 벡터 데이터를 이용해 RAG 검색을 수행합니다.
필요시 쿼리 보강 알고리즘을 적용하여 검색 성능을 개선합니다.
"""

import sys
from pathlib import Path
import json
from tabulate import tabulate
from colorama import init, Fore, Style
import chromadb

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Import the RAG manager
try:
    from sapiens_engine.core.rag_manager import RAGManager
    from sapiens_engine.core.query_enhancer import enhance_query
except ImportError:
    print("Warning: Sapiens engine core modules not found. Using direct imports.")
    from core.rag_manager import RAGManager
    try:
        from core.query_enhancer import enhance_query
    except ImportError:
        print("Warning: Query enhancer module not found. Query enhancement will be disabled.")
        enhance_query = None

# Initialize colorama
init()

def get_available_collections(db_path="./vectordb"):
    """
    벡터 DB에 저장된 컬렉션 목록 조회
    
    Args:
        db_path: 벡터 DB 경로
        
    Returns:
        컬렉션 이름 목록
    """
    client = chromadb.PersistentClient(path=db_path)
    return [collection.name for collection in client.list_collections()]

def search_with_real_query(query, collection_name="pdf_cc54f541", num_results=5, use_query_enhancement=False, enhancement_method="hybrid"):
    """
    실제 쿼리로 RAG 검색 수행
    
    Args:
        query: 검색 쿼리 문자열
        collection_name: 사용할 컬렉션 이름 (기본값: pdf_cc54f541)
        num_results: 반환할 결과 개수
        use_query_enhancement: 쿼리 보강 사용 여부
        enhancement_method: 쿼리 보강 방법
        
    Returns:
        검색 결과 목록
    """
    # RAG 매니저 초기화
    rag_manager = RAGManager(db_path="./vectordb")
    
    print(f"{Fore.GREEN}원본 쿼리:{Style.RESET_ALL} {query}")
    print(f"{Fore.GREEN}컬렉션:{Style.RESET_ALL} {collection_name}")
    
    # 쿼리 보강 적용
    enhanced_queries = [query]  # 기본값은 원본 쿼리만 사용
    
    if use_query_enhancement and enhance_query:
        print(f"{Fore.GREEN}쿼리 보강 방법:{Style.RESET_ALL} {enhancement_method}")
        try:
            # enhancement_method가 "all"인 경우 모든 방법 사용
            if enhancement_method == "all":
                enhancement_methods = [
                    "paraphrasing", 
                    "keyword_extraction", 
                    "embedding_based", 
                    "query_to_question", 
                    "target_keyword", 
                    "keyword_expansion", 
                    "hybrid"
                ]
                enhanced_queries = [query]  # 원본 쿼리는 항상 포함
                print(f"{Fore.YELLOW}모든 보강 방법을 사용합니다:{Style.RESET_ALL}")
                
                for method in enhancement_methods:
                    print(f"\n{Fore.CYAN}방법: {method}{Style.RESET_ALL}")
                    method_queries = enhance_query(query, method=method)
                    # 첫 번째는 원본 쿼리이므로 제외
                    if len(method_queries) > 1:
                        for i, eq in enumerate(method_queries[1:], 1):
                            print(f"  {len(enhanced_queries)}. [{method}] {eq}")
                            enhanced_queries.append(eq)
            # enhancement_method가 쉼표로 구분된 여러 방법인 경우
            elif "," in enhancement_method:
                methods_list = [m.strip() for m in enhancement_method.split(",")]
                enhanced_queries = [query]  # 원본 쿼리는 항상 포함
                print(f"{Fore.YELLOW}선택한 보강 방법들을 사용합니다:{Style.RESET_ALL}")
                
                for method in methods_list:
                    print(f"\n{Fore.CYAN}방법: {method}{Style.RESET_ALL}")
                    method_queries = enhance_query(query, method=method)
                    # 첫 번째는 원본 쿼리이므로 제외
                    if len(method_queries) > 1:
                        for i, eq in enumerate(method_queries[1:], 1):
                            print(f"  {len(enhanced_queries)}. [{method}] {eq}")
                            enhanced_queries.append(eq)
            # 단일 방법인 경우 (기존 코드)
            else:
                enhanced_queries = enhance_query(query, method=enhancement_method)
                print(f"{Fore.YELLOW}보강된 쿼리 목록:{Style.RESET_ALL}")
                for i, eq in enumerate(enhanced_queries):
                    is_original = i == 0
                    marker = "(원본)" if is_original else ""
                    print(f"  {i}. {marker} {eq}")
        except Exception as e:
            print(f"{Fore.RED}쿼리 보강 실패: {str(e)}{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}검색 알고리즘: 각 알고리즘별 검색 결과 비교{Style.RESET_ALL}\n")
    
    # 다양한 검색 알고리즘으로 검색 실행
    results = {}
    
    # 각 알고리즘에 대해 원본 쿼리와 보강된 쿼리 모두 검색
    for algorithm, algo_name in [
        ("basic_top_k", "기본 Top-K 검색"),
        ("semantic_window", "의미적 윈도우 검색"),
        ("threshold", "임계값 검색"),
        ("merged_chunks", "청크 병합 검색"),
        ("hybrid", "하이브리드 검색"),
        ("mmr", "다양성 보존 검색(MMR)")
    ]:
        print(f"{Fore.CYAN}{algorithm} 실행 중...{Style.RESET_ALL}")
        
        # 각 알고리즘별 결과 초기화
        algorithm_results = []
        
        # 원본 쿼리와 보강된 쿼리로 검색
        for idx, enhanced_query in enumerate(enhanced_queries):
            # 쿼리 보강을 사용하지 않거나 첫 번째(원본) 쿼리만 처리할 경우
            if not use_query_enhancement and idx > 0:
                continue
                
            query_marker = "" if idx == 0 else f" (보강 쿼리 #{idx})"
            print(f"  - 쿼리 실행 중{query_marker}: {enhanced_query}")
            
            # 알고리즘별 검색 실행
            try:
                if algorithm == "basic_top_k":
                    search_results = rag_manager.simple_top_k_search(collection_name, enhanced_query, k=num_results)
                elif algorithm == "semantic_window":
                    search_results = rag_manager.semantic_window_search(collection_name, enhanced_query, k=num_results)
                elif algorithm == "threshold":
                    search_results = rag_manager.threshold_search(collection_name, enhanced_query, threshold=0.7, max_results=num_results)
                elif algorithm == "merged_chunks":
                    search_results = rag_manager.merged_chunks_search(collection_name, enhanced_query, k=num_results)
                elif algorithm == "hybrid":
                    search_results = rag_manager.hybrid_search(collection_name, enhanced_query, k=num_results)
                elif algorithm == "mmr":
                    search_results = rag_manager.mmr_search(collection_name, enhanced_query, k=num_results)
                
                # 결과에 사용된 쿼리 정보 추가
                for result in search_results:
                    result['query_used'] = enhanced_query
                    result['is_enhanced'] = idx > 0
                    algorithm_results.append(result)
            except Exception as e:
                print(f"    {Fore.RED}오류 발생: {str(e)}{Style.RESET_ALL}")
        
        # 결과 저장
        results[algorithm] = algorithm_results
    
    return results

def print_results(results, show_query=True):
    """
    검색 결과를 보기 좋게 출력
    
    Args:
        results: 검색 결과 딕셔너리
        show_query: 각 결과별 사용된 쿼리 표시 여부
    """
    print("\n" + "=" * 100)
    
    for algo_name, algo_results in results.items():
        print(f"\n{Fore.MAGENTA}▶ {algo_name.upper()} 검색 결과:{Style.RESET_ALL}")
        
        if not algo_results:
            print(f"  {Fore.RED}결과 없음{Style.RESET_ALL}")
            continue
        
        rows = []
        for i, result in enumerate(algo_results, 1):
            # 유사도 계산 (distance가 있으면 1-distance, 없으면 0)
            distance = result.get('distance', 0)
            similarity = 1 - distance if distance <= 1 else 0
            
            # 메타데이터 가져오기
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'N/A')
            page = metadata.get('page', 'N/A')
            chunk_id = metadata.get('chunk_id', 'N/A')
            
            # 텍스트 짧게 표시 (너무 길면 자르기)
            text = result.get('text', '')
            text_display = text[:150] + "..." if len(text) > 150 else text
            
            # 사용된 쿼리 정보
            query_info = ""
            if show_query and 'query_used' in result:
                is_enhanced = result.get('is_enhanced', False)
                query_text = result.get('query_used', '')
                if query_text:
                    query_text_short = query_text[:50] + "..." if len(query_text) > 50 else query_text
                    marker = f"{Fore.BLUE}[보강]{Style.RESET_ALL}" if is_enhanced else ""
                    query_info = f"{marker} {query_text_short}"
            
            # 행 추가
            color = Fore.GREEN if similarity > 0.8 else (Fore.YELLOW if similarity > 0.7 else Fore.WHITE)
            row = [
                i,
                f"{color}{similarity:.4f}{Style.RESET_ALL}",
                source,
                page,
                chunk_id
            ]
            
            if show_query:
                row.append(query_info)
                
            row.append(text_display)
            rows.append(row)
        
        headers = ["순위", "유사도", "출처", "페이지", "청크ID"]
        if show_query:
            headers.append("사용 쿼리")
        headers.append("내용")
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    
    print("\n" + "=" * 100)

def save_results_to_file(query, results, enhanced_queries=None, filename="real_search_results.json"):
    """
    검색 결과를 JSON 파일로 저장
    
    Args:
        query: 검색 쿼리
        results: 검색 결과
        enhanced_queries: 보강된 쿼리 목록
        filename: 저장할 파일 이름
    """
    output = {
        "query": query,
        "enhanced_queries": enhanced_queries if enhanced_queries else [query],
        "results": {}
    }
    
    for algo_name, algo_results in results.items():
        formatted_results = []
        
        for result in algo_results:
            # 유사도 계산
            distance = result.get('distance', 0)
            similarity = 1 - distance if distance <= 1 else 0
            
            # 메타데이터 가져오기
            metadata = result.get('metadata', {})
            
            formatted_result = {
                "text": result.get('text', ''),
                "similarity": round(similarity, 4),
                "metadata": metadata
            }
            
            # 사용된 쿼리 정보 추가
            if 'query_used' in result:
                formatted_result["query_used"] = result.get('query_used')
                formatted_result["is_enhanced"] = result.get('is_enhanced', False)
                
            formatted_results.append(formatted_result)
        
        output["results"][algo_name] = formatted_results
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"{Fore.GREEN}검색 결과가 {filename}에 저장되었습니다.{Style.RESET_ALL}")

def main():
    """메인 함수"""
    print(f"{Fore.GREEN}실제 PDF 데이터 RAG 검색 테스트{Style.RESET_ALL}")
    
    # 토론 텍스트에서 발췌한 쿼리 목록 (영어로 번역)
    test_queries = [
        {
            "ko": "트랜스휴머니즘은 인간의 존재를 기술적 문제로 단순화한다",
            "en": "Transhumanism simplifies human existence into a technical problem"
        },
        {
            "ko": "인간은 본질적으로 불완전하고 한계를 가진 존재이다",
            "en": "Humans are inherently imperfect beings with limitations"
        },
        {
            "ko": "트랜스휴머니즘이 인간의 본질적인 불완전함을 부정한다",
            "en": "Transhumanism denies the essential imperfection of humans"
        },
        {
            "ko": "초인 개념이 인간의 본질을 부정하고 인간의 존재를 위협한다",
            "en": "The concept of the Übermensch denies human essence and threatens human existence"
        }
    ]
    
    # 컬렉션 이름 목록 가져오기
    collections = get_available_collections()
    
    print(f"\n{Fore.YELLOW}사용 가능한 컬렉션 목록:{Style.RESET_ALL}")
    for i, collection in enumerate(collections, 1):
        print(f"{i}. {collection}")
    
    # 쿼리 선택 메뉴
    print(f"\n{Fore.YELLOW}테스트할 쿼리를 선택하세요 (니체 vs 카뮈 토론에서 발췌):{Style.RESET_ALL}")
    for i, query in enumerate(test_queries, 1):
        print(f"{i}. {query['ko']} (영어: {query['en']})")
    print(f"{len(test_queries) + 1}. 직접 입력")
    
    try:
        choice = int(input("\n선택 (번호 입력): "))
        
        if 1 <= choice <= len(test_queries):
            query_data = test_queries[choice - 1]
            query = query_data["en"]  # 영어 쿼리 사용
            print(f"\n선택한 쿼리: {query_data['ko']}")
            print(f"영어 변환: {query}")
        elif choice == len(test_queries) + 1:
            ko_query = input("\n검색할 쿼리를 한국어로 입력하세요: ")
            en_query = input("\n영어로 번역하여 입력하세요: ")
            query = en_query
        else:
            raise ValueError()
        
        # 컬렉션 선택 메뉴
        print(f"\n{Fore.YELLOW}검색할 컬렉션을 선택하세요:{Style.RESET_ALL}")
        for i, collection in enumerate(collections, 1):
            print(f"{i}. {collection}")
        
        collection_choice = int(input("\n선택 (번호 입력, 기본값: 1): ") or "1")
        if 1 <= collection_choice <= len(collections):
            collection_name = collections[collection_choice - 1]
        else:
            collection_name = collections[0]
        
        # 결과 개수 입력
        num_results = int(input("\n반환할 결과 개수 (기본값: 5): ") or "5")
        
        # 쿼리 보강 사용 여부
        use_enhancement = False
        enhancement_method = "hybrid"
        
        if enhance_query:
            use_enhancement_input = input("\n쿼리 보강을 사용하시겠습니까? (y/n, 기본값: n): ").lower()
            use_enhancement = use_enhancement_input.startswith('y')
            
            if use_enhancement:
                enhancement_methods = [
                    "paraphrasing", 
                    "keyword_extraction", 
                    "embedding_based", 
                    "query_to_question", 
                    "target_keyword", 
                    "keyword_expansion", 
                    "hybrid",
                    "all"  # 새 옵션: 모든 방법 사용
                ]
                
                print(f"\n{Fore.YELLOW}사용할 보강 방법을 선택하세요:{Style.RESET_ALL}")
                for i, method in enumerate(enhancement_methods, 1):
                    print(f"{i}. {method}")
                print(f"{len(enhancement_methods) + 1}. 여러 방법 사용 (쉼표로 구분)")
                
                enhancement_choice = int(input("\n선택 (번호 입력, 기본값: 7): ") or "7")
                if 1 <= enhancement_choice <= len(enhancement_methods):
                    enhancement_method = enhancement_methods[enhancement_choice - 1]
                elif enhancement_choice == len(enhancement_methods) + 1:
                    print("\n사용할 방법들을 쉼표로 구분하여 입력하세요")
                    print("예: paraphrasing,keyword_extraction,query_to_question")
                    methods_input = input("방법들: ")
                    enhancement_method = methods_input
                else:
                    enhancement_method = "hybrid"
        
        # 검색 실행
        results = search_with_real_query(
            query, 
            collection_name, 
            num_results,
            use_enhancement,
            enhancement_method
        )
        
        # 보강된 쿼리 목록 생성
        enhanced_queries = None
        if use_enhancement and enhance_query:
            try:
                if enhancement_method == "all":
                    # 모든 쿼리 보강 결과 저장
                    enhancement_methods = [
                        "paraphrasing", 
                        "keyword_extraction", 
                        "embedding_based", 
                        "query_to_question", 
                        "target_keyword", 
                        "keyword_expansion", 
                        "hybrid"
                    ]
                    enhanced_queries = [query]  # 원본 쿼리 포함
                    for method in enhancement_methods:
                        method_queries = enhance_query(query, method=method)
                        if len(method_queries) > 1:  # 첫 번째는 원본 쿼리이므로 제외
                            enhanced_queries.extend(method_queries[1:])
                elif "," in enhancement_method:
                    methods_list = [m.strip() for m in enhancement_method.split(",")]
                    enhanced_queries = [query]  # 원본 쿼리 포함
                    for method in methods_list:
                        method_queries = enhance_query(query, method=method)
                        if len(method_queries) > 1:  # 첫 번째는 원본 쿼리이므로 제외
                            enhanced_queries.extend(method_queries[1:])
                else:
                    enhanced_queries = enhance_query(query, method=enhancement_method)
            except Exception as e:
                print(f"{Fore.RED}최종 쿼리 목록 생성 중 오류: {str(e)}{Style.RESET_ALL}")
                enhanced_queries = [query]
        
        # 결과 출력
        print_results(results, show_query=use_enhancement)
        
        # 결과 저장
        save_results_to_file(query, results, enhanced_queries)
        
    except ValueError:
        print(f"{Fore.RED}올바른 숫자를 입력하세요.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}오류 발생: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 