"""
Vector Store Module for Debate Dialogues

토론 대화에서 컨텍스트 검색을 위한 벡터 저장소 모듈.
Sentence-Transformers 및 FAISS를 사용하여 의미적 유사성 기반 검색을 제공합니다.
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# 선택적 의존성 임포트
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence_transformers not available. Vector store will operate in limited mode.")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("faiss-cpu not available. Vector store will operate in limited mode.")
    FAISS_AVAILABLE = False


class VectorStore:
    """
    토론 대화에서 컨텍스트 관리를 위한 벡터 저장소
    
    Attributes:
        model_name (str): 사용할 Sentence-Transformers 모델 이름
        model: 임베딩 생성에 사용되는 모델 인스턴스
        documents (List[Dict]): 저장된 문서 리스트
        index: FAISS 인덱스 (활성화된 경우)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", store_path: str = "data/debate_vector_store"):
        """
        벡터 저장소 초기화
        
        Args:
            model_name: 사용할 임베딩 모델 이름
            store_path: 벡터 저장소가 저장될 경로
        """
        self.model_name = model_name
        self.store_path = store_path
        self.documents = []
        self.index = None
        self.model = None
        
        # 디렉토리 생성
        os.makedirs(store_path, exist_ok=True)
        
        # 모델 초기화 (가능한 경우)
        self._initialize_model()
        
        logger.info(f"Initialized Vector Store with model {model_name}")
    
    def _initialize_model(self):
        """임베딩 모델 초기화"""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(self.model_name)
                
                # FAISS 인덱스 초기화 (가능한 경우)
                if FAISS_AVAILABLE:
                    # 모델의 출력 차원 확인
                    embedding_dim = self.model.get_sentence_embedding_dimension()
                    # 표준 L2 정규화된 인덱스 생성
                    self.index = faiss.IndexFlatIP(embedding_dim)
                    logger.info(f"Initialized FAISS index with dimension {embedding_dim}")
                
                logger.info(f"Initialized embedding model {self.model_name}")
            except Exception as e:
                logger.error(f"Error initializing model: {str(e)}")
                self.model = None
        else:
            logger.warning("Sentence-Transformers not available. Using fallback methods.")
    
    def add_documents(self, texts: Union[str, List[str]], metadata: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        문서 추가
        
        Args:
            texts: 추가할 텍스트 또는 텍스트 리스트
            metadata: 각 텍스트에 대응하는 메타데이터 리스트 (선택 사항)
        """
        # 단일 문서 처리
        if isinstance(texts, str):
            texts = [texts]
            if metadata is not None and not isinstance(metadata, list):
                metadata = [metadata]
        
        # 메타데이터 없으면 빈 딕셔너리로 초기화
        if metadata is None:
            metadata = [{} for _ in texts]
        
        if len(metadata) != len(texts):
            logger.warning(f"Metadata count ({len(metadata)}) does not match text count ({len(texts)}). Using empty metadata.")
            metadata = [{} for _ in texts]
        
        # 모델이 없으면 텍스트만 저장
        if self.model is None:
            for i, text in enumerate(texts):
                doc_id = len(self.documents)
                self.documents.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata[i]
                })
            logger.info(f"Added {len(texts)} documents without embeddings")
            return
        
        # 임베딩 생성
        try:
            embeddings = self.model.encode(texts)
            if FAISS_AVAILABLE and self.index is not None:
                # FAISS 인덱스에 추가
                faiss.normalize_L2(np.array(embeddings, dtype=np.float32))
                self.index.add(np.array(embeddings, dtype=np.float32))
            
            # 문서 저장
            start_id = len(self.documents)
            for i, text in enumerate(texts):
                doc_id = start_id + i
                self.documents.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata[i],
                    'embedding': embeddings[i] if not FAISS_AVAILABLE else None  # FAISS 사용 시 중복 저장 방지
                })
            
            logger.info(f"Added {len(texts)} documents with embeddings")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            # 오류 시 텍스트만 저장
            for i, text in enumerate(texts):
                doc_id = len(self.documents)
                self.documents.append({
                    'id': doc_id,
                    'text': text,
                    'metadata': metadata[i]
                })
            logger.warning(f"Added {len(texts)} documents without embeddings due to error")
    
    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            limit: 반환할 최대 결과 수
            
        Returns:
            유사도 점수와 함께 검색된 문서 리스트
        """
        if not self.documents:
            logger.warning("Vector store is empty. No search results.")
            return []
        
        # 모델이 없으면 키워드 검색으로 폴백
        if self.model is None:
            return self._keyword_search(query, limit)
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.model.encode(query)
            
            if FAISS_AVAILABLE and self.index is not None:
                # FAISS 인덱스로 검색
                faiss.normalize_L2(np.array([query_embedding], dtype=np.float32))
                similarities, indices = self.index.search(
                    np.array([query_embedding], dtype=np.float32), 
                    min(limit, len(self.documents))
                )
                
                # 결과 구성
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < 0 or idx >= len(self.documents):
                        continue
                    
                    doc = self.documents[idx]
                    results.append({
                        'id': doc['id'],
                        'text': doc['text'],
                        'metadata': doc['metadata'],
                        'score': float(similarities[0][i])
                    })
                
                return results
            else:
                # FAISS 없이 직접 계산
                similarities = []
                for doc in self.documents:
                    if 'embedding' in doc:
                        # 코사인 유사도 계산
                        sim = np.dot(query_embedding, doc['embedding'])
                        similarities.append((sim, doc))
                
                # 유사도 기준 정렬 및 상위 결과 반환
                similarities.sort(reverse=True, key=lambda x: x[0])
                results = []
                for sim, doc in similarities[:limit]:
                    results.append({
                        'id': doc['id'],
                        'text': doc['text'],
                        'metadata': doc['metadata'],
                        'score': float(sim)
                    })
                
                return results
        except Exception as e:
            logger.error(f"Error during vector search: {str(e)}")
            # 오류 시 키워드 검색으로 폴백
            return self._keyword_search(query, limit)
    
    def _keyword_search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        임베딩을 사용할 수 없을 때 단순 키워드 검색으로 폴백
        
        Args:
            query: 검색 쿼리
            limit: 반환할 최대 결과 수
            
        Returns:
            검색 결과 리스트
        """
        query_words = set(query.lower().split())
        
        # 단어 매칭으로 문서 점수 계산
        scored_docs = []
        for doc in self.documents:
            text = doc['text'].lower()
            # 각 쿼리 단어가 문서에 포함되어 있는지 확인
            matches = sum(word in text for word in query_words)
            if matches > 0:  # 일치하는 단어가 있는 경우만 포함
                score = matches / len(query_words)
                scored_docs.append((score, doc))
        
        # 점수 기준 정렬 및 상위 결과 반환
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        results = []
        for score, doc in scored_docs[:limit]:
            results.append({
                'id': doc['id'],
                'text': doc['text'],
                'metadata': doc['metadata'],
                'score': float(score)
            })
        
        return results
    
    def clear(self) -> None:
        """벡터 저장소 초기화"""
        self.documents = []
        if FAISS_AVAILABLE and self.index is not None:
            # 모델의 출력 차원 확인
            embedding_dim = self.model.get_sentence_embedding_dimension()
            # 새 인덱스 생성
            self.index = faiss.IndexFlatIP(embedding_dim)
        
        logger.info("Vector store cleared")
    
    def save(self) -> None:
        """벡터 저장소 저장"""
        documents_path = os.path.join(self.store_path, "documents.json")
        index_path = os.path.join(self.store_path, "faiss_index.bin")
        
        # 문서 저장
        serializable_docs = []
        for doc in self.documents:
            # numpy 배열은 JSON으로 직렬화할 수 없으므로 제거
            serializable_doc = {k: v for k, v in doc.items() if k != 'embedding'}
            serializable_docs.append(serializable_doc)
            
        with open(documents_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_docs, f, ensure_ascii=False, indent=2)
        
        # FAISS 인덱스 저장
        if FAISS_AVAILABLE and self.index is not None:
            faiss.write_index(self.index, index_path)
        
        logger.info(f"Vector store saved to {self.store_path}")
    
    def load(self) -> bool:
        """
        저장된 벡터 저장소 불러오기
        
        Returns:
            성공 여부
        """
        documents_path = os.path.join(self.store_path, "documents.json")
        index_path = os.path.join(self.store_path, "faiss_index.bin")
        
        if not os.path.exists(documents_path):
            logger.info("No saved vector store found")
            return False
        
        try:
            # 문서 불러오기
            with open(documents_path, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            # FAISS 인덱스 불러오기
            if FAISS_AVAILABLE and os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            
            logger.info(f"Loaded vector store with {len(self.documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False 