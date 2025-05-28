"""
토론 메시지 분석 및 RAG 쿼리 생성 테스트

이 모듈은 토론 참가자의 메시지를 분석하여 논리적으로 부족한 주장을 식별하고,
해당 주장을 강화하기 위한 RAG 쿼리를 생성하는 기능을 테스트합니다.
"""

import sys
import os
import json
from typing import Dict, List, Any, Tuple
import uuid
from datetime import datetime

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

# LLMManager 임포트
from src.models.llm.llm_manager import LLMManager
from src.rag.retrieval.web_retriever import WebSearchRetriever
from src.rag.retrieval.vector_store import VectorStore

class DebateRagQueryGenerator:
    """
    토론 메시지에서 논리적으로 부족한 주장을 식별하고 
    강화하기 위한 RAG 쿼리를 생성하는 클래스
    """
    
    def __init__(self):
        """초기화"""
        self.llm_manager = LLMManager()
        self.vector_store = None
        self.web_retriever = None
        self.dialogue_history = []
        
        # 철학자 작품 벡터 저장소 초기화
        self._init_vector_store()
        
        # 웹 검색 초기화
        self._init_web_retriever()
    
    def _init_vector_store(self):
        """벡터 저장소 초기화"""
        try:
            self.vector_store = VectorStore(
                model_name="all-MiniLM-L6-v2",
                store_path="./data/vector_store"
            )
            print("벡터 저장소 초기화 완료")
            
            # 테스트 데이터 추가
            if not self.vector_store.documents:
                self._add_sample_documents()
                
        except Exception as e:
            print(f"벡터 저장소 초기화 오류: {str(e)}")
            self.vector_store = None
    
    def _init_web_retriever(self):
        """웹 검색 초기화"""
        try:
            # SerpAPI 대신 Google API로 변경
            self.web_retriever = WebSearchRetriever(
                embedding_model="all-MiniLM-L6-v2",
                search_provider="google",  # 'serpapi' 대신 'google' 사용
                max_results=3
            )
            print("웹 검색 초기화 완료")
        except Exception as e:
            print(f"웹 검색 초기화 오류: {str(e)}")
            self.web_retriever = None
    
    def _add_sample_documents(self):
        """테스트용 샘플 문서 추가"""
        sample_texts = [
            "GDPR은 유럽연합의 데이터 보호 규정으로, 개인정보 보호와 데이터 활용 간의 균형을 맞추기 위한 제도적 장치입니다. 개인의 데이터 주권을 보장하면서도 혁신을 방해하지 않는 규제의 좋은 사례입니다.",
            "동형암호(Homomorphic Encryption)는 데이터를 암호화된 상태로 분석할 수 있게 해주는 기술로, 개인정보를 보호하면서도 데이터의 활용 가치를 유지할 수 있습니다.",
            "차등 프라이버시(Differential Privacy)는 개인 데이터에 통계적 노이즈를 추가하여 개인 식별 가능성을 낮추면서도 데이터 분석의 정확도를 유지하는 기술입니다.",
            "애플은 개인정보 보호를 중시하는 기업 철학을 바탕으로 '개인정보 보호 라벨'과 같은 혁신적인 기능을 도입하여 사용자의 신뢰를 얻고 경쟁력을 강화했습니다.",
            "에스토니아의 디지털 ID 시스템은 높은 수준의 데이터 보호와 투명성을 보장하면서도 효율적인 디지털 서비스를 제공하는 좋은 예입니다.",
            "프라이버시 중심 설계(Privacy by Design)는 제품이나 서비스 개발 초기 단계부터 개인정보 보호를 고려하는 접근 방식으로, 혁신과 개인정보 보호를 동시에 달성할 수 있게 합니다.",
            "GDPR 도입 이후 유럽에서는 프라이버시 중심 기술에 대한 투자와 혁신이 증가했으며, 이는 엄격한 규제가 오히려 혁신을 촉진할 수 있음을 보여줍니다.",
            "의사결정 시스템에서 설명 가능성과 투명성을 높이는 XAI(eXplainable AI) 기술은 개인정보 보호 규제를 준수하면서도 AI 기술 발전을 가능하게 합니다.",
            "개인정보 영향평가(PIA)와 같은 프로세스를 통해 기업들은 데이터 활용의 위험과 혜택을 사전에 평가하여 균형 잡힌 접근 방식을 취할 수 있습니다.",
            "영국의 Open Banking 이니셔티브는 사용자 동의 기반의 데이터 공유를 통해 금융 서비스 혁신을 촉진하면서도 개인정보 보호를 유지하는 좋은 사례입니다."
        ]
        
        # 메타데이터와 함께 문서 추가
        metadata_list = []
        for i, text in enumerate(sample_texts):
            metadata_list.append({
                "id": f"doc_{i}",
                "source": "sample",
                "topic": "privacy_and_innovation",
                "date": datetime.now().isoformat()
            })
        
        self.vector_store.add_documents(sample_texts, metadata_list)
        print(f"{len(sample_texts)}개의 샘플 문서가 벡터 저장소에 추가되었습니다.")
    
    def analyze_message(self, message: str, debate_topic: str = None) -> Dict[str, Any]:
        """
        토론 메시지를 분석하여 논리적으로 부족한 주장과 그에 대한 RAG 쿼리 생성
        
        Args:
            message: 분석할 토론 메시지
            debate_topic: 토론 주제 (선택 사항)
            
        Returns:
            분석 결과와 RAG 쿼리를 포함한 딕셔너리
        """
        # 시스템 프롬프트 구성
        system_prompt = """
You are an expert debate analysis AI that helps identify claims in debate arguments that need more evidence or logical support.
Your task is to identify claims that:
1. Lack specific examples or evidence
2. Use general statements without concrete facts
3. Make assertions without substantiation
4. Could be strengthened with data or case studies

For each identified weak claim, generate specific search queries IN ENGLISH ONLY that could help find supporting evidence.
"""

        # 유저 프롬프트 구성
        topic_context = f"The debate topic is: {debate_topic}\n\n" if debate_topic else ""
        user_prompt = f"""
{topic_context}Analyze the following debate message to identify claims that need more evidence or logical support:

MESSAGE:
{message}

For each identified claim that needs strengthening:
1. Quote the specific claim text
2. Explain why it needs more support (lacks specifics, needs examples, etc.)
3. Generate 2-3 specific search queries IN ENGLISH that would help find supporting evidence

Format your response as a JSON object with the following structure:
{{
  "identified_claims": [
    {{
      "claim_text": "quoted text of the claim",
      "issue": "brief explanation of what's missing",
      "search_queries": [
        "specific search query 1 in English",
        "specific search query 2 in English",
        "specific search query 3 in English"
      ]
    }},
    // more claims...
  ]
}}
"""

        # LLM 호출
        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=1500
        )
        
        # JSON 파싱
        try:
            import json
            import re
            
            # JSON 형식 찾기
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return result
            else:
                return {"error": "JSON 형식을 찾을 수 없습니다.", "raw_response": response}
            
        except Exception as e:
            return {"error": f"JSON 파싱 실패: {str(e)}", "raw_response": response}
    
    def generate_rag_queries(self, message: str, debate_topic: str = None) -> List[str]:
        """
        토론 메시지에서 RAG 쿼리 목록만 추출
        
        Args:
            message: 분석할 토론 메시지
            debate_topic: 토론 주제 (선택 사항)
            
        Returns:
            RAG 쿼리 목록
        """
        analysis = self.analyze_message(message, debate_topic)
        
        if "error" in analysis:
            return [f"Error generating queries: {analysis['error']}"]
        
        queries = []
        for claim in analysis.get("identified_claims", []):
            queries.extend(claim.get("search_queries", []))
        
        return queries
    
    def determine_source_for_query(self, query: str, debate_topic: str = None, philosopher_characters: List[str] = None) -> Dict[str, Any]:
        """
        LLM을 사용하여 쿼리 내용을 분석하고 적절한 소스를 결정
        
        Args:
            query: 검색 쿼리
            debate_topic: 토론 주제 (선택 사항)
            philosopher_characters: 토론에 등장하는 철학자 캐릭터 리스트 (선택 사항)
            
        Returns:
            소스 결정 결과를 포함한 딕셔너리
        """
        # 시스템 프롬프트 구성
        system_prompt = """
You are an expert research assistant tasked with determining the most appropriate sources for debate research queries.
Your goal is to analyze each query and determine which information sources would be most useful for answering it.

Available sources:
1. dialogue_history - Previous statements and arguments from the current debate
2. user_context - Documents, PDFs, articles, or other materials provided by the user
3. web - Real-time information from the internet
4. philosopher_works - Specific works and writings of philosophers (if query relates to philosophical concepts)

For each query, analyze its nature and content to determine the most appropriate source(s).
"""

        # 철학자 정보 구성
        philosopher_info = ""
        if philosopher_characters and len(philosopher_characters) > 0:
            philosopher_info = f"The debate involves the following philosophers: {', '.join(philosopher_characters)}.\n"
        
        # 유저 프롬프트 구성
        topic_context = f"The debate topic is: {debate_topic}\n" if debate_topic else ""
        user_prompt = f"""
{topic_context}{philosopher_info}
Please analyze the following search query and determine which source(s) would be most appropriate for finding relevant information:

QUERY: "{query}"

Consider:
- If the query relates to current/factual information, web search may be appropriate
- If the query relates to previous arguments or positions in the debate, dialogue history may be useful
- If the query relates to documents provided for the debate, user context would be best
- If the query relates to philosophical concepts and any of the philosophers involved, their works would be relevant

Return your response as a JSON object with the following structure:
{{
  "primary_source": "The single most appropriate source (dialogue_history/user_context/web/philosopher_works)",
  "additional_sources": ["Any other useful sources in priority order"],
  "reasoning": "Brief explanation of why these sources were selected"
}}
"""

        # LLM 호출
        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=500
        )
        
        # JSON 파싱
        try:
            import json
            import re
            
            # JSON 형식 찾기
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                # 소스 목록 구성
                sources = [result.get("primary_source")]
                if "additional_sources" in result:
                    sources.extend(result.get("additional_sources", []))
                
                # 중복 제거 및 None 값 제거
                sources = [s for s in sources if s]
                sources = list(dict.fromkeys(sources))  # 중복 제거
                
                return {
                    "sources": sources,
                    "reasoning": result.get("reasoning", "")
                }
            else:
                # 기본값 반환
                return {
                    "sources": ["web"],
                    "reasoning": "Failed to parse LLM response, defaulting to web search."
                }
            
        except Exception as e:
            # 오류 발생 시 기본값 반환
            return {
                "sources": ["web"],
                "reasoning": f"Error processing source determination: {str(e)}"
            }
    
    def search_information(self, query: str, sources: List[str]) -> List[Dict[str, Any]]:
        """
        쿼리와 소스에 따라 정보 검색 수행
        
        Args:
            query: 검색 쿼리
            sources: 검색 소스 목록
            
        Returns:
            검색 결과 목록
        """
        results = []
        
        for source in sources:
            if source == "web" and self.web_retriever is not None:
                try:
                    print(f"웹 검색 수행: '{query}'")
                    web_results = self.web_retriever.search(query, 3)
                    
                    if web_results:
                        # 웹 검색 결과 형식 통일
                        for item in web_results:
                            results.append({
                                "source": "web",
                                "title": item.get("title", ""),
                                "content": item.get("snippet", ""),
                                "url": item.get("url", ""),
                                "relevance": 0.8,  # 기본 관련성 점수
                            })
                except Exception as e:
                    print(f"웹 검색 오류: {str(e)}")
            
            elif source == "user_context" and self.vector_store is not None:
                try:
                    print(f"벡터 검색 수행: '{query}'")
                    vector_results = self.vector_store.search(query, 3)
                    
                    if vector_results:
                        # 벡터 검색 결과 형식 통일
                        for item in vector_results:
                            results.append({
                                "source": "user_context",
                                "title": f"Document {item.get('id', '')}",
                                "content": item.get("text", ""),
                                "metadata": item.get("metadata", {}),
                                "relevance": 1 - item.get("score", 0),  # 거리를 관련성으로 변환
                            })
                except Exception as e:
                    print(f"벡터 검색 오류: {str(e)}")
            
            elif source == "dialogue_history" and self.dialogue_history:
                try:
                    # 간단한 키워드 매칭을 통한 대화 기록 검색
                    print(f"대화 기록 검색 수행: '{query}'")
                    keywords = query.lower().split()
                    
                    for msg in self.dialogue_history:
                        text = msg.get("text", "").lower()
                        # 키워드 포함 여부 확인
                        if any(kw in text for kw in keywords):
                            results.append({
                                "source": "dialogue_history",
                                "speaker": msg.get("speaker", "Unknown"),
                                "content": msg.get("text", ""),
                                "timestamp": msg.get("timestamp", ""),
                                "relevance": 0.7,  # 기본 관련성 점수
                            })
                except Exception as e:
                    print(f"대화 기록 검색 오류: {str(e)}")
        
        # 관련성 순으로 정렬
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        return results[:5]  # 상위 5개 결과만 반환
    
    def strengthen_claim_with_evidence(self, claim: str, evidence: List[Dict[str, Any]]) -> str:
        """
        검색된 증거를 사용하여 주장 강화
        
        Args:
            claim: 강화할 주장
            evidence: 검색된 증거 목록
            
        Returns:
            강화된 주장
        """
        if not evidence:
            return f"{claim}\n[No supporting evidence found]"
        
        # 증거를 컨텍스트로 구성
        evidence_context = "\n\n".join([
            f"Source: {item.get('source')}\n"
            f"Title: {item.get('title', 'N/A')}\n"
            f"Content: {item.get('content')}"
            for item in evidence
        ])
        
        # 시스템 프롬프트 구성
        system_prompt = """
You are an expert debate assistant that helps strengthen arguments with supporting evidence.
Your task is to rewrite a debate claim by incorporating relevant evidence to make it more compelling and substantiated.
Keep the same position and perspective as the original claim, but add specific examples, data, or case studies from the provided evidence.
"""

        # 유저 프롬프트 구성
        user_prompt = f"""
Original Claim:
{claim}

Available Evidence:
{evidence_context}

Please rewrite the claim to make it stronger by incorporating the most relevant evidence. 
The strengthened claim should:
1. Maintain the same core argument and position as the original
2. Add specific examples, data points or case studies from the evidence
3. Be well-structured and persuasive
4. Be approximately 2-3 paragraphs in length

Only use information from the provided evidence. Do not make up facts or examples.
"""

        # LLM 호출
        strengthened_claim = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=1000
        )
        
        return strengthened_claim
    
    def analyze_message_with_sources(self, message: str, debate_topic: str = None, 
                                    philosopher_characters: List[str] = None) -> Dict[str, Any]:
        """
        토론 메시지를 분석하여 논리적으로 부족한 주장과 그에 대한 RAG 쿼리 및 소스 생성
        
        Args:
            message: 분석할 토론 메시지
            debate_topic: 토론 주제 (선택 사항)
            philosopher_characters: 토론에 등장하는 철학자 캐릭터 리스트 (선택 사항)
            
        Returns:
            분석 결과와 RAG 쿼리 및 소스를 포함한 딕셔너리
        """
        # 기본 분석 수행
        analysis = self.analyze_message(message, debate_topic)
        
        if "error" in analysis:
            return analysis
        
        # 각 쿼리에 대한 소스 결정 추가
        for claim in analysis.get("identified_claims", []):
            claim["query_sources"] = []
            for query in claim.get("search_queries", []):
                source_result = self.determine_source_for_query(
                    query, 
                    debate_topic, 
                    philosopher_characters
                )
                
                claim["query_sources"].append({
                    "query": query,
                    "sources": source_result.get("sources", ["web"]),
                    "reasoning": source_result.get("reasoning", "")
                })
        
        return analysis
    
    def analyze_and_strengthen_message(self, message: str, debate_topic: str = None, 
                                     philosopher_characters: List[str] = None) -> Dict[str, Any]:
        """
        토론 메시지 분석, 정보 검색, 주장 강화를 수행
        
        Args:
            message: 분석할 토론 메시지
            debate_topic: 토론 주제 (선택 사항)
            philosopher_characters: 토론에 등장하는 철학자 캐릭터 리스트 (선택 사항)
            
        Returns:
            분석 결과와 강화된 주장을 포함한 딕셔너리
        """
        # 분석 및 쿼리 소스 결정
        analysis = self.analyze_message_with_sources(message, debate_topic, philosopher_characters)
        
        if "error" in analysis:
            return analysis
        
        # 각 주장에 대해 정보 검색 및 강화
        for claim in analysis.get("identified_claims", []):
            claim["retrieved_evidence"] = []
            claim["strengthened_claim"] = ""
            
            # 각 쿼리에 대한 정보 검색
            all_evidence = []
            for query_source in claim.get("query_sources", []):
                query = query_source.get("query", "")
                sources = query_source.get("sources", ["web"])
                
                # 정보 검색 수행
                evidence = self.search_information(query, sources)
                query_source["evidence"] = evidence
                all_evidence.extend(evidence)
            
            # 검색된 모든 증거 저장
            claim["retrieved_evidence"] = all_evidence
            
            # 증거를 사용하여 주장 강화
            if all_evidence:
                claim["strengthened_claim"] = self.strengthen_claim_with_evidence(
                    claim.get("claim_text", ""), 
                    all_evidence
                )
        
        return analysis

    def generate_enhanced_message(self, original_message: str, analysis_result: Dict[str, Any]) -> str:
        """
        분석 결과와 강화된 주장을 사용하여 전체 메시지를 재생성
        
        Args:
            original_message: 원본 메시지
            analysis_result: 분석 및 주장 강화 결과
            
        Returns:
            강화된 전체 메시지
        """
        # 강화된 주장 수집
        strengthened_claims = []
        for claim in analysis_result.get("identified_claims", []):
            if claim.get("strengthened_claim"):
                strengthened_claims.append({
                    "original": claim.get("claim_text", ""),
                    "strengthened": claim.get("strengthened_claim", "")
                })
        
        # 강화된 주장이 없으면 원본 메시지 반환
        if not strengthened_claims:
            return original_message
        
        # 시스템 프롬프트 구성
        system_prompt = """
You are an expert debate assistant that helps rewrite entire debate arguments.
Your task is to rewrite a debate message by replacing weak claims with strengthened versions that include supporting evidence.
Maintain the overall structure, tone, and position of the original message, but incorporate the strengthened claims seamlessly.
"""

        # 유저 프롬프트 구성
        claims_context = "\n\n".join([
            f"Original Claim {i+1}:\n{claim['original']}\n\nStrengthened Claim {i+1}:\n{claim['strengthened']}"
            for i, claim in enumerate(strengthened_claims)
        ])
        
        user_prompt = f"""
Original Debate Message:
{original_message}

Claims to replace with strengthened versions:
{claims_context}

Please rewrite the entire debate message by:
1. Maintaining the overall structure, flow, and position of the original message
2. Replacing the original claims with their strengthened versions (incorporating the evidence)
3. Ensuring smooth transitions between sections
4. Keeping a consistent tone and style throughout the message
5. Preserving any introduction and conclusion from the original message

The final message should read as a cohesive, persuasive argument that naturally incorporates the strengthened claims.
"""

        # LLM 호출
        enhanced_message = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=2000
        )
        
        return enhanced_message


def test_rag_query_generation():
    """RAG 쿼리 생성 테스트 함수"""
    # 테스트 메시지 - 개인정보 보호론자의 반론
    test_message = """먼저, 찬성 측의 주장에 대한 제 반박을 시작하겠습니다. 기술 혁신과 개인 정보 보호의 균형이 필요하다는 주장에는, 제가 말하고자 하는 것이 보다 중요하다는 것을 깨닫지 못하고 있는 것 같습니다. 그것은 바로 우리의 디지털 프라이버시를 지키는 것입니다. 

물론, 기술 혁신이 가져오는 이점을 인정하지 않을 수 없습니다. 하지만 이런 이점이 프라이버시 침해의 위험성을 감당할 만큼 크다고 볼 수 있는가요? 블록체인 기술이나 익명화 기술 등이 개인 정보 보호와 데이터 활용 사이의 균형을 이룰 수 있다고 주장하였습니다. 그러나 이런 기술들이 정말로 완벽한 해결책이라고 할 수 있을까요? 

저는 반대합니다. 아무리 기술이 발전하더라도, 항상 새로운 취약점이 존재할 것입니다. 최근에도 다양한 기업들의 데이터 유출 사건이 발생하면서, 고객들의 신용 카드 정보, 개인 식별 정보 등이 유출되는 사태가 발생했습니다. 이런 사실이 우리에게 알려주는 것은, 기술 혁신 만으로는 개인정보 보호를 완벽하게 보장할 수 없다는 것입니다.

또한, 데이터의 사회적, 경제적 가치를 최대화한다는 목표는, 자칫하면 무분별한 정보 수집과 동의 없는 정보 공유로 이어질 수 있습니다. 여기서 중요한 것은, 우리가 정보를 공유하고자 하는지, 그리고 어떤 정보를 공유하고 싶어하는지에 대한 선택권이 보장되어야 한다는 점입니다. 우리의 디지털 프라이버시는 우리 개개인의 손에 달려 있어야 합니다.

마지막으로, 국가 안보나 범죄 예방 등을 위해 데이터를 활용하는 것에 대해 언급하셨습니다. 이는 분명히 중요한 이슈입니다. 그러나, 이러한 이유로 개인의 프라이버시를 침해하는 것은 절대로 허용될 수 없습니다. 우리는 개인의 프라이버시를 지키면서도 범죄를 예방하고 국가를 보호하는 방법을 찾아야 합니다.

결론적으로, 디지털 프라이버시의 미래는 개인 정보 보호를 최우선으로 두어야 합니다. 기술 혁신은 중요하지만, 그것이 우리의 프라이버시를 침해하는 우려가 있는 한, 그것을 무조건적으로 받아들이는 것은 위험하다고 강조하고 싶습니다. 따라서, 우리의 디지털 프라이버시를 보호하는 것이 가장 중요하며, 이를 위해 필요한 법률, 정책, 기술 등을 개발하는 것이 우선되어야 합니다."""
    
    # 토론 주제 설정
    debate_topic = "디지털 프라이버시의 미래: 개인 정보 보호와 혁신 사이의 균형"
    
    # DebateRagQueryGenerator 인스턴스 생성
    rag_generator = DebateRagQueryGenerator()
    
    # 메시지 분석 및 RAG 쿼리 생성
    print("\n=== 토론 메시지 분석 시작 ===")
    analysis_result = rag_generator.analyze_message(test_message, debate_topic)
    
    # 결과 출력
    if "identified_claims" in analysis_result:
        print(f"\n총 {len(analysis_result['identified_claims'])}개의 주장이 식별되었습니다:")
        
        for i, claim in enumerate(analysis_result["identified_claims"]):
            print(f"\n{i+1}. 주장: {claim.get('claim_text')}")
            print(f"   부족한 점: {claim.get('issue')}")
            print(f"   검색 쿼리: {', '.join(claim.get('search_queries', []))}")
    else:
        print("\n주장 식별에 실패했습니다.")
        if "error" in analysis_result:
            print(f"오류: {analysis_result['error']}")
    
    # 소스 결정 및 정보 검색, 주장 강화 수행
    print("\n=== 주장 강화 시작 ===")
    enhanced_result = rag_generator.analyze_and_strengthen_message(test_message, debate_topic)
    
    # 결과 저장
    output_file = "debate_rag_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced_result, f, ensure_ascii=False, indent=2)
    print(f"\n결과가 {output_file}에 저장되었습니다.")
    
    # 강화된 전체 메시지 생성
    enhanced_message = rag_generator.generate_enhanced_message(test_message, enhanced_result)
    print("\n=== 강화된 메시지 ===")
    print(enhanced_message)
    
    return enhanced_result


if __name__ == "__main__":
    test_rag_query_generation() 