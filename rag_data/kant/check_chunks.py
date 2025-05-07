import os
import sys
import json
import re
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import openai
import statistics
from collections import Counter

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

# ChromaDB 클라이언트 설정
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "vector_db"))
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

# 컬렉션 가져오기 - 기존에 있는 langchain 컬렉션 사용
collection = chroma_client.get_collection(name="langchain", embedding_function=embedding_function)

def analyze_chunks():
    """벡터 DB에 저장된 청크들의 특성을 분석"""
    print(f"컬렉션 이름: {collection.name}")
    count = collection.count()
    print(f"총 청크 수: {count}")
    
    # 모든 청크 가져오기
    all_chunks = collection.get(include=["documents", "metadatas"])
    documents = all_chunks["documents"]
    metadatas = all_chunks["metadatas"]
    
    # 청크 길이 분석
    chunk_lengths = [len(doc) for doc in documents]
    avg_length = sum(chunk_lengths) / len(chunk_lengths)
    max_length = max(chunk_lengths)
    min_length = min(chunk_lengths)
    median_length = statistics.median(chunk_lengths)
    stdev_length = statistics.stdev(chunk_lengths) if len(chunk_lengths) > 1 else 0
    
    # 단어 수 분석
    word_counts = [len(doc.split()) for doc in documents]
    avg_words = sum(word_counts) / len(word_counts)
    max_words = max(word_counts)
    min_words = min(word_counts)
    median_words = statistics.median(word_counts)
    stdev_words = statistics.stdev(word_counts) if len(word_counts) > 1 else 0
    
    # 문장 수 분석
    sentence_pattern = re.compile(r'[.!?]+')
    sentence_counts = [len(sentence_pattern.findall(doc)) + 1 for doc in documents]
    avg_sentences = sum(sentence_counts) / len(sentence_counts)
    max_sentences = max(sentence_counts)
    min_sentences = min(sentence_counts)
    
    # 소스 분석
    sources = [metadata.get("source", "Unknown") for metadata in metadatas]
    source_counts = Counter(sources)
    
    # 청크 시작/끝 패턴 분석
    start_patterns = [doc[:50].strip() for doc in documents]
    start_pattern_counts = Counter([pattern.split()[0] if pattern.split() else "" for pattern in start_patterns])
    
    # 결과 출력
    print("\n=== 청크 길이 분석 ===")
    print(f"평균 길이: {avg_length:.2f} 글자")
    print(f"최대 길이: {max_length} 글자")
    print(f"최소 길이: {min_length} 글자")
    print(f"중앙값 길이: {median_length} 글자")
    print(f"표준 편차: {stdev_length:.2f} 글자")
    
    print("\n=== 단어 수 분석 ===")
    print(f"평균 단어 수: {avg_words:.2f} 단어")
    print(f"최대 단어 수: {max_words} 단어")
    print(f"최소 단어 수: {min_words} 단어")
    print(f"중앙값 단어 수: {median_words} 단어")
    print(f"표준 편차: {stdev_words:.2f} 단어")
    
    print("\n=== 문장 수 분석 ===")
    print(f"평균 문장 수: {avg_sentences:.2f} 문장")
    print(f"최대 문장 수: {max_sentences} 문장")
    print(f"최소 문장 수: {min_sentences} 문장")
    
    print("\n=== 소스 분석 ===")
    for source, count in source_counts.most_common():
        print(f"{source}: {count}개 청크 ({count/len(sources)*100:.1f}%)")
    
    print("\n=== 청크 시작 패턴 분석 ===")
    for pattern, count in start_pattern_counts.most_common(10):
        if pattern:
            print(f"'{pattern}': {count}개 청크 ({count/len(start_patterns)*100:.1f}%)")
    
    # 샘플 청크 출력
    print("\n=== 샘플 청크 (최대 길이, 최소 길이, 중앙값 길이) ===")
    max_idx = chunk_lengths.index(max_length)
    min_idx = chunk_lengths.index(min_length)
    median_idx = chunk_lengths.index(min(chunk_lengths, key=lambda x: abs(x - median_length)))
    
    print(f"\n[최대 길이 청크 ({max_length} 글자, {word_counts[max_idx]} 단어)]")
    print(f"소스: {metadatas[max_idx].get('source', 'Unknown')}")
    print(documents[max_idx][:500] + "..." if len(documents[max_idx]) > 500 else documents[max_idx])
    
    print(f"\n[최소 길이 청크 ({min_length} 글자, {word_counts[min_idx]} 단어)]")
    print(f"소스: {metadatas[min_idx].get('source', 'Unknown')}")
    print(documents[min_idx])
    
    print(f"\n[중앙값 길이 청크 ({len(documents[median_idx])} 글자, {word_counts[median_idx]} 단어)]")
    print(f"소스: {metadatas[median_idx].get('source', 'Unknown')}")
    print(documents[median_idx][:500] + "..." if len(documents[median_idx]) > 500 else documents[median_idx])
    
    # 길이 분포 히스토그램 데이터 준비
    length_ranges = [
        (0, 100), (100, 200), (200, 500), (500, 1000), 
        (1000, 2000), (2000, 5000), (5000, 10000), (10000, float('inf'))
    ]
    
    length_distribution = {f"{start}-{end if end != float('inf') else '이상'}": 0 for start, end in length_ranges}
    for length in chunk_lengths:
        for start, end in length_ranges:
            if start <= length < end:
                length_distribution[f"{start}-{end if end != float('inf') else '이상'}"] += 1
                break
    
    print("\n=== 청크 길이 분포 ===")
    for range_str, count in length_distribution.items():
        print(f"{range_str} 글자: {count}개 청크 ({count/len(chunk_lengths)*100:.1f}%)")
    
    return {
        "total_chunks": count,
        "avg_length": avg_length,
        "max_length": max_length,
        "min_length": min_length,
        "median_length": median_length,
        "stdev_length": stdev_length,
        "avg_words": avg_words,
        "length_distribution": length_distribution,
        "source_distribution": {source: count for source, count in source_counts.most_common()}
    }

if __name__ == "__main__":
    print("ChromaDB 청크 분석 시작...")
    stats = analyze_chunks()
    
    # 결과를 JSON 파일로 저장
    output_path = os.path.join(os.path.dirname(__file__), "chunk_stats.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\n분석 결과가 저장되었습니다: {output_path}") 