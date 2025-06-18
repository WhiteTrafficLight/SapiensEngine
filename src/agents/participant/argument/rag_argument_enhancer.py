"""
RAG-based argument enhancement module for debate participants.

Handles RAG query generation, evidence search, and argument strengthening.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class RAGArgumentEnhancer:
    """RAG 기반 논증 강화를 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], 
                 rag_search_manager, llm_manager):
        """
        RAGArgumentEnhancer 초기화
        
        Args:
            agent_id: 에이전트 ID
            philosopher_data: 철학자 데이터
            rag_search_manager: RAG 검색 매니저
            llm_manager: LLM 매니저 인스턴스
        """
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.rag_search_manager = rag_search_manager
        self.llm_manager = llm_manager
        
        # 철학자 정보 추출
        self.philosopher_name = philosopher_data.get("name", "Unknown Philosopher")
        self.philosopher_essence = philosopher_data.get("essence", "")
        
        # ✅ RAG 정보 추적용 속성 추가
        self.rag_info = {
            "rag_used": False,
            "rag_source_count": 0,
            "rag_sources": []
        }
        self.search_results = []  # 검색 결과 저장용
    
    # =================================================================
    # ORIGINAL METHOD (주석 처리) - 논증에 RAG 쿼리를 별도로 추가
    # =================================================================
    
    # def generate_rag_queries_for_arguments(self, topic: str, core_arguments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     """
    #     핵심 주장들에 대한 RAG 검색 쿼리 생성
    #     
    #     Args:
    #         topic: 토론 주제
    #         core_arguments: 핵심 주장 리스트
    #         
    #     Returns:
    #         RAG 쿼리가 추가된 주장 리스트
    #     """
    #     logger.info(f"[{self.agent_id}] Generating RAG queries for {len(core_arguments)} arguments")
    #     
    #     enhanced_arguments = []
    #     
    #     for i, argument in enumerate(core_arguments):
    #         try:
    #             argument_text = argument.get("argument", "")
    #             reasoning = argument.get("reasoning", "")
    #             
    #             # 개별 주장에 대한 RAG 쿼리 생성
    #             rag_queries = self._generate_queries_for_single_argument(topic, argument_text, reasoning)
    #             
    #             # 원본 주장에 RAG 쿼리 추가
    #             enhanced_argument = argument.copy()
    #             enhanced_argument["rag_queries"] = rag_queries
    #             
    #             enhanced_arguments.append(enhanced_argument)
    #             logger.info(f"[{self.agent_id}] Generated {len(rag_queries)} RAG queries for argument {i+1}")
    #             
    #         except Exception as e:
    #             logger.error(f"[{self.agent_id}] Error generating RAG queries for argument {i+1}: {str(e)}")
    #             enhanced_arguments.append(argument)  # 실패 시 원본 유지
    #     
    #     return enhanced_arguments
    
    # =================================================================
    # NEW OPTIMIZED METHOD - 이미 쿼리가 포함된 논증 처리
    # =================================================================
    
    def generate_rag_queries_for_arguments(self, topic: str, core_arguments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        RAG 쿼리 생성 (최적화된 버전 - 이미 쿼리가 있으면 그대로 반환)
        
        Args:
            topic: 토론 주제  
            core_arguments: 핵심 주장 리스트 (이미 RAG 쿼리 포함될 수 있음)
            
        Returns:
            RAG 쿼리가 포함된 주장 리스트
        """
        logger.info(f"[{self.agent_id}] Processing arguments for RAG queries")
        
        # 이미 쿼리가 있는지 확인
        has_queries = all(arg.get("rag_queries") for arg in core_arguments)
        
        if has_queries:
            # 이미 쿼리가 있으면 바로 반환 (최적화된 경우)
            total_queries = sum(len(arg.get("rag_queries", [])) for arg in core_arguments)
            logger.info(f"[{self.agent_id}] ✅ Arguments already have {total_queries} RAG queries - skipping generation")
            return core_arguments
        else:
            # 쿼리가 없으면 기존 방식으로 생성 (fallback)
            logger.info(f"[{self.agent_id}] ⚠️ Arguments missing RAG queries - generating them separately")
            return self._generate_queries_fallback(topic, core_arguments)
    
    def _generate_queries_fallback(self, topic: str, core_arguments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        RAG 쿼리가 없는 경우 별도로 생성 (fallback 방식)
        
        Args:
            topic: 토론 주제
            core_arguments: 핵심 주장 리스트
            
        Returns:
            RAG 쿼리가 추가된 주장 리스트
        """
        enhanced_arguments = []
        
        for i, argument in enumerate(core_arguments):
            try:
                argument_text = argument.get("argument", "")
                reasoning = argument.get("reasoning", "")
                
                # 개별 주장에 대한 RAG 쿼리 생성
                rag_queries = self._generate_queries_for_single_argument(topic, argument_text, reasoning)
                
                # 원본 주장에 RAG 쿼리 추가
                enhanced_argument = argument.copy()
                enhanced_argument["rag_queries"] = rag_queries
                
                enhanced_arguments.append(enhanced_argument)
                logger.info(f"[{self.agent_id}] Generated {len(rag_queries)} RAG queries for argument {i+1}")
                
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error generating RAG queries for argument {i+1}: {str(e)}")
                enhanced_arguments.append(argument)  # 실패 시 원본 유지
        
        return enhanced_arguments
    
    def _generate_queries_for_single_argument(self, topic: str, argument: str, reasoning: str) -> List[Dict[str, Any]]:
        """
        단일 주장에 대한 RAG 쿼리 생성
        
        Args:
            topic: 토론 주제
            argument: 주장 내용
            reasoning: 주장 근거
            
        Returns:
            RAG 쿼리 리스트
        """
        system_prompt = f"""
You are {self.philosopher_name}, preparing to strengthen your philosophical argument with evidence.

Your essence: {self.philosopher_essence}

Generate 3-4 specific search queries to find evidence that supports your philosophical argument.
Each query should target different types of evidence:
1. Empirical data/statistics
2. Research studies/academic findings  
3. Historical examples/case studies
4. Expert opinions/philosophical works

Make queries specific and focused. Avoid overly broad terms.

Format as JSON array:
[
  {{
    "query": "specific search query",
    "source_type": "web|vector|philosopher",
    "evidence_type": "empirical|research|historical|expert",
    "purpose": "brief description of what this evidence would prove"
  }},
  ...
]
"""

        user_prompt = f"""
TOPIC: "{topic}"
ARGUMENT: "{argument}"
REASONING: "{reasoning}"

Generate 3-4 targeted search queries to find evidence that would strengthen this philosophical argument.
Think about what specific data, studies, examples, or expert opinions would validate your reasoning.

Respond with a JSON array of search queries.
"""

        try:
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=800
            )
            
            # JSON 파싱
            import json
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                queries = json.loads(json_str)
                return queries
            else:
                logger.warning(f"[{self.agent_id}] Could not parse RAG queries JSON")
                return []
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error generating RAG queries: {str(e)}")
            return []
    
    def strengthen_arguments_with_rag(self, core_arguments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        RAG 검색을 통해 주장들을 강화
        
        Args:
            core_arguments: RAG 쿼리가 포함된 핵심 주장 리스트
            
        Returns:
            강화된 주장 리스트
        """
        logger.info(f"[{self.agent_id}] Strengthening {len(core_arguments)} arguments with RAG...")
        
        # ✅ RAG 정보 초기화
        self.rag_info = {
            "rag_used": False,
            "rag_source_count": 0,
            "rag_sources": []
        }
        self.search_results = []
        
        strengthened_arguments = []
        total_evidence_count = 0
        all_sources = []
        
        for i, argument in enumerate(core_arguments):
            try:
                logger.info(f"[{self.agent_id}] Processing argument {i+1}: {argument['argument'][:50]}...")
                
                # RAG 검색 수행
                evidence_list = self._perform_rag_search_for_argument(argument)
                
                if evidence_list:
                    # ✅ 검색 결과 누적
                    self.search_results.extend(evidence_list)
                    total_evidence_count += len(evidence_list)
                    
                    # 소스 정보 수집
                    for ev in evidence_list:
                        content = ev.get("snippet", ev.get("content", ""))
                        if not content:  # content가 비어있으면 기본값 제공
                            content = ev.get("title", "No content available")
                        
                        source_info = {
                            "type": ev.get("source_type", "web"),  # ✅ type 필드 사용
                            "content": content,  # ✅ content 필드 사용 (기본값 보장)
                            "title": ev.get("title", "Unknown Title"),
                            "url": ev.get("url", ev.get("link", "")),
                            "relevance_score": ev.get("relevance", ev.get("relevance_score", 0.0))
                        }
                        all_sources.append(source_info)
                    
                    # 증거를 바탕으로 주장 강화
                    strengthened_arg = self._strengthen_single_argument_with_evidence(
                        argument["argument"], 
                        argument["reasoning"], 
                        evidence_list
                    )
                    
                    # 원본 정보 유지하면서 강화된 내용 업데이트
                    enhanced_argument = argument.copy()
                    enhanced_argument.update(strengthened_arg)
                    enhanced_argument["evidence_used"] = len(evidence_list)
                    enhanced_argument["evidence_sources"] = [
                        self._format_evidence_source(ev) for ev in evidence_list[:3]
                    ]
                    enhanced_argument["strengthened"] = True
                    
                    strengthened_arguments.append(enhanced_argument)
                    logger.info(f"[{self.agent_id}] ✅ Argument {i+1} strengthened with {len(evidence_list)} evidence pieces")
                else:
                    # 증거를 찾지 못한 경우 원본 유지
                    argument["strengthened"] = False
                    strengthened_arguments.append(argument)
                    logger.info(f"[{self.agent_id}] ⚠️ No evidence found for argument {i+1}, keeping original")
                    
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error strengthening argument {i+1}: {str(e)}")
                argument["strengthened"] = False
                strengthened_arguments.append(argument)
        
        # ✅ 최종 RAG 정보 업데이트
        self.rag_info = {
            "rag_used": total_evidence_count > 0,
            "rag_source_count": total_evidence_count,
            "rag_sources": all_sources[:10]  # 상위 10개 소스만 저장
        }
        
        logger.info(f"[{self.agent_id}] RAG strengthening completed: {total_evidence_count} evidence pieces from {len(all_sources)} sources")
        
        return strengthened_arguments
    
    def _perform_rag_search_for_argument(self, argument: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        단일 주장에 대한 RAG 검색 수행
        
        Args:
            argument: RAG 쿼리가 포함된 주장
            
        Returns:
            검색된 증거 리스트
        """
        evidence_list = []
        rag_queries = argument.get("rag_queries", [])
        
        for query_info in rag_queries[:3]:  # 최대 3개 쿼리만 처리
            try:
                query = query_info.get("query", "")
                source_type = query_info.get("source_type", "web")
                
                if not query:
                    continue
                
                # 소스 타입에 따른 검색
                if source_type == "web":
                    results = self._web_search(query)
                elif source_type == "vector":
                    results = self._vector_search(query)
                elif source_type == "philosopher":
                    results = self._philosopher_search(query)
                else:
                    results = self._web_search(query)  # 기본값
                
                # 결과를 증거 리스트에 추가
                for result in results[:2]:  # 각 쿼리당 최대 2개 결과
                    # 더 나은 소스 정보 추출
                    source_info = self._extract_source_info(result, source_type)
                    
                    evidence = {
                        "content": result.get("content", result.get("snippet", "")),
                        "source": source_info,  # 개선된 소스 정보
                        "title": result.get("title", ""),
                        "url": result.get("url", result.get("link", "")),
                        "relevance": result.get("relevance", 0.5),
                        "query": query,
                        "evidence_type": query_info.get("evidence_type", "general"),
                        "source_type": source_type
                    }
                    evidence_list.append(evidence)
                    
            except Exception as e:
                logger.warning(f"[{self.agent_id}] RAG search failed for query '{query}': {str(e)}")
                continue
        
        return evidence_list
    
    def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 수행"""
        if self.rag_search_manager:
            return self.rag_search_manager.search_web_only(query)
        return []
    
    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """벡터 검색 수행"""
        if self.rag_search_manager:
            return self.rag_search_manager.search_vector_only(query)
        return []
    
    def _philosopher_search(self, query: str) -> List[Dict[str, Any]]:
        """철학자 검색 수행"""
        if self.rag_search_manager:
            return self.rag_search_manager.search_philosopher_only(query)
        return []
    
    def _extract_source_info(self, result: Dict[str, Any], source_type: str) -> str:
        """
        검색 결과에서 소스 정보를 추출
        
        Args:
            result: 검색 결과
            source_type: 검색 소스 타입
            
        Returns:
            추출된 소스 정보
        """
        # 1. 명시적 source 필드가 있으면 사용
        if result.get("source") and result.get("source") != "unknown":
            extracted_source = result.get("source")
            logger.debug(f"[{self.agent_id}] 소스 추출: 명시적 source 필드 사용 -> {extracted_source}")
            return extracted_source
        
        # 2. URL에서 도메인 추출
        url = result.get("url", result.get("link", ""))
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain:
                    # www. 제거
                    if domain.startswith("www."):
                        domain = domain[4:]
                    logger.debug(f"[{self.agent_id}] 소스 추출: URL에서 도메인 추출 -> {domain}")
                    return domain
            except:
                pass
        
        # 3. 제목에서 소스 정보 추출 (출처가 포함된 경우)
        title = result.get("title", "")
        if title:
            # "- Wikipedia", "| CNN", "by The Guardian" 등의 패턴 찾기
            import re
            source_patterns = [
                r'\|\s*([A-Za-z\s]+)$',  # | CNN
                r'-\s*([A-Za-z\s]+)$',   # - Wikipedia
                r'by\s+([A-Za-z\s]+)$',  # by The Guardian
                r'\(([A-Za-z\s]+)\)$'    # (BBC News)
            ]
            
            for pattern in source_patterns:
                match = re.search(pattern, title)
                if match:
                    extracted_source = match.group(1).strip()
                    logger.debug(f"[{self.agent_id}] 소스 추출: 제목에서 패턴 발견 -> {extracted_source}")
                    return extracted_source
        
        # 4. 소스 타입별 기본값
        type_defaults = {
            "web": "웹 검색",
            "vector": "학술 자료",
            "philosopher": "철학 문헌"
        }
        
        default_source = type_defaults.get(source_type, "연구 자료")
        logger.debug(f"[{self.agent_id}] 소스 추출: 기본값 사용 ({source_type}) -> {default_source}")
        return default_source
    
    def _strengthen_single_argument_with_evidence(self, argument: str, reasoning: str, 
                                                evidence_list: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        단일 주장을 증거로 강화
        
        Args:
            argument: 원본 주장
            reasoning: 원본 근거
            evidence_list: 증거 리스트
            
        Returns:
            강화된 주장과 근거
        """
        # 증거를 요약하여 포맷팅
        evidence_summary = []
        for i, evidence in enumerate(evidence_list[:3]):  # 최대 3개 증거만 사용
            key_data = self._extract_key_data(evidence.get("content", ""), evidence)
            source_info = evidence.get("source", "research")
            evidence_summary.append(f"- {key_data} ({source_info})")
        
        evidence_text = "\n".join(evidence_summary)
        
        system_prompt = f"""
You are {self.philosopher_name}, strengthening your philosophical argument with supporting evidence.

Your essence: {self.philosopher_essence}

CRITICAL INSTRUCTIONS:
1. You remain the primary voice - your philosophical perspective dominates (70%)
2. Evidence serves to validate your insights, not replace them (30%)
3. Integrate evidence naturally into your philosophical reasoning
4. Maintain your unique thinking style and approach
5. The strengthened argument should still sound distinctly like you

INTEGRATION APPROACH:
- Start with your philosophical insight
- Show how evidence confirms your reasoning
- Return to philosophical implications
- Keep your voice and style prominent
"""

        user_prompt = f"""
ORIGINAL ARGUMENT: "{argument}"
ORIGINAL REASONING: "{reasoning}"

SUPPORTING EVIDENCE:
{evidence_text}

Strengthen your argument by integrating this evidence while maintaining your philosophical voice as the primary perspective.

REQUIREMENTS:
1. Keep your philosophical reasoning as the foundation (70% philosophy, 30% evidence)
2. Show how the evidence validates your philosophical insights
3. Maintain your distinctive thinking style
4. Make the evidence feel like natural support for your wisdom
5. Return the strengthened argument and reasoning separately

Format your response as:
STRENGTHENED_ARGUMENT: [Your enhanced argument statement]
STRENGTHENED_REASONING: [Your enhanced reasoning with integrated evidence]
"""

        try:
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=800
            )
            
            # 응답에서 강화된 주장과 근거 추출
            strengthened_arg_match = re.search(r'STRENGTHENED_ARGUMENT:\s*(.+?)(?=STRENGTHENED_REASONING:|$)', response, re.DOTALL)
            strengthened_reasoning_match = re.search(r'STRENGTHENED_REASONING:\s*(.+?)$', response, re.DOTALL)
            
            if strengthened_arg_match and strengthened_reasoning_match:
                return {
                    "argument": strengthened_arg_match.group(1).strip(),
                    "reasoning": strengthened_reasoning_match.group(1).strip()
                }
            else:
                logger.warning(f"[{self.agent_id}] Could not parse strengthened argument response")
                return {"argument": argument, "reasoning": reasoning}
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error strengthening argument: {str(e)}")
            return {"argument": argument, "reasoning": reasoning}
    
    def _extract_key_data(self, content: str, evidence: Dict[str, Any]) -> str:
        """
        증거에서 핵심 데이터 추출
        
        Args:
            content: 증거 내용
            evidence: 증거 메타데이터
            
        Returns:
            핵심 데이터 요약
        """
        # 간단한 키워드 기반 추출
        if not content:
            return "relevant research findings"
        
        # 숫자나 통계가 포함된 문장 찾기
        sentences = re.split(r'[.!?]', content)
        for sentence in sentences:
            if re.search(r'\d+(?:\.\d+)?%|\d+(?:,\d+)*\s+(?:people|participants|cases|studies)', sentence):
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 20 and len(clean_sentence) < 150:
                    return clean_sentence
        
        # 통계를 찾지 못한 경우 첫 번째 의미있는 문장 반환
        for sentence in sentences:
            clean_sentence = sentence.strip()
            if len(clean_sentence) > 30 and len(clean_sentence) < 200:
                return clean_sentence
        
        return "relevant research findings"
    
    def _format_evidence_source(self, evidence: Dict[str, Any]) -> str:
        """
        증거 소스 정보를 포맷팅
        
        Args:
            evidence: 증거 메타데이터
            
        Returns:
            포맷팅된 증거 소스 정보
        """
        source_info = evidence.get("source", "research")
        content = evidence.get("content", "No content available")
        title = evidence.get("title", "Unknown Title")
        url = evidence.get("url", evidence.get("link", ""))
        
        if source_info == "research":
            return f"{title} ({content})"
        elif source_info == "web":
            return f"{title} ({url})"
        elif source_info == "philosopher":
            return f"{title} ({source_info})"
        else:
            return f"{title} ({source_info})" 