"""
RAG 실험 파이프라인 코어 구현

다양한 RAG 알고리즘과 파라미터 조합을 자동화된 방식으로 실행하고 평가하는 파이프라인
"""

import os
import sys
import json
import glob
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 설정
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent.absolute()
sys.path.append(str(project_root))

# 로컬 모듈 임포트
from experiments.rag.config import ExperimentConfig
from experiments.rag.metrics import ExperimentMetrics, PerformanceTimer

# sapiens_engine 모듈 임포트
try:
    from sapiens_engine.retrieval.web_retriever import WebSearchRetriever
    from sapiens_engine.core.rag_manager import RAGManager
    from sapiens_engine.core.context_manager import ContextManager
    from sapiens_engine.core.query_enhancer import QueryEnhancer
except ImportError as e:
    logging.error(f"sapiens_engine 패키지를 찾을 수 없습니다: {str(e)}")
    raise


class ExperimentPipeline:
    """
    RAG 실험 파이프라인
    
    다양한 RAG 설정에 대한 실험을 실행하고 결과를 측정하는 파이프라인
    """
    
    def __init__(self, base_output_dir: str = './experiment_results'):
        """
        초기화
        
        Args:
            base_output_dir: 실험 결과를 저장할 기본 디렉토리
        """
        self.base_output_dir = base_output_dir
        self.logger = self._setup_logger()
        
        # 결과 디렉토리 생성
        os.makedirs(base_output_dir, exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger("rag_experiments")
        logger.setLevel(logging.INFO)
        
        # 로그 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러
        log_dir = Path(self.base_output_dir) / "logs"
        log_dir.mkdir(exist_ok=True, parents=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"rag_experiments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
        
    def run_experiment(self, config: ExperimentConfig) -> Dict[str, Any]:
        """
        단일 실험 설정 실행
        
        Args:
            config: 실험 설정
            
        Returns:
            실험 결과
        """
        self.logger.info(f"실험 시작: {config.name} (ID: {config.experiment_id})")
        
        # 현재 날짜 및 시간 가져오기
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 실험 결과 저장 디렉토리 (이름을 "config 파일 이름 - 날짜시간" 형식으로 변경)
        config_name = config.name.replace(' ', '_')
        experiment_dir_name = f"{config_name}-{timestamp}"
        experiment_dir = os.path.join(self.base_output_dir, experiment_dir_name)
        os.makedirs(experiment_dir, exist_ok=True)
        
        # 원래 experiment_id를 메타데이터로 유지
        original_id = config.experiment_id
        
        # 설정 저장
        config_path = os.path.join(experiment_dir, 'config.json')
        config.save(config_path)
        
        # 결과 및 성능 측정 초기화
        results = {
            "experiment_id": config.experiment_id,
            "experiment_dir": experiment_dir_name,
            "name": config.name,
            "description": config.description,
            "timestamp": datetime.now().isoformat(),
            "config": config.to_dict(),
            "query_results": [],
            "metrics": {},
            "token_usage": {}
        }
        
        # 성능 타이머 초기화
        timer = PerformanceTimer()
        timer.start()
        
        try:
            # RAG 구성요소 초기화
            components = self._initialize_components(config)
            timer.checkpoint("initialization")
            
            # 쿼리 처리 실행
            self.logger.info(f"쿼리 처리 시작: {len(config.test_queries)}개 쿼리")
            
            for query_idx, query in enumerate(config.test_queries):
                query_timer = PerformanceTimer()
                query_timer.start()
                
                self.logger.info(f"쿼리 {query_idx+1}/{len(config.test_queries)}: {query}")
                
                # 쿼리 강화 적용
                enhanced_query = self._enhance_query(query, components, config)
                query_timer.checkpoint("query_enhancement")
                
                # 검색 실행
                retrieval_results = self._run_retrieval(enhanced_query, components, config)
                query_timer.checkpoint("retrieval")
                
                # 쿼리 결과 및 메트릭 저장
                query_metrics = ExperimentMetrics.calculate_similarity_metrics(retrieval_results)
                performance_metrics = ExperimentMetrics.calculate_performance_metrics(
                    query_timer.start_time, 
                    query_timer.get_checkpoint_time("retrieval")
                )
                
                query_result = {
                    "query": query,
                    "enhanced_query": enhanced_query,
                    "retrieval_results": retrieval_results,
                    "metrics": {**query_metrics, **performance_metrics},
                    "timing": query_timer.get_all_intervals()
                }
                
                results["query_results"].append(query_result)
                query_timer.stop()
                
            # 실험 종료 및 메트릭 집계
            timer.stop()
            results["timing"] = timer.get_all_intervals()
            results["metrics"] = self._aggregate_metrics(results["query_results"])
            results["metrics"]["total_execution_time"] = timer.get_execution_time()
            
            # 결과 저장
            results_path = os.path.join(experiment_dir, 'results.json')
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"실험 완료: {config.name} (소요 시간: {timer.get_execution_time():.2f}초)")
            self.logger.info(f"결과 저장 경로: {experiment_dir}")
            return results
            
        except Exception as e:
            self.logger.error(f"실험 실행 중 오류 발생: {str(e)}", exc_info=True)
            
            # 부분적 결과라도 저장
            timer.stop()
            results["error"] = str(e)
            results["timing"] = timer.get_all_intervals()
            
            error_path = os.path.join(experiment_dir, 'error_results.json')
            with open(error_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"오류 결과 저장 경로: {experiment_dir}")
            return results
    
    def run_experiment_suite(self, configs_dir: str) -> List[Dict[str, Any]]:
        """
        여러 실험 구성을 순차적으로 실행
        
        Args:
            configs_dir: 실험 설정 파일이 있는 디렉토리
            
        Returns:
            실험 결과 목록
        """
        self.logger.info(f"실험 스위트 시작: {configs_dir}")
        
        # 설정 파일 찾기
        config_files = glob.glob(os.path.join(configs_dir, "*.yaml"))
        if not config_files:
            config_files = glob.glob(os.path.join(configs_dir, "*.json"))
            
        if not config_files:
            self.logger.warning(f"설정 파일을 찾을 수 없음: {configs_dir}")
            return []
            
        self.logger.info(f"{len(config_files)}개 실험 설정 파일 발견")
        
        # 각 설정 파일에 대한 실험 실행
        all_results = []
        
        for config_file in sorted(config_files):
            self.logger.info(f"설정 파일 로드: {config_file}")
            
            if config_file.endswith(".yaml"):
                config = ExperimentConfig.from_yaml(config_file)
            else:
                config = ExperimentConfig.load(config_file)
                
            result = self.run_experiment(config)
            all_results.append(result)
            
        self.logger.info(f"실험 스위트 완료: {len(all_results)}개 실험 실행됨")
        return all_results
    
    def _initialize_components(self, config: ExperimentConfig) -> Dict[str, Any]:
        """
        RAG 구성요소 초기화
        
        Args:
            config: 실험 설정
            
        Returns:
            초기화된 구성요소 사전
        """
        self.logger.info("RAG 구성요소 초기화")
        components = {}
        
        # 임베딩 모델 설정
        components["embedding_model"] = config.embedding_model
        components["query_embedding_model"] = config.query_embedding_model or config.embedding_model
        components["doc_embedding_model"] = config.doc_embedding_model or config.embedding_model
        
        # 문서 데이터 로드 및 처리
        if config.data_sources:
            self.logger.info(f"{len(config.data_sources)}개 데이터 소스 로드")
            
            # ContextManager 초기화 (문서 청크화 담당)
            context_manager = ContextManager(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                chunking_method=config.chunking_strategy,  # chunking_strategy를 chunking_method로 매핑
                db_path="./vectordb",  # 벡터 DB 저장 경로
                embedding_model=components["doc_embedding_model"]
            )
            components["context_manager"] = context_manager
            
            # 문서 로드 및 청크화
            for source in config.data_sources:
                try:
                    # 파일 경로 확인
                    if os.path.isfile(source):
                        # 파일 확장자 확인
                        if source.lower().endswith('.pdf'):
                            # PDF 파일 처리
                            collection_name = context_manager.process_file(source)
                        elif source.lower().endswith(('.txt', '.md')):
                            # 텍스트 파일 읽기
                            with open(source, 'r', encoding='utf-8') as f:
                                text = f.read()
                            # 텍스트 처리
                            collection_name = context_manager.process_text(
                                text, 
                                source_id=os.path.basename(source)
                            )
                        else:
                            self.logger.warning(f"지원되지 않는 파일 형식: {source}")
                            continue
                    # URL 처리
                    elif source.startswith(('http://', 'https://')):
                        collection_name = context_manager.process_url(source)
                    else:
                        self.logger.warning(f"지원되지 않는 소스 형식: {source}")
                        continue
                        
                    self.logger.info(f"로드됨: {source} (컬렉션: {collection_name})")
                    
                except Exception as e:
                    self.logger.error(f"데이터 소스 로드 실패: {source} - {str(e)}")
            
            # 컬렉션 목록 확인
            collections = context_manager.list_collections()
            self.logger.info(f"총 {len(collections)}개 컬렉션이 생성됨")
        else:
            self.logger.warning("데이터 소스가 지정되지 않음")
        
        # 쿼리 강화 설정
        if config.query_enhancement:
            self.logger.info(f"쿼리 강화 활성화: {config.enhancement_type}")
            
            query_enhancer = QueryEnhancer(
                enhancement_type=config.enhancement_type,
                model=config.enhancement_model
            )
            components["query_enhancer"] = query_enhancer
            
        # 웹 검색 설정
        if config.web_search_enabled:
            self.logger.info(f"웹 검색 활성화: {config.search_provider}")
            
            web_retriever = WebSearchRetriever(
                embedding_model=components["query_embedding_model"],
                search_provider=config.search_provider,
                max_results=config.max_results
            )
            components["web_retriever"] = web_retriever
        
        # RAG 매니저 초기화
        rag_manager = RAGManager()
        components["rag_manager"] = rag_manager
        
        return components
    
    def _enhance_query(self, 
                      query: str, 
                      components: Dict[str, Any],
                      config: ExperimentConfig) -> str:
        """
        쿼리 강화 적용
        
        Args:
            query: 원본 쿼리
            components: 초기화된 구성요소
            config: 실험 설정
            
        Returns:
            강화된 쿼리
        """
        if not config.query_enhancement:
            return query
            
        try:
            query_enhancer = components.get("query_enhancer")
            if not query_enhancer:
                return query
                
            enhanced_query = query_enhancer.enhance_query(
                query=query,
                enhancement_type=config.enhancement_type,
                num_expansions=config.expansion_terms
            )
            
            self.logger.info(f"쿼리 강화: '{query}' -> '{enhanced_query}'")
            return enhanced_query
            
        except Exception as e:
            self.logger.error(f"쿼리 강화 실패: {str(e)}")
            return query
    
    def _run_retrieval(self, 
                      query: str, 
                      components: Dict[str, Any],
                      config: ExperimentConfig) -> List[Dict[str, Any]]:
        """
        검색 실행
        
        Args:
            query: 쿼리 (강화된 쿼리가 있으면 해당 쿼리)
            components: 초기화된 구성요소
            config: 실험 설정
            
        Returns:
            검색 결과
        """
        results = []
        
        # 로컬 문서 검색
        if "context_manager" in components and "rag_manager" in components:
            context_manager = components["context_manager"]
            rag_manager = components["rag_manager"]
            
            # 컬렉션 목록 가져오기
            collections = context_manager.list_collections()
            
            if collections:
                local_results = []
                for collection_name in collections:
                    # 각 컬렉션에서 검색 실행
                    collection_results = []
                    
                    # 선택된 검색 알고리즘에 따라 RAGManager 메서드 호출
                    if config.search_algorithm == "top_k":
                        self.logger.info(f"Top-{config.top_k} 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.simple_top_k_search(
                            collection_name=collection_name,
                            query=query, 
                            k=config.top_k
                        )
                    elif config.search_algorithm == "threshold":
                        self.logger.info(f"임계값 {config.similarity_threshold} 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.threshold_search(
                            collection_name=collection_name,
                            query=query,
                            threshold=config.similarity_threshold,
                            max_results=config.top_k
                        )
                    elif config.search_algorithm == "adjacent_chunks":
                        self.logger.info(f"인접 청크 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.adjacent_chunks_search(
                            collection_name=collection_name,
                            query=query,
                            k=config.top_k,
                            include_neighbors=True,
                            neighbor_threshold=config.neighbor_threshold
                        )
                    elif config.search_algorithm == "merged_chunks":
                        self.logger.info(f"병합 청크 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.merged_chunks_search(
                            collection_name=collection_name,
                            query=query,
                            k=config.top_k,
                            merge_threshold=config.similarity_threshold
                        )
                    elif config.search_algorithm == "semantic_window":
                        self.logger.info(f"의미적 윈도우 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.semantic_window_search(
                            collection_name=collection_name,
                            query=query,
                            k=config.top_k,
                            window_size=config.window_size,
                            window_threshold=config.window_threshold
                        )
                    elif config.search_algorithm == "hybrid":
                        self.logger.info(f"하이브리드 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.hybrid_search(
                            collection_name=collection_name,
                            query=query,
                            k=config.top_k,
                            semantic_weight=config.semantic_weight
                        )
                    elif config.search_algorithm == "mmr":
                        self.logger.info(f"MMR 검색 실행 (컬렉션: {collection_name})")
                        collection_results = rag_manager.mmr_search(
                            collection_name=collection_name,
                            query=query,
                            k=config.top_k,
                            lambda_param=config.lambda_param,
                            initial_results=config.initial_results
                        )
                    elif config.search_algorithm == "conversational":
                        self.logger.info(f"대화형 검색 실행 (컬렉션: {collection_name})")
                        # 대화 이력이 필요하지만 현재 구현에서는 사용할 수 없으므로 빈 리스트 전달
                        collection_results = rag_manager.conversational_search(
                            collection_name=collection_name,
                            query=query,
                            chat_history=[],
                            k=config.top_k,
                            history_weight=config.history_weight
                        )
                    else:  # 기본값: top_k
                        self.logger.warning(f"알 수 없는 검색 알고리즘: {config.search_algorithm}, top_k 사용")
                        collection_results = rag_manager.simple_top_k_search(
                            collection_name=collection_name,
                            query=query, 
                            k=config.top_k
                        )
                    
                    # 결과를 로컬 결과 목록에 추가
                    for result in collection_results:
                        local_results.append({
                            "text": result["text"],
                            "metadata": result.get("metadata", {}),
                            "score": 1.0 - result.get("distance", 0),  # distance를 유사도 점수로 변환
                            "source": "local",
                            "similarity": 1.0 - result.get("distance", 0)  # distance를 유사도 점수로 변환
                        })
                
                # 스코어 기준으로 정렬하고 상위 결과만 선택
                local_results = sorted(local_results, key=lambda x: x.get("score", 0), reverse=True)
                if config.top_k > 0:
                    local_results = local_results[:config.top_k]
                
                results.extend(local_results)
                self.logger.info(f"로컬 검색 결과: {len(local_results)}개")
        
        # 웹 검색
        if config.web_search_enabled and "web_retriever" in components:
            web_retriever = components["web_retriever"]
            
            try:
                # advanced_scoring 옵션 확인 및 전달
                advanced_scoring = getattr(config, 'advanced_scoring', False)
                self.logger.info(f"웹 검색 시작 (고급 점수 계산: {'활성화' if advanced_scoring else '비활성화'})")
                
                web_results = web_retriever.retrieve_and_extract(
                    query=query,
                    max_pages=config.max_results,
                    chunk_size=config.chunk_size,
                    chunk_overlap=config.chunk_overlap,
                    rerank=True
                )
                
                # 웹 검색 결과 처리 개선
                web_filtered = []
                for result in web_results:
                    # 이미 source 필드가 있을 수도 있지만, 명시적으로 재설정
                    result["source"] = "web"
                    
                    # similarity 필드가 없는 경우 추가 (웹 검색 결과의 경우 similarity는 벡터 유사도)
                    if "similarity" not in result:
                        similarity = result.get("score", 0)
                        result["similarity"] = similarity
                    
                    # score 필드 없으면 추가
                    if "score" not in result and "similarity" in result:
                        # 고급 점수 계산 비활성화 시에만 similarity를 score로 사용
                        if not advanced_scoring:
                            result["score"] = result["similarity"]
                        
                    # 최소 유사도 이상의 결과만 추가
                    min_sim_threshold = 0.5  # 기본 최소 유사도 기준
                    if result.get("similarity", 0) >= min_sim_threshold:
                        web_filtered.append(result)
                
                if web_filtered:
                    # 고급 점수 계산 상태 출력
                    if advanced_scoring:
                        # 점수 차이 비교 출력
                        for i, result in enumerate(web_filtered[:3]):  # 처음 3개만 출력
                            sim = result.get("similarity", 0)
                            score = result.get("score", 0)
                            diff = score - sim
                            self.logger.info(f"  결과 {i+1}: similarity={sim:.4f}, score={score:.4f}, 차이={diff:.4f}")
                    
                    self.logger.info(f"웹 검색 결과: {len(web_filtered)}개 (필터링 후)")
                    results.extend(web_filtered)
                else:
                    self.logger.warning(f"웹 검색 결과: {len(web_results)}개 검색됨, 하지만 최소 유사도 기준을 충족하는 결과 없음")
                
            except Exception as e:
                self.logger.error(f"웹 검색 실패: {str(e)}")
        
        # 결과 융합 및 재정렬
        if config.fusion_strategy == "weighted" and "local" in [r.get("source") for r in results] and "web" in [r.get("source") for r in results]:
            self.logger.info(f"가중치 기반 융합: 로컬({config.local_weight}) + 웹({config.web_weight})")
            
            # 가중치 적용
            for result in results:
                if result.get("source") == "local":
                    result["weighted_score"] = result.get("similarity", 0) * config.local_weight
                else:  # web
                    result["weighted_score"] = result.get("similarity", 0) * config.web_weight
            
            # 재정렬
            results = sorted(results, key=lambda x: x.get("weighted_score", 0), reverse=True)
            
            # 상위 결과만 유지
            if config.top_k > 0 and len(results) > config.top_k:
                results = results[:config.top_k]
        
        return results
    
    def _aggregate_metrics(self, query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        전체 쿼리에 대한 메트릭 집계
        
        Args:
            query_results: 쿼리별 결과 목록
            
        Returns:
            집계된 메트릭
        """
        if not query_results:
            return {}
            
        # 유사도 메트릭 집계
        top_similarities = [r["metrics"].get("top_chunk_similarity", 0) for r in query_results]
        avg_similarities = [r["metrics"].get("avg_similarity", 0) for r in query_results]
        
        # 성능 메트릭 집계
        exec_times = [r["metrics"].get("execution_time", 0) for r in query_results]
        
        return {
            "avg_top_similarity": sum(top_similarities) / len(top_similarities) if top_similarities else 0,
            "min_top_similarity": min(top_similarities) if top_similarities else 0,
            "max_top_similarity": max(top_similarities) if top_similarities else 0,
            "avg_similarity": sum(avg_similarities) / len(avg_similarities) if avg_similarities else 0,
            "avg_exec_time": sum(exec_times) / len(exec_times) if exec_times else 0,
            "total_queries": len(query_results)
        } 