import os
import sys
import json
import re
import tiktoken
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import openai
from openai import OpenAI
import time
import requests
import shutil
from tqdm import tqdm

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
        print(f"Error reading .env.local: {e}")
        return None

# .env.local 파일 위치
env_path = Path(__file__).parent.parent.parent / '.env.local'
print(f"Loading API key from: {env_path} (exists: {env_path.exists()})")

# API 키 파싱
openai_api_key = parse_api_key_from_env_file(env_path)
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env.local")
else:
    # 키 일부만 표시하여 로드 확인
    masked_key = f"{openai_api_key[:10]}...{openai_api_key[-5:]}"
    print(f"API Key loaded: {masked_key} (length: {len(openai_api_key)})")

# 청크 설정
TARGET_TOKEN_SIZE = 120  # 목표 토큰 크기
MIN_TOKEN_SIZE = 80      # 최소 토큰 크기
MAX_TOKEN_SIZE = 150     # 최대 토큰 크기
TOKEN_OVERLAP = 20       # 토큰 중복 크기

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=openai_api_key)

# ChromaDB 클라이언트 설정
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "vector_db"))
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

# 기존 컬렉션 가져오기
collection = chroma_client.get_collection(name="langchain", embedding_function=embedding_function)

# tiktoken 인코더 설정
encoding = tiktoken.encoding_for_model("gpt-4")

def download_kant_works():
    """칸트의 작품들을 다운로드"""
    works = {
        "critique_of_pure_reason": "https://www.gutenberg.org/files/4280/4280-0.txt",  # 순수 이성 비판
        "critique_of_judgment": "https://www.gutenberg.org/files/48433/48433-0.txt",   # 판단력 비판
    }
    
    data_dir = Path(__file__).parent / "raw_texts"
    data_dir.mkdir(exist_ok=True)
    
    downloaded_files = {}
    
    for work_name, url in works.items():
        output_path = data_dir / f"{work_name}.txt"
        if output_path.exists():
            print(f"File already exists: {output_path}")
            downloaded_files[work_name] = str(output_path)
            continue
            
        print(f"Downloading {work_name} from {url}...")
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {work_name} to {output_path}")
                downloaded_files[work_name] = str(output_path)
            else:
                print(f"Failed to download {work_name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Error downloading {work_name}: {e}")
    
    return downloaded_files

def clean_text(text):
    """텍스트 정리 - 주석, 특수문자 등 처리"""
    # 공백 정리
    text = re.sub(r'\s+', ' ', text)
    # 특수 인코딩 및 HTML 엔티티 처리
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    # Project Gutenberg 헤더/푸터 제거 (필요한 경우)
    text = re.sub(r'Project Gutenberg.*?START OF (THIS|THE) PROJECT GUTENBERG EBOOK.*?\*\*\*', '', text, flags=re.DOTALL)
    text = re.sub(r'\*\*\* END OF (THIS|THE) PROJECT GUTENBERG EBOOK.*', '', text, flags=re.DOTALL)
    
    return text.strip()

def preprocess_text_file(file_path, work_name):
    """텍스트 파일 전처리"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        print(f"Read {len(text)} characters from {file_path}")
        
        # 텍스트 정리
        clean_content = clean_text(text)
        print(f"After cleaning: {len(clean_content)} characters")
        
        return clean_content
    except Exception as e:
        print(f"Error preprocessing {file_path}: {e}")
        return None

def create_chunks_with_tiktoken(text, work_name):
    """Tiktoken을 사용하여 텍스트를 토큰 기반으로 분할"""
    tokens = encoding.encode(text)
    token_count = len(tokens)
    
    print(f"Total tokens in {work_name}: {token_count}")
    
    chunks = []
    chunk_id = 0
    
    i = 0
    while i < token_count:
        chunk_end = min(i + TARGET_TOKEN_SIZE, token_count)
        
        # 청크 분리 (문장 경계 고려)
        if chunk_end < token_count:
            # 원본 텍스트의 해당 부분 확인
            chunk_text = encoding.decode(tokens[i:chunk_end])
            
            # 마지막 문장 완성 확인 (마침표, 물음표, 느낌표 등으로 끝나는지)
            last_sentence_end = max(
                chunk_text.rfind('. '), 
                chunk_text.rfind('? '), 
                chunk_text.rfind('! '),
                chunk_text.rfind('.\n'),
                chunk_text.rfind('?\n'),
                chunk_text.rfind('!\n')
            )
            
            # 문장 경계가 발견되고 청크 내에 있으면 조정
            if last_sentence_end > 0 and last_sentence_end > len(chunk_text) * 0.5:  # 최소 50% 정도 포함
                adjusted_text = chunk_text[:last_sentence_end + 1]  # +1로 구두점 포함
                adjusted_tokens = encoding.encode(adjusted_text)
                chunk_end = i + len(adjusted_tokens)
            
        # 청크 생성
        chunk_tokens = tokens[i:chunk_end]
        chunk_text = encoding.decode(chunk_tokens)
        
        # 최소 토큰 수 확인
        if len(chunk_tokens) >= MIN_TOKEN_SIZE:
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": work_name,
                    "chunk_id": f"{work_name.lower().replace(' ', '_')}_chunk_{chunk_id}",
                    "token_count": len(chunk_tokens),
                    "original_order": chunk_id
                }
            })
            chunk_id += 1
        
        # 다음 청크의 시작 위치 (중복 고려)
        next_position = chunk_end - TOKEN_OVERLAP
        i = max(i + 1, next_position)  # 최소 1 토큰은 전진
    
    print(f"Created {len(chunks)} chunks from {work_name}")
    return chunks

def add_chunks_to_vector_db(chunks):
    """청크를 벡터 DB에 추가"""
    # 기존 컬렉션 크기 확인
    existing_count = collection.count()
    print(f"Existing documents in DB: {existing_count}")
    
    # 추가할 ID, 텍스트, 메타데이터 리스트 준비
    ids = []
    texts = []
    metadatas = []
    
    for chunk in chunks:
        ids.append(chunk["metadata"]["chunk_id"])
        texts.append(chunk["text"])
        metadatas.append(chunk["metadata"])
    
    # Batch 단위로 추가 (한 번에 너무 많은 요청 방지)
    BATCH_SIZE = 100
    
    for i in tqdm(range(0, len(ids), BATCH_SIZE), desc="Adding chunks to vector DB"):
        batch_ids = ids[i:i+BATCH_SIZE]
        batch_texts = texts[i:i+BATCH_SIZE]
        batch_metadatas = metadatas[i:i+BATCH_SIZE]
        
        collection.add(
            ids=batch_ids,
            documents=batch_texts,
            metadatas=batch_metadatas
        )
        time.sleep(0.1)  # API 속도 제한 방지
    
    # 업데이트 후 컬렉션 크기 확인
    updated_count = collection.count()
    print(f"Updated documents in DB: {updated_count}")
    print(f"Added {updated_count - existing_count} new documents")

def validate_chunks(chunks, min_size=MIN_TOKEN_SIZE, max_size=MAX_TOKEN_SIZE):
    """생성된 청크의 품질 검사"""
    # 각 청크의 토큰 수와 문자 수 계산
    token_counts = [chunk["metadata"]["token_count"] for chunk in chunks]
    char_lengths = [len(chunk["text"]) for chunk in chunks]
    
    print(f"\n=== 청크 통계 ===")
    print(f"총 청크 수: {len(chunks)}")
    print(f"평균 토큰 수: {sum(token_counts) / len(token_counts):.2f} 토큰")
    print(f"최소 토큰 수: {min(token_counts)} 토큰")
    print(f"최대 토큰 수: {max(token_counts)} 토큰")
    print(f"평균 문자 수: {sum(char_lengths) / len(char_lengths):.2f} 문자")
    
    # 토큰 수 분포
    below_min = sum(1 for t in token_counts if t < min_size)
    between_min_target = sum(1 for t in token_counts if min_size <= t < TARGET_TOKEN_SIZE)
    between_target_max = sum(1 for t in token_counts if TARGET_TOKEN_SIZE <= t <= max_size)
    above_max = sum(1 for t in token_counts if t > max_size)
    
    print(f"\n토큰 분포:")
    print(f"- {min_size} 미만: {below_min} 청크 ({below_min/len(chunks)*100:.1f}%)")
    print(f"- {min_size}~{TARGET_TOKEN_SIZE-1}: {between_min_target} 청크 ({between_min_target/len(chunks)*100:.1f}%)")
    print(f"- {TARGET_TOKEN_SIZE}~{max_size}: {between_target_max} 청크 ({between_target_max/len(chunks)*100:.1f}%)")
    print(f"- {max_size} 초과: {above_max} 청크 ({above_max/len(chunks)*100:.1f}%)")
    
    # 유효성 검사 결과
    valid_count = between_min_target + between_target_max
    valid_pct = valid_count / len(chunks) * 100
    
    if valid_pct >= 95:
        print(f"\n✅ 검증 통과: {valid_pct:.2f}%의 청크가 유효한 크기 ({min_size}~{max_size} 토큰)입니다.")
        return True
    else:
        print(f"\n⚠️ 검증 실패: 유효한 크기의 청크가 {valid_pct:.2f}%에 불과합니다. 95% 이상이 필요합니다.")
        return False

def main():
    # 1. 칸트의 작품 다운로드
    downloaded_files = download_kant_works()
    
    if not downloaded_files:
        print("No files were downloaded. Exiting.")
        return
    
    all_chunks = []
    
    # 2. 각 작품 처리
    for work_name, file_path in downloaded_files.items():
        print(f"\n{'='*50}")
        print(f"Processing {work_name}...")
        print(f"{'='*50}")
        
        # 텍스트 전처리
        processed_text = preprocess_text_file(file_path, work_name)
        if not processed_text:
            print(f"Skipping {work_name} due to preprocessing error.")
            continue
        
        # 작품 이름 변환 (가독성 향상)
        display_name = " ".join(word.capitalize() for word in work_name.split("_"))
        display_name = "The " + display_name
        
        # 청크 생성
        chunks = create_chunks_with_tiktoken(processed_text, display_name)
        all_chunks.extend(chunks)
        
        # 일부 청크 샘플 보기
        print("\n샘플 청크:")
        for i in range(min(3, len(chunks))):
            chunk = chunks[i]
            print(f"\n--- 청크 {i+1} (토큰: {chunk['metadata']['token_count']}) ---")
            print(f"{chunk['text'][:150]}..." if len(chunk['text']) > 150 else chunk['text'])
    
    # 3. 청크 검증
    if all_chunks:
        print(f"\n{'='*50}")
        print(f"검증 중... 총 {len(all_chunks)} 청크")
        is_valid = validate_chunks(all_chunks)
        
        # 4. 벡터 DB에 추가
        if is_valid:
            print(f"\n{'='*50}")
            print("벡터 DB에 청크 추가 중...")
            add_chunks_to_vector_db(all_chunks)
            print("\n✅ 완료! 모든 청크가 벡터 DB에 추가되었습니다.")
        else:
            print("\n벡터 DB 구축을 위해서는 청크 검증을 통과해야 합니다.")
            user_input = input("그래도 진행하시겠습니까? (y/n): ")
            if user_input.lower() == 'y':
                add_chunks_to_vector_db(all_chunks)
                print("\n✅ 완료! 모든 청크가 벡터 DB에 추가되었습니다.")

if __name__ == "__main__":
    main() 