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

def test_specific_queries():
    """특정 쿼리로 RAG 성능 테스트"""
    
    # 철학적 주장이 담긴 한국어 문장들
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
        # 쿼리 이름 설정
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
        
        # 검색된 텍스트와 유사도 점수 출력
        chunk_details = []
        for j, (text, distance) in enumerate(zip(retrieved_texts, distances if distances else [None] * len(retrieved_texts))):
            similarity = distance_to_similarity(distance)
            similarity_text = f"유사도: {similarity:.4f}" if similarity is not None else "유사도: N/A"
            metadata = metadatas[j] if metadatas and j < len(metadatas) else {}
            source = metadata.get("source", "Unknown")
            
            print(f"\n--- 청크 {j+1} ({similarity_text}, 출처: {source}) ---")
            print(f"{text[:150]}..." if len(text) > 150 else text)
            
            chunk_details.append({
                "text": text,
                "raw_distance": float(distance) if distance is not None else None,
                "similarity": float(similarity) if similarity is not None else None,
                "metadata": metadata
            })
        
        # 주장 강화를 위한 추가 컨텍스트 생성
        print("\n\n[원본 주장 강화를 위한 컨텍스트 생성]")
        
        retrieved_contexts = "\n\n".join([f"Source {j+1} ({chunk['metadata'].get('source', 'Unknown')}): {chunk['text']}" 
                                         for j, chunk in enumerate(chunk_details)])
        
        enhancement_prompt = f"""
Based on the following philosophical statement:

"{en_query}"

And these relevant excerpts from my works:

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
            "retrieved_chunks": chunk_details,
            "enhanced_statement": enhanced_statement
        })
    
    # 결과를 JSON 파일로 저장
    output_path = os.path.join(os.path.dirname(__file__), "philosophy_arguments_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n테스트 결과가 저장되었습니다: {output_path}")

if __name__ == "__main__":
    test_specific_queries() 