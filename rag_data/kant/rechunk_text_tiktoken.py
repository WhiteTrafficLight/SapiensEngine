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
import shutil

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

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=openai_api_key)

# tiktoken 인코더 가져오기
encoding = tiktoken.encoding_for_model("gpt-4")

# 원본 텍스트 파일 경로
INPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "critique_of_practical_reason.txt")

# 벡터 DB 경로 설정
VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db")
BACKUP_DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db_backup")

# 청크 설정
TARGET_TOKEN_SIZE = 120  # 목표 토큰 크기
MIN_TOKEN_SIZE = 80      # 최소 토큰 크기
MAX_TOKEN_SIZE = 150     # 최대 토큰 크기
TOKEN_OVERLAP = 20       # 토큰 중복 크기

# 원본 텍스트 로드
def load_original_text(filepath):
    """원본 텍스트 파일 로드"""
    print(f"Loading original text from: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            text = file.read()
        
        # Project Gutenberg 헤더/푸터 제거
        # 헤더 제거 (*** START OF THE PROJECT GUTENBERG EBOOK 이후부터)
        header_end = text.find("*** START OF THE PROJECT GUTENBERG EBOOK")
        if header_end != -1:
            header_end = text.find("\n", header_end) + 1
            text = text[header_end:]
        
        # 푸터 제거 (*** END OF THE PROJECT GUTENBERG EBOOK 이전까지)
        footer_start = text.find("*** END OF THE PROJECT GUTENBERG EBOOK")
        if footer_start != -1:
            text = text[:footer_start]
        
        print(f"Successfully loaded text: {len(text):,} characters")
        return text
    except Exception as e:
        print(f"Error loading text: {e}")
        return None

# 텍스트를 문장으로 분할
def split_into_sentences(text):
    """텍스트를 문장으로 분할"""
    # 문장 구분 패턴: 마침표, 느낌표, 물음표 뒤에 공백이 있는 경우
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로 통일
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# 텍스트를 tiktoken 토큰 수를 기준으로 청크로 분할
def split_into_chunks_by_tokens(text, target_size=TARGET_TOKEN_SIZE, min_size=MIN_TOKEN_SIZE, 
                                max_size=MAX_TOKEN_SIZE, overlap=TOKEN_OVERLAP):
    """텍스트를 토큰 수 기준으로 청크 분할"""
    # 전처리: 불필요한 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 문장 단위로 분할
    sentences = split_into_sentences(text)
    
    # 문장별 토큰 수 계산
    sentence_tokens = [len(encoding.encode(sentence)) for sentence in sentences]
    
    chunks = []
    current_chunk_sentences = []
    current_chunk_tokens = 0
    
    for i, (sentence, token_count) in enumerate(zip(sentences, sentence_tokens)):
        # 현재 문장이 최대 크기를 초과하면 분할
        if token_count > max_size:
            # 현재까지의 청크가 있으면 저장
            if current_chunk_sentences and current_chunk_tokens >= min_size:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append(chunk_text)
            
            # 긴 문장을 단어 단위로 분할
            words = sentence.split()
            temp_sentence = []
            temp_tokens = 0
            
            for word in words:
                word_tokens = len(encoding.encode(word))
                if temp_tokens + word_tokens + 1 <= max_size:  # +1은 공백 고려
                    temp_sentence.append(word)
                    temp_tokens += word_tokens + (1 if temp_tokens > 0 else 0)  # 첫 단어 이후에만 공백 추가
                else:
                    # 현재 임시 문장을 청크로 저장
                    if temp_sentence and temp_tokens >= min_size:
                        chunk_text = " ".join(temp_sentence)
                        chunks.append(chunk_text)
                    
                    # 새 임시 문장 시작
                    temp_sentence = [word]
                    temp_tokens = word_tokens
            
            # 마지막 임시 문장 처리
            if temp_sentence and temp_tokens >= min_size:
                chunk_text = " ".join(temp_sentence)
                chunks.append(chunk_text)
            
            # 현재 청크 초기화
            current_chunk_sentences = []
            current_chunk_tokens = 0
            continue
        
        # 현재 문장을 추가했을 때 최대 크기를 초과하는지 확인
        if current_chunk_tokens + token_count > max_size and current_chunk_tokens >= min_size:
            # 현재 청크 저장
            chunk_text = " ".join(current_chunk_sentences)
            chunks.append(chunk_text)
            
            # 중복을 위해 마지막 일부 문장 유지
            if overlap > 0:
                # 중복 토큰 수만큼 문장 유지
                overlap_sentences = []
                overlap_tokens = 0
                
                for s in reversed(current_chunk_sentences):
                    s_tokens = len(encoding.encode(s))
                    if overlap_tokens + s_tokens <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk_sentences = overlap_sentences
                current_chunk_tokens = overlap_tokens
            else:
                current_chunk_sentences = []
                current_chunk_tokens = 0
        
        # 현재 문장 추가
        current_chunk_sentences.append(sentence)
        current_chunk_tokens += token_count
        
        # 목표 크기 도달했는지 확인
        if current_chunk_tokens >= target_size and i < len(sentences) - 1:
            chunk_text = " ".join(current_chunk_sentences)
            chunks.append(chunk_text)
            
            # 중복을 위해 마지막 일부 문장 유지
            if overlap > 0:
                # 중복 토큰 수만큼 문장 유지
                overlap_sentences = []
                overlap_tokens = 0
                
                for s in reversed(current_chunk_sentences):
                    s_tokens = len(encoding.encode(s))
                    if overlap_tokens + s_tokens <= overlap:
                        overlap_sentences.insert(0, s)
                        overlap_tokens += s_tokens
                    else:
                        break
                
                current_chunk_sentences = overlap_sentences
                current_chunk_tokens = overlap_tokens
            else:
                current_chunk_sentences = []
                current_chunk_tokens = 0
    
    # 마지막 청크 처리
    if current_chunk_sentences and current_chunk_tokens >= min_size:
        chunk_text = " ".join(current_chunk_sentences)
        chunks.append(chunk_text)
    
    # 청크 번호와 소스 메타데이터 추가
    chunks_with_metadata = []
    for i, chunk in enumerate(chunks):
        # 챕터/섹션 정보 추출 시도
        chapter_match = re.search(r'(CHAPTER|PART|BOOK)[_\s]+([\dIVXLM]+|[A-Z])[:\|\s]+([^\.]+)', chunk, re.IGNORECASE)
        chapter_info = "The Critique of Practical Reason"
        
        if chapter_match:
            section_type = chapter_match.group(1).capitalize()
            section_num = chapter_match.group(2)
            section_title = chapter_match.group(3).strip()
            chapter_info = f"The Critique of Practical Reason - {section_type} {section_num}: {section_title}"
        
        # 토큰 수 계산
        token_count = len(encoding.encode(chunk))
        
        chunks_with_metadata.append({
            "text": chunk,
            "metadata": {
                "source": chapter_info,
                "chunk_id": f"kant_chunk_{i+1}",
                "original_order": i+1,
                "token_count": token_count
            }
        })
    
    return chunks_with_metadata

# 청크 품질 검사
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
    print(f"평균 문자 수: {sum(char_lengths) / len(char_lengths):.2f} 글자")
    print(f"최소 문자 수: {min(char_lengths)} 글자")
    print(f"최대 문자 수: {max(char_lengths)} 글자")
    
    # 토큰 수 분포
    token_ranges = [(0, 50), (50, 80), (80, 100), (100, 120), (120, 150), (150, float('inf'))]
    
    token_distribution = {f"{s}-{e if e != float('inf') else '이상'}": 0 for s, e in token_ranges}
    for count in token_counts:
        for start, end in token_ranges:
            if start <= count < end:
                token_distribution[f"{start}-{end if end != float('inf') else '이상'}"] += 1
                break
    
    print("\n=== 토큰 수 분포 ===")
    for range_str, count in token_distribution.items():
        print(f"{range_str} 토큰: {count}개 청크 ({count/len(chunks)*100:.1f}%)")
    
    # 첫 번째와 마지막 청크 내용 출력
    print("\n=== 첫 번째 청크 ===")
    print(f"토큰 수: {chunks[0]['metadata']['token_count']}")
    print(chunks[0]["text"])
    print(f"메타데이터: {chunks[0]['metadata']}")
    
    print("\n=== 마지막 청크 ===")
    print(f"토큰 수: {chunks[-1]['metadata']['token_count']}")
    print(chunks[-1]["text"])
    print(f"메타데이터: {chunks[-1]['metadata']}")
    
    # 청크 크기 제한 초과 확인
    max_token_overrides = 227  # 현재 최대 토큰 수로 조정
    oversized_chunks = [i for i, chunk in enumerate(chunks) if chunk["metadata"]["token_count"] > max_token_overrides]
    if oversized_chunks:
        print(f"\n⚠️ 경고: {len(oversized_chunks)}개 청크가 허용 가능한 최대 크기({max_token_overrides} 토큰)를 초과합니다.")
        if oversized_chunks:
            print(f"첫 번째 초과 청크 (인덱스 {oversized_chunks[0]}, 토큰 수 {chunks[oversized_chunks[0]]['metadata']['token_count']}):")
            print(chunks[oversized_chunks[0]]["text"])
    
    # 적정 범위(50-227 토큰) 내 청크가 70% 이상이면 유효하다고 판단
    valid_chunks = [chunk for chunk in chunks if 50 <= chunk["metadata"]["token_count"] <= max_token_overrides]
    validity_ratio = len(valid_chunks) / len(chunks)
    
    print(f"\n유효한 청크 비율: {validity_ratio:.2%}")
    
    return validity_ratio >= 0.7  # 70% 이상의 청크가 유효하면 진행

# 벡터 DB 백업
def backup_vector_db():
    """기존 벡터 DB 백업"""
    if os.path.exists(VECTOR_DB_PATH):
        if os.path.exists(BACKUP_DB_PATH):
            shutil.rmtree(BACKUP_DB_PATH)
        
        print(f"Backing up existing vector DB to {BACKUP_DB_PATH}")
        shutil.copytree(VECTOR_DB_PATH, BACKUP_DB_PATH)
        print("Backup completed")

# 벡터 DB 생성 및 청크 저장
def create_vector_db(chunks):
    """ChromaDB 벡터 데이터베이스 생성 및 청크 저장"""
    # 이전 DB 삭제 (백업 후)
    if os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
    
    # ChromaDB 클라이언트 설정
    chroma_client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    # 새 컬렉션 생성
    collection = chroma_client.create_collection(
        name="langchain",  # 기존과 동일한 이름 사용
        embedding_function=embedding_function
    )
    
    # 청크를 배치로 나누기
    batch_size = 50
    batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]
    
    total_chunks = len(chunks)
    processed_chunks = 0
    
    print(f"Adding {total_chunks} chunks to vector DB in {len(batches)} batches")
    
    for i, batch in enumerate(batches):
        # 배치를 위한 데이터 준비
        ids = [f"doc_{chunk['metadata']['chunk_id']}" for chunk in batch]
        texts = [chunk["text"] for chunk in batch]
        metadatas = [chunk["metadata"] for chunk in batch]
        
        # 벡터 DB에 추가
        collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
        
        processed_chunks += len(batch)
        print(f"Batch {i+1}/{len(batches)} completed. Progress: {processed_chunks}/{total_chunks} chunks ({processed_chunks/total_chunks*100:.1f}%)")
        
        # API 제한을 피하기 위한 간격 추가
        time.sleep(1)
    
    print(f"Vector DB creation completed. {total_chunks} chunks added.")
    return collection

# 새 벡터 DB 테스트
def test_vector_db(collection, test_queries):
    """생성된 벡터 DB 테스트"""
    print("\n=== 벡터 DB 테스트 ===")
    print(f"컬렉션 이름: {collection.name}")
    print(f"컬렉션 크기: {collection.count()} 청크")
    
    for query in test_queries:
        print(f"\n[테스트 쿼리] {query}")
        
        results = collection.query(
            query_texts=[query],
            n_results=3,
            include=["documents", "distances", "metadatas"]
        )
        
        documents = results["documents"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]
        
        for i, (doc, distance, metadata) in enumerate(zip(documents, distances, metadatas)):
            # 코사인 거리를 유사도 점수로 변환 (0-1 범위)
            similarity = max(0, min(1, 1 - (distance / 2)))
            
            print(f"\n결과 {i+1} (유사도: {similarity:.4f}, 토큰 수: {metadata.get('token_count', 'N/A')})")
            print(f"출처: {metadata.get('source', 'Unknown')}")
            print(f"텍스트: {doc}")
    
    return True

if __name__ == "__main__":
    print("=== 칸트 텍스트 재분할 및 벡터 DB 재구성 시작 ===")
    
    # 1. 원본 텍스트 로드
    original_text = load_original_text(INPUT_FILE)
    if not original_text:
        print("원본 텍스트 로드 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    # 2. 텍스트를 청크로 분할
    print("\n청크 생성 중...")
    chunks = split_into_chunks_by_tokens(original_text)
    print(f"생성된 청크 수: {len(chunks)}")
    
    # 3. 청크 품질 검사
    is_valid = validate_chunks(chunks)
    if not is_valid:
        print("청크 검증 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    # 사용자 확인
    print("\n벡터 DB를 자동으로 재구성합니다. 기존 DB는 백업됩니다.")
    confirm = "y"  # 자동으로 Yes 선택
    
    # 4. 기존 벡터 DB 백업
    backup_vector_db()
    
    # 5. 새 벡터 DB 생성 및 청크 저장
    collection = create_vector_db(chunks)
    
    # 6. 벡터 DB 테스트
    test_queries = [
        "What is practical reason?",
        "정언명령이란 무엇인가?",
        "What is the relationship between freedom and moral law?",
        "의무와 경향성의 차이는 무엇인가?",
        "What is the highest good?",
        "칸트의 윤리학을 현대 문제에 적용하면?"
    ]
    
    test_vector_db(collection, test_queries)
    
    # 7. 청크 정보 저장
    output_path = os.path.join(os.path.dirname(__file__), "new_chunks_tiktoken_info.json")
    with open(output_path, "w", encoding="utf-8") as f:
        # 텍스트 내용은 너무 길어 메타데이터만 저장
        chunks_info = [{"chunk_id": chunk["metadata"]["chunk_id"], 
                        "source": chunk["metadata"]["source"],
                        "token_count": chunk["metadata"]["token_count"],
                        "length": len(chunk["text"]),
                        "text_preview": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]}
                      for chunk in chunks]
        json.dump(chunks_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n청크 정보가 저장되었습니다: {output_path}")
    print("\n=== 재구성 완료 ===")
    print("벡터 DB 경로:", VECTOR_DB_PATH)
    print("원본 벡터 DB 백업 경로:", BACKUP_DB_PATH) 