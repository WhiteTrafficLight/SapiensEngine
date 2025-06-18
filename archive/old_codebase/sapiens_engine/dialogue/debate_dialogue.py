"""
찬반토론 대화 형식을 구현하는 클래스
- 찬성/반대/중립 입장에 따른 발언 순서 관리
- 토론 단계(opening, discussion, closing) 관리
- 각 입장에 맞는 AI 응답 생성
- 진행자(Moderator) 역할 추가
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any, Union, Tuple

from .base_dialogue import BaseDialogue

logger = logging.getLogger(__name__)

class DebateStage:
    """토론 단계 정의"""
    OPENING = "opening"
    DISCUSSION = "discussion"
    CLOSING = "closing"
    COMPLETED = "completed"

class ParticipantRole:
    """참가자 역할 정의"""
    PRO = "pro"
    CON = "con"
    NEUTRAL = "neutral"
    MODERATOR = "moderator"  # 진행자 역할 추가

class DebateDialogue(BaseDialogue):
    """찬반토론 대화 형식 구현"""
    
    def __init__(self, room_id: str, room_data: Dict[str, Any] = None):
        """
        찬반토론 대화 초기화
        
        Args:
            room_id: 채팅방 ID
            room_data: 채팅방 관련 데이터
        """
        super().__init__(room_id, room_data)
        self.dialogue_type = "debate"
        
        # 토론 상태 초기화
        self.debate_state = {
            "current_stage": DebateStage.OPENING,
            "turn_count": 0,
            "speaking_history": [],
            "key_points": [], 
            "next_speaker": None,
            "last_update_time": time.time(),
            "moderator_id": "Moderator"  # 진행자 ID 추가
        }
        
        # 주제에서 찬성/반대 입장 명확화
        self.stance_statements = self._generate_stance_statements()
        
        # 참가자 분류
        self.pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
        self.con_participants = self._get_participants_by_role(ParticipantRole.CON)
        self.neutral_participants = self._get_participants_by_role(ParticipantRole.NEUTRAL)
        
        # 발언 순서 초기화 - 진행자가 첫 번째로 시작
        self.speaking_order = self._initialize_speaking_order()
        
        logger.info(f"Debate dialogue initialized for room {room_id} with "
                   f"{len(self.pro_participants)} pro, {len(self.con_participants)} con, "
                   f"and {len(self.neutral_participants)} neutral participants")
        
        # 진행자 오프닝 메시지 생성 (채팅방 생성 시 자동 생성)
        self._create_opening_message()
    
    def _generate_stance_statements(self) -> Dict[str, str]:
        """주제에서 찬성/반대 입장 명확화"""
        topic = self.room_data.get('title', '')
        context = self.room_data.get('context', '')
        
        try:
            # LLM을 통해 주제에 대한 찬성/반대 입장을 명확하게 문장으로 표현
            # LLM 매니저를 임포트하기 위한 코드 추가 필요할 수 있음
            from sapiens_engine.core.llm_manager import LLMManager
            from sapiens_engine.core.config_loader import ConfigLoader
            
            config_loader = ConfigLoader()
            llm_manager = LLMManager(config_loader)
            
            system_prompt = """
            You are a debate preparation assistant. Your task is to analyze the given topic and create clear stance statements for both PRO and CON positions.
            Format your response as JSON with the following structure:
            {
                "pro_statement": "Clear statement supporting the position...",
                "con_statement": "Clear statement opposing the position..."
            }
            Keep each statement concise (1-2 sentences) and strongly articulated.
            """
            
            user_prompt = f"Topic: {topic}\n\nContext: {context}"
            
            # LLM 호출
            response = llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_provider="openai",
                llm_model="gpt-4o"
            )
            
            # JSON 응답 파싱
            try:
                result = json.loads(response)
                pro_statement = result.get("pro_statement", "")
                con_statement = result.get("con_statement", "")
            except:
                # JSON 파싱 실패 시 기본값
                logger.error(f"Failed to parse stance statements for topic: {topic}")
                pro_statement = f"{topic} is true and beneficial."
                con_statement = f"{topic} is false and harmful."
            
            logger.info(f"Generated stance statements - PRO: {pro_statement}, CON: {con_statement}")
            
            return {
                "pro": pro_statement,
                "con": con_statement
            }
        except Exception as e:
            logger.error(f"Error generating stance statements: {str(e)}")
            # 오류 시 기본값
            return {
                "pro": f"{topic} is true and beneficial.",
                "con": f"{topic} is false and harmful."
            }
    
    def _create_opening_message(self) -> Dict[str, Any]:
        """진행자의 오프닝 메시지 생성"""
        try:
            topic = self.room_data.get('title', '')
            context = self.room_data.get('context', '')
            
            logger.info(f"[DEBUG] 진행자 오프닝 메시지 생성 시작: 주제 '{topic}'")
            logger.info(f"[DEBUG] 컨텍스트 길이: {len(context) if context else 0}")
            logger.info(f"[DEBUG] 찬성/반대 입장 정보: {self.stance_statements}")
            
            # LLM 매니저를 임포트하기 위한 코드 추가 필요할 수 있음
            from sapiens_engine.core.llm_manager import LLMManager
            from sapiens_engine.core.config_loader import ConfigLoader
            
            config_loader = ConfigLoader()
            llm_manager = LLMManager(config_loader)
            
            # 프롬프트 구성
            system_prompt = f"""
            You are the moderator of a debate on the topic: "{topic}".
            
            Act as a professional podcast host with a neutral stance. Your task is to:
            1. Welcome the audience and participants
            2. Summarize the debate topic clearly
            3. Explain the format of the debate
            4. Call on the PRO side to present their opening statement
            
            Important: Respond in the same language as the topic. Keep your response concise (150-200 words).
            """
            
            # 참가자 정보 구성
            pro_participants_names = [self._get_participant_name(p) for p in self.pro_participants]
            con_participants_names = [self._get_participant_name(p) for p in self.con_participants]
            
            logger.info(f"[DEBUG] 참가자 정보 - 찬성측: {pro_participants_names}, 반대측: {con_participants_names}")
            
            # 주제 언어에 맞게 응답하기 위한 추가 정보
            user_prompt = f"""
            Topic: {topic}
            
            Additional context: {context}
            
            PRO position: {self.stance_statements.get('pro', '')}
            CON position: {self.stance_statements.get('con', '')}
            
            PRO side participants: {', '.join(pro_participants_names)}
            CON side participants: {', '.join(con_participants_names)}
            """
            
            logger.info(f"[DEBUG] LLM 요청 시작 - provider: openai, model: gpt-4o")
            logger.info(f"[DEBUG] System prompt: {system_prompt[:100]}...")
            logger.info(f"[DEBUG] User prompt: {user_prompt[:100]}...")
            
            # LLM API 호출
            opening_message = llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_provider="openai",
                llm_model="gpt-4o"
            )
            
            logger.info(f"[DEBUG] LLM 응답 받음 - 길이: {len(opening_message) if opening_message else 0}")
            logger.info(f"[DEBUG] LLM 응답 내용: {opening_message[:100]}..." if opening_message else "[DEBUG] LLM 응답 없음")
            logger.info(f"Generated moderator opening message for room {self.room_id}")
            
            # 생성된 메시지 객체
            message_obj = {
                "id": f"moderator-{int(time.time())}",
                "text": opening_message,
                "sender": self.debate_state["moderator_id"],
                "isUser": False,
                "timestamp": time.time(),
                "role": ParticipantRole.MODERATOR
            }
            
            # 메시지를 speaking_history에 추가하여 다음 발언자를 올바르게 결정할 수 있도록 함
            self.debate_state["speaking_history"].append({
                "speaker_id": self.debate_state["moderator_id"],
                "role": ParticipantRole.MODERATOR,
                "timestamp": time.time(),
                "stage": self.debate_state["current_stage"]
            })
            
            # 턴 카운트 증가
            self.debate_state["turn_count"] += 1
            
            # 다음 발언자 결정
            next_speaker = self.get_next_speaker()
            self.debate_state["next_speaker"] = next_speaker["speaker_id"]
            
            logger.info(f"Next speaker after moderator opening: {next_speaker['speaker_id']} ({next_speaker['role']})")
            
            return message_obj
            
        except Exception as e:
            logger.error(f"[ERROR] Error creating opening message: {str(e)}", exc_info=True)
            # 기본 메시지 반환
            return {
                "id": f"moderator-{int(time.time())}",
                "text": f"Welcome to our debate on '{topic}'. Let's begin with opening statements from our participants.",
                "sender": self.debate_state["moderator_id"],
                "isUser": False,
                "timestamp": time.time(),
                "role": ParticipantRole.MODERATOR
            }
    
    def _get_participant_name(self, participant_id: str) -> str:
        """참가자 ID로 이름 반환 (실제 구현 필요)"""
        # 실제 구현에서는 NPC 정보를 조회하여 이름 반환
        return participant_id
    
    def _get_participants_by_role(self, role: str) -> List[str]:
        """채팅방 데이터에서 역할별 참가자 목록 추출"""
        if not self.room_data:
            return []
        
        # room_data에서 pro, con, neutral 목록 가져오기
        # npcPositions 딕셔너리를 사용하는 방식으로 변경
        if role in [ParticipantRole.PRO, ParticipantRole.CON]:
            npc_positions = self.room_data.get("npcPositions", {})
            if npc_positions:
                return [npc_id for npc_id, pos in npc_positions.items() if pos.lower() == role.lower()]
        
        # 기존 방식도 지원 (하위 호환성)
        return self.room_data.get(role, [])
    
    def _initialize_speaking_order(self) -> List[Dict[str, Any]]:
        """토론 발언 순서 초기화"""
        speaking_order = []
        
        # 진행자가 첫 번째로 발언
        speaking_order.append({
            "speaker_id": self.debate_state["moderator_id"],
            "role": ParticipantRole.MODERATOR
        })
        
        # 오프닝 단계 순서 - 각 입장의 대표자부터 시작
        if self.pro_participants:
            speaking_order.append({"speaker_id": self.pro_participants[0], "role": ParticipantRole.PRO})
        if self.con_participants:
            speaking_order.append({"speaker_id": self.con_participants[0], "role": ParticipantRole.CON})
        
        # 중립 참가자 추가
        for neutral_id in self.neutral_participants:
            speaking_order.append({"speaker_id": neutral_id, "role": ParticipantRole.NEUTRAL})
        
        # 나머지 참가자 추가 (이미 추가된 대표자 제외)
        for pro_id in self.pro_participants[1:]:
            speaking_order.append({"speaker_id": pro_id, "role": ParticipantRole.PRO})
        for con_id in self.con_participants[1:]:
            speaking_order.append({"speaker_id": con_id, "role": ParticipantRole.CON})
        
        return speaking_order
    
    def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        사용자 메시지 처리
        
        Args:
            message: 사용자 메시지 내용
            user_id: 사용자 ID
            
        Returns:
            처리된 메시지 정보
        """
        logger.info(f"Processing debate message from {user_id} in room {self.room_id}")
        
        # 사용자 역할 확인
        user_role = self._get_user_role(user_id)
        
        # 토론 진행 상태 업데이트
        self.debate_state["turn_count"] += 1
        self.debate_state["speaking_history"].append({
            "speaker_id": user_id,
            "role": user_role,
            "timestamp": time.time(),
            "stage": self.debate_state["current_stage"]
        })
        
        # 단계 전환 체크
        self._check_stage_transition()
        
        # 다음 발언자 결정
        next_speaker = self.get_next_speaker()
        self.debate_state["next_speaker"] = next_speaker["speaker_id"]
        
        return {
            "processed": True,
            "user_id": user_id,
            "user_role": user_role,
            "message": message,
            "dialogue_type": self.dialogue_type,
            "debate_stage": self.debate_state["current_stage"],
            "next_speaker": next_speaker
        }
    
    def _get_user_role(self, user_id: str) -> str:
        """사용자의 토론 역할 확인"""
        if user_id in self.pro_participants:
            return ParticipantRole.PRO
        elif user_id in self.con_participants:
            return ParticipantRole.CON
        else:
            return ParticipantRole.NEUTRAL
    
    def _check_stage_transition(self) -> None:
        """토론 단계 전환 조건 체크 및 상태 업데이트"""
        current_stage = self.debate_state["current_stage"]
        turn_count = self.debate_state["turn_count"]
        
        # 오프닝 단계 -> 토론 단계
        if current_stage == DebateStage.OPENING and turn_count >= len(self.speaking_order):
            logger.info(f"Transitioning from OPENING to DISCUSSION in room {self.room_id}")
            self.debate_state["current_stage"] = DebateStage.DISCUSSION
        
        # 토론 단계 -> 마무리 단계 (기준: 메시지 20개 이상이면 마무리로 전환)
        elif current_stage == DebateStage.DISCUSSION and turn_count >= 20:
            logger.info(f"Transitioning from DISCUSSION to CLOSING in room {self.room_id}")
            self.debate_state["current_stage"] = DebateStage.CLOSING
        
        # 마무리 단계 -> 완료
        elif current_stage == DebateStage.CLOSING and turn_count >= 20 + len(self.speaking_order):
            logger.info(f"Debate COMPLETED in room {self.room_id}")
            self.debate_state["current_stage"] = DebateStage.COMPLETED
    
    def generate_response(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        토론 형식에 맞는 AI 응답 생성
        
        Args:
            context: 응답 생성에 필요한 컨텍스트
            
        Returns:
            생성된 응답 정보
        """
        context = context or {}
        next_speaker = self.get_next_speaker()
        speaker_id = next_speaker.get("speaker_id")
        speaker_role = next_speaker.get("role")
        current_stage = self.debate_state["current_stage"]
        
        # 스피커 역할에 따른 프롬프트 생성
        prompt = self._build_stage_specific_prompt(speaker_id, speaker_role, current_stage, context)
        
        logger.info(f"Generating debate response from {speaker_id} ({speaker_role}) "
                   f"in stage {current_stage} for room {self.room_id}")
        
        return {
            "speaker_id": speaker_id,
            "speaker_role": speaker_role,
            "prompt": prompt,
            "dialogue_type": self.dialogue_type,
            "debate_stage": current_stage
        }
    
    def _build_stage_specific_prompt(self, speaker_id: str, speaker_role: str, 
                                   stage: str, context: Dict[str, Any]) -> str:
        """단계별 맞춤형 프롬프트 생성"""
        # 진행자인 경우 별도 프롬프트 생성
        if speaker_role == ParticipantRole.MODERATOR:
            return self._create_moderator_prompt(stage, context)
        elif stage == DebateStage.OPENING:
            return self._create_opening_prompt(speaker_id, speaker_role, context)
        elif stage == DebateStage.CLOSING:
            return self._create_closing_prompt(speaker_id, speaker_role, context)
        else:  # DISCUSSION
            return self._create_discussion_prompt(speaker_id, speaker_role, context)
    
    def _create_moderator_prompt(self, stage: str, context: Dict[str, Any]) -> str:
        """진행자용 단계별 프롬프트"""
        topic = self.room_data.get('title', 'the topic')
        recent_messages = context.get('recent_messages', [])
        pro_statement = self.stance_statements.get('pro', f"The idea that {topic} is beneficial")
        con_statement = self.stance_statements.get('con', f"The idea that {topic} is harmful")
        
        # 최근 5개 메시지
        recent_messages_text = "\n".join([
            f"{msg.get('sender', 'Unknown')} ({self._get_role_display(msg.get('sender', ''))}): {msg.get('text', '')}" 
            for msg in recent_messages[-5:]
        ])
        
        # 단계별 다른 프롬프트
        if stage == DebateStage.OPENING:
            return f"""You are the moderator of a debate on the topic: "{topic}".
            
As the moderator, your role is to guide the debate and ensure all sides are heard fairly.

This is the OPENING phase. Your task is to:
1. Welcome the audience and participants
2. Summarize the debate topic clearly including these positions:
   - PRO: {pro_statement}
   - CON: {con_statement}
3. Explain the format of the debate
4. Call on the PRO side to present their opening statement

Keep your response concise, engaging, and in the tone of a professional podcast host.
Respond in the same language as the topic.

Recent messages:
{recent_messages_text}

Your moderation:"""
        
        elif stage == DebateStage.DISCUSSION:
            return f"""You are the moderator of a debate on the topic: "{topic}".

This is the DISCUSSION phase. Your task is to:
1. Summarize the key points made by each side so far
2. Pose a thoughtful question to redirect or deepen the debate if needed
3. Call on the next speaker (alternate between PRO and CON positions)

The positions being debated are:
- PRO: {pro_statement}
- CON: {con_statement}

Recent messages:
{recent_messages_text}

Keep your moderation concise and balanced between both sides.

Your moderation:"""
        
        else:  # CLOSING
            return f"""You are the moderator of a debate on the topic: "{topic}".

This is the CLOSING phase. Your task is to:
1. Summarize the key arguments from both sides:
   - PRO: {pro_statement}
   - CON: {con_statement}
2. Highlight the strongest points made by each side
3. Thank all participants
4. Conclude the debate with a balanced summary
5. Do NOT declare a winner

Recent messages:
{recent_messages_text}

Your closing moderation:"""
    
    def _create_opening_prompt(self, speaker_id: str, speaker_role: str, 
                             context: Dict[str, Any]) -> str:
        """오프닝 단계 프롬프트 생성"""
        topic = self.room_data.get('title', 'the topic')
        
        stance_instruction = ""
        if speaker_role == ParticipantRole.PRO:
            stance_instruction = f"You strongly SUPPORT the idea that {topic}. Present your opening statement arguing in favor."
        elif speaker_role == ParticipantRole.CON:
            stance_instruction = f"You strongly OPPOSE the idea that {topic}. Present your opening statement arguing against it."
        else:  # NEUTRAL
            stance_instruction = f"You have a NEUTRAL stance on whether {topic}. Present your opening statement with a balanced view."
        
        return f"""You are {speaker_id} participating in a structured debate.
Topic: {topic}

This is the OPENING phase of the debate. Introduce your position clearly and concisely.
{stance_instruction}

Keep your opening statement focused and under 200 words. Do not respond to others yet.
Speak in your philosophical voice and draw on your key ideas.

Your opening statement:"""
    
    def _create_discussion_prompt(self, speaker_id: str, speaker_role: str, 
                                context: Dict[str, Any]) -> str:
        """토론 단계 프롬프트 생성"""
        topic = self.room_data.get('title', 'the topic')
        recent_messages = context.get('recent_messages', [])
        
        # 최근 5개 메시지만 포함
        recent_messages_text = "\n".join([
            f"{msg.get('sender', 'Unknown')} ({self._get_role_display(msg.get('sender', ''))}): {msg.get('text', '')}" 
            for msg in recent_messages[-5:]
        ])
        
        stance_instruction = ""
        if speaker_role == ParticipantRole.PRO:
            stance_instruction = f"You support the idea that {topic}. Defend this position and counter opposing arguments."
        elif speaker_role == ParticipantRole.CON:
            stance_instruction = f"You oppose the idea that {topic}. Attack the opposing position and strengthen your own arguments."
        else:  # NEUTRAL
            stance_instruction = f"You are neutral on whether {topic}. Analyze both sides fairly or suggest compromise positions."
        
        return f"""You are {speaker_id} participating in an ongoing debate.
Topic: {topic}

This is the DISCUSSION phase. Respond to previous points and develop arguments.
{stance_instruction}

Recent messages:
{recent_messages_text}

Keep your response focused, under 150 words, and directly engage with recent points.
Speak in your philosophical voice and draw on your key ideas.

Your response:"""
    
    def _create_closing_prompt(self, speaker_id: str, speaker_role: str, 
                             context: Dict[str, Any]) -> str:
        """마무리 단계 프롬프트 생성"""
        topic = self.room_data.get('title', 'the topic')
        key_points = self.debate_state.get("key_points", [])
        
        # 주요 논점 추출 (역할별로 그룹화)
        pro_points = [point for point in key_points if point.get('role') == ParticipantRole.PRO]
        con_points = [point for point in key_points if point.get('role') == ParticipantRole.CON]
        
        pro_points_text = "\n".join([f"- {point.get('text', '')}" for point in pro_points[:3]])
        con_points_text = "\n".join([f"- {point.get('text', '')}" for point in con_points[:3]])
        
        stance_instruction = ""
        if speaker_role == ParticipantRole.PRO:
            stance_instruction = f"You support the idea that {topic}. Summarize why your position is stronger."
        elif speaker_role == ParticipantRole.CON:
            stance_instruction = f"You oppose the idea that {topic}. Summarize why your position is stronger."
        else:  # NEUTRAL
            stance_instruction = f"You are neutral on whether {topic}. Provide a balanced conclusion about the debate."
        
        return f"""You are {speaker_id} concluding a structured debate.
Topic: {topic}

This is the CLOSING phase of the debate. Summarize your position and the strongest arguments.
{stance_instruction}

Key supporting points:
{pro_points_text}

Key opposing points:
{con_points_text}

Keep your closing statement focused and under 200 words.
Speak in your philosophical voice and draw on your key ideas.

Your closing statement:"""
    
    def _get_role_display(self, speaker_id: str) -> str:
        """화자 ID에 해당하는 역할 표시 텍스트 반환"""
        if speaker_id in self.pro_participants:
            return "Pro"
        elif speaker_id in self.con_participants:
            return "Con"
        else:
            return "Neutral"
    
    def get_next_speaker(self) -> Dict[str, Any]:
        """
        토론 단계와 순서에 따른 다음 발언자 결정
        
        Returns:
            다음 발언자 정보
        """
        current_stage = self.debate_state["current_stage"]
        turn_count = self.debate_state["turn_count"]
        
        if current_stage == DebateStage.COMPLETED:
            logger.info(f"Debate is completed in room {self.room_id}, no next speaker")
            return {
                "speaker_id": None, 
                "role": None, 
                "status": "completed",
                "is_user": False,
                "display_message": "토론이 종료되었습니다."
            }
        
        # 각 단계별 다음 발언자 결정
        if current_stage == DebateStage.OPENING:
            next_speaker = self._get_next_opening_speaker()
        elif current_stage == DebateStage.CLOSING:
            next_speaker = self._get_next_closing_speaker()
        else:  # DISCUSSION
            next_speaker = self._determine_discussion_speaker()
        
        # 사용자인지 여부 결정 (프론트엔드에서 사용)
        is_user = next_speaker["speaker_id"] in ["You", "User123"] or (
            self.room_data and 
            self.room_data.get("participants", {}).get("users", []) and
            next_speaker["speaker_id"] in self.room_data["participants"]["users"]
        )
        
        # 표시용 메시지 생성
        display_name = self._get_participant_name(next_speaker["speaker_id"])
        if next_speaker["role"] == ParticipantRole.MODERATOR:
            display_message = "진행자의 차례입니다."
        else:
            role_text = "찬성측" if next_speaker["role"] == ParticipantRole.PRO else (
                "반대측" if next_speaker["role"] == ParticipantRole.CON else "중립"
            )
            display_message = f"{display_name}({role_text})의 차례입니다."
        
        if is_user:
            display_message = "지금은 당신의 발언 차례입니다!"
        
        logger.info(f"Next speaker in room {self.room_id}: {next_speaker['speaker_id']} ({next_speaker['role']})")
        
        # 확장된 응답 형식
        return {
            "speaker_id": next_speaker["speaker_id"],
            "role": next_speaker["role"],
            "dialogue_type": self.dialogue_type,
            "debate_stage": current_stage,
            "status": "ready",
            "is_user": is_user,
            "display_message": display_message,
            "display_name": display_name
        }

    def _get_next_opening_speaker(self) -> Dict[str, str]:
        """오프닝 단계의 다음 발언자 결정"""
        speaking_history = self.debate_state["speaking_history"]
        roles_spoken = [entry.get("role") for entry in speaking_history]
        
        # 모더레이터가 아직 발언하지 않았다면
        if ParticipantRole.MODERATOR not in roles_spoken:
            logger.info(f"[DEBUG] 모더레이터가 아직 발언하지 않음, 모더레이터 선택")
            return {
                "speaker_id": self.debate_state["moderator_id"],
                "role": ParticipantRole.MODERATOR
            }
        
        # 모더레이터 발언 후, 찬성측이 아직 모두 발언하지 않았다면
        pro_speakers_history = [entry.get("speaker_id") for entry in speaking_history 
                               if entry.get("role") == ParticipantRole.PRO]
        
        if len(pro_speakers_history) < len(self.pro_participants):
            # 아직 발언하지 않은 찬성측 참가자 찾기
            for p in self.pro_participants:
                if p not in pro_speakers_history:
                    logger.info(f"[DEBUG] 찬성측 참가자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.PRO}
        
        # 찬성측이 모두 발언한 후, 반대측 참가자 찾기
        con_speakers_history = [entry.get("speaker_id") for entry in speaking_history 
                               if entry.get("role") == ParticipantRole.CON]
        
        if len(con_speakers_history) < len(self.con_participants):
            # 아직 발언하지 않은 반대측 참가자 찾기
            for p in self.con_participants:
                if p not in con_speakers_history:
                    logger.info(f"[DEBUG] 반대측 참가자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.CON}
        
        # 모두 발언했으면 다음 단계로 전환 (DISCUSSION)
        logger.info(f"[DEBUG] 모든 참가자가 오프닝 발언 완료, 토론 단계로 전환")
        self.debate_state["current_stage"] = DebateStage.DISCUSSION
        return self._determine_discussion_speaker()
    
    def _get_next_closing_speaker(self) -> Dict[str, str]:
        """마무리 단계의 다음 발언자 결정"""
        # 마무리 단계는 역순으로 발언
        total_speakers = len(self.speaking_order)
        turn_count = self.debate_state["turn_count"]
        index = (total_speakers - (turn_count % total_speakers) - 1) % total_speakers
        return self.speaking_order[index]
    
    def _determine_discussion_speaker(self) -> Dict[str, str]:
        """토론 단계에서 다음 발언자 결정 로직"""
        # 디버그 로깅 추가
        logger.info(f"[DEBUG] _determine_discussion_speaker 호출 - room_id: {self.room_id}")
        logger.info(f"[DEBUG] 현재 speaking_history 길이: {len(self.debate_state['speaking_history'])}")
        logger.info(f"[DEBUG] Pro 참가자: {self.pro_participants}")
        logger.info(f"[DEBUG] Con 참가자: {self.con_participants}")
        
        # 이전 발언 기록 확인
        if not self.debate_state["speaking_history"]:
            # 기록이 없으면 찬성측부터 시작
            logger.info(f"[DEBUG] 발언 기록 없음, 찬성측부터 시작")
            if self.pro_participants:
                return {"speaker_id": self.pro_participants[0], "role": ParticipantRole.PRO}
            elif self.neutral_participants:
                return {"speaker_id": self.neutral_participants[0], "role": ParticipantRole.NEUTRAL}
            else:
                return {"speaker_id": self.con_participants[0], "role": ParticipantRole.CON}
        
        # 현재 토론 단계의 발언 기록만 필터링
        current_stage = self.debate_state["current_stage"]
        stage_history = [s for s in self.debate_state["speaking_history"] 
                        if s.get("stage") == current_stage]
        
        # 가장 최근 발언자 정보
        last_speaker = self.debate_state["speaking_history"][-1]
        last_speaker_id = last_speaker.get("speaker_id")
        last_role = last_speaker.get("role", ParticipantRole.NEUTRAL)
        
        logger.info(f"[DEBUG] 최근 발언자: {last_speaker_id}, 역할: {last_role}")
        
        # 현재 단계에서 발언한 각 측의 참가자들 추적
        spoken_pro = [s.get("speaker_id") for s in stage_history 
                    if s.get("role") == ParticipantRole.PRO]
        spoken_con = [s.get("speaker_id") for s in stage_history 
                    if s.get("role") == ParticipantRole.CON]
        spoken_neutral = [s.get("speaker_id") for s in stage_history 
                        if s.get("role") == ParticipantRole.NEUTRAL]
        
        logger.info(f"[DEBUG] 현재 단계에서 발언한 Pro: {spoken_pro}")
        logger.info(f"[DEBUG] 현재 단계에서 발언한 Con: {spoken_con}")
        logger.info(f"[DEBUG] 현재 단계에서 발언한 Neutral: {spoken_neutral}")
        
        # 각 측의 모든 참가자가 발언했는지 확인
        all_pro_spoken = all(p in spoken_pro for p in self.pro_participants)
        all_con_spoken = all(p in spoken_con for p in self.con_participants)
        all_neutral_spoken = all(p in spoken_neutral for p in self.neutral_participants)
        
        logger.info(f"[DEBUG] 모든 Pro 발언 완료: {all_pro_spoken}")
        logger.info(f"[DEBUG] 모든 Con 발언 완료: {all_con_spoken}")
        logger.info(f"[DEBUG] 모든 Neutral 발언 완료: {all_neutral_spoken}")
        
        # 순서 결정 로직: 찬성측 모두 → 반대측 모두 → 중립 → 다시 찬성측 모두...
        
        # 마지막 발언이 어느 측이었는지에 따라 다음 발언자 결정
        if last_role == ParticipantRole.PRO:
            # Pro 측이 마지막으로 발언한 경우
            
            # 1. 아직 발언하지 않은 Pro 측 참가자가 있으면 먼저 발언하게 함
            for p in self.pro_participants:
                if p not in spoken_pro:
                    logger.info(f"[DEBUG] 아직 발언하지 않은 Pro 참가자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.PRO}
            
            # 2. 모든 Pro 측이 발언했으면 Con 측으로 전환
            logger.info(f"[DEBUG] 모든 Pro 참가자가 발언함, Con 측으로 전환")
            # Con 측에서 아직 발언하지 않은 첫 번째 참가자 선택
            for p in self.con_participants:
                if p not in spoken_con:
                    logger.info(f"[DEBUG] Con 측의 첫 발언자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.CON}
            
            # 3. 모든 Con도 발언했다면, Neutral 측으로 전환 (있을 경우)
            if self.neutral_participants:
                for p in self.neutral_participants:
                    if p not in spoken_neutral:
                        logger.info(f"[DEBUG] Neutral 측의 첫 발언자 선택: {p}")
                        return {"speaker_id": p, "role": ParticipantRole.NEUTRAL}
            
            # 4. 모두 발언했으면 다시 처음부터 (Pro 측부터)
            logger.info(f"[DEBUG] 모든 참가자가 발언 완료, 다시 Pro 측부터 시작")
            # 모든 참가자가 발언했으므로 speaking_history 초기화 고려
            return {"speaker_id": self.pro_participants[0], "role": ParticipantRole.PRO}
                
        elif last_role == ParticipantRole.CON:
            # Con 측이 마지막으로 발언한 경우
            
            # 1. 아직 발언하지 않은 Con 측 참가자가 있으면 먼저 발언하게 함
            for p in self.con_participants:
                if p not in spoken_con:
                    logger.info(f"[DEBUG] 아직 발언하지 않은 Con 참가자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.CON}
            
            # 2. 모든 Con 측이 발언했으면 Neutral 측으로 전환 (있을 경우)
            if self.neutral_participants:
                logger.info(f"[DEBUG] 모든 Con 참가자가 발언함, Neutral 측으로 전환")
                for p in self.neutral_participants:
                    if p not in spoken_neutral:
                        logger.info(f"[DEBUG] Neutral 측의 첫 발언자 선택: {p}")
                        return {"speaker_id": p, "role": ParticipantRole.NEUTRAL}
            
            # 3. Neutral이 없거나 모두 발언했다면, Pro 측으로 전환
            logger.info(f"[DEBUG] Neutral 측이 없거나 모두 발언함, Pro 측으로 전환")
            for p in self.pro_participants:
                if p not in spoken_pro:
                    logger.info(f"[DEBUG] Pro 측의 첫 발언자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.PRO}
            
            # 4. 모두 발언했으면 다시 처음부터 (Pro 측부터)
            logger.info(f"[DEBUG] 모든 참가자가 발언 완료, 다시 Pro 측부터 시작")
            # 모든 참가자가 발언했으므로 speaking_history 초기화 고려
            return {"speaker_id": self.pro_participants[0], "role": ParticipantRole.PRO}
                
        else:  # NEUTRAL
            # Neutral 측이 마지막으로 발언한 경우
            
            # 1. 아직 발언하지 않은 Neutral 측 참가자가 있으면 먼저 발언하게 함
            for p in self.neutral_participants:
                if p not in spoken_neutral:
                    logger.info(f"[DEBUG] 아직 발언하지 않은 Neutral 참가자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.NEUTRAL}
            
            # 2. 모든 Neutral 측이 발언했으면 Pro 측으로 전환
            logger.info(f"[DEBUG] 모든 Neutral 참가자가 발언함, Pro 측으로 전환")
            for p in self.pro_participants:
                if p not in spoken_pro:
                    logger.info(f"[DEBUG] Pro 측의 첫 발언자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.PRO}
            
            # 3. 모든 Pro도 발언했다면, Con 측으로 전환
            logger.info(f"[DEBUG] 모든 Pro 참가자가 발언함, Con 측으로 전환")
            for p in self.con_participants:
                if p not in spoken_con:
                    logger.info(f"[DEBUG] Con 측의 첫 발언자 선택: {p}")
                    return {"speaker_id": p, "role": ParticipantRole.CON}
            
            # 4. 모두 발언했으면 다시 처음부터 (Pro 측부터)
            logger.info(f"[DEBUG] 모든 참가자가 발언 완료, 다시 Pro 측부터 시작")
            # 모든 참가자가 발언했으므로 speaking_history 초기화 고려
            return {"speaker_id": self.pro_participants[0], "role": ParticipantRole.PRO}
    
    def get_dialogue_state(self) -> Dict[str, Any]:
        """
        현재 토론 상태 반환
        
        Returns:
            토론 상태 정보
        """
        return {
            "room_id": self.room_id,
            "dialogue_type": self.dialogue_type,
            "debate_state": self.debate_state,
            "pro_participants": self.pro_participants,
            "con_participants": self.con_participants,
            "neutral_participants": self.neutral_participants
        }
    
    def update_dialogue_state(self, state_update: Dict[str, Any]) -> None:
        """
        토론 상태 업데이트
        
        Args:
            state_update: 업데이트할 상태 정보
        """
        for key, value in state_update.items():
            if key in self.debate_state:
                self.debate_state[key] = value
        
        self.debate_state["last_update_time"] = time.time()
        logger.info(f"Updated debate state for room {self.room_id}")
    
    def extract_key_points(self, message: Dict[str, Any]) -> None:
        """
        메시지에서 주요 논점 추출하여 저장
        
        Args:
            message: 처리할 메시지
        """
        # 실제 구현에서는 AI를 사용하여 주요 논점 추출 가능
        # 이 예제에서는 단순화된 접근 사용
        speaker_id = message.get("sender")
        text = message.get("text", "")
        role = self._get_user_role(speaker_id)
        
        # 일정 길이 이상의 메시지만 주요 논점으로 고려
        if len(text) > 50:
            # 첫 100자만 주요 논점으로 추출 (실제로는 AI 요약 사용)
            key_point = text[:100] + ("..." if len(text) > 100 else "")
            
            self.debate_state["key_points"].append({
                "speaker_id": speaker_id,
                "role": role,
                "text": key_point,
                "timestamp": time.time()
            })
            
            logger.info(f"Extracted key point from {speaker_id} ({role}) in room {self.room_id}") 