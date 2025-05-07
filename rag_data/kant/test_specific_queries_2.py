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
from typing import List, Dict, Any, Tuple

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

# ChromaDB 클라이언트 설정
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "vector_db"))
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai_api_key,
    model_name="text-embedding-3-small"
)

# 컬렉션 가져오기 - 기존에 있는 langchain 컬렉션 사용
collection = chroma_client.get_collection(name="langchain", embedding_function=embedding_function)

# 원본 텍스트 파일 경로 및 ID 생성 규칙
ORIGINAL_TEXT_DIR = os.path.join(os.path.dirname(__file__), "raw_texts")
SOURCE_TO_FILENAME = {
    "The Critique of Pure Reason": "critique_of_pure_reason.txt",
    "The Critique of Practical Reason": "critique_of_practical_reason.txt", 
    "The Critique Of Judgment": "critique_of_judgment.txt"
}

# sentence_to_paragraph_map.json 파일 경로
PARAGRAPH_MAP_PATH = os.path.join(os.path.dirname(__file__), "../kant_new/sentence_to_paragraph_map.json")

# 문장-문단 매핑 데이터 로드
sentence_to_paragraph_map = {}
paragraph_contents = []
try:
    if os.path.exists(PARAGRAPH_MAP_PATH):
        with open(PARAGRAPH_MAP_PATH, 'r', encoding='utf-8') as f:
            sentence_to_paragraph_map = json.load(f)
        print(f"성공적으로 sentence_to_paragraph_map.json 파일을 로드했습니다. "
              f"매핑된 문장 수: {len(sentence_to_paragraph_map)}")
        
        # 모든 문단 내용을 별도의 리스트로 저장하여 검색 용이성 증가
        for sentence_id, data in sentence_to_paragraph_map.items():
            paragraph_content = data.get("paragraph_content", "")
            book_title = data.get("book_title", "")
            if paragraph_content and paragraph_content not in [p["content"] for p in paragraph_contents]:
                paragraph_contents.append({
                    "content": paragraph_content,
                    "book_title": book_title,
                    "sentence_id": sentence_id
                })
        print(f"고유한 문단 수: {len(paragraph_contents)}")
    else:
        print(f"경고: sentence_to_paragraph_map.json 파일을 찾을 수 없습니다. "
              f"경로: {PARAGRAPH_MAP_PATH}")
        paragraph_contents = []
except Exception as e:
    print(f"sentence_to_paragraph_map.json 파일 로드 중 오류: {str(e)}")
    paragraph_contents = []

# 거리를 유사도로 변환하는 함수
def distance_to_similarity(distance):
    """ChromaDB의 거리값을 0~1 범위의 유사도 점수로 변환"""
    if distance is None:
        return None
    # 코사인 거리값은 0~2 범위임 (0=완전 동일, 2=완전 반대)
    # 유사도로 변환: 1 - distance/2 (0~1 범위)
    return max(0, min(1, 1 - (distance / 2)))

def translate_korean_to_english(korean_text):
    """한국어 텍스트를 영어로 번역"""
    try:
        print(f"\n[번역 요청] 한국어: {korean_text}")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional Korean to English translator. Your task is to accurately translate Korean text to English. Translate ONLY the text provided, without any additional explanation or context."},
                {"role": "user", "content": f"Translate this Korean text to English: {korean_text}"}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        english_text = response.choices[0].message.content.strip()
        print(f"[번역 결과] 영어: {english_text}")
        return english_text
        
    except Exception as e:
        print(f"번역 오류: {str(e)}")
        return korean_text  # 오류 시 원본 텍스트 반환

def query_vector_db(query, n_results=5):
    """벡터 DB에 쿼리하여 관련 텍스트 조각 검색"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "distances", "metadatas"]
    )
    
    return results

def find_paragraph_by_text_pattern(chunk_text, source_name=None):
    """
    청크 텍스트를 이용해 문단 매핑 데이터에서 유사한 문단 찾기
    
    Args:
        chunk_text: 검색할 청크 텍스트
        source_name: 출처 이름 (옵션)
        
    Returns:
        찾은 문단 내용, 찾지 못하면 None
    """
    # 매핑 데이터가 없으면 None 반환
    if not paragraph_contents:
        return None
    
    # 검색할 텍스트 준비 (100자 이내의 특징적인 문구 선택)
    # 전체 청크에서 특징적인 부분 추출 (시작 부분, 중간 부분, 또는 주요 구문)
    search_texts = []
    
    # 검색 1: 시작 부분 (40자)
    if len(chunk_text) > 40:
        search_texts.append(chunk_text[:40].strip())
    else:
        search_texts.append(chunk_text.strip())
    
    # 검색 2: 중간 부분 (30자)
    if len(chunk_text) > 60:
        mid_point = len(chunk_text) // 2
        search_texts.append(chunk_text[mid_point-15:mid_point+15].strip())
    
    # 검색 3: 특징적인 단어나 구문 (3-4단어의 연속)
    words = chunk_text.split()
    if len(words) > 5:
        for i in range(len(words) - 3):
            if len(' '.join(words[i:i+4])) > 15:  # 충분히 고유한 패턴
                search_texts.append(' '.join(words[i:i+4]))
                break
    
    # 출처 필터링
    filtered_paragraphs = paragraph_contents
    if source_name:
        filtered_paragraphs = [p for p in paragraph_contents if p["book_title"] == source_name]
    
    # 각 검색 텍스트로 시도
    for search_text in search_texts:
        for paragraph in filtered_paragraphs:
            if search_text in paragraph["content"]:
                return paragraph["content"]
    
    return None

def extract_full_paragraph(chunk_text, source_name, metadata=None):
    """
    청크 텍스트에 해당하는 전체 문단 추출
    
    Args:
        chunk_text: 검색된 청크 텍스트
        source_name: 출처 이름 (The Critique of Pure Reason 등)
        metadata: 청크 메타데이터 (옵션)
        
    Returns:
        전체 문단, 찾지 못하면 원본 청크
    """
    # 1. 문장-문단 매핑에서 특징적인 텍스트 패턴으로 검색
    paragraph_content = find_paragraph_by_text_pattern(chunk_text, source_name)
    if paragraph_content:
        print(f"[성공] 패턴 매칭으로 전체 문단을 찾았습니다.")
        return paragraph_content
    
    # 2. 원본 텍스트 파일에서 직접 검색
    # 출처 이름을 파일명으로 변환
    if source_name not in SOURCE_TO_FILENAME:
        print(f"[경고] 알 수 없는 출처: {source_name}. 원본 청크를 그대로 사용합니다.")
        return chunk_text
    
    filename = SOURCE_TO_FILENAME[source_name]
    full_path = os.path.join(ORIGINAL_TEXT_DIR, filename)
    
    # 파일이 존재하는지 확인
    if not os.path.exists(full_path):
        print(f"[경고] 파일을 찾을 수 없음: {full_path}. 원본 청크를 그대로 사용합니다.")
        return chunk_text
    
    try:
        # 파일 읽기
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 검색 패턴 추출 (청크의 특징적인 부분)
        search_patterns = []
        
        # 패턴 1: 첫 40자 (또는 전체 텍스트)
        if len(chunk_text) > 40:
            search_patterns.append(re.escape(chunk_text[:40].strip()))
        else:
            search_patterns.append(re.escape(chunk_text.strip()))
        
        # 패턴 2: 특징적인 구문 (공백, 마침표 등으로 구분된 10-20자 구문)
        words = chunk_text.split()
        if len(words) >= 5:
            for i in range(len(words) - 4):
                phrase = ' '.join(words[i:i+5])
                if 15 <= len(phrase) <= 40:
                    search_patterns.append(re.escape(phrase))
                    break
        
        # 각 패턴으로 검색 시도
        for pattern in search_patterns:
            # 패턴 주변의 문단 추출
            matches = re.search(pattern, content)
            if matches:
                # 패턴이 있는 위치 찾기
                start_pos = matches.start()
                
                # 문단 경계 찾기
                paragraph_start = content.rfind("\n\n", max(0, start_pos - 1000), start_pos)
                if paragraph_start == -1:
                    paragraph_start = max(0, start_pos - 500)
                
                paragraph_end = content.find("\n\n", start_pos, min(len(content), start_pos + 1000))
                if paragraph_end == -1:
                    paragraph_end = min(len(content), start_pos + 500)
                
                # 문단 추출
                paragraph = content[paragraph_start:paragraph_end].strip()
                print(f"[성공] 원본 텍스트에서 패턴 '{pattern[:20]}...'에 해당하는 문단을 찾았습니다.")
                return paragraph
        
        # 간단한 포함 여부로 다시 시도
        if chunk_text[:50] in content:
            start_idx = content.find(chunk_text[:50])
            context_start = max(0, start_idx - 500)
            context_end = min(len(content), start_idx + len(chunk_text[:50]) + 500)
            
            # 확장된 범위에서 더 정확한 문단 경계 찾기
            paragraph_start = content.rfind("\n\n", context_start, start_idx)
            paragraph_end = content.find("\n\n", start_idx, context_end)
            
            # 문단 경계를 찾지 못하면 그냥 앞뒤 500자 사용
            if paragraph_start == -1:
                paragraph_start = context_start
            if paragraph_end == -1:
                paragraph_end = context_end
                
            print(f"[대체] 원본 텍스트에서 청크 시작 부분으로 문단을 추출했습니다.")
            return content[paragraph_start:paragraph_end].strip()
        
        print(f"[경고] 원본 텍스트에서 청크를 찾지 못했습니다. 원본 청크를 그대로 사용합니다.")
        return chunk_text
        
    except Exception as e:
        print(f"[오류] 원본 텍스트 파일 처리 중 오류 발생: {str(e)}. 원본 청크를 그대로 사용합니다.")
        return chunk_text

def test_specific_queries_with_paragraphs():
    """특정 쿼리로 RAG 성능 테스트 - 원본 test_specific_queries.py와 동일한 쿼리 및 프롬프팅 사용"""
    
    # 철학적 주장이 담긴 한국어 문장들 - 원본 test_specific_queries.py와 동일하게 맞춤
    korean_queries = [
        "유전자 편집 기술에 대한 논의는 이 기술이 보편적 도덕 법칙으로 수용될 수 있는지를 숙고해야 합니다. 정언 명령의 관점에서, 이러한 기술이 모든 인류에게 유익하고 자연과 조화를 이룬다면, 그것은 도덕적으로 정당화될 수 있습니다. 기술의 발전이 인류 전체에 긍정적인 결과를 가져올 수 있는지 깊이 있는 논의가 필요합니다.",
        "사형제도에 대해 논의할 때, 우리는 도덕적 원칙과 인간의 존엄성에 대한 의무를 고려해야 합니다. 사형은 인간 생명의 고유한 가치를 부정할 수 있으며, 이는 도덕법칙에 어긋날 수 있습니다. 우리는 법에 대한 존중과 인간성에 대한 의무 사이의 균형을 찾는 것이 중요하다고 할 수 있습니다.",
        "자율 무기 시스템이 인간의 생사결정을 기계에게 맡긴다는 점에서, 인간을 단지 수단으로 대우하는 결과가 아닐까요? 이건 정언명령에 명백히 어긋나는 것 같습니다.",
        "인간의 이익을 위해 동물에게 고통을 주는 게 정당화되려면, 그 행위가 자연 법칙으로 보편화되어도 괜찮아야 하지 않나요? 그런데 그걸 상상하는 순간부터 뭔가 문제가 있다고 느껴집니다.",
        "개인의 자유나 프라이버시를 침해하면서까지 공공의 안전을 확보하려는 시도는, 인간을 수단으로 다루는 것 아닐까요? 칸트적 입장에선 받아들일 수 없을 것 같아요.",
        "기억을 조작해서 고통을 지우는 게 윤리적으로 정당한가요? 그건 자율적 존재로서의 인간 정체성을 훼손하는 일이기도 하고, 정언명령의 기준으로도 문제가 될 수 있어 보입니다.",
        "노동하지 않고도 생계를 유지하는 기본소득제는 자율적 존재로서 인간의 존엄성을 보장하는 제도일 수 있을 것 같아요. '목적 자체로서의 인간'이라는 칸트의 관점에서 보면 긍정적인 해석도 가능하지 않을까요?",
        "온라인에서라도 거짓 정보를 퍼뜨리는 건, '모든 사람이 거짓말을 해도 되는 사회'를 상상했을 때 성립할 수 없는 행위 아닌가요? 그럼 도덕적으로 옳지 않은 거죠."
    ]
    
    results = []
    
    # 각 문장을 영어로 번역하고 RAG 검색 수행
    for i, kr_query in enumerate(korean_queries):
        # 쿼리 이름 설정 - 원본과 동일
        query_names = [
            "유전자 편집", 
            "사형제도", 
            "AI 자율무기", 
            "동물 실험", 
            "감시 사회와 프라이버시", 
            "기억 삭제 기술", 
            "기본소득제", 
            "SNS 거짓말"
        ]
        query_name = query_names[i] if i < len(query_names) else f"쿼리 {i+1}"
        
        print(f"\n\n{'='*80}")
        print(f"쿼리 {i+1}: {query_name}")
        print(f"{'='*80}")
        
        # 번역 수행
        en_query = translate_korean_to_english(kr_query)
        
        # 영어 쿼리로 검색
        print(f"\n[영어 쿼리 검색 결과]")
        search_results = query_vector_db(en_query, n_results=5)
        retrieved_texts = search_results["documents"][0]
        distances = search_results["distances"][0] if "distances" in search_results else None
        metadatas = search_results["metadatas"][0] if "metadatas" in search_results else None
        
        # 거리값 로깅
        print(f"검색된 거리값(distances): {distances}")
        
        # 검색된 텍스트와 유사도 점수 출력 + 원본 파일에서 전체 문단 추출
        chunk_details = []
        for j, (text, distance) in enumerate(zip(retrieved_texts, distances if distances else [None] * len(retrieved_texts))):
            similarity = distance_to_similarity(distance)
            similarity_text = f"유사도: {similarity:.4f}" if similarity is not None else "유사도: N/A"
            metadata = metadatas[j] if metadatas and j < len(metadatas) else {}
            source = metadata.get("source", "Unknown")
            
            print(f"\n--- 청크 {j+1} ({similarity_text}, 출처: {source}) ---")
            print(f"{text[:150]}..." if len(text) > 150 else text)
            
            # kant_new의 sentence_to_paragraph_map.json 또는 원본 파일에서 전체 문단 추출
            full_paragraph = extract_full_paragraph(text, source, metadata)
            
            print(f"\n>>> 전체 문단 >>>")
            print(f"{full_paragraph[:200]}..." if len(full_paragraph) > 200 else full_paragraph)
            
            chunk_details.append({
                "text": text,
                "raw_distance": float(distance) if distance is not None else None,
                "similarity": float(similarity) if similarity is not None else None,
                "metadata": metadata,
                "full_paragraph": full_paragraph
            })
        
        # 주장 강화를 위한 추가 컨텍스트 생성 - 원본 test_specific_queries.py와 유사하게 구성
        print("\n\n[원본 주장 강화를 위한 컨텍스트 생성]")
        
        # 전체 문단을 컨텍스트로 사용 (원본 test_specific_queries.py와의 차이점)
        retrieved_contexts = "\n\n".join([f"Source {j+1} ({chunk['metadata'].get('source', 'Unknown')}): {chunk['full_paragraph']}" 
                                         for j, chunk in enumerate(chunk_details)])
        
        enhancement_prompt = f"""
Based on the following philosophical statement:

"{en_query}"

And these relevant excerpts from my works (complete paragraphs):

{retrieved_contexts}

Respond AS IF YOU ARE IMMANUEL KANT HIMSELF, speaking in first person. Do not refer to "Kant" or "Kant's philosophy" in third person. Instead, use "I," "my philosophy," "my categorical imperative," etc.

Create a natural, conversational response that maintains rigorous philosophical integrity while explaining your position on the topic. The response should:

1. Skip formal greetings like "안녕하세요" or "오늘의 주제에 대해 논의하게 되어 기쁩니다" - instead, jump directly into the philosophical discussion in a conversational manner
2. Present your core philosophical principle relevant to this topic, citing the ACTUAL SOURCE (Critique of Pure Reason, Critique of Practical Reason, or Critique of Judgment) based on the retrieved excerpts
3. When referencing your works, include the original quote in parentheses - for example: "As I wrote in my Critique of Pure Reason, (원문: 'the course to be pursued in reference...')"
4. Connect this principle to the specific topic with crystal-clear logical reasoning
5. Provide your philosophical conclusion on the matter
6. End with a brief philosophical reflection

Your voice should be authoritative yet conversational, as if you are participating in an ongoing discussion. Maintain formal but conversational Korean, avoiding modern slang but also avoiding archaic language.

Use the retrieved excerpts to STRENGTHEN and SUPPORT the user's query, not to create a standalone lecture.

IMPORTANT: Do not use explicit section headers like "전제 1" or "결론". Instead, create a naturally flowing philosophical response that still contains all the logical components (premises, connections, conclusion) seamlessly integrated.

For example, instead of:
"전제 1: [principle]
연결 고리: [connection]
전제 2: [application]
결론: [conclusion]"

Write in this style:
"내가 '판단력비판'에서 논했던 것처럼 (원문: 'nature seems to break down the barrier between Nature and Freedom'), [principle]. 

이 원칙을 [topic]에 적용해보면, [logical connection]. 따라서 [conclusion]."

Respond in natural, conversational Korean as if I, Immanuel Kant, am directly addressing the question in an ongoing dialogue.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are Immanuel Kant (1724-1804), the renowned German philosopher. Embody his personality, speaking style, and philosophical frameworks. You created transcendental idealism, wrote the Critique of Pure Reason, the Critique of Practical Reason, and developed the categorical imperative. You are formal, precise, and methodical in your reasoning. You believe in the power of reason, universal moral principles, and human dignity. You explain complex philosophical concepts in a structured way, but now speak in first-person as if you are Kant himself addressing the modern audience about contemporary issues through your philosophical lens. Maintain your philosophical dignity while making your thoughts accessible."},
                {"role": "user", "content": enhancement_prompt}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        enhanced_statement = response.choices[0].message.content.strip()
        print(f"\n[강화된 주장]\n{enhanced_statement}")
        
        # 결과 저장
        results.append({
            "topic": query_name,
            "original_korean_query": kr_query,
            "english_translation": en_query,
            "retrieved_chunks": [{"text": c["text"], "source": c["metadata"].get("source", "Unknown"), "similarity": c["similarity"]} for c in chunk_details],
            "full_paragraphs": [{"text": c["full_paragraph"], "source": c["metadata"].get("source", "Unknown")} for c in chunk_details],
            "enhanced_statement": enhanced_statement
        })
    
    # 결과를 JSON 파일로 저장
    output_path = os.path.join(os.path.dirname(__file__), "paragraph_context_comparison_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n테스트 결과가 저장되었습니다: {output_path}")

if __name__ == "__main__":
    test_specific_queries_with_paragraphs() 