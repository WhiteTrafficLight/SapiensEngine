import os
import re
import json
import glob
import uuid
import time
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API 키를 직접 .env.local 파일에서 파싱
def parse_api_key_from_env_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            # OPENAI_API_KEY 행 찾기
            match = re.search(r'OPENAI_API_KEY=([^\n]+)', content)
            if match:
                # 키 값 추출
                api_key = match.group(1).strip()
                return api_key
            return None
    except Exception as e:
        logger.error(f"Error reading .env.local: {e}")
        return None

# .env.local 파일 위치
env_path = Path(__file__).parent.parent.parent / '.env.local'
logger.info(f"Loading API key from: {env_path} (exists: {env_path.exists()})")

# API 키 파싱
OPENAI_API_KEY = parse_api_key_from_env_file(env_path)
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in .env.local")
    raise ValueError("OPENAI_API_KEY not found in .env.local")
else:
    # 키 일부만 표시하여 로드 확인
    masked_key = f"{OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-5:]}"
    logger.info(f"API Key loaded: {masked_key} (length: {len(OPENAI_API_KEY)})")

def simple_sentence_tokenize(text):
    """
    간단한 정규식 기반 문장 분리 함수
    
    Args:
        text: 분리할 텍스트
        
    Returns:
        문장 리스트
    """
    # 문장 끝 패턴: 마침표, 물음표, 느낌표 뒤에 공백이나 줄바꿈이 오는 경우
    sentence_endings = r'(?<=[.!?])\s+'
    
    # 텍스트 분리
    sentences = re.split(sentence_endings, text)
    
    # 빈 문장 제거 및 정리
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

class SentenceChunker:
    def __init__(self, input_dir, output_dir):
        """
        문장 단위 청킹을 위한 클래스 초기화
        
        Args:
            input_dir: 원본 텍스트 파일이 있는 디렉토리 (None일 수 있음)
            output_dir: 청킹된 결과를 저장할 디렉토리
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/chunks", exist_ok=True)
        os.makedirs(f"{output_dir}/vector_db", exist_ok=True)
        
        # ChromaDB 클라이언트 설정
        self.chroma_client = chromadb.PersistentClient(path=f"{output_dir}/vector_db")
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small"
        )
        
        # 문장과 문단 매핑을 저장할 딕셔너리
        self.sentence_to_paragraph = {}
        
    def process_files(self):
        """전체 파일 처리 프로세스"""
        # 텍스트 파일 목록 가져오기
        txt_files = glob.glob(f"{self.input_dir}/**/*.txt", recursive=True)
        logger.info(f"Found {len(txt_files)} text files to process")
        
        all_chunks = []
        
        for file_path in tqdm(txt_files, desc="Processing files"):
            try:
                # 파일에서 청크 생성
                file_chunks = self.create_sentence_chunks(file_path)
                all_chunks.extend(file_chunks)
                
                # 중간 저장
                chunk_file = os.path.join(
                    self.output_dir, 
                    "chunks", 
                    f"{os.path.basename(file_path).replace('.txt', '')}_chunks.json"
                )
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(file_chunks, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Created {len(file_chunks)} chunks from {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        
        # 전체 결과 저장
        with open(f"{self.output_dir}/all_chunks.json", 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
        # 문장-문단 매핑 저장
        with open(f"{self.output_dir}/sentence_to_paragraph_map.json", 'w', encoding='utf-8') as f:
            json.dump(self.sentence_to_paragraph, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Total chunks created: {len(all_chunks)}")
        
        # 벡터 DB 생성
        self.create_vector_db(all_chunks)
        
    def create_sentence_chunks(self, file_path):
        """
        파일을 문장 단위로 청킹하고 문단 컨텍스트를 저장
        
        Args:
            file_path: 처리할 텍스트 파일 경로
            
        Returns:
            문장 단위 청크 리스트
        """
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 파일 메타데이터 추출
        file_name = os.path.basename(file_path)
        book_title = self.extract_book_title(file_name)
        
        # 문단으로 분리
        paragraphs = self.split_into_paragraphs(text)
        
        chunks = []
        paragraph_map = {}
        
        # 각 문단별로 처리
        for p_idx, paragraph in enumerate(paragraphs):
            # 빈 문단 건너뛰기
            if not paragraph.strip():
                continue
            
            # 문단 ID 생성
            paragraph_id = f"{book_title}_p{p_idx}"
            
            # 문단에서 문장 추출 (nltk 대신 간단한 정규식 사용)
            sentences = simple_sentence_tokenize(paragraph)
            
            # 각 문장을 청크로 저장
            for s_idx, sentence in enumerate(sentences):
                # 빈 문장 건너뛰기
                if not sentence.strip():
                    continue
                
                # 문장 ID 생성
                sentence_id = f"{paragraph_id}_s{s_idx}"
                
                # 청크 생성
                chunk = {
                    "id": sentence_id,
                    "content": sentence.strip(),
                    "source": book_title,
                    "paragraph_id": paragraph_id,
                    "paragraph_index": p_idx,
                    "sentence_index": s_idx,
                    "paragraph_content": paragraph
                }
                
                chunks.append(chunk)
                
                # 문장-문단 매핑 저장
                self.sentence_to_paragraph[sentence_id] = {
                    "paragraph_id": paragraph_id,
                    "paragraph_content": paragraph,
                    "book_title": book_title
                }
                
                # 이웃 문단도 저장 (컨텍스트 확장용)
                paragraph_map[paragraph_id] = {
                    "content": paragraph,
                    "book_title": book_title
                }
        
        # 문단 간의 이웃 관계 저장
        for p_idx in range(len(paragraphs)):
            paragraph_id = f"{book_title}_p{p_idx}"
            
            # 이전 문단
            if p_idx > 0:
                prev_id = f"{book_title}_p{p_idx-1}"
                if prev_id in paragraph_map:
                    if "neighbors" not in paragraph_map[paragraph_id]:
                        paragraph_map[paragraph_id]["neighbors"] = []
                    paragraph_map[paragraph_id]["neighbors"].append({
                        "id": prev_id, 
                        "content": paragraph_map[prev_id]["content"],
                        "relation": "previous"
                    })
            
            # 다음 문단
            if p_idx < len(paragraphs) - 1:
                next_id = f"{book_title}_p{p_idx+1}"
                if next_id in paragraph_map:
                    if "neighbors" not in paragraph_map[paragraph_id]:
                        paragraph_map[paragraph_id]["neighbors"] = []
                    paragraph_map[paragraph_id]["neighbors"].append({
                        "id": next_id, 
                        "content": paragraph_map[next_id]["content"],
                        "relation": "next"
                    })
        
        # 문단 맵을 문장-문단 매핑에 병합
        for sentence_id, sentence_data in self.sentence_to_paragraph.items():
            paragraph_id = sentence_data["paragraph_id"]
            if paragraph_id in paragraph_map and "neighbors" in paragraph_map[paragraph_id]:
                self.sentence_to_paragraph[sentence_id]["neighbors"] = paragraph_map[paragraph_id]["neighbors"]
        
        return chunks
    
    def create_vector_db(self, chunks):
        """
        ChromaDB 벡터 데이터베이스 생성
        
        Args:
            chunks: 청크 리스트
        """
        # 컬렉션 생성 또는 가져오기
        collection_name = "sentence_chunks"
        
        # 기존 컬렉션이 있으면 삭제
        try:
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except:
            pass
        
        # 새 컬렉션 생성
        collection = self.chroma_client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Kant works sentence-level chunks"}
        )
        
        # 청크를 배치로 나누기
        batch_size = 100
        batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]
        
        for batch_idx, batch in enumerate(tqdm(batches, desc="Creating vector DB")):
            ids = [chunk["id"] for chunk in batch]
            documents = [chunk["content"] for chunk in batch]
            metadatas = [
                {
                    "source": chunk["source"],
                    "paragraph_id": chunk["paragraph_id"],
                    "paragraph_index": chunk["paragraph_index"],
                    "sentence_index": chunk["sentence_index"]
                } 
                for chunk in batch
            ]
            
            # Chroma DB에 추가
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added batch {batch_idx+1}/{len(batches)} to vector DB")
            time.sleep(0.5)  # API 속도 제한 방지
        
        logger.info(f"Vector DB created with {collection.count()} chunks")
    
    def split_into_paragraphs(self, text):
        """텍스트를 문단으로 분리"""
        # 빈 줄로 분리
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def extract_book_title(self, file_name):
        """파일 이름에서 책 제목 추출"""
        # 파일 이름 형식에 맞게 수정 필요
        if "critique_of_pure_reason" in file_name.lower():
            return "Critique of Pure Reason"
        elif "critique_of_practical_reason" in file_name.lower():
            return "Critique of Practical Reason"
        elif "critique_of_judgment" in file_name.lower():
            return "Critique of Judgment"
        else:
            return file_name.replace('.txt', '')

    def get_context_for_sentence(self, sentence_id):
        """
        문장 ID에 해당하는 문단 컨텍스트 가져오기
        
        Args:
            sentence_id: 문장 ID
            
        Returns:
            문장이 포함된 문단과 이웃 문단들의 정보
        """
        if sentence_id not in self.sentence_to_paragraph:
            return None
        
        context = self.sentence_to_paragraph[sentence_id]
        return {
            "paragraph_content": context["paragraph_content"],
            "book_title": context["book_title"],
            "neighbors": context.get("neighbors", [])
        }

def main():
    # 입력 및 출력 디렉토리 설정
    # 명확한 파일 경로 지정
    input_files = [
        "rag_data/kant/critique_of_practical_reason.txt",
        "rag_data/kant/raw_texts/critique_of_judgment.txt",
        "rag_data/kant/raw_texts/critique_of_pure_reason.txt"
    ]
    output_dir = "rag_data/kant_new"
    
    # 청커 초기화
    chunker = SentenceChunker(None, output_dir)  # input_dir은 사용하지 않음
    
    # 모든 청크 저장 리스트
    all_chunks = []
    
    # 각 파일 처리
    for file_path in tqdm(input_files, desc="Processing files"):
        try:
            # 파일 존재하는지 확인
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                continue
                
            # 파일에서 청크 생성
            file_chunks = chunker.create_sentence_chunks(file_path)
            all_chunks.extend(file_chunks)
            
            # 중간 저장
            chunk_file = os.path.join(
                output_dir, 
                "chunks", 
                f"{os.path.basename(file_path).replace('.txt', '')}_chunks.json"
            )
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(file_chunks, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created {len(file_chunks)} chunks from {file_path}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
    
    # 전체 결과 저장
    with open(f"{output_dir}/all_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    
    # 문장-문단 매핑 저장
    with open(f"{output_dir}/sentence_to_paragraph_map.json", 'w', encoding='utf-8') as f:
        json.dump(chunker.sentence_to_paragraph, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Total chunks created: {len(all_chunks)}")
    
    # 벡터 DB 생성
    chunker.create_vector_db(all_chunks)
    
    logger.info("Sentence chunking completed successfully")

if __name__ == "__main__":
    main() 