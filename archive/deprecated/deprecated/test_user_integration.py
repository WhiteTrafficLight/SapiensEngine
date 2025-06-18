#!/usr/bin/env python3
"""
User 클래스 통합 테스트

UserParticipant와 UserManager가 DebateDialogue와 제대로 통합되는지 테스트
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.dialogue.types.debate_dialogue import DebateDialogue, ParticipantRole
from src.dialogue.managers.user_manager import get_user_manager
from src.agents.participant.user_participant import UserParticipant

def test_user_integration():
    """User 클래스들의 통합 테스트"""
    print("=== User 클래스 통합 테스트 시작 ===\n")
    
    # 1. UserManager 테스트
    print("1. UserManager 테스트")
    user_manager = get_user_manager()
    
    # 사용자 세션 생성
    session = user_manager.create_user_session("user123", "테스트유저")
    print(f"   세션 생성: {session.user_id} ({session.username})")
    
    # UserParticipant 생성
    user_participant = user_manager.create_user_participant(
        "user123", 
        "테스트유저",
        {
            "role": "pro",
            "participation_style": "active",
            "preferences": {
                "language": "ko",
                "response_time_limit": 300
            }
        }
    )
    print(f"   UserParticipant 생성: {user_participant.user_id}")
    print(f"   사용자 역할: {user_participant.role}")
    print()
    
    # 2. DebateDialogue에 사용자 포함 테스트
    print("2. DebateDialogue에 사용자 포함 테스트")
    
    # 사용자가 포함된 room_data 구성
    room_data = {
        "title": "인공지능의 윤리적 사용에 대한 토론",
        "context": "AI 기술의 발전과 함께 윤리적 고려사항들이 중요해지고 있습니다.",
        "participants": {
            "pro": {
                "character_id": "nietzsche",
                "name": "니체"
            },
            "con": {
                "character_id": "camus", 
                "name": "카뮈"
            },
            "users": ["user123"],
            "user_configs": {
                "user123": {
                    "username": "테스트유저",
                    "role": "neutral",
                    "participation_style": "active"
                }
            }
        }
    }
    
    # DebateDialogue 초기화
    try:
        debate = DebateDialogue("test_room_001", room_data)
        print(f"   토론 대화 초기화 완료: {debate.room_id}")
        print(f"   참가자 수: {len(debate.participants)}")
        print(f"   사용자 참가자 수: {len(debate.user_participants)}")
        
        # 사용자 참가자 확인
        user_participant = debate.get_user_participant("user123")
        if user_participant:
            print(f"   사용자 참가자 확인: {user_participant.username} ({user_participant.role})")
        else:
            print("   ❌ 사용자 참가자를 찾을 수 없음")
        
        print()
        
        # 3. 사용자 메시지 처리 테스트
        print("3. 사용자 메시지 처리 테스트")
        
        # 현재 다음 발언자 확인
        next_speaker = debate.get_next_speaker()
        print(f"   현재 다음 발언자: {next_speaker.get('speaker_id')} (is_user: {next_speaker.get('is_user')})")
        
        # 사용자가 발언 차례가 아닐 때 메시지 전송 시도
        if next_speaker.get('speaker_id') != 'user123':
            result = debate.process_message("안녕하세요, 토론에 참여하고 싶습니다.", "user123")
            print(f"   순서가 아닐 때 메시지 결과: {result.get('status')}")
        
        # 4. 사용자 상태 및 통계 테스트
        print("\n4. 사용자 상태 및 통계 테스트")
        
        user_stats = user_manager.get_user_stats("user123")
        print(f"   사용자 온라인 상태: {user_stats['is_online']}")
        print(f"   현재 참여 대화: {user_stats['current_dialogue']}")
        print(f"   메시지 수: {user_stats['message_count']}")
        
        # 5. 사용자 설정 업데이트 테스트
        print("\n5. 사용자 설정 업데이트 테스트")
        
        update_result = user_manager.update_user_config("user123", {
            "response_time_limit": 600,
            "debate_style_preference": "collaborative"
        })
        print(f"   설정 업데이트 결과: {update_result}")
        
        updated_config = user_manager.get_user_config("user123")
        print(f"   업데이트된 설정: {updated_config}")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"   ❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def test_user_participant_standalone():
    """UserParticipant 단독 테스트"""
    print("\n=== UserParticipant 단독 테스트 ===\n")
    
    # UserParticipant 생성
    user = UserParticipant(
        user_id="test_user",
        username="테스트사용자",
        config={
            "role": "pro",
            "participation_style": "active",
            "preferences": {
                "language": "ko",
                "response_time_limit": 300
            },
            "permissions": {
                "can_speak": True,
                "can_moderate": False
            }
        }
    )
    
    print(f"사용자 생성: {user.username} ({user.user_id})")
    print(f"역할: {user.role}")
    print(f"참여 스타일: {user.participation_style}")
    
    # 다양한 액션 테스트
    actions = [
        {"action": "get_status"},
        {"action": "check_turn", "dialogue_state": {"next_speaker": "test_user"}},
        {"action": "process_message", "message": "안녕하세요!", "current_stage": "opening"},
        {"action": "join_dialogue", "dialogue_id": "test_dialogue", "role": "pro"}
    ]
    
    for action_data in actions:
        result = user.process(action_data)
        print(f"\n액션 '{action_data['action']}' 결과:")
        print(f"  상태: {result.get('status', 'N/A')}")
        if 'is_my_turn' in result:
            print(f"  내 차례: {result['is_my_turn']}")
        if 'message_count' in result:
            print(f"  메시지 수: {result['message_count']}")
    
    # 통계 확인
    stats = user.get_participation_stats()
    print(f"\n참여 통계: {stats}")
    
    # 권한 확인
    print(f"\n권한 확인:")
    print(f"  발언 가능: {user.can_perform_action('speak')}")
    print(f"  모더레이션 가능: {user.can_perform_action('moderate')}")
    
    # 딕셔너리 변환 테스트
    user_dict = user.to_dict()
    print(f"\n딕셔너리 변환 키들: {list(user_dict.keys())}")

if __name__ == "__main__":
    test_user_participant_standalone()
    test_user_integration() 