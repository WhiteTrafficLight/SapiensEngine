#!/usr/bin/env python3
"""
웹 검색 기반 RAG 테스트 스크립트

WebSearchRetriever를 사용하여 실시간 웹 검색 및 콘텐츠 추출을 테스트합니다.
"""

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from colorama import init, Fore, Style
from dotenv import load_dotenv

# 경로 설정
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent.absolute()

# .env.local 파일 로드 - 상대 경로 수정
load_dotenv(project_root / '.env.local')

# Google API 키 설정 - .env.local에 저장된 변수명 매핑
if os.environ.get("GOOGLE_API_KEY"):
    os.environ["SEARCH_API_KEY"] = os.environ.get("GOOGLE_API_KEY")

# CX ID 직접 설정 - .env.local의 값이 올바르지 않음
os.environ["GOOGLE_SEARCH_CX"] = os.environ.get("GOOGLE_SEARCH_CX")

# 키 확인 출력
print(f"API 키 설정 상태: {'O' if os.environ.get('SEARCH_API_KEY') else 'X'}")
print(f"CX 설정 상태: {'O' if os.environ.get('GOOGLE_SEARCH_CX') else 'X'}")

# 경로 설정 (프로젝트 루트를 sys.path에 추가)
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))

# 패키지 임포트
try:
    from sapiens_engine.retrieval.web_retriever import WebSearchRetriever
except ImportError:
    print("sapiens_engine 패키지를 찾을 수 없습니다. 경로를 확인하세요.")
    sys.exit(1)

# colorama 초기화
init()

def run_web_search_test(
    query: str, 
    search_provider: str = "serpapi", 
    max_results: int = 3,
    save_results: bool = True,
    output_file: str = None,
    embedding_model: str = "BAAI/bge-large-en-v1.5"
):
    """
    웹 검색 및 콘텐츠 추출 테스트 실행
    
    Args:
        query: 검색 쿼리
        search_provider: 검색 제공자 (serpapi, google, bing)
        max_results: 최대 결과 수
        save_results: 결과 저장 여부
        output_file: 결과 저장 파일 (None이면 자동 생성)
        embedding_model: 임베딩 모델 이름
    """
    print(f"{Fore.CYAN}===== 웹 검색 기반 RAG 테스트 ====={Style.RESET_ALL}")
    print(f"{Fore.GREEN}쿼리:{Style.RESET_ALL} {query}")
    print(f"{Fore.GREEN}검색 제공자:{Style.RESET_ALL} {search_provider}")
    print(f"{Fore.GREEN}최대 결과 수:{Style.RESET_ALL} {max_results}")
    print(f"{Fore.GREEN}임베딩 모델:{Style.RESET_ALL} {embedding_model}")
    print("-" * 50)
    
    # API 키 확인
    if search_provider == "serpapi" and not os.environ.get("SERP_API_KEY"):
        print(f"{Fore.RED}경고: SERP_API_KEY 환경 변수가 설정되지 않았습니다.{Style.RESET_ALL}")
    elif search_provider in ["google", "bing"] and not os.environ.get("SEARCH_API_KEY"):
        print(f"{Fore.RED}경고: SEARCH_API_KEY 환경 변수가 설정되지 않았습니다.{Style.RESET_ALL}")
    
    # WebSearchRetriever 초기화
    retriever = WebSearchRetriever(
        search_provider=search_provider,
        max_results=max_results,
        cache_dir="./.cache/web_search_test",
        embedding_model=embedding_model
    )
    
    print(f"{Fore.YELLOW}1. 웹 검색 수행 중...{Style.RESET_ALL}")
    search_results = retriever.search(query)
    
    print(f"\n{Fore.GREEN}검색 결과 {len(search_results)}개 찾음:{Style.RESET_ALL}")
    for i, result in enumerate(search_results):
        print(f"  {i+1}. {Fore.CYAN}{result.get('title', '제목 없음')}{Style.RESET_ALL}")
        print(f"     URL: {result.get('url', '')}")
        print(f"     도메인: {result.get('domain', '')}")
        print(f"     발췌: {result.get('snippet', '')[:100]}...")
        print()
    
    print(f"{Fore.YELLOW}2. 콘텐츠 추출 및 청크화 중...{Style.RESET_ALL}")
    extracted_chunks = retriever.retrieve_and_extract(
        query=query,
        max_pages=max_results,
        chunk_size=500,
        chunk_overlap=50,
        rerank=True
    )
    
    print(f"\n{Fore.GREEN}추출된 청크 {len(extracted_chunks)}개:{Style.RESET_ALL}")
    for i, chunk in enumerate(extracted_chunks[:5]):  # 상위 5개만 표시
        similarity = chunk.get("similarity", 0)
        score = chunk.get("score", 0)
        color = Fore.RED if similarity < 0.5 else Fore.GREEN
        
        print(f"  {i+1}. {color}[유사도: {similarity:.4f} | 점수: {score:.4f}]{Style.RESET_ALL}")
        print(f"     출처: {chunk['metadata'].get('url', '')}")
        print(f"     도메인: {chunk['metadata'].get('domain', '')}")
        print(f"     내용: {chunk['text'][:150]}...")
        print()
    
    # 더 많은 청크가 있는 경우
    if len(extracted_chunks) > 5:
        print(f"... 외 {len(extracted_chunks) - 5}개 청크 더 있음")
    
    # 결과 저장
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_file or f"../../results/web/web_search_results_{timestamp}.json"
        
        results = {
            "query": query,
            "search_provider": search_provider,
            "embedding_model": embedding_model,
            "timestamp": datetime.now().isoformat(),
            "search_results": search_results,
            "extracted_chunks": extracted_chunks
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n{Fore.GREEN}결과가 {output_file}에 저장되었습니다.{Style.RESET_ALL}")
    
    return extracted_chunks

def get_user_input():
    """
    사용자로부터 대화형으로 검색 옵션을 입력받습니다.
    
    Returns:
        dict: 사용자 입력 옵션
    """
    print(f"\n{Fore.CYAN}===== 웹 검색 RAG 테스트 설정 ====={Style.RESET_ALL}")
    
    # 쿼리 입력
    query = input(f"{Fore.GREEN}검색 쿼리를 입력하세요: {Style.RESET_ALL}")
    
    # 검색 제공자 선택
    print(f"\n{Fore.GREEN}검색 제공자를 선택하세요:{Style.RESET_ALL}")
    print(f"  1. {Fore.CYAN}SerpAPI{Style.RESET_ALL} (가장 정확하지만 유료)")
    print(f"  2. {Fore.CYAN}Google Custom Search{Style.RESET_ALL} (무료지만 일일 할당량 있음)")
    print(f"  3. {Fore.CYAN}Bing Search{Style.RESET_ALL} (무료지만 추가 설정 필요)")
    
    provider_choice = input(f"{Fore.GREEN}번호 선택 [기본값: 1]: {Style.RESET_ALL}")
    provider_options = {
        "1": "serpapi",
        "2": "google",
        "3": "bing"
    }
    search_provider = provider_options.get(provider_choice, "serpapi")
    
    # 임베딩 모델 선택
    print(f"\n{Fore.GREEN}임베딩 모델을 선택하세요:{Style.RESET_ALL}")
    print(f"  1. {Fore.CYAN}BAAI/bge-large-en-v1.5{Style.RESET_ALL} (기본값, 대형 고성능)")
    print(f"  2. {Fore.CYAN}all-MiniLM-L6-v2{Style.RESET_ALL} (소형 빠른 모델)")
    print(f"  3. {Fore.CYAN}sentence-transformers/all-mpnet-base-v2{Style.RESET_ALL} (중형 균형 모델)")
    print(f"  4. {Fore.CYAN}text-embedding-ada-002{Style.RESET_ALL} (OpenAI 모델, API 키 필요)")
    print(f"  5. {Fore.CYAN}직접 입력{Style.RESET_ALL}")
    
    model_choice = input(f"{Fore.GREEN}번호 선택 [기본값: 1]: {Style.RESET_ALL}")
    model_options = {
        "1": "BAAI/bge-large-en-v1.5",
        "2": "all-MiniLM-L6-v2",
        "3": "sentence-transformers/all-mpnet-base-v2",
        "4": "text-embedding-ada-002"
    }
    
    if model_choice == "5":
        embedding_model = input(f"{Fore.GREEN}임베딩 모델 이름을 입력하세요: {Style.RESET_ALL}")
    else:
        embedding_model = model_options.get(model_choice, "BAAI/bge-large-en-v1.5")
    
    # 결과 수 입력
    max_results_input = input(f"\n{Fore.GREEN}검색할 최대 결과 수 [기본값: 3]: {Style.RESET_ALL}")
    max_results = int(max_results_input) if max_results_input.isdigit() else 3
    
    # 결과 저장 여부
    save_input = input(f"\n{Fore.GREEN}결과를 파일로 저장하시겠습니까? (y/n) [기본값: y]: {Style.RESET_ALL}").lower()
    save_results = save_input in ["", "y", "yes"]
    
    # 저장 경로 지정 (선택 사항)
    output_file = None
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"../../results/web/web_search_results_{timestamp}.json"
        output_input = input(f"\n{Fore.GREEN}저장 파일 경로 [기본값: {default_output}]: {Style.RESET_ALL}")
        output_file = output_input if output_input else default_output
    
    # 선택 항목 요약
    print(f"\n{Fore.CYAN}=== 선택한 옵션 ===={Style.RESET_ALL}")
    print(f"• 쿼리: {query}")
    print(f"• 검색 제공자: {search_provider}")
    print(f"• 임베딩 모델: {embedding_model}")
    print(f"• 최대 결과 수: {max_results}")
    print(f"• 결과 저장: {'예' if save_results else '아니오'}")
    if save_results:
        print(f"• 저장 경로: {output_file}")
    
    confirm = input(f"\n{Fore.YELLOW}이대로 진행하시겠습니까? (y/n) [기본값: y]: {Style.RESET_ALL}").lower()
    if confirm not in ["", "y", "yes"]:
        print(f"\n{Fore.RED}검색이 취소되었습니다.{Style.RESET_ALL}")
        sys.exit(0)
    
    return {
        "query": query,
        "search_provider": search_provider,
        "max_results": max_results,
        "save_results": save_results,
        "output_file": output_file,
        "embedding_model": embedding_model
    }

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="웹 검색 기반 RAG 테스트")
    
    parser.add_argument('-q', '--query', type=str, 
                      help='검색 쿼리')
    parser.add_argument('-p', '--provider', type=str, default="serpapi",
                      choices=["serpapi", "google", "bing"],
                      help='검색 제공자')
    parser.add_argument('-n', '--num_results', type=int, default=3,
                      help='최대 결과 수')
    parser.add_argument('-s', '--save', action='store_true',
                      help='결과 저장 여부')
    parser.add_argument('-o', '--output', type=str, default=None,
                      help='결과 저장 파일')
    parser.add_argument('-e', '--embedding_model', type=str, default="BAAI/bge-large-en-v1.5",
                      help='임베딩 모델 이름')
    
    args = parser.parse_args()
    
    # 명령줄 인수가 제공되었는지 확인
    # 쿼리가 제공되었으면 명령줄 모드, 아니면 대화형 모드
    if args.query:
        # 명령줄 모드
    run_web_search_test(
        query=args.query,
        search_provider=args.provider,
        max_results=args.num_results,
        save_results=args.save,
            output_file=args.output,
            embedding_model=args.embedding_model
        )
    else:
        # 대화형 모드
        user_options = get_user_input()
        run_web_search_test(
            query=user_options["query"],
            search_provider=user_options["search_provider"],
            max_results=user_options["max_results"],
            save_results=user_options["save_results"],
            output_file=user_options["output_file"],
            embedding_model=user_options["embedding_model"]
    )

if __name__ == "__main__":
    main() 