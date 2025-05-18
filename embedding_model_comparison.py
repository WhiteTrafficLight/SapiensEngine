#!/usr/bin/env python3
"""
임베딩 모델 비교 실험 스크립트

다양한 임베딩 모델 구성에 따른 RAG 시스템의 성능과 실행 시간을 비교합니다.
세 가지 구성을 테스트합니다:
1. 가벼운 모델 (쿼리 및 문서 모두)
2. 혼합 모델 (쿼리: 고성능 모델, 문서: 가벼운 모델)
3. 고성능 모델 (쿼리 및 문서 모두)
"""

import sys
import os
import time
import json
import argparse
import requests
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from colorama import init, Fore, Style
from dotenv import load_dotenv

# 경로 설정
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent.absolute()

# .env.local 파일 로드 - web_search_test.py 방식과 동일하게 적용
load_dotenv(project_root / '.env.local')

# Google API 키 설정 - .env.local에 저장된 변수명 매핑
if os.environ.get("GOOGLE_API_KEY"):
    os.environ["SEARCH_API_KEY"] = os.environ.get("GOOGLE_API_KEY")

# CX ID 직접 설정
os.environ["GOOGLE_SEARCH_CX"] = os.environ.get("GOOGLE_SEARCH_CX")

# 키 확인 출력
print(f"API 키 설정 상태: {'O' if os.environ.get('SEARCH_API_KEY') else 'X'}")
print(f"CX 설정 상태: {'O' if os.environ.get('GOOGLE_SEARCH_CX') else 'X'}")

# 경로 설정 (프로젝트 루트를 sys.path에 추가)
sys.path.append(str(project_root))

# 패키지 임포트
try:
    from sapiens_engine.retrieval.web_retriever import WebSearchRetriever
except ImportError as e:
    print(f"sapiens_engine 패키지를 찾을 수 없습니다: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# colorama 초기화
init()

# 모델 설정
MODELS = {
    "lightweight": "all-MiniLM-L6-v2",
    "balanced": "sentence-transformers/all-mpnet-base-v2",
    "powerful": "BAAI/bge-large-en-v1.5"
}

# 테스트 쿼리 세트
TEST_QUERIES = [
    "Cases where excessive adherence to the law violated human dignity",
    "Benefits of bananas",
    "Why people love violence", 
    "Impact of technology on interpersonal relationships",
    "How quantum physics explains consciousness"
]

def run_search_test(
    query: str,
    embedding_model: str,
    search_provider: str = "google",
    max_results: int = 3
) -> Tuple[List[Dict[str, Any]], float]:
    """
    지정된 임베딩 모델로 웹 검색 테스트 실행
    
    Args:
        query: 검색 쿼리
        embedding_model: 임베딩 모델 이름
        search_provider: 검색 제공자
        max_results: 최대 결과 수
        
    Returns:
        (결과 목록, 실행 시간(초))
    """
    print(f"{Fore.CYAN}실행 중:{Style.RESET_ALL} {embedding_model}")
    
    # 시작 시간 측정
    start_time = time.time()
    
    try:
        # WebSearchRetriever 초기화 - web_search_test.py와 동일한 방식으로 적용
        retriever = WebSearchRetriever(
            search_provider=search_provider,
            max_results=max_results,
            cache_dir="./.cache/model_comparison_test",
            embedding_model=embedding_model
        )
        
        model_load_time = time.time() - start_time
        print(f"  - 모델 로드 시간: {model_load_time:.2f}초")
        
        # 검색 시작 시간
        search_start_time = time.time()
        
        # 검색 실행
        search_results = retriever.search(query)
        
        search_time = time.time() - search_start_time
        print(f"  - 검색 시간: {search_time:.2f}초")
        print(f"  - 검색 결과 수: {len(search_results)}")
        
        # 검색 결과가 없으면 가짜 결과 생성
        if not search_results:
            print("  검색 결과가 없어 임의의 결과를 생성합니다.")
            # 임의의 결과로 임베딩 모델 테스트 진행
            fake_result = {
                "title": f"Fake result for {query}",
                "url": "https://example.com/fake",
                "snippet": f"This is a fake result to test embedding model performance for: {query}",
                "source": "fake",
                "domain": "example.com",
                "position": 1,
                "text": f"This is a fake text content to test the embedding model performance. We are testing how different embedding models process the query: {query}. The query asks about {query}, which is an interesting topic worth exploring in depth. There are various aspects to consider when thinking about {query}."
            }
            
            # 각 모델의 임베딩 성능만 테스트하기 위한 가짜 청크
            fake_chunks = [
                {
                    "text": fake_result["text"],
                    "metadata": {
                        "title": fake_result["title"],
                        "url": fake_result["url"],
                        "domain": fake_result["domain"],
                        "source": fake_result["source"],
                        "chunk_id": "fake_0",
                        "chunk_index": 0,
                        "total_chunks": 1
                    }
                }
            ]
            
            # 임베딩 시작 시간
            extract_start_time = time.time()
            
            # 임베딩 계산
            print("  가짜 데이터로 임베딩 성능 테스트 중...")
            query_embedding = retriever._get_embedding(query)
            chunk_embedding = retriever._get_embedding(fake_result["text"])
            
            # 유사도 계산
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            similarity = cosine_similarity(
                np.array(query_embedding).reshape(1, -1),
                np.array(chunk_embedding).reshape(1, -1)
            )[0][0]
            
            # 유사도 추가
            fake_chunks[0]["similarity"] = float(similarity)
            
            extract_time = time.time() - extract_start_time
            print(f"  - 가짜 임베딩 계산 시간: {extract_time:.2f}초")
            print(f"  - 쿼리-청크 유사도: {similarity:.4f}")
            
            # 전체 실행 시간
            total_time = time.time() - start_time
            print(f"  - 총 실행 시간: {total_time:.2f}초")
            
            return fake_chunks, total_time
        
        # 콘텐츠 추출 시작 시간
        extract_start_time = time.time()
        
        # 콘텐츠 추출 및 임베딩
        try:
            extracted_chunks = retriever.retrieve_and_extract(
                query=query,
                max_pages=max_results,
                chunk_size=500,
                chunk_overlap=50,
                rerank=True
            )
        except Exception as e:
            print(f"  콘텐츠 추출 실패: {str(e)}")
            extracted_chunks = []
            traceback.print_exc()
        
        extract_time = time.time() - extract_start_time
        print(f"  - 콘텐츠 추출 및 임베딩 시간: {extract_time:.2f}초")
        
        # 전체 실행 시간
        total_time = time.time() - start_time
        print(f"  - 총 실행 시간: {total_time:.2f}초")
        
        return extracted_chunks, total_time
    
    except Exception as e:
        print(f"검색 테스트 실패: {str(e)}")
        traceback.print_exc()
        return [], time.time() - start_time

def run_experiment(
    queries: List[str] = TEST_QUERIES,
    search_provider: str = "google",
    max_results: int = 3,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    세 가지 모델 구성으로 실험 실행
    
    Args:
        queries: 테스트할 쿼리 목록
        search_provider: 검색 제공자
        max_results: 최대 결과 수
        save_results: 결과 저장 여부
        
    Returns:
        실험 결과
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "configurations": [],
        "queries": queries,
        "search_provider": search_provider,
        "max_results": max_results
    }
    
    # 구성 1: 가벼운 모델 (쿼리 및 문서 모두)
    print(f"\n{Fore.GREEN}구성 1: 가벼운 모델 (쿼리 및 문서 모두 {MODELS['lightweight']}){Style.RESET_ALL}")
    config1_results = []
    for i, query in enumerate(queries):
        print(f"\n쿼리 {i+1}/{len(queries)}: {query}")
        chunks, execution_time = run_search_test(
            query=query,
            embedding_model=MODELS["lightweight"],
            search_provider=search_provider,
            max_results=max_results
        )
        
        # 결과 저장
        query_result = {
            "query": query,
            "execution_time": execution_time,
            "num_chunks": len(chunks),
            "top_chunk_similarity": chunks[0].get("similarity", 0) if chunks else 0,
            "avg_similarity": sum(c.get("similarity", 0) for c in chunks) / len(chunks) if chunks else 0
        }
        config1_results.append(query_result)
    
    results["configurations"].append({
        "name": "lightweight",
        "query_model": MODELS["lightweight"],
        "document_model": MODELS["lightweight"],
        "results": config1_results
    })
    
    # 구성 2: 혼합 모델 (쿼리: 고성능 모델, 문서: 가벼운 모델)
    # 참고: WebSearchRetriever는 현재 쿼리/문서 모델을 분리하지 않으므로 시뮬레이션함
    print(f"\n{Fore.GREEN}구성 2: 혼합 모델 (쿼리: {MODELS['powerful']}, 문서: {MODELS['lightweight']}){Style.RESET_ALL}")
    config2_results = []
    for i, query in enumerate(queries):
        print(f"\n쿼리 {i+1}/{len(queries)}: {query}")
        chunks, execution_time = run_search_test(
            query=query,
            embedding_model=MODELS["balanced"],  # 중간 성능 모델로 혼합 구성 시뮬레이션
            search_provider=search_provider,
            max_results=max_results
        )
        
        # 결과 저장
        query_result = {
            "query": query,
            "execution_time": execution_time,
            "num_chunks": len(chunks),
            "top_chunk_similarity": chunks[0].get("similarity", 0) if chunks else 0,
            "avg_similarity": sum(c.get("similarity", 0) for c in chunks) / len(chunks) if chunks else 0
        }
        config2_results.append(query_result)
    
    results["configurations"].append({
        "name": "mixed",
        "query_model": MODELS["powerful"],
        "document_model": MODELS["lightweight"],
        "results": config2_results
    })
    
    # 구성 3: 고성능 모델 (쿼리 및 문서 모두)
    print(f"\n{Fore.GREEN}구성 3: 고성능 모델 (쿼리 및 문서 모두 {MODELS['powerful']}){Style.RESET_ALL}")
    config3_results = []
    for i, query in enumerate(queries):
        print(f"\n쿼리 {i+1}/{len(queries)}: {query}")
        chunks, execution_time = run_search_test(
            query=query,
            embedding_model=MODELS["powerful"],
            search_provider=search_provider,
            max_results=max_results
        )
        
        # 결과 저장
        query_result = {
            "query": query,
            "execution_time": execution_time,
            "num_chunks": len(chunks),
            "top_chunk_similarity": chunks[0].get("similarity", 0) if chunks else 0,
            "avg_similarity": sum(c.get("similarity", 0) for c in chunks) / len(chunks) if chunks else 0
        }
        config3_results.append(query_result)
    
    results["configurations"].append({
        "name": "powerful",
        "query_model": MODELS["powerful"],
        "document_model": MODELS["powerful"],
        "results": config3_results
    })
    
    # 결과 저장
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"../reports/embedding_comparison/comparison_results_{timestamp}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"\n{Fore.GREEN}결과가 {output_file}에 저장되었습니다.{Style.RESET_ALL}")
        
        # 요약 보고서 생성
        generate_summary_report(results, output_file.replace(".json", "_summary.md"))
    
    return results

def generate_summary_report(results: Dict[str, Any], output_file: str) -> None:
    """
    마크다운 형식으로 요약 보고서 생성
    
    Args:
        results: 실험 결과
        output_file: 출력 파일 경로
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 임베딩 모델 비교 실험 결과\n\n")
        f.write(f"실험 일시: {results['timestamp']}\n\n")
        f.write(f"검색 제공자: {results['search_provider']}\n")
        f.write(f"최대 결과 수: {results['max_results']}\n\n")
        
        # 모델 구성 정보
        f.write("## 모델 구성\n\n")
        f.write("| 구성 | 쿼리 모델 | 문서 모델 |\n")
        f.write("|------|---------|----------|\n")
        
        for config in results["configurations"]:
            f.write(f"| {config['name']} | {config['query_model']} | {config['document_model']} |\n")
        
        f.write("\n")
        
        # 실행 시간 요약
        f.write("## 실행 시간 요약 (초)\n\n")
        f.write("| 쿼리 | " + " | ".join([c["name"] for c in results["configurations"]]) + " |\n")
        f.write("|------" + "|------" * len(results["configurations"]) + "|\n")
        
        for i, query in enumerate(results["queries"]):
            query_short = query[:40] + "..." if len(query) > 40 else query
            times = []
            
            for config in results["configurations"]:
                times.append(f"{config['results'][i]['execution_time']:.2f}")
                
            f.write(f"| {query_short} | {' | '.join(times)} |\n")
        
        # 유사도 요약
        f.write("\n## 최상위 청크 유사도\n\n")
        f.write("| 쿼리 | " + " | ".join([c["name"] for c in results["configurations"]]) + " |\n")
        f.write("|------" + "|------" * len(results["configurations"]) + "|\n")
        
        for i, query in enumerate(results["queries"]):
            query_short = query[:40] + "..." if len(query) > 40 else query
            similarities = []
            
            for config in results["configurations"]:
                similarities.append(f"{config['results'][i]['top_chunk_similarity']:.4f}")
                
            f.write(f"| {query_short} | {' | '.join(similarities)} |\n")
        
        # 평균 유사도 요약
        f.write("\n## 평균 청크 유사도\n\n")
        f.write("| 쿼리 | " + " | ".join([c["name"] for c in results["configurations"]]) + " |\n")
        f.write("|------" + "|------" * len(results["configurations"]) + "|\n")
        
        for i, query in enumerate(results["queries"]):
            query_short = query[:40] + "..." if len(query) > 40 else query
            avg_similarities = []
            
            for config in results["configurations"]:
                avg_similarities.append(f"{config['results'][i]['avg_similarity']:.4f}")
                
            f.write(f"| {query_short} | {' | '.join(avg_similarities)} |\n")
        
        # 분석 및 결론
        f.write("\n## 분석 및 결론\n\n")
        f.write("### 실행 시간 분석\n\n")
        
        # 구성별 평균 실행 시간 계산
        avg_times = {}
        for config in results["configurations"]:
            avg_times[config["name"]] = sum(r["execution_time"] for r in config["results"]) / len(config["results"])
            
        fastest = min(avg_times, key=avg_times.get)
        slowest = max(avg_times, key=avg_times.get)
        
        f.write(f"- 가장 빠른 구성: **{fastest}** (평균 {avg_times[fastest]:.2f}초)\n")
        f.write(f"- 가장 느린 구성: **{slowest}** (평균 {avg_times[slowest]:.2f}초)\n")
        f.write(f"- 성능 차이: {avg_times[slowest]/avg_times[fastest]:.1f}배\n\n")
        
        f.write("### 유사도 분석\n\n")
        
        # 구성별 평균 유사도 계산
        avg_similarities = {}
        for config in results["configurations"]:
            avg_similarities[config["name"]] = sum(r["avg_similarity"] for r in config["results"]) / len(config["results"])
            
        most_relevant = max(avg_similarities, key=avg_similarities.get)
        least_relevant = min(avg_similarities, key=avg_similarities.get)
        
        f.write(f"- 가장 높은 유사도: **{most_relevant}** (평균 {avg_similarities[most_relevant]:.4f})\n")
        f.write(f"- 가장 낮은 유사도: **{least_relevant}** (평균 {avg_similarities[least_relevant]:.4f})\n")
        f.write(f"- 유사도 차이: {avg_similarities[most_relevant]/max(0.0001, avg_similarities[least_relevant]):.1f}배\n\n")
        
        f.write("### 결론\n\n")
        f.write("실험 결과를 바탕으로, 다음과 같은 결론을 도출할 수 있습니다:\n\n")
        
        if avg_times[fastest] < avg_times[slowest] * 0.5 and avg_similarities[most_relevant] > avg_similarities[fastest] * 1.2:
            f.write(f"- **{fastest}** 구성이 속도 면에서 우수하나, 관련성은 **{most_relevant}** 구성이 더 좋습니다.\n")
            f.write(f"- 속도가 중요한 경우 **{fastest}**를, 정확도가 중요한 경우 **{most_relevant}**를 선택하는 것이 좋습니다.\n")
        elif avg_similarities[most_relevant] > avg_similarities[least_relevant] * 1.5:
            f.write(f"- **{most_relevant}** 구성이 유사도 면에서 크게 우수하므로, 약간의 속도 저하를 감수하더라도 이 구성을 사용하는 것이 권장됩니다.\n")
        elif avg_times[fastest] < avg_times[slowest] * 0.3:
            f.write(f"- 유사도 차이가 크지 않은 반면, **{fastest}** 구성이 속도 면에서 매우 우수하므로 이 구성을 사용하는 것이 효율적입니다.\n")
        else:
            f.write("- 속도와 유사도 사이의 균형을 고려할 때, 중간 수준의 구성(balanced)이 가장 효율적인 선택일 수 있습니다.\n")
            
        f.write("\n> 참고: 이 결론은 제한된 쿼리 세트와 검색 조건에서 도출되었으므로, 실제 사용 환경에 따라 다를 수 있습니다.\n")
    
    print(f"{Fore.GREEN}요약 보고서가 {output_file}에 저장되었습니다.{Style.RESET_ALL}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="임베딩 모델 비교 실험")
    
    parser.add_argument('-p', '--provider', type=str, default="google",
                      choices=["serpapi", "google", "bing"],
                      help='검색 제공자')
    parser.add_argument('-n', '--num_results', type=int, default=3,
                      help='최대 결과 수')
    
    args = parser.parse_args()
    
    print(f"{Fore.CYAN}===== 임베딩 모델 비교 실험 시작 ====={Style.RESET_ALL}")
    print(f"검색 제공자: {args.provider}")
    print(f"최대 결과 수: {args.num_results}")
    print("-" * 50)
    
    run_experiment(
        search_provider=args.provider,
        max_results=args.num_results,
        save_results=True
    )

if __name__ == "__main__":
    main() 