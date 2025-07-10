"""
RAG Manager Module (검색 증강 생성 관리자)

이 모듈은 RAG(Retrieval Augmented Generation)를 위한 다양한 검색 알고리즘을 제공합니다.
context_manager.py에서 생성된 벡터 데이터베이스를 기반으로 상황에 맞는 검색 전략을 적용합니다.

기능:
- 다양한 검색 알고리즘 (Top-K, 임계값 기반, 의미적 윈도우 등)
- 검색 결과 병합 및 후처리
- 대화 맥락에 따른 동적 검색 전략 조정
"""

import os
from typing import List, Dict, Any, Union, Optional, Tuple
import logging

# 조건부 임포트 - chromadb
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("chromadb not available. RAG manager will operate in limited mode.")

# 조건부 임포트 - sentence_transformers
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence_transformers not available. RAG manager will operate in limited mode.")

# 조건부 임포트 - numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available. Advanced numerical operations disabled.")

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGManager:
    """
    RAG(Retrieval Augmented Generation) 관리자 클래스
    
    다양한 검색 알고리즘을 제공하여 상황에 맞는 최적의 컨텍스트를 검색합니다.
    """
    
    def __init__(
        self,
        db_path: str = "./vectordb",
        embedding_model: str = "BAAI/bge-large-en-v1.5"
    ):
        """
        초기화 함수
        
        Args:
            db_path: 벡터 DB 경로
            embedding_model: 임베딩 모델 이름
        """
        self.db_path = db_path
        self.embedding_model_name = embedding_model
        
        # ChromaDB 클라이언트 초기화 (가능한 경우)
        if CHROMADB_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=db_path)
                # 임베딩 함수 초기화
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=embedding_model
                )
                logger.info(f"ChromaDB initialized at {db_path}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {str(e)}")
                self.client = None
                self.embedding_function = None
        else:
            self.client = None
            self.embedding_function = None
            logger.warning("ChromaDB not available. Vector search disabled.")
        
        # 임베딩 모델 로드 (가능한 경우)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                logger.info(f"Embedding model loaded: {embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {str(e)}")
                self.embedding_model = None
        else:
            self.embedding_model = None
            logger.warning("SentenceTransformers not available. Embedding disabled.")
        
        logger.info(f"RAGManager 초기화 완료: DB 경로 {db_path}, 모델 {embedding_model}")
    
    def simple_top_k_search(
        self, 
        collection_name: str, 
        query: str, 
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        간단한 Top-K 검색 수행
        
        주어진 쿼리에 대해 가장 유사한 상위 K개 청크를 반환합니다.
        가장 기본적인 벡터 검색 방식입니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping simple_top_k_search.")
            return []

        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Top-K 검색 실패: {str(e)}")
            raise
    
    def threshold_search(
        self, 
        collection_name: str, 
        query: str,
        threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        임계값 기반 검색
        
        임계값(threshold)보다 높은 유사도를 가진 청크만 반환합니다.
        정확도가 중요한 경우 유용합니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            threshold: 최소 유사도 임계값 (0~1, 높을수록 더 유사한 결과만 포함)
            max_results: 최대 결과 수
            
        Returns:
            임계값을 넘는 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping threshold_search.")
            return []

        try:
            # 일단 max_results만큼 가져옴
            results = self.simple_top_k_search(collection_name, query, max_results)
            
            # 임계값 필터링 (거리는 작을수록 유사, 유사도는 1-거리)
            filtered_results = [r for r in results if (1 - r['distance']) >= threshold]
            
            logger.info(f"임계값 검색 결과: 전체 {len(results)}개 중 {len(filtered_results)}개 임계값 통과")
            return filtered_results
            
        except Exception as e:
            logger.error(f"임계값 검색 실패: {str(e)}")
            raise
    
    def adjacent_chunks_search(
        self, 
        collection_name: str, 
        query: str,
        k: int = 3,
        include_neighbors: bool = True,
        neighbor_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        인접 청크 포함 검색
        
        Top-K 검색 후 각 청크의 앞뒤 청크를 추가로 포함합니다.
        인접 청크 포함 여부는 neighbor_threshold로 제어합니다.
        맥락을 더 잘 파악하기 위한 방법입니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 기본 반환할 결과 수
            include_neighbors: 인접 청크 포함 여부
            neighbor_threshold: 인접 청크 포함 임계값
            
        Returns:
            검색 결과 목록 (인접 청크 포함)
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping adjacent_chunks_search.")
            return []

        try:
            # 기본 검색 수행
            base_results = self.simple_top_k_search(collection_name, query, k)
            
            if not include_neighbors:
                return base_results
            
            # 인접 청크 ID 수집
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            all_chunks = set()
            neighbor_ids = set()
            
            for result in base_results:
                chunk_id = result.get('metadata', {}).get('chunk_id')
                if chunk_id is not None:
                    all_chunks.add(chunk_id)
                    # 앞뒤 청크 ID 추가
                    neighbor_ids.add(f"chunk_{chunk_id - 1}")
                    neighbor_ids.add(f"chunk_{chunk_id + 1}")
            
            # 이미 결과에 있는 청크 ID 제외
            existing_ids = {r.get('metadata', {}).get('chunk_id') for r in base_results}
            neighbor_ids = {nid for nid in neighbor_ids if nid.split('_')[1] not in existing_ids and nid.split('_')[1].isdigit()}
            
            if not neighbor_ids:
                return base_results
            
            # 인접 청크 조회
            neighbors = collection.get(
                ids=list(neighbor_ids),
                include=["documents", "metadatas"]
            )
            
            # 인접 청크 임베딩 계산
            if neighbors['documents']:
                neighbor_embeddings = self.embedding_model.encode(neighbors['documents'])
                query_embedding = self.embedding_model.encode(query)
                
                # 유사도 계산
                similarities = util.dot_score(query_embedding, neighbor_embeddings)[0].tolist()
                
                # 임계값을 넘는 인접 청크만 결과에 추가
                for i, sim in enumerate(similarities):
                    if sim >= neighbor_threshold:
                        neighbor_result = {
                            "text": neighbors['documents'][i],
                            "metadata": neighbors['metadatas'][i] if i < len(neighbors['metadatas']) else {},
                            "distance": 1 - sim,  # 거리로 변환
                            "is_neighbor": True
                        }
                        base_results.append(neighbor_result)
            
            # 청크 ID 순서로 정렬
            base_results.sort(key=lambda x: x.get('metadata', {}).get('chunk_id', float('inf')))
            
            logger.info(f"인접 청크 검색 결과: 기본 {k}개 중 인접 청크 {len(base_results) - k}개 추가")
            return base_results
            
        except Exception as e:
            logger.error(f"인접 청크 검색 실패: {str(e)}")
            raise
    
    def merged_chunks_search(
        self, 
        collection_name: str, 
        query: str,
        k: int = 3,
        merge_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        청크 병합 검색
        
        검색 결과를 가져온 후 의미적으로 유사한 인접 청크를 하나로 병합합니다.
        문맥의 분절을 줄이고 더 자연스러운 컨텍스트를 제공합니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 반환할 결과 수
            merge_threshold: 병합 임계값 (높을수록 더 유사한 청크만 병합)
            
        Returns:
            병합된 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping merged_chunks_search.")
            return []

        try:
            # 인접 청크 포함 검색 수행
            results = self.adjacent_chunks_search(collection_name, query, k, True, 0.5)
            
            # 청크 ID 기준 정렬
            results.sort(key=lambda x: x.get('metadata', {}).get('chunk_id', float('inf')))
            
            merged_results = []
            i = 0
            
            while i < len(results):
                current = results[i]
                merged_text = current['text']
                merged_metadata = current.get('metadata', {}).copy()
                
                j = i + 1
                while j < len(results):
                    next_chunk = results[j]
                    
                    # 현재 청크와 다음 청크가 연속적인지 확인
                    current_id = current.get('metadata', {}).get('chunk_id')
                    next_id = next_chunk.get('metadata', {}).get('chunk_id')
                    
                    if current_id is not None and next_id is not None and abs(next_id - current_id) == 1:
                        # 두 청크의 임베딩 유사도 계산
                        emb1 = self.embedding_model.encode(current['text'])
                        emb2 = self.embedding_model.encode(next_chunk['text'])
                        similarity = util.dot_score(emb1, emb2)[0][0].item()
                        
                        if similarity >= merge_threshold:
                            # 병합 수행
                            merged_text += "\n" + next_chunk['text']
                            merged_metadata['chunk_id'] = f"{current_id}-{next_id}"
                            merged_metadata['chunk_text'] = merged_text[:100] + "..."
                            j += 1
                            continue
                    
                    break
                
                # 병합된 청크 저장
                merged_result = {
                    "text": merged_text,
                    "metadata": merged_metadata,
                    "distance": current['distance'],
                    "merged": j - i > 1
                }
                
                merged_results.append(merged_result)
                i = j
            
            logger.info(f"청크 병합 검색 결과: 원본 {len(results)}개 → 병합 후 {len(merged_results)}개")
            return merged_results
            
        except Exception as e:
            logger.error(f"청크 병합 검색 실패: {str(e)}")
            raise
    
    def semantic_window_search(
        self, 
        collection_name: str, 
        query: str,
        k: int = 3,
        window_size: int = 5,
        window_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        의미적 윈도우 검색
        
        Top-K 검색 후 각 청크 주변에 의미적 윈도우를 형성합니다.
        단순히 인접 청크가 아닌, 의미적으로 관련된 청크들을 동적으로 포함합니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 기본 반환할 결과 수
            window_size: 의미적 윈도우 크기 (앞뒤로 몇 개의 청크를 고려할지)
            window_threshold: 윈도우 포함 임계값
            
        Returns:
            의미적 윈도우 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping semantic_window_search.")
            return []

        try:
            # 기본 검색 수행
            base_results = self.simple_top_k_search(collection_name, query, k)
            
            # 의미적 윈도우 생성을 위한 청크 ID 수집
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            all_chunks = set()
            window_ids = set()
            
            for result in base_results:
                chunk_id = result.get('metadata', {}).get('chunk_id')
                if chunk_id is not None:
                    all_chunks.add(chunk_id)
                    # 윈도우 범위 내 청크 ID 추가
                    for w in range(-window_size, window_size + 1):
                        if w != 0:  # 자기 자신 제외
                            window_ids.add(f"chunk_{chunk_id + w}")
            
            # 이미 결과에 있는 청크 ID 제외
            existing_ids = {str(r.get('metadata', {}).get('chunk_id')) for r in base_results}
            window_ids = {wid for wid in window_ids if wid.split('_')[1] not in existing_ids and wid.split('_')[1].isdigit()}
            
            if not window_ids:
                return base_results
            
            # 윈도우 내 청크 조회
            try:
                window_chunks = collection.get(
                    ids=list(window_ids),
                    include=["documents", "metadatas"]
                )
            except Exception as e:
                logger.warning(f"일부 윈도우 청크를 찾을 수 없음: {str(e)}")
                window_chunks = {"documents": [], "metadatas": []}
            
            # 조회된 청크가 없으면 기본 결과 반환
            if not window_chunks['documents']:
                return base_results
            
            # 윈도우 청크와 쿼리의 의미적 유사도 계산
            window_embeddings = self.embedding_model.encode(window_chunks['documents'])
            query_embedding = self.embedding_model.encode(query)
            
            # 유사도 계산
            similarities = util.dot_score(query_embedding, window_embeddings)[0].tolist()
            
            # 임계값을 넘는 윈도우 청크만 결과에 추가
            window_results = []
            for i, sim in enumerate(similarities):
                if sim >= window_threshold:
                    window_result = {
                        "text": window_chunks['documents'][i],
                        "metadata": window_chunks['metadatas'][i] if i < len(window_chunks['metadatas']) else {},
                        "distance": 1 - sim,  # 거리로 변환
                        "is_window": True
                    }
                    window_results.append(window_result)
            
            # 기본 결과와 윈도우 결과 병합
            combined_results = base_results + window_results
            
            # 유사도 기준 정렬
            combined_results.sort(key=lambda x: x['distance'])
            
            logger.info(f"의미적 윈도우 검색 결과: 기본 {len(base_results)}개 + 윈도우 {len(window_results)}개")
            return combined_results
            
        except Exception as e:
            logger.error(f"의미적 윈도우 검색 실패: {str(e)}")
            raise
    
    def hybrid_search(
        self, 
        collection_name: str, 
        query: str,
        k: int = 3,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (키워드 + 의미적 검색)
        
        벡터 기반 의미적 검색과 키워드 기반 검색을 결합합니다.
        단어 일치와 의미적 유사성을 모두 고려하여 검색의 다양성과 정확성을 높입니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 반환할 결과 수
            semantic_weight: 의미적 검색 가중치 (0~1, 높을수록 의미적 검색 중시)
            
        Returns:
            하이브리드 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping hybrid_search.")
            return []

        try:
            # 벡터 검색 (의미적 검색)
            semantic_results = self.simple_top_k_search(collection_name, query, k*2)
            
            # 키워드 검색을 위한 준비
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            # 쿼리에서 키워드 추출 (간단하게 공백 기준 분리)
            keywords = query.lower().split()
            keywords = [kw for kw in keywords if len(kw) > 3]  # 짧은 단어 제외
            
            if not keywords:
                return semantic_results[:k]
            
            # 전체 문서 가져오기 (실제 구현에서는 인덱싱된 키워드 검색이 효율적)
            all_docs = collection.get(
                limit=100,  # 실제 구현에서는 더 효율적인 방법 필요
                include=["documents", "metadatas", "embeddings"]
            )
            
            # 키워드 기반 점수 계산
            keyword_scores = []
            for i, doc in enumerate(all_docs['documents']):
                doc_lower = doc.lower()
                score = sum(1 for kw in keywords if kw in doc_lower)
                if score > 0:
                    keyword_scores.append({
                        "text": doc,
                        "metadata": all_docs['metadatas'][i] if i < len(all_docs['metadatas']) else {},
                        "keyword_score": score,
                        "id": i
                    })
            
            # 키워드 점수로 정렬
            keyword_scores.sort(key=lambda x: x['keyword_score'], reverse=True)
            keyword_results = keyword_scores[:k*2]
            
            # 하이브리드 결과 계산
            hybrid_results = []
            seen_ids = set()
            
            # 의미적 결과와 키워드 결과 병합
            for sem_res in semantic_results:
                sem_id = sem_res.get('metadata', {}).get('chunk_id')
                if sem_id not in seen_ids:
                    sem_res['hybrid_score'] = (1 - sem_res['distance']) * semantic_weight
                    hybrid_results.append(sem_res)
                    seen_ids.add(sem_id)
            
            for kw_res in keyword_results:
                kw_id = kw_res.get('metadata', {}).get('chunk_id')
                if kw_id not in seen_ids:
                    # 키워드 점수를 0~1 범위로 정규화
                    max_possible_score = len(keywords)
                    normalized_score = kw_res['keyword_score'] / max_possible_score
                    
                    kw_res['distance'] = 1 - normalized_score
                    kw_res['hybrid_score'] = normalized_score * (1 - semantic_weight)
                    hybrid_results.append(kw_res)
                    seen_ids.add(kw_id)
            
            # 하이브리드 점수로 정렬
            hybrid_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            logger.info(f"하이브리드 검색 결과: 의미적 {len(semantic_results)}개 + 키워드 {len(keyword_results)}개 → 병합 {len(hybrid_results)}개")
            return hybrid_results[:k]
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {str(e)}")
            raise

    def mmr_search(
        self, 
        collection_name: str, 
        query: str,
        k: int = 3,
        lambda_param: float = 0.7,
        initial_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        MMR(Maximum Marginal Relevance) 검색
        
        다양성과 관련성의 균형을 맞춘 검색 결과를 제공합니다.
        단순히 가장 유사한 결과만 반환하는 것이 아니라, 결과 간 다양성도 고려합니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            k: 반환할 결과 수
            lambda_param: 다양성-관련성 균형 파라미터 (0~1, 높을수록 관련성 중시)
            initial_results: MMR 계산을 위한 초기 결과 수
            
        Returns:
            MMR 기반 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping mmr_search.")
            return []

        try:
            # 초기 검색 결과 가져오기
            initial_set = self.simple_top_k_search(collection_name, query, initial_results)
            
            # 결과가 k보다 적으면 모두 반환
            if len(initial_set) <= k:
                return initial_set
            
            # 쿼리와 문서들의 임베딩 계산
            query_embedding = self.embedding_model.encode(query)
            doc_embeddings = self.embedding_model.encode([r['text'] for r in initial_set])
            
            # MMR 알고리즘 구현
            selected_indices = []
            selected_embeddings = []
            
            # 첫 번째로 가장 관련성 높은 문서 선택
            similarities = util.dot_score(query_embedding, doc_embeddings)[0]
            # PyTorch 텐서를 NumPy 배열로 변환
            similarities_np = similarities.cpu().numpy()
            best_idx = np.argmax(similarities_np)
            selected_indices.append(best_idx)
            selected_embeddings.append(doc_embeddings[best_idx].reshape(1, -1))
            
            # 나머지 k-1개 문서 선택
            for _ in range(min(k-1, len(initial_set)-1)):
                # 현재까지 선택된 문서들과의 최대 유사도 계산
                remaining_indices = [i for i in range(len(initial_set)) if i not in selected_indices]
                remaining_embeddings = doc_embeddings[remaining_indices]
                
                # 쿼리와의 유사도 계산
                query_sim_tensor = util.dot_score(query_embedding, remaining_embeddings)[0]
                # PyTorch 텐서를 NumPy 배열로 변환
                query_similarities = query_sim_tensor.cpu().numpy()
                
                # 선택된 문서들과의 유사도 계산
                selected_concat = np.concatenate(selected_embeddings, axis=0)
                doc_similarities = util.dot_score(remaining_embeddings, selected_concat)
                
                # PyTorch 텐서를 NumPy 배열로 변환 후 최대값 계산
                doc_similarities_np = doc_similarities.cpu().numpy()
                max_doc_similarities = np.max(doc_similarities_np, axis=1)
                
                # MMR 점수 계산
                mmr_scores = lambda_param * query_similarities - (1 - lambda_param) * max_doc_similarities
                
                # 최대 MMR 점수를 가진 문서 선택
                mmr_idx = np.argmax(mmr_scores)
                selected_idx = remaining_indices[mmr_idx]
                selected_indices.append(selected_idx)
                selected_embeddings.append(doc_embeddings[selected_idx].reshape(1, -1))
            
            # 선택된 인덱스로 최종 결과 생성
            mmr_results = [initial_set[i] for i in selected_indices]
            
            logger.info(f"MMR 검색 결과: 초기 {initial_results}개 → MMR 선택 {len(mmr_results)}개")
            return mmr_results
            
        except Exception as e:
            logger.error(f"MMR 검색 실패: {str(e)}")
            raise
    
    def multi_collection_search(
        self, 
        collection_names: List[str], 
        query: str,
        k_per_collection: int = 2,
        strategy: str = "simple"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        다중 컬렉션 검색
        
        여러 컬렉션에 대해 동시에 검색을 수행합니다.
        각 컬렉션별 결과와 통합 결과를 제공합니다.
        
        Args:
            collection_names: 검색할 컬렉션 이름 목록
            query: 검색 쿼리
            k_per_collection: 컬렉션별 반환할 결과 수
            strategy: 검색 전략 ('simple', 'threshold', 'mmr' 등)
            
        Returns:
            컬렉션별 검색 결과와 통합 결과
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping multi_collection_search.")
            return {}

        try:
            all_results = {}
            
            for collection_name in collection_names:
                # 전략에 따른 검색 수행
                if strategy == "simple":
                    results = self.simple_top_k_search(collection_name, query, k_per_collection)
                elif strategy == "threshold":
                    results = self.threshold_search(collection_name, query, 0.7, k_per_collection)
                elif strategy == "mmr":
                    results = self.mmr_search(collection_name, query, k_per_collection)
                elif strategy == "semantic_window":
                    results = self.semantic_window_search(collection_name, query, k_per_collection)
                elif strategy == "merged":
                    results = self.merged_chunks_search(collection_name, query, k_per_collection)
                else:
                    results = self.simple_top_k_search(collection_name, query, k_per_collection)
                
                # 컬렉션 정보 추가
                for r in results:
                    if 'metadata' in r:
                        r['metadata']['collection'] = collection_name
                
                all_results[collection_name] = results
            
            # 통합 결과 생성
            combined = []
            for collection, results in all_results.items():
                combined.extend(results)
            
            # 유사도순 정렬
            combined.sort(key=lambda x: x['distance'])
            
            all_results['combined'] = combined
            
            logger.info(f"다중 컬렉션 검색 완료: {len(collection_names)}개 컬렉션, 전략 '{strategy}'")
            return all_results
            
        except Exception as e:
            logger.error(f"다중 컬렉션 검색 실패: {str(e)}")
            raise
    
    def conversational_search(
        self, 
        collection_name: str, 
        query: str,
        chat_history: List[str],
        k: int = 3,
        history_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        대화형 검색
        
        현재 쿼리뿐만 아니라 이전 대화 기록을 고려한 검색을 수행합니다.
        대화 맥락에 더 적합한 결과를 찾는 데 유용합니다.
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 현재 검색 쿼리
            chat_history: 이전 대화 목록
            k: 반환할 결과 수
            history_weight: 대화 기록 가중치 (0~1, 높을수록 대화 기록 중시)
            
        Returns:
            대화 맥락을 고려한 검색 결과 목록
        """
        if not self.client or not self.embedding_function:
            logger.warning("ChromaDB or embedding function not available. Skipping conversational_search.")
            return []

        try:
            # 현재 쿼리로 검색
            current_results = self.simple_top_k_search(collection_name, query, k*2)
            
            # 대화 기록이 없으면 현재 쿼리 결과만 반환
            if not chat_history:
                return current_results[:k]
            
            # 대화 기록에서 최근 N개만 사용
            recent_history = chat_history[-3:] if len(chat_history) > 3 else chat_history
            
            # 대화 기록을 하나의 텍스트로 결합
            combined_history = " ".join(recent_history)
            
            # 대화 기록으로 검색
            history_results = self.simple_top_k_search(collection_name, combined_history, k*2)
            
            # 결과 병합을 위한 스코어링
            all_results = {}
            
            # 현재 쿼리 결과 스코어링 (높은 가중치)
            for res in current_results:
                chunk_id = res.get('metadata', {}).get('chunk_id')
                if chunk_id:
                    all_results[chunk_id] = {
                        "data": res,
                        "score": (1 - res['distance']) * (1 - history_weight)
                    }
            
            # 대화 기록 결과 스코어링 (낮은 가중치)
            for res in history_results:
                chunk_id = res.get('metadata', {}).get('chunk_id')
                if chunk_id:
                    if chunk_id in all_results:
                        all_results[chunk_id]["score"] += (1 - res['distance']) * history_weight
                    else:
                        all_results[chunk_id] = {
                            "data": res,
                            "score": (1 - res['distance']) * history_weight
                        }
            
            # 최종 점수로 정렬
            sorted_results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
            final_results = [item["data"] for item in sorted_results[:k]]
            
            logger.info(f"대화형 검색 결과: 현재 쿼리 {len(current_results)}개 + 대화 기록 {len(history_results)}개 → 병합 {len(final_results)}개")
            return final_results
            
        except Exception as e:
            logger.error(f"대화형 검색 실패: {str(e)}")
            raise

    def _format_results(
        self, 
        chroma_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        ChromaDB 결과를 표준 형식으로 변환하는 헬퍼 함수
        
        Args:
            chroma_results: ChromaDB 쿼리 결과
            
        Returns:
            표준화된 결과 목록
        """
        formatted_results = []
        
        for i in range(len(chroma_results['documents'][0])):
            item = {
                "text": chroma_results['documents'][0][i],
                "distance": chroma_results['distances'][0][i],
            }
            
            if 'metadatas' in chroma_results:
                item["metadata"] = chroma_results['metadatas'][0][i]
            
            formatted_results.append(item)
        
        return formatted_results

    def smart_query_strategy(self, query: str, debate_context: Dict[str, Any]) -> List[str]:
        """
        토론 상황에 따라 적절한 RAG 쿼리 전략을 선택하고 최적화합니다.
        
        Args:
            query: 원본 쿼리 문장
            debate_context: 토론 맥락 정보를 담은 사전 (화자, 토론 단계, 화자 입장, 상대방 주장 등)
            
        Returns:
            최적화된 쿼리 목록 (단일 또는 병렬 실행용)
        """
        # 토론 단계에 따른 쿼리 전략 설정
        phase = debate_context.get('phase', 'middle')  # 기본값은 중간 단계
        speaker_position = debate_context.get('position', 'neutral')  # 화자 입장
        speaker_id = debate_context.get('speaker_id', 'user')  # 화자 ID
        opponent_claims = debate_context.get('opponent_claims', [])  # 상대방 주장
        
        optimized_queries = []
        
        # 1. 토론 초기 단계 - 개념 정의와 입장 정립
        if phase == 'initial':
            # 기본 개념과 입장에 초점
            optimized_queries.append(f"{query}의 정의와 핵심 개념")
            
            # 화자 입장에 따른 추가 쿼리
            if speaker_position == 'pro':
                optimized_queries.append(f"{query}의 긍정적 측면과 지지 근거")
            elif speaker_position == 'con':
                optimized_queries.append(f"{query}의 문제점과 비판적 관점")
        
        # 2. 토론 중기 단계 - 주장 심화와 반박
        elif phase == 'middle':
            # 기본 쿼리 유지
            optimized_queries.append(query)
            
            # 철학자 ID에 따른 맞춤형 쿼리
            if speaker_id == 'nietzsche':
                optimized_queries.append(f"니체의 초인 개념과 의지의 힘 관점에서 {query}")
            elif speaker_id == 'camus':
                optimized_queries.append(f"카뮈의 부조리 철학 관점에서 {query}")
            
            # 상대방 주장 반박 쿼리
            if opponent_claims:
                opponent_claim = opponent_claims[0]  # 가장 최근 상대 주장
                optimized_queries.append(f"{opponent_claim}에 대한 반박 논거와 {query}의 연관성")
        
        # 3. 토론 후기 단계 - 종합 및 결론
        elif phase == 'final':
            # 종합적 관점
            optimized_queries.append(f"{query}에 관한 다양한 철학적 관점 종합")
            optimized_queries.append(f"{query}의 미래 전망과 함의")
            
            # 입장 강화
            if speaker_position in ['pro', 'con']:
                optimized_queries.append(f"{query}에 대한 {speaker_position} 입장의 최종 논거 정리")
        
        # 쿼리가 생성되지 않았을 경우 원본 쿼리 사용
        if not optimized_queries:
            return [query]
            
        return optimized_queries
        
    def enhance_query_with_context(self, query: str, context_chunks: List[str], max_enhanced_queries: int = 3) -> List[str]:
        """
        이전 토론 내용(맥락)을 활용하여 쿼리를 향상시킵니다.
        
        Args:
            query: 원본 쿼리
            context_chunks: 토론 맥락 청크 목록
            max_enhanced_queries: 생성할 향상된 쿼리 최대 개수
            
        Returns:
            향상된 쿼리 목록
        """
        if not context_chunks:
            return [query]
            
        # 맥락에서 주요 키워드 추출
        all_context = " ".join(context_chunks)
        # 토론에 등장한 주요 철학적 개념 추출 (여기서는 간단한 접근법 사용)
        key_concepts = self._extract_key_concepts(all_context)
        
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        # 주요 개념 조합으로 쿼리 향상
        for concept in key_concepts[:min(len(key_concepts), max_enhanced_queries-1)]:
            enhanced_queries.append(f"{concept}와(과) {query}의 관계")
            
        return enhanced_queries
        
    def _extract_key_concepts(self, text: str) -> List[str]:
        """
        텍스트에서 주요 철학적 개념을 추출합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 주요 개념 목록
        """
        # 주요 철학 개념 목록 (실제로는 더 정교한 알고리즘 필요)
        concepts = [
            "초인", "의지의 힘", "윌 투 파워", "부조리", "실존", "한계 초월", 
            "불완전성", "인간 본질", "기술적 향상", "트랜스휴머니즘", "시지프스",
            "자기 변형", "정체성", "인간 조건", "윤리적 책임"
        ]
        
        # 텍스트에 등장하는 개념 추출
        found_concepts = []
        for concept in concepts:
            if concept in text:
                found_concepts.append(concept)
                
        return found_concepts
        
    def query_by_debate_phase(self, topic: str, phase: str, speaker_id: str = None, position: str = None) -> List[Dict[str, Any]]:
        """
        토론 단계에 따라 자동으로 적합한 쿼리를 생성하고 실행합니다.
        
        Args:
            topic: 토론 주제
            phase: 토론 단계 ('initial', 'middle', 'final')
            speaker_id: 화자 ID (e.g., 'nietzsche', 'camus')
            position: 화자 입장 ('pro', 'con', 'neutral')
            
        Returns:
            검색 결과 목록
        """
        # 토론 단계별 자동 쿼리 생성
        if phase == 'initial':
            queries = [
                f"{topic}의 정의와 역사적 발전 과정",
                f"{topic}에 관한 주요 철학적 입장들"
            ]
            
            # 화자별 추가 쿼리
            if speaker_id == 'nietzsche':
                queries.append(f"니체의 초인 개념과 {topic}의 연관성")
            elif speaker_id == 'camus':
                queries.append(f"카뮈의 부조리 철학과 {topic}의 관계")
                
        elif phase == 'middle':
            queries = [f"{topic}에 관한 철학적 논쟁"]
            
            # 입장별 추가 쿼리
            if position == 'pro':
                queries.append(f"{topic}을 지지하는 철학적 근거")
            elif position == 'con':
                queries.append(f"{topic}에 대한 비판적 관점")
                
            # 화자별 추가 쿼리
            if speaker_id == 'nietzsche':
                queries.append(f"니체 관점에서 {topic}의 의미")
            elif speaker_id == 'camus':
                queries.append(f"카뮈 관점에서 {topic}의 문제점")
        
        elif phase == 'final':
            queries = [
                f"{topic}에 관한 다양한 입장 종합",
                f"{topic}의 미래 전망과 철학적 함의"
            ]
        
        else:  # 기본 쿼리
            queries = [topic]
            
        # 모든 쿼리에 대해 검색 실행
        all_results = []
        for query in queries:
            results = self.search(query, top_k=self.default_top_k)
            all_results.extend(results)
            
        # 결과 중복 제거 및 관련성 기준 정렬
        unique_results = {}
        for result in all_results:
            # chunk_id로 중복 제거
            chunk_id = result.get('metadata', {}).get('chunk_id', '')
            if chunk_id not in unique_results or result['distance'] < unique_results[chunk_id]['distance']:
                unique_results[chunk_id] = result
                
        # 관련성 기준 정렬
        sorted_results = sorted(unique_results.values(), key=lambda x: x['distance'])
        
        return sorted_results[:self.default_top_k]

    def parallel_search(self, queries: List[str], top_k: int = None) -> List[Dict[str, Any]]:
        """
        여러 쿼리를 병렬로 검색하고 결과를 통합합니다.
        
        Args:
            queries: 검색할 쿼리 목록
            top_k: 각 쿼리별 반환할 최대 결과 수
            
        Returns:
            병합된 검색 결과 목록
        """
        if top_k is None:
            top_k = self.default_top_k
        
        # 모든 쿼리에 대해 검색 실행
        all_results = []
        for query in queries:
            results = self.search(query, top_k=top_k)
            all_results.extend(results)
            
        # 결과 중복 제거 및 관련성 기준 정렬
        unique_results = {}
        for result in all_results:
            # chunk_id로 중복 제거
            chunk_id = result.get('metadata', {}).get('chunk_id', '')
            if chunk_id not in unique_results or result['distance'] < unique_results[chunk_id]['distance']:
                unique_results[chunk_id] = result
                
        # 관련성 기준 정렬
        sorted_results = sorted(unique_results.values(), key=lambda x: x['distance'])
        
        return sorted_results[:top_k]
        
    async def parallel_search_async(self, queries: List[str], top_k: int = None) -> List[Dict[str, Any]]:
        """
        여러 쿼리를 비동기 병렬로 검색하고 결과를 통합합니다.
        
        Args:
            queries: 검색할 쿼리 목록
            top_k: 각 쿼리별 반환할 최대 결과 수
            
        Returns:
            병합된 검색 결과 목록
        """
        import asyncio
        
        if top_k is None:
            top_k = self.default_top_k
        
        # 각 쿼리에 대한 비동기 검색 함수
        async def async_search(query):
            # 비동기 실행을 위해 검색 작업을 별도 스레드에서 실행
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: self.search(query, top_k=top_k))
        
        # 모든 쿼리를 비동기로 실행
        tasks = [async_search(query) for query in queries]
        results_list = await asyncio.gather(*tasks)
        
        # 모든 결과 병합
        all_results = []
        for results in results_list:
            all_results.extend(results)
            
        # 결과 중복 제거 및 관련성 기준 정렬
        unique_results = {}
        for result in all_results:
            # chunk_id로 중복 제거
            chunk_id = result.get('metadata', {}).get('chunk_id', '')
            if chunk_id not in unique_results or result['distance'] < unique_results[chunk_id]['distance']:
                unique_results[chunk_id] = result
                
        # 관련성 기준 정렬
        sorted_results = sorted(unique_results.values(), key=lambda x: x['distance'])
        
        return sorted_results[:top_k]
        
    def debate_dynamic_search(self, 
                            query: str, 
                            debate_context: Dict[str, Any], 
                            use_async: bool = False,
                            pre_processing: bool = True) -> List[Dict[str, Any]]:
        """
        토론 상황에 맞게 동적으로 쿼리를 최적화하고 검색을 수행합니다.
        
        Args:
            query: 원본 쿼리
            debate_context: 토론 맥락 정보
            use_async: 비동기 병렬 처리 사용 여부
            pre_processing: 쿼리 전처리 수행 여부
            
        Returns:
            검색 결과 목록
        """
        # 1. 토론 상황에 맞게 쿼리 최적화
        optimized_queries = self.smart_query_strategy(query, debate_context)
        
        # 2. 맥락 정보로 쿼리 향상 (옵션)
        if pre_processing and 'context_chunks' in debate_context:
            context_chunks = debate_context['context_chunks']
            enhanced_queries = self.enhance_query_with_context(query, context_chunks)
            # 원본 쿼리와 향상된 쿼리 병합 (중복 제거)
            all_queries = list(set(optimized_queries + enhanced_queries))
        else:
            all_queries = optimized_queries
            
        # 3. 로깅
        logger.info(f"Original query: {query}")
        logger.info(f"Optimized queries: {all_queries}")
        
        # 4. 비동기 또는 동기 검색 수행
        if use_async:
            import asyncio
            # 비동기 실행을 위한 래퍼 함수
            async def run_async():
                return await self.parallel_search_async(all_queries)
                
            # 이미 이벤트 루프가 있으면 그대로 사용, 없으면 새로 생성
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 이미 실행 중인 이벤트 루프가 있는 경우 Future 사용
                    future = asyncio.run_coroutine_threadsafe(run_async(), loop)
                    results = future.result()
                else:
                    results = loop.run_until_complete(run_async())
            except RuntimeError:
                # 이벤트 루프가 없는 경우 새로 생성
                results = asyncio.run(run_async())
        else:
            # 동기 처리
            results = self.parallel_search(all_queries)
            
        return results 

    def pre_compute_debate_queries(self, 
                                debate_topic: str, 
                                current_turn: int, 
                                total_turns: int,
                                speakers: List[Dict[str, Any]],
                                debate_history: List[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        토론의 다음 단계를 예측하여 미리 RAG 쿼리를 실행하고 결과를 캐시합니다.
        
        Args:
            debate_topic: 토론 주제
            current_turn: 현재 토론 턴 번호
            total_turns: 전체 토론 턴 수
            speakers: 토론 참가자 정보 [{id, name, position}, ...]
            debate_history: 지금까지의 토론 내용
            
        Returns:
            예측 쿼리별 결과 사전 (캐시)
        """
        # 토론 단계 결정
        if current_turn < total_turns * 0.3:
            phase = 'initial'
        elif current_turn < total_turns * 0.7:
            phase = 'middle'
        else:
            phase = 'final'
            
        # 다음 단계에 예상되는 토론자 결정
        next_speaker_idx = current_turn % len(speakers)
        next_speaker = speakers[next_speaker_idx]
        
        # 상대방 마지막 주장 추출
        opponent_claims = []
        if debate_history:
            # 마지막 발언자와 다른 사람들의 최근 발언 찾기
            for entry in reversed(debate_history):
                if entry.get('speaker_id') != next_speaker['id'] and 'text' in entry:
                    opponent_claims.append(entry['text'])
                    break
        
        # 다음 발언자의 맥락 정보
        debate_context = {
            'phase': phase,
            'position': next_speaker['position'],
            'speaker_id': next_speaker['id'],
            'opponent_claims': opponent_claims,
            'context_chunks': [entry.get('text', '') for entry in debate_history[-5:] if 'text' in entry] if debate_history else []
        }
        
        # 예측 쿼리 생성 및 결과 캐싱
        cached_results = {}
        
        # 1. 일반적인 토론 주제 관련 쿼리
        topic_query = f"{debate_topic}에 관한 철학적 관점"
        cached_results['topic'] = self.search(topic_query)
        
        # 2. 토론자 입장 기반 쿼리
        position_query = f"{debate_topic}에 대한 {next_speaker['position']} 관점"
        cached_results['position'] = self.search(position_query)
        
        # 3. 화자 ID 기반 쿼리 (철학자별 특화 쿼리)
        if next_speaker['id'] == 'nietzsche':
            speaker_query = f"니체의 관점에서 {debate_topic}"
            cached_results['speaker'] = self.search(speaker_query)
        elif next_speaker['id'] == 'camus':
            speaker_query = f"카뮈의 관점에서 {debate_topic}"
            cached_results['speaker'] = self.search(speaker_query)
        
        # 4. 상대방 주장 반박 관련 쿼리
        if opponent_claims:
            claim_keywords = self._extract_key_concepts(opponent_claims[0])
            if claim_keywords:
                rebuttal_query = f"{claim_keywords[0]}에 대한 {next_speaker['id']} 관점의 반박 논거"
                cached_results['rebuttal'] = self.search(rebuttal_query)
        
        # 5. 토론 단계별 맞춤 쿼리
        phase_queries = self.smart_query_strategy(debate_topic, debate_context)
        phase_results = self.parallel_search(phase_queries)
        cached_results['phase'] = phase_results
        
        logger.info(f"Pre-computed RAG queries for {next_speaker['name']} (Turn {current_turn+1}/{total_turns})")
        
        return cached_results
        
    def get_cached_results(self, cache: Dict[str, List[Dict[str, Any]]], query: str) -> List[Dict[str, Any]]:
        """
        캐시된 결과에서 쿼리와 가장 관련성 높은 결과를 반환합니다.
        
        Args:
            cache: 캐시된 결과 사전
            query: 현재 쿼리
            
        Returns:
            가장 관련성 높은 캐시 결과
        """
        if not cache:
            return []
            
        # 쿼리 키워드 추출
        query_keywords = set(query.lower().split())
        
        # 가장 적합한 캐시 결과 선택
        best_match_key = None
        best_match_score = 0
        
        for key in cache.keys():
            if key == 'phase':  # phase는 항상 포함
                continue
                
            # 키워드 겹침 점수 계산
            key_words = set(key.lower().split())
            common_words = query_keywords.intersection(key_words)
            match_score = len(common_words) / max(len(query_keywords), 1)
            
            if match_score > best_match_score:
                best_match_score = match_score
                best_match_key = key
        
        # 결과 병합 (phase 결과 + 가장 일치하는 결과)
        combined_results = []
        
        # phase 결과 항상 포함
        if 'phase' in cache:
            combined_results.extend(cache['phase'])
            
        # 가장 일치하는 결과 포함
        if best_match_key and best_match_score > 0.3:  # 30% 이상 일치시에만
            combined_results.extend(cache[best_match_key])
            
        # 중복 제거 및 정렬
        unique_results = {}
        for result in combined_results:
            chunk_id = result.get('metadata', {}).get('chunk_id', '')
            if chunk_id not in unique_results or result['distance'] < unique_results[chunk_id]['distance']:
                unique_results[chunk_id] = result
                
        sorted_results = sorted(unique_results.values(), key=lambda x: x['distance'])
        
        return sorted_results[:self.default_top_k] 