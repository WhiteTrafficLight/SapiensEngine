#!/usr/bin/env python3
"""
다중 참가자 토론 테스트 (NPC + 사용자 혼합)

찬성측: 니체(AI), 헤겔(AI)
반대측: 카뮈(AI), User123(실제 사용자)

다중 참가자 구조와 사용자 참여를 동시에 테스트
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
from src.dialogue.managers.user_manager import UserManager
from src.agents.participant.user_participant import UserParticipant

def create_multi_participant_room_data():
    """다중 참가자 토론방 데이터 생성"""
    # 철학자 데이터 로드
    philosophers_file = os.path.join(project_root, "philosophers", "debate_optimized.yaml")
    try:
        with open(philosophers_file, 'r', encoding='utf-8') as file:
            philosophers = yaml.safe_load(file)
    except Exception as e:
        print(f"⚠️ 철학자 데이터 로드 실패: {e}")
        philosophers = {}
    
    # 모더레이터 스타일 로드
    moderator_style_file = os.path.join(project_root, "src", "agents", "moderator", "moderator_style.json")
    try:
        with open(moderator_style_file, 'r', encoding='utf-8') as file:
            moderator_styles = json.load(file)
    except Exception as e:
        print(f"⚠️ 모더레이터 스타일 로드 실패: {e}")
        moderator_styles = {}
    
    # 철학자 데이터 가져오기
    nietzsche_data = philosophers.get("nietzsche", {})
    hegel_data = philosophers.get("hegel", {})
    camus_data = philosophers.get("camus", {})
    
    return {
        "title": "AI가 인간의 창의성을 대체할 수 있는가?",
        "context": """
인공지능과 창의성에 대한 철학적 토론입니다.

## 주요 논점:
- AI의 창의성 정의와 범위
- 인간 창의성의 고유성
- 기술과 예술의 관계
- 미래 창작 활동의 변화

## 찬성 논리 (니체 & 헤겔):
- AI는 이미 음악, 미술, 문학 분야에서 창작 활동
- 패턴 인식과 조합을 통한 새로운 창작 가능
- 인간의 한계를 뛰어넘는 무한한 가능성
- 창의성은 결과물로 판단되어야 함
- 변증법적 발전을 통한 새로운 창조 형태

## 반대 논리 (카뮈 & User123):
- 창의성에는 감정과 경험이 필수
- AI는 기존 데이터의 재조합일 뿐
- 진정한 창조는 의식과 의도에서 나옴
- 인간만이 가진 직관과 영감의 중요성
- 부조리한 존재로서의 인간만이 진정한 창조 가능

이 토론에서는 4명의 참가자가 AI의 창의성에 대해 깊이 있게 논의합니다.
        """,
        "participants": {
            # 다중 참가자 구조 사용
            "pro": [
                {
                    "character_id": "nietzsche",
                    "name": nietzsche_data.get("name", "니체"),
                    "personality": "passionate",
                    "style": "provocative"
                },
                {
                    "character_id": "hegel",
                    "name": hegel_data.get("name", "헤겔"),
                    "personality": "systematic",
                    "style": "dialectical"
                }
            ],
            "con": [
                {
                    "character_id": "camus",
                    "name": camus_data.get("name", "카뮈"),
                    "personality": "existential",
                    "style": "absurdist"
                },
                {
                    "character_id": "user123",
                    "name": "User123",
                    "is_user": True  # 사용자임을 표시
                }
            ],
            "users": ["user123"],  # 사용자 목록
            "user_configs": {
                "user123": {
                    "username": "User123",
                    "display_name": "User123",
                    "role": "con",
                    "participation_style": "active"
                }
            }
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
    """메시지 출력 (다중 참가자용)"""
    if is_waiting:
        print(f"\n🔄 [{speaker}] 입력을 기다리는 중...")
    elif is_user:
        print(f"\n👤 [{speaker}]: {message}")
    elif speaker in ["nietzsche", "Nietzsche", "니체"]:
        print(f"\n⚡ [{speaker}]: {message}")
    elif speaker in ["hegel", "Hegel", "헤겔"]:
        print(f"\n🔄 [{speaker}]: {message}")
    elif speaker in ["camus", "Camus", "카뮈"]:
        print(f"\n🌊 [{speaker}]: {message}")
    else:
        print(f"\n🤖 [{speaker}]: {message}")

def print_dialogue_state(dialogue):
    """대화 상태 출력 (다중 참가자용)"""
    state = dialogue.get_dialogue_state()
    participants = dialogue.participants
    
    print(f"\n📊 대화 상태:")
    print(f"   - 현재 단계: {state['current_stage']}")
    print(f"   - 턴 수: {state['turn_count']}")
    print(f"   - 다음 발언자: {state.get('next_speaker', 'Unknown')}")
    print(f"   - 진행 상태: {state['status']}")
    print(f"   - 찬성측 참가자: {len(participants.get('pro', []))}명")
    print(f"   - 반대측 참가자: {len(participants.get('con', []))}명")
    print(f"   - 사용자 참가자: {len(participants.get('user', []))}명")

def get_user_input(prompt_message, current_stage):
    """실제 사용자 입력 받기 (다중 참가자용)"""
    print(f"\n💬 {prompt_message}")
    print("📝 입력 옵션:")
    print("   - 토론 발언을 입력하세요")
    print("   - 'exit' 입력시 토론 종료")
    print("   - 'skip' 입력시 이번 턴 건너뛰기")
    print("   - 'status' 입력시 현재 상태 확인")
    
    # 단계별 안내
    stage_guidance = {
        "con_argument": "💡 반대 입론: AI가 인간 창의성을 대체할 수 없는 이유를 논리적으로 제시하세요",
        "interactive_argument": "💡 상호논증: 상대방 주장에 대한 반박이나 질문을 제시하세요",
        "con_conclusion": "💡 최종 결론: 지금까지의 토론을 바탕으로 최종 입장을 정리하세요"
    }
    
    if current_stage in stage_guidance:
        print(f"📌 {stage_guidance[current_stage]}")
    
    print("-" * 50)
    
    user_input = input("👤 당신의 발언: ").strip()
    
    if not user_input:
        print("⚠️ 빈 입력입니다. 다시 입력해주세요.")
        return get_user_input(prompt_message, current_stage)
    
    return user_input

def print_participants_info():
    """참가자 정보 출력"""
    print("👥 토론 참가자:")
    print("   📍 찬성측 (PRO):")
    print("      ⚡ 니체 - 권력의지와 창조적 파괴의 철학자")
    print("      🔄 헤겔 - 변증법적 발전과 절대정신의 철학자")
    print("   📍 반대측 (CON):")
    print("      🌊 카뮈 - 부조리와 반항의 철학자")
    print("      👤 User123 - 실제 사용자 (당신)")
    print()
    print("🎯 당신의 역할:")
    print("   - 반대측 참가자로서 AI가 인간 창의성을 대체할 수 없다는 입장")
    print("   - 카뮈와 함께 협력하여 찬성측(니체, 헤겔)에 맞서기")
    print("   - 인간만의 고유한 창의성과 존재적 가치 강조")

def test_multi_participant_debate():
    """다중 참가자 토론 테스트"""
    print_header("다중 참가자 토론 테스트 (NPC + 사용자 혼합)")
    
    # 1. 토론방 데이터 생성
    room_data = create_multi_participant_room_data()
    print(f"📝 토론 주제: {room_data['title']}")
    print_participants_info()
    
    # 2. 사용자 매니저 초기화
    user_manager = UserManager()
    
    # 3. 사용자 등록 및 세션 생성
    user_config = {
        "role": "con",
        "display_name": "User123",
        "is_user": True,
        "preferences": {
            "language": "ko",
            "response_time_limit": 300
        },
        "permissions": {
            "can_speak": True,
            "can_moderate": False
        }
    }
    
    # 사용자 세션 생성
    session = user_manager.create_user_session("user123", "User123")
    print(f"✅ 사용자 세션 생성 완료: {session.session_id}")
    
    # UserParticipant 객체 생성
    user_participant = user_manager.create_user_participant("user123", "User123", user_config)
    print(f"✅ 사용자 등록 완료: {user_participant.username}")
    
    # 4. 토론 대화 초기화
    try:
        dialogue = DebateDialogue("test_multi_room", room_data)
        print(f"✅ 다중 참가자 토론 대화 초기화 완료")
        
        # 사용자를 토론에 추가 (이미 room_data에 포함되어 있지만 명시적으로 추가)
        dialogue.add_user_participant("user123", "User123", user_config)
        print(f"✅ 사용자를 토론에 추가 완료")
        
        # 사용자 매니저에도 대화 참여 등록
        user_manager.add_user_to_dialogue("user123", "test_multi_room")
        print(f"✅ 사용자 매니저에 대화 참여 등록 완료")
        
        # 참가자 확인
        participants = dialogue.participants
        print(f"✅ 참가자 확인:")
        print(f"   - 찬성측: {participants.get('pro', [])}")
        print(f"   - 반대측: {participants.get('con', [])}")
        print(f"   - 사용자: {participants.get('user', [])}")
        
    except Exception as e:
        print(f"❌ 토론 초기화 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 초기 상태 확인
    print_dialogue_state(dialogue)
    
    # 6. 토론 진행 시뮬레이션
    max_turns = 20  # 다중 참가자이므로 더 많은 턴 필요
    turn_count = 0
    
    print_header("다중 참가자 토론 진행 시작")
    
    # 사용자 안내 메시지
    print("🎯 다중 참가자 토론 안내:")
    print("   - 총 4명이 참여하는 토론입니다")
    print("   - 찬성측: 니체, 헤겔 (AI)")
    print("   - 반대측: 카뮈 (AI), User123 (당신)")
    print()
    print("💡 토론 진행 순서:")
    print("   1. 모더레이터 오프닝")
    print("   2. 찬성측 입론 (니체 → 헤겔)")
    print("   3. 반대측 입론 (카뮈 → User123) ← 여기서 입력 요청")
    print("   4. 모더레이터 요약")
    print("   5. 상호논증 (자유 발언)")
    print("   6. 최종 결론 (각자 순서대로)")
    print()
    print("⌨️ 추가 명령어:")
    print("   - 'participants': 참가자 정보 다시 보기")
    print("   - 'history': 최근 대화 기록 보기")
    print()
    
    input("📍 준비가 되면 Enter를 눌러 다중 참가자 토론을 시작하세요...")
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
            
            # 사용자 차례인지 확인
            if next_speaker == "user123":
                print_header("사용자 차례 (다중 참가자 토론)")
                
                # 사용자 참가자 객체 가져오기
                user_participant = dialogue.get_user_participant("user123")
                if not user_participant:
                    print("❌ 사용자 참가자를 찾을 수 없습니다.")
                    break
                
                # 사용자 활동 시간 업데이트
                user_manager.update_user_activity("user123")
                
                # 현재 상황 안내
                print(f"🎯 현재 상황:")
                print(f"   - 단계: {current_stage}")
                print(f"   - 역할: 반대측 참가자")
                print(f"   - 동료: 카뮈 (AI)")
                print(f"   - 상대: 니체, 헤겔 (AI)")
                
                # 사용자 입력 대기
                user_input = get_user_input("다중 참가자 토론에서 사용자 입력 요청", current_stage)
                
                # 특수 명령어 처리
                if user_input.lower() == "exit":
                    print("👋 사용자가 토론을 종료했습니다.")
                    break
                elif user_input.lower() == "skip":
                    print("⏭️ 사용자가 이번 턴을 건너뛰었습니다.")
                    continue
                elif user_input.lower() == "status":
                    print_dialogue_state(dialogue)
                    continue
                elif user_input.lower() == "participants":
                    print_participants_info()
                    continue
                elif user_input.lower() == "history":
                    speaking_history = dialogue.state.get("speaking_history", [])
                    print(f"\n📜 최근 대화 기록 (최근 5개):")
                    for i, msg in enumerate(speaking_history[-5:], 1):
                        speaker = msg.get("speaker_id", "Unknown")
                        text = msg.get("text", "")[:100] + "..." if len(msg.get("text", "")) > 100 else msg.get("text", "")
                        print(f"   {i}. [{speaker}]: {text}")
                    continue
                
                # 사용자 메시지 처리
                print_message("User123", user_input, is_user=True)
                
                # 토론에 메시지 추가
                dialogue_result = dialogue.process_message(
                    message=user_input,
                    user_id="user123"
                )
                
                if dialogue_result.get("status") != "success":
                    print(f"⚠️ 메시지 처리 실패: {dialogue_result.get('reason', 'Unknown error')}")
                else:
                    print("✅ 사용자 메시지가 성공적으로 처리되었습니다.")
                    
            else:
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
                    elif speaker_name in ["hegel", "Hegel"]:
                        print("   💭 헤겔의 변증법적 사고가 드러나는 발언")
                    elif speaker_name in ["camus", "Camus"]:
                        print("   💭 카뮈의 부조리 철학이 드러나는 발언")
                        
                elif result.get("status") == "waiting_for_user":
                    print(f"⏳ 사용자 입력 대기 중: {result.get('speaker_id')}")
                    continue
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
    
    # 7. 토론 종료 및 결과
    print_header("다중 참가자 토론 종료")
    
    # 사용자 통계
    if user_participant:
        stats = user_participant.get_participation_stats()
        print(f"📊 사용자 참여 통계:")
        print(f"   - 총 메시지: {stats['total_messages']}")
        print(f"   - 평균 메시지 길이: {stats['average_message_length']}")
        print(f"   - 마지막 활동: {stats['last_activity']}")
    
    # 전체 대화 기록 분석
    speaking_history = dialogue.state.get("speaking_history", [])
    speaker_counts = {}
    for msg in speaking_history:
        speaker = msg.get("speaker_id", "Unknown")
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    print(f"\n📈 참가자별 발언 통계:")
    for speaker, count in speaker_counts.items():
        if speaker == "user123":
            print(f"   👤 {speaker}: {count}회 발언")
        else:
            print(f"   🤖 {speaker}: {count}회 발언")
    
    print(f"\n📜 전체 대화 기록 ({len(speaking_history)}개 메시지):")
    for i, msg in enumerate(speaking_history[-8:], 1):  # 마지막 8개 표시
        speaker = msg.get("speaker_id", "Unknown")
        stage = msg.get("stage", "unknown")
        text = msg.get("text", "")[:150] + "..." if len(msg.get("text", "")) > 150 else msg.get("text", "")
        
        if speaker == "user123":
            print(f"   {i}. 👤 [{speaker}] ({stage}): {text}")
        else:
            print(f"   {i}. 🤖 [{speaker}] ({stage}): {text}")
    
    # 세션 정리
    user_manager.end_user_session(session.session_id)
    print(f"✅ 사용자 세션 종료 완료")

def test_multi_structure_validation():
    """다중 참가자 구조 검증 테스트"""
    print_header("다중 참가자 구조 검증 테스트")
    
    room_data = create_multi_participant_room_data()
    
    try:
        dialogue = DebateDialogue("test_structure", room_data)
        
        # 참가자 구조 확인
        participants = dialogue.participants
        print(f"✅ 참가자 구조 검증:")
        print(f"   - PRO 측: {participants.get('pro', [])} ({len(participants.get('pro', []))}명)")
        print(f"   - CON 측: {participants.get('con', [])} ({len(participants.get('con', []))}명)")
        print(f"   - USER: {participants.get('user', [])} ({len(participants.get('user', []))}명)")
        
        # 에이전트 구조 확인
        agents = dialogue.agents
        print(f"\n✅ 에이전트 구조 검증:")
        for agent_id, agent in agents.items():
            agent_type = "User" if hasattr(agent, 'username') else "AI"
            print(f"   - {agent_id}: {agent_type} ({agent.name if hasattr(agent, 'name') else 'Unknown'})")
        
        # 발언 순서 시뮬레이션
        print(f"\n✅ 발언 순서 시뮬레이션:")
        for i in range(10):
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
    print_header("다중 참가자 토론 테스트 시스템 (NPC + 사용자 혼합)")
    
    print("🎮 테스트 옵션을 선택하세요:")
    print("   1. 다중 참가자 토론 실행 (대화형)")
    print("   2. 다중 참가자 구조 검증만")
    print("   3. 전체 테스트 실행")
    print()
    
    try:
        choice = input("선택 (1-3): ").strip()
        
        if choice == "1":
            # 다중 참가자 토론만
            test_multi_participant_debate()
        elif choice == "2":
            # 구조 검증만
            test_multi_structure_validation()
        elif choice == "3":
            # 전체 테스트
            test_multi_structure_validation()
            print("\n" + "-"*70)
            test_multi_participant_debate()
        else:
            print("❌ 잘못된 선택입니다. 전체 테스트를 실행합니다.")
            test_multi_structure_validation()
            print("\n" + "-"*70)
            test_multi_participant_debate()
        
        print_header("모든 테스트 완료")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 