#!/usr/bin/env python3

import logging
import sys
import time
import os
from pathlib import Path

# Add src to path  
current_dir = Path(__file__).parent.absolute()
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Disable tokenizer parallelism to avoid deadlocks
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from agents.participant.debate_participant_agent import DebateParticipantAgent

def test_single_argument_rag():
    print("🧪 단일 논지 RAG 테스트 (병목 분석)")
    print("=" * 60)
    
    # Configuration
    agent_id = "nietzsche_single_test"
    agent_name = "Friedrich Nietzsche"
    topic = "이재명은 공산당의 꼭두각시인가?"
    stance_statement = "이재명은 위험한 공산주의자이다"
    
    config = {
        "role": "pro",
        "personality": "provocative",
        "knowledge_level": "expert", 
        "style": "philosophical",
        "philosopher_key": "nietzsche",
        "argumentation_style": "emotional",
        "response_focus": "attack"
    }
    
    try:
        # Step 1: Agent initialization
        step_start = time.time()
        print(f"\n🔧 [Step 1] 에이전트 초기화 시작...")
        agent = DebateParticipantAgent(agent_id, agent_name, config)
        step_time = time.time() - step_start
        print(f"✅ 에이전트 초기화 완료: {step_time:.2f}초")
        
        # Step 2: Generate ONE core argument
        step_start = time.time()
        print(f"\n🎯 [Step 2] 핵심 주장 1개 생성 시작...")
        agent._generate_core_arguments(topic, stance_statement)
        step_time = time.time() - step_start
        print(f"✅ 핵심 주장 생성 완료: {step_time:.2f}초")
        print(f"📊 생성된 주장 수: {len(agent.core_arguments)}개")
        
        if agent.core_arguments:
            first_arg = agent.core_arguments[0]
            print(f"📝 첫 번째 주장: {first_arg.get('argument', 'Unknown')[:100]}...")
        
        # Step 3: Generate RAG query for FIRST argument only
        step_start = time.time()
        print(f"\n🔍 [Step 3] 첫 번째 주장용 RAG 쿼리 생성 시작...")
        agent._generate_rag_queries_for_arguments(topic)
        step_time = time.time() - step_start
        print(f"✅ RAG 쿼리 생성 완료: {step_time:.2f}초")
        print(f"📊 생성된 쿼리 수: {len(agent.argument_queries)}개")
        
        if agent.argument_queries:
            first_query_data = agent.argument_queries[0]
            for evidence in first_query_data.get('evidence', []):
                query = evidence.get('query', 'Unknown')
                source = evidence.get('source', 'Unknown')
                print(f"🔍 쿼리: {query}")
                print(f"📡 소스: {source}")
        
        # Step 4: Process ONLY the first query
        if agent.argument_queries:
            step_start = time.time()
            print(f"\n🌐 [Step 4] 첫 번째 쿼리 웹 검색 시작...")
            
            first_query_data = agent.argument_queries[0]
            first_evidence = first_query_data.get('evidence', [{}])[0]
            test_query = first_evidence.get('query', 'Lee Jae-myung political analysis')
            
            print(f"🔍 검색 쿼리: '{test_query}'")
            
            # Test web search directly
            search_results = agent._web_search(test_query)
            step_time = time.time() - step_start
            
            print(f"✅ 웹 검색 완료: {step_time:.2f}초")
            print(f"📊 검색 결과 수: {len(search_results)}개")
            
            if search_results:
                for i, result in enumerate(search_results[:3]):
                    title = result.get('title', 'No title')[:50]
                    relevance = result.get('relevance', 0)
                    content_len = len(result.get('content', ''))
                    print(f"  {i+1}. {title}... (관련도: {relevance:.3f}, 길이: {content_len}자)")
            else:
                print("❌ 검색 결과 없음")
        
        # Step 5: Test argument strengthening (only first argument)
        if search_results:
            step_start = time.time()
            print(f"\n💪 [Step 5] 첫 번째 주장 강화 테스트...")
            
            # Manually set results for first argument
            if agent.argument_queries:
                agent.argument_queries[0]['evidence'][0]['results'] = search_results
            
            # Test strengthening logic
            for query_data in agent.argument_queries[:1]:  # Only first one
                argument = query_data.get("argument", "")
                best_evidence = None
                highest_score = 0
                
                for evidence in query_data.get("evidence", []):
                    for result in evidence.get("results", []):
                        relevance = result.get("relevance", 0)
                        if relevance > highest_score and relevance >= 0.6:
                            highest_score = relevance
                            best_evidence = result
                
                if best_evidence:
                    print(f"✅ 강화 증거 발견: 관련도 {highest_score:.3f}")
                    print(f"📰 제목: {best_evidence.get('title', 'No title')}")
                    print(f"📝 내용: {best_evidence.get('content', '')[:200]}...")
                else:
                    print(f"❌ 신뢰도 0.6 이상 증거 없음 (최고: {highest_score:.3f})")
            
            step_time = time.time() - step_start
            print(f"✅ 주장 강화 분석 완료: {step_time:.2f}초")
        
        print(f"\n🎯 단일 논지 RAG 테스트 완료!")
        print(f"📊 총 처리 시간: 각 단계별 시간 참조")
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {str(e)}")
        import traceback
        print(f"🔍 상세 에러:\n{traceback.format_exc()}")

if __name__ == "__main__":
    test_single_argument_rag() 