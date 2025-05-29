#!/usr/bin/env python3
"""
1대1 토론 테스트 (니체 vs 카뮈)

찬성측: 니체(AI)
반대측: 카뮈(AI)

빠른 테스트를 위한 1대1 구조
"""

import sys
import os
import asyncio
import time
from pathlib import Path
import yaml
import json

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.dialogue.types.debate_dialogue import DebateDialogue

def create_one_on_one_debate_data():
    """1대1 토론방 데이터 생성"""
    
    return {
        "title": "AI가 인간의 창의성을 대체할 수 있는가?",
        "context": """
인공지능과 창의성에 대한 철학적 토론입니다.

## 주요 논점:
- AI의 창의성 정의와 범위
- 인간 창의성의 고유성
- 기술과 예술의 관계
- 미래 창작 활동의 변화

## 찬성 논리 (니체):
- AI는 이미 음악, 미술, 문학 분야에서 창작 활동
- 패턴 인식과 조합을 통한 새로운 창작 가능
- 인간의 한계를 뛰어넘는 무한한 가능성
- 창의성은 결과물로 판단되어야 함
- 권력의지를 통한 새로운 창조 형태

## 반대 논리 (카뮈):
- 창의성에는 감정과 경험이 필수
- AI는 기존 데이터의 재조합일 뿐
- 진정한 창조는 의식과 의도에서 나옴
- 인간만이 가진 직관과 영감의 중요성
- 부조리한 존재로서의 인간만이 진정한 창조 가능

이 토론에서는 2명의 철학자가 AI의 창의성에 대해 깊이 있게 논의합니다.
        """,
        "participants": {
            # 1대1 구조 - 철학자 키만 지정
            "pro": [
                {
                    "character_id": "nietzsche",
                    "philosopher_key": "nietzsche",  # YAML에서 로드할 키
                    "name": "Nietzsche",  # 기본 이름 (YAML에서 덮어씀)
                    "personality": "passionate",
                    "style": "provocative"
                }
            ],
            "con": [
                {
                    "character_id": "camus",
                    "philosopher_key": "camus",  # YAML에서 로드할 키
                    "name": "Camus",  # 기본 이름 (YAML에서 덮어씀)
                    "personality": "existential",
                    "style": "absurdist"
                }
            ],
            "users": [],  # 사용자 없음
            "user_configs": {}
        },
        "moderator": {
            "agent_id": "debate_moderator",
            "name": "토론 진행자",
            "style_id": "0"  # moderator_style.json의 "0" (Casual Young Moderator)
        }
    }

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def print_message(speaker, message, is_user=False, is_waiting=False):
    """메시지 출력 (1대1용)"""
    if is_waiting:
        print(f"\n🔄 [{speaker}] 입력을 기다리는 중...")
    elif speaker in ["nietzsche", "Nietzsche", "니체"]:
        print(f"\n⚡ [{speaker}]: {message}")
    elif speaker in ["camus", "Camus", "카뮈"]:
        print(f"\n🌊 [{speaker}]: {message}")
    else:
        print(f"\n🤖 [{speaker}]: {message}")

def print_dialogue_state(dialogue):
    """대화 상태 출력 (1대1용)"""
    state = dialogue.get_dialogue_state()
    participants = dialogue.participants
    
    print(f"\n📊 대화 상태:")
    print(f"   - 현재 단계: {state['current_stage']}")
    print(f"   - 턴 수: {state['turn_count']}")
    print(f"   - 다음 발언자: {state.get('next_speaker', 'Unknown')}")
    print(f"   - 진행 상태: {state['status']}")
    print(f"   - 찬성측 참가자: {len(participants.get('pro', []))}명")
    print(f"   - 반대측 참가자: {len(participants.get('con', []))}명")

def print_participants_info():
    """참가자 정보 출력"""
    print("👥 토론 참가자:")
    print("   📍 찬성측 (PRO):")
    print("      ⚡ 니체 - 권력의지와 창조적 파괴의 철학자")
    print("   📍 반대측 (CON):")
    print("      🌊 카뮈 - 부조리와 반항의 철학자")
    print()
    print("🎯 토론 주제:")
    print("   - AI가 인간의 창의성을 대체할 수 있는가?")
    print("   - 니체: 권력의지를 통한 창조적 혁신 지지")
    print("   - 카뮈: 부조리한 인간 존재의 고유한 창조성 강조")

def print_performance_analysis(dialogue):
    """모든 에이전트의 성능 분석 결과 출력"""
    print("\n" + "="*80)
    print("🔍 성능 분석 결과")
    print("="*80)
    
    total_time = 0
    agent_summaries = []
    
    # 모든 에이전트의 성능 요약 수집
    for agent_id, agent in dialogue.agents.items():
        if hasattr(agent, 'get_performance_summary'):
            summary = agent.get_performance_summary()
            agent_summaries.append(summary)
            total_time += summary.get('total_time', 0)
    
    # 에이전트별 성능 출력
    for summary in agent_summaries:
        agent_name = summary.get('philosopher_name', summary.get('agent_name', summary.get('agent_id', 'Unknown')))
        print(f"\n📊 {agent_name}")
        print(f"   총 액션 수: {summary.get('total_actions', 0)}")
        print(f"   총 소요 시간: {summary.get('total_time', 0):.2f}초")
        
        actions = summary.get('actions', {})
        for action_name, timing in actions.items():
            print(f"   - {action_name}: {timing['duration']:.2f}초 ({timing['start_time']} ~ {timing['end_time']})")
    
    # 전체 요약
    print(f"\n📈 전체 요약")
    print(f"   총 에이전트 수: {len(agent_summaries)}")
    print(f"   전체 소요 시간: {total_time:.2f}초")
    print(f"   평균 에이전트당 시간: {total_time/len(agent_summaries):.2f}초" if agent_summaries else "   평균 계산 불가")
    
    # 가장 오래 걸린 액션들
    all_actions = []
    for summary in agent_summaries:
        agent_name = summary.get('philosopher_name', summary.get('agent_name', summary.get('agent_id', 'Unknown')))
        actions = summary.get('actions', {})
        for action_name, timing in actions.items():
            all_actions.append({
                'agent': agent_name,
                'action': action_name,
                'duration': timing['duration']
            })
    
    # 시간순 정렬
    all_actions.sort(key=lambda x: x['duration'], reverse=True)
    
    print(f"\n⏱️  가장 오래 걸린 액션들 (Top 5)")
    for i, action in enumerate(all_actions[:5]):
        print(f"   {i+1}. {action['agent']} - {action['action']}: {action['duration']:.2f}초")
    
    print("="*80)

def test_one_on_one_debate():
    """1대1 토론 테스트"""
    print_header("1대1 토론 테스트 (니체 vs 카뮈)")
    
    # 1. 토론방 데이터 생성
    room_data = create_one_on_one_debate_data()
    print(f"📝 토론 주제: {room_data['title']}")
    print_participants_info()
    
    # 2. 토론 대화 초기화
    try:
        dialogue = DebateDialogue("test_one_on_one", room_data)
        print(f"✅ 1대1 토론 대화 초기화 완료")
        
        # 참가자 확인
        participants = dialogue.participants
        print(f"✅ 참가자 확인:")
        print(f"   - 찬성측: {participants.get('pro', [])}")
        print(f"   - 반대측: {participants.get('con', [])}")
        
    except Exception as e:
        print(f"❌ 토론 초기화 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 초기 상태 확인
    print_dialogue_state(dialogue)
    
    # 4. 토론 진행 시뮬레이션
    max_turns = 15  # 1대1이므로 적은 턴
    turn_count = 0
    
    print_header("1대1 토론 진행 시작")
    
    # 토론 안내 메시지
    print("🎯 1대1 토론 안내:")
    print("   - 니체 vs 카뮈의 철학적 대결")
    print("   - 찬성측: 니체 (AI의 창조적 가능성 지지)")
    print("   - 반대측: 카뮈 (인간 고유의 창조성 강조)")
    print()
    print("💡 토론 진행 순서:")
    print("   1. 모더레이터 오프닝")
    print("   2. 찬성측 입론 (니체)")
    print("   3. 반대측 입론 (카뮈)")
    print("   4. 상호논증 (자유 발언)")
    print("   5. 최종 결론 (각자 순서대로)")
    print()
    
    input("📍 준비가 되면 Enter를 눌러 1대1 토론을 시작하세요...")
    print()
    
    while turn_count < max_turns and dialogue.playing:
        turn_count += 1
        print(f"\n🔄 턴 {turn_count}")
        
        try:
            # 현재 발언자 확인
            next_speaker_info = dialogue.get_next_speaker()
            next_speaker = next_speaker_info.get("speaker_id")
            speaker_role = next_speaker_info.get("role")
            current_stage = dialogue.state.get("current_stage")
            
            print(f"📢 다음 발언자: {next_speaker} ({speaker_role})")
            print(f"📍 현재 단계: {current_stage}")
            
            # AI 에이전트 차례
            print(f"🤖 AI 에이전트 차례: {next_speaker}")
            
            # AI 응답 생성
            result = dialogue.generate_response()
            
            if result.get("status") == "success":
                speaker_name = result.get("speaker_id", next_speaker)
                message = result.get("message", "")
                
                print_message(speaker_name, message)
                
                # 발언자별 특별 표시
                if speaker_name in ["nietzsche", "Nietzsche"]:
                    print("   💭 니체의 권력의지 철학이 드러나는 발언")
                elif speaker_name in ["camus", "Camus"]:
                    print("   💭 카뮈의 부조리 철학이 드러나는 발언")
                    
            elif result.get("status") == "paused":
                print(f"⏸️ 토론이 일시정지되었습니다.")
                break
            else:
                print(f"⚠️ AI 응답 생성 실패: {result.get('reason', 'Unknown error')}")
            
            # 상태 업데이트 확인
            print_dialogue_state(dialogue)
            
            # 토론 완료 확인
            if dialogue.state.get("current_stage") == "completed":
                print("🎉 토론이 완료되었습니다!")
                break
            
            # 잠시 대기 (실제 대화 속도 시뮬레이션)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ 턴 {turn_count} 처리 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            break
    
    # 5. 토론 종료 및 결과
    print_header("1대1 토론 종료")
    
    # 전체 대화 기록 분석
    speaking_history = dialogue.state.get("speaking_history", [])
    speaker_counts = {}
    for msg in speaking_history:
        speaker = msg.get("speaker_id", "Unknown")
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print(f"\n📈 참가자별 발언 통계:")
    for speaker, count in speaker_counts.items():
        print(f"   🤖 {speaker}: {count}회 발언")
    
    print(f"\n📜 전체 대화 기록 ({len(speaking_history)}개 메시지):")
    for i, msg in enumerate(speaking_history[-6:], 1):  # 마지막 6개 표시
        speaker = msg.get("speaker_id", "Unknown")
        stage = msg.get("stage", "unknown")
        text = msg.get("text", "")[:150] + "..." if len(msg.get("text", "")) > 150 else msg.get("text", "")
        
        print(f"   {i}. 🤖 [{speaker}] ({stage}): {text}")

    # 성능 분석 출력
    print_performance_analysis(dialogue)

def test_one_on_one_structure_validation():
    """1대1 구조 검증 테스트"""
    print_header("1대1 구조 검증 테스트")
    
    room_data = create_one_on_one_debate_data()
    
    try:
        dialogue = DebateDialogue("test_structure", room_data)
        
        # 참가자 구조 확인
        participants = dialogue.participants
        print(f"✅ 참가자 구조 검증:")
        print(f"   - PRO 측: {participants.get('pro', [])} ({len(participants.get('pro', []))}명)")
        print(f"   - CON 측: {participants.get('con', [])} ({len(participants.get('con', []))}명)")
        
        # 에이전트 구조 확인
        agents = dialogue.agents
        print(f"\n✅ 에이전트 구조 검증:")
        for agent_id, agent in agents.items():
            agent_type = "AI"
            print(f"   - {agent_id}: {agent_type} ({agent.name if hasattr(agent, 'name') else 'Unknown'})")
        
        # 발언 순서 시뮬레이션
        print(f"\n✅ 발언 순서 시뮬레이션:")
        for i in range(8):
            next_speaker = dialogue.get_next_speaker()
            speaker_id = next_speaker.get("speaker_id")
            role = next_speaker.get("role")
            stage = dialogue.state.get("current_stage")
            
            print(f"   턴 {i+1}: {speaker_id} ({role}) - {stage}")
            
            # 가상 메시지로 단계 진행
            dialogue.state["speaking_history"].append({
                "speaker_id": speaker_id,
                "role": role,
                "stage": stage,
                "text": f"Test message from {speaker_id}",
                "timestamp": time.time()
            })
            dialogue.state["turn_count"] += 1
            
            if dialogue.state.get("current_stage") == "completed":
                break
        
        print(f"✅ 구조 검증 완료")
        
    except Exception as e:
        print(f"❌ 구조 검증 실패: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """메인 테스트 실행"""
    print_header("1대1 토론 테스트 시스템 (니체 vs 카뮈)")
    
    print("🎮 테스트 옵션을 선택하세요:")
    print("   1. 1대1 토론 실행")
    print("   2. 1대1 구조 검증만")
    print("   3. 전체 테스트 실행")
    print()
    
    try:
        choice = input("선택 (1-3): ").strip()
        
        if choice == "1":
            # 1대1 토론만
            test_one_on_one_debate()
        elif choice == "2":
            # 구조 검증만
            test_one_on_one_structure_validation()
        elif choice == "3":
            # 전체 테스트
            test_one_on_one_structure_validation()
            print("\n" + "-"*70)
            test_one_on_one_debate()
        else:
            print("❌ 잘못된 선택입니다. 전체 테스트를 실행합니다.")
            test_one_on_one_structure_validation()
            print("\n" + "-"*70)
            test_one_on_one_debate()
        
        print_header("모든 테스트 완료")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 