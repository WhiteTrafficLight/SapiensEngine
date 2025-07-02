"""
CrewAI 기반 협업 토론 에이전트

여러 전문가 에이전트가 역할을 분담하여 협업하는 구조:
- 논증 분석가: 주제 분석 및 논점 도출
- 정보 수집가: RAG 검색 및 자료 수집
- 반박 전문가: 상대방 논증 분석 및 공격 전략
- 작성자: 최종 논증 및 응답 작성

각 에이전트가 전문성을 발휘하여 고품질 결과 생성
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# CrewAI imports
try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    from langchain.tools import Tool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not available. Please install: pip install crewai")

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """웹 검색 도구"""
    name: str = "web_search"
    description: str = "인터넷에서 관련 정보를 검색합니다"
    
    def __init__(self, web_searcher):
        super().__init__()
        self.web_searcher = web_searcher
    
    def _run(self, query: str) -> str:
        """검색 실행"""
        try:
            results = asyncio.run(self.web_searcher.search(query, max_results=3))
            if results:
                formatted = []
                for i, result in enumerate(results[:3]):
                    formatted.append(f"{i+1}. {result.get('title', '')} - {result.get('snippet', '')[:150]}...")
                return '\n'.join(formatted)
            return "검색 결과 없음"
        except Exception as e:
            return f"검색 오류: {str(e)}"

class ArgumentAnalysisTool(BaseTool):
    """논증 분석 도구"""
    name: str = "analyze_argument"
    description: str = "텍스트에서 논증 구조와 취약점을 분석합니다"
    
    def _run(self, text: str) -> str:
        """논증 분석 실행"""
        try:
            # 간단한 논증 분석
            analysis = {
                "main_claims": [],
                "premises": [],
                "vulnerabilities": []
            }
            
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 주장 탐지
                if any(word in sentence for word in ['주장', '생각', '믿는다', '확신']):
                    analysis["main_claims"].append(sentence)
                
                # 전제 탐지
                if any(word in sentence for word in ['왜냐하면', '때문에', '근거', '이유']):
                    analysis["premises"].append(sentence)
                
                # 취약점 탐지
                if any(word in sentence for word in ['모든', '항상', '절대', '당연히']):
                    analysis["vulnerabilities"].append(f"과도한 일반화: {sentence}")
            
            return f"""
논증 분석 결과:
주요 주장: {'; '.join(analysis['main_claims'][:2])}
전제/근거: {'; '.join(analysis['premises'][:2])}
취약점: {'; '.join(analysis['vulnerabilities'][:2])}
"""
        except Exception as e:
            return f"분석 오류: {str(e)}"

class CrewAIDebateAgent:
    """
    CrewAI 기반 협업 토론 에이전트
    
    여러 전문가 에이전트가 협업하여 토론 응답 생성
    """
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], config: Dict[str, Any]):
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI is required for this agent")
            
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.config = config
        self.llm_manager = config.get('llm_manager')
        
        # 도구 초기화
        self._setup_tools()
        
        # 전문가 에이전트들 생성
        self._create_expert_agents()
        
        # 성능 추적
        self.performance_stats = {
            'crew_executions': 0,
            'total_agents': 4,
            'total_time': 0,
            'task_completion_times': []
        }
    
    def _setup_tools(self):
        """도구들 설정"""
        try:
            from ..rag.web_searcher import WebSearcher
            web_searcher = WebSearcher(self.config.get('web_search', {}))
            
            self.web_search_tool = WebSearchTool(web_searcher)
            self.argument_analysis_tool = ArgumentAnalysisTool()
            
        except Exception as e:
            logger.error(f"Error setting up tools: {str(e)}")
            # 폴백 도구들
            self.web_search_tool = None
            self.argument_analysis_tool = None
    
    def _create_expert_agents(self):
        """전문가 에이전트들 생성"""
        philosopher_name = self.philosopher_data.get('name', '철학자')
        philosopher_essence = self.philosopher_data.get('essence', '')
        
        # 1. 논증 분석가
        self.argument_analyst = Agent(
            role="논증 분석가",
            goal="주제를 깊이 분석하고 핵심 논점들을 도출합니다",
            backstory=f"""
당신은 {philosopher_name}의 사상을 깊이 이해하는 논증 분석 전문가입니다.
{philosopher_essence}
주어진 주제에 대해 철학적 관점에서 핵심 논점들을 도출하고 논리적 구조를 분석합니다.
""",
            verbose=True,
            allow_delegation=False,
            tools=[self.argument_analysis_tool] if self.argument_analysis_tool else []
        )
        
        # 2. 정보 수집가
        self.research_specialist = Agent(
            role="정보 수집가",
            goal="논증을 뒷받침할 수 있는 신뢰할 만한 정보와 자료를 수집합니다",
            backstory=f"""
당신은 {philosopher_name}의 철학적 관점에서 관련 정보를 수집하는 전문가입니다.
웹 검색과 자료 분석을 통해 논증을 강화할 수 있는 증거들을 찾아내는 것이 전문입니다.
철학자의 사상과 일치하는 자료들을 우선적으로 수집합니다.
""",
            verbose=True,
            allow_delegation=False,
            tools=[self.web_search_tool] if self.web_search_tool else []
        )
        
        # 3. 반박 전문가
        self.counter_expert = Agent(
            role="반박 전문가",
            goal="상대방 논증의 약점을 찾아내고 효과적인 반박 전략을 수립합니다",
            backstory=f"""
당신은 {philosopher_name}의 날카로운 분석력을 바탕으로 한 반박 전문가입니다.
{philosopher_essence}
상대방의 논증에서 논리적 허점, 근거 부족, 가정의 문제점 등을 찾아내어
효과적인 반박과 질문을 제시하는 것이 전문입니다.
""",
            verbose=True,
            allow_delegation=False,
            tools=[self.argument_analysis_tool] if self.argument_analysis_tool else []
        )
        
        # 4. 작성자
        self.final_writer = Agent(
            role="최종 작성자",
            goal=f"{philosopher_name}의 스타일로 설득력 있는 토론 응답을 작성합니다",
            backstory=f"""
당신은 {philosopher_name} 자신입니다.
{philosopher_essence}
{self.philosopher_data.get('debate_style', '')}

다른 전문가들이 수집한 분석, 정보, 반박 전략을 바탕으로
철학자 본인의 스타일과 개성을 살려 최종 응답을 작성합니다.
논리적이면서도 철학자의 독특한 관점과 표현 방식을 반영합니다.
""",
            verbose=True,
            allow_delegation=False
        )
    
    async def generate_opening_argument(self, topic: str, stance: str) -> Dict[str, Any]:
        """
        협업을 통한 입론 생성
        
        Args:
            topic: 토론 주제
            stance: 입장
            
        Returns:
            생성된 입론과 메타데이터
        """
        start_time = time.time()
        
        try:
            # 태스크들 정의
            analysis_task = Task(
                description=f"""
주제 '{topic}'에 대해 {stance} 입장에서 다음을 수행하세요:

1. 주제의 핵심 쟁점들을 분석하세요
2. {stance} 입장에서 제시할 수 있는 3가지 주요 논점을 도출하세요
3. 각 논점의 논리적 근거와 철학적 배경을 설명하세요
4. 예상되는 반대 논리도 함께 분석하세요

{self.philosopher_data.get('name', '')}의 철학적 관점을 반영하여 분석하세요.
""",
                agent=self.argument_analyst
            )
            
            research_task = Task(
                description=f"""
논증 분석가의 분석 결과를 바탕으로 다음을 수행하세요:

1. 각 논점을 뒷받침할 수 있는 관련 정보를 웹에서 검색하세요
2. 신뢰할 만한 자료와 데이터를 수집하세요
3. {self.philosopher_data.get('name', '')}의 사상과 연관된 자료들을 우선 수집하세요
4. 수집된 정보를 논점별로 정리하세요

검색 결과는 간결하고 핵심적인 내용만 포함하세요.
""",
                agent=self.research_specialist,
                context=[analysis_task]
            )
            
            writing_task = Task(
                description=f"""
논증 분석가의 분석과 정보 수집가의 자료를 바탕으로 다음을 수행하세요:

1. {self.philosopher_data.get('name', '')}의 스타일로 입론을 작성하세요
2. 다음 구조를 따르세요:
   - 인사 및 입장 표명
   - 첫 번째 논증 (근거와 자료 포함)
   - 두 번째 논증 (근거와 자료 포함)
   - 세 번째 논증 (근거와 자료 포함)
   - 강력한 결론

3. 철학자의 특징을 살려 설득력 있게 작성하세요:
   - 특성: {self.philosopher_data.get('personality', '')}
   - 토론 스타일: {self.philosopher_data.get('debate_style', '')}

4. 논리적이면서도 철학자만의 독특한 관점을 반영하세요

최종 입론만 출력하세요.
""",
                agent=self.final_writer,
                context=[analysis_task, research_task]
            )
            
            # Crew 생성 및 실행
            crew = Crew(
                agents=[self.argument_analyst, self.research_specialist, self.final_writer],
                tasks=[analysis_task, research_task, writing_task],
                process=Process.sequential,
                verbose=True
            )
            
            # 비동기 실행
            result = await self._run_crew_async(crew)
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 3)
            
            return {
                "status": "success",
                "argument": result,
                "generation_time": end_time - start_time,
                "agents_involved": 3,
                "workflow": "sequential",
                "philosopher": self.philosopher_data['name']
            }
            
        except Exception as e:
            logger.error(f"Error in CrewAI opening argument generation: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def generate_interactive_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        협업을 통한 상호논증 응답 생성
        
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
            
            # 반박 분석 태스크
            counter_analysis_task = Task(
                description=f"""
상대방의 다음 발언을 분석하세요:
"{opponent_message}"

다음을 수행하세요:
1. 상대방 논증의 구조를 분석하세요
2. 논리적 허점이나 약점을 찾아내세요
3. 근거가 부족한 부분을 지적하세요
4. 가장 효과적인 반박 포인트 2-3개를 제시하세요

{self.philosopher_data.get('name', '')}의 관점에서 분석하세요.
""",
                agent=self.counter_expert
            )
            
            # 빠른 응답 작성 태스크
            quick_response_task = Task(
                description=f"""
반박 전문가의 분석을 바탕으로 다음을 수행하세요:

1. {self.philosopher_data.get('name', '')}의 스타일로 2-3문장의 날카로운 응답을 작성하세요
2. 상대방의 가장 약한 부분을 공격하세요
3. 질문이나 논리적 지적을 포함하세요
4. 철학자의 특성을 살려 깊이 있으면서도 직접적으로 작성하세요

현재 입장: {my_stance}
철학자 스타일: {self.philosopher_data.get('debate_style', '')}

간결하고 임팩트 있는 응답만 출력하세요.
""",
                agent=self.final_writer,
                context=[counter_analysis_task]
            )
            
            # 빠른 Crew 실행 (2개 에이전트만 사용)
            quick_crew = Crew(
                agents=[self.counter_expert, self.final_writer],
                tasks=[counter_analysis_task, quick_response_task],
                process=Process.sequential,
                verbose=True
            )
            
            result = await self._run_crew_async(quick_crew)
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 2)
            
            return {
                "status": "success",
                "response": result,
                "generation_time": end_time - start_time,
                "agents_involved": 2,
                "workflow": "quick_response"
            }
            
        except Exception as e:
            logger.error(f"Error in CrewAI interactive response: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def _run_crew_async(self, crew) -> str:
        """Crew를 비동기로 실행"""
        loop = asyncio.get_event_loop()
        
        def run_crew():
            return crew.kickoff()
        
        result = await loop.run_in_executor(None, run_crew)
        return str(result) if result else "응답 생성 실패"
    
    def _update_performance_stats(self, execution_time: float, agents_used: int):
        """성능 통계 업데이트"""
        self.performance_stats['crew_executions'] += 1
        self.performance_stats['total_time'] += execution_time
        self.performance_stats['task_completion_times'].append({
            'execution': self.performance_stats['crew_executions'],
            'time': execution_time,
            'agents_used': agents_used
        })
    
    def get_agent_status(self) -> Dict[str, Any]:
        """각 전문가 에이전트의 상태 반환"""
        return {
            "argument_analyst": {
                "role": self.argument_analyst.role,
                "goal": self.argument_analyst.goal,
                "tools": len(self.argument_analyst.tools) if self.argument_analyst.tools else 0
            },
            "research_specialist": {
                "role": self.research_specialist.role,
                "goal": self.research_specialist.goal,
                "tools": len(self.research_specialist.tools) if self.research_specialist.tools else 0
            },
            "counter_expert": {
                "role": self.counter_expert.role,
                "goal": self.counter_expert.goal,
                "tools": len(self.counter_expert.tools) if self.counter_expert.tools else 0
            },
            "final_writer": {
                "role": self.final_writer.role,
                "goal": self.final_writer.goal,
                "tools": 0
            }
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        stats = self.performance_stats.copy()
        if stats['crew_executions'] > 0:
            stats['avg_execution_time'] = stats['total_time'] / stats['crew_executions']
        else:
            stats['avg_execution_time'] = 0
        return stats 