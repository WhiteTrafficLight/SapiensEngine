import unittest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Add the src directory to the path for imports
current_dir = Path(__file__).parent.absolute()
src_path = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_path))

from agents.participant.debate_participant_agent import DebateParticipantAgent

class TestArgumentGenerationWithRAG(unittest.TestCase):
    """Test opening argument generation with RAG search tracking"""
    
    def setUp(self):
        """Set up test environment"""
        self.agent_id = "nietzsche_agent"
        self.agent_name = "Nietzsche"
        self.topic = "이재명은 중국 공산당의 꼭두각시인가"
        self.stance_statement = "이재명은 중국 공산당의 꼭두각시이다"
        
        # Nietzsche config
        self.nietzsche_config = {
            "role": "pro",  # 찬성 입장
            "personality": "provocative",
            "knowledge_level": "expert",
            "style": "philosophical",
            "philosopher_key": "nietzsche",
            "argumentation_style": "emotional",
            "response_focus": "attack"
        }
        
        # Mock philosopher data for Nietzsche
        self.mock_nietzsche_data = {
            "name": "Friedrich Nietzsche",
            "essence": "God is dead, and we have killed him",
            "debate_style": "Provocative and challenging conventional wisdom",
            "personality": "Bold, uncompromising, critical of weakness",
            "key_traits": ["critical", "provocative", "anti-establishment", "individualistic"],
            "quote": "What does not destroy me, makes me stronger",
            "strategy_weights": {
                "logical_attack": 0.7,
                "emotional_appeal": 0.9,
                "factual_evidence": 0.6,
                "moral_challenge": 1.0,
                "power_analysis": 0.9
            }
        }
        
        # Track RAG search calls
        self.rag_search_calls = {
            "web_search": [],
            "vector_search": [],
            "dialogue_search": [],
            "philosopher_search": []
        }
        
        # Mock search results
        self.mock_search_results = {
            "web_search": [
                {
                    "title": "이재명과 중국의 관계 분석",
                    "content": "이재명 후보의 중국 정책 및 경제 협력 방안에 대한 분석",
                    "url": "https://example.com/analysis1",
                    "relevance_score": 0.85
                },
                {
                    "title": "한국 정치인들의 대중국 정책",
                    "content": "한국 주요 정치인들의 중국에 대한 입장과 정책 비교",
                    "url": "https://example.com/analysis2", 
                    "relevance_score": 0.78
                }
            ],
            "vector_search": [
                {
                    "content": "중국 공산당의 해외 영향력 확장 전략과 정치적 침투",
                    "source": "정치학 논문",
                    "relevance_score": 0.82
                },
                {
                    "content": "동아시아 정치 엘리트들과 중국의 관계 패턴",
                    "source": "국제관계 연구",
                    "relevance_score": 0.75
                }
            ],
            "dialogue_search": [
                {
                    "content": "과거 토론에서 이재명의 중국 관련 발언들",
                    "context": "정치 토론 기록",
                    "relevance_score": 0.80
                }
            ],
            "philosopher_search": [
                {
                    "content": "니체의 권력 의지론과 정치적 예속에 대한 비판",
                    "source": "니체 철학 연구",
                    "philosopher": "nietzsche",
                    "relevance_score": 0.88
                },
                {
                    "content": "니체의 노예 도덕 비판과 현대 정치적 맥락",
                    "source": "철학적 정치 분석",
                    "philosopher": "nietzsche", 
                    "relevance_score": 0.83
                }
            ]
        }

    def mock_rag_search_methods(self, agent):
        """Mock RAG search methods to track calls and return test data"""
        
        def mock_web_search(query: str) -> List[Dict[str, Any]]:
            print(f"\n🌐 [WEB SEARCH] Query: {query}")
            self.rag_search_calls["web_search"].append(query)
            results = self.mock_search_results["web_search"]
            print(f"📊 Results found: {len(results)}")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result['title']}")
                print(f"     Content: {result['content'][:100]}...")
                print(f"     Relevance: {result['relevance_score']}")
            return results
        
        def mock_vector_search(query: str) -> List[Dict[str, Any]]:
            print(f"\n🔍 [VECTOR SEARCH] Query: {query}")
            self.rag_search_calls["vector_search"].append(query)
            results = self.mock_search_results["vector_search"]
            print(f"📊 Results found: {len(results)}")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result['content'][:100]}...")
                print(f"     Source: {result['source']}")
                print(f"     Relevance: {result['relevance_score']}")
            return results
        
        def mock_dialogue_search(query: str) -> List[Dict[str, Any]]:
            print(f"\n💬 [DIALOGUE SEARCH] Query: {query}")
            self.rag_search_calls["dialogue_search"].append(query)
            results = self.mock_search_results["dialogue_search"]
            print(f"📊 Results found: {len(results)}")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result['content'][:100]}...")
                print(f"     Context: {result['context']}")
                print(f"     Relevance: {result['relevance_score']}")
            return results
        
        def mock_philosopher_search(query: str) -> List[Dict[str, Any]]:
            print(f"\n🧠 [PHILOSOPHER SEARCH] Query: {query}")
            self.rag_search_calls["philosopher_search"].append(query)
            results = self.mock_search_results["philosopher_search"]
            print(f"📊 Results found: {len(results)}")
            for i, result in enumerate(results):
                print(f"  {i+1}. {result['content'][:100]}...")
                print(f"     Source: {result['source']}")
                print(f"     Philosopher: {result['philosopher']}")
                print(f"     Relevance: {result['relevance_score']}")
            return results
        
        # Replace the methods
        agent._web_search = mock_web_search
        agent._vector_search = mock_vector_search
        agent._dialogue_search = mock_dialogue_search
        agent._philosopher_search = mock_philosopher_search

    @patch('agents.participant.debate_participant_agent.LLMManager')
    @patch.object(DebateParticipantAgent, '_load_philosopher_data')
    @patch.object(DebateParticipantAgent, '_load_strategy_styles')
    def test_nietzsche_opening_argument_with_rag_tracking(self, mock_load_strategy, mock_load_philosopher, mock_llm):
        """Test Nietzsche generating opening argument with RAG search tracking"""
        
        print("\n" + "="*80)
        print("🎭 니체(Nietzsche) 입론 생성 테스트 - RAG 검색 추적")
        print("="*80)
        print(f"📋 주제: {self.topic}")
        print(f"📍 입장: {self.stance_statement}")
        print(f"🧠 철학자: {self.agent_name}")
        print("="*80)
        
        # Mock setup
        mock_load_philosopher.return_value = self.mock_nietzsche_data
        mock_load_strategy.return_value = {}
        
        # Mock LLM manager to return realistic responses
        mock_llm_instance = MagicMock()
        
        def mock_llm_response(system_prompt="", user_prompt="", **kwargs):
            if "핵심 주장" in user_prompt or "core arguments" in user_prompt.lower():
                return """{
  "core_arguments": [
    {
      "argument": "이재명의 친중 정책은 한국의 독립적 의지를 포기하는 노예적 행태이다",
      "rationale": "니체의 노예 도덕 개념을 통해 보면, 강대국에 굴복하는 것은 약자의 행태이다"
    },
    {
      "argument": "중국 공산당의 경제적 유혹에 굴복하는 것은 '약자의 도덕'의 전형이다",
      "rationale": "진정한 권력의 의지를 가진 지도자라면 외부 압력에 굴복하지 않아야 한다"
    },
    {
      "argument": "진정한 정치 지도자라면 강대국의 압력에 굴복하지 않고 독자적 길을 개척해야 한다",
      "rationale": "위대한 개인은 자신만의 가치를 창조하고 독립적 의지를 실현한다"
    }
  ]
}"""
            elif "search query" in user_prompt.lower() or "generate 1 specific search query" in user_prompt:
                return """{
  "query": "Lee Jae-myung China Communist Party influence Korea politics",
  "source": "web",
  "reasoning": "Web search is most appropriate to find current news and analysis about political relationships"
}"""
            elif "입론" in user_prompt or "opening argument" in user_prompt.lower():
                return """
동료 시민들이여! 나 니체는 오늘 여러분 앞에서 한 가지 충격적 진실을 폭로하고자 한다. 
이재명이라는 자는 중국 공산당의 꼭두각시에 불과하다는 것이다!

첫째, 그의 친중 정책들을 보라. 이는 한국의 독립적 의지를 포기하는 노예적 행태이다. 
내가 『도덕의 계보』에서 경고했듯이, 강자에게 굴복하는 약자의 도덕이 바로 이것이다.

둘째, 중국 공산당의 경제적 유혹에 굴복하는 모습은 진정한 지도자의 자질과는 거리가 멀다. 
권력의 의지를 가진 자라면 외부의 압력에 굴복하지 않고 독자적 길을 개척해야 한다.

셋째, 한국이 진정 위대한 민족이 되려면 중국의 그림자에서 벗어나야 한다. 
이재명의 정책은 우리를 영원한 속국으로 만들려는 음모의 일환이다!

따라서 나는 단언한다. 이재명은 중국 공산당의 꼭두각시이며, 
한국의 미래를 중국에 팔아넘기려는 배신자이다!
"""
            else:
                return "니체의 철학적 관점에서 본 정치적 분석"
        
        mock_llm_instance.generate_response.side_effect = mock_llm_response
        mock_llm.return_value = mock_llm_instance
        
        # Create agent
        agent = DebateParticipantAgent(self.agent_id, self.agent_name, self.nietzsche_config)
        
        # Mock RAG search methods
        self.mock_rag_search_methods(agent)
        
        print("\n🚀 입론 생성 시작...")
        start_time = time.time()
        
        # Generate opening argument with RAG
        try:
            agent.prepare_argument_with_rag(self.topic, self.stance_statement)
            
            end_time = time.time()
            generation_time = end_time - start_time
            
            print(f"\n✅ 입론 생성 완료 (소요시간: {generation_time:.2f}초)")
            
            # Print the generated argument
            if agent.prepared_argument:
                print("\n" + "="*80)
                print("📜 생성된 입론:")
                print("="*80)
                print(agent.prepared_argument)
                print("="*80)
            else:
                print("\n❌ 입론이 생성되지 않았습니다.")
                
            # Print RAG search summary
            self._print_rag_search_summary()
            
            # Assertions
            self.assertTrue(agent.argument_prepared, "입론이 준비되어야 합니다")
            self.assertIsNotNone(agent.prepared_argument, "입론 텍스트가 있어야 합니다")
            self.assertTrue(len(agent.core_arguments) > 0, "핵심 주장들이 생성되어야 합니다")
            
            # Check that RAG searches were called
            total_searches = sum(len(calls) for calls in self.rag_search_calls.values())
            self.assertGreater(total_searches, 0, "RAG 검색이 호출되어야 합니다")
            
            print(f"\n🎯 테스트 성공! 총 {total_searches}개의 RAG 검색이 수행되었습니다.")
            
        except Exception as e:
            print(f"\n❌ 입론 생성 중 오류 발생: {str(e)}")
            raise

    def _print_rag_search_summary(self):
        """Print summary of RAG search calls"""
        print("\n" + "="*80)
        print("🔍 RAG 검색 요약")
        print("="*80)
        
        total_searches = 0
        for search_type, calls in self.rag_search_calls.items():
            if calls:
                print(f"\n📋 {search_type.upper()}:")
                for i, query in enumerate(calls, 1):
                    print(f"  {i}. {query}")
                total_searches += len(calls)
            else:
                print(f"\n📋 {search_type.upper()}: 호출되지 않음")
        
        print(f"\n📊 총 검색 횟수: {total_searches}")
        print("="*80)

    def test_check_rag_methods_exist(self):
        """Test that RAG search methods exist in the agent"""
        
        with patch('agents.participant.debate_participant_agent.LLMManager'), \
             patch.object(DebateParticipantAgent, '_load_philosopher_data') as mock_load_philosopher, \
             patch.object(DebateParticipantAgent, '_load_strategy_styles') as mock_load_strategy:
            
            mock_load_philosopher.return_value = self.mock_nietzsche_data
            mock_load_strategy.return_value = {}
            
            agent = DebateParticipantAgent(self.agent_id, self.agent_name, self.nietzsche_config)
            
            # Check that RAG search methods exist
            self.assertTrue(hasattr(agent, '_web_search'), "웹 검색 메서드가 있어야 합니다")
            self.assertTrue(hasattr(agent, '_vector_search'), "벡터 검색 메서드가 있어야 합니다") 
            self.assertTrue(hasattr(agent, '_dialogue_search'), "대화 검색 메서드가 있어야 합니다")
            self.assertTrue(hasattr(agent, '_philosopher_search'), "철학자 검색 메서드가 있어야 합니다")
            self.assertTrue(hasattr(agent, 'prepare_argument_with_rag'), "RAG 입론 생성 메서드가 있어야 합니다")
            
            print("\n✅ 모든 RAG 검색 메서드가 존재합니다")

    @patch('agents.participant.debate_participant_agent.LLMManager')
    @patch.object(DebateParticipantAgent, '_load_philosopher_data')
    @patch.object(DebateParticipantAgent, '_load_strategy_styles')
    def test_core_arguments_generation(self, mock_load_strategy, mock_load_philosopher, mock_llm):
        """Test core arguments generation step"""
        
        print("\n" + "="*60)
        print("🎯 핵심 주장 생성 단계 테스트")
        print("="*60)
        
        mock_load_philosopher.return_value = self.mock_nietzsche_data
        mock_load_strategy.return_value = {}
        
        # Mock LLM to return core arguments
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.return_value = """{
  "core_arguments": [
    {
      "argument": "이재명의 친중 정책은 국가 주권 포기를 의미한다",
      "rationale": "주권 국가가 외부 세력에 종속되는 것은 국가의 존재 의미를 부정하는 것이다"
    },
    {
      "argument": "경제적 이익을 위해 정치적 독립성을 팔아넘기는 행위이다",
      "rationale": "단기적 경제 이익을 위해 장기적 국가 독립성을 포기하는 것은 근시안적이다"
    },
    {
      "argument": "중국 공산당의 영향력 확장 전략에 부응하는 위험한 정책이다",
      "rationale": "중국의 대외 정책은 주변국을 자신의 영향권에 편입시키는 것을 목표로 한다"
    }
  ]
}"""
        mock_llm.return_value = mock_llm_instance
        
        agent = DebateParticipantAgent(self.agent_id, self.agent_name, self.nietzsche_config)
        
        # Generate core arguments
        agent._generate_core_arguments(self.topic, self.stance_statement)
        
        print(f"📋 생성된 핵심 주장 수: {len(agent.core_arguments)}")
        for i, arg in enumerate(agent.core_arguments, 1):
            print(f"  {i}. {arg}")
        
        self.assertGreater(len(agent.core_arguments), 0, "핵심 주장이 생성되어야 합니다")
        print("\n✅ 핵심 주장 생성 성공")


if __name__ == '__main__':
    # Run specific test with detailed output
    test_case = TestArgumentGenerationWithRAG()
    test_case.setUp()
    
    print("🎭 니체 입론 생성 및 RAG 검색 추적 테스트 실행")
    print("=" * 80)
    
    # Create test suite for the main test
    suite = unittest.TestSuite()
    suite.addTest(TestArgumentGenerationWithRAG('test_nietzsche_opening_argument_with_rag_tracking'))
    suite.addTest(TestArgumentGenerationWithRAG('test_check_rag_methods_exist'))
    suite.addTest(TestArgumentGenerationWithRAG('test_core_arguments_generation'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1) 