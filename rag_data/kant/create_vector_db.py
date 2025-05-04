import os
import dotenv
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import hashlib
import re
import uuid

# .env.local에서 OpenAI API 키 로드
dotenv_path = Path(__file__).parent.parent.parent / '.env.local'
dotenv.load_dotenv(dotenv_path)

# API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env.local")

def clean_text(text):
    """텍스트 정리"""
    # 여러 줄바꿈 제거
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 불필요한 공백 제거
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def chunk_text(text, max_chunk_size=1000, overlap=200):
    """텍스트를 청크로 나누기"""
    text = clean_text(text)
    
    # 각 단락을 기준으로 분할
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) <= max_chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # 새 청크 시작 (이전 청크와 겹치는 부분 포함)
            if len(current_chunk) > overlap:
                overlap_text = current_chunk[-overlap:]
                current_chunk = overlap_text + paragraph + "\n\n"
            else:
                current_chunk = paragraph + "\n\n"
    
    # 마지막 청크 추가
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def get_chunk_id(text):
    """청크 텍스트에서 안정적인 ID 생성"""
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"chunk_{text_hash}"

def create_kant_vector_db():
    """칸트의 실천이성비판 벡터 데이터베이스 생성"""
    # 파일 경로 설정
    file_path = os.path.join(os.path.dirname(__file__), "critique_of_practical_reason.txt")
    
    # 파일 존재 확인
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # 파일 읽기
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # 텍스트 청크로 나누기
    chunks = chunk_text(text)
    print(f"텍스트를 {len(chunks)}개 청크로 나누었습니다.")
    
    # ChromaDB 클라이언트 설정
    chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "vector_db"))
    
    # 기존 컬렉션이 있으면 삭제
    try:
        chroma_client.delete_collection("kant_practical_reason")
        print("기존 컬렉션 삭제됨")
    except:
        pass
    
    # Embedding 함수 설정
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    # 새 컬렉션 생성
    collection = chroma_client.create_collection(
        name="kant_practical_reason",
        embedding_function=embedding_function,
        metadata={"description": "Kant's Critique of Practical Reason"}
    )
    
    # 청크 추가
    chunk_ids = []
    documents = []
    metadatas = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = get_chunk_id(chunk)
        chunk_ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "source": "critique_of_practical_reason",
            "chunk_index": i,
            "total_chunks": len(chunks)
        })
    
    # 벡터 DB에 추가
    collection.add(
        ids=chunk_ids,
        documents=documents,
        metadatas=metadatas
    )
    
    print(f"벡터 데이터베이스에 {len(chunks)}개 청크 추가 완료!")
    print(f"컬렉션 크기: {collection.count()}")
    
    return collection

if __name__ == "__main__":
    create_kant_vector_db() 