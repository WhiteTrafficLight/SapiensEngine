"""
트랜스휴머니즘 토론 테스트 - 니체 vs 마르크스 (JSON 출력 포함)
PDF 컨텍스트를 사용한 철학적 토론 시뮬레이션 + 대화 내용과 전략 정보 JSON 저장
"""

import sys
import os
import time
import logging
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.dialogue.types.debate_dialogue import DebateDialogue, DebateStage, ParticipantRole

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DebateDataCollector:
    """토론 데이터 수집 및 JSON 저장 클래스"""
    
    def __init__(self):
        self.conversation_data = {
            "metadata": {
                "topic": "",
                "start_time": "",
                "end_time": "",
                "total_duration": 0,
                "participants": {},
                "pdf_context": ""
            },
            "stance_statements": {},
            "conversation": [],
            "strategy_analysis": {
                "nietzsche": {
                    "attack_strategies": [],
                    "defense_strategies": [],
                    "rag_usage": []
                },
                "marx": {
                    "attack_strategies": [],
                    "defense_strategies": [],
                    "rag_usage": []
                }
            },
            "performance_metrics": {}
        }
        self.start_time = None
        
    def initialize(self, dialogue, topic):
        """데이터 수집 초기화"""
        self.start_time = time.time()
        self.conversation_data["metadata"]["topic"] = topic
        self.conversation_data["metadata"]["start_time"] = datetime.now().isoformat()
        
        # 참가자 정보
        participants = dialogue.participants
        self.conversation_data["metadata"]["participants"] = {
            "pro": participants.get(ParticipantRole.PRO, []),
            "con": participants.get(ParticipantRole.CON, [])
        }
        
        # 입장 진술문
        self.conversation_data["stance_statements"] = dialogue.stance_statements
        
        # PDF 컨텍스트
        if hasattr(dialogue, 'vector_store') and dialogue.vector_store:
            self.conversation_data["metadata"]["pdf_context"] = "LimitationsofTranshumanism.pdf"
    
    def add_message(self, speaker_id, speaker_role, message, stage, turn_count, response_time=None):
        """대화 메시지 추가"""
        message_data = {
            "turn": turn_count,
            "timestamp": datetime.now().isoformat(),
            "speaker_id": speaker_id,
            "speaker_role": speaker_role,
            "stage": stage,
            "message": message,
            "response_time": response_time,
            "strategies": self._extract_strategy_info(speaker_id, stage)
        }
        
        self.conversation_data["conversation"].append(message_data)
    
    def _extract_strategy_info(self, speaker_id, stage):
        """전략 정보 추출 (해당 에이전트에서)"""
        strategy_info = {
            "attack_strategy": None,
            "defense_strategy": None,
            "rag_used": False,
            "rag_score": None,
            "emotion_state": None
        }
        
        # 실제 구현에서는 에이전트에서 전략 정보를 가져와야 함
        # 현재는 간단한 예시로 대체
        if "interactive_argument" in stage and speaker_id in ["nietzsche", "marx"]:
            strategy_info["attack_strategy"] = "Estimated Strategy"
            strategy_info["rag_used"] = True
            strategy_info["rag_score"] = 0.5
        
        return strategy_info
    
    def finalize(self, dialogue):
        """데이터 수집 완료 및 성능 메트릭 추가"""
        end_time = time.time()
        self.conversation_data["metadata"]["end_time"] = datetime.now().isoformat()
        self.conversation_data["metadata"]["total_duration"] = end_time - self.start_time
        
        # 성능 메트릭
        try:
            self.conversation_data["performance_metrics"] = dialogue.get_performance_metrics()
        except:
            self.conversation_data["performance_metrics"] = {"error": "Could not extract performance metrics"}
    
    def save_to_json(self, filename):
        """JSON 파일로 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 대화 데이터가 {filename}에 저장되었습니다.")

def create_transhumanism_debate_data():
    """트랜스휴머니즘 토론 데이터 생성 - 니체 vs 마르크스"""
    
    # PDF 파일 경로 (절대 경로로 설정)
    pdf_path = os.path.join(project_root, "sapiens_engine", "context_files", "LimitationsofTranshumanism.pdf")
    
    return {
        'title': '트랜스휴머니즘: 인간의 도약인가 종말인가?',
        'context': pdf_path,  # PDF 파일 경로를 컨텍스트로 사용
        'dialogueType': 'debate',
        'participants': {
            'pro': {
                'character_id': 'nietzsche',
                'philosopher_key': 'nietzsche',
                'name': '프리드리히 니체',
                'personality': 'passionate',
                'style': 'provocative',
                'argumentation_style': 'philosophical'
            },
            'con': {
                'character_id': 'marx',
                'philosopher_key': 'marx', 
                'name': '칼 마르크스',
                'personality': 'analytical',
                'style': 'systematic',
                'argumentation_style': 'materialist'
            }
        },
        'moderator': {
            'agent_id': 'moderator_001',
            'name': 'AI 모더레이터',
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

def test_transhumanism_debate_with_json():
    """트랜스휴머니즘 토론 테스트 실행 (JSON 출력 포함)"""
    
    print_header("트랜스휴머니즘 토론 테스트 - 니체 vs 마르크스 (JSON 출력)")
    
    # PDF 파일 존재 확인
    pdf_path = os.path.join(project_root, "sapiens_engine", "context_files", "LimitationsofTranshumanism.pdf")
    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return False
    
    print(f"✅ PDF 컨텍스트 파일 확인: {pdf_path}")
    
    # 데이터 수집기 초기화
    collector = DebateDataCollector()
    
    # 토론 데이터 생성
    room_data = create_transhumanism_debate_data()
    topic = room_data['title']
    
    print(f"\n👥 참가자:")
    print(f"   🟥 찬성 (PRO): 프리드리히 니체 - '초인' 철학으로 인간 향상 지지")
    print(f"   🟦 반대 (CON): 칼 마르크스 - 유물론적 관점에서 기술의 사회적 영향 비판")
    print(f"   🟨 모더레이터: AI 모더레이터")
    
    # 토론 대화 초기화
    print(f"\n🚀 토론 초기화 중...")
    start_time = time.time()
    
    try:
        dialogue = DebateDialogue(
            room_id="transhumanism_debate_json_001",
            room_data=room_data,
            use_async_init=False,
            enable_streaming=False
        )
        
        init_time = time.time() - start_time
        print(f"✅ 토론 초기화 완료 ({init_time:.2f}초)")
        
        # 데이터 수집 초기화
        collector.initialize(dialogue, topic)
        
        # 입장 진술문 확인
        print(f"\n📝 입장 진술문:")
        stance_statements = dialogue.stance_statements
        print(f"   🟥 찬성 (니체): {stance_statements.get('pro', 'N/A')}")
        print(f"   🟦 반대 (마르크스): {stance_statements.get('con', 'N/A')}")
        
        # 토론 진행
        print(f"\n🎭 토론 시작!")
        
        max_turns = 12  # 최대 턴 수 제한 (JSON 출력을 위해 적당히)
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
                current_stage = response.get("current_stage", "unknown")
                speaker_role = next_speaker_info.get("role", "unknown")
                
                print_message(speaker, message)
                print(f"   ⏱️ 응답 시간: {response_time:.2f}초")
                
                # 현재 단계 표시
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
                
                # 데이터 수집
                collector.add_message(
                    speaker_id=speaker,
                    speaker_role=speaker_role,
                    message=message,
                    stage=current_stage,
                    turn_count=turn_count,
                    response_time=response_time
                )
                
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
                time.sleep(0.5)  # 입론 단계
            elif current_stage == "interactive_argument":
                time.sleep(0.2)  # 상호논증 단계
            else:
                time.sleep(0.2)  # 기타 단계
        
        # 데이터 수집 완료
        collector.finalize(dialogue)
        
        # JSON 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"transhumanism_debate_{timestamp}.json"
        collector.save_to_json(json_filename)
        
        total_time = time.time() - start_time
        print(f"\n⏱️ 총 소요 시간: {total_time:.2f}초")
        print(f"📊 평균 턴당 시간: {total_time/turn_count:.2f}초")
        print(f"💾 JSON 파일: {json_filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ 토론 테스트 실패: {str(e)}")
        logger.error(f"Debate test error: {str(e)}", exc_info=True)
        return False

def main():
    """메인 함수"""
    print_header("트랜스휴머니즘 토론 테스트 (JSON 출력 포함)")
    
    # 토론 테스트 실행
    success = test_transhumanism_debate_with_json()
    
    if success:
        print(f"\n🎉 테스트 성공! JSON 파일이 생성되었습니다.")
        return True
    else:
        print(f"\n❌ 테스트 실패!")
        return False

if __name__ == "__main__":
    main() 