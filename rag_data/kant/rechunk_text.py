import os
import sys
import json
import re
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import openai
from openai import OpenAI
import time
import hashlib
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

# 원본 텍스트 파일 경로
INPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "critique_of_practical_reason.txt")

# 벡터 DB 경로 설정
VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db")
BACKUP_DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db_backup")

# 청크 설정
TARGET_CHUNK_SIZE = 350  # 목표 청크 크기 (글자 수)
MIN_CHUNK_SIZE = 150     # 최소 청크 크기
MAX_CHUNK_SIZE = 600     # 최대 청크 크기 (500에서 600으로 증가)
CHUNK_OVERLAP = 50       # 청크 간 중복 크기

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

# 텍스트를 문장으로 분할하는 간단한 함수 (NLTK 대신 정규식 사용)
def split_into_sentences(text):
    """텍스트를 문장으로 분할 (정규식 사용)"""
    # 문장 구분 패턴: 마침표, 느낌표, 물음표 뒤에 공백이 있는 경우
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로 통일
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

# 텍스트를 의미 있는 청크로 분할
def split_into_chunks(text, target_size=TARGET_CHUNK_SIZE, min_size=MIN_CHUNK_SIZE, 
                     max_size=MAX_CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """텍스트를 의미 있는 단위로 청크 분할"""
    # 전처리: 불필요한 공백 제거 및 프로젝트 구텐베르크 헤더 제거
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 문단 분할
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # 문단이 너무 길면 문장 단위로 분할
        if len(para) > max_size:
            sentences = split_into_sentences(para)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 단일 문장이 최대 크기를 초과하는 경우 강제로 분할
                if len(sentence) > max_size:
                    words = sentence.split()
                    temp_sentence = ""
                    
                    for word in words:
                        if len(temp_sentence) + len(word) + 1 > max_size:
                            if len(temp_sentence) >= min_size:
                                # 현재 청크에 추가할 수 있는지 확인
                                if len(current_chunk) + len(temp_sentence) + 1 <= max_size:
                                    current_chunk = (current_chunk + " " + temp_sentence).strip()
                                else:
                                    # 현재 청크가 최소 크기를 넘으면 저장하고 새 청크 시작
                                    if len(current_chunk) >= min_size:
                                        chunks.append(current_chunk)
                                        # 중복을 위해 마지막 부분 유지
                                        if overlap > 0 and len(current_chunk) > overlap:
                                            current_chunk = current_chunk[-overlap:] + " " + temp_sentence
                                        else:
                                            current_chunk = temp_sentence
                                    else:
                                        # 현재 청크가 너무 작으면 계속 추가
                                        current_chunk = (current_chunk + " " + temp_sentence).strip()
                            else:
                                # temp_sentence가 너무 작으면 현재 청크에 그냥 추가
                                current_chunk = (current_chunk + " " + temp_sentence).strip()
                                
                            # 새 문장 시작
                            temp_sentence = word
                        else:
                            # 단어 추가
                            temp_sentence = (temp_sentence + " " + word).strip()
                    
                    # 마지막 부분 처리
                    if temp_sentence:
                        if len(current_chunk) + len(temp_sentence) + 1 <= max_size:
                            current_chunk = (current_chunk + " " + temp_sentence).strip()
                        else:
                            if len(current_chunk) >= min_size:
                                chunks.append(current_chunk)
                                current_chunk = temp_sentence
                            else:
                                current_chunk = (current_chunk + " " + temp_sentence).strip()
                else:
                    # 일반 문장 추가
                    if len(current_chunk) + len(sentence) + 1 <= max_size:
                        # 현재 청크에 문장 추가
                        current_chunk = (current_chunk + " " + sentence).strip()
                    else:
                        # 현재 청크가 최소 크기 이상이면 저장
                        if len(current_chunk) >= min_size:
                            chunks.append(current_chunk)
                            
                            # 중복을 위해 마지막 부분 유지
                            if overlap > 0 and len(current_chunk) > overlap:
                                # 이전 청크의 마지막 부분 + 새 문장
                                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                                current_chunk = (overlap_text + " " + sentence).strip()
                                
                                # 중복 부분이 최대 크기를 초과하면 새로 시작
                                if len(current_chunk) > max_size:
                                    current_chunk = sentence
                            else:
                                current_chunk = sentence
                        else:
                            # 최소 크기에 도달하지 않았다면 강제로 추가
                            current_chunk = (current_chunk + " " + sentence).strip()
                            
                            # 그래도 최대 크기를 초과하면 분할해서 저장
                            if len(current_chunk) > max_size:
                                chunks.append(current_chunk[:max_size])
                                current_chunk = current_chunk[max_size:].strip()
        else:
            # 문단 전체가 최대 크기 내에 있는 경우
            if len(current_chunk) + len(para) + 1 <= max_size:
                # 현재 청크에 문단 추가
                current_chunk = (current_chunk + " " + para).strip()
            else:
                # 현재 청크가 최소 크기 이상이면 저장
                if len(current_chunk) >= min_size:
                    chunks.append(current_chunk)
                    
                    # 중복을 위해 마지막 부분 유지
                    if overlap > 0 and len(current_chunk) > overlap:
                        overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                        current_chunk = (overlap_text + " " + para).strip()
                        
                        # 중복 부분이 최대 크기를 초과하면 새로 시작
                        if len(current_chunk) > max_size:
                            current_chunk = para
                    else:
                        current_chunk = para
                else:
                    # 최소 크기에 도달하지 않았다면 강제로 추가
                    current_chunk = (current_chunk + " " + para).strip()
                    
                    # 그래도 최대 크기를 초과하면 분할해서 저장
                    if len(current_chunk) > max_size:
                        chunks.append(current_chunk[:max_size])
                        current_chunk = current_chunk[max_size:].strip()
    
    # 마지막 청크 추가
    if current_chunk and len(current_chunk) >= min_size:
        chunks.append(current_chunk)
    elif current_chunk:
        # 마지막 청크가 최소 크기보다 작으면 마지막-1 청크와 합침
        if chunks:
            last_chunk = chunks.pop()
            combined = (last_chunk + " " + current_chunk).strip()
            
            # 합쳐도 최대 크기를 초과하지 않으면 합친 청크 추가
            if len(combined) <= max_size:
                chunks.append(combined)
            else:
                # 초과하면 분리하여 추가
                chunks.append(last_chunk)
                if len(current_chunk) >= min_size:
                    chunks.append(current_chunk)
    
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
        
        chunks_with_metadata.append({
            "text": chunk,
            "metadata": {
                "source": chapter_info,
                "chunk_id": f"kant_chunk_{i+1}",
                "original_order": i+1
            }
        })
    
    return chunks_with_metadata

# 청크 품질 검사
def validate_chunks(chunks, min_size=MIN_CHUNK_SIZE, max_size=MAX_CHUNK_SIZE):
    """생성된 청크의 품질 검사"""
    lengths = [len(chunk["text"]) for chunk in chunks]
    
    print(f"\n=== 청크 통계 ===")
    print(f"총 청크 수: {len(chunks)}")
    print(f"평균 길이: {sum(lengths) / len(lengths):.2f} 글자")
    print(f"최소 길이: {min(lengths)} 글자")
    print(f"최대 길이: {max(lengths)} 글자")
    
    # 크기별 분포
    size_ranges = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500), (500, 600), (600, float('inf'))]
    
    distribution = {f"{s}-{e if e != float('inf') else '이상'}": 0 for s, e in size_ranges}
    for length in lengths:
        for start, end in size_ranges:
            if start <= length < end:
                distribution[f"{start}-{end if end != float('inf') else '이상'}"] += 1
                break
    
    print("\n=== 청크 길이 분포 ===")
    for range_str, count in distribution.items():
        print(f"{range_str} 글자: {count}개 청크 ({count/len(chunks)*100:.1f}%)")
    
    # 첫 번째와 마지막 청크 내용 출력
    print("\n=== 첫 번째 청크 ===")
    print(chunks[0]["text"][:200] + "..." if len(chunks[0]["text"]) > 200 else chunks[0]["text"])
    print(f"메타데이터: {chunks[0]['metadata']}")
    
    print("\n=== 마지막 청크 ===")
    print(chunks[-1]["text"][:200] + "..." if len(chunks[-1]["text"]) > 200 else chunks[-1]["text"])
    print(f"메타데이터: {chunks[-1]['metadata']}")
    
    # 청크 크기 제한 초과 확인
    oversized_chunks = [i for i, chunk in enumerate(chunks) if len(chunk["text"]) > max_size]
    if oversized_chunks:
        print(f"\n⚠️ 경고: {len(oversized_chunks)}개 청크가 최대 크기({max_size} 글자)를 초과합니다.")
        print(f"첫 번째 초과 청크 (인덱스 {oversized_chunks[0]}, 길이 {len(chunks[oversized_chunks[0]]['text'])} 글자):")
        print(chunks[oversized_chunks[0]]["text"][:200] + "...")
        
        # 초과 비율이 크지 않으면 경고만 표시
        if len(oversized_chunks) / len(chunks) < 0.05:  # 5% 미만이면 허용
            print(f"초과 비율이 5% 미만이므로 무시합니다.")
            oversized_chunks = []
    
    # 허용하는 청크가 80% 이상이면 진행 (90%에서 80%로 완화)
    valid_chunks = [chunk for chunk in chunks if min_size <= len(chunk["text"]) <= max_size]
    validity_ratio = len(valid_chunks) / len(chunks)
    
    print(f"\n유효한 청크 비율: {validity_ratio:.2%}")
    
    return validity_ratio >= 0.8  # 80% 이상의 청크가 유효하면 진행

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
            
            print(f"\n결과 {i+1} (유사도: {similarity:.4f})")
            print(f"출처: {metadata.get('source', 'Unknown')}")
            print(f"텍스트: {doc[:200]}..." if len(doc) > 200 else doc)
    
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
    chunks = split_into_chunks(original_text)
    print(f"생성된 청크 수: {len(chunks)}")
    
    # 3. 청크 품질 검사
    is_valid = validate_chunks(chunks)
    if not is_valid:
        print("청크 검증 실패. 프로그램을 종료합니다.")
        sys.exit(1)
    
    # 사용자 확인
    confirm = input("\n벡터 DB를 재구성하시겠습니까? 기존 DB는 백업됩니다. (y/n): ")
    if confirm.lower() != 'y':
        print("사용자가 취소했습니다. 프로그램을 종료합니다.")
        sys.exit(0)
    
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
    output_path = os.path.join(os.path.dirname(__file__), "new_chunks_info.json")
    with open(output_path, "w", encoding="utf-8") as f:
        # 텍스트 내용은 너무 길어 메타데이터만 저장
        chunks_info = [{"chunk_id": chunk["metadata"]["chunk_id"], 
                        "source": chunk["metadata"]["source"],
                        "length": len(chunk["text"]),
                        "text_preview": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]}
                      for chunk in chunks]
        json.dump(chunks_info, f, ensure_ascii=False, indent=2)
    
    print(f"\n청크 정보가 저장되었습니다: {output_path}")
    print("\n=== 재구성 완료 ===")
    print("벡터 DB 경로:", VECTOR_DB_PATH)
    print("원본 벡터 DB 백업 경로:", BACKUP_DB_PATH) 