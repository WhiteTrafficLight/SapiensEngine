#!/usr/bin/env python3

import sys
sys.path.append('.')

def test_simple_debate_init():
    print("🔧 [DEBUG] 테스트 시작")
    
    try:
        print("🔧 [DEBUG] DebateDialogue import 시도")
        from src.dialogue.types.debate_dialogue import DebateDialogue
        print("🔧 [DEBUG] DebateDialogue import 성공")
        
        room_data = {
            'title': '간단한 테스트 주제',
            'context': '테스트용 컨텍스트',
            'participants': {
                'pro': {'character_id': 'nietzsche'},
                'con': {'character_id': 'camus'}
            }
        }
        print("🔧 [DEBUG] room_data 준비 완료")
        
        print("🔧 [DEBUG] DebateDialogue 생성 시도")
        debate = DebateDialogue('test_room', room_data)
        print("🔧 [DEBUG] DebateDialogue 생성 성공!")
        
        print("🔧 [DEBUG] 첫 번째 응답 생성 시도")
        response = debate.generate_response()
        print(f"🔧 [DEBUG] 응답 결과: {response}")
        
    except Exception as e:
        print(f"🔧 [DEBUG] ❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_debate_init() 