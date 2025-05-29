#!/usr/bin/env python3
"""
사용자 참여 토론 테스트

실제 사용자가 토론에 참여하는 상황을 시뮬레이션하고 테스트
- 니체 (찬성측 AI)
- User123 (반대측 실제 사용자)
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

def create_user_debate_room_data():
    """사용자 참여 토론방 데이터 생성 - YAML/JSON 파일에서 로드"""
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
    
    # 니체 데이터 가져오기
    nietzsche_data = philosophers.get("nietzsche", {})
    
    return {
        "title": "AI가 인간의 창의성을 대체할 수 있는가?",
        "context": """
인공지능과 창의성에 대한 철학적 토론입니다.

## 주요 논점:
- AI의 창의성 정의와 범위
- 인간 창의성의 고유성
- 기술과 예술의 관계
- 미래 창작 활동의 변화

## 찬성 논리:
- AI는 이미 음악, 미술, 문학 분야에서 창작 활동
- 패턴 인식과 조합을 통한 새로운 창작 가능
- 인간의 한계를 뛰어넘는 무한한 가능성
- 창의성은 결과물로 판단되어야 함

## 반대 논리:
- 창의성에는 감정과 경험이 필수
- AI는 기존 데이터의 재조합일 뿐
- 진정한 창조는 의식과 의도에서 나옴
- 인간만이 가진 직관과 영감의 중요성

이 토론에서는 AI의 창의성이 인간을 대체할 수 있는지에 대해 깊이 있게 논의합니다.
        """,
        "participants": {
            "pro": {
                "character_id": "nietzsche",
                "name": nietzsche_data.get("name", "니체"),
                # 철학자 데이터에서 자동으로 로드됨 (debate_dialogue.py에서 처리)
            },
            "con": {
                "character_id": "user123",
                "name": "User123",
                "is_user": True  # 사용자임을 표시
            },
            "users": ["user123"]  # 사용자 목록
        },
        "moderator": {
            "agent_id": "debate_moderator",
            "name": "토론 진행자",
            "style_id": "1"  # moderator_style.json의 "1" (Formal University Professor)
        }
    }

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_message(speaker, message, is_user=False, is_waiting=False):
    """메시지 출력"""
    if is_waiting:
        print(f"\n🔄 [{speaker}] 입력을 기다리는 중...")
    elif is_user:
        print(f"\n👤 [{speaker}]: {message}")
    else:
        print(f"\n🤖 [{speaker}]: {message}")

def print_dialogue_state(dialogue):
    """대화 상태 출력"""
    state = dialogue.get_dialogue_state()
    print(f"\n📊 대화 상태:")
    print(f"   - 현재 단계: {state['current_stage']}")
    print(f"   - 턴 수: {state['turn_count']}")
    print(f"   - 다음 발언자: {state['next_speaker']}")
    print(f"   - 진행 상태: {state['status']}")

def get_user_input(prompt_message):
    """실제 사용자 입력 받기"""
    print(f"\n💬 {prompt_message}")
    print("📝 입력 옵션:")
    print("   - 토론 발언을 입력하세요")
    print("   - 'exit' 입력시 토론 종료")
    print("   - 'skip' 입력시 이번 턴 건너뛰기")
    print("-" * 50)
    
    user_input = input("👤 당신의 발언: ").strip()
    
    if not user_input:
        print("⚠️ 빈 입력입니다. 다시 입력해주세요.")
        return get_user_input(prompt_message)
    
    return user_input

def test_user_participation():
    """사용자 참여 토론 테스트"""
    print_header("사용자 참여 토론 테스트 시작")
    
    # 1. 토론방 데이터 생성
    room_data = create_user_debate_room_data()
    print(f"📝 토론 주제: {room_data['title']}")
    print(f"👥 참가자: 니체(찬성) vs User123(반대)")
    
    # 2. 사용자 매니저 초기화
    user_manager = UserManager()
    
    # 3. 사용자 등록 및 세션 생성
    user_config = {
        "role": "con",
        "display_name": "User123",
        "is_user": True,  # 사용자임을 명시
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
        dialogue = DebateDialogue("test_user_room", room_data)
        print(f"✅ 토론 대화 초기화 완료")
        
        # 사용자를 토론에 추가
        dialogue.add_user_participant("user123", "User123", user_config)
        print(f"✅ 사용자를 토론에 추가 완료")
        
        # 사용자 매니저에도 대화 참여 등록
        user_manager.add_user_to_dialogue("user123", "test_user_room")
        print(f"✅ 사용자 매니저에 대화 참여 등록 완료")
        
    except Exception as e:
        print(f"❌ 토론 초기화 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. 초기 상태 확인
    print_dialogue_state(dialogue)
    
    # 6. 토론 진행 시뮬레이션
    max_turns = 10
    turn_count = 0
    
    print_header("토론 진행 시작")
    
    # 사용자 안내 메시지
    print("🎯 토론 참여 안내:")
    print("   - 당신은 '반대측(CON)' 참가자로 참여합니다")
    print("   - 주제: AI가 인간의 창의성을 대체할 수 있는가?")
    print("   - 당신의 입장: AI는 인간의 창의성을 대체할 수 없다")
    print("   - 상대방: 프리드리히 니체 (찬성측)")
    print()
    print("💡 토론 진행 방식:")
    print("   1. 모더레이터 오프닝")
    print("   2. 니체의 찬성 입론")
    print("   3. 당신의 반대 입론 ← 여기서 입력 요청")
    print("   4. 이후 반박, 질의응답 등 진행")
    print()
    print("⌨️ 입력 방법:")
    print("   - 'exit': 토론 종료")
    print("   - 'skip': 현재 턴 건너뛰기")
    print("   - 그 외: 토론 발언으로 처리")
    print()
    
    input("📍 준비가 되면 Enter를 눌러 토론을 시작하세요...")
    print()
    
    while turn_count < max_turns and dialogue.playing:
        turn_count += 1
        print(f"\n🔄 턴 {turn_count}")
        
        try:
            # 현재 발언자 확인
            next_speaker_info = dialogue.get_next_speaker()
            next_speaker = next_speaker_info.get("speaker_id") or next_speaker_info.get("next_speaker")
            print(f"📢 다음 발언자: {next_speaker}")
            
            # 사용자 차례인지 확인
            if next_speaker == "user123":
                print_header("사용자 차례")
                
                # 사용자 참가자 객체 가져오기
                user_participant = dialogue.get_user_participant("user123")
                if not user_participant:
                    print("❌ 사용자 참가자를 찾을 수 없습니다.")
                    break
                
                # 사용자 활동 시간 업데이트
                user_manager.update_user_activity("user123")
                
                # 사용자 차례 확인
                turn_check = user_participant.process({
                    "action": "check_turn",
                    "dialogue_state": {
                        "next_speaker": next_speaker
                    }
                })
                
                if turn_check.get("is_my_turn"):
                    print(f"⏰ 응답 제한 시간: {turn_check.get('time_limit', 300)}초")
                    
                    # 사용자 입력 대기 시뮬레이션
                    print_message("System", "사용자 입력을 기다리는 중...", is_waiting=True)
                    
                    # 실제 환경에서는 여기서 사용자 입력을 기다림
                    user_input = get_user_input("사용자 입력 요청")
                    
                    if user_input.lower() == "exit":
                        print("👋 사용자가 토론을 종료했습니다.")
                        break
                    elif user_input.lower() == "skip":
                        print("⏭️ 사용자가 이번 턴을 건너뛰었습니다.")
                        # 다음 단계로 강제 전환
                        dialogue._check_stage_transition()
                        continue
                    
                    # 사용자 메시지 처리
                    message_result = user_participant.process({
                        "action": "process_message",
                        "message": user_input,
                        "timestamp": time.time(),
                        "current_stage": dialogue.state.get("current_stage", "discussion")
                    })
                    
                    print_message("User123", user_input, is_user=True)
                    
                    # 토론에 메시지 추가 - 올바른 형식으로 수정
                    dialogue_result = dialogue.process_message(
                        message=user_input,
                        user_id="user123"
                    )
                    
                    if dialogue_result.get("status") != "success":
                        print(f"⚠️ 메시지 처리 실패: {dialogue_result.get('message', 'Unknown error')}")
                    else:
                        print("✅ 사용자 메시지가 성공적으로 처리되었습니다.")
                    
                else:
                    print("⚠️ 사용자의 차례가 아닙니다.")
                    
            else:
                # AI 에이전트 차례
                print(f"🤖 AI 에이전트 차례: {next_speaker}")
                
                # AI 응답 생성
                result = dialogue.generate_response()
                
                if result.get("status") == "success" and result.get("response"):
                    response_data = result["response"]
                    speaker_name = response_data.get("speaker_name", next_speaker)
                    message = response_data.get("message", "")
                    
                    print_message(speaker_name, message)
                else:
                    print(f"⚠️ AI 응답 생성 실패: {result.get('message', 'Unknown error')}")
            
            # 상태 업데이트 확인
            print_dialogue_state(dialogue)
            
            # 잠시 대기 (실제 대화 속도 시뮬레이션)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ 턴 {turn_count} 처리 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            break
    
    # 7. 토론 종료 및 결과
    print_header("토론 종료")
    
    # 사용자 통계
    if user_participant:
        stats = user_participant.get_participation_stats()
        print(f"📊 사용자 참여 통계:")
        print(f"   - 총 메시지: {stats['total_messages']}")
        print(f"   - 평균 메시지 길이: {stats['average_message_length']}")
        print(f"   - 마지막 활동: {stats['last_activity']}")
    
    # 사용자 매니저 통계
    user_stats = user_manager.get_user_stats("user123")
    if user_stats:
        print(f"📈 사용자 매니저 통계:")
        print(f"   - 온라인 상태: {user_stats.get('is_online', False)}")
        print(f"   - 현재 대화: {user_stats.get('current_dialogue', 'None')}")
        print(f"   - 세션 시간: {user_stats.get('session_duration', 0):.1f}초")
    
    # 전체 대화 기록
    speaking_history = dialogue.state.get("speaking_history", [])
    print(f"\n📜 전체 대화 기록 ({len(speaking_history)}개 메시지):")
    for i, msg in enumerate(speaking_history[-5:], 1):  # 마지막 5개만 표시
        speaker = msg.get("speaker_name", "Unknown")
        text = msg.get("text", "")[:100] + "..." if len(msg.get("text", "")) > 100 else msg.get("text", "")
        print(f"   {i}. [{speaker}]: {text}")
    
    # 세션 정리
    user_manager.end_user_session(session.session_id)
    print(f"✅ 사용자 세션 종료 완료")

def test_user_manager_integration():
    """사용자 매니저 통합 테스트"""
    print_header("사용자 매니저 통합 테스트")
    
    user_manager = UserManager()
    
    # 여러 사용자 등록
    users = [
        ("user123", "User123", {"role": "con", "is_user": True}),
        ("user456", "User456", {"role": "pro", "is_user": True}),
        ("user789", "User789", {"role": "neutral", "is_user": True})
    ]
    
    sessions = []
    for user_id, username, config in users:
        # 세션 생성
        session = user_manager.create_user_session(user_id, username)
        sessions.append(session)
        
        # UserParticipant 생성
        user = user_manager.create_user_participant(user_id, username, config)
        print(f"✅ 등록: {user.username} ({user.role})")
    
    # 활성 사용자 확인
    online_users = user_manager.get_online_users()
    print(f"\n👥 온라인 사용자: {len(online_users)}명")
    
    # 토론 참여자 관리
    dialogue_id = "test_debate_001"
    
    for user_id, _, _ in users:
        user_manager.add_user_to_dialogue(user_id, dialogue_id)
        print(f"📝 {user_id}를 토론 {dialogue_id}에 추가")
    
    # 토론별 참여자 확인
    participants = user_manager.get_dialogue_participants(dialogue_id)
    print(f"\n🎯 토론 {dialogue_id} 참여자: {len(participants)}명")
    for user_id in participants:
        user_participant = user_manager.get_user_participant(user_id)
        if user_participant:
            print(f"   - {user_participant.username} ({user_participant.role})")
    
    # 시스템 통계
    system_stats = user_manager.get_system_stats()
    print(f"\n📊 시스템 통계:")
    print(f"   - 총 활성 사용자: {system_stats.get('total_active_users', 0)}")
    print(f"   - 총 세션: {system_stats.get('total_sessions', 0)}")
    print(f"   - 활성 대화: {system_stats.get('active_dialogues', 0)}")
    
    # 세션 정리
    for session in sessions:
        user_manager.end_user_session(session.session_id)
    print(f"\n✅ 모든 세션 종료 완료")

def main():
    """메인 테스트 실행"""
    print_header("사용자 참여 토론 테스트 시스템")
    
    print("🎮 테스트 옵션을 선택하세요:")
    print("   1. 실제 사용자 참여 토론 (대화형)")
    print("   2. 사용자 매니저 통합 테스트만")
    print("   3. 전체 테스트 실행")
    print()
    
    try:
        choice = input("선택 (1-3): ").strip()
        
        if choice == "1":
            # 실제 사용자 참여 토론만
            test_user_participation()
        elif choice == "2":
            # 사용자 매니저 테스트만
            test_user_manager_integration()
        elif choice == "3":
            # 전체 테스트
            test_user_participation()
            print("\n" + "-"*60)
            test_user_manager_integration()
        else:
            print("❌ 잘못된 선택입니다. 전체 테스트를 실행합니다.")
            test_user_participation()
            print("\n" + "-"*60)
            test_user_manager_integration()
        
        print_header("모든 테스트 완료")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 