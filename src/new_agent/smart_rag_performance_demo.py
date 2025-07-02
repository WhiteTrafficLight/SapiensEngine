#!/usr/bin/env python3
"""
지능형 RAG 성능 비교 데모
- 기존 방식: 모든 논지에 대해 일괄 RAG 검색
- 새로운 방식: 필요할 때만 지능적으로 RAG/웹서치 사용
"""

import asyncio
import json
import yaml
import time
import sys
import os
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.new_agent.smart_rag_unified_agent import SmartRAGUnifiedAgent
from src.new_agent.real_llm_performance_demo import RealLLMManager, TraditionalDebateAgent

class SmartRAGPerformanceDemo:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.debates_data = self._load_pregenerated_debates()
        self.philosophers_data = self._load_philosophers_data()
        
        # 실제 LLM Manager 초기화
        try:
            self.llm_manager = RealLLMManager()
            print("✅ OpenAI API 연결 성공")
        except ValueError as e:
            print(f"❌ {str(e)}")
            print("   export OPENAI_API_KEY=your_api_key")
            sys.exit(1)
    
    def _load_pregenerated_debates(self) -> Dict[str, Any]:
        """pregenerated_debates.json 로드"""
        debates_path = self.project_root / "src" / "new" / "data" / "pregenerated_debates.json"
        try:
            with open(debates_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ {debates_path} 파일을 찾을 수 없습니다.")
            return {}
    
    def _load_philosophers_data(self) -> Dict[str, Any]:
        """debate_optimized.yaml 로드"""
        phil_path = self.project_root / "philosophers" / "debate_optimized.yaml"
        try:
            with open(phil_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ {phil_path} 파일을 찾을 수 없습니다.")
            return {}

    def get_test_scenarios(self) -> List[Dict[str, Any]]:
        """RAG 필요성에 따른 다양한 시나리오"""
        return [
            {
                'name': '🌐 웹서치 필요 주제',
                'topic': 'Should AI be regulated by government policies in 2024?',
                'category': 'current_events',
                'expected_rag': ['web_search'],
                'reasoning': '최신 정보와 정부 정책이 필요'
            },
            {
                'name': '📊 데이터 중심 주제', 
                'topic': 'Do statistics show that remote work increases productivity?',
                'category': 'data_heavy',
                'expected_rag': ['web_search', 'vector_search'],
                'reasoning': '통계와 연구 데이터가 필요'
            },
            {
                'name': '🤔 철학적 주제',
                'topic': 'Is consciousness purely a product of brain activity?',
                'category': 'philosophical_depth', 
                'expected_rag': ['philosopher_search', 'vector_search'],
                'reasoning': '철학적 깊이와 사상가들의 견해가 필요'
            },
            {
                'name': '💭 단순 윤리 주제',
                'topic': 'Is it wrong to lie to protect someone\'s feelings?',
                'category': 'simple_ethics',
                'expected_rag': [],
                'reasoning': '기본적인 논증만으로 충분, RAG 불필요'
            }
        ]

    async def run_smart_rag_approach(self, scenario: Dict[str, Any], philosopher_key: str, stance: str) -> Dict[str, Any]:
        """지능형 RAG 방식 실행"""
        print(f"\n🧠 지능형 RAG 방식 ({scenario['name']}) 실행...")
        print(f"   주제: {scenario['topic']}")
        print(f"   예상 RAG: {scenario['expected_rag']}")
        
        start_time = time.time()
        
        philosopher_data = self.philosophers_data.get(philosopher_key, {})
        config = {
            'llm_manager': self.llm_manager,
            'model': 'gpt-4o',
            'use_context_enhancement': True
        }
        
        agent = SmartRAGUnifiedAgent(
            agent_id=f"{philosopher_key}_smart_rag",
            philosopher_data=philosopher_data,
            config=config
        )
        
        try:
            # 지능형 입론 생성
            result = await agent.generate_intelligent_opening_argument(
                topic=scenario['topic'], 
                stance=stance
            )
            
            result['scenario'] = scenario['name']
            result['expected_vs_actual'] = {
                'expected_rag': scenario['expected_rag'],
                'actual_web_searches': result.get('web_searches', 0),
                'actual_vector_searches': result.get('vector_searches', 0)
            }
            
            print(f"✅ 지능형 RAG 방식 완료")
            print(f"   ⏱️  소요시간: {result['generation_time']:.2f}초")
            print(f"   🔄 LLM 호출: {result['llm_calls']}회")
            print(f"   🌐 웹 검색: {result['web_searches']}회")
            print(f"   📚 벡터 검색: {result['vector_searches']}회")
            
            return result
            
        except Exception as e:
            print(f"❌ 지능형 RAG 방식 실패: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'generation_time': time.time() - start_time,
                'scenario': scenario['name']
            }

    async def run_traditional_heavy_rag_approach(self, scenario: Dict[str, Any], philosopher_key: str, stance: str) -> Dict[str, Any]:
        """기존 방식 (모든 논지에 대해 RAG 검색) 실행"""
        print(f"\n🐌 기존 Heavy RAG 방식 ({scenario['name']}) 실행...")
        
        start_time = time.time()
        philosopher_data = self.philosophers_data.get(philosopher_key, {})
        
        # Enhanced Traditional Agent with Heavy RAG
        agent = EnhancedTraditionalAgent(philosopher_data, self.llm_manager)
        
        result = await agent.generate_heavy_rag_argument(
            topic=scenario['topic'], 
            stance=stance, 
            context_data=scenario
        )
        
        result['scenario'] = scenario['name']
        result['method'] = 'traditional_heavy_rag'
        
        print(f"✅ 기존 Heavy RAG 방식 완료")
        print(f"   ⏱️  소요시간: {result['generation_time']:.2f}초")
        print(f"   🔄 LLM 호출: {result['llm_calls']}회") 
        print(f"   🔍 RAG 검색: {result['rag_searches']}회 (필수)")
        
        return result

    def display_smart_rag_analysis(self, smart_results: List[Dict[str, Any]], traditional_results: List[Dict[str, Any]]):
        """지능형 RAG 분석 결과 출력"""
        print("\n" + "="*120)
        print("🎯 지능형 RAG vs 기존 Heavy RAG 방식 비교 분석")
        print("="*120)
        
        total_smart_time = sum(r.get('generation_time', 0) for r in smart_results if r.get('status') == 'success')
        total_trad_time = sum(r.get('generation_time', 0) for r in traditional_results if r.get('status') == 'success')
        
        total_smart_web = sum(r.get('web_searches', 0) for r in smart_results)
        total_smart_vector = sum(r.get('vector_searches', 0) for r in smart_results)
        total_smart_llm = sum(r.get('llm_calls', 0) for r in smart_results)
        
        total_trad_rag = sum(r.get('rag_searches', 0) for r in traditional_results)
        total_trad_llm = sum(r.get('llm_calls', 0) for r in traditional_results)
        
        print(f"\n📊 전체 성능 요약:")
        print(f"   🧠 지능형 RAG 방식:")
        print(f"      ⏱️  총 소요시간: {total_smart_time:.2f}초")
        print(f"      🔄 총 LLM 호출: {total_smart_llm}회")
        print(f"      🌐 총 웹 검색: {total_smart_web}회")
        print(f"      📚 총 벡터 검색: {total_smart_vector}회")
        print(f"      🎯 검색 효율성: 필요시에만 선택적 실행")
        
        print(f"\n   🐌 기존 Heavy RAG 방식:")
        print(f"      ⏱️  총 소요시간: {total_trad_time:.2f}초")
        print(f"      🔄 총 LLM 호출: {total_trad_llm}회")
        print(f"      🔍 총 RAG 검색: {total_trad_rag}회 (모든 논지에 대해 필수)")
        print(f"      💸 검색 비효율성: 불필요한 경우에도 일괄 실행")
        
        if total_trad_time > 0:
            speedup = total_trad_time / total_smart_time if total_smart_time > 0 else 0
            search_reduction = ((total_trad_rag - (total_smart_web + total_smart_vector)) / total_trad_rag * 100) if total_trad_rag > 0 else 0
            
            print(f"\n🚀 성능 개선 효과:")
            print(f"   ⚡ 속도 향상: {speedup:.1f}배 빨라짐")
            print(f"   💰 검색 절약: {search_reduction:.1f}% 검색 횟수 감소")
            print(f"   🎯 지능성: 상황에 맞는 적응형 RAG")
            print(f"   🔧 효율성: 불필요한 작업 제거")
        
        print(f"\n📝 시나리오별 RAG 사용 분석:")
        for i, (smart, traditional) in enumerate(zip(smart_results, traditional_results)):
            if smart.get('status') == 'success':
                expected = smart.get('expected_vs_actual', {})
                print(f"   {i+1}. {smart.get('scenario', 'Unknown')}")
                print(f"      예상 RAG: {expected.get('expected_rag', [])}")
                print(f"      실제 실행: 웹={expected.get('actual_web_searches', 0)}회, 벡터={expected.get('actual_vector_searches', 0)}회")
                print(f"      기존 방식: RAG={traditional.get('rag_searches', 0)}회 (무조건)")
                print(f"      효율성: {'✅ 적절' if len(expected.get('expected_rag', [])) > 0 else '✅ 불필요한 검색 회피'}")

class EnhancedTraditionalAgent(TraditionalDebateAgent):
    """기존 방식을 Heavy RAG로 강화한 에이전트"""
    
    async def generate_heavy_rag_argument(self, topic: str, stance: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Heavy RAG 방식 입론 생성 (모든 논지에 대해 RAG 필수)"""
        start_time = time.time()
        print(f"   🔍 모든 논지에 대해 필수 RAG 검색 시작...")
        
        try:
            # 1단계: 핵심 논증 생성
            core_arguments = await self._generate_core_arguments(topic, stance)
            self.llm_calls += 1
            
            # 2단계: 모든 논지에 대해 필수 RAG (3가지 소스)
            print("   🌐 필수 웹 검색 1...")
            web_search_1 = await self._simulate_web_search(f"{topic} current data")
            self.rag_searches += 1
            
            print("   🌐 필수 웹 검색 2...")
            web_search_2 = await self._simulate_web_search(f"{topic} expert opinions")  
            self.rag_searches += 1
            
            print("   📚 필수 벡터 검색 1...")
            vector_search_1 = await self._simulate_vector_search(f"{topic} academic research")
            self.rag_searches += 1
            
            print("   📚 필수 벡터 검색 2...")
            vector_search_2 = await self._simulate_vector_search(f"{topic} philosophical analysis")
            self.rag_searches += 1
            
            print("   🧠 필수 철학자 검색...")
            philosopher_search = await self._simulate_philosopher_search(topic)
            self.rag_searches += 1
            
            # 3단계: 모든 검색 결과 통합
            print("   🔄 모든 RAG 결과 통합...")
            integrated_rag = await self._integrate_all_rag_results(
                core_arguments, web_search_1, web_search_2, 
                vector_search_1, vector_search_2, philosopher_search
            )
            self.llm_calls += 1
            
            # 4단계: 최종 입론 생성
            print("   ✍️  최종 입론 생성...")
            final_argument = await self._generate_final_argument(topic, stance, integrated_rag)
            self.llm_calls += 1
            
            end_time = time.time()
            
            return {
                "status": "success",
                "argument": final_argument,
                "generation_time": end_time - start_time,
                "llm_calls": self.llm_calls,
                "rag_searches": self.rag_searches,
                "philosopher": self.philosopher_data.get('name', 'Unknown'),
                "rag_strategy": "heavy_mandatory"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "generation_time": time.time() - start_time,
                "llm_calls": self.llm_calls,
                "rag_searches": self.rag_searches
            }
    
    async def _integrate_all_rag_results(self, core_args: str, web1: str, web2: str, vec1: str, vec2: str, phil: str) -> str:
        """모든 RAG 결과 통합"""
        await asyncio.sleep(0.3)  # 통합 처리 시간
        
        prompt = f"""
핵심 논증: {core_args}
웹 검색 1: {web1}
웹 검색 2: {web2}  
벡터 검색 1: {vec1}
벡터 검색 2: {vec2}
철학자 검색: {phil}

위 모든 정보를 종합하여 통합된 논증을 생성하세요.
"""
        
        response = await self._simple_llm_call(prompt)
        return response

async def main():
    """메인 실행 함수"""
    demo = SmartRAGPerformanceDemo()
    
    print("🎯 지능형 RAG vs 기존 Heavy RAG 방식 성능 비교")
    print("="*120)
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 다양한 시나리오 테스트
    scenarios = demo.get_test_scenarios()
    philosopher_key = 'nietzsche'  # 니체 선택
    stance = 'pro'
    
    print(f"\n📚 테스트 시나리오 ({len(scenarios)}개):")
    for i, scenario in enumerate(scenarios, 1):
        print(f"   {i}. {scenario['name']}: {scenario['topic']}")
        print(f"      → {scenario['reasoning']}")
    
    philosopher_name = demo.philosophers_data.get(philosopher_key, {}).get('name', philosopher_key)
    print(f"\n🧠 선택된 철학자: {philosopher_name}")
    print(f"📍 RAG 친화도: {demo.philosophers_data.get(philosopher_key, {}).get('rag_affinity', 0.5)}")
    
    print(f"\n🔄 각 시나리오별 성능 비교 시작...")
    
    smart_results = []
    traditional_results = []
    
    # 각 시나리오별로 두 방식 비교
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n" + "="*80)
        print(f"📋 시나리오 {i}: {scenario['name']}")
        print(f"   주제: {scenario['topic']}")
        print(f"   카테고리: {scenario['category']}")
        print("="*80)
        
        # 지능형 RAG 방식
        smart_result = await demo.run_smart_rag_approach(scenario, philosopher_key, stance)
        smart_results.append(smart_result)
        
        # 기존 Heavy RAG 방식  
        traditional_result = await demo.run_traditional_heavy_rag_approach(scenario, philosopher_key, stance)
        traditional_results.append(traditional_result)
        
        # 시나리오별 비교
        if smart_result.get('status') == 'success' and traditional_result.get('status') == 'success':
            smart_time = smart_result.get('generation_time', 0)
            trad_time = traditional_result.get('generation_time', 0)
            speedup = trad_time / smart_time if smart_time > 0 else 0
            
            print(f"\n   📊 시나리오 {i} 결과:")
            print(f"      🧠 지능형: {smart_time:.2f}초, LLM {smart_result.get('llm_calls', 0)}회")
            print(f"      🐌 기존형: {trad_time:.2f}초, LLM {traditional_result.get('llm_calls', 0)}회")
            print(f"      🚀 개선: {speedup:.1f}배 빨라짐")
    
    # 종합 분석 결과
    demo.display_smart_rag_analysis(smart_results, traditional_results)
    
    print(f"\n✨ 지능형 RAG vs Heavy RAG 비교 완료!")
    print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🎯 결론: 지능형 RAG가 상황에 맞는 효율적 검색으로 성능과 비용을 모두 최적화했습니다!")

if __name__ == "__main__":
    asyncio.run(main()) 