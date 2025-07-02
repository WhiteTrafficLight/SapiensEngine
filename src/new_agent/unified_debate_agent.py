"""
OpenAI Function Calling 기반 통합 토론 에이전트

기존의 멀티 모듈 구조를 하나의 통합 에이전트로 변경하여
LLM 호출 횟수를 5-10회에서 1-2회로 대폭 감소
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class UnifiedDebateAgent:
    """
    통합 토론 에이전트 - OpenAI Function Calling 기반
    
    기존 여러 모듈의 기능을 하나의 LLM 호출로 통합:
    - 논증 생성
    - RAG 검색
    - 전략 선택
    - 응답 생성
    """
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], config: Dict[str, Any]):
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.config = config
        self.llm_manager = config.get('llm_manager')
        
        # 성능 추적
        self.performance_stats = {
            'llm_calls': 0,
            'total_time': 0,
            'avg_response_time': 0
        }
        
        # 함수 정의
        self.functions = self._define_functions()
        
    def _define_functions(self) -> List[Dict[str, Any]]:
        """OpenAI Function Calling에 사용할 함수들 정의"""
        return [
            {
                "name": "web_search",
                "description": "인터넷에서 관련 정보를 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색할 키워드"},
                        "max_results": {"type": "integer", "description": "최대 검색 결과 수", "default": 5}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "vector_search", 
                "description": "벡터 데이터베이스에서 관련 문서를 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색할 쿼리"},
                        "max_results": {"type": "integer", "description": "최대 검색 결과 수", "default": 3}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "analyze_opponent_argument",
                "description": "상대방 논증의 취약점을 분석합니다",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "argument_text": {"type": "string", "description": "분석할 상대방 논증"},
                        "strategy_type": {"type": "string", "description": "사용할 공격 전략"}
                    },
                    "required": ["argument_text"]
                }
            },
            {
                "name": "get_philosopher_wisdom",
                "description": "특정 철학자의 사상과 접근법을 가져옵니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "관련 주제"},
                        "philosopher": {"type": "string", "description": "철학자 이름"}
                    },
                    "required": ["topic", "philosopher"]
                }
            }
        ]
    
    async def generate_opening_argument(self, topic: str, stance: str) -> Dict[str, Any]:
        """
        통합된 입론 생성 - 기존 5-10번 LLM 호출을 1번으로 통합
        
        Args:
            topic: 토론 주제
            stance: 입장 (찬성/반대)
            
        Returns:
            생성된 입론과 메타데이터
        """
        start_time = time.time()
        
        system_prompt = f"""
당신은 {self.philosopher_data['name']}입니다.

철학자 특성:
- 본질: {self.philosopher_data.get('essence', '')}
- 토론 스타일: {self.philosopher_data.get('debate_style', '')}
- 성격: {self.philosopher_data.get('personality', '')}

주제: {topic}
당신의 입장: {stance}

다음 순서로 입론을 작성하세요:

1. 먼저 필요하다면 web_search나 vector_search를 사용해 관련 정보를 수집하세요
2. get_philosopher_wisdom을 사용해 당신의 철학적 관점을 확인하세요
3. 수집된 정보를 바탕으로 강력한 입론을 작성하세요

입론은 다음 구조로 작성하세요:
- 인사 및 입장 표명
- 3개의 핵심 논증 (각각 근거와 함께)
- 강력한 결론

철학자의 특성을 살려 설득력 있게 작성하세요.
"""

        try:
            # Function Calling을 활용한 통합 처리
            response = await self.llm_manager.generate_response_with_functions(
                system_prompt=system_prompt,
                user_prompt=f"'{topic}'에 대한 {stance} 입장의 입론을 작성하세요.",
                functions=self.functions,
                function_handler=self._handle_function_call
            )
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            return {
                "status": "success",
                "argument": response,
                "generation_time": end_time - start_time,
                "llm_calls": 1,
                "philosopher": self.philosopher_data['name']
            }
            
        except Exception as e:
            logger.error(f"Error generating opening argument: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def generate_interactive_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        상호논증 응답 생성 - 상황 분석부터 응답까지 한 번에 처리
        
        Args:
            context: 토론 컨텍스트 (최근 메시지, 상대방 정보 등)
            
        Returns:
            생성된 응답
        """
        start_time = time.time()
        
        recent_messages = context.get('recent_messages', [])
        topic = context.get('topic', '')
        my_stance = context.get('my_stance', '')
        
        # 최근 상대방 발언 분석
        opponent_last_message = None
        for msg in reversed(recent_messages):
            if msg.get('speaker_id') != self.agent_id:
                opponent_last_message = msg
                break
        
        if not opponent_last_message:
            return {"status": "error", "message": "상대방 발언을 찾을 수 없습니다"}
        
        system_prompt = f"""
당신은 {self.philosopher_data['name']}입니다.

철학자 특성:
- 본질: {self.philosopher_data.get('essence', '')}
- 토론 스타일: {self.philosopher_data.get('debate_style', '')}

현재 상황:
- 주제: {topic}
- 당신의 입장: {my_stance}
- 상대방 마지막 발언: "{opponent_last_message.get('text', '')}"

다음 과정을 거쳐 응답하세요:

1. analyze_opponent_argument로 상대방 논증의 취약점을 분석하세요
2. 필요시 web_search로 반박 자료를 찾으세요
3. 당신의 철학적 관점에서 2-3문장의 날카로운 반박을 작성하세요

응답은 짧고 직접적이며 철학자다운 깊이가 있어야 합니다.
"""

        try:
            response = await self.llm_manager.generate_response_with_functions(
                system_prompt=system_prompt,
                user_prompt="상대방의 마지막 발언에 대해 반박하세요.",
                functions=self.functions,
                function_handler=self._handle_function_call
            )
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            return {
                "status": "success",
                "response": response,
                "generation_time": end_time - start_time,
                "llm_calls": 1
            }
            
        except Exception as e:
            logger.error(f"Error generating interactive response: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def _handle_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Function Call 처리"""
        try:
            if function_name == "web_search":
                return await self._web_search(arguments.get('query'), arguments.get('max_results', 5))
            elif function_name == "vector_search":
                return await self._vector_search(arguments.get('query'), arguments.get('max_results', 3))
            elif function_name == "analyze_opponent_argument":
                return await self._analyze_opponent_argument(arguments.get('argument_text'), arguments.get('strategy_type'))
            elif function_name == "get_philosopher_wisdom":
                return await self._get_philosopher_wisdom(arguments.get('topic'), arguments.get('philosopher'))
            else:
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error in function call {function_name}: {str(e)}")
            return {"error": str(e)}
    
    async def _web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """웹 검색 실행"""
        try:
            # OpenAI Web Search API 활용 (향후 구현)
            # 현재는 기존 검색 시스템 활용
            from ..rag.web_searcher import WebSearcher
            
            searcher = WebSearcher(self.config.get('web_search', {}))
            results = await searcher.search(query, max_results)
            
            return {
                "results": results,
                "query": query,
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return {"error": str(e), "results": []}
    
    async def _vector_search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """벡터 검색 실행"""
        try:
            # OpenAI Embeddings API 활용 벡터 검색
            # 기존 시스템과 통합
            search_results = []  # 실제 구현 필요
            
            return {
                "results": search_results,
                "query": query,
                "total_results": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return {"error": str(e), "results": []}
    
    async def _analyze_opponent_argument(self, argument_text: str, strategy_type: str = None) -> Dict[str, Any]:
        """상대방 논증 분석"""
        try:
            # 간단한 키워드 기반 취약점 분석
            vulnerabilities = []
            
            # 논리적 오류 찾기
            if "모든" in argument_text or "항상" in argument_text:
                vulnerabilities.append("과도한 일반화")
            
            if "~때문에" in argument_text:
                vulnerabilities.append("인과관계 검증 필요")
                
            if "당연히" in argument_text or "명백히" in argument_text:
                vulnerabilities.append("근거 부족")
            
            return {
                "vulnerabilities": vulnerabilities,
                "suggested_attack": "논리적 근거 요구" if vulnerabilities else "추가 질문",
                "confidence": 0.8 if vulnerabilities else 0.3
            }
            
        except Exception as e:
            logger.error(f"Argument analysis error: {str(e)}")
            return {"error": str(e)}
    
    async def _get_philosopher_wisdom(self, topic: str, philosopher: str) -> Dict[str, Any]:
        """철학자 지혜 검색"""
        try:
            # 철학자 데이터에서 관련 내용 추출
            wisdom = {
                "quote": self.philosopher_data.get('quote', ''),
                "key_concepts": self.philosopher_data.get('key_traits', []),
                "approach": self.philosopher_data.get('essence', ''),
                "topic_relevance": f"{philosopher}의 {topic}에 대한 관점"
            }
            
            return wisdom
            
        except Exception as e:
            logger.error(f"Philosopher wisdom error: {str(e)}")
            return {"error": str(e)}
    
    def _update_performance_stats(self, execution_time: float, llm_calls: int):
        """성능 통계 업데이트"""
        self.performance_stats['llm_calls'] += llm_calls
        self.performance_stats['total_time'] += execution_time
        
        if self.performance_stats['llm_calls'] > 0:
            self.performance_stats['avg_response_time'] = (
                self.performance_stats['total_time'] / self.performance_stats['llm_calls']
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return self.performance_stats.copy() 