"""
트랜스휴머니즘 토론 테스트 (유저 vs 카뮈) - 빠른 테스트용
사용자 직접 참여 토론 시뮬레이션 (PDF 컨텍스트 없음)
"""

import sys
import os
import time
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.dialogue.types.debate_dialogue import DebateDialogue, DebateStage, ParticipantRole

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_user_vs_nietzsche_debate_data():
    """유저 vs 니체 토론 데이터 생성"""
    
    return {
        'title': '트랜스휴머니즘: 인간의 도약인가 종말인가?',
        'context': '기술을 통한 인간 능력 향상과 수명 연장이 가능해지고 있는 현재, 트랜스휴머니즘이 인류에게 미칠 영향에 대해 토론합니다.',
        'dialogueType': 'debate',
        'participants': {
            'pro': {
                'character_id': 'nietzsche',
                'philosopher_key': 'nietzsche',
                'name': '프리드리히 니체',
                'personality': 'passionate',
                'style': 'provocative',
                'argumentation_style': 'revolutionary'
            },
            'con': {
                'id': 'user_001',
                'name': '사용자',
                'is_user': True
            },
            'users': ['user_001']
        },
        'moderator': {
            'agent_id': 'moderator_001',
            'name': 'AI 모더레이터',
            'style': 'neutral',
            'style_id': '0',
            'personality': 'balanced'
        },
        'user_ids': ['user_001']
    }

def print_header(title):
    """헤더 출력"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_message(speaker, message, is_user=False, is_waiting=False):
    """메시지 출력 (색상 포함)"""
    if is_waiting:
        print(f"\n⏳ [{speaker}] 분석 완료 대기 중...")
        return
        
    # 발언자별 색상 설정
    if speaker == "moderator" or speaker == "moderator_001":
        color = "\033[96m"  # 청록색
        icon = "🎯"
        display_name = "모더레이터"
    elif speaker == "camus":
        color = "\033[94m"  # 파란색 (반대)
        icon = "🚬"
        display_name = "카뮈"
    elif speaker == "user_001" or is_user:
        color = "\033[92m"  # 초록색 (사용자)
        icon = "👤"
        display_name = "사용자 (찬성)"
    else:
        color = "\033[93m"  # 노란색
        icon = "❓"
        display_name = speaker
    
    reset = "\033[0m"
    
    print(f"\n{color}{icon} [{display_name}]{reset}")
    print(f"{message}")

def get_user_input(prompt_text):
    """사용자 입력 받기"""
    print(f"\n{prompt_text}")
    print("=" * 60)
    
    lines = []
    print("💬 메시지를 입력하세요 (빈 줄 입력시 완료):")
    
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        except KeyboardInterrupt:
            print("\n❌ 입력이 취소되었습니다.")
            return None
    
    user_message = "\n".join(lines).strip()
    
    if not user_message:
        print("⚠️ 메시지가 비어있습니다. 기본 메시지를 사용합니다.")
        return "죄송합니다. 더 생각해보겠습니다."
    
    return user_message

def print_dialogue_state(dialogue):
    """대화 상태 출력"""
    state = dialogue.get_dialogue_state()
    
    print(f"\n📊 토론 상태:")
    print(f"   단계: {state['current_stage']}")
    print(f"   턴 수: {state['turn_count']}")
    print(f"   상태: {'진행 중' if state['playing'] else '일시정지'}")

def print_participants_info():
    """참가자 정보 출력"""
    print(f"\n👥 참가자:")
    print(f"   🟥 찬성 (PRO): 🗲 니체 - 창조적 개인의 의지력과 가치 창조 옹호")
    print(f"   🟦 반대 (CON): 👤 사용자 - 트랜스휴머니즘의 문제점 지적")
    print(f"   🟨 모더레이터: 🎯 AI 모더레이터")

def test_user_vs_nietzsche_debate():
    """유저 vs 니체 토론 테스트 실행"""
    
    print_header("트랜스휴머니즘 토론 테스트 - 니체 vs 사용자")
    
    # 토론 데이터 생성
    room_data = create_user_vs_nietzsche_debate_data()
    
    print_participants_info()
    
    print(f"\n🎯 토론 주제: {room_data['title']}")
    print(f"📝 컨텍스트: {room_data['context']}")
    
    # 토론 대화 초기화
    print(f"\n🚀 토론 초기화 중...")
    start_time = time.time()
    
    try:
        dialogue = DebateDialogue(
            room_id="user_vs_nietzsche_001",
            room_data=room_data,
            use_async_init=False,
            enable_streaming=False,
            sequential_rag_search=True
        )
        
        init_time = time.time() - start_time
        print(f"✅ 토론 초기화 완료 ({init_time:.2f}초)")
        
        # 입장 진술문 확인
        print(f"\n📝 입장 진술문:")
        stance_statements = dialogue.stance_statements
        print(f"   🟥 찬성 (니체): {stance_statements.get('pro', 'N/A')}")
        print(f"   🟦 반대 (사용자): {stance_statements.get('con', 'N/A')}")
        
        print_dialogue_state(dialogue)
        
        print(f"\n🎭 토론 시작!")
        print(f"📋 진행 순서:")
        print(f"   1. 모더레이터 오프닝")
        print(f"   2. 니체 입론 (찬성)")
        print(f"   3. 사용자 입론 (반대)")
        print(f"   4. 상호논증 단계")
        print(f"   5. 토론 마무리")
        
        max_turns = 10
        turn_count = 0
        
        while turn_count < max_turns:
            turn_count += 1
            
            # 다음 발언자 확인
            next_speaker_info = dialogue.get_next_speaker()
            
            print(f"\n--- 턴 {turn_count} ---")
            print(f"🔍 다음 발언자 정보: {next_speaker_info}")
            
            # waiting 상태 처리 개선
            if next_speaker_info.get("status") == "waiting":
                speaker_id = next_speaker_info.get("speaker_id")
                print(f"⏳ [{speaker_id}] 분석 대기 중... 강제 완료 처리")
                
                # 모든 분석을 강제 완료
                dialogue.force_analysis_completion(speaker_id)
                print(f"   ✅ [{speaker_id}] 분석 완료 처리")
                
                # 다시 다음 발언자 확인
                next_speaker_info = dialogue.get_next_speaker()
                print(f"   🔄 재확인 결과: {next_speaker_info}")
            
            if not next_speaker_info.get("can_proceed", True):
                print(f"❌ 토론 진행 불가: {next_speaker_info}")
                break
            
            speaker_id = next_speaker_info.get("speaker_id")
            if not speaker_id:
                print(f"✅ 토론 완료!")
                break
            
            # 사용자 차례인지 확인
            if speaker_id == "user_001":
                # 사용자 입력 받기
                stage_info = {
                    "con_argument": "🟦 반대측 입론 단계",
                    "interactive_argument": "⚔️ 상호논증 - 반박 단계"
                }
                
                current_stage = dialogue.get_dialogue_state().get('current_stage', 'unknown')
                stage_name = stage_info.get(current_stage, f"단계: {current_stage}")
                
                user_message = get_user_input(f"👤 [{stage_name}] 사용자님의 발언을 입력해주세요:")
                
                if user_message is None:
                    print("❌ 토론이 중단되었습니다.")
                    break
                
                # 사용자 메시지 처리
                print(f"📤 사용자 메시지 처리 중...")
                user_response = dialogue.process_message(user_message, "user_001")
                
                if user_response.get("status") == "success":
                    print_message("user_001", user_message, is_user=True)
                    print(f"   ✅ 사용자 메시지 처리 완료")
                    
                    # 현재 단계 표시
                    current_stage = user_response.get("current_stage", "unknown")
                    stage_names = {
                        "opening": "🎬 오프닝",
                        "pro_argument": "🟥 찬성측 입론",
                        "con_argument": "🟦 반대측 입론", 
                        "interactive_argument": "⚔️ 상호논증",
                        "closing": "🎬 마무리",
                        "completed": "✅ 완료"
                    }
                    stage_display = stage_names.get(current_stage, current_stage)
                    print(f"   📍 단계: {stage_display}")
                else:
                    print(f"❌ 사용자 메시지 처리 실패: {user_response.get('message', 'Unknown error')}")
                    break
            else:
                # AI 응답 생성
                print(f"🤖 [{speaker_id}] AI 응답 생성 중...")
                response_start = time.time()
                response = dialogue.generate_response()
                response_time = time.time() - response_start
                
                if response.get("status") == "success":
                    message = response.get("message", "")
                    speaker = response.get("speaker_id", "unknown")
                    
                    print_message(speaker, message)
                    print(f"   ⏱️ 응답 시간: {response_time:.2f}초")
                    
                    # 현재 단계 표시
                    current_stage = response.get("current_stage", "unknown")
                    stage_names = {
                        "opening": "🎬 오프닝",
                        "pro_argument": "🟥 찬성측 입론",
                        "con_argument": "🟦 반대측 입론", 
                        "interactive_argument": "⚔️ 상호논증",
                        "closing": "🎬 마무리",
                        "completed": "✅ 완료"
                    }
                    stage_display = stage_names.get(current_stage, current_stage)
                    print(f"   📍 단계: {stage_display}")
                    
                elif response.get("status") == "paused":
                    print(f"⏸️ 토론 일시정지")
                    break
                elif response.get("status") == "completed":
                    print(f"🏁 토론 완료!")
                    break
                else:
                    print(f"❌ 응답 생성 실패: {response.get('message', 'Unknown error')}")
                    print(f"   🔍 응답 상세: {response}")
                    break
            
            # 단계별 대기 시간
            time.sleep(0.5)
        
        # 최종 상태 출력
        print_dialogue_state(dialogue)
        
        total_time = time.time() - start_time
        print(f"\n⏱️ 총 소요 시간: {total_time:.2f}초")
        if turn_count > 0:
            print(f"📊 평균 턴당 시간: {total_time/turn_count:.2f}초")
        
        return True
        
    except Exception as e:
        print(f"❌ 토론 테스트 실패: {str(e)}")
        logger.error(f"Debate test error: {str(e)}", exc_info=True)
        return False

def main():
    """메인 함수"""
    print_header("트랜스휴머니즘 토론 테스트 (니체 vs 사용자) 시작")
    
    # 바로 토론 실행
    if test_user_vs_nietzsche_debate():
        print(f"\n🎉 토론 테스트 성공!")
        return True
    else:
        print(f"\n⚠️ 토론 테스트 실패")
        return False

if __name__ == "__main__":
    main() 