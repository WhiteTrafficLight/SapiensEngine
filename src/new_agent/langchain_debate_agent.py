"""
LangChain 기반 토론 에이전트

LangChain의 체인, 메모리, 캐싱 기능을 활용하여
구조화된 워크플로우로 토론 응답을 생성

주요 기능:
- Chain 기반 워크플로우
- ConversationBufferMemory로 컨텍스트 관리
- 캐싱으로 중복 작업 방지
- LCEL로 복잡한 로직 간소화
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# LangChain imports
try:
    from langchain.chains import LLMChain, SequentialChain
    from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain.prompts import PromptTemplate, ChatPromptTemplate
    from langchain.schema import BaseOutputParser
    from langchain.cache import InMemoryCache
    from langchain.globals import set_llm_cache
    from langchain.schema.runnable import RunnablePassthrough, RunnableParallel
    from langchain.schema.output_parser import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.warning("LangChain not available. Please install: pip install langchain")

logger = logging.getLogger(__name__)

class ArgumentOutputParser(BaseOutputParser):
    """논증 출력 파싱"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """생성된 텍스트를 구조화된 논증으로 파싱"""
        lines = text.strip().split('\n')
        
        result = {
            "opening": "",
            "arguments": [],
            "conclusion": "",
            "raw_text": text
        }
        
        current_section = "opening"
        current_argument = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "첫째" in line or "둘째" in line or "셋째" in line:
                if current_argument:
                    result["arguments"].append(current_argument)
                current_argument = line
                current_section = "arguments"
            elif "결론" in line or "따라서" in line or "마지막으로" in line:
                if current_argument:
                    result["arguments"].append(current_argument)
                current_section = "conclusion"
                result["conclusion"] = line
            else:
                if current_section == "opening":
                    result["opening"] += line + " "
                elif current_section == "arguments":
                    current_argument += " " + line
                elif current_section == "conclusion":
                    result["conclusion"] += " " + line
        
        # 마지막 논증 추가
        if current_argument and current_section == "arguments":
            result["arguments"].append(current_argument)
            
        return result

class LangChainDebateAgent:
    """
    LangChain 기반 토론 에이전트
    
    체인과 메모리를 활용한 효율적인 토론 응답 생성
    """
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], config: Dict[str, Any]):
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required for this agent")
            
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.config = config
        self.llm_manager = config.get('llm_manager')
        
        # LangChain 캐싱 설정
        set_llm_cache(InMemoryCache())
        
        # 메모리 설정
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="input",
            output_key="output"
        )
        
        # 요약 메모리 (긴 대화 처리용)
        self.summary_memory = ConversationSummaryMemory(
            llm=self._get_langchain_llm(),
            memory_key="summary",
            input_key="input",
            output_key="output"
        )
        
        # 체인들 초기화
        self._setup_chains()
        
        # 성능 추적
        self.performance_stats = {
            'chain_calls': 0,
            'cache_hits': 0,
            'total_time': 0
        }
    
    def _get_langchain_llm(self):
        """LangChain 호환 LLM 래퍼 생성"""
        # 기존 llm_manager를 LangChain LLM으로 래핑
        from langchain.llms.base import LLM
        
        class CustomLLM(LLM):
            def __init__(self, llm_manager):
                super().__init__()
                self.llm_manager = llm_manager
                
            @property
            def _llm_type(self) -> str:
                return "custom"
                
            def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
                return self.llm_manager.generate_response(
                    system_prompt="", 
                    user_prompt=prompt,
                    llm_model="gpt-4o"
                )
        
        return CustomLLM(self.llm_manager)
    
    def _setup_chains(self):
        """LangChain 체인들 설정"""
        llm = self._get_langchain_llm()
        
        # 1. 논증 분석 체인
        analysis_prompt = PromptTemplate(
            input_variables=["topic", "stance", "philosopher_essence"],
            template="""
당신은 {philosopher_essence}인 철학자입니다.

주제: {topic}
입장: {stance}

이 주제에 대한 핵심 논점 3가지를 분석하고 각각의 근거를 제시하세요.

분석 결과:
1. 논점 1: [논점과 근거]
2. 논점 2: [논점과 근거]  
3. 논점 3: [논점과 근거]

철학자의 관점을 반영하여 분석하세요.
"""
        )
        
        self.analysis_chain = LLMChain(
            llm=llm,
            prompt=analysis_prompt,
            output_key="analysis",
            memory=self.memory
        )
        
        # 2. RAG 검색 체인 (병렬 처리)
        rag_prompt = PromptTemplate(
            input_variables=["analysis", "topic"],
            template="""
다음 분석 결과를 바탕으로 각 논점을 뒷받침할 수 있는 검색 키워드를 생성하세요:

분석: {analysis}
주제: {topic}

각 논점별로 검색할 키워드 3개씩 제안하세요:

논점 1 검색어: [키워드1], [키워드2], [키워드3]
논점 2 검색어: [키워드1], [키워드2], [키워드3]
논점 3 검색어: [키워드1], [키워드2], [키워드3]
"""
        )
        
        self.rag_search_chain = LLMChain(
            llm=llm,
            prompt=rag_prompt,
            output_key="search_keywords"
        )
        
        # 3. 최종 논증 생성 체인
        argument_prompt = PromptTemplate(
            input_variables=["analysis", "search_results", "philosopher_style", "topic", "stance"],
            template="""
당신은 {philosopher_style}인 철학자입니다.

주제: {topic}
입장: {stance}
분석 결과: {analysis}
참고 자료: {search_results}

위 정보를 바탕으로 설득력 있는 입론을 작성하세요.

구조:
1. 인사 및 입장 표명
2. 첫 번째 논증 (근거 포함)
3. 두 번째 논증 (근거 포함)
4. 세 번째 논증 (근거 포함)
5. 강력한 결론

철학자의 특성을 살려 논리적이고 설득력 있게 작성하세요.
"""
        )
        
        self.argument_chain = LLMChain(
            llm=llm,
            prompt=argument_prompt,
            output_key="final_argument",
            output_parser=ArgumentOutputParser()
        )
        
        # 4. 순차 체인 구성 (전체 워크플로우)
        self.full_chain = SequentialChain(
            chains=[self.analysis_chain, self.rag_search_chain, self.argument_chain],
            input_variables=["topic", "stance", "philosopher_essence", "philosopher_style"],
            output_variables=["analysis", "search_keywords", "final_argument"],
            verbose=True
        )
        
        # 5. 상호논증용 빠른 응답 체인
        quick_response_prompt = PromptTemplate(
            input_variables=["opponent_message", "my_stance", "philosopher_style", "chat_history"],
            template="""
당신은 {philosopher_style}인 철학자입니다.

이전 대화: {chat_history}

상대방 발언: {opponent_message}
당신의 입장: {my_stance}

상대방의 발언에 대해 2-3문장으로 날카롭게 반박하세요.
철학자의 관점을 살려 논리적 허점을 지적하거나 질문을 던지세요.

응답:
"""
        )
        
        self.quick_response_chain = LLMChain(
            llm=llm,
            prompt=quick_response_prompt,
            output_key="response",
            memory=self.memory
        )
    
    async def generate_opening_argument(self, topic: str, stance: str) -> Dict[str, Any]:
        """
        입론 생성 - LangChain 체인 활용
        
        Args:
            topic: 토론 주제
            stance: 입장
            
        Returns:
            생성된 입론과 메타데이터
        """
        start_time = time.time()
        
        try:
            # 체인 실행 - 캐싱 자동 적용
            result = await self._run_chain_async(self.full_chain, {
                "topic": topic,
                "stance": stance,
                "philosopher_essence": self.philosopher_data.get('essence', ''),
                "philosopher_style": self.philosopher_data.get('debate_style', '')
            })
            
            # RAG 검색 실행 (병렬)
            search_keywords = result.get('search_keywords', '')
            search_results = await self._parallel_rag_search(search_keywords)
            
            # 검색 결과와 함께 최종 논증 생성
            final_result = await self._run_chain_async(self.argument_chain, {
                "analysis": result.get('analysis', ''),
                "search_results": search_results,
                "philosopher_style": self.philosopher_data.get('debate_style', ''),
                "topic": topic,
                "stance": stance
            })
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 2)  # 2번의 체인 호출
            
            return {
                "status": "success",
                "argument": final_result.get('final_argument', ''),
                "analysis": result.get('analysis', ''),
                "search_keywords": search_keywords,
                "generation_time": end_time - start_time,
                "chain_calls": 2,
                "philosopher": self.philosopher_data['name']
            }
            
        except Exception as e:
            logger.error(f"Error in LangChain opening argument generation: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def generate_interactive_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        상호논증 응답 생성 - 빠른 응답 체인 활용
        
        Args:
            context: 토론 컨텍스트
            
        Returns:
            생성된 응답
        """
        start_time = time.time()
        
        try:
            recent_messages = context.get('recent_messages', [])
            my_stance = context.get('my_stance', '')
            
            # 상대방 마지막 발언 찾기
            opponent_message = ""
            for msg in reversed(recent_messages):
                if msg.get('speaker_id') != self.agent_id:
                    opponent_message = msg.get('text', '')
                    break
            
            if not opponent_message:
                return {"status": "error", "message": "상대방 발언을 찾을 수 없습니다"}
            
            # 빠른 응답 체인 실행
            result = await self._run_chain_async(self.quick_response_chain, {
                "opponent_message": opponent_message,
                "my_stance": my_stance,
                "philosopher_style": self.philosopher_data.get('debate_style', '')
            })
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            return {
                "status": "success",
                "response": result.get('response', ''),
                "generation_time": end_time - start_time,
                "chain_calls": 1,
                "memory_used": len(self.memory.chat_memory.messages)
            }
            
        except Exception as e:
            logger.error(f"Error in LangChain interactive response: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def _run_chain_async(self, chain, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """체인을 비동기로 실행"""
        # LangChain은 기본적으로 동기이므로 asyncio로 래핑
        import asyncio
        
        def run_chain():
            return chain.run(inputs)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_chain)
        return result if isinstance(result, dict) else {"output": result}
    
    async def _parallel_rag_search(self, search_keywords: str) -> str:
        """병렬 RAG 검색 실행"""
        try:
            import asyncio
            
            # 키워드 추출
            keywords = []
            for line in search_keywords.split('\n'):
                if '검색어:' in line:
                    kw_part = line.split('검색어:')[-1].strip()
                    keywords.extend([kw.strip('[], ') for kw in kw_part.split(',')])
            
            # 병렬 검색 실행
            search_tasks = []
            for keyword in keywords[:6]:  # 최대 6개 키워드
                if keyword:
                    search_tasks.append(self._single_search(keyword))
            
            if search_tasks:
                search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                # 결과 통합
                combined_results = []
                for result in search_results:
                    if isinstance(result, list):
                        combined_results.extend(result[:2])  # 각 검색에서 상위 2개만
                
                # 결과 포맷팅
                formatted_results = []
                for i, result in enumerate(combined_results[:6]):  # 최대 6개 결과
                    if isinstance(result, dict):
                        formatted_results.append(f"{i+1}. {result.get('title', '')} - {result.get('snippet', '')[:100]}...")
                
                return '\n'.join(formatted_results) if formatted_results else "검색 결과 없음"
            else:
                return "검색 키워드 없음"
                
        except Exception as e:
            logger.error(f"Parallel RAG search error: {str(e)}")
            return f"검색 오류: {str(e)}"
    
    async def _single_search(self, keyword: str) -> List[Dict[str, Any]]:
        """단일 키워드 검색"""
        try:
            # 기존 검색 시스템 활용
            from ..rag.web_searcher import WebSearcher
            
            searcher = WebSearcher(self.config.get('web_search', {}))
            results = await searcher.search(keyword, max_results=3)
            return results
            
        except Exception as e:
            logger.error(f"Single search error for '{keyword}': {str(e)}")
            return []
    
    def _update_performance_stats(self, execution_time: float, chain_calls: int):
        """성능 통계 업데이트"""
        self.performance_stats['chain_calls'] += chain_calls
        self.performance_stats['total_time'] += execution_time
    
    def clear_memory(self):
        """메모리 초기화"""
        self.memory.clear()
        self.summary_memory.clear()
    
    def get_memory_summary(self) -> str:
        """대화 요약 반환"""
        return self.summary_memory.buffer if hasattr(self.summary_memory, 'buffer') else ""
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        stats = self.performance_stats.copy()
        stats['memory_size'] = len(self.memory.chat_memory.messages)
        stats['cache_enabled'] = True
        return stats 