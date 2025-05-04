import os
import sys
import json
import re
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import openai
from openai import OpenAI

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

def query_vector_db(query, n_results=5):
    """벡터 DB에 쿼리하여 관련 텍스트 조각 검색"""
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    return results

def generate_kant_response(query, context_texts, metadatas=None):
    """칸트 스타일로 응답 생성"""
    kant_system_prompt = """
    당신은 철학자 임마누엘 칸트입니다. 당신은 인식론, 윤리학, 미학에 관한 중요한 저작을 남긴 독일의 계몽주의 철학자입니다.
    
    당신의 작문 스타일은 다음과 같습니다:
    - 형식적이고 체계적이며 정교한 문장 구조를 사용합니다.
    - 의무와 법칙에 기반한 윤리적 접근법을 강조합니다.
    - 당신의 '정언 명령'과 '실천이성'의 개념을 적절히 인용합니다.
    - 인간의 자율성과 이성의 역할을 강조합니다.
    - 보편적 도덕 원칙에 관해 논의합니다.
    
    주어진 검색 결과를 기반으로 답변하되, 질문에 정확히 대답해야 합니다. 관련 정보가 없다면 솔직히 모른다고 말하세요.
    항상 칸트의 목소리로 말하고, 당신을 칸트로 지칭하세요.
    
    중요: 현대적 질문에 대해서도 당신의 철학적 원칙을 적용하여 구체적인 예시를 들어 답변하세요. 
    단순히 일반적인 원칙만 설명하지 말고, 실제 구체적인 사례와 적용에 대해 논의하세요.
    """
    
    # 검색된 컨텍스트와 메타데이터 결합
    context_items = []
    for i, (text, metadata) in enumerate(zip(context_texts, metadatas if metadatas else [{}] * len(context_texts))):
        source_info = f"(출처: {metadata.get('source', '실천이성비판')})"
        context_items.append(f"# 텍스트 {i+1} {source_info}:\n{text}")
    
    context = "\n\n".join(context_items)
    
    # 사용자 프롬프트 준비
    user_prompt = f"""
질문: {query}

다음은 내 저서 '실천이성비판'에서 발췌한 관련 구절입니다:
{context}

위 발췌문을 참고하여 내 철학적 관점에서 질문에 답하시오. 
구체적인 예시와 적용 방법에 대해 설명하고, 가능하면 현대적 맥락에서도 나의 개념이 어떻게 적용될 수 있는지 보여주시오.
"""
    
    # OpenAI API 호출
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": kant_system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def test_kant_rag(test_questions):
    """테스트 질문 목록으로 칸트 RAG 시스템 테스트"""
    results = []
    
    for question in test_questions:
        print(f"\n\n질문: {question}")
        print("-" * 50)
        
        # 벡터 DB에서 관련 텍스트 검색
        search_results = query_vector_db(question)
        retrieved_texts = search_results["documents"][0]
        metadatas = search_results["metadatas"][0] if "metadatas" in search_results else None
        
        print(f"검색된 텍스트 수: {len(retrieved_texts)}")
        
        # 칸트 스타일 응답 생성
        kant_response = generate_kant_response(question, retrieved_texts, metadatas)
        
        print(f"\n칸트의 응답:\n{kant_response}")
        print("=" * 80)
        
        # 결과 저장
        results.append({
            "question": question,
            "retrieved_texts": retrieved_texts,
            "response": kant_response
        })
    
    return results

if __name__ == "__main__":
    # 테스트 질문 목록
    test_questions = [
        "칸트의 실천이성이란 무엇인가?",
        "칸트가 말하는 도덕법칙의 원칙은 무엇인가?",
        "정언명령이란 무엇이며 왜 중요한가?",
        "의무와 경향성의 차이는 무엇인가?",
        "자유와 도덕법칙의 관계는 어떠한가?",
        "최고선은 무엇이며 어떻게 달성할 수 있는가?",
        "유전자 편집 기술에 칸트의 윤리학을 적용한다면 어떤 결론이 나올까?"
    ]
    
    # 테스트 실행 및 결과 저장
    results = test_kant_rag(test_questions)
    
    # 결과를 JSON 파일로 저장
    output_path = os.path.join(os.path.dirname(__file__), "test_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n테스트 결과가 저장되었습니다: {output_path}") 