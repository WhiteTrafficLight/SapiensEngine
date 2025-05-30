#!/usr/bin/env python3
"""
방어 응답 시스템 테스트
마르크스가 니체를 Clipping 전략 + RAG로 공격할 때 니체의 방어 응답 테스트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.agents.participant.debate_participant_agent import DebateParticipantAgent
from src.models.llm.llm_manager import LLMManager

class MockAttackerAgent:
    """Mock 공격자 에이전트 (마르크스)"""
    
    def __init__(self):
        self.agent_id = "marx"
        self.philosopher_name = "Marx"
        self.attack_strategies = {}
        self.last_used_strategy = None
        
        # 니체에 대한 공격 전략 준비
        self.attack_strategies["nietzsche"] = [{
            "strategy_type": "Clipping",
            "rag_decision": {
                "use_rag": True,
                "rag_score": 0.75,
                "results": [
                    {
                        "title": "Historical Analysis of Individualism",
                        "content": "Research shows that extreme individualism often leads to social fragmentation and inequality, contrary to progressive social development.",
                        "url": "https://example.com/individualism-study"
                    }
                ]
            },
            "vulnerability_score": 0.82,
            "attack_plan": {
                "target_point": "Individual superiority argument",
                "strategy_application": "Direct refutation using class analysis",
                "key_phrase": "Your individual focus ignores collective reality",
                "expected_counter": "Nietzsche may defend individual excellence",
                "follow_up": "Counter with material conditions argument"
            },
            "target_argument": {
                "claim": "Individual excellence and will to power drive human progress",
                "evidence": "Historical examples of great individuals",
                "reasoning": "Strong individuals create values and lead society forward"
            }
        }]

def create_mock_nietzsche():
    """Mock 니체 에이전트 생성"""
    config = {
        "philosopher_key": "nietzsche",
        "role": "con"
    }
    
    nietzsche = DebateParticipantAgent.create_from_philosopher_key(
        agent_id="nietzsche",
        philosopher_key="nietzsche", 
        role="con",
        config=config
    )
    
    # LLM 매니저 설정
    nietzsche.set_llm_manager(LLMManager())
    
    return nietzsche

def create_mock_marx():
    """Mock 마르크스 에이전트 생성"""
    return MockAttackerAgent()

def setup_mock_context(nietzsche, marx):
    """Mock 컨텍스트 설정 - 에이전트 참조 연결"""
    # 니체가 마르크스 에이전트를 참조할 수 있도록 설정
    nietzsche._debate_dialogue_manager = type('MockManager', (), {
        'participants': {
            'marx': marx
        }
    })()

def test_defense_response():
    """방어 응답 테스트 실행"""
    print("🧪 방어 응답 시스템 테스트 시작")
    print("=" * 60)
    
    # 1. 에이전트 생성
    print("1️⃣ 에이전트 생성 중...")
    nietzsche = create_mock_nietzsche()
    marx = create_mock_marx()
    
    # 2. 컨텍스트 설정
    print("2️⃣ Mock 컨텍스트 설정 중...")
    setup_mock_context(nietzsche, marx)
    
    # 3. 토론 설정
    topic = "개인의 우월성 vs 집단의 평등: 인간 발전의 원동력"
    stance_statements = {
        "pro": "개인의 창조적 의지와 우월성이 인류 발전을 이끈다",
        "con": "집단의 협력과 사회적 평등이 진정한 발전을 가능하게 한다"
    }
    
    # 4. 마르크스의 공격 메시지 생성
    recent_messages = [
        {
            "speaker_id": "marx",
            "role": "pro", 
            "text": "니체님, 당신의 개인 우월성 논리는 완전히 잘못되었습니다. 연구에 따르면 극단적 개인주의는 사회 분열과 불평등을 야기할 뿐입니다. 역사적 유물론적 관점에서 보면, 개인의 의지가 아닌 물질적 조건과 계급투쟁이 역사를 발전시켜왔습니다.",
            "timestamp": "2024-01-01T10:00:00"
        }
    ]
    
    dialogue_state = {
        "current_stage": "interactive_argument",
        "participants": {
            "pro": ["marx"],
            "con": ["nietzsche"]
        }
    }
    
    print("3️⃣ 테스트 시나리오:")
    print(f"   📖 주제: {topic}")
    print(f"   🗡️ 공격자: 마르크스 (Clipping 전략 + RAG)")
    print(f"   🛡️ 방어자: 니체")
    print(f"   💬 공격 메시지: {recent_messages[0]['text'][:100]}...")
    print()
    
    # 5. 니체의 방어 응답 생성 테스트
    print("4️⃣ 니체의 방어 응답 생성 중...")
    print("-" * 40)
    
    try:
        defense_response = nietzsche._generate_interactive_argument_response(
            topic=topic,
            recent_messages=recent_messages,
            dialogue_state=dialogue_state,
            stance_statements=stance_statements,
            emotion_enhancement=None
        )
        
        print("-" * 40)
        print("✅ 방어 응답 생성 성공!")
        print()
        print("🗨️ 니체의 방어 응답:")
        print(f'   "{defense_response}"')
        print()
        
        # 6. 응답 분석
        print("5️⃣ 응답 분석:")
        print(f"   📏 응답 길이: {len(defense_response)} 문자")
        print(f"   🎯 마르크스 언급: {'Marx' in defense_response or '마르크스' in defense_response or 'marx' in defense_response.lower()}")
        print(f"   🛡️ 방어적 어조: {'clarify' in defense_response.lower() or '명확' in defense_response or '설명' in defense_response}")
        print(f"   💪 니체다운 표현: {'will' in defense_response.lower() or '의지' in defense_response or '개인' in defense_response}")
        
        return True
        
    except Exception as e:
        print(f"❌ 방어 응답 생성 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_attack_analysis():
    """공격 분석 시스템 단독 테스트"""
    print("\n🔍 공격 분석 시스템 단독 테스트")
    print("=" * 40)
    
    nietzsche = create_mock_nietzsche()
    marx = create_mock_marx()
    setup_mock_context(nietzsche, marx)
    
    recent_messages = [
        {
            "speaker_id": "marx",
            "role": "pro",
            "text": "니체님, 당신의 논리는 잘못되었습니다. 연구 결과에 따르면...",
            "timestamp": "2024-01-01T10:00:00"
        }
    ]
    
    try:
        attack_info = nietzsche._analyze_incoming_attack(recent_messages)
        
        print("📊 공격 분석 결과:")
        print(f"   🗡️ 공격 전략: {attack_info.get('attack_strategy', 'Unknown')}")
        print(f"   📚 RAG 사용: {attack_info.get('rag_used', False)}")
        print(f"   👤 공격자: {attack_info.get('attacker_id', 'Unknown')}")
        print(f"   📍 정보 출처: {attack_info.get('source', 'Unknown')}")
        
        return attack_info
        
    except Exception as e:
        print(f"❌ 공격 분석 실패: {str(e)}")
        return None

def test_defense_strategy_selection():
    """방어 전략 선택 시스템 단독 테스트"""
    print("\n🛡️ 방어 전략 선택 시스템 단독 테스트")
    print("=" * 40)
    
    nietzsche = create_mock_nietzsche()
    
    # Mock 공격 정보
    attack_info = {
        "attack_strategy": "Clipping",
        "rag_used": True,
        "attacker_id": "marx",
        "source": "mock_test"
    }
    
    try:
        defense_strategy = nietzsche._select_defense_strategy(attack_info, None)
        
        print("🎯 방어 전략 선택 결과:")
        print(f"   🛡️ 선택된 전략: {defense_strategy}")
        
        # RAG 사용 여부 테스트
        rag_decision = nietzsche._determine_defense_rag_usage(defense_strategy, attack_info)
        
        print("📚 방어 RAG 결정:")
        print(f"   📖 RAG 사용: {rag_decision.get('use_rag', False)}")
        print(f"   📊 RAG 점수: {rag_decision.get('rag_score', 0.0):.3f}")
        
        return defense_strategy, rag_decision
        
    except Exception as e:
        print(f"❌ 방어 전략 선택 실패: {str(e)}")
        return None, None

if __name__ == "__main__":
    print("🧪 니체 방어 응답 시스템 종합 테스트")
    print("=" * 60)
    
    # 개별 시스템 테스트
    attack_info = test_attack_analysis()
    defense_strategy, rag_decision = test_defense_strategy_selection()
    
    # 통합 테스트
    success = test_defense_response()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 모든 테스트 통과! 방어 시스템이 정상 작동합니다.")
    else:
        print("❌ 테스트 실패! 디버깅이 필요합니다.") 