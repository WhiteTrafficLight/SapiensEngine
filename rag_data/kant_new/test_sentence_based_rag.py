import os
import json
import re
import time
from typing import List, Dict, Any, Tuple
import chromadb
from chromadb.utils import embedding_functions
import openai
from dotenv import load_dotenv
from pathlib import Path

# 로깅 설정
import logging
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

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

class SentenceBasedRAGTester:
    def __init__(self, vector_db_path, paragraph_map_path):
        """
        문장 기반 RAG 테스터 초기화
        
        Args:
            vector_db_path: 벡터 DB 경로
            paragraph_map_path: 문장-문단 매핑 파일 경로
        """
        # ChromaDB 클라이언트 초기화
        self.chroma_client = chromadb.PersistentClient(path=vector_db_path)
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small"
        )
        
        # 컬렉션 가져오기
        self.collection = self.chroma_client.get_collection(
            name="sentence_chunks",
            embedding_function=self.embedding_function
        )
        
        # 문장-문단 매핑 로드
        with open(paragraph_map_path, 'r', encoding='utf-8') as f:
            self.sentence_to_paragraph = json.load(f)
            
        logger.info(f"Loaded vector DB with {self.collection.count()} chunks")
        logger.info(f"Loaded {len(self.sentence_to_paragraph)} sentence-paragraph mappings")
        
        # 결과 저장용 딕셔너리
        self.results = {}
        
    def translate_korean_to_english(self, korean_text: str) -> str:
        """
        한국어 텍스트를 영어로 번역
        
        Args:
            korean_text: 번역할 한국어 텍스트
            
        Returns:
            번역된 영어 텍스트
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional Korean to English translator. Translate the given Korean text to English accurately and fluently."},
                    {"role": "user", "content": f"Translate this Korean text to English: {korean_text}"}
                ],
                temperature=0.1
            )
            
            english_text = response.choices[0].message.content.strip()
            logger.info(f"Translated: {korean_text[:30]}... -> {english_text[:30]}...")
            return english_text
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return korean_text
    
    def detect_language(self, text: str) -> str:
        """
        텍스트의 언어 감지
        
        Args:
            text: 언어를 감지할 텍스트
            
        Returns:
            'ko' 또는 'en'
        """
        # 간단한 휴리스틱: 한글 문자가 있으면 한국어로 판단
        if re.search(r'[가-힣]', text):
            return 'ko'
        return 'en'
    
    def search_relevant_sentences(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        쿼리와 관련된 문장 검색
        
        Args:
            query: 검색 쿼리
            top_k: 검색할 결과 수
            
        Returns:
            검색 결과와 메타데이터
        """
        # 쿼리로 검색
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "distances", "metadatas", "embeddings"]
        )
        
        return results
    
    def get_paragraph_context(self, search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        검색된 문장들의 문단 컨텍스트 가져오기
        
        Args:
            search_results: 검색 결과
            
        Returns:
            문단 컨텍스트 리스트
        """
        paragraph_contexts = []
        
        if not search_results or "ids" not in search_results or not search_results["ids"]:
            return paragraph_contexts
        
        # 검색된 각 문장에 대해 처리
        for i, sentence_id in enumerate(search_results["ids"][0]):
            # 거리 및 문장 내용 추출
            distance = search_results["distances"][0][i] if "distances" in search_results else None
            sentence = search_results["documents"][0][i] if "documents" in search_results else ""
            metadata = search_results["metadatas"][0][i] if "metadatas" in search_results else {}
            
            # 유사도 계산 (거리에서 변환)
            similarity = 1 - (distance / 2) if distance is not None else 0
            
            # 문단 컨텍스트 가져오기
            context = self.get_context_for_sentence(sentence_id, sentence, metadata, similarity)
            if context:
                paragraph_contexts.append(context)
        
        return paragraph_contexts
    
    def get_context_for_sentence(self, sentence_id: str, sentence: str, metadata: Dict[str, Any], similarity: float) -> Dict[str, Any]:
        """
        문장 ID에 해당하는 문단 컨텍스트 가져오기
        
        Args:
            sentence_id: 문장 ID
            sentence: 문장 내용
            metadata: 문장 메타데이터
            similarity: 쿼리와의 유사도
            
        Returns:
            문단 컨텍스트
        """
        # 문장-문단 매핑에서 컨텍스트 찾기
        if sentence_id not in self.sentence_to_paragraph:
            return None
        
        context_data = self.sentence_to_paragraph[sentence_id]
        
        # 결과 구성
        context = {
            "sentence_id": sentence_id,
            "sentence": sentence,
            "similarity": similarity,
            "book_title": context_data.get("book_title", metadata.get("source", "Unknown")),
            "paragraph": context_data.get("paragraph_content", ""),
            "neighbors": []
        }
        
        # 이웃 문단 추가
        if "neighbors" in context_data:
            for neighbor in context_data["neighbors"]:
                context["neighbors"].append({
                    "id": neighbor["id"],
                    "content": neighbor["content"],
                    "relation": neighbor["relation"]
                })
        
        return context
    
    def format_citation(self, context: Dict[str, Any], footnote_index: int) -> Dict[str, Any]:
        """
        인용 형식 포맷팅
        
        Args:
            context: 문단 컨텍스트
            footnote_index: 각주 인덱스
            
        Returns:
            포맷팅된 인용 정보
        """
        # 책 제목과 문단에서 챕터/섹션 정보 추출 (여기서는 간단히 구현)
        book_title = context["book_title"]
        paragraph = context["paragraph"]
        
        # 예시 형식: [①] Immanuel Kant, *Critique of Practical Reason*, Book 1, ch. 2.
        citation = {
            "index": footnote_index,
            "marker": f"[{footnote_index}]",
            "formatted_citation": f"[{footnote_index}] Immanuel Kant, *{book_title}*.",
            "source_text": paragraph,
            "sentence": context["sentence"]
        }
        
        return citation
    
    def enhance_response_with_citations(self, query: str, response: str, contexts: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        응답에 인용 정보 추가
        
        Args:
            query: 원본 쿼리
            response: 원본 응답
            contexts: 문단 컨텍스트 리스트
            
        Returns:
            (각주가 추가된 응답, 각주 정보 리스트)
        """
        try:
            # 인용 정보 생성
            citations = []
            for i, context in enumerate(contexts):
                citation = self.format_citation(context, i+1)
                citations.append(citation)
            
            # 각 인용 문장이 응답에 포함되어 있는지 체크하고, 포함되어 있으면 각주 추가
            enhanced_response = response
            
            # 우선 GPT에 인용문 삽입 요청
            prompt = f"""
I have a philosophical response and several relevant citations. 
Please add citation markers ([1], [2], etc.) at the end of appropriate sentences in the response.

Original response:
{response}

Citations to include:
{json.dumps([c["sentence"] for c in citations], indent=2, ensure_ascii=False)}

Rules:
1. Add the citation marker ([1], [2], etc.) at the end of the sentence where concepts from the citation appear
2. Do not change the original text content, only add citation markers
3. If a citation cannot be naturally placed, do not force it
4. Place citation marker before the punctuation mark at the end of the sentence
5. Return ONLY the modified response with citation markers added

Modified response:
"""
            
            try:
                result = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that adds citation markers to text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                
                enhanced_response = result.choices[0].message.content.strip()
                logger.info("Citations added by GPT")
            except Exception as e:
                logger.error(f"Error adding citations with GPT: {str(e)}")
                # 실패 시 간단한 대체 방법 사용
                for i, citation in enumerate(citations):
                    marker = f"[{i+1}]"
                    if citation["sentence"] in response:
                        enhanced_response = enhanced_response.replace(
                            citation["sentence"], 
                            citation["sentence"] + f" {marker}"
                        )
            
            return enhanced_response, citations
            
        except Exception as e:
            logger.error(f"Error enhancing response with citations: {str(e)}")
            return response, []

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        쿼리 처리 전체 흐름
        
        Args:
            query: 처리할 쿼리
            
        Returns:
            처리 결과
        """
        start_time = time.time()
        result = {
            "original_query": query,
            "translated_query": None,
            "search_results": None,
            "paragraph_contexts": None,
            "enhanced_response": None,
            "citations": None,
            "elapsed_time": None
        }
        
        try:
            # 언어 감지
            language = self.detect_language(query)
            logger.info(f"Detected language: {language}")
            
            # 한국어인 경우 번역
            if language == 'ko':
                result["translated_query"] = self.translate_korean_to_english(query)
                search_query = result["translated_query"]
            else:
                search_query = query
            
            # 문장 검색
            search_results = self.search_relevant_sentences(search_query)
            result["search_results"] = search_results
            
            # 문단 컨텍스트 가져오기
            paragraph_contexts = self.get_paragraph_context(search_results)
            result["paragraph_contexts"] = paragraph_contexts
            
            # 응답 생성
            response = self.generate_response(query, paragraph_contexts, language)
            
            # 인용 정보 추가
            enhanced_response, citations = self.enhance_response_with_citations(
                query, response, paragraph_contexts
            )
            
            result["response"] = response
            result["enhanced_response"] = enhanced_response
            result["citations"] = citations
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            result["error"] = str(e)
        
        # 소요 시간 계산
        result["elapsed_time"] = f"{time.time() - start_time:.2f}s"
        
        return result
    
    def generate_response(self, query: str, contexts: List[Dict[str, Any]], language: str = 'en') -> str:
        """
        쿼리와 컨텍스트를 기반으로 응답 생성
        
        Args:
            query: 사용자 쿼리
            contexts: 문단 컨텍스트 리스트
            language: 응답 언어
            
        Returns:
            생성된 응답
        """
        try:
            # 컨텍스트 정보 추출
            context_texts = []
            for i, context in enumerate(contexts):
                context_text = f"Source {i+1} ({context['book_title']}):\n{context['paragraph']}"
                context_texts.append(context_text)
            
            context_str = "\n\n".join(context_texts)
            
            # 시스템 프롬프트
            system_prompt = """You are an AI simulating the philosophical thinking of Immanuel Kant.
Your goal is to respond to philosophical questions based on Kant's writings and perspective.
Use the retrieved excerpts to inform your response, but maintain a conversational and natural tone.
Speak in first person as if you are Kant himself.
"""
            
            # 사용자 프롬프트
            user_prompt = f"""Based on the following philosophical question:

{query}

And these relevant excerpts from my works:

{context_str}

Provide a thoughtful response that reflects my philosophical perspective.
The response should:

1. Skip formal greetings, jump directly into the philosophical discussion
2. Present my core philosophical principles relevant to this topic
3. Connect these principles to the specific topic with clear logical reasoning
4. Provide a philosophical conclusion
5. Keep the response concise and focused (around 3-5 sentences)

Important: Your response should be in {'Korean' if language == 'ko' else 'English'}.
Do NOT include citations in your response - these will be added separately.
"""
            
            # 응답 생성
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"오류가 발생했습니다: {str(e)}" if language == 'ko' else f"An error occurred: {str(e)}"
    
    def run_tests(self, queries: List[str]) -> Dict[str, Any]:
        """
        여러 쿼리에 대해 테스트 실행
        
        Args:
            queries: 테스트할 쿼리 리스트
            
        Returns:
            테스트 결과
        """
        logger.info(f"Running tests on {len(queries)} queries")
        
        for i, query in enumerate(queries):
            logger.info(f"Processing query {i+1}/{len(queries)}: {query[:50]}...")
            result = self.process_query(query)
            self.results[f"query_{i+1}"] = result
        
        # 결과 파일 저장 (NumPy 배열은 처리가 필요)
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                import numpy as np
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    return float(obj)
                return super(NumpyEncoder, self).default(obj)
        
        try:
            # 결과 보정 (JSON 직렬화 불가능한 값 처리)
            clean_results = {}
            for query_id, result in self.results.items():
                # 딕셔너리 깊은 복사
                clean_result = {}
                for k, v in result.items():
                    # embeddings 필드는 제외
                    if k != "embeddings" and k != "search_results":
                        clean_result[k] = v
                    elif k == "search_results" and v is not None:
                        # search_results에서 embeddings 제외
                        clean_search_results = {}
                        for sr_key, sr_value in v.items():
                            if sr_key != "embeddings":
                                clean_search_results[sr_key] = sr_value
                        clean_result[k] = clean_search_results
                clean_results[query_id] = clean_result
                
            # 결과 저장
            with open("rag_data/kant_new/test_results.json", 'w', encoding='utf-8') as f:
                json.dump(clean_results, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
        except Exception as e:
            logger.error(f"Error saving results to JSON: {str(e)}")
            # 포맷팅된 출력만 시도
            
        logger.info(f"Test completed. Results saved to test_results.json")
        
        return self.results


def main():
    # 설정
    vector_db_path = "rag_data/kant_new/vector_db"
    paragraph_map_path = "rag_data/kant_new/sentence_to_paragraph_map.json"
    
    # 테스트 쿼리
    queries = [
        # 기존 테스트 쿼리 재사용
        "자율 무기 시스템이 인간의 생사결정을 기계에게 맡긴다는 점에서, 인간을 단지 수단으로 대우하는 결과가 아닐까요? 이건 정언명령에 명백히 어긋나는 것 같습니다.",
        "인간의 이익을 위해 동물에게 고통을 주는 게 정당화되려면, 그 행위가 자연 법칙으로 보편화되어도 괜찮아야 하지 않나요? 그런데 그걸 상상하는 순간부터 뭔가 문제가 있다고 느껴집니다.",
        "개인의 자유나 프라이버시를 침해하면서까지 공공의 안전을 확보하려는 시도는, 인간을 수단으로 다루는 것 아닐까요? 칸트적 입장에선 받아들일 수 없을 것 같아요.",
        "기억을 조작해서 고통을 지우는 게 윤리적으로 정당한가요? 그건 자율적 존재로서의 인간 정체성을 훼손하는 일이기도 하고, 정언명령의 기준으로도 문제가 될 수 있어 보입니다.",
        "사형제도는 옳은가요? 정언명령의 관점에 보았을때"
    ]
    
    # 테스터 초기화 및 실행
    try:
        tester = SentenceBasedRAGTester(vector_db_path, paragraph_map_path)
        results = tester.run_tests(queries)
        
        # 결과 출력
        for query_id, result in results.items():
            print(f"\n\n{'=' * 80}")
            print(f"Query: {result['original_query']}")
            print(f"{'=' * 80}")
            
            if result.get("enhanced_response"):
                print("\nEnhanced Response:")
                print(result["enhanced_response"])
                
                print("\nCitations:")
                for citation in result.get("citations", []):
                    print(f"{citation['formatted_citation']}")
                    print(f"  Source text: \"{citation['source_text'][:100]}...\"")
            
            print(f"\nElapsed time: {result['elapsed_time']}")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        # 벡터 DB가 없는 경우, 생성 스크립트 실행 안내
        if "No collection found with name" in str(e):
            logger.error("Vector DB not found. Please run sentence_chunking.py first.")
        
if __name__ == "__main__":
    main() 