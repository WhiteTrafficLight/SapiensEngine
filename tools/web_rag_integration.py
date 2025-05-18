#!/usr/bin/env python3
"""
웹 검색 및 벡터 DB 통합 RAG 시스템

웹 검색 결과와 로컬 벡터 데이터베이스를 함께 활용하는 통합 RAG 시스템입니다.
실시간 웹 검색과 로컬 벡터 스토어를 조합해 더 포괄적인 검색 결과를 제공합니다.
"""

import sys
import json
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from colorama import init, Fore, Style
from tabulate import tabulate

# 경로 설정
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# 패키지 임포트
try:
    from sapiens_engine.retrieval.web_retriever import WebSearchRetriever
    from sapiens_engine.core.rag_manager import RAGManager
    from sapiens_engine.core.query_enhancer import enhance_query
except ImportError as e:
    print(f"필요한 패키지를 찾을 수 없습니다: {str(e)}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# colorama 초기화
init()

class WebIntegratedRAG:
    """
    웹 검색과 로컬 벡터 데이터베이스를 통합한 RAG 시스템
    
    웹 검색 결과와 로컬 데이터를 함께 활용해 더 포괄적인 컨텍스트를 제공합니다.
    """
    
    def __init__(
        self,
        vector_db_path: str = "./vectordb",
        vector_collection: str = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        search_provider: str = "serpapi",
        api_key: Optional[str] = None,
        cache_dir: str = "./.cache/web_rag",
        web_max_results: int = 3,
        web_weight: float = 0.5
    ):
        """
        WebIntegratedRAG 초기화
        
        Args:
            vector_db_path: 로컬 벡터 DB 경로
            vector_collection: 사용할 벡터 DB 컬렉션 이름
            embedding_model: 임베딩 모델 이름
            search_provider: 웹 검색 제공자
            api_key: 검색 API 키
            cache_dir: 웹 검색 캐시 디렉토리
            web_max_results: 웹 검색 최대 결과 수
            web_weight: 웹 검색 결과 가중치 (0~1)
        """
        # 가중치 검증
        if not 0 <= web_weight <= 1:
            raise ValueError("web_weight는 0과 1 사이의 값이어야 합니다.")
        
        self.web_weight = web_weight
        self.vector_weight = 1.0 - web_weight
        
        # RAG 매니저 초기화
        self.rag_manager = RAGManager(
            db_path=vector_db_path,
            embedding_model=embedding_model
        )
        
        # 웹 검색 리트리버 초기화
        self.web_retriever = WebSearchRetriever(
            embedding_model=embedding_model,
            search_provider=search_provider,
            api_key=api_key,
            max_results=web_max_results,
            cache_dir=cache_dir
        )
        
        # 컬렉션 이름 설정
        self.vector_collection = vector_collection
        if not vector_collection:
            collections = self.rag_manager.client.list_collections()
            if collections:
                self.vector_collection = collections[0].name
                logger.info(f"기본 컬렉션 사용: {self.vector_collection}")
            else:
                logger.warning("사용 가능한 벡터 DB 컬렉션이 없습니다.")
    
    def search(
        self,
        query: str,
        use_web: bool = True,
        use_vector: bool = True,
        enhance_queries: bool = False,
        enhancement_method: str = "hybrid",
        vector_search_method: str = "simple",
        vector_k: int = 5,
        web_max_pages: int = 3,
        rerank: bool = True,
        max_results: int = 8
    ) -> Dict[str, Any]:
        """
        통합 검색 수행
        
        Args:
            query: 검색 쿼리
            use_web: 웹 검색 사용 여부
            use_vector: 벡터 DB 검색 사용 여부
            enhance_queries: 쿼리 보강 사용 여부
            enhancement_method: 쿼리 보강 방법
            vector_search_method: 벡터 검색 방법
            vector_k: 벡터 검색 결과 수
            web_max_pages: 웹 검색할 최대 페이지 수
            rerank: 재순위화 여부
            max_results: 최종 반환할 최대 결과 수
            
        Returns:
            통합 검색 결과
        """
        if not use_web and not use_vector:
            raise ValueError("웹 검색과 벡터 DB 검색 중 적어도 하나는 활성화해야 합니다.")
        
        # 쿼리 보강 (선택 사항)
        queries = [query]
        if enhance_queries:
            enhanced_queries = enhance_query(query, method=enhancement_method, count=2)
            queries.extend(enhanced_queries)
            logger.info(f"쿼리 보강 완료: {len(queries)}개 쿼리 생성")
        
        all_results = []
        
        # 벡터 DB 검색
        vector_results = []
        if use_vector and self.vector_collection:
            try:
                for q in queries:
                    # 검색 방법에 따라 다른 함수 호출
                    if vector_search_method == "simple":
                        results = self.rag_manager.simple_top_k_search(self.vector_collection, q, vector_k)
                    elif vector_search_method == "semantic":
                        results = self.rag_manager.semantic_window_search(self.vector_collection, q, vector_k)
                    elif vector_search_method == "hybrid":
                        results = self.rag_manager.hybrid_search(self.vector_collection, q, vector_k)
                    elif vector_search_method == "mmr":
                        results = self.rag_manager.mmr_search(self.vector_collection, q, vector_k)
                    elif vector_search_method == "threshold":
                        results = self.rag_manager.threshold_search(self.vector_collection, q, 0.6, vector_k)
                    else:
                        results = self.rag_manager.simple_top_k_search(self.vector_collection, q, vector_k)
                    
                    # 소스 정보 추가
                    for r in results:
                        r["source"] = "vector_db"
                        r["query_used"] = q
                        r["is_enhanced"] = q != query
                        
                        # 벡터 가중치 적용
                        similarity = 1.0 - r.get("distance", 0)
                        r["similarity"] = similarity
                        r["weighted_similarity"] = similarity * self.vector_weight
                    
                    vector_results.extend(results)
                
                logger.info(f"벡터 DB 검색 완료: {len(vector_results)}개 결과")
            except Exception as e:
                logger.error(f"벡터 DB 검색 실패: {str(e)}")
        
        # 웹 검색
        web_results = []
        if use_web:
            try:
                for q in queries:
                    # 웹 검색 및 콘텐츠 추출
                    chunks = self.web_retriever.retrieve_and_extract(
                        query=q,
                        max_pages=web_max_pages,
                        chunk_size=500,
                        chunk_overlap=50,
                        rerank=True
                    )
                    
                    # 소스 정보 추가
                    for chunk in chunks:
                        chunk["source"] = "web"
                        chunk["query_used"] = q
                        chunk["is_enhanced"] = q != query
                        
                        # similarity가 없는 경우 기본값 설정
                        if "similarity" not in chunk:
                            chunk["similarity"] = 0.5
                        
                        # 웹 가중치 적용
                        chunk["weighted_similarity"] = chunk["similarity"] * self.web_weight
                    
                    web_results.extend(chunks)
                
                logger.info(f"웹 검색 완료: {len(web_results)}개 결과")
            except Exception as e:
                logger.error(f"웹 검색 실패: {str(e)}")
        
        # 결과 병합
        all_results = vector_results + web_results
        
        # 재순위화
        if rerank and all_results:
            # weighted_similarity 기준으로 정렬
            all_results.sort(key=lambda x: x.get("weighted_similarity", 0), reverse=True)
            
            # 중복 제거 (URL 또는 청크 ID 기준)
            seen_ids = set()
            unique_results = []
            
            for result in all_results:
                # 벡터 DB 결과는 chunk_id로 식별
                if result.get("source") == "vector_db":
                    id_key = result.get("metadata", {}).get("chunk_id", "")
                # 웹 결과는 URL로 식별
                else:
                    id_key = result.get("metadata", {}).get("url", "")
                
                if id_key and id_key not in seen_ids:
                    seen_ids.add(id_key)
                    unique_results.append(result)
            
            all_results = unique_results[:max_results]
        
        # 결과 형식 통일
        final_results = []
        for result in all_results:
            # 결과 구조 통일
            if result.get("source") == "vector_db":
                item = {
                    "text": result.get("text", ""),
                    "similarity": result.get("similarity", 0),
                    "weighted_similarity": result.get("weighted_similarity", 0),
                    "metadata": result.get("metadata", {}),
                    "query_used": result.get("query_used", query),
                    "is_enhanced": result.get("is_enhanced", False),
                    "source": "vector_db"
                }
            else:
                item = {
                    "text": result.get("text", ""),
                    "similarity": result.get("similarity", 0),
                    "weighted_similarity": result.get("weighted_similarity", 0),
                    "metadata": result.get("metadata", {}),
                    "query_used": result.get("query_used", query),
                    "is_enhanced": result.get("is_enhanced", False),
                    "source": "web"
                }
            
            final_results.append(item)
        
        # 최종 결과 구성
        results_data = {
            "query": query,
            "enhanced_queries": queries[1:] if len(queries) > 1 else [],
            "vector_weight": self.vector_weight,
            "web_weight": self.web_weight,
            "results": final_results,
            "vector_results_count": len(vector_results),
            "web_results_count": len(web_results),
            "timestamp": datetime.now().isoformat()
        }
        
        return results_data

def run_test(
    query: str,
    vector_collection: str = None,
    use_web: bool = True,
    use_vector: bool = True,
    enhance_queries: bool = False,
    enhancement_method: str = "hybrid",
    vector_search_method: str = "simple",
    web_provider: str = "serpapi",
    web_weight: float = 0.5,
    max_results: int = 8,
    save_results: bool = True,
    output_file: str = None
):
    """
    통합 RAG 시스템 테스트
    
    Args:
        query: 검색 쿼리
        vector_collection: 벡터 DB 컬렉션 이름
        use_web: 웹 검색 사용 여부
        use_vector: 벡터 DB 검색 사용 여부
        enhance_queries: 쿼리 보강 사용 여부
        enhancement_method: 쿼리 보강 방법
        vector_search_method: 벡터 검색 방법
        web_provider: 웹 검색 제공자
        web_weight: 웹 검색 결과 가중치 (0~1)
        max_results: 최종 반환할 최대 결과 수
        save_results: 결과 저장 여부
        output_file: 결과 저장 파일 (None이면 자동 생성)
    """
    print(f"{Fore.CYAN}===== 통합 RAG 시스템 테스트 ====={Style.RESET_ALL}")
    print(f"{Fore.GREEN}쿼리:{Style.RESET_ALL} {query}")
    print(f"{Fore.GREEN}벡터 DB 사용:{Style.RESET_ALL} {use_vector}")
    print(f"{Fore.GREEN}웹 검색 사용:{Style.RESET_ALL} {use_web}")
    print(f"{Fore.GREEN}벡터 컬렉션:{Style.RESET_ALL} {vector_collection}")
    print(f"{Fore.GREEN}벡터 검색 방법:{Style.RESET_ALL} {vector_search_method}")
    print(f"{Fore.GREEN}웹 검색 제공자:{Style.RESET_ALL} {web_provider}")
    print(f"{Fore.GREEN}웹:벡터 가중치:{Style.RESET_ALL} {web_weight}:{1-web_weight}")
    print("-" * 50)
    
    # API 키 확인
    if use_web:
        if web_provider == "serpapi" and not os.environ.get("SERP_API_KEY"):
            print(f"{Fore.RED}경고: SERP_API_KEY 환경 변수가 설정되지 않았습니다.{Style.RESET_ALL}")
        elif web_provider in ["google", "bing"] and not os.environ.get("SEARCH_API_KEY"):
            print(f"{Fore.RED}경고: SEARCH_API_KEY 환경 변수가 설정되지 않았습니다.{Style.RESET_ALL}")
    
    # 통합 RAG 시스템 초기화
    rag_system = WebIntegratedRAG(
        vector_collection=vector_collection,
        search_provider=web_provider,
        web_weight=web_weight
    )
    
    # 검색 수행
    print(f"{Fore.YELLOW}통합 검색 수행 중...{Style.RESET_ALL}")
    results = rag_system.search(
        query=query,
        use_web=use_web,
        use_vector=use_vector,
        enhance_queries=enhance_queries,
        enhancement_method=enhancement_method,
        vector_search_method=vector_search_method,
        vector_k=max(5, max_results // 2),
        web_max_pages=max(3, max_results // 3),
        rerank=True,
        max_results=max_results
    )
    
    # 결과 분석 및 출력
    print(f"\n{Fore.GREEN}검색 결과:{Style.RESET_ALL}")
    if enhance_queries and results["enhanced_queries"]:
        print(f"{Fore.CYAN}보강된 쿼리:{Style.RESET_ALL}")
        for i, q in enumerate(results["enhanced_queries"]):
            print(f"  {i+1}. {q}")
    
    # 결과 통계
    print(f"\n{Fore.CYAN}결과 통계:{Style.RESET_ALL}")
    print(f"  - 벡터 DB 결과: {results['vector_results_count']}개")
    print(f"  - 웹 검색 결과: {results['web_results_count']}개")
    print(f"  - 최종 결과: {len(results['results'])}개")
    
    # 테이블 형식으로 요약 결과 출력
    table_data = []
    for i, result in enumerate(results["results"]):
        similarity = result.get("similarity", 0)
        weighted_similarity = result.get("weighted_similarity", 0)
        source = result.get("source", "unknown")
        source_color = Fore.BLUE if source == "vector_db" else Fore.GREEN
        
        # 메타데이터에서 정보 추출
        metadata = result.get("metadata", {})
        if source == "vector_db":
            source_info = metadata.get("source", "").split("/")[-1]
            id_info = metadata.get("chunk_id", "")
        else:
            source_info = metadata.get("domain", "")
            id_info = metadata.get("url", "").split("/")[-1]
        
        # 유사도에 따른 색상
        sim_color = Fore.RED
        if similarity >= 0.7:
            sim_color = Fore.GREEN
        elif similarity >= 0.5:
            sim_color = Fore.YELLOW
        
        row = [
            i+1,
            f"{source_color}{source}{Style.RESET_ALL}",
            f"{sim_color}{similarity:.4f}{Style.RESET_ALL}",
            weighted_similarity:.4f,
            source_info,
            result.get("query_used", "")[:20] + ("..." if len(result.get("query_used", "")) > 20 else ""),
            result.get("text", "")[:60] + "..."
        ]
        table_data.append(row)
    
    headers = ["#", "출처", "유사도", "가중치적용", "소스", "사용쿼리", "내용"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="pretty"))
    
    # 상위 3개 결과 상세 출력
    print(f"\n{Fore.CYAN}상위 결과 상세:{Style.RESET_ALL}")
    for i, result in enumerate(results["results"][:3]):
        source = result.get("source", "unknown")
        source_color = Fore.BLUE if source == "vector_db" else Fore.GREEN
        similarity = result.get("similarity", 0)
        query_used = result.get("query_used", "")
        is_enhanced = result.get("is_enhanced", False)
        
        print(f"\n{i+1}. {source_color}[{source}]{Style.RESET_ALL} {Fore.YELLOW}[유사도: {similarity:.4f}]{Style.RESET_ALL}")
        if is_enhanced:
            print(f"   {Fore.CYAN}보강 쿼리:{Style.RESET_ALL} {query_used}")
        
        metadata = result.get("metadata", {})
        if source == "vector_db":
            print(f"   출처: {metadata.get('source', '')}")
            print(f"   청크 ID: {metadata.get('chunk_id', '')}")
        else:
            print(f"   URL: {metadata.get('url', '')}")
            print(f"   도메인: {metadata.get('domain', '')}")
            print(f"   제목: {metadata.get('title', '')}")
        
        print(f"   {Fore.GREEN}내용:{Style.RESET_ALL}")
        print(f"   {result.get('text', '')[:500]}...")
    
    # 결과 저장
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_file or f"integrated_search_results_{timestamp}.json"
        
        # JSON 직렬화를 위해 ANSI 색상 코드 제거
        save_results = results.copy()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n{Fore.GREEN}결과가 {output_file}에 저장되었습니다.{Style.RESET_ALL}")
    
    return results

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="통합 RAG 시스템 테스트")
    
    parser.add_argument('-q', '--query', type=str, required=True,
                      help='검색 쿼리')
    parser.add_argument('-c', '--collection', type=str, default=None,
                      help='벡터 DB 컬렉션 이름')
    parser.add_argument('--no-web', action='store_true',
                      help='웹 검색 비활성화')
    parser.add_argument('--no-vector', action='store_true',
                      help='벡터 DB 검색 비활성화')
    parser.add_argument('-e', '--enhance', action='store_true',
                      help='쿼리 보강 사용')
    parser.add_argument('-m', '--enhancement-method', type=str, default="hybrid",
                      choices=["paraphrasing", "keywords", "semantic", "question", "hybrid"],
                      help='쿼리 보강 방법')
    parser.add_argument('-v', '--vector-method', type=str, default="simple",
                      choices=["simple", "semantic", "hybrid", "mmr", "threshold"],
                      help='벡터 검색 방법')
    parser.add_argument('-p', '--provider', type=str, default="serpapi",
                      choices=["serpapi", "google", "bing"],
                      help='웹 검색 제공자')
    parser.add_argument('-w', '--web-weight', type=float, default=0.5,
                      help='웹 검색 결과 가중치 (0~1)')
    parser.add_argument('-n', '--num-results', type=int, default=8,
                      help='최대 결과 수')
    parser.add_argument('-s', '--save', action='store_true',
                      help='결과 저장 여부')
    parser.add_argument('-o', '--output', type=str, default=None,
                      help='결과 저장 파일')
    
    args = parser.parse_args()
    
    run_test(
        query=args.query,
        vector_collection=args.collection,
        use_web=not args.no_web,
        use_vector=not args.no_vector,
        enhance_queries=args.enhance,
        enhancement_method=args.enhancement_method,
        vector_search_method=args.vector_method,
        web_provider=args.provider,
        web_weight=args.web_weight,
        max_results=args.num_results,
        save_results=args.save,
        output_file=args.output
    )

if __name__ == "__main__":
    main() 