import unittest
import sys
import time
import os
import logging
from pathlib import Path
from typing import Dict, Any, List
import re

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Add the src directory to the path for imports
current_dir = Path(__file__).parent.absolute()
src_path = current_dir.parent.parent / "src"
sys.path.insert(0, str(src_path))

# Add the project root to path as well for src imports to work
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from agents.participant.debate_participant_agent import DebateParticipantAgent


class TestRealRAGArgumentGeneration(unittest.TestCase):
    """Test real RAG argument generation with actual external searches and LLM calls"""
    
    def setUp(self):
        """Set up test environment with real configurations"""
        self.agent_id = "nietzsche_real_test"
        self.agent_name = "Friedrich Nietzsche"
        self.topic = "이재명은 공산당의 꼭두각시인가?"
        self.stance_statement = "이재명은 위험한 공산주의자이다"
        
        # Real Nietzsche configuration
        self.nietzsche_config = {
            "role": "pro",  # 찬성 입장
            "personality": "provocative",
            "knowledge_level": "expert", 
            "style": "philosophical",
            "philosopher_key": "nietzsche",
            "argumentation_style": "emotional",
            "response_focus": "attack"
        }
        
        # Track the entire process
        self.process_log = []
        
    def log_step(self, step_name: str, data: Any = None):
        """Log each step of the process"""
        timestamp = time.strftime("%H:%M:%S")
        self.process_log.append({
            "timestamp": timestamp,
            "step": step_name,
            "data": data
        })
        print(f"\n[{timestamp}] 🔄 {step_name}")
        if data:
            print(f"    📊 Data: {str(data)[:200]}{'...' if len(str(data)) > 200 else ''}")

    def _analyze_rag_usage_in_argument(self, final_argument: str, search_results: List[Dict], agent) -> Dict[str, Any]:
        """Analyze how RAG search results are used in the final argument"""
        usage_analysis = {
            "total_search_results": len(search_results),
            "used_results": 0,
            "unused_results": 0,
            "content_matches": [],
            "keyword_matches": [],
            "url_references": [],
            "source_integration": {},
            "prompt_evidence": None,
            "evidence_threshold_met": False
        }
        
        # 실제 agent 로직에 따른 활용 여부 확인
        best_evidence = None
        highest_relevance = 0
        
        # agent와 동일한 로직으로 best_evidence 찾기
        for query_data in agent.argument_queries:
            argument = query_data.get("argument", "")
            for evidence in query_data.get("evidence", []):
                for result in evidence.get("results", []):
                    relevance = result.get("relevance", 0)
                    content = result.get("content", "")
                    
                    if relevance > highest_relevance and relevance > 0.5:
                        highest_relevance = relevance
                        best_evidence = {
                            "argument": argument,
                            "source": result.get("title", "Research"),
                            "url": result.get("url", ""),
                            "relevance": relevance,
                            "raw_content": content[:150]
                        }
        
        # 실제 프롬프트 포함 여부 확인 (agent 로직: highest_relevance > 0.5)
        if best_evidence and highest_relevance > 0.5:
            usage_analysis["used_results"] = 1
            usage_analysis["unused_results"] = len(search_results) - 1
            usage_analysis["evidence_threshold_met"] = True
            usage_analysis["prompt_evidence"] = {
                "source": best_evidence["source"],
                "relevance": highest_relevance,
                "url": best_evidence["url"],
                "content": best_evidence["raw_content"]
            }
            
            # 실제 입론에서 해당 소스 언급 여부 확인
            source_title_words = best_evidence["source"].split()[:3]  # 소스 제목의 처음 3단어
            for word in source_title_words:
                if len(word) > 3 and word.lower() in final_argument.lower():
                    usage_analysis["content_matches"].append({
                        "source": best_evidence["source"],
                        "content": f"Source reference: {word}",
                        "url": best_evidence["url"]
                    })
                    break
        else:
            usage_analysis["used_results"] = 0
            usage_analysis["unused_results"] = len(search_results)
            usage_analysis["evidence_threshold_met"] = False
        
        # Extract keywords from search results for additional analysis
        all_keywords = set()
        for result_data in search_results:
            result = result_data.get('result', {})
            title = result.get('title', '')
            content = result.get('content', '')
            
            # Extract meaningful keywords (Korean and English) - 더 엄격한 기준
            title_keywords = [w for w in re.findall(r'[\w가-힣]{4,}', title) 
                            if w.lower() not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will', 'said', 'says']]
            content_keywords = [w for w in re.findall(r'[\w가-힣]{4,}', content) 
                              if w.lower() not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will', 'said', 'says']]
            all_keywords.update(title_keywords[:5])  # 제목에서 처음 5개만
            all_keywords.update(content_keywords[:10])  # 내용에서 처음 10개만
        
        # Check for keyword usage in final argument
        for keyword in all_keywords:
            if len(keyword) > 3 and keyword.lower() in final_argument.lower():
                usage_analysis["keyword_matches"].append(keyword)
        
        # Check for URL or source references
        for result_data in search_results:
            result = result_data.get('result', {})
            url = result.get('url', '')
            if url and url in final_argument:
                usage_analysis["url_references"].append(url)
        
        return usage_analysis

    def test_complete_real_rag_argument_generation(self):
        """Test complete RAG argument generation process with real external calls"""
        
        print("\n" + "="*100)
        print("🎭 니체(Nietzsche) 실제 RAG 검색 입론 생성 테스트")
        print("="*100)
        print(f"📋 주제: {self.topic}")
        print(f"📍 입장: {self.stance_statement}")
        print(f"🧠 철학자: {self.agent_name}")
        print(f"⚙️  실제 LLM 및 외부 검색 사용")
        print("="*100)
        
        # Step 1: Create agent with real configuration
        self.log_step("에이전트 초기화")
        start_time = time.time()
        
        try:
            agent = DebateParticipantAgent(self.agent_id, self.agent_name, self.nietzsche_config)
            
            # Verify agent is properly initialized
            self.assertEqual(agent.philosopher_key, "nietzsche")
            self.assertEqual(agent.role, "pro")
            
            self.log_step("에이전트 초기화 완료", {
                "agent_id": agent.agent_id,
                "philosopher": agent.philosopher_name,
                "role": agent.role
            })
            
            # Step 2: Generate core arguments (real LLM call)
            self.log_step("핵심 주장 생성 시작")
            core_args_start = time.time()
            
            agent._generate_core_arguments(self.topic, self.stance_statement)
            
            core_args_end = time.time()
            self.log_step("핵심 주장 생성 완료", {
                "count": len(agent.core_arguments),
                "duration": f"{core_args_end - core_args_start:.2f}초"
            })
            
            # Print generated core arguments
            print(f"\n📋 생성된 핵심 주장 ({len(agent.core_arguments)}개):")
            for i, arg in enumerate(agent.core_arguments, 1):
                print(f"  {i}. {arg.get('argument', '알 수 없음')}")
                print(f"     근거: {arg.get('rationale', '없음')}")
            
            # Verify core arguments were generated
            self.assertGreater(len(agent.core_arguments), 0, "핵심 주장이 생성되어야 합니다")
            
            # Step 3: Generate RAG queries for each argument (real LLM call)
            self.log_step("RAG 쿼리 생성 시작")
            queries_start = time.time()
            
            agent._generate_rag_queries_for_arguments(self.topic)
            
            queries_end = time.time()
            self.log_step("RAG 쿼리 생성 완료", {
                "query_count": len(agent.argument_queries),
                "duration": f"{queries_end - queries_start:.2f}초"
            })
            
            # Print generated queries
            print(f"\n🔍 생성된 RAG 쿼리 ({len(agent.argument_queries)}개):")
            for i, query_data in enumerate(agent.argument_queries, 1):
                arg = query_data.get('argument', '알 수 없음')
                for evidence in query_data.get('evidence', []):
                    query = evidence.get('query', '알 수 없음')
                    source = evidence.get('source', '알 수 없음')
                    print(f"  {i}. 주장: {arg[:50]}...")
                    print(f"     쿼리: {query}")
                    print(f"     소스: {source}")
            
            # Step 4: Perform real RAG searches
            self.log_step("실제 RAG 검색 시작")
            rag_start = time.time()
            
            total_searches = 0
            search_results_summary = {
                "web": 0,
                "vector": 0, 
                "dialogue": 0,
                "philosopher": 0
            }
            
            agent._strengthen_arguments_with_rag()
            
            rag_end = time.time()
            
            # Count actual search results and collect for analysis
            all_search_results = []
            for query_data in agent.argument_queries:
                for evidence in query_data.get('evidence', []):
                    results = evidence.get('results', [])
                    total_searches += len(results)
                    source = evidence.get('source', 'unknown')
                    if source in search_results_summary:
                        search_results_summary[source] += len(results)
                    
                    # Store all results for later analysis
                    for result in results:
                        all_search_results.append({
                            'argument': query_data.get('argument', '')[:100],
                            'query': evidence.get('query', ''),
                            'source': source,
                            'result': result
                        })
            
            self.log_step("실제 RAG 검색 완료", {
                "total_results": total_searches,
                "duration": f"{rag_end - rag_start:.2f}초",
                "breakdown": search_results_summary
            })
            
            # Print search results summary
            print(f"\n🔍 RAG 검색 결과 요약:")
            print(f"  📊 총 검색 결과: {total_searches}개")
            for source, count in search_results_summary.items():
                if count > 0:
                    print(f"  🔗 {source.upper()}: {count}개 결과")
            
            # Print ALL search results with clickable URLs
            print(f"\n📚 전체 검색 결과 상세 ({total_searches}개):")
            print("=" * 80)
            
            for i, query_data in enumerate(agent.argument_queries, 1):
                argument = query_data.get('argument', '알 수 없음')
                print(f"\n🎯 주장 {i}: {argument}")
                
                for j, evidence in enumerate(query_data.get('evidence', []), 1):
                    query = evidence.get('query', '알 수 없음')
                    source = evidence.get('source', '알 수 없음')
                    results = evidence.get('results', [])
                    
                    print(f"  🔍 검색 쿼리: {query}")
                    print(f"  📊 소스: {source}")
                    print(f"  📈 결과 수: {len(results)}개")
                    
                    for k, result in enumerate(results, 1):
                        title = result.get('title', '제목 없음')
                        content = result.get('content', '내용 없음')
                        url = result.get('url', '')
                        relevance = result.get('relevance', 0.0)
                        
                        print(f"    {k}. 📰 {title[:80]}...")
                        print(f"       📝 {content[:150]}...")
                        print(f"       📊 관련도: {relevance}")
                        if url:
                            print(f"       🌐 클릭 가능한 링크: {url}")
                        print()
            
            print("=" * 80)
            
            # Step 5: Generate final opening argument (real LLM call)
            self.log_step("최종 입론 생성 시작")
            final_start = time.time()
            
            agent._generate_final_opening_argument(self.topic, self.stance_statement)
            
            final_end = time.time()
            self.log_step("최종 입론 생성 완료", {
                "argument_length": len(agent.prepared_argument) if agent.prepared_argument else 0,
                "duration": f"{final_end - final_start:.2f}초"
            })
            
            # Step 6: Mark argument as prepared
            agent.argument_prepared = True
            
            total_time = time.time() - start_time
            
            # Print final results
            print(f"\n" + "="*100)
            print("📜 최종 생성된 입론:")
            print("="*100)
            if agent.prepared_argument:
                print(agent.prepared_argument)
            else:
                print("❌ 입론이 생성되지 않았습니다.")
            print("="*100)
            
            # Step 7: Analyze RAG usage in final argument
            if agent.prepared_argument and all_search_results:
                print(f"\n🔍 RAG 데이터 활용도 분석:")
                print("=" * 80)
                
                rag_analysis = self._analyze_rag_usage_in_argument(agent.prepared_argument, all_search_results, agent)
                
                print(f"📊 총 검색 결과: {rag_analysis['total_search_results']}개")
                print(f"✅ 사용된 결과: {rag_analysis['used_results']}개")
                print(f"❌ 미사용 결과: {rag_analysis['unused_results']}개")
                print(f"🔑 매칭된 키워드: {len(rag_analysis['keyword_matches'])}개")
                print(f"📝 콘텐츠 매칭: {len(rag_analysis['content_matches'])}개")
                print(f"🔗 URL 참조: {len(rag_analysis['url_references'])}개")
                
                # 프롬프트 포함 상세 정보
                print(f"🎯 증거 임계값 달성: {'✅' if rag_analysis['evidence_threshold_met'] else '❌'}")
                if rag_analysis['prompt_evidence']:
                    print(f"\n📋 프롬프트에 포함된 증거:")
                    print(f"  📰 소스: {rag_analysis['prompt_evidence']['source']}")
                    print(f"  📊 유사도: {rag_analysis['prompt_evidence']['relevance']}")
                    print(f"  📝 내용: {rag_analysis['prompt_evidence']['content']}")
                    if rag_analysis['prompt_evidence']['url']:
                        print(f"  🔗 URL: {rag_analysis['prompt_evidence']['url']}")
                else:
                    print(f"\n❌ 프롬프트에 포함된 증거 없음 (유사도 < 0.5 또는 증거 부족)")
                
                if rag_analysis['keyword_matches']:
                    print(f"\n🔑 활용된 키워드:")
                    for keyword in rag_analysis['keyword_matches'][:10]:  # Show first 10
                        print(f"  - {keyword}")
                
                if rag_analysis['content_matches']:
                    print(f"\n📝 직접 활용된 콘텐츠:")
                    for match in rag_analysis['content_matches'][:3]:  # Show first 3
                        print(f"  📰 출처: {match['source']}")
                        print(f"  📝 내용: {match['content'][:100]}...")
                        if match['url']:
                            print(f"  🔗 링크: {match['url']}")
                        print()
                
                if rag_analysis['url_references']:
                    print(f"\n🔗 참조된 URL:")
                    for url in rag_analysis['url_references']:
                        print(f"  - {url}")
                
                print("=" * 80)
            
            # Print process summary
            print(f"\n📊 전체 프로세스 요약:")
            print(f"  ⏱️  총 소요시간: {total_time:.2f}초")
            print(f"  🎯 핵심 주장 수: {len(agent.core_arguments)}개")
            print(f"  🔍 검색 쿼리 수: {len(agent.argument_queries)}개")
            print(f"  📊 총 검색 결과: {total_searches}개")
            print(f"  📜 최종 입론 길이: {len(agent.prepared_argument) if agent.prepared_argument else 0}자")
            
            # Print detailed process log
            print(f"\n📝 세부 프로세스 로그:")
            for i, log_entry in enumerate(self.process_log, 1):
                print(f"  {i:2d}. [{log_entry['timestamp']}] {log_entry['step']}")
            
            # Assertions
            self.assertTrue(agent.argument_prepared, "입론이 준비되어야 합니다")
            self.assertIsNotNone(agent.prepared_argument, "입론 텍스트가 있어야 합니다")
            self.assertGreater(len(agent.prepared_argument), 50, "입론이 충분히 길어야 합니다")
            self.assertTrue(len(agent.core_arguments) > 0, "핵심 주장들이 생성되어야 합니다")
            self.assertTrue(len(agent.argument_queries) > 0, "RAG 쿼리들이 생성되어야 합니다")
            
            print(f"\n🎯 테스트 성공! 니체의 실제 RAG 기반 입론이 생성되었습니다.")
            
        except Exception as e:
            print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
            print(f"   오류 타입: {type(e).__name__}")
            import traceback
            print(f"   스택 트레이스:\n{traceback.format_exc()}")
            raise

    def test_agent_initialization_with_real_data(self):
        """Test agent initialization with real philosopher data"""
        
        print("\n" + "="*60)
        print("⚙️  에이전트 초기화 테스트")
        print("="*60)
        
        agent = DebateParticipantAgent(self.agent_id, self.agent_name, self.nietzsche_config)
        
        # Print loaded philosopher data
        print(f"🧠 철학자 정보:")
        print(f"  이름: {agent.philosopher_name}")
        print(f"  핵심 사상: {agent.philosopher_essence}")
        print(f"  토론 스타일: {agent.philosopher_debate_style}")
        print(f"  성격: {agent.philosopher_personality}")
        print(f"  주요 특성: {', '.join(agent.philosopher_key_traits) if agent.philosopher_key_traits else '없음'}")
        print(f"  명언: {agent.philosopher_quote}")
        
        # Test core functionality
        self.assertEqual(agent.philosopher_key, "nietzsche")
        self.assertEqual(agent.role, "pro")
        self.assertIsNotNone(agent.llm_manager)
        
        print(f"\n✅ 에이전트 초기화 성공")


if __name__ == '__main__':
    # Set up test environment
    print("🚀 실제 RAG 검색 시스템 테스트 시작")
    print("⚠️  주의: 이 테스트는 실제 LLM API 호출과 웹 검색을 수행합니다")
    print("💰 비용이 발생할 수 있으니 주의하세요!")
    
    # Ask for confirmation
    try:
        confirm = input("\n계속하시겠습니까? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("테스트가 취소되었습니다.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n테스트가 취소되었습니다.")
        sys.exit(0)
    
    print("\n" + "="*100)
    
    # Create test suite for the specific tests we want to run
    suite = unittest.TestSuite()
    
    # Add tests in order
    suite.addTest(TestRealRAGArgumentGeneration('test_agent_initialization_with_real_data'))
    suite.addTest(TestRealRAGArgumentGeneration('test_complete_real_rag_argument_generation'))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    # Final summary
    print(f"\n" + "="*100)
    print("📊 최종 테스트 결과:")
    print(f"  ✅ 성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  ❌ 실패: {len(result.failures)}")
    print(f"  🚫 오류: {len(result.errors)}")
    print("="*100)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1) 