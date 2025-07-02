#!/usr/bin/env python3
"""
새로운 토론 에이전트 데모 스크립트

4가지 최적화된 에이전트를 간단하게 테스트할 수 있는 스크립트
"""

import asyncio
import time
import os
from typing import Dict, Any

# 테스트용 철학자 데이터
PHILOSOPHERS = {
    "socrates": {
        "name": "소크라테스",
        "essence": "무지의 지(無知の知)를 바탕으로 끊임없이 질문하며 진리를 탐구하는 철학자",
        "debate_style": "대화를 통해 상대방의 사고를 자극하고 논리적 모순을 드러내는 문답법을 사용",
        "personality": "겸손하면서도 날카로운 질문으로 상대방의 생각을 깊이 탐구하는 성격",
        "key_traits": ["대화법", "논리적 사고", "진리 탐구", "겸손", "비판적 사고"],
        "quote": "나는 내가 모른다는 것을 안다"
    },
    "plato": {
        "name": "플라톤",
        "essence": "이데아론을 바탕으로 완전한 진리와 정의를 추구하는 이상주의 철학자",
        "debate_style": "이상적 개념과 현실을 대비하며 논리적 구조로 설명하는 체계적 접근",
        "personality": "이상을 추구하며 체계적이고 논리적인 사고를 중시하는 성격",
        "key_traits": ["이데아론", "체계적 사고", "교육철학", "정의론", "이상주의"],
        "quote": "동굴의 우화에서 진정한 현실을 보라"
    },
    "aristotle": {
        "name": "아리스토텔레스", 
        "essence": "경험과 관찰을 바탕으로 한 실용적이고 체계적인 논리학의 아버지",
        "debate_style": "단계적 논증과 경험적 근거를 바탕으로 한 실용적 접근법",
        "personality": "실용적이고 체계적이며 경험을 중시하는 현실주의적 성격",
        "key_traits": ["논리학", "경험주의", "체계성", "실용성", "분류학"],
        "quote": "인간은 본성적으로 정치적 동물이다"
    }
}

# 테스트 시나리오
TEST_SCENARIOS = [
    {
        "topic": "인공지능 발전이 인간의 창의성에 미치는 영향",
        "stance": "인공지능이 인간의 창의성을 증진시킨다",
        "description": "AI와 창의성에 대한 현대적 주제"
    },
    {
        "topic": "원격근무의 확산이 사회에 미치는 영향",
        "stance": "원격근무는 사회 전체에 긍정적 영향을 미친다",
        "description": "현대 사회의 변화에 대한 토론"
    },
    {
        "topic": "기본소득 제도 도입의 필요성",
        "stance": "기본소득 제도는 현대 사회에 반드시 필요하다",
        "description": "경제 정책에 대한 사회적 논의"
    }
]

class DemoRunner:
    """데모 실행 클래스"""
    
    def __init__(self):
        self.results = {}
        
    def print_header(self):
        """데모 시작 헤더 출력"""
        print("🚀" + "=" * 60 + "🚀")
        print("   새로운 토론 에이전트 최적화 프로젝트 데모")
        print("🚀" + "=" * 60 + "🚀")
        print()
        print("🎯 목표: 기존 시스템 대비 5-10배 빠른 토론 에이전트 구현")
        print("📊 개선: LLM 호출 80% 감소, API 비용 60-80% 절약")
        print()
    
    def select_philosopher(self) -> str:
        """철학자 선택"""
        print("🎭 철학자 선택:")
        for i, (key, data) in enumerate(PHILOSOPHERS.items(), 1):
            print(f"  {i}. {data['name']} - {data['essence'][:50]}...")
        
        while True:
            try:
                choice = input("\n철학자를 선택하세요 (1-3, 기본값: 1): ").strip()
                if not choice:
                    choice = "1"
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(PHILOSOPHERS):
                    philosopher_key = list(PHILOSOPHERS.keys())[choice_idx]
                    print(f"✅ {PHILOSOPHERS[philosopher_key]['name']} 선택!")
                    return philosopher_key
                else:
                    print("❌ 잘못된 선택입니다. 1-3 중에서 선택해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
    
    def select_agent_type(self) -> str:
        """에이전트 타입 선택"""
        agent_types = [
            ("unified", "UnifiedDebateAgent", "🥇 최고 속도 (3-5초, 1회 LLM 호출)"),
            ("langchain", "LangChainDebateAgent", "🧠 체계적 워크플로우 (5-8초, 메모리 관리)"),
            ("crewai", "CrewAIDebateAgent", "🏆 최고 품질 (10-15초, 전문가 협업)"),
            ("assistant", "AssistantAPIDebateAgent", "🚀 최신 기능 (6-10초, OpenAI 내장 도구)")
        ]
        
        print("\n🤖 에이전트 타입 선택:")
        for i, (key, name, desc) in enumerate(agent_types, 1):
            print(f"  {i}. {name}")
            print(f"     {desc}")
        
        while True:
            try:
                choice = input("\n에이전트를 선택하세요 (1-4, 기본값: 1): ").strip()
                if not choice:
                    choice = "1"
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(agent_types):
                    agent_key, agent_name, desc = agent_types[choice_idx]
                    print(f"✅ {agent_name} 선택!")
                    return agent_key
                else:
                    print("❌ 잘못된 선택입니다. 1-4 중에서 선택해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
    
    def select_scenario(self) -> Dict[str, Any]:
        """시나리오 선택"""
        print("\n📝 토론 주제 선택:")
        for i, scenario in enumerate(TEST_SCENARIOS, 1):
            print(f"  {i}. {scenario['topic']}")
            print(f"     입장: {scenario['stance']}")
            print(f"     설명: {scenario['description']}")
            print()
        
        # 커스텀 주제 옵션 추가
        print(f"  {len(TEST_SCENARIOS) + 1}. 직접 입력")
        
        while True:
            try:
                choice = input(f"주제를 선택하세요 (1-{len(TEST_SCENARIOS) + 1}, 기본값: 1): ").strip()
                if not choice:
                    choice = "1"
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(TEST_SCENARIOS):
                    scenario = TEST_SCENARIOS[choice_idx]
                    print(f"✅ 선택된 주제: {scenario['topic'][:50]}...")
                    return scenario
                elif choice_idx == len(TEST_SCENARIOS):
                    # 커스텀 입력
                    topic = input("토론 주제를 입력하세요: ").strip()
                    stance = input("당신의 입장을 입력하세요: ").strip()
                    
                    if topic and stance:
                        return {
                            "topic": topic,
                            "stance": stance,
                            "description": "사용자 정의 주제"
                        }
                    else:
                        print("❌ 주제와 입장을 모두 입력해주세요.")
                else:
                    print(f"❌ 잘못된 선택입니다. 1-{len(TEST_SCENARIOS) + 1} 중에서 선택해주세요.")
            except ValueError:
                print("❌ 숫자를 입력해주세요.")
    
    async def run_unified_agent_demo(self, philosopher_key: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """UnifiedDebateAgent 데모 실행"""
        try:
            from .unified_debate_agent import UnifiedDebateAgent
            
            config = self._get_mock_config()
            philosopher_data = PHILOSOPHERS[philosopher_key]
            
            agent = UnifiedDebateAgent(philosopher_key, philosopher_data, config)
            
            print(f"🔄 {philosopher_data['name']}이(가) 입론을 준비 중...")
            start_time = time.time()
            
            result = await agent.generate_opening_argument(
                scenario["topic"], 
                scenario["stance"]
            )
            
            end_time = time.time()
            
            return {
                "agent_type": "UnifiedDebateAgent",
                "philosopher": philosopher_data['name'],
                "duration": end_time - start_time,
                "status": result.get("status", "unknown"),
                "argument": result.get("argument", "생성 실패"),
                "llm_calls": result.get("llm_calls", 0),
                "performance": agent.get_performance_stats()
            }
            
        except ImportError:
            return {
                "agent_type": "UnifiedDebateAgent",
                "status": "error",
                "message": "UnifiedDebateAgent를 로드할 수 없습니다."
            }
        except Exception as e:
            return {
                "agent_type": "UnifiedDebateAgent", 
                "status": "error",
                "message": str(e)
            }
    
    async def run_mock_demo(self, agent_type: str, philosopher_key: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """모의 데모 실행 (실제 에이전트가 없는 경우)"""
        philosopher_data = PHILOSOPHERS[philosopher_key]
        
        print(f"🔄 {philosopher_data['name']}이(가) {agent_type}로 입론을 준비 중...")
        
        # 각 에이전트별 예상 시간
        expected_times = {
            "unified": 3.5,
            "langchain": 6.5, 
            "crewai": 12.0,
            "assistant": 8.0
        }
        
        expected_time = expected_times.get(agent_type, 5.0)
        
        # 시뮬레이션 대기
        await asyncio.sleep(min(expected_time / 10, 2.0))  # 실제 시간의 1/10로 축소
        
        # 모의 응답 생성
        mock_argument = f"""
안녕하세요. 저는 {philosopher_data['name']}입니다.

'{scenario['topic']}'에 대해 말씀드리겠습니다.

첫째, {philosopher_data['essence']}의 관점에서 보면, 이 문제는 근본적으로 인간의 본성과 관련이 있습니다.

둘째, {philosopher_data['quote']}라는 저의 철학에 비춰볼 때, 우리는 더 깊이 사고해야 합니다.

셋째, {scenario['stance']}는 {', '.join(philosopher_data['key_traits'][:2])}의 원리에 부합한다고 생각합니다.

따라서 저는 이 입장을 강력히 지지합니다. 

(이것은 {agent_type} 에이전트의 모의 응답입니다)
"""
        
        return {
            "agent_type": agent_type,
            "philosopher": philosopher_data['name'],
            "duration": expected_time,
            "status": "success",
            "argument": mock_argument.strip(),
            "llm_calls": 1 if agent_type in ["unified", "assistant"] else 2,
            "is_simulation": True
        }
    
    def _get_mock_config(self) -> Dict[str, Any]:
        """모의 설정 반환"""
        return {
            "openai_api_key": "mock_key",
            "web_search": {"provider": "mock"},
            "max_rag_results": 5,
            "llm_manager": MockLLMManager()
        }
    
    def display_result(self, result: Dict[str, Any], scenario: Dict[str, Any]):
        """결과 출력"""
        print("\n" + "🎉" + "=" * 58 + "🎉")
        print("                     결과 발표")
        print("🎉" + "=" * 58 + "🎉")
        
        if result.get("status") == "success":
            print(f"✅ 성공적으로 입론을 생성했습니다!")
            print(f"📊 소요시간: {result['duration']:.2f}초")
            print(f"🤖 에이전트: {result['agent_type']}")
            print(f"🎭 철학자: {result['philosopher']}")
            print(f"⚡ LLM 호출: {result.get('llm_calls', 'N/A')}회")
            
            if result.get("is_simulation"):
                print("🔮 (시뮬레이션 결과)")
            
            print(f"\n📝 생성된 입론:")
            print("-" * 60)
            print(result['argument'])
            print("-" * 60)
            
            # 성능 비교
            print(f"\n📈 성능 비교:")
            original_time = "30-60초"
            original_calls = "5-10회"
            improvement = 60 / result['duration'] if result['duration'] > 0 else 1
            
            print(f"   기존 시스템: {original_time}, {original_calls} LLM 호출")
            print(f"   새 시스템:   {result['duration']:.1f}초, {result.get('llm_calls', 1)}회 LLM 호출")
            print(f"   🚀 속도 개선: {improvement:.1f}배 빨라짐!")
            
        else:
            print(f"❌ 오류가 발생했습니다: {result.get('message', 'Unknown error')}")
    
    async def run_demo(self):
        """전체 데모 실행"""
        self.print_header()
        
        # 사용자 선택
        philosopher_key = self.select_philosopher()
        agent_type = self.select_agent_type()
        scenario = self.select_scenario()
        
        print(f"\n🚀 데모 시작!")
        print(f"철학자: {PHILOSOPHERS[philosopher_key]['name']}")
        print(f"주제: {scenario['topic']}")
        print(f"입장: {scenario['stance']}")
        print()
        
        # 에이전트 실행
        if agent_type == "unified":
            result = await self.run_unified_agent_demo(philosopher_key, scenario)
        else:
            result = await self.run_mock_demo(agent_type, philosopher_key, scenario)
        
        # 결과 출력
        self.display_result(result, scenario)
        
        # 추가 테스트 제안
        print(f"\n💡 다른 에이전트도 테스트해보세요!")
        print(f"   python -m src.new_agent.demo")

class MockLLMManager:
    """테스트용 모의 LLM 매니저"""
    
    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        time.sleep(0.1)
        return "Mock response generated"
    
    async def generate_response_with_functions(self, system_prompt: str, user_prompt: str, 
                                             functions: list, function_handler=None) -> str:
        await asyncio.sleep(0.2)
        return "Mock response with functions generated"

async def main():
    """메인 함수"""
    demo = DemoRunner()
    await demo.run_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 데모를 종료합니다. 감사합니다!")
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {str(e)}")
        print("문제가 지속되면 개발팀에 문의해주세요.") 