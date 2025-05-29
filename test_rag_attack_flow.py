#!/usr/bin/env python3
"""
실제 RAG 공격 파이프라인 테스트
입론 단계에서 생성되어야 하는 데이터들을 mock으로 만들어서 
실제 구현된 함수들의 작동을 확인
"""

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath('.'))

from src.agents.participant.debate_participant_agent import DebateParticipantAgent

def setup_mock_analysis_data(marx_agent, nietzsche_agent):
    """
    입론 단계에서 생성되어야 하는 논지 분석 데이터를 mock으로 설정
    실제 analyze_and_score_arguments 함수가 생성하는 데이터 구조와 동일하게 생성
    """
    print("🔧 Mock 논지 분석 데이터 설정 중...")
    
    # 니체의 가상 발언 (입론에서 나왔을 것으로 가정)
    nietzsche_response = """
    개인의 권력의지야말로 사회 발전의 원동력이다. 역사를 보라! 
    위대한 문명들은 모두 뛰어난 개인들에 의해 건설되었다. 
    그리스의 철학자들, 르네상스의 예술가들, 근대의 과학자들... 
    이들은 모두 평범한 대중을 뛰어넘는 개인들이었다.
    
    따라서 사회는 이러한 뛰어난 개인들의 권력의지를 억압하지 말고 
    오히려 장려해야 한다. 평등주의는 인간의 잠재력을 제한하는 독이다.
    강한 자가 약한 자를 이끄는 것은 자연의 법칙이며, 
    이를 통해 인류는 더 높은 단계로 발전할 수 있다.
    """
    
    # 마르크스가 니체의 발언을 분석 (실제 함수 호출)
    print("📊 마르크스가 니체 발언 분석 중...")
    analysis_result = marx_agent.analyze_and_score_arguments(nietzsche_response, "nietzsche")
    
    if analysis_result.get("status") == "success":
        print(f"✅ 논지 분석 완료: {analysis_result['arguments_count']}개 논지 추출")
        for i, arg in enumerate(analysis_result.get('scored_arguments', []), 1):
            print(f"   {i}. 취약성: {arg['vulnerability_rank']:.3f}")
            print(f"      주장: {arg['argument']['claim'][:80]}...")
    else:
        print(f"❌ 논지 분석 실패: {analysis_result}")
        return False
    
    return True

def test_attack_strategy_preparation(marx_agent):
    """
    실제 prepare_attack_strategies_for_speaker 함수 테스트
    """
    print("\n🗡️ 공격 전략 준비 테스트")
    print("="*50)
    
    # 실제 함수 호출
    strategy_result = marx_agent.process({
        "action": "prepare_attack_strategies",
        "target_speaker_id": "nietzsche"
    })
    
    if strategy_result.get("status") == "success":
        strategies = strategy_result.get("strategies", [])
        rag_usage_count = strategy_result.get("rag_usage_count", 0)
        
        print(f"✅ 공격 전략 준비 완료:")
        print(f"   📊 총 전략 수: {len(strategies)}")
        print(f"   🔍 RAG 사용 전략: {rag_usage_count}개")
        
        for i, strategy in enumerate(strategies, 1):
            print(f"\n   🎯 전략 {i}:")
            print(f"      전략 타입: {strategy['strategy_type']}")
            print(f"      취약성 점수: {strategy['vulnerability_score']:.3f}")
            print(f"      우선순위: {strategy['priority']}")
            
            # RAG 판별 결과 출력
            rag_decision = strategy.get('rag_decision', {})
            print(f"      RAG 사용: {rag_decision.get('use_rag', False)}")
            print(f"      RAG 점수: {rag_decision.get('rag_score', 0):.3f}")
            
            if rag_decision.get('use_rag'):
                print(f"      RAG 쿼리: {rag_decision.get('query', '')}")
                print(f"      RAG 결과 수: {rag_decision.get('results_count', 0)}")
                
                # RAG 결과 미리보기
                results = rag_decision.get('results', [])
                for j, result in enumerate(results[:2], 1):
                    title = result.get('title', 'No title')[:40]
                    print(f"         {j}. {title}...")
            
            # 공격 계획 출력
            attack_plan = strategy.get('attack_plan', {})
            if attack_plan:
                print(f"      공격 포인트: {attack_plan.get('target_point', '')[:60]}...")
                print(f"      핵심 공격구: {attack_plan.get('key_phrase', '')[:60]}...")
        
        return strategies[0] if strategies else None  # 첫 번째 전략 반환
    else:
        print(f"❌ 공격 전략 준비 실패: {strategy_result}")
        return None

def test_interactive_argument_generation(marx_agent, selected_strategy):
    """
    실제 상호논증 메시지 생성 테스트
    """
    print("\n💬 상호논증 메시지 생성 테스트")
    print("="*50)
    
    # 가상의 대화 상태 (실제 debate_dialogue.py에서 전달되는 형태)
    mock_dialogue_state = {
        "current_stage": "interactive_argument",
        "turn_count": 5,
        "speaking_history": [
            {
                "speaker_id": "moderator",
                "text": "이제 상호논증 단계를 시작하겠습니다.",
                "stage": "moderator_summary_1",
                "role": "moderator"
            },
            {
                "speaker_id": "nietzsche", 
                "text": "개인의 권력의지야말로 사회 발전의 원동력이다. 위대한 문명들은 모두 뛰어난 개인들에 의해 건설되었다.",
                "stage": "pro_argument",
                "role": "pro"
            }
        ],
        "next_speaker": "marx",
        "participants": {
            "pro": ["nietzsche"],
            "con": ["marx"]
        }
    }
    
    # 실제 _generate_interactive_argument_response 메서드 직접 호출
    print("🤖 마르크스의 상호논증 응답 생성 중...")
    
    try:
        # 토론 주제와 최근 메시지 설정
        topic = "AI가 인간의 창의성을 대체할 수 있는가?"
        recent_messages = mock_dialogue_state["speaking_history"]
        stance_statements = {
            "pro": "AI는 인간의 창의성을 대체할 수 있다",
            "con": "AI는 인간의 창의성을 대체할 수 없다"
        }
        
        # 실제 메서드 직접 호출
        message = marx_agent._generate_interactive_argument_response(
            topic=topic,
            recent_messages=recent_messages,
            dialogue_state=mock_dialogue_state,
            stance_statements=stance_statements,
            emotion_enhancement=None
        )
        
        if message:
            print("✅ 상호논증 메시지 생성 완료!")
            print("\n" + "="*70)
            print("🎭 마르크스의 최종 공격 메시지:")
            print("="*70)
            print(message)
            print("="*70)
            
            # 메시지 분석
            print(f"\n📊 메시지 분석:")
            print(f"   - 길이: {len(message)}자")
            print(f"   - 단어 수: {len(message.split())}개")
            
            if selected_strategy:
                strategy_type = selected_strategy.get('strategy_type', 'Unknown')
                rag_used = selected_strategy.get('rag_decision', {}).get('use_rag', False)
                print(f"   - 사용된 전략: {strategy_type}")
                print(f"   - RAG 활용: {'예' if rag_used else '아니오'}")
                
                if rag_used:
                    rag_query = selected_strategy.get('rag_decision', {}).get('query', '')
                    rag_count = selected_strategy.get('rag_decision', {}).get('results_count', 0)
                    print(f"   - RAG 쿼리: {rag_query}")
                    print(f"   - 참조 자료: {rag_count}개")
            
            return message
        else:
            print("❌ 메시지가 비어있습니다")
            return None
            
    except Exception as e:
        print(f"❌ 상호논증 메시지 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_full_pipeline():
    """
    전체 RAG 공격 파이프라인 테스트
    """
    print("🧪 실제 RAG 공격 파이프라인 테스트")
    print("🎭 시나리오: 마르크스가 니체의 개인주의를 집단주의로 공격")
    print("="*70)
    
    # 1. 에이전트 생성
    print("\n1️⃣ 에이전트 생성")
    try:
        marx_agent = DebateParticipantAgent.create_from_philosopher_key(
            agent_id="marx_test",
            philosopher_key="marx",
            role="con",
            config={}
        )
        
        nietzsche_agent = DebateParticipantAgent.create_from_philosopher_key(
            agent_id="nietzsche_test", 
            philosopher_key="nietzsche",
            role="pro",
            config={}
        )
        
        print(f"✅ 마르크스 에이전트: {marx_agent.philosopher_name}")
        print(f"   📊 RAG 스탯: {getattr(marx_agent, 'philosopher_data', {}).get('rag_stats', {})}")
        print(f"✅ 니체 에이전트: {nietzsche_agent.philosopher_name}")
        
    except Exception as e:
        print(f"❌ 에이전트 생성 실패: {e}")
        return
    
    # 2. Mock 논지 분석 데이터 설정 (실제 함수 사용)
    print("\n2️⃣ 논지 분석 단계")
    if not setup_mock_analysis_data(marx_agent, nietzsche_agent):
        print("❌ Mock 데이터 설정 실패")
        return
    
    # 3. 공격 전략 준비 (실제 함수 사용)
    print("\n3️⃣ 공격 전략 준비 단계")
    selected_strategy = test_attack_strategy_preparation(marx_agent)
    
    if not selected_strategy:
        print("❌ 공격 전략 준비 실패")
        return
    
    # 4. 상호논증 메시지 생성 (실제 함수 사용)
    print("\n4️⃣ 상호논증 메시지 생성 단계")
    final_message = test_interactive_argument_generation(marx_agent, selected_strategy)
    
    if final_message:
        print("\n🎉 전체 파이프라인 테스트 성공!")
        print(f"📈 최종 결과: {len(final_message)}자의 공격 메시지 생성")
    else:
        print("❌ 상호논증 메시지 생성 실패")

def test_individual_components():
    """
    개별 컴포넌트 테스트
    """
    print("\n" + "="*70)
    print("🔧 개별 컴포넌트 테스트")
    print("="*70)
    
    try:
        marx_agent = DebateParticipantAgent.create_from_philosopher_key(
            agent_id="marx_component_test",
            philosopher_key="marx",
            role="con",
            config={}
        )
        
        # 1. RAG 판별 테스트
        print("\n1️⃣ RAG 판별 컴포넌트 테스트")
        test_strategies = ["Clipping", "Conceptual Undermining", "Ethical Reversal", "Framing Shift"]
        
        for strategy in test_strategies:
            rag_decision = marx_agent._determine_rag_usage_for_strategy(strategy)
            use_rag = "사용" if rag_decision.get('use_rag') else "미사용"
            score = rag_decision.get('rag_score', 0)
            print(f"   🗡️ {strategy}: RAG {score:.3f} → {use_rag}")
        
        # 2. 공격 쿼리 생성 테스트
        print("\n2️⃣ 공격 쿼리 생성 컴포넌트 테스트")
        mock_argument = {
            "claim": "개인의 권력의지가 사회 발전의 원동력이다",
            "evidence": "역사상 위대한 문명들은 강력한 지도자들에 의해 건설되었다",
            "reasoning": "따라서 뛰어난 개인들을 장려해야 한다"
        }
        
        for strategy in test_strategies[:2]:  # 2개만 테스트
            query = marx_agent._generate_attack_rag_query_for_strategy(mock_argument, strategy)
            print(f"   🗡️ {strategy}:")
            print(f"      🔍 쿼리: {query}")
        
        # 3. RAG 검색 테스트
        print("\n3️⃣ RAG 검색 컴포넌트 테스트")
        test_query = "evidence against individual superiority theory"
        search_results = marx_agent._perform_attack_rag_search(test_query, "Ethical Reversal")
        print(f"   📝 검색 결과: {len(search_results)}개")
        for i, result in enumerate(search_results, 1):
            title = result.get('title', 'No title')[:50]
            print(f"      {i}. {title}...")
        
        # 4. RAG 포맷팅 테스트
        if search_results:
            print("\n4️⃣ RAG 포맷팅 컴포넌트 테스트")
            formatted = marx_agent._format_attack_rag_results(search_results, "Ethical Reversal")
            print(f"   📝 포맷팅된 결과 ({len(formatted)}자):")
            print(f"      {formatted[:200]}...")
        
    except Exception as e:
        print(f"❌ 컴포넌트 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 테스트 실행"""
    print("🧪 실제 RAG 공격 파이프라인 종합 테스트")
    print("📋 테스트 내용:")
    print("   - 실제 analyze_and_score_arguments 함수")
    print("   - 실제 prepare_attack_strategies_for_speaker 함수") 
    print("   - 실제 _generate_interactive_argument_response 함수")
    print("   - 실제 RAG 판별, 쿼리 생성, 검색, 포맷팅 함수들")
    print()
    
    # 전체 파이프라인 테스트
    test_full_pipeline()
    
    # 개별 컴포넌트 테스트
    test_individual_components()
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    main() 