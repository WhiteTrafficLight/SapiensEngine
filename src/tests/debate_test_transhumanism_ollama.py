"""
트랜스휴머니즘 토론 테스트 - 니체 vs 마르크스
PDF 컨텍스트를 사용한 철학적 토론 시뮬레이션
"""

import sys
import os
import time
import logging

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.dialogue.types.debate_dialogue_ollama import DebateDialogue, DebateStage, ParticipantRole

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_transhumanism_debate_data():
    """트랜스휴머니즘 토론 데이터 생성 - 니체 vs 마르크스"""
    
    # PDF 파일 경로 (절대 경로로 설정)
    pdf_path = os.path.join(project_root, "sapiens_engine", "context_files", "LimitationsofTranshumanism.pdf")
    
    return {
        'title': 'Transhumanism: Human Evolution or Human Extinction?',
        'context': pdf_path,  # PDF 파일 경로를 컨텍스트로 사용
        'dialogueType': 'debate',
        'participants': {
            'pro': {
                'character_id': 'nietzsche',
                'philosopher_key': 'nietzsche',
                'name': 'Friedrich Nietzsche',
                'personality': 'passionate',
                'style': 'provocative',
                'argumentation_style': 'philosophical'
            },
            'con': {
                'character_id': 'marx',
                'philosopher_key': 'marx', 
                'name': 'Karl Marx',
                'personality': 'analytical',
                'style': 'systematic',
                'argumentation_style': 'materialist'
            }
        },
        'moderator': {
            'agent_id': 'moderator_001',
            'name': 'AI Moderator',
            'style': 'neutral',
            'style_id': '0',
            'personality': 'balanced'
        }
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
    if speaker == "moderator":
        color = "\033[96m"  # 청록색
        icon = "🎯"
    elif speaker == "nietzsche":
        color = "\033[91m"  # 빨간색 (찬성)
        icon = "⚡"
    elif speaker == "marx":
        color = "\033[94m"  # 파란색 (반대)
        icon = "🔨"
    else:
        color = "\033[92m"  # 초록색 (사용자)
        icon = "👤"
    
    reset = "\033[0m"
    
    print(f"\n{color}{icon} [{speaker}]{reset}")
    print(f"{message}")

def print_dialogue_state(dialogue):
    """대화 상태 출력"""
    state = dialogue.get_dialogue_state()
    
    print(f"\n📊 토론 상태:")
    print(f"   단계: {state['current_stage']}")
    print(f"   턴 수: {state['turn_count']}")
    print(f"   상태: {'진행 중' if state['playing'] else '일시정지'}")

def print_participants_info():
    """참가자 정보 출력"""
    print(f"\n👥 Participants:")
    print(f"   🟥 PRO: Friedrich Nietzsche - Supporting human enhancement through 'Übermensch' philosophy")
    print(f"   🟦 CON: Karl Marx - Critiquing technological impact from materialist perspective")
    print(f"   🟨 Moderator: AI Moderator")

def print_performance_analysis(dialogue):
    """성능 분석 출력"""
    try:
        metrics = dialogue.get_performance_metrics()
        
        print(f"\n📈 성능 분석:")
        print(f"   방 ID: {metrics['room_id']}")
        print(f"   스트리밍: {'활성화' if metrics['streaming_enabled'] else '비활성화'}")
        print(f"   벡터 저장소: {'사용' if metrics['vector_store_available'] else '미사용'}")
        print(f"   참가자 수: PRO {metrics['participants_count']['pro']}, CON {metrics['participants_count']['con']}")
        print(f"   에이전트 수: {metrics['agents_count']}")
        
        # 분석 상태 확인
        analysis_status = dialogue.get_analysis_status()
        if analysis_status.get('analysis_completion_tracker'):
            print(f"   논지 분석 상태:")
            for analyzer, targets in analysis_status['analysis_completion_tracker'].items():
                completed = sum(1 for status in targets.values() if status)
                total = len(targets)
                print(f"     [{analyzer}]: {completed}/{total} 완료")
        
    except Exception as e:
        print(f"   성능 분석 오류: {str(e)}")

def test_transhumanism_debate():
    """트랜스휴머니즘 토론 테스트 실행"""
    
    print_header("트랜스휴머니즘 토론 테스트 - 니체 vs 마르크스")
    
    # PDF 파일 존재 확인
    pdf_path = os.path.join(project_root, "sapiens_engine", "context_files", "LimitationsofTranshumanism.pdf")
    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return False
    
    print(f"✅ PDF 컨텍스트 파일 확인: {pdf_path}")
    
    # 토론 데이터 생성
    room_data = create_transhumanism_debate_data()
    
    print_participants_info()
    
    # 토론 대화 초기화
    print(f"\n🚀 토론 초기화 중...")
    start_time = time.time()
    
    try:
        dialogue = DebateDialogue(
            room_id="transhumanism_debate_001",
            room_data=room_data,
            use_async_init=False,
            enable_streaming=False
        )
        
        init_time = time.time() - start_time
        print(f"✅ 토론 초기화 완료 ({init_time:.2f}초)")
        
        # 입장 진술문 확인
        print(f"\n📝 입장 진술문:")
        stance_statements = dialogue.stance_statements
        print(f"   🟥 찬성 (니체): {stance_statements.get('pro', 'N/A')}")
        print(f"   🟦 반대 (마르크스): {stance_statements.get('con', 'N/A')}")
        
        print_dialogue_state(dialogue)
        print_performance_analysis(dialogue)
        
        # 토론 진행
        print(f"\n🎭 토론 시작!")
        
        max_turns = 15  # 최대 턴 수 제한
        turn_count = 0
        
        while turn_count < max_turns:
            turn_count += 1
            
            # 다음 발언자 확인
            next_speaker_info = dialogue.get_next_speaker()
            
            if next_speaker_info.get("status") == "waiting":
                # 분석 대기 상태
                speaker_id = next_speaker_info.get("speaker_id")
                print_message(speaker_id, next_speaker_info.get("message", "분석 완료 대기 중"), is_waiting=True)
                
                # 분석 완료 강제 설정 (테스트용)
                if speaker_id in ["nietzsche", "marx"]:
                    dialogue.force_analysis_completion(speaker_id)
                    print(f"   ✅ [{speaker_id}] 분석 완료 처리")
                
                continue
            
            if not next_speaker_info.get("can_proceed", True):
                print(f"❌ 토론 진행 불가: {next_speaker_info}")
                break
            
            speaker_id = next_speaker_info.get("speaker_id")
            if not speaker_id:
                print(f"✅ 토론 완료!")
                break
            
            print(f"\n--- 턴 {turn_count} ---")
            
            # 응답 생성
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
                    "moderator_summary_1": "📋 1차 요약",
                    "interactive_argument": "⚔️ 상호논증",
                    "moderator_summary_2": "📋 2차 요약",
                    "pro_conclusion": "🟥 찬성측 결론",
                    "con_conclusion": "🟦 반대측 결론",
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
                break
            
            # 단계별 대기 시간
            if current_stage in ["pro_argument", "con_argument"]:
                time.sleep(1)  # 입론 단계
            elif current_stage == "interactive_argument":
                time.sleep(0.5)  # 상호논증 단계
            else:
                time.sleep(0.5)  # 기타 단계
        
        # 최종 상태 출력
        print_dialogue_state(dialogue)
        print_performance_analysis(dialogue)
        
        total_time = time.time() - start_time
        print(f"\n⏱️ 총 소요 시간: {total_time:.2f}초")
        print(f"📊 평균 턴당 시간: {total_time/turn_count:.2f}초")
        
        return True
        
    except Exception as e:
        print(f"❌ 토론 테스트 실패: {str(e)}")
        logger.error(f"Debate test error: {str(e)}", exc_info=True)
        return False

def test_transhumanism_structure_validation():
    """트랜스휴머니즘 토론 구조 검증"""
    
    print_header("토론 구조 검증")
    
    try:
        room_data = create_transhumanism_debate_data()
        dialogue = DebateDialogue(
            room_id="structure_test_001",
            room_data=room_data
        )
        
        # 기본 구조 검증
        assert dialogue.room_id == "structure_test_001"
        assert dialogue.dialogue_type == "debate"
        assert dialogue.room_data['title'] == "Transhumanism: Human Evolution or Human Extinction?"
        
        # 참가자 검증
        assert ParticipantRole.PRO in dialogue.participants
        assert ParticipantRole.CON in dialogue.participants
        assert ParticipantRole.MODERATOR in dialogue.participants
        
        # 에이전트 검증
        assert "nietzsche" in dialogue.agents
        assert "marx" in dialogue.agents
        assert ParticipantRole.MODERATOR in dialogue.agents
        
        # 입장 진술문 검증
        assert "pro" in dialogue.stance_statements
        assert "con" in dialogue.stance_statements
        
        # 벡터 저장소 검증 (PDF 컨텍스트 사용)
        assert dialogue.vector_store is not None
        
        print(f"✅ 모든 구조 검증 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 구조 검증 실패: {str(e)}")
        return False

def main():
    """메인 함수"""
    print_header("트랜스휴머니즘 토론 테스트 시작")
    
    success_count = 0
    total_tests = 2
    
    # 1. 구조 검증 테스트
    print(f"\n🧪 테스트 1/2: 토론 구조 검증")
    if test_transhumanism_structure_validation():
        success_count += 1
        print(f"✅ 구조 검증 성공")
    else:
        print(f"❌ 구조 검증 실패")
    
    # 2. 실제 토론 테스트
    print(f"\n🧪 테스트 2/2: 트랜스휴머니즘 토론 실행")
    if test_transhumanism_debate():
        success_count += 1
        print(f"✅ 토론 테스트 성공")
    else:
        print(f"❌ 토론 테스트 실패")
    
    # 결과 요약
    print_header("테스트 결과 요약")
    print(f"성공: {success_count}/{total_tests}")
    print(f"성공률: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print(f"🎉 모든 테스트 성공!")
        return True
    else:
        print(f"⚠️ 일부 테스트 실패")
        return False

if __name__ == "__main__":
    main() 