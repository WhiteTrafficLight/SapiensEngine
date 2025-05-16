import streamlit as st
import os
import time
import json
import openai
import random
import sys
import dotenv
from typing import List, Dict, Any, Optional
from pathlib import Path

# 환경 변수 불러오기 - .env.local 파일 우선 사용
dotenv.load_dotenv(".env.local")
dotenv.load_dotenv(".env")

# Sapiens Engine 모듈 경로 추가
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Sapiens Engine 모듈 임포트
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.dialogue import DialogueFactory
from sapiens_engine.dialogue.debate_dialogue import DebateDialogue
from sapiens_engine.dialogue.emotion_inference import infer_emotion_from_context, apply_emotion_to_prompt, EmotionManager

# Set page config
st.set_page_config(
    page_title="철학자 찬반토론 실험",
    page_icon="🧠",
    layout="wide"
)

# 설정 로더 및 LLM 매니저 초기화
config_loader = ConfigLoader()
llm_manager = LLMManager(config_loader)

# Check for OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key

# Philosopher data
PHILOSOPHERS = {
    "socrates": {"name": "소크라테스", "description": "Socrates was an Ancient Greek philosopher known for the Socratic method of questioning."},
    "plato": {"name": "플라톤", "description": "Plato was an Ancient Greek philosopher, student of Socrates, and founder of the Academy."},
    "aristotle": {"name": "아리스토텔레스", "description": "Aristotle was an Ancient Greek philosopher, student of Plato, known for empiricism and systematic knowledge."},
    "kant": {"name": "칸트", "description": "Kant was an 18th century German philosopher known for his work on ethics and metaphysics."},
    "nietzsche": {"name": "니체", "description": "Nietzsche was a 19th century German philosopher known for his critique of morality and religion."},
    "marx": {"name": "마르크스", "description": "Marx was a 19th century German philosopher, economist, and political theorist."},
    "sartre": {"name": "사르트르", "description": "Sartre was a 20th century French existentialist philosopher and writer."},
    "camus": {"name": "카뮈", "description": "Camus was a 20th century French philosopher associated with absurdism."},
    "beauvoir": {"name": "보부아르", "description": "Simone de Beauvoir was a 20th century French philosopher and feminist theorist."},
    "hegel": {"name": "헤겔", "description": "Hegel was a German philosopher known for his dialectical method of thinking."}
}

# 디버깅용 사이드바 설정
with st.sidebar:
    st.header("디버깅 정보")
    st.write(f"OpenAI API Key: {'설정됨' if openai_api_key else '설정 안됨'}")
    st.write(f"LLM Manager: {'초기화됨' if llm_manager else '초기화 안됨'}")
    
    # 상세 디버깅 토글
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = True
    
    st.session_state.debug_mode = st.checkbox("디버깅 모드", value=st.session_state.debug_mode)
    
    # 디버깅 로그 저장 공간 확보
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
        
    # 로그 클리어 버튼
    if st.button("로그 지우기"):
        st.session_state.debug_logs = []

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "debate_state" not in st.session_state:
    st.session_state.debate_state = {
        "topic": "",
        "context": "",
        "pro_side": [],
        "con_side": [],
        "user_side": None,
        "current_stage": "setup",  # setup, opening, pro_arguments, con_arguments, summary, rebuttal
        "speaking_history": [],
        "turn_index": 0,
        "generated_opening": "",
        "debate_complete": False,
        "waiting_for_user": False,
        "emotion_states": {}  # 참가자별 감정 상태 추적
    }

# 디베이트 인스턴스 저장
if "debate_instance" not in st.session_state:
    st.session_state.debate_instance = None

# EmotionManager 인스턴스 생성 (해당 위치에 추가)
if "emotion_manager" not in st.session_state:
    st.session_state.emotion_manager = None

# 사용자 입력 처리 플래그 추가
if "user_input_processed" not in st.session_state:
    st.session_state.user_input_processed = False

# Helper functions
def generate_moderator_opening(topic: str, context: str, pro_side: List[str], con_side: List[str]) -> str:
    """Generate a moderator opening statement for the debate using LLM Manager"""
    # Construct participants names
    pro_names = [PHILOSOPHERS[p]["name"] for p in pro_side if p in PHILOSOPHERS]
    con_names = [PHILOSOPHERS[p]["name"] for p in con_side if p in PHILOSOPHERS]
    
    # Add user if present
    if st.session_state.debate_state["user_side"] == "pro":
        pro_names.append("당신")
    elif st.session_state.debate_state["user_side"] == "con":
        con_names.append("당신")
    
    system_prompt = """
    당신은 전문적인 토론 진행자입니다. 주어진 주제에 대한 찬반토론의 시작 멘트를 작성해 주세요.
    한국어로 자연스럽게 토론을 소개하고, 참가자들을 소개하며, 토론의 규칙을 간략히 설명해 주세요.
    찬성과 반대 입장을 명확하게 제시하고, 첫 번째 발언자(찬성측)를 지명해 주세요.
    """
    
    user_prompt = f"""
    토론 주제: {topic}
    
    배경 정보: {context if context else "별도 배경 정보 없음"}
    
    찬성측 참가자: {', '.join(pro_names)}
    반대측 참가자: {', '.join(con_names)}
    
    첫 번째 발언자: {pro_names[0] if pro_names else '찬성측 발언자'}
    
    토론 진행자로서 위 정보를 바탕으로 토론을 시작하는 멘트를 작성해 주세요.
    """
    
    opening_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    return opening_text

def generate_philosopher_argument_with_emotion(
    philosopher_id: str, 
    topic: str, 
    context: str, 
    side: str, 
    debate_history: List[Dict],
    use_emotion: bool = False
) -> str:
    """감정 추론을 사용한 철학자 발언 생성"""
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher"})
    
    # 대화 이력을 텍스트로 변환
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    # 기본 프롬프트 로드
    system_prompt = f"""
    당신은 철학자 {philosopher['name']}입니다. {philosopher['description']}
    
    당신은 주어진 토론 주제에 대해 {side}측 입장을 가지고 있습니다.
    철학자로서 당신의 철학적 배경, 사상, 방법론을 반영하여 토론에 참여하세요.
    
    발언 시 다음 사항을 고려하세요:
    1. 당신의 철학적 관점과 일관된 주장을 펼치세요.
    2. 구체적인 예시나 비유를 활용하여 설득력을 높이세요.
    3. 논리적 구조를 갖추고, 핵심 논점을 명확히 제시하세요.
    4. 이전 발언자의 주장에 적절히 대응하고, 필요시 반박하세요.
    5. 당신의 고유한 철학적 용어나 개념을 적절히 활용하세요.
    """
    
    user_prompt = f"""
    토론 주제: {topic}
    배경 정보: {context if context else "별도 배경 정보 없음"}
    
    당신의 입장: {side}측 ({"찬성" if side == "pro" else "반대"})
    
    이전 토론 내용:
    {history_text}
    
    당신({philosopher['name']})의 차례입니다. {"찬성" if side == "pro" else "반대"} 입장에서 설득력 있는 주장을 펼치세요.
    """
    
    # 반박 단계에서 감정 추론 활성화
    if use_emotion and st.session_state.debate_state["current_stage"] in ["rebuttal", "cross_examination"]:
        try:
            # 최근 3-5개 메시지만 사용
            recent_history = debate_history[-5:] if len(debate_history) > 5 else debate_history
            
            # EmotionManager 초기화
            if st.session_state.emotion_manager is None:
                st.session_state.emotion_manager = EmotionManager(llm_manager)
                print("EmotionManager 초기화 성공")
                
            # 감정 추론 (간단한 폴백 메커니즘 사용)
            fallback_emotion = f"""
            이 토론은 점점 열기를 띠고 있습니다. 당신({philosopher['name']})은 상대측의 주장에 대해 감정적 반응을 보일 수 있습니다.
            
            상대방의 주장에 대해 다음과 같은 감정을 표현하세요:
            - 상대방의 논리적 오류에 대한 실망이나 당혹감
            - 상대방의 주장이 가져올 결과에 대한 우려나 경계심
            - 당신의 철학적 가치가 훼손될 때의 방어적 태도
            
            단, 감정을 표현할 때도 철학자로서의 논리성과 품위는 유지하세요.
            철학적 웅변과 수사적 표현을 사용하여 감정을 효과적으로 전달하세요.
            """
            
            system_prompt += f"\n\n{fallback_emotion}"
                
        except Exception as e:
            print(f"감정 추론 과정에서 오류 발생: {str(e)}")
    
    # LLM 호출하여 응답 생성
    return llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

def generate_moderator_summary(topic: str, debate_history: List[Dict]) -> str:
    """Generate a moderator summary of the debate using LLM Manager"""
    # Format debate history
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = """
    당신은 전문적인 토론 진행자입니다. 방금 진행된 찬반토론의 주요 내용을 요약해 주세요.
    각 측의 주요 주장과 논점을 객관적으로 정리하고, 토론의 결론을 중립적으로 제시해 주세요.
    """
    
    user_prompt = f"""
    토론 주제: {topic}
    
    토론 내용:
    {history_text}
    
    위 토론의 주요 내용과 각 측의 핵심 주장을 요약해 주세요. 중립적인 관점에서 토론의 주요 쟁점과 결론을 정리해 주세요.
    """
    
    summary_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    return summary_text

def initialize_debate_instance():
    """Initialize the debate dialogue instance using the Sapiens Engine modules"""
    # Room 데이터 구성
    room_data = {
        "id": "streamlit_debate",
        "title": st.session_state.debate_state["topic"],
        "context": st.session_state.debate_state["context"],
        "dialogueType": "debate",
        "pro": st.session_state.debate_state["pro_side"].copy(),
        "con": st.session_state.debate_state["con_side"].copy(),
        "participants": {
            "users": ["User123"],
            "npcs": st.session_state.debate_state["pro_side"] + st.session_state.debate_state["con_side"]
        }
    }
    
    # 사용자를 참여자에 추가
    if st.session_state.debate_state["user_side"] == "pro":
        room_data["pro"].append("User123")
    elif st.session_state.debate_state["user_side"] == "con":
        room_data["con"].append("User123")
    
    # DebateDialogue 인스턴스 생성
    debate_instance = DebateDialogue("streamlit_debate", room_data)
    
    # 세션 상태에 저장
    st.session_state.debate_instance = debate_instance
    
    if st.session_state.debug_mode:
        st.sidebar.write("Debate Instance 초기화 완료")
        st.sidebar.write(f"Pro: {room_data['pro']}")
        st.sidebar.write(f"Con: {room_data['con']}")

    # stages 설정 추가
    if st.session_state.debate_instance:
        # 단계 확장 (반박 단계 추가)
        st.session_state.debate_instance.stages = ["opening", "pro_arguments", "con_arguments", "summary", "rebuttal", "rebuttal_summary", "cross_examination", "closing_summary"]

def add_message(speaker_id: str, speaker_name: str, text: str, side: str = None, is_moderator: bool = False, is_user: bool = False):
    """Add a message to the debate history"""
    message = {
        "speaker_id": speaker_id,
        "speaker_name": speaker_name,
        "text": text,
        "side": side,
        "is_moderator": is_moderator,
        "is_user": is_user,
        "timestamp": time.time(),
        "current_stage": st.session_state.debate_state["current_stage"]  # 현재 단계 저장
    }
    
    st.session_state.messages.append(message)
    st.session_state.debate_state["speaking_history"].append(message)
    
    # 사용자 입력인 경우 처리 플래그 업데이트
    if is_user:
        if "user_input_processed" not in st.session_state:
            st.session_state.user_input_processed = False
        st.session_state.user_input_processed = True
        # 사용자 차례가 아님을 명시적으로 설정
        st.session_state.debate_state["waiting_for_user"] = False
        
        # 디버깅 정보 출력
        print(f"사용자 메시지 추가됨 - side: {side}")
        print(f"user_input_processed: {st.session_state.user_input_processed}")
        print(f"waiting_for_user: {st.session_state.debate_state['waiting_for_user']}")
        
        if st.session_state.debug_mode:
            log_debug("사용자 메시지 추가됨", "👤")
            log_debug(f"waiting_for_user: {st.session_state.debate_state['waiting_for_user']}")
        
        # 현재 단계가 완료되었는지 검사 (로그용)
        current_stage = st.session_state.debate_state["current_stage"]
        if current_stage == "con_arguments":
            # 모든 반대측 발언이 끝났는지 확인
            all_con_spoke = check_all_speakers_spoke("con")
            if all_con_spoke and side == "con":
                print("사용자가 마지막 반대측 발언자 - 다음 버튼 클릭 시 요약 단계로 진행 예정")
        elif current_stage == "pro_arguments":
            # 모든 찬성측 발언이 끝났는지 확인
            all_pro_spoke = check_all_speakers_spoke("pro")
            if all_pro_spoke and side == "pro":
                print("사용자가 마지막 찬성측 발언자 - 다음 버튼 클릭 시 반대측 입론 단계로 진행 예정")
    
    # 디베이트 인스턴스가 존재하고 스피킹 히스토리 업데이트가 필요하면 업데이트
    if st.session_state.debate_instance and not is_moderator:
        # 디베이트 인스턴스의 스피킹 히스토리 업데이트
        speaker_info = {
            "speaker_id": speaker_id,
            "role": side,
            "timestamp": time.time(),
            "stage": st.session_state.debate_instance.debate_state.get("current_stage", "opening")
        }
        
        st.session_state.debate_instance.debate_state["speaking_history"].append(speaker_info)
        st.session_state.debate_instance.debate_state["turn_count"] += 1
        
        # 사용자 발언이면 turn_index도 업데이트
        if is_user:
            st.session_state.debate_instance._check_stage_transition()
            if st.session_state.debug_mode:
                log_debug("디베이트 인스턴스 단계 전환 확인", "🔄")
    
    if st.session_state.debug_mode:
        log_debug(f"메시지 추가: {speaker_name} ({side if side else '중립'})", "💬")
    
    return message

def get_next_speaker() -> Optional[Dict]:
    """Get the next speaker based on the debate instance or fallback to stateful logic"""
    debate_state = st.session_state.debate_state
    
    # 디버깅을 위한 프린트문 추가
    print("\n==== get_next_speaker 함수 시작 ====")
    print(f"현재 단계: {debate_state['current_stage']}")
    print(f"현재 턴: {debate_state['turn_index']}")
    print(f"waiting_for_user: {debate_state['waiting_for_user']}")
    
    # If waiting for user input
    if debate_state["waiting_for_user"]:
        if st.session_state.debug_mode:
            log_debug("이미 사용자 입력 대기 중이므로 발언자 없음", "🔒")
        print("이미 사용자 입력 대기 중이므로 None 반환")
        return None
    
    # 사용자 입력이 처리되었는지 체크
    user_input_processed = getattr(st.session_state, 'user_input_processed', False)
    print(f"사용자 입력 처리 여부: {user_input_processed}")
    
    # 요약 단계 - 모더레이터 발언 (여기서는 다음 버튼 클릭 시만 처리하도록 변경)
    if debate_state['current_stage'] == "summary":
        print("요약 단계 - 다음 버튼 클릭 시 모더레이터 요약 생성")
        
    # 반박 요약 단계는 무조건 모더레이터가 처리
    elif debate_state['current_stage'] == "rebuttal_summary":
        print("반박 요약 단계 - 모더레이터 반환")
        return {
            "speaker_id": "moderator",
            "speaker_name": "진행자",
            "is_moderator": True,
            "is_user": False,
            "side": "neutral"
        }
    
    # 디베이트 인스턴스가 있으면 사용
    if st.session_state.debate_instance:
        try:
            next_speaker_info = st.session_state.debate_instance.get_next_speaker()
            
            if st.session_state.debug_mode:
                log_debug("다음 발언자 (디베이트 인스턴스):", "🎯")
                if next_speaker_info:
                    log_debug(f"- ID: {next_speaker_info.get('speaker_id', 'Unknown')}", "🔹")
                    log_debug(f"- 역할: {next_speaker_info.get('role', 'Unknown')}", "🔹")
            
            # 유효한 데이터 확인
            if not next_speaker_info or not isinstance(next_speaker_info, dict):
                if st.session_state.debug_mode:
                    log_debug(f"유효하지 않은 next_speaker_info: {next_speaker_info}", "⚠️")
                    log_debug("인스턴스 정보 없음. 폴백 로직 사용", "⚠️")
            else:
                speaker_id = next_speaker_info.get("speaker_id")
                role = next_speaker_info.get("role")
                is_user = speaker_id == "User123"
                
                # 모더레이터 확인
                if role == "moderator":
                    if st.session_state.debug_mode:
                        log_debug("모더레이터 선택됨 (인스턴스)", "👉")
                    return {
                        "speaker_id": "moderator",
                        "speaker_name": "진행자",
                        "is_moderator": True,
                        "is_user": False,
                        "side": "neutral"
                    }
                
                # 사용자 확인
                if is_user:
                    # 사용자 차례
                    if st.session_state.debug_mode:
                        log_debug("사용자 선택됨 (인스턴스)", "👉")
                    return {
                        "speaker_id": "user",
                        "speaker_name": "당신",
                        "side": role,
                        "is_user": True,
                        "is_moderator": False
                    }
                
                # NPC 확인
                if speaker_id in PHILOSOPHERS:
                    if st.session_state.debug_mode:
                        log_debug(f"철학자 선택됨 (인스턴스): {speaker_id}", "👉")
                    return {
                        "speaker_id": speaker_id,
                        "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                        "side": role,
                        "is_user": False,
                        "is_moderator": False
                    }
                
                # 모더레이터 요약 단계로 진행
                if role == "summary":
                    if st.session_state.debug_mode:
                        log_debug("요약 단계 모더레이터 선택됨 (인스턴스)", "👉")
                    return {
                        "speaker_id": "moderator",
                        "speaker_name": "진행자",
                        "is_moderator": True,
                        "is_user": False,
                        "side": "neutral"
                    }
        except Exception as e:
            if st.session_state.debug_mode:
                log_debug(f"인스턴스에서 다음 발언자 가져오기 오류: {str(e)}", "❌")
    
    # 폴백 로직: 기존 방식으로 다음 발언자 결정
    if st.session_state.debug_mode:
        log_debug("폴백 로직으로 다음 발언자 결정", "🔄")
        
    current_stage = debate_state["current_stage"]
    turn_index = debate_state["turn_index"]
    
    # 기존 단계들 처리
    if current_stage == "opening":
        # 자동 전환하지 않고 다음 버튼으로만 전환하도록 수정
        print("오프닝 단계 - 다음 버튼 클릭 시 찬성측 입론으로 전환")
        # 철학자 발언만 생성
        if debate_state["pro_side"]:
            speaker_id = debate_state["pro_side"][0]
            return {
                "speaker_id": speaker_id,
                "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                "side": "pro",
                "is_user": False,
                "is_moderator": False
            }
        else:
            # 사용자가 찬성측에 있는 경우
            return {
                "speaker_id": "user",
                "speaker_name": "당신",
                "side": "pro",
                "is_user": True,
                "is_moderator": False
            }
    
    elif current_stage == "pro_arguments":
        pro_side = debate_state["pro_side"]
        
        # 디버깅 정보
        if st.session_state.debug_mode:
            log_debug(f"찬성측 로직: 현재 턴 {turn_index}, 찬성측 인원 {len(pro_side)}명", "🔍")
            pro_speakers = [msg.get("speaker_id") for msg in debate_state["speaking_history"] 
                          if msg.get("side") == "pro" and msg.get("speaker_id") != "user"]
            user_spoke = any(msg.get("is_user", False) for msg in debate_state["speaking_history"] 
                           if msg.get("side") == "pro")
            log_debug(f"찬성측 발언자: {pro_speakers}", "🔍")
            log_debug(f"사용자(찬성측) 발언: {user_spoke}", "🔍")
            print(f"찬성측 발언자 목록: {pro_speakers}")
            print(f"찬성측 발언자 수: {len(set(pro_speakers))}/{len(pro_side)}")
        
        # 모든 찬성측 발언자가 발언했는지 확인
        pro_speakers = set(msg.get("speaker_id") for msg in debate_state["speaking_history"] 
                         if msg.get("side") == "pro" and msg.get("speaker_id") != "user")
        user_spoke = any(msg.get("is_user", False) for msg in debate_state["speaking_history"] 
                       if msg.get("side") == "pro")
        
        all_pro_spoke = (len(pro_speakers) >= len(pro_side)) and (debate_state["user_side"] != "pro" or user_spoke)
        
        # 모든 찬성측이 발언한 경우, 자동으로 단계 전환하지 않음
        if all_pro_spoke:
            if debate_state["user_side"] == "pro" and not user_spoke:
                debate_state["waiting_for_user"] = True
                if st.session_state.debug_mode:
                    log_debug("사용자(찬성측) 차례", "👉")
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": "pro",
                    "is_user": True,
                    "is_moderator": False
                }
            else:
                print("모든 찬성측 발언 완료 - 다음 버튼 클릭 시 반대측 입론으로 전환 가능")
                return None
        
        # 아직 발언하지 않은 찬성측 발언자 선택
        remaining_speakers = [spk for spk in pro_side if spk not in pro_speakers]
        if remaining_speakers:
            speaker_id = remaining_speakers[0]
        else:
            speaker_id = pro_side[turn_index % len(pro_side)]
        
        debate_state["turn_index"] += 1
        
        if st.session_state.debug_mode:
            log_debug(f"다음 찬성측 발언자: {speaker_id}", "👉")
        
        print(f"찬성측 발언자 반환: {speaker_id}")
        return {
            "speaker_id": speaker_id,
            "speaker_name": PHILOSOPHERS[speaker_id]["name"],
            "side": "pro",
            "is_user": False,
            "is_moderator": False
        }
    
    elif current_stage == "con_arguments":
        con_side = debate_state["con_side"]
        
        # 디버깅 정보
        if st.session_state.debug_mode:
            log_debug(f"반대측 로직: 현재 턴 {turn_index}, 반대측 인원 {len(con_side)}명", "🔍")
            con_speakers = [msg.get("speaker_id") for msg in debate_state["speaking_history"] 
                          if msg.get("side") == "con" and msg.get("speaker_id") != "user"]
            user_spoke = any(msg.get("is_user", False) for msg in debate_state["speaking_history"] 
                           if msg.get("side") == "con")
            log_debug(f"반대측 발언자: {con_speakers}", "🔍")
            log_debug(f"사용자(반대측) 발언: {user_spoke}", "🔍")
            print(f"반대측 발언자 목록: {con_speakers}")
            print(f"반대측 발언자 수: {len(set(con_speakers))}/{len(con_side)}")
        
        # 모든 반대측 발언자가 발언했는지 확인
        con_speakers = set(msg.get("speaker_id") for msg in debate_state["speaking_history"] 
                         if msg.get("side") == "con" and msg.get("speaker_id") != "user")
        user_spoke = any(msg.get("is_user", False) for msg in debate_state["speaking_history"] 
                       if msg.get("side") == "con")
        
        all_con_spoke = (len(con_speakers) >= len(con_side)) and (debate_state["user_side"] != "con" or user_spoke)
        print(f"모든 반대측 발언 여부: {all_con_spoke} (발언자 수: {len(con_speakers)}, 필요 수: {len(con_side)})")
        
        # 모든 반대측이 발언한 경우, 자동으로 단계 전환하지 않음 
        if all_con_spoke:
            # 유저가 반대측의 마지막 발언자인지 확인
            if debate_state["user_side"] == "con" and not user_spoke:
                debate_state["waiting_for_user"] = True
                if st.session_state.debug_mode:
                    log_debug("사용자(반대측) 차례", "👉")
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": "con",
                    "is_user": True,
                    "is_moderator": False
                }
            else:
                print("모든 반대측 발언 완료 - 다음 버튼 클릭 시 요약 단계로 전환 가능")
                return None
        
        # 아직 발언하지 않은 반대측 발언자 선택
        remaining_speakers = [spk for spk in con_side if spk not in con_speakers]
        if remaining_speakers:
            speaker_id = remaining_speakers[0]
        else:
            speaker_id = con_side[turn_index % len(con_side)]
        
        debate_state["turn_index"] += 1
        
        if st.session_state.debug_mode:
            log_debug(f"다음 반대측 발언자: {speaker_id}", "👉")
        
        print(f"반대측 발언자 반환: {speaker_id}")
        return {
            "speaker_id": speaker_id,
            "speaker_name": PHILOSOPHERS[speaker_id]["name"],
            "side": "con",
            "is_user": False,
            "is_moderator": False
        }
    
    elif current_stage == "summary":
        # 요약 단계에서는 다음 버튼을 통해서만 진행
        print("요약 단계 - 다음 버튼 클릭 시 모더레이터 요약 생성")
        return None
    
    elif current_stage == "rebuttal":
        # 디버깅 정보
        if st.session_state.debug_mode:
            log_debug(f"반박 단계 로직: 현재 턴 {turn_index}", "🔄")
            pro_rebuttals = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                           if msg.get("side") == "pro" and msg.get("speaker_id") != "user"]
            con_rebuttals = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                           if msg.get("side") == "con" and msg.get("speaker_id") != "user"]
            user_pro_rebuttal = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                                  if msg.get("side") == "pro")
            user_con_rebuttal = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                                  if msg.get("side") == "con")
            
            log_debug(f"찬성측 반박자: {pro_rebuttals}", "🔍")
            log_debug(f"반대측 반박자: {con_rebuttals}", "🔍")
            log_debug(f"사용자 찬성 반박: {user_pro_rebuttal}", "🔍")
            log_debug(f"사용자 반대 반박: {user_con_rebuttal}", "🔍")
        
        # 반박 단계 시작 시점 찾기
        rebuttal_start_idx = 0
        for i, msg in enumerate(st.session_state.debate_state["speaking_history"]):
            if msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
                rebuttal_start_idx = i
                break
        
        # 반박 단계 이후의 메시지만 필터링
        rebuttal_messages = st.session_state.debate_state["speaking_history"][rebuttal_start_idx:]
        
        # 반박 단계에서 발언한 사람들 확인
        pro_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                          if msg.get("side") == "pro" and msg.get("speaker_id") != "user" 
                          and not msg.get("is_moderator", False))
        con_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                          if msg.get("side") == "con" and msg.get("speaker_id") != "user"
                          and not msg.get("is_moderator", False))
        
        user_pro_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                            if msg.get("side") == "pro")
        user_con_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                            if msg.get("side") == "con")
        
        # 디버깅 정보 출력
        print(f"\n==== 반박 단계 상태 확인 ====")
        print(f"찬성측 반박자 수: {len(pro_rebuttals)}/{len(st.session_state.debate_state['pro_side'])}")
        print(f"반대측 반박자 수: {len(con_rebuttals)}/{len(st.session_state.debate_state['con_side'])}")
        print(f"사용자 찬성측: {st.session_state.debate_state['user_side'] == 'pro'}, 사용자 찬성 반박: {user_pro_rebuttal}")
        print(f"사용자 반대측: {st.session_state.debate_state['user_side'] == 'con'}, 사용자 반대 반박: {user_con_rebuttal}")
        print(f"===============================\n")
        
        # 모든 반박이 완료되었는지 확인
        all_pro_rebuttals = (len(pro_rebuttals) >= len(st.session_state.debate_state["pro_side"])) and (st.session_state.debate_state["user_side"] != "pro" or user_pro_rebuttal)
        all_con_rebuttals = (len(con_rebuttals) >= len(st.session_state.debate_state["con_side"])) and (st.session_state.debate_state["user_side"] != "con" or user_con_rebuttal)
        
        # 1. 찬성측 반론 먼저 진행
        if not all_pro_rebuttals:
            # 사용자가 찬성측이고 아직 반론하지 않았다면
            if st.session_state.debate_state["user_side"] == "pro" and not user_pro_rebuttal:
                st.session_state.debate_state["waiting_for_user"] = True
                print("사용자(찬성측) 반론 차례")
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": "pro",
                    "is_user": True,
                    "is_moderator": False
                }
            
            # 찬성측 NPC 중 아직 반론하지 않은 사람 선택
            remaining_pro_speakers = [spk for spk in st.session_state.debate_state["pro_side"] if spk not in pro_rebuttals]
            if remaining_pro_speakers:
                speaker_id = remaining_pro_speakers[0]
                st.session_state.debate_state["turn_index"] += 1
                print(f"찬성측 NPC({speaker_id}) 반론 차례")
                return {
                    "speaker_id": speaker_id,
                    "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                    "side": "pro",
                    "is_user": False,
                    "is_moderator": False
                }
        
        # 2. 찬성측 반론이 모두 끝난 후 반대측 반론 진행
        elif all_pro_rebuttals and not all_con_rebuttals:
            # 사용자가 반대측이고 아직 반론하지 않았다면
            if st.session_state.debate_state["user_side"] == "con" and not user_con_rebuttal:
                st.session_state.debate_state["waiting_for_user"] = True
                print("사용자(반대측) 반론 차례")
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": "con",
                    "is_user": True,
                    "is_moderator": False
                }
            
            # 반대측 NPC 중 아직 반론하지 않은 사람 선택
            remaining_con_speakers = [spk for spk in st.session_state.debate_state["con_side"] if spk not in con_rebuttals]
            if remaining_con_speakers:
                speaker_id = remaining_con_speakers[0]
                st.session_state.debate_state["turn_index"] += 1
                print(f"반대측 NPC({speaker_id}) 반론 차례")
                return {
                    "speaker_id": speaker_id,
                    "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                    "side": "con",
                    "is_user": False,
                    "is_moderator": False
                }
    
    elif current_stage == "rebuttal_summary":
        # 반박 요약 단계 - 모더레이터가 담당
        print("반박 요약 단계 - 모더레이터 반환")
        return {
            "speaker_id": "moderator",
            "speaker_name": "진행자",
            "is_moderator": True,
            "is_user": False,
            "side": "neutral"
        }
    
    elif current_stage == "cross_examination":
        # 상호질문 단계 로직
        print("상호질문 단계 - 발언자 선택 로직")
        
        # 버튼 대기 상태인 경우
        if st.session_state.debate_state.get("waiting_for_button", False):
            print("발언권 버튼 대기 중")
            return None
            
        # 사용자가 버튼을 눌렀을 경우
        if st.session_state.debate_state.get("user_pressed_button", False):
            st.session_state.debate_state["waiting_for_user"] = True
            st.session_state.debate_state["user_pressed_button"] = False  # 플래그 리셋
            print("사용자가 발언권 획득")
            
            # 사용자 측 반대편에서 타겟 선택
            user_side = st.session_state.debate_state["user_side"]
            target_side = "con" if user_side == "pro" else "pro"
            target_candidates = st.session_state.debate_state[f"{target_side}_side"]
            
            if target_candidates:
                target_id = random.choice(target_candidates)
                print(f"사용자({user_side}측)가 {target_id}({target_side}측)에게 질문")
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": user_side,
                    "is_user": True,
                    "is_moderator": False,
                    "target_speaker": target_id
                }
            else:
                # 타겟이 없는 경우 일반 발언으로 처리
                return {
                    "speaker_id": "user",
                    "speaker_name": "당신",
                    "side": user_side,
                    "is_user": True,
                    "is_moderator": False
                }
            
        # 현재 진행 중인 대화 확인
        current_speakers = st.session_state.debate_state.get("current_speakers", [])
        cross_exam_round = st.session_state.debate_state.get("cross_exam_round", 0)
        
        # 새로운 대화 시작 (발언권 버튼 타이머 종료 후 또는 첫 발언)
        if not current_speakers:
            # 랜덤하게 질문자 선택 (pro/con 중에서)
            sides = ["pro", "con"]
            questioner_side = random.choice(sides)
            
            if questioner_side == "pro":
                if st.session_state.debate_state["pro_side"]:
                    questioner_id = random.choice(st.session_state.debate_state["pro_side"])
                    responder_id = random.choice(st.session_state.debate_state["con_side"]) if st.session_state.debate_state["con_side"] else None
                else:
                    questioner_side = "con"
                    questioner_id = random.choice(st.session_state.debate_state["con_side"]) if st.session_state.debate_state["con_side"] else None
                    responder_id = None
            else:  # con side
                if st.session_state.debate_state["con_side"]:
                    questioner_id = random.choice(st.session_state.debate_state["con_side"])
                    responder_id = random.choice(st.session_state.debate_state["pro_side"]) if st.session_state.debate_state["pro_side"] else None
                else:
                    questioner_side = "pro"
                    questioner_id = random.choice(st.session_state.debate_state["pro_side"]) if st.session_state.debate_state["pro_side"] else None
                    responder_id = None
            
            # 선택된 질문자와 응답자 저장
            st.session_state.debate_state["current_speakers"] = [
                {"id": questioner_id, "side": questioner_side, "turns": 0},
                {"id": responder_id, "side": "pro" if questioner_side == "con" else "con", "turns": 0}
            ]
            
            # 질문자 반환
            print(f"새 대화 시작: {questioner_id}({questioner_side}) -> {responder_id}")
            return {
                "speaker_id": questioner_id,
                "speaker_name": PHILOSOPHERS[questioner_id]["name"],
                "side": questioner_side,
                "is_user": False,
                "is_moderator": False,
                "target_speaker": responder_id
            }
        
        # 현재 대화가 있는 경우, 다음 발언자 결정
        # 총 3-5턴의 대화 진행 (질문-응답-질문-응답-질문)
        total_turns = sum(speaker.get("turns", 0) for speaker in current_speakers)
        
        if total_turns >= 5:  # 대화가 충분히 진행됨
            # 모더레이터 중재 메시지로 전환
            print("충분한 대화 후 모더레이터 중재")
            return {
                "speaker_id": "moderator",
                "speaker_name": "진행자",
                "is_moderator": True,
                "is_user": False,
                "side": "neutral",
                "is_intervention": True
            }
        
        # 다음 발언자 선택 (번갈아가며)
        last_speaker_idx = 0 if current_speakers[1].get("turns", 0) > current_speakers[0].get("turns", 0) else 1
        next_speaker_idx = 1 - last_speaker_idx
        
        current_speakers[next_speaker_idx]["turns"] += 1
        next_speaker = current_speakers[next_speaker_idx]
        target_speaker = current_speakers[last_speaker_idx]
        
        print(f"다음 발언자: {next_speaker['id']}({next_speaker['side']}) -> {target_speaker['id']}")
        
        return {
            "speaker_id": next_speaker["id"],
            "speaker_name": PHILOSOPHERS[next_speaker["id"]]["name"],
            "side": next_speaker["side"],
            "is_user": False,
            "is_moderator": False,
            "target_speaker": target_speaker["id"]
        }
    
    elif current_stage == "closing_summary":
        # 최종 요약 단계 - 모더레이터가 담당
        print("최종 요약 단계 - 모더레이터 반환")
        return {
            "speaker_id": "moderator",
            "speaker_name": "진행자",
            "is_moderator": True,
            "is_user": False,
            "side": "neutral"
        }
    
    return None

def run_debate_step():
    """Run the next step in the debate"""
    if st.session_state.debate_state["debate_complete"]:
        return
    
    if st.session_state.debug_mode:
        log_debug(f"현재 단계: {st.session_state.debate_state['current_stage']}", "🔄")
        log_debug(f"현재 턴: {st.session_state.debate_state['turn_index']}", "🔄")
    
    if st.session_state.debate_state["current_stage"] == "setup":
        # 디베이트 인스턴스 초기화
        initialize_debate_instance()
        log_debug("디베이트 인스턴스 초기화 완료", "🏁")
        
        # Generate opening statement
        opening_text = generate_moderator_opening(
            st.session_state.debate_state["topic"],
            st.session_state.debate_state["context"],
            st.session_state.debate_state["pro_side"],
            st.session_state.debate_state["con_side"]
        )
        
        st.session_state.debate_state["generated_opening"] = opening_text
        add_message("moderator", "진행자", opening_text, is_moderator=True)
        log_debug("모더레이터 오프닝 생성 완료", "🎬")
        
        # Move to the next stage
        st.session_state.debate_state["current_stage"] = "opening"
        st.session_state.debate_state["turn_index"] = 0
    
    elif st.session_state.debate_state["waiting_for_user"]:
        # Waiting for user input - do nothing
        log_debug("사용자 입력 대기 중", "⏳")
        print("사용자 입력 대기 중 - waiting_for_user:", st.session_state.debate_state["waiting_for_user"])
        pass
    
    else:
        # 사용자 입력이 처리되었는지 확인 후 다음 단계로 진행
        if hasattr(st.session_state, 'user_input_processed') and st.session_state.user_input_processed:
            print("사용자 입력이 처리되었으므로 다음 단계 버튼이 표시됩니다")
            # 사용자 입력 처리 플래그는 유지 - 다음 버튼 클릭 시 초기화
            
            # 단계별 상태 확인 - 실제 전환은 다음 버튼 클릭 시 수행
            current_stage = st.session_state.debate_state["current_stage"]
            if current_stage == "opening":
                print("오프닝 단계 - 다음 버튼 클릭 시 pro_arguments로 진행 가능")
            elif current_stage == "pro_arguments":
                # 모든 찬성측 발언이 끝났는지 확인
                all_pro_spoke = check_all_speakers_spoke("pro")
                if all_pro_spoke:
                    print("모든 찬성측 발언 완료 - 다음 버튼 클릭 시 con_arguments 진행 가능")
            elif current_stage == "con_arguments":
                # 모든 반대측 발언이 끝났는지 확인
                all_con_spoke = check_all_speakers_spoke("con")
                if all_con_spoke:
                    print("모든 반대측 발언 완료 - 다음 버튼 클릭 시 summary 단계 진행 가능")
        
        # Get the next speaker
        next_speaker = get_next_speaker()
        
        # 디버깅을 위한 프린트문 추가
        print("\n==== 다음 발언자 정보 ====")
        print(f"next_speaker: {next_speaker}")
        if next_speaker:
            print(f"speaker_id: {next_speaker.get('speaker_id', 'None')}")
            print(f"speaker_name: {next_speaker.get('speaker_name', 'None')}")
            print(f"side: {next_speaker.get('side', 'None')}")
            print(f"is_moderator: {next_speaker.get('is_moderator', False)}")
            print(f"is_user: {next_speaker.get('is_user', False)}")
        print("========================\n")
        
        if st.session_state.debug_mode:
            log_debug("다음 발언자 정보:", "🔍")
            if next_speaker:
                log_debug(f"- 발언자: {next_speaker.get('speaker_name', 'Unknown')}", "👤")
                log_debug(f"- 역할: {next_speaker.get('side', 'Unknown')}", "🔹")
            log_debug(f"단계 확인: {st.session_state.debate_state['current_stage']}", "🔄")
        
        if not next_speaker:
            if st.session_state.debug_mode:
                log_debug("다음 발언자 정보가 없음, 상태를 초기화하거나 턴 재설정 필요", "⚠️")
            
            # 단계 전환이 필요한지 확인 - 여기서는 다음 버튼 클릭 시 처리하도록 변경
            current_stage = st.session_state.debate_state["current_stage"]
            if current_stage == "con_arguments":
                # 모든 반대측 발언이 끝났는지 확인 (로그용)
                all_con_spoke = check_all_speakers_spoke("con")
                if all_con_spoke:
                    print("모든 반대측 발언 완료 - 다음 버튼 클릭 시 요약 단계로 진행 가능")
            
            elif current_stage == "rebuttal":
                # 모든 반박이 끝났는지 확인 (로그용)
                all_rebuttals_complete = check_all_rebuttals_complete()
                if all_rebuttals_complete:
                    print("모든 반박 완료 - 다음 버튼 클릭 시 요약 단계로 진행 가능")
            
            return
        
        # 필수 필드 체크
        required_fields = ["speaker_id", "speaker_name", "is_user", "is_moderator"]
        for field in required_fields:
            if field not in next_speaker:
                if st.session_state.debug_mode:
                    log_debug(f"다음 발언자 정보에 필수 필드({field})가 없음", "⚠️")
                print(f"오류: 다음 발언자 정보에 필수 필드({field})가 없음")
                return
        
        # 모든 필드가 있는지 확인 - 안전하게 get()으로 접근
        is_user = next_speaker.get("is_user", False)
        is_moderator = next_speaker.get("is_moderator", False)
        
        if is_user:
            # 사용자 입력이 이미 처리되었는지 확인
            if not hasattr(st.session_state, 'user_input_processed') or not st.session_state.user_input_processed:
                # Wait for user input
                st.session_state.debate_state["waiting_for_user"] = True
                print(f"사용자 입력 대기 상태로 전환 - is_user: {is_user}, user_input_processed: {getattr(st.session_state, 'user_input_processed', None)}")
                if st.session_state.debug_mode:
                    log_debug("사용자 입력 대기 상태로 전환", "⏳")
            return
        
        if is_moderator:
            # 현재 stage에 따라 중재자 메시지 생성
            current_stage = st.session_state.debate_state["current_stage"]
            
            print(f"모더레이터 발언 처리 - 단계: {current_stage}")
            if st.session_state.debug_mode:
                log_debug(f"모더레이터 발언 - 단계: {current_stage}", "🎭")
            
            if current_stage == "summary":
                generate_summary_and_transition_to_rebuttal()
                return
            
            elif current_stage == "rebuttal_summary":
                print("반박 요약 단계 처리 시작")
                # 반박 단계 요약 생성
                try:
                    # 반박 단계 메시지만 필터링
                    rebuttal_messages = []
                    started_rebuttal = False
                    
                    for msg in st.session_state.debate_state["speaking_history"]:
                        if not started_rebuttal and msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
                            started_rebuttal = True
                        
                        if started_rebuttal and st.session_state.debate_state["current_stage"] != "rebuttal_summary":
                            rebuttal_messages.append(msg)
                    
                    print(f"반박 단계 메시지 수: {len(rebuttal_messages)}")
                    if len(rebuttal_messages) > 0:
                        rebuttal_summary = generate_moderator_summary(
                            st.session_state.debate_state["topic"],
                            rebuttal_messages
                        )
                    else:
                        # 반박 메시지가 없으면 기본 메시지 사용
                        rebuttal_summary = f"""
                        지금까지 양측의 반박을 주의 깊게 들어보았습니다. 
                        
                        찬성측과 반대측 모두 자신의 철학적 관점에서 상대방의 논점에 대해 비판적인 시각을 제시해 주셨습니다.
                        각 철학자들의 고유한 사상과 방법론이 반박 과정에서도 잘 드러났다고 생각합니다.
                        
                        이제 상호질문 단계를 통해 더 깊이 있는 토론으로 나아가 보겠습니다.
                        """
                    
                    add_message("moderator", "진행자", rebuttal_summary, is_moderator=True)
                    print("반박 요약 메시지 추가 완료")
                    
                    # 상호질문 단계로 전환
                    cross_examination_intro = f"""
                    이제 상호질문 단계로 넘어가겠습니다. 
                    
                    이 단계에서는 양측이 서로의 주장에 대해 자유롭게 질문하고 토론할 수 있습니다.
                    논리적인 오류나 약점을 지적하고, 서로의 관점을 더 깊이 탐구하는 시간이 될 것입니다.
                    
                    각자 상대측의 발언자를 지목하여 질문을 하거나 의견을 제시할 수 있습니다.
                    예의를 지키되, 철학적 깊이가 있는 토론이 되길 바랍니다.
                    
                    발언권을 얻고자 하는 분은 발언권 버튼을 눌러주세요.
                    5초 내에 아무도 버튼을 누르지 않으면, 자동으로 NPC에게 발언권이 넘어갑니다.
                    """
                    
                    add_message("moderator", "진행자", cross_examination_intro, is_moderator=True)
                    
                    # 상호질문 단계로 전환
                    st.session_state.debate_state["current_stage"] = "cross_examination"
                    st.session_state.debate_state["cross_exam_round"] = 0
                    st.session_state.debate_state["current_speakers"] = []
                    st.session_state.debate_state["timer_running"] = True
                    st.session_state.debate_state["waiting_for_button"] = True
                    print("상호질문 단계로 전환 완료")
                except Exception as e:
                    if st.session_state.debug_mode:
                        log_debug(f"반박 요약 생성 오류: {str(e)}", "❌")
                    print(f"반박 요약 생성 오류: {str(e)}")
                    # 오류 발생 시 기본 메시지 사용
                    fallback_message = """
                    지금까지 양측의 반박을 들어보았습니다. 흥미로운 논점들이 오갔습니다.
                    
                    이제 상호질문 단계로 넘어가 더 심도있는 토론을 이어가겠습니다.
                    발언권을 얻고자 하는 분은 발언권 버튼을 눌러주세요.
                    """
                    add_message("moderator", "진행자", fallback_message, is_moderator=True)
                    
                    # 상호질문 단계로 전환
                    st.session_state.debate_state["current_stage"] = "cross_examination"
                    st.session_state.debate_state["cross_exam_round"] = 0
                    st.session_state.debate_state["current_speakers"] = []
                    st.session_state.debate_state["timer_running"] = True
                    st.session_state.debate_state["waiting_for_button"] = True
                
                return
            
            elif current_stage == "cross_examination":
                # 모더레이터 중재 메시지
                if next_speaker.get("is_intervention", False):
                    intervention_text = generate_moderator_intervention()
                    add_message("moderator", "진행자", intervention_text, is_moderator=True)
                    st.session_state.debate_state["is_intervention"] = True
                    st.session_state.debate_state["waiting_for_button"] = True
                    st.session_state.debate_state["timer_running"] = True
                    return
            
            elif current_stage == "closing_summary":
                # 최종 요약 생성
                try:
                    closing_summary = generate_closing_summary(
                        st.session_state.debate_state["topic"],
                        st.session_state.debate_state["speaking_history"]
                    )
                    add_message("moderator", "진행자", closing_summary, is_moderator=True)
                    st.session_state.debate_state["debate_complete"] = True
                    print("토론 최종 요약 및 마무리 완료")
                    return
                except Exception as e:
                    if st.session_state.debug_mode:
                        log_debug("최종 요약 생성 오류", "❌")
                    print(f"최종 요약 생성 오류: {str(e)}")
                    fallback_summary = f"""
                    '{st.session_state.debate_state["topic"]}'에 관한 오늘의 토론은 매우 유익했습니다.
                    
                    양측 모두 철학적 깊이가 담긴 훌륭한 주장과 반박을 펼쳐주셨으며,
                    상호질문 단계에서는 더욱 심도 있는 논의가 이루어졌습니다.
                    
                    이 토론이 청중 여러분께 주제에 대한 다양한 철학적 관점을 제공했기를 바랍니다.
                    참여해 주신 모든 분들께 감사드립니다.
                    """
                    add_message("moderator", "진행자", fallback_summary, is_moderator=True)
                    st.session_state.debate_state["debate_complete"] = True
                    return
        
        # Generate philosopher's argument
        speaker_id = next_speaker.get("speaker_id", "")
        side = next_speaker.get("side", "neutral")
        
        print(f"철학자 발언 생성 시작 - speaker_id: {speaker_id}, side: {side}")
        
        # 상호질문 단계인 경우 질문/응답 생성 로직 사용
        if st.session_state.debate_state["current_stage"] == "cross_examination":
            target_speaker_id = next_speaker.get("target_speaker")
            
            if not target_speaker_id:
                print(f"오류: 대상 발언자 ID가 없음")
                return
                
            current_speakers = st.session_state.debate_state.get("current_speakers", [])
            
            # 첫 턴인지 확인 (질문인지 응답인지 판단)
            if len(current_speakers) >= 2 and current_speakers[0].get("turns", 0) > 0:
                # 상대방 질문에 대한 응답 생성
                response_text = generate_cross_examination_response(
                    next_speaker["speaker_id"],
                    target_speaker_id,
                    st.session_state.debate_state["topic"],
                    st.session_state.debate_state["speaking_history"]
                )
            else:
                # 첫 질문 생성
                response_text = generate_cross_examination_question(
                    next_speaker["speaker_id"],
                    target_speaker_id,
                    st.session_state.debate_state["topic"],
                    st.session_state.debate_state["speaking_history"]
                )
            
            add_message(
                next_speaker["speaker_id"],
                next_speaker["speaker_name"],
                response_text,
                side=side
            )
            return
        
        # 현재 단계에 따라 감정 추론 사용 여부 결정
        use_emotion = st.session_state.debate_state["current_stage"] in ["rebuttal", "cross_examination"]
        
        # 일반 발언/반박 생성
        argument_text = generate_philosopher_argument_with_emotion(
            speaker_id,
            st.session_state.debate_state["topic"],
            st.session_state.debate_state["context"],
            side,
            st.session_state.debate_state["speaking_history"],
            use_emotion=use_emotion
        )
        
        add_message(
            speaker_id,
            next_speaker["speaker_name"],
            argument_text,
            side=side
        )
        print(f"철학자({speaker_id}) 발언 추가 완료")

def log_debug(message: str, emoji: str = "ℹ️"):
    """디버깅 로그 추가"""
    if st.session_state.debug_mode:
        log_entry = f"{emoji} {message}"
        st.session_state.debug_logs.append(log_entry)
        st.sidebar.write(log_entry)

def display_debug_logs():
    """사이드바에 저장된 디버깅 로그 표시"""
    if st.session_state.debug_mode:
        with st.sidebar.expander("상세 로그", expanded=False):
            for log in st.session_state.debug_logs:
                st.write(log)

# UI Components
def setup_debate():
    st.title("철학자 찬반토론 실험")
    
    # 디버깅 로그 표시
    display_debug_logs()
    
    # Topic and context
    st.header("토론 설정")
    debate_topic = st.text_input("토론 주제", placeholder="예: 인공지능은 인간을 대체할 것인가?")
    debate_context = st.text_area("배경 설명 (선택사항)", placeholder="주제에 대한 배경 설명이나 추가 정보를 입력하세요.")
    
    # Philosopher selection
    st.subheader("철학자 선택")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 찬성측")
        pro_philosophers = []
        for philosopher_id, philosopher in PHILOSOPHERS.items():
            if st.checkbox(f"{philosopher['name']} (찬성)", key=f"pro_{philosopher_id}"):
                pro_philosophers.append(philosopher_id)
    
    with col2:
        st.markdown("#### 반대측")
        con_philosophers = []
        for philosopher_id, philosopher in PHILOSOPHERS.items():
            if philosopher_id in pro_philosophers:
                continue  # Skip if already selected for pro side
            if st.checkbox(f"{philosopher['name']} (반대)", key=f"con_{philosopher_id}"):
                con_philosophers.append(philosopher_id)
    
    # User participation
    st.subheader("사용자 참여")
    user_participation = st.radio(
        "토론에 참여하시겠습니까?",
        ["참여하지 않음", "찬성측으로 참여", "반대측으로 참여"],
        index=0
    )
    
    user_side = None
    if user_participation == "찬성측으로 참여":
        user_side = "pro"
    elif user_participation == "반대측으로 참여":
        user_side = "con"
    
    # Submit button
    if st.button("토론 시작", disabled=not debate_topic or (not pro_philosophers and user_side != "pro") or (not con_philosophers and user_side != "con")):
        st.session_state.debate_state = {
            "topic": debate_topic,
            "context": debate_context,
            "pro_side": pro_philosophers,
            "con_side": con_philosophers,
            "user_side": user_side,
            "current_stage": "setup",
            "speaking_history": [],
            "turn_index": 0,
            "generated_opening": "",
            "debate_complete": False,
            "waiting_for_user": False,
            "emotion_states": {}  # 참가자별 감정 상태 추적
        }
        
        st.session_state.messages = []
        st.session_state.debate_instance = None
        st.session_state.emotion_manager = None  # 감정 매니저도 초기화
        st.session_state.user_input_processed = False  # 사용자 입력 처리 플래그 초기화
        
        # Initialize the debate
        run_debate_step()
        
        st.rerun()  # experimental_rerun 대신 rerun 사용

def display_debate():
    st.title(f"토론 주제: {st.session_state.debate_state['topic']}")
    
    # 디버깅 로그 표시
    display_debug_logs()
    
    # 사이드바에 현재 토론 상태 표시
    if st.session_state.debug_mode:
        with st.sidebar:
            st.subheader("현재 토론 상태")
            
            stage_labels = {
                "setup": "준비",
                "opening": "오프닝",
                "pro_arguments": "찬성측 입론",
                "con_arguments": "반대측 입론",
                "summary": "입론 요약",
                "rebuttal": "반론",
                "rebuttal_summary": "반론 요약",
                "cross_examination": "상호질문",
                "closing_summary": "결론 요약"
            }
            
            current_stage = st.session_state.debate_state["current_stage"]
            stage_label = stage_labels.get(current_stage, current_stage)
            
            st.write(f"**현재 단계:** {stage_label}")
            st.write(f"**현재 턴:** {st.session_state.debate_state['turn_index']}")
            st.write(f"**사용자 입력 대기:** {'예' if st.session_state.debate_state['waiting_for_user'] else '아니오'}")
            
            # 발언자 정보 표시
            st.subheader("발언자 정보")
            
            # 입론 단계 발언자
            pro_speakers = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                         if msg.get("side") == "pro" and msg.get("speaker_id") != "user"]
            con_speakers = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                         if msg.get("side") == "con" and msg.get("speaker_id") != "user"]
            
            # 반박 단계 발언자
            pro_rebuttals = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                          if msg.get("side") == "pro" and msg.get("speaker_id") != "user" 
                          and "current_stage" in msg and msg.get("current_stage") == "rebuttal"]
            con_rebuttals = [msg.get("speaker_id") for msg in st.session_state.debate_state["speaking_history"] 
                          if msg.get("side") == "con" and msg.get("speaker_id") != "user"
                          and "current_stage" in msg and msg.get("current_stage") == "rebuttal"]
            
            # 사용자 발언 현황
            user_pro = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                        if msg.get("side") == "pro")
            user_con = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                        if msg.get("side") == "con")
            
            user_pro_rebuttal = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                               if msg.get("side") == "pro" 
                               and "current_stage" in msg and msg.get("current_stage") == "rebuttal")
            user_con_rebuttal = any(msg.get("is_user", False) for msg in st.session_state.debate_state["speaking_history"] 
                               if msg.get("side") == "con" 
                               and "current_stage" in msg and msg.get("current_stage") == "rebuttal")
            
            # 입론 현황 표시
            st.write("**찬성측 입론 현황:**")
            for speaker_id in st.session_state.debate_state["pro_side"]:
                if speaker_id in pro_speakers:
                    st.write(f"✅ {PHILOSOPHERS[speaker_id]['name']}")
                else:
                    st.write(f"❌ {PHILOSOPHERS[speaker_id]['name']}")
            
            if st.session_state.debate_state["user_side"] == "pro":
                if user_pro:
                    st.write("✅ 당신 (사용자)")
                else:
                    st.write("❌ 당신 (사용자)")
            
            st.write("**반대측 입론 현황:**")
            for speaker_id in st.session_state.debate_state["con_side"]:
                if speaker_id in con_speakers:
                    st.write(f"✅ {PHILOSOPHERS[speaker_id]['name']}")
                else:
                    st.write(f"❌ {PHILOSOPHERS[speaker_id]['name']}")
            
            if st.session_state.debate_state["user_side"] == "con":
                if user_con:
                    st.write("✅ 당신 (사용자)")
                else:
                    st.write("❌ 당신 (사용자)")
            
            # 단계 진행 정보
            st.subheader("단계 진행 상태")
            stages = ["opening", "pro_arguments", "con_arguments", "summary", "rebuttal", "rebuttal_summary", "cross_examination", "closing_summary"]
            for stage in stages:
                if stage == current_stage:
                    st.write(f"▶️ {stage_labels.get(stage, stage)} (현재)")
                elif stages.index(stage) < stages.index(current_stage):
                    st.write(f"✅ {stage_labels.get(stage, stage)} (완료)")
                else:
                    st.write(f"⏳ {stage_labels.get(stage, stage)} (대기)")
                    
            # 메시지 현황
            st.subheader("메시지 현황")
            st.write(f"총 메시지: {len(st.session_state.messages)}개")
            moderator_count = sum(1 for m in st.session_state.messages if m.get("is_moderator", False))
            user_count = sum(1 for m in st.session_state.messages if m.get("is_user", False))
            npc_count = len(st.session_state.messages) - moderator_count - user_count
            
            st.write(f"- 진행자: {moderator_count}개")
            st.write(f"- 사용자: {user_count}개")
            st.write(f"- 철학자: {npc_count}개")
    
    # Display debate information
    with st.expander("토론 정보", expanded=False):
        st.write(f"**주제:** {st.session_state.debate_state['topic']}")
        if st.session_state.debate_state['context']:
            st.write(f"**배경 정보:** {st.session_state.debate_state['context']}")
        
        st.write("**찬성측:**")
        for philosopher_id in st.session_state.debate_state["pro_side"]:
            st.write(f"- {PHILOSOPHERS[philosopher_id]['name']}")
        if st.session_state.debate_state["user_side"] == "pro":
            st.write("- 당신 (사용자)")
        
        st.write("**반대측:**")
        for philosopher_id in st.session_state.debate_state["con_side"]:
            st.write(f"- {PHILOSOPHERS[philosopher_id]['name']}")
        if st.session_state.debate_state["user_side"] == "con":
            st.write("- 당신 (사용자)")
    
    # Messages display
    st.header("토론 내용")
    
    for i, message in enumerate(st.session_state.messages):
        if message.get("is_moderator", False):
            with st.chat_message("assistant", avatar="🎭"):
                st.markdown(f"**{message['speaker_name']}**")
                # 긴 텍스트를 처리하기 위해 expander 사용하지 않고 직접 출력
                st.markdown(message["text"])
        elif message.get("is_user", False):
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"**{message['speaker_name']} (당신)**")
                st.markdown(message["text"])
        else:
            side = message.get("side", "")
            avatar = "🔵" if side == "pro" else "🔴"
            with st.chat_message("assistant" if side == "pro" else "user", avatar=avatar):
                st.markdown(f"**{message['speaker_name']}** ({side}측)")
                st.markdown(message["text"])
    
    # User input
    if st.session_state.debate_state["waiting_for_user"]:
        user_side = st.session_state.debate_state["user_side"]
        side_text = "찬성" if user_side == "pro" else "반대"
        
        st.info(f"당신의 입력 차례입니다! ({side_text}측)")
        user_input = st.chat_input("당신의 주장을 입력하세요...")
        
        if user_input:
            # Add user message
            add_message("user", "당신", user_input, side=user_side, is_user=True)
            
            # Reset waiting state and set user_input_processed flag
            st.session_state.debate_state["waiting_for_user"] = False
            
            # 사용자 입력 처리 플래그 설정
            if "user_input_processed" not in st.session_state:
                st.session_state.user_input_processed = False
            st.session_state.user_input_processed = True
            
            # 중요: input_completed 플래그 추가하여 입력 완료 상태 저장
            if "input_completed" not in st.session_state:
                st.session_state.input_completed = False
            st.session_state.input_completed = True
            
            if st.session_state.debug_mode:
                log_debug("사용자 입력 처리됨", "✅")
                log_debug(f"  - waiting_for_user: {st.session_state.debate_state['waiting_for_user']}")
                log_debug(f"  - user_input_processed: {st.session_state.user_input_processed}")
                log_debug(f"  - input_completed: {st.session_state.input_completed}")
            
            # 현재 단계 확인 (디버깅용)
            current_stage = st.session_state.debate_state["current_stage"]
            print(f"사용자 입력 후 단계 확인: {current_stage}, 측: {user_side}")
            print(f"입력 완료 플래그: {st.session_state.input_completed}")
            
            # 변경: 여기서 자동으로 다음 단계로 넘어가지 않도록 수정
            # 다음 버튼을 보여주기 위해 rerun
            st.rerun()
    
    # Auto-advance button (when not waiting for user)
    # 변경: 입력 완료 후에도 다음 버튼을 표시하도록 수정
    show_next_button = not st.session_state.debate_state["debate_complete"]
    
    # 사용자 입력 대기 중에는 다음 버튼 숨김 (이 부분은 유지)
    if st.session_state.debate_state["waiting_for_user"]:
        show_next_button = False
    
    # 상호질문 단계에서 발언권 버튼 표시
    if st.session_state.debate_state["current_stage"] == "cross_examination" and st.session_state.debate_state.get("waiting_for_button", False):
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("발언권 가져오기", key="get_speech_right"):
                # 사용자가 발언권 버튼을 누름
                st.session_state.debate_state["user_pressed_button"] = True
                st.session_state.debate_state["waiting_for_button"] = False
                st.session_state.debate_state["timer_running"] = False
                
                if st.session_state.debug_mode:
                    log_debug("사용자가 발언권 버튼 클릭", "👆")
                
                st.rerun()
        
        with col2:
            # 타이머 진행 상태 표시
            if st.session_state.debate_state.get("timer_running", False):
                if "timer_start" not in st.session_state.debate_state:
                    st.session_state.debate_state["timer_start"] = time.time()
                    st.session_state.debate_state["timer_duration"] = 5  # 5초
                
                elapsed = time.time() - st.session_state.debate_state["timer_start"]
                remaining = max(0, st.session_state.debate_state["timer_duration"] - elapsed)
                
                # 타이머 표시
                st.warning(f"발언권 획득 기회: {remaining:.1f}초 남음")
                
                # 타이머가 끝났는지 확인
                if remaining <= 0:
                    # 타이머 종료, NPC에게 발언권 부여
                    st.session_state.debate_state["waiting_for_button"] = False
                    st.session_state.debate_state["timer_running"] = False
                    
                    if st.session_state.debug_mode:
                        log_debug("타이머 종료, NPC에게 발언권 이전", "⏱️")
                    
                    st.rerun()
            else:
                st.info("5초 내에 버튼을 누르지 않으면, 자동으로 NPC에게 발언권이 넘어갑니다.")
    
    if show_next_button:
        if st.session_state.debug_mode:
            log_debug("다음 발언 버튼 표시됨", "🔘")
            
        # 디버깅을 위한 프린트문 추가
        print("\n==== 다음 발언 버튼 상태 ====")
        print(f"show_next_button: {show_next_button}")
        print(f"waiting_for_user: {st.session_state.debate_state['waiting_for_user']}")
        print(f"debate_complete: {st.session_state.debate_state['debate_complete']}")
        print(f"user_input_processed: {getattr(st.session_state, 'user_input_processed', None)}")
        print(f"input_completed: {getattr(st.session_state, 'input_completed', None)}")
        print(f"current_stage: {st.session_state.debate_state['current_stage']}")
        print("============================\n")
            
        if st.button("다음 발언"):
            if st.session_state.debug_mode:
                log_debug("다음 발언 버튼 클릭됨", "👆")
            
            print("다음 발언 버튼 클릭됨")
            
            # 사용자 입력 완료 플래그 초기화
            if hasattr(st.session_state, 'input_completed'):
                st.session_state.input_completed = False
            
            # 사용자 입력 처리 플래그 초기화
            if hasattr(st.session_state, 'user_input_processed'):
                st.session_state.user_input_processed = False
            
            # 현재 단계 기준으로 분기 처리
            current_stage = st.session_state.debate_state["current_stage"]
            
            # 1. 오프닝 → 찬성측 발언
            if current_stage == "opening":
                st.session_state.debate_state["current_stage"] = "pro_arguments"
                st.session_state.debate_state["turn_index"] = 0
                print("오프닝에서 찬성측 입론으로 전환")
            
            # 2. 찬성측 발언 → 반대측 발언 (모든 찬성측이 발언했을 경우)
            elif current_stage == "pro_arguments":
                all_pro_spoke = check_all_speakers_spoke("pro")
                if all_pro_spoke:
                    st.session_state.debate_state["current_stage"] = "con_arguments"
                    st.session_state.debate_state["turn_index"] = 0
                    print("모든 찬성측 발언 완료, 반대측 입론으로 전환")
            
            # 3. 반대측 발언 → 요약 (모든 반대측이 발언했을 경우)
            elif current_stage == "con_arguments":
                all_con_spoke = check_all_speakers_spoke("con")
                if all_con_spoke:
                    st.session_state.debate_state["current_stage"] = "summary"
                    st.session_state.debate_state["turn_index"] = 0
                    print("모든 반대측 발언 완료, 요약 단계로 전환")
                    generate_summary_and_transition_to_rebuttal()
                    st.rerun()
                    return
            
            # 4. 요약 단계 → 반박 단계
            elif current_stage == "summary":
                print("요약 단계에서 반박 단계로 전환")
                generate_summary_and_transition_to_rebuttal()
                st.rerun()
                return
            
            # 5. 반박 단계 → 반박 요약 (모든 반박이 끝났을 경우)
            elif current_stage == "rebuttal":
                # 반박 단계 상태 확인
                # 반박 단계 시작 시점 찾기
                rebuttal_start_idx = 0
                for i, msg in enumerate(st.session_state.debate_state["speaking_history"]):
                    if msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
                        rebuttal_start_idx = i
                        break
                
                # 반박 단계 이후의 메시지만 필터링
                rebuttal_messages = st.session_state.debate_state["speaking_history"][rebuttal_start_idx:]
                
                # 반박 단계에서 발언한 사람들 확인
                pro_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                                 if msg.get("side") == "pro" and msg.get("speaker_id") != "user" 
                                 and not msg.get("is_moderator", False))
                con_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                                 if msg.get("side") == "con" and msg.get("speaker_id") != "user"
                                 and not msg.get("is_moderator", False))
                
                user_pro_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                                    if msg.get("side") == "pro")
                user_con_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                                    if msg.get("side") == "con")
                
                # 디버깅 정보 출력
                print(f"\n==== 반박 단계 상태 확인 ====")
                print(f"찬성측 반박자 수: {len(pro_rebuttals)}/{len(st.session_state.debate_state['pro_side'])}")
                print(f"반대측 반박자 수: {len(con_rebuttals)}/{len(st.session_state.debate_state['con_side'])}")
                print(f"사용자 찬성측: {st.session_state.debate_state['user_side'] == 'pro'}, 사용자 찬성 반박: {user_pro_rebuttal}")
                print(f"사용자 반대측: {st.session_state.debate_state['user_side'] == 'con'}, 사용자 반대 반박: {user_con_rebuttal}")
                print(f"===============================\n")
                
                # 모든 반박이 완료되었는지 확인
                all_pro_rebuttals = (len(pro_rebuttals) >= len(st.session_state.debate_state["pro_side"])) and (st.session_state.debate_state["user_side"] != "pro" or user_pro_rebuttal)
                all_con_rebuttals = (len(con_rebuttals) >= len(st.session_state.debate_state["con_side"])) and (st.session_state.debate_state["user_side"] != "con" or user_con_rebuttal)
                
                # 1. 찬성측 반론 먼저 진행
                if not all_pro_rebuttals:
                    # 사용자가 찬성측이고 아직 반론하지 않았다면
                    if st.session_state.debate_state["user_side"] == "pro" and not user_pro_rebuttal:
                        st.session_state.debate_state["waiting_for_user"] = True
                        print("사용자(찬성측) 반론 차례")
                        return {
                            "speaker_id": "user",
                            "speaker_name": "당신",
                            "side": "pro",
                            "is_user": True,
                            "is_moderator": False
                        }
                    
                    # 찬성측 NPC 중 아직 반론하지 않은 사람 선택
                    remaining_pro_speakers = [spk for spk in st.session_state.debate_state["pro_side"] if spk not in pro_rebuttals]
                    if remaining_pro_speakers:
                        speaker_id = remaining_pro_speakers[0]
                        st.session_state.debate_state["turn_index"] += 1
                        print(f"찬성측 NPC({speaker_id}) 반론 차례")
                        return {
                            "speaker_id": speaker_id,
                            "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                            "side": "pro",
                            "is_user": False,
                            "is_moderator": False
                        }
                
                # 2. 찬성측 반론이 모두 끝난 후 반대측 반론 진행
                elif all_pro_rebuttals and not all_con_rebuttals:
                    # 사용자가 반대측이고 아직 반론하지 않았다면
                    if st.session_state.debate_state["user_side"] == "con" and not user_con_rebuttal:
                        st.session_state.debate_state["waiting_for_user"] = True
                        print("사용자(반대측) 반론 차례")
                        return {
                            "speaker_id": "user",
                            "speaker_name": "당신",
                            "side": "con",
                            "is_user": True,
                            "is_moderator": False
                        }
                    
                    # 반대측 NPC 중 아직 반론하지 않은 사람 선택
                    remaining_con_speakers = [spk for spk in st.session_state.debate_state["con_side"] if spk not in con_rebuttals]
                    if remaining_con_speakers:
                        speaker_id = remaining_con_speakers[0]
                        st.session_state.debate_state["turn_index"] += 1
                        print(f"반대측 NPC({speaker_id}) 반론 차례")
                        return {
                            "speaker_id": speaker_id,
                            "speaker_name": PHILOSOPHERS[speaker_id]["name"],
                            "side": "con",
                            "is_user": False,
                            "is_moderator": False
                        }
                
                # 3. 모든 반론이 끝난 경우 요약 단계로 전환 준비 (다음 버튼으로 전환됨)
                if all_pro_rebuttals and all_con_rebuttals:
                    print("모든 반론 완료 - 다음 버튼 클릭 시 요약 단계로 진행 가능")
                    return None
                
                # 여기까지 왔다면 모든 처리가 끝난 상태
                print("모든 반론 발언 완료됨, 다음 버튼 클릭 시 요약 단계로 진행")
                return None
            
            # 6. 반박 요약 단계 - 자동으로 모더레이터 요약 생성
            elif current_stage == "rebuttal_summary":
                print("반박 요약 단계 시작, 모더레이터 요약 생성")
                # 상호질문 단계로 넘어가기 위한 요약 생성 및 처리
                try:
                    # 반박 단계 메시지만 필터링
                    rebuttal_messages = []
                    started_rebuttal = False
                    
                    for msg in st.session_state.debate_state["speaking_history"]:
                        if not started_rebuttal and msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
                            started_rebuttal = True
                        
                        if started_rebuttal:
                            rebuttal_messages.append(msg)
                    
                    print(f"반박 단계 메시지 수: {len(rebuttal_messages)}")
                    rebuttal_summary = generate_moderator_summary(
                        st.session_state.debate_state["topic"],
                        rebuttal_messages
                    )
                    
                    add_message("moderator", "진행자", rebuttal_summary, is_moderator=True)
                    print("반박 요약 메시지 추가 완료")
                    
                    # 상호질문 단계로 전환
                    cross_examination_intro = f"""
                    이제 상호질문 단계로 넘어가겠습니다. 
                    
                    이 단계에서는 양측이 서로의 주장에 대해 자유롭게 질문하고 토론할 수 있습니다.
                    논리적인 오류나 약점을 지적하고, 서로의 관점을 더 깊이 탐구하는 시간이 될 것입니다.
                    
                    각자 상대측의 발언자를 지목하여 질문을 하거나 의견을 제시할 수 있습니다.
                    예의를 지키되, 철학적 깊이가 있는 토론이 되길 바랍니다.
                    
                    발언권을 얻고자 하는 분은 발언권 버튼을 눌러주세요.
                    5초 내에 아무도 버튼을 누르지 않으면, 자동으로 NPC에게 발언권이 넘어갑니다.
                    """
                    
                    add_message("moderator", "진행자", cross_examination_intro, is_moderator=True)
                    
                    # 상호질문 단계로 전환
                    st.session_state.debate_state["current_stage"] = "cross_examination"
                    st.session_state.debate_state["cross_exam_round"] = 0
                    st.session_state.debate_state["current_speakers"] = []
                    st.session_state.debate_state["timer_running"] = True
                    st.session_state.debate_state["waiting_for_button"] = True
                    print("상호질문 단계로 전환 완료")
                except Exception as e:
                    if st.session_state.debug_mode:
                        log_debug(f"상호질문 단계 전환 오류: {str(e)}", "❌")
                    print(f"상호질문 단계 전환 오류: {str(e)}")
                
                st.rerun()
                return
            
            # 7. 상호질문 단계
            elif current_stage == "cross_examination":
                # 상호질문 단계에서 다음 버튼 클릭 시
                if st.session_state.debate_state.get("waiting_for_button", False):
                    # 발언권 버튼 대기 중이면 타이머 종료, NPC 자동 선택
                    st.session_state.debate_state["waiting_for_button"] = False
                    st.session_state.debate_state["timer_running"] = False
                    print("다음 버튼으로 NPC 발언자 자동 선택")
                elif "is_intervention" in st.session_state.debate_state:
                    # 모더레이터 개입 후 다음 라운드 시작
                    st.session_state.debate_state.pop("is_intervention", None)
                    st.session_state.debate_state["current_speakers"] = []
                    st.session_state.debate_state["cross_exam_round"] += 1
                    
                    if st.session_state.debate_state["cross_exam_round"] >= 2:
                        # 충분한 상호질문 후 마무리 단계로
                        st.session_state.debate_state["current_stage"] = "closing_summary"
                        print("상호질문 단계 완료, 마무리 단계로 전환")
                    else:
                        # 새로운 질문 라운드 시작 - 발언권 버튼 표시
                        st.session_state.debate_state["waiting_for_button"] = True
                        st.session_state.debate_state["timer_running"] = True
                        
                        # 타이머 초기화
                        st.session_state.debate_state["timer_start"] = time.time()
                        st.session_state.debate_state["timer_duration"] = 5  # 5초
                        
                        print("새로운 상호질문 라운드 시작")
                
                run_debate_step()
                st.rerun()
                return
            
            # 8. 마무리 단계
            elif current_stage == "closing_summary":
                print("마무리 단계, 최종 요약 생성")
                
                # closing_summary 단계 처리
                try:
                    # 전체 토론 내용에서 중요 부분 추출하여 최종 요약 생성
                    closing_summary = generate_closing_summary(
                        st.session_state.debate_state["topic"],
                        st.session_state.debate_state["speaking_history"]
                    )
                    
                    add_message("moderator", "진행자", closing_summary, is_moderator=True)
                    print("최종 요약 메시지 추가 완료")
                    
                    # 토론 종료 표시
                    st.session_state.debate_state["debate_complete"] = True
                    print("토론 종료")
                except Exception as e:
                    if st.session_state.debug_mode:
                        log_debug(f"최종 요약 생성 오류: {str(e)}", "❌")
                    print(f"최종 요약 생성 오류: {str(e)}")
                    
                    # 오류 발생 시 기본 메시지 사용
                    fallback_summary = f"""
                    '{st.session_state.debate_state["topic"]}'에 관한 오늘의 토론은 매우 유익했습니다.
                    
                    양측 모두 철학적 깊이가 담긴 훌륭한 주장과 반박을 펼쳐주셨으며,
                    상호질문 단계에서는 더욱 심도 있는 논의가 이루어졌습니다.
                    
                    이 토론이 청중 여러분께 주제에 대한 다양한 철학적 관점을 제공했기를 바랍니다.
                    참여해 주신 모든 분들께 감사드립니다.
                    """
                    add_message("moderator", "진행자", fallback_summary, is_moderator=True)
                    
                    # 토론 종료 표시
                    st.session_state.debate_state["debate_complete"] = True
                
                st.rerun()
                return
            
            # 일반적인 다음 단계 실행
            run_debate_step()
            st.rerun()
    
    # 디버깅 모드일 때 상태 표시
    if st.session_state.debug_mode and st.session_state.debate_instance:
        with st.sidebar:
            st.subheader("디베이트 인스턴스 상태")
            st.write(f"현재 단계: {st.session_state.debate_instance.debate_state.get('current_stage', 'unknown')}")
            st.write(f"Turn Count: {st.session_state.debate_instance.debate_state.get('turn_count', 0)}")
            st.write(f"유저 입력 대기: {st.session_state.debate_state['waiting_for_user']}")
            
            if hasattr(st.session_state, 'user_input_processed'):
                st.write(f"유저 입력 처리됨: {st.session_state.user_input_processed}")
            
            # 발언 기록 표시
            st.write("**발언 기록:**")
            for idx, entry in enumerate(st.session_state.debate_instance.debate_state.get("speaking_history", [])):
                st.write(f"{idx+1}. {entry.get('speaker_id')} ({entry.get('role')})")
            
            # 감정 상태 표시
            if st.session_state.debate_state["emotion_states"]:
                st.write("**감정 상태:**")
                for speaker_id, emotion_data in st.session_state.debate_state["emotion_states"].items():
                    philosopher_name = PHILOSOPHERS.get(speaker_id, {}).get("name", speaker_id)
                    st.write(f"{philosopher_name}: {emotion_data.get('primary_emotion')} ({emotion_data.get('intensity')})")
    
    # Reset button
    if st.button("새 토론 시작"):
        st.session_state.debate_state["current_stage"] = "setup"
        st.session_state.debate_state["debate_complete"] = False
        st.rerun()

# Main app
def main():
    # 추가 세션 상태 변수 초기화
    if "user_pressed_button" not in st.session_state.debate_state:
        st.session_state.debate_state["user_pressed_button"] = False
    
    if "waiting_for_button" not in st.session_state.debate_state:
        st.session_state.debate_state["waiting_for_button"] = False
    
    if "timer_running" not in st.session_state.debate_state:
        st.session_state.debate_state["timer_running"] = False
    
    if "cross_exam_round" not in st.session_state.debate_state:
        st.session_state.debate_state["cross_exam_round"] = 0
    
    if "current_speakers" not in st.session_state.debate_state:
        st.session_state.debate_state["current_speakers"] = []
    
    # Display setup or debate based on state
    if st.session_state.debate_state["current_stage"] == "setup":
        setup_debate()
    else:
        display_debate()

# 추가: 모든 발언자가 발언했는지 확인하는 도우미 함수
def check_all_speakers_spoke(side):
    """해당 측의 모든 발언자가 발언했는지 확인"""
    debate_state = st.session_state.debate_state
    side_speakers = debate_state[f"{side}_side"]
    
    # 해당 측의 발언자 확인
    speakers = set(msg.get("speaker_id") for msg in debate_state["speaking_history"] 
                if msg.get("side") == side and msg.get("speaker_id") != "user")
    
    # 사용자가 해당 측에 있고 발언했는지 확인
    user_spoke = any(msg.get("is_user", False) for msg in debate_state["speaking_history"] 
                  if msg.get("side") == side)
    
    # 모든 발언자가 발언했는지 여부
    all_spoke = (len(speakers) >= len(side_speakers)) and (debate_state["user_side"] != side or user_spoke)
    
    print(f"{side}측 발언 확인: 발언자 {len(speakers)}/{len(side_speakers)}, 사용자 발언: {user_spoke}, 모두 발언: {all_spoke}")
    
    return all_spoke

# 추가: 모든 반박이 완료되었는지 확인하는 함수
def check_all_rebuttals_complete():
    """모든 반박이 완료되었는지 확인"""
    debate_state = st.session_state.debate_state
    pro_side = debate_state["pro_side"]
    con_side = debate_state["con_side"]
    
    # 현재 단계가 rebuttal인지 확인
    current_stage = debate_state["current_stage"]
    
    # 반박 단계 시작 시점 찾기
    rebuttal_start_idx = 0
    for i, msg in enumerate(debate_state["speaking_history"]):
        if msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
            rebuttal_start_idx = i
            break
    
    # 반박 단계 이후의 메시지만 필터링
    rebuttal_messages = debate_state["speaking_history"][rebuttal_start_idx:]
    
    # 반박 단계에서 발언한 사람들 확인
    pro_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                      if msg.get("side") == "pro" and msg.get("speaker_id") != "user" 
                      and not msg.get("is_moderator", False))
    con_rebuttals = set(msg.get("speaker_id") for msg in rebuttal_messages 
                      if msg.get("side") == "con" and msg.get("speaker_id") != "user"
                      and not msg.get("is_moderator", False))
    
    user_pro_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                          if msg.get("side") == "pro")
    user_con_rebuttal = any(msg.get("is_user", False) for msg in rebuttal_messages 
                          if msg.get("side") == "con")
    
    # 모든 반박이 완료되었는지 확인
    all_pro_rebuttals = (len(pro_rebuttals) >= len(pro_side)) and (debate_state["user_side"] != "pro" or user_pro_rebuttal)
    all_con_rebuttals = (len(con_rebuttals) >= len(con_side)) and (debate_state["user_side"] != "con" or user_con_rebuttal)
    
    print(f"반박 완료 확인: 찬성측 {len(pro_rebuttals)}/{len(pro_side)}, 반대측 {len(con_rebuttals)}/{len(con_side)}")
    print(f"사용자 반박: 찬성측 {user_pro_rebuttal}, 반대측 {user_con_rebuttal}")
    print(f"모든 반박 완료 여부: 찬성측 {all_pro_rebuttals}, 반대측 {all_con_rebuttals}")
    
    return all_pro_rebuttals and all_con_rebuttals

# 추가: 모더레이터 요약 생성 및 반박 단계로 전환하는 함수
def generate_summary_and_transition_to_rebuttal():
    """모더레이터 요약 생성 및 반박 단계로 전환"""
    # 입론 단계 요약 생성
    summary_text = generate_moderator_summary(
        st.session_state.debate_state["topic"],
        st.session_state.debate_state["speaking_history"]
    )
    
    add_message("moderator", "진행자", summary_text, is_moderator=True)
    print("모더레이터 요약 메시지 추가 완료")
    
    # 반박 단계로 전환
    st.session_state.debate_state["current_stage"] = "rebuttal"
    st.session_state.debate_state["turn_index"] = 0
    print("반박 단계로 전환 완료")
    
    # 반박 단계 소개 메시지
    rebuttal_intro = f"""
    이제 반박 단계로 넘어가겠습니다. 지금까지 양측의 주장을 들었으니, 
    이제 각 측은 상대측의 주장에 대해 반박할 기회를 갖게 됩니다.
    
    반박 시 상대방의 주장에 대한 논리적 오류나 약점을 지적하고, 
    자신의 입장을 더욱 공고히 하는 방향으로 진행해 주시기 바랍니다.
    
    먼저 찬성측부터 반박을 시작하겠습니다.
    """
    
    add_message("moderator", "진행자", rebuttal_intro, is_moderator=True)
    print("반박 단계 소개 메시지 추가 완료")
    
    # 중요: 반박 단계에서 찬성측 발언 기록 초기화 (반대측이 먼저 선택되는 문제 해결)
    st.session_state.debate_state["pro_rebuttal_started"] = False
    st.session_state.debate_state["con_rebuttal_started"] = False
    
    # 사용자가 반대측이면 즉시 찬성측 첫 발언 생성 (중요 수정)
    if st.session_state.debate_state["user_side"] == "con":
        # 찬성측 NPC 첫 발언 즉시 생성
        pro_side = st.session_state.debate_state["pro_side"]
        if pro_side:
            speaker_id = pro_side[0]
            
            print(f"찬성측 첫 반박 - {speaker_id} 발언 생성 시작")
            
            # 찬성측 첫 발언 강제 생성
            pro_argument = generate_philosopher_argument_with_emotion(
                speaker_id,
                st.session_state.debate_state["topic"],
                st.session_state.debate_state["context"],
                "pro",
                st.session_state.debate_state["speaking_history"],
                use_emotion=True
            )
            
            # 메시지 추가
            add_message(
                speaker_id,
                PHILOSOPHERS[speaker_id]["name"],
                pro_argument,
                side="pro"
            )
            
            print(f"찬성측 첫 반박({speaker_id}) 생성 완료")
    else:
        # 사용자가 찬성측이면 사용자 입력 기다림
        st.session_state.debate_state["waiting_for_user"] = True
        print("사용자(찬성측)의 첫 반박 대기")

# 추가: 모더레이터 반박 요약 생성 함수
def generate_rebuttal_summary():
    """모더레이터 반박 요약 생성 및 토론 마무리"""
    print("반박 요약 단계 처리 시작")
    try:
        # 반박 단계 메시지만 필터링
        rebuttal_messages = []
        started_rebuttal = False
        
        for msg in st.session_state.debate_state["speaking_history"]:
            if not started_rebuttal and msg.get("is_moderator", False) and "반박 단계" in msg.get("text", ""):
                started_rebuttal = True
            
            if started_rebuttal:
                rebuttal_messages.append(msg)
        
        print(f"반박 단계 메시지 수: {len(rebuttal_messages)}")
        rebuttal_summary = generate_moderator_summary(
            st.session_state.debate_state["topic"],
            rebuttal_messages
        )
    except Exception as e:
        if st.session_state.debug_mode:
            log_debug("반박 요약 생성 오류", "❌")
        print(f"반박 요약 생성 오류: {str(e)}")
        rebuttal_summary = "지금까지 양측이 훌륭한 반박을 주고받았습니다."
    
    add_message("moderator", "진행자", rebuttal_summary, is_moderator=True)
    print("반박 요약 메시지 추가 완료")
    
    # 토론 마무리
    conclusion_text = f"""
    이것으로 '{st.session_state.debate_state["topic"]}'에 관한 토론을 마치겠습니다.
    양측 모두 철학적 깊이가 담긴 훌륭한 주장과 반박을 펼쳐주셨습니다.
    
    이 토론이 청중 여러분께 주제에 대한 더 깊은 통찰을 제공했기를 바랍니다.
    참여해 주신 모든 분들께 감사드립니다.
    """
    
    add_message("moderator", "진행자", conclusion_text, is_moderator=True)
    st.session_state.debate_state["debate_complete"] = True
    print("토론 마무리 완료 - debate_complete = True")

def generate_cross_examination_question(questioner_id, target_id, topic, debate_history):
    """상호질문 단계에서 질문 생성"""
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher"})
    target = PHILOSOPHERS.get(target_id, {"name": target_id, "description": "A philosopher"})
    
    # 대화 이력을 텍스트로 변환
    history_text = ""
    for entry in debate_history[-10:]:  # 최근 10개 메시지만 사용
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = f"""
    당신은 철학자 {questioner["name"]}입니다. {questioner["description"]}
    
    지금은 상호질문 단계로, 당신은 {target["name"]}에게 비판적인 질문을 하거나 그의 주장의 약점을 지적해야 합니다.
    철학자로서 당신의 철학적 배경, 사상, 방법론을 반영하여 질문하세요.
    
    질문 시 다음 사항을 고려하세요:
    1. 상대방의 주장에서 논리적 모순이나 약점을 지적하세요.
    2. 상대방의 가정이나 전제를 비판적으로 분석하세요.
    3. 상대방의 주장이 가져올 수 있는 문제점이나 부정적 결과를 지적하세요.
    4. 당신의 관점에서 상대방의 주장을 반박할 수 있는 근거나 사례를 제시하세요.
    5. 예의는 지키되, 철학적으로 날카로운 질문을 하세요.
    """
    
    user_prompt = f"""
    토론 주제: {topic}
    
    최근 토론 내용:
    {history_text}
    
    당신({questioner["name"]})의 차례입니다. {target["name"]}의 주장에 대해 비판적인 질문을 하거나 약점을 지적하세요.
    직접 {target["name"]}의 이름을 언급하며 질문을 시작하세요.
    """
    
    return llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

def generate_cross_examination_response(responder_id, questioner_id, topic, debate_history):
    """상호질문 단계에서 응답 생성"""
    responder = PHILOSOPHERS.get(responder_id, {"name": responder_id, "description": "A philosopher"})
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher"})
    
    # 대화 이력을 텍스트로 변환
    history_text = ""
    for entry in debate_history[-10:]:  # 최근 10개 메시지만 사용
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = f"""
    당신은 철학자 {responder["name"]}입니다. {responder["description"]}
    
    지금은 상호질문 단계로, {questioner["name"]}의 질문이나 비판에 대해 답변해야 합니다.
    철학자로서 당신의 철학적 배경, 사상, 방법론을 반영하여 응답하세요.
    
    응답 시 다음 사항을 고려하세요:
    1. 질문에 직접적으로 답변하되, 자신의 입장을 명확히 하세요.
    2. 비판에 대해 방어하거나 반박하는 논리를 제시하세요.
    3. 필요하다면 자신의 원래 주장을 더 명확히 하거나 보완하세요.
    4. 상대방의 오해가 있다면 정중하게 바로잡으세요.
    5. 당신의 고유한 철학적 용어나 개념을 적절히 활용하세요.
    """
    
    user_prompt = f"""
    토론 주제: {topic}
    
    최근 토론 내용:
    {history_text}
    
    당신({responder["name"]})의 차례입니다. {questioner["name"]}의 질문이나 비판에 직접 답변하세요.
    직접 {questioner["name"]}의 이름을 언급하며 응답을 시작하세요.
    """
    
    return llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

def generate_moderator_intervention():
    """모더레이터의 상호질문 중재 메시지 생성"""
    intervention_text = f"""
    흥미로운 대화가 오가고 있군요. 두 분의 관점 모두 철학적 깊이가 느껴집니다.
    
    이제 다른 참가자들에게도 발언 기회를 드리겠습니다.
    
    발언권을 얻고자 하는 분은 발언권 버튼을 눌러주세요.
    5초 내에 아무도 버튼을 누르지 않으면, 자동으로 NPC에게 발언권이 넘어갑니다.
    """
    
    return intervention_text

def generate_closing_summary(topic, debate_history):
    """토론 최종 요약 생성"""
    # 전체 토론 내용에서 중요 부분 추출
    important_messages = []
    
    try:
        # 단계별로 메시지 추출 대신 간단하게 최근 메시지 사용
        if len(debate_history) > 20:
            # 최신 20개 메시지만 사용
            important_messages = debate_history[-20:]
        else:
            important_messages = debate_history
        
        # 메시지를 텍스트로 변환
        history_text = ""
        for entry in important_messages:
            speaker_name = entry.get("speaker_name", "Unknown")
            side = entry.get("side", "")
            side_text = f"({side}측)" if side and side not in ["neutral"] else ""
            text = entry.get("text", "")
            history_text += f"{speaker_name} {side_text}: {text}\n\n"
        
        system_prompt = """
        당신은 전문적인 토론 진행자입니다. 지금까지 진행된 철학적 토론의 최종 요약을 생성해 주세요.
        토론의 주요 쟁점과 각 측의 핵심 주장을 객관적으로 요약하고, 토론에서 드러난 철학적 함의를 강조해 주세요.
        중립적인 관점을 유지하며, 토론의 결론을 제시해 주세요.
        """
        
        user_prompt = f"""
        토론 주제: {topic}
        
        주요 토론 내용:
        {history_text}
        
        위 토론의 주요 내용을 요약하고, 각 측의 핵심 주장과 쟁점을 정리해 주세요.
        이 토론에서 드러난 철학적 함의와 현대적 의미도 함께 언급해 주세요.
        마지막으로 토론 참가자들에게 감사 인사를 전하며 마무리해 주세요.
        """
        
        closing_summary = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return closing_summary
    except Exception as e:
        print(f"요약 생성 중 오류 발생: {str(e)}")
        # 기본 요약 반환
        return f"""
        토론을 마무리하겠습니다. 모든 참가자들께서 주제에 대한 깊은 통찰을 보여주셨습니다.
        이번 토론을 통해 '{topic}'에 대한 다양한 철학적 관점을 들을 수 있었습니다.
        참여해 주신 모든 분들께 감사드립니다.
        """

if __name__ == "__main__":
    main() 