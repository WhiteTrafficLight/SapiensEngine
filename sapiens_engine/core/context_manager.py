"""
Context Manager Module

이 모듈은 다양한 형식(PDF, 웹 URL, 텍스트)의 컨텍스트를 로드하고,
청크화한 후 벡터 DB에 저장하는 기능을 제공합니다.

기능:
- 다양한 형식의 컨텍스트 로드 (PDF, URL, 텍스트)
- 문장 단위 청크화 및 오버래핑 슬라이딩 윈도우 청크화
- ChromaDB를 사용한 벡터 저장 및 검색
"""

import os
import re
import pdfplumber
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Union, Optional
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter
)
from sentence_transformers import SentenceTransformer
import nltk
import logging
from pathlib import Path
import hashlib

# NLTK 데이터 다운로드
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContextManager:
    """
    컨텍스트 관리자 클래스
    
    다양한 형식의 컨텍스트를 로드, 청크화하고 벡터 DB에 저장하는 기능 제공
    """
    
    def __init__(
        self,
        db_path: str = "./vectordb",
        chunk_size: int = 500,
        chunk_overlap: float = 0.25,
        chunking_method: str = "sliding_window",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        초기화 함수
        
        Args:
            db_path: 벡터 DB 저장 경로
            chunk_size: 청크 크기 (토큰 단위)
            chunk_overlap: 오버랩 비율 (0.0 ~ 1.0)
            chunking_method: 청크화 방식 ('sentence' 또는 'sliding_window')
            embedding_model: 임베딩 모델 이름
        """
        self.db_path = db_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunking_method = chunking_method
        self.embedding_model_name = embedding_model
        
        # 경로가 없으면 생성
        os.makedirs(db_path, exist_ok=True)
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=db_path)
        
        # 임베딩 함수 초기화
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # 임베딩 모델 로드 (직접 토큰 카운팅용)
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # 토큰 스플리터 초기화
        self.token_splitter = SentenceTransformersTokenTextSplitter(
            model_name=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=int(chunk_size * chunk_overlap)
        )
        
        # 문장 스플리터 초기화
        self.sentence_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size * 4,  # 문자 기준으로 크기 조정
            chunk_overlap=int(chunk_size * 4 * chunk_overlap),
            separators=["\n\n", "\n", ". ", "! ", "? ", ";", ":", " ", ""]
        )
        
        logger.info(f"ContextManager 초기화 완료: {chunk_size} 토큰, {chunk_overlap*100}% 오버랩, {chunking_method} 방식")
    
    def load_pdf(self, file_path: str) -> str:
        """
        PDF 파일을 텍스트로 로드
        
        Args:
            file_path: PDF 파일 경로
            
        Returns:
            추출된 텍스트
        """
        logger.info(f"PDF 로드 중: {file_path}")
        
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
        except Exception as e:
            logger.error(f"PDF 로드 실패: {str(e)}")
            raise
        
        # 여러 줄바꿈 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        logger.info(f"PDF 로드 완료: {len(text)} 자")
        return text
    
    def load_url(self, url: str) -> str:
        """
        URL에서 텍스트 추출
        
        Args:
            url: 웹 페이지 URL
            
        Returns:
            추출된 텍스트
        """
        logger.info(f"URL 컨텐츠 로드 중: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 스크립트, 스타일 태그 제거
            for script in soup(["script", "style"]):
                script.extract()
            
            text = soup.get_text(separator='\n')
            
            # 여러 줄바꿈 정리
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\s{3,}', ' ', text)
            
            logger.info(f"URL 로드 완료: {len(text)} 자")
            return text
            
        except Exception as e:
            logger.error(f"URL 로드 실패: {str(e)}")
            raise
    
    def chunk_text(self, text: str) -> List[str]:
        """
        텍스트를 청크화
        
        Args:
            text: 청크화할 텍스트
            
        Returns:
            청크 리스트
        """
        if self.chunking_method == "sentence":
            logger.info("문장 단위 청크화 수행")
            chunks = self.sentence_splitter.split_text(text)
        else:  # sliding_window
            logger.info("슬라이딩 윈도우 청크화 수행")
            chunks = self.token_splitter.split_text(text)
        
        logger.info(f"청크화 완료: {len(chunks)} 청크 생성")
        return chunks
    
    def process_and_store(
        self, 
        content: str, 
        source_id: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        컨텐츠를 처리하고 벡터 DB에 저장
        
        Args:
            content: 텍스트 컨텐츠
            source_id: 소스 식별자 (파일명, URL 등)
            source_type: 소스 유형 (pdf, url, text)
            metadata: 추가 메타데이터
            
        Returns:
            생성된 컬렉션 이름
        """
        # 컬렉션 이름 생성
        collection_name = f"{source_type}_{hashlib.md5(source_id.encode()).hexdigest()[:8]}"
        
        # 기존 컬렉션이 있으면 삭제
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"기존 컬렉션 삭제: {collection_name}")
        except:
            pass
        
        # 컬렉션 생성
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"source": source_id, "type": source_type}
        )
        
        # 텍스트 청크화
        chunks = self.chunk_text(content)
        
        # 기본 메타데이터 설정
        if metadata is None:
            metadata = {}
        
        base_metadata = {
            "source": source_id,
            "type": source_type,
            **metadata
        }
        
        # 각 청크를 벡터 DB에 저장
        ids = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            ids.append(chunk_id)
            
            # 청크별 메타데이터 추가
            chunk_metadata = {
                **base_metadata,
                "chunk_id": i,
                "chunk_text": chunk[:100] + "..." if len(chunk) > 100 else chunk
            }
            metadatas.append(chunk_metadata)
        
        # 벌크 저장
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )
        
        logger.info(f"벡터 DB 저장 완료: {len(chunks)} 청크, 컬렉션 '{collection_name}'")
        return collection_name
    
    def process_file(
        self, 
        file_path: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        파일을 처리하고 벡터 DB에 저장
        
        Args:
            file_path: 파일 경로
            metadata: 추가 메타데이터
            
        Returns:
            생성된 컬렉션 이름
        """
        file_path = os.path.abspath(file_path)
        
        # 파일 확장자 확인
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.pdf':
            # PDF 파일 처리
            content = self.load_pdf(file_path)
            return self.process_and_store(content, file_path, "pdf", metadata)
        elif ext in ['.txt', '.md', '.json', '.csv']:
            # 텍스트 파일 처리
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.process_and_store(content, file_path, "text", metadata)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {ext}")
    
    def process_url(
        self, 
        url: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        URL을 처리하고 벡터 DB에 저장
        
        Args:
            url: 웹 페이지 URL
            metadata: 추가 메타데이터
            
        Returns:
            생성된 컬렉션 이름
        """
        content = self.load_url(url)
        return self.process_and_store(content, url, "url", metadata)
    
    def process_text(
        self, 
        text: str, 
        source_id: str = "custom_text",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        텍스트를 처리하고 벡터 DB에 저장
        
        Args:
            text: 처리할 텍스트
            source_id: 소스 식별자
            metadata: 추가 메타데이터
            
        Returns:
            생성된 컬렉션 이름
        """
        return self.process_and_store(text, source_id, "text", metadata)
    
    def search(
        self, 
        collection_name: str, 
        query: str, 
        n_results: int = 3,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        벡터 DB에서 쿼리와 유사한 청크 검색
        
        Args:
            collection_name: 검색할 컬렉션 이름
            query: 검색 쿼리
            n_results: 반환할 결과 수
            include_metadata: 메타데이터 포함 여부
            
        Returns:
            검색 결과 목록
        """
        try:
            collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # 결과 포맷팅
            formatted_results = []
            
            for i in range(len(results['documents'][0])):
                item = {
                    "text": results['documents'][0][i],
                    "distance": results['distances'][0][i],
                }
                
                if include_metadata and 'metadatas' in results:
                    item["metadata"] = results['metadatas'][0][i]
                
                formatted_results.append(item)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"검색 실패: {str(e)}")
            raise
    
    def list_collections(self) -> List[str]:
        """
        저장된 컬렉션 목록 조회
        
        Returns:
            컬렉션 이름 목록
        """
        return [collection.name for collection in self.client.list_collections()]
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        컬렉션 정보 조회
        
        Args:
            collection_name: 컬렉션 이름
            
        Returns:
            컬렉션 정보
        """
        collection = self.client.get_collection(name=collection_name)
        return {
            "name": collection_name,
            "count": collection.count(),
            "metadata": collection.metadata
        } 