"""
OpenAI Assistant API 기반 토론 에이전트

OpenAI의 Assistant API 내장 기능들을 최대한 활용:
- 내장 웹 검색 (Web Search)
- 자동 스레드 관리
- Function Calling
- 파일 분석
- 코드 실행

가장 효율적이고 최신 기능을 활용한 접근법
"""

import logging
import time
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# OpenAI imports
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available. Please install: pip install openai")

logger = logging.getLogger(__name__)

class AssistantAPIDebateAgent:
    """
    OpenAI Assistant API 기반 토론 에이전트
    
    최신 OpenAI 기능들을 활용한 최고 효율의 토론 에이전트
    """
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], config: Dict[str, Any]):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library is required for this agent")
            
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.config = config
        
        # OpenAI 클라이언트 초기화
        self.client = OpenAI(api_key=config.get('openai_api_key'))
        
        # Assistant 생성 (한 번만)
        self.assistant = None
        self.thread = None
        
        # 성능 추적
        self.performance_stats = {
            'api_calls': 0,
            'total_time': 0,
            'thread_messages': 0,
            'tools_used': []
        }
        
        # Assistant 설정
        self._setup_assistant()
    
    def _setup_assistant(self):
        """OpenAI Assistant 설정"""
        try:
            philosopher_name = self.philosopher_data.get('name', '철학자')
            philosopher_essence = self.philosopher_data.get('essence', '')
            debate_style = self.philosopher_data.get('debate_style', '')
            personality = self.philosopher_data.get('personality', '')
            
            # Assistant 생성
            self.assistant = self.client.beta.assistants.create(
                name=f"{philosopher_name} 토론 에이전트",
                instructions=f"""
당신은 {philosopher_name}입니다.

철학자 특성:
- 본질: {philosopher_essence}
- 토론 스타일: {debate_style}
- 성격: {personality}

역할:
1. 토론 주제에 대해 철학자의 관점에서 입론을 작성합니다
2. 상대방 논증을 분석하고 날카로운 반박을 제시합니다
3. 웹 검색을 활용해 논증을 뒷받침할 자료를 찾습니다
4. 철학자의 독특한 사상과 접근법을 반영합니다

지침:
- 항상 논리적이고 설득력 있게 논증하세요
- 철학자의 특성을 살려 깊이 있는 관점을 제시하세요
- 필요시 웹 검색을 활용해 최신 정보를 수집하세요
- 상호논증에서는 간결하고 직접적으로 응답하세요

모든 응답은 주제의 언어로 작성하세요 (한국어 주제면 한국어로, 영어 주제면 영어로).
""",
                model="gpt-4o",
                tools=[
                    {"type": "web_search"},  # 내장 웹 검색
                    {"type": "code_interpreter"},  # 코드 실행 (데이터 분석용)
                    {
                        "type": "function",
                        "function": {
                            "name": "analyze_opponent_argument",
                            "description": "상대방 논증의 구조와 취약점을 분석합니다",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "argument_text": {
                                        "type": "string",
                                        "description": "분석할 상대방 논증 텍스트"
                                    },
                                    "analysis_focus": {
                                        "type": "string",
                                        "description": "분석 초점 (logic, evidence, assumptions)"
                                    }
                                },
                                "required": ["argument_text"]
                            }
                        }
                    },
                    {
                        "type": "function", 
                        "function": {
                            "name": "get_philosopher_perspective",
                            "description": "특정 철학자의 관점에서 주제를 해석합니다",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "topic": {
                                        "type": "string",
                                        "description": "해석할 주제"
                                    },
                                    "aspect": {
                                        "type": "string", 
                                        "description": "관점 측면 (ethical, logical, existential)"
                                    }
                                },
                                "required": ["topic"]
                            }
                        }
                    }
                ]
            )
            
            logger.info(f"Assistant created: {self.assistant.id}")
            
        except Exception as e:
            logger.error(f"Error setting up Assistant: {str(e)}")
            self.assistant = None
    
    async def generate_opening_argument(self, topic: str, stance: str) -> Dict[str, Any]:
        """
        Assistant API를 활용한 입론 생성
        
        Args:
            topic: 토론 주제
            stance: 입장
            
        Returns:
            생성된 입론과 메타데이터
        """
        start_time = time.time()
        
        if not self.assistant:
            return {
                "status": "error", 
                "message": "Assistant not available",
                "generation_time": time.time() - start_time
            }
        
        try:
            # 새 스레드 생성
            thread = self.client.beta.threads.create()
            self.thread = thread
            
            # 메시지 추가
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=f"""
주제: "{topic}"
입장: {stance}

다음 과정을 거쳐 강력한 입론을 작성해주세요:

1. 먼저 web_search를 사용해 이 주제에 대한 최신 정보와 데이터를 검색하세요
2. get_philosopher_perspective를 사용해 당신({self.philosopher_data.get('name', '')})의 철학적 관점을 확인하세요
3. 수집된 정보를 바탕으로 다음 구조로 입론을 작성하세요:

구조:
- 인사 및 입장 표명
- 첫 번째 핵심 논증 (구체적 근거와 자료 포함)
- 두 번째 핵심 논증 (구체적 근거와 자료 포함)  
- 세 번째 핵심 논증 (구체적 근거와 자료 포함)
- 강력한 결론

철학자의 특성을 살려 논리적이고 설득력 있게 작성하세요.
주제의 언어로 응답하세요.
"""
            )
            
            # 실행 및 결과 대기
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant.id
            )
            
            # 실행 완료 대기 및 도구 호출 처리
            result_content = await self._wait_for_run_completion(thread.id, run.id)
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            return {
                "status": "success",
                "argument": result_content,
                "generation_time": end_time - start_time,
                "api_calls": 1,
                "tools_used": self.performance_stats['tools_used'][-5:],  # 최근 5개
                "philosopher": self.philosopher_data['name'],
                "thread_id": thread.id
            }
            
        except Exception as e:
            logger.error(f"Error in Assistant API opening argument generation: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def generate_interactive_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assistant API를 활용한 상호논증 응답 생성
        
        Args:
            context: 토론 컨텍스트
            
        Returns:
            생성된 응답
        """
        start_time = time.time()
        
        if not self.assistant:
            return {
                "status": "error",
                "message": "Assistant not available", 
                "generation_time": time.time() - start_time
            }
        
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
            
            # 기존 스레드 사용 또는 새 스레드 생성
            if not self.thread:
                thread = self.client.beta.threads.create()
                self.thread = thread
            else:
                thread = self.thread
            
            # 빠른 응답 메시지 추가
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user", 
                content=f"""
현재 상황: 상호논증 단계
내 입장: {my_stance}

상대방이 다음과 같이 발언했습니다:
"{opponent_message}"

다음 과정으로 빠르게 응답하세요:

1. analyze_opponent_argument를 사용해 상대방 논증의 취약점을 분석하세요
2. 필요하면 web_search로 반박 근거를 찾으세요
3. 2-3문장의 날카롭고 직접적인 반박을 작성하세요

요구사항:
- 상대방의 가장 약한 지점을 공격하세요
- 논리적 허점이나 근거 부족을 지적하세요
- 철학자의 관점에서 질문이나 지적을 포함하세요
- 간결하고 임팩트 있게 작성하세요

주제의 언어로 응답하세요.
"""
            )
            
            # 실행
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant.id
            )
            
            # 결과 대기
            result_content = await self._wait_for_run_completion(thread.id, run.id)
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            return {
                "status": "success",
                "response": result_content,
                "generation_time": end_time - start_time,
                "api_calls": 1,
                "tools_used": self.performance_stats['tools_used'][-3:],  # 최근 3개
                "thread_messages": self.performance_stats['thread_messages']
            }
            
        except Exception as e:
            logger.error(f"Error in Assistant API interactive response: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def _wait_for_run_completion(self, thread_id: str, run_id: str) -> str:
        """실행 완료 대기 및 도구 호출 처리"""
        max_wait_time = 60  # 최대 60초 대기
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait_time:
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                if run.status == "completed":
                    # 메시지 가져오기
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="desc",
                        limit=1
                    )
                    
                    if messages.data:
                        content = messages.data[0].content[0].text.value
                        self.performance_stats['thread_messages'] = len(messages.data)
                        return content
                    else:
                        return "응답 생성 실패"
                
                elif run.status == "requires_action":
                    # 도구 호출 처리
                    await self._handle_required_actions(thread_id, run_id, run.required_action)
                
                elif run.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Run failed with status: {run.status}")
                    return f"실행 실패: {run.status}"
                
                # 짧은 대기
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error waiting for run completion: {str(e)}")
                return f"대기 중 오류: {str(e)}"
        
        return "응답 대기 시간 초과"
    
    async def _handle_required_actions(self, thread_id: str, run_id: str, required_action):
        """필요한 도구 호출 처리"""
        try:
            tool_outputs = []
            
            for tool_call in required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # 사용된 도구 기록
                self.performance_stats['tools_used'].append({
                    'name': function_name,
                    'timestamp': time.time()
                })
                
                # 함수 실행
                if function_name == "analyze_opponent_argument":
                    output = await self._analyze_opponent_argument(
                        function_args.get('argument_text', ''),
                        function_args.get('analysis_focus', 'logic')
                    )
                elif function_name == "get_philosopher_perspective":
                    output = await self._get_philosopher_perspective(
                        function_args.get('topic', ''),
                        function_args.get('aspect', 'ethical')
                    )
                else:
                    output = f"알 수 없는 함수: {function_name}"
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": output
                })
            
            # 도구 출력 제출
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=tool_outputs
            )
            
        except Exception as e:
            logger.error(f"Error handling required actions: {str(e)}")
    
    async def _analyze_opponent_argument(self, argument_text: str, analysis_focus: str = "logic") -> str:
        """상대방 논증 분석"""
        try:
            analysis = {
                "structure": [],
                "weaknesses": [],
                "attack_points": []
            }
            
            # 문장 분석
            sentences = argument_text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # 논리적 문제 탐지
                if analysis_focus in ["logic", "all"]:
                    if any(word in sentence for word in ['모든', '항상', '절대']):
                        analysis["weaknesses"].append(f"과도한 일반화: {sentence[:50]}...")
                        analysis["attack_points"].append("일반화의 예외 사례 제시")
                    
                    if any(word in sentence for word in ['당연히', '명백히', '분명히']):
                        analysis["weaknesses"].append(f"근거 부족: {sentence[:50]}...")
                        analysis["attack_points"].append("구체적 근거 요구")
                
                # 증거 문제 탐지
                if analysis_focus in ["evidence", "all"]:
                    if any(word in sentence for word in ['연구', '조사', '데이터']) and '에 따르면' not in sentence:
                        analysis["weaknesses"].append(f"출처 불명확: {sentence[:50]}...")
                        analysis["attack_points"].append("구체적 출처와 데이터 요구")
            
            # 결과 포맷팅
            result = f"""
논증 분석 결과:

구조적 약점:
{chr(10).join(['- ' + w for w in analysis["weaknesses"][:3]])}

추천 공격 포인트:
{chr(10).join(['- ' + a for a in analysis["attack_points"][:3]])}

{self.philosopher_data.get('name', '')}의 관점에서 가장 효과적인 반박은 철학적 깊이를 더해 근본적인 가정에 의문을 제기하는 것입니다.
"""
            
            return result
            
        except Exception as e:
            return f"분석 오류: {str(e)}"
    
    async def _get_philosopher_perspective(self, topic: str, aspect: str = "ethical") -> str:
        """철학자 관점 제공"""
        try:
            philosopher_name = self.philosopher_data.get('name', '')
            essence = self.philosopher_data.get('essence', '')
            key_traits = self.philosopher_data.get('key_traits', [])
            quote = self.philosopher_data.get('quote', '')
            
            perspective = f"""
{philosopher_name}의 {topic}에 대한 관점:

핵심 철학: {essence}

이 주제에 대한 접근법:
- 주요 특성: {', '.join(key_traits[:3])}
- 철학적 입장에서 {topic}는 {aspect} 차원에서 중요한 의미를 가집니다

대표적 사상: "{quote}"

이 관점에서 논증을 전개할 때는 {philosopher_name}의 독특한 사고방식을 반영하여 
단순한 찬반을 넘어서 더 깊은 철학적 차원에서 문제를 바라보아야 합니다.
"""
            
            return perspective
            
        except Exception as e:
            return f"관점 조회 오류: {str(e)}"
    
    def _update_performance_stats(self, execution_time: float, api_calls: int):
        """성능 통계 업데이트"""
        self.performance_stats['api_calls'] += api_calls
        self.performance_stats['total_time'] += execution_time
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self.assistant:
                # Assistant 삭제 (선택적)
                # self.client.beta.assistants.delete(self.assistant.id)
                pass
                
            if self.thread:
                # Thread는 자동으로 관리됨
                pass
                
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        stats = self.performance_stats.copy()
        if stats['api_calls'] > 0:
            stats['avg_response_time'] = stats['total_time'] / stats['api_calls']
        else:
            stats['avg_response_time'] = 0
        
        stats['assistant_id'] = self.assistant.id if self.assistant else None
        stats['thread_id'] = self.thread.id if self.thread else None
        return stats
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """대화 기록 반환"""
        if not self.thread:
            return []
        
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=self.thread.id,
                order="asc"
            )
            
            history = []
            for message in messages.data:
                history.append({
                    "role": message.role,
                    "content": message.content[0].text.value if message.content else "",
                    "timestamp": message.created_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return [] 