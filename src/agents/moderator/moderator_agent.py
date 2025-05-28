"""
대화 중재자(Moderator) 에이전트 모듈

대화 진행, 발언권 관리, 요약 생성 등 중재자 역할을 수행하는 에이전트 구현
"""

from typing import Dict, Any, List, Optional
import os
import logging
from src.agents.base.agent import Agent
from src.dialogue.state.dialogue_state import DialogueStage, Message
from src.models.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)

class ModeratorAgent(Agent):
    """
    대화 중재자 에이전트
    
    대화 흐름 제어, 토론 진행, 발언권 분배 등의 역할 수행
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        중재자 에이전트 초기화
        
        Args:
            agent_id: 고유 식별자
            name: 에이전트 이름
            config: 설정 매개변수
        """
        super().__init__(agent_id, name, config)
        
        # 중재자 성격 설정
        self.strictness = config.get("parameters", {}).get("strictness", 0.7)
        self.neutrality = config.get("parameters", {}).get("neutrality", 0.9)
        
        # 찬반 입장 저장
        self.stance_statements = config.get("stance_statements", {})
        
        # 중재자 상태 초기화
        self.state.update({
            "current_speaker": None,
            "next_speakers": [],
            "turn_count": 0,
            "intervention_needed": False,
            "summary_points": []
        })
        
        # LLM 관리자 초기화
        self.llm_manager = LLMManager()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        에이전트로 요청 처리
        
        Args:
            input_data: 처리할 입력 데이터
            
        Returns:
            처리 결과
        """
        action = input_data.get("action", "")
        
        # 액션별 처리 로직
        if action == "generate_introduction":
            return self._generate_introduction(input_data.get("dialogue_state", {}))
            
        elif action == "generate_response":
            return self._generate_response_for_stage(input_data)
            
        elif action == "determine_next_speaker":
            return self._determine_next_speaker(
                input_data.get("dialogue_state", {}),
                input_data.get("participants", {}),
                input_data.get("current_stage", "")
            )
            
        elif action == "check_if_intervention_needed":
            # 단일 메시지 객체를 받아서 처리
            return self._moderate_qa_session(
                input_data.get("dialogue_state", {}),
                input_data.get("current_message", {})  # 리스트가 아닌 딕셔너리 객체
            )
        
        # 이전 방식 지원 (호환성)
        dialogue_state = input_data.get("dialogue_state")
        
        # dict인 경우 직접 current_stage 필드 접근
        if isinstance(dialogue_state, dict):
            current_stage = dialogue_state.get("current_stage", "INITIALIZATION")
        else:
            current_stage = getattr(dialogue_state, "stage", "INITIALIZATION")
        
        if current_stage == "INITIALIZATION":
            return self._generate_introduction(dialogue_state)
        elif current_stage == "MAIN_DISCUSSION":
            return self._manage_discussion(dialogue_state, input_data.get("current_message"))
        elif current_stage == "CONCLUSION":
            return self._generate_conclusion(dialogue_state)
        elif current_stage == "SUMMARY":
            return self._generate_summary(dialogue_state)
        else:
            return {"status": "success", "message": "대화 진행 중입니다."}
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        중재자 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        self.state.update(state_update)
    
    def _determine_next_speaker_external(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        외부 호출을 통한 다음 발언자 결정 (DebateDialogue에서 호출)
        
        Args:
            input_data: 다음 발언자 결정에 필요한 입력 데이터
            
        Returns:
            다음 발언자 정보
        """
        participants = input_data.get("participants", {})
        dialogue_state = input_data.get("dialogue_state", {})
        current_stage = input_data.get("current_stage", "")
        
        # 모더레이터가 발언해야 하는 단계
        moderator_stages = [
            "opening", 
            "moderator_summary_1", 
            "moderator_summary_2", 
            "moderator_summary_3", 
            "closing"
        ]
        
        # 단계별 다음 발언자 결정 로직
        if any(stage in current_stage for stage in moderator_stages):
            # 모더레이터 발언 단계
            return {
                "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
                "role": "moderator"
            }
        elif "pro_" in current_stage:
            # 찬성측 발언 단계
            pro_participants = participants.get("pro", [])
            if pro_participants:
                return {
                    "speaker_id": pro_participants[0],
                    "role": "pro"
                }
        elif "con_" in current_stage:
            # 반대측 발언 단계
            con_participants = participants.get("con", [])
            if con_participants:
                return {
                    "speaker_id": con_participants[0],
                    "role": "con"
                }
        elif "con_to_pro" in current_stage:
            # 질의응답: 반대->찬성
            speak_history = dialogue_state.get("speaking_history", [])
            recent_msgs = [msg for msg in speak_history if msg.get("stage") == current_stage]
            
            if not recent_msgs or len(recent_msgs) % 2 == 0:  # 시작 또는 짝수번째 메시지 후
                con_participants = participants.get("con", [])
                if con_participants:
                    return {
                        "speaker_id": con_participants[0],
                        "role": "con"
                    }
            else:  # 홀수번째 메시지 후
                pro_participants = participants.get("pro", [])
                if pro_participants:
                    return {
                        "speaker_id": pro_participants[0],
                        "role": "pro"
                    }
        elif "pro_to_con" in current_stage:
            # 질의응답: 찬성->반대
            speak_history = dialogue_state.get("speaking_history", [])
            recent_msgs = [msg for msg in speak_history if msg.get("stage") == current_stage]
            
            if not recent_msgs or len(recent_msgs) % 2 == 0:  # 시작 또는 짝수번째 메시지 후
                pro_participants = participants.get("pro", [])
                if pro_participants:
                    return {
                        "speaker_id": pro_participants[0],
                        "role": "pro"
                    }
            else:  # 홀수번째 메시지 후
                con_participants = participants.get("con", [])
                if con_participants:
                    return {
                        "speaker_id": con_participants[0],
                        "role": "con"
                    }
                    
        # 기본값: 모더레이터
        return {
            "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
            "role": "moderator"
        }
    
    def _generate_response_for_stage(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        현재 단계에 맞는 모더레이터 응답 생성
        
        Args:
            input_data: 응답 생성에 필요한 입력 데이터
            
        Returns:
            생성된 응답
        """
        dialogue_state = input_data.get("dialogue_state", {})
        context = input_data.get("context", {})
        current_stage = context.get("current_stage", "")
        
        if "opening" in current_stage:
            return self._generate_introduction(dialogue_state)
        elif "summary_1" in current_stage:
            return self._generate_summary(dialogue_state)
        elif "summary_2" in current_stage:
            return self._generate_summary(dialogue_state)
        elif "summary_3" in current_stage:
            return self._generate_summary(dialogue_state)
        elif "closing" in current_stage:
            return self._generate_conclusion(dialogue_state)
        else:
            # Generate a basic moderator message using the debate topic language
            topic = context.get("topic", "the topic")
            
            system_prompt = """
You are a debate moderator facilitating the discussion.
Your responses should be brief, neutral, and keep the debate moving forward.
"""

            user_prompt = f"""
As a moderator for the debate on "{topic}", provide a brief transition statement appropriate for this point in the debate.

Your statement should:
1. Be neutral and unbiased
2. Acknowledge the previous speaker(s)
3. Encourage the next speaker to continue
4. Be brief (1-2 sentences at most)

Important: Write your response in the SAME LANGUAGE as the debate topic. If the topic is in Korean, respond in Korean. If in English, respond in English, etc.
"""
            
            try:
                response = self.llm_manager.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    llm_model="gpt-4",
                    max_tokens=300
                )
                if response:
                    return {"status": "success", "message": response}
            except Exception as e:
                logger.error(f"Error generating basic moderator response: {str(e)}")
            
            # 기본 모더레이터 멘트
            return {
                "status": "success", 
                "message": "네, 계속 토론을 진행해 주세요."
            }
    
    def _generate_introduction(self, dialogue_state: Any) -> Dict[str, Any]:
        """
        토론 시작 소개 생성
        
        Args:
            dialogue_state: 현재 대화 상태
            
        Returns:
            생성된 소개 메시지
        """
        # input_data 형식 처리
        if isinstance(dialogue_state, dict) and "topic" in dialogue_state:
            topic = dialogue_state.get("topic", "the topic")
        elif isinstance(dialogue_state, dict) and "dialogue_state" in dialogue_state:
            # 새 형식 처리
            topic = dialogue_state.get("topic", "the topic")
            if not topic:
                topic = dialogue_state.get("dialogue_state", {}).get("topic", "the topic")
        else:
            # 이전 형식 처리
            topic = getattr(dialogue_state, "topic", "the topic")
            if not topic:
                topic = dialogue_state.get("topic", "the topic")
        
        # 두 위치에서 찬반 입장 정보 가져오기
        pro_statement = self.stance_statements.get("pro", "")
        con_statement = self.stance_statements.get("con", "")
        
        # 인자를 통해 전달된 찬반 입장이 있으면 우선 사용
        if isinstance(dialogue_state, dict) and "stance_statements" in dialogue_state:
            stance_statements = dialogue_state.get("stance_statements", {})
            if stance_statements:
                pro_statement = stance_statements.get("pro", pro_statement)
                con_statement = stance_statements.get("con", con_statement)
        
        # 참가자 정보 가져오기
        participants_info = dialogue_state.get("participants_info", {}) if isinstance(dialogue_state, dict) else {}
        pro_participants = participants_info.get("pro", [])
        con_participants = participants_info.get("con", [])
        
        # 참가자 이름 추출 (character_id에서 실제 이름으로 변환)
        pro_participant_names = []
        con_participant_names = []
        
        # 철학자 데이터 로드 시도
        try:
            import yaml
            import os
            philosophers_file = os.path.join(os.getcwd(), "philosophers", "debate_optimized.yaml")
            with open(philosophers_file, 'r', encoding='utf-8') as file:
                philosophers = yaml.safe_load(file)
        except Exception as e:
            philosophers = {}
        
        # PRO 참가자 이름 변환
        for participant_id in pro_participants:
            if participant_id in philosophers:
                name = philosophers[participant_id].get("name", participant_id)
                pro_participant_names.append(name)
            else:
                pro_participant_names.append(participant_id)
        
        # CON 참가자 이름 변환
        for participant_id in con_participants:
            if participant_id in philosophers:
                name = philosophers[participant_id].get("name", participant_id)
                con_participant_names.append(name)
            else:
                con_participant_names.append(participant_id)
        
        # 모더레이터 스타일 로드
        style_id = self.config.get("style_id", "0")  # 기본값은 "0" (Casual Young Moderator)
        
        try:
            import json
            import os
            
            # moderator_style.json 파일 경로
            style_file_path = os.path.join(
                os.path.dirname(__file__), 
                "moderator_style.json"
            )
            
            # 스타일 파일 로드
            with open(style_file_path, 'r', encoding='utf-8') as f:
                moderator_styles = json.load(f)
            
            # 지정된 스타일 ID의 템플릿 가져오기
            if style_id in moderator_styles:
                style_template = moderator_styles[style_id]["text"]
                style_name = moderator_styles[style_id]["name"]
                
                # 템플릿을 현재 토론 주제에 맞게 수정
                system_prompt = f"""
You are a debate moderator with the style: "{style_name}".
Your task is to create an opening introduction for a debate, following the style and tone of the provided template.
Adapt the template to the current debate topic while maintaining the same personality and speaking style.
Write a complete, comprehensive opening statement without cutting off in the middle.
"""

                user_prompt = f"""
You are moderating a debate on: "{topic}"

TEMPLATE STYLE (adapt this style to the current topic):
{style_template}

PARTICIPANTS:
- PRO side: {', '.join(pro_participant_names) if pro_participant_names else 'Pro participants'}
- CON side: {', '.join(con_participant_names) if con_participant_names else 'Con participants'}

Your task:
1. Create an opening introduction that matches the style and tone of the template
2. Introduce the debate topic: "{topic}"
3. Present the two opposing viewpoints:
   - PRO: {pro_statement}
   - CON: {con_statement}
4. Introduce the participants on both sides
5. Maintain the same personality and speaking style as shown in the template
6. Ensure your response is complete - do not stop mid-sentence

Important: Write your response in the SAME LANGUAGE as the debate topic. If the topic is in Korean, respond in Korean. If in English, respond in English, etc.
"""
                
                # LLM 호출
                try:
                    introduction = self.llm_manager.generate_response(
                        system_prompt=system_prompt, 
                        user_prompt=user_prompt,
                        llm_model="gpt-4",
                        max_tokens=1500
                    )
                    
                    if introduction:
                        return {
                            "status": "success",
                            "message": introduction
                        }
                        
                except Exception as e:
                    logger.error(f"Error generating styled introduction: {str(e)}")
                    
            else:
                logger.warning(f"Style ID '{style_id}' not found in moderator_style.json")
                
        except Exception as e:
            logger.error(f"Error loading moderator style: {str(e)}")
        
        # 스타일 로드 실패 시 기본 프롬프트 사용
        system_prompt = """
You are the moderator of a formal debate. Your role is to be neutral, fair, and to ensure the debate runs smoothly.
You will introduce the topic, explain the format, and set expectations for a respectful discussion.
Write a complete, comprehensive opening statement without cutting off in the middle.
"""

        user_prompt = f"""
You are the moderator of a formal debate on the topic: "{topic}".

PARTICIPANTS:
- PRO side: {', '.join(pro_participant_names) if pro_participant_names else 'Pro participants'}
- CON side: {', '.join(con_participant_names) if con_participant_names else 'Con participants'}

Your task is to give an opening introduction for the debate with the following details:
1. Welcome the audience and participants
2. Introduce the debate topic clearly
3. Present the two opposing viewpoints:
   - PRO: {pro_statement}
   - CON: {con_statement}
4. Introduce the participants on both sides
5. Set expectations for a respectful discussion

Important: Write your response in the SAME LANGUAGE as the debate topic. If the topic is in Korean, respond in Korean. If in English, respond in English, etc.

Your opening introduction should be formal, neutral, and engaging. Ensure your response is complete - do not stop mid-sentence.
"""
        
        # LLM 호출
        try:
            introduction = self.llm_manager.generate_response(
                system_prompt=system_prompt, 
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Error generating introduction: {str(e)}")
            introduction = ""
        
        # LLM 응답이 비어있는 경우 기본 응답 사용
        if not introduction:
            introduction = f"""안녕하세요, '{topic}'에 대한 토론에 오신 것을 환영합니다.
            
오늘 우리는 다음 입장에 대해 논의할 예정입니다:
- 찬성 입장: {pro_statement}
- 반대 입장: {con_statement}

토론은 다음과 같이 진행됩니다:
1. 양측의 입론 발표
2. 반론 단계
3. 상호 질의응답
4. 최종 결론 발표

모든 참가자들께서는 상대방의 의견을 존중하며 토론에 임해주시기 바랍니다.
먼저 찬성측부터 입장을 발표해 주시기 바랍니다."""
        
        result = {
            "status": "success",
            "message": introduction
        }
        
        return result
    
    def _manage_discussion(self, dialogue_state: Any, current_message: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        토론 진행 관리
        
        Args:
            dialogue_state: 현재 대화 상태
            current_message: 현재 처리 중인 메시지
            
        Returns:
            관리 결과 및 필요시 개입 메시지
        """
        # 현재 단계와 상황에 따라 다르게 대응
        current_stage = dialogue_state.get("current_stage", "")
        
        # QA 단계에서 모더레이터 개입이 필요한지 확인
        if "qa" in current_stage.lower():
            return self._moderate_qa_session(dialogue_state, current_message)
        
        # 일반적인 토론 진행 모니터링
        return {
            "status": "monitoring",
            "needs_intervention": False
        }
    
    def _moderate_qa_session(self, dialogue_state: Any, current_message: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        QA 세션 모더레이팅
        
        Args:
            dialogue_state: 현재 대화 상태
            current_message: 현재 처리 중인 메시지
            
        Returns:
            중재 결과 및 필요시 개입 메시지
        """
        if not current_message:
            return {"status": "monitoring", "needs_intervention": False}
        
        topic = dialogue_state.get("topic", "the topic")
        current_stage = dialogue_state.get("current_stage", "")
        
        # 영어로 프롬프트 작성
        system_prompt = """
You are a debate moderator who must decide when to intervene in a discussion.
You should only intervene if the conversation becomes unproductive, disrespectful, or goes significantly off-topic.
You will analyze a message and decide whether to intervene. 
If you decide to intervene, write a complete intervention message without cutting off in the middle.
"""

        user_prompt = f"""
You are moderating a debate Q&A session on: "{topic}".

TASK: Review this message and determine if you need to intervene. Intervene ONLY if:
1. The discussion is becoming hostile or disrespectful
2. The speaker is going significantly off-topic
3. The question/answer exceeds reasonable time limits
4. The participants are talking in circles without progress

Current message: "{current_message.get('text', '')}"

Based solely on this message content, do you need to intervene? 
Respond with a JSON format:
{{"should_intervene": true/false, "reason": "brief explanation if you decided to intervene", "intervention_message": "your intervention message if needed"}}

Important: If you decide to intervene, write your intervention message in the SAME LANGUAGE as the debate topic.
Ensure your messages are complete and do not cut off mid-sentence.
"""
        
        # LLM 호출
        try:
            intervention_response = self.llm_manager.generate_response(
                system_prompt=system_prompt, 
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Error checking for intervention: {str(e)}")
            return {"status": "monitoring", "should_intervene": False}
        
        # 응답 처리
        try:
            import json
            response_json = json.loads(intervention_response.replace("'", "\""))
            should_intervene = response_json.get("should_intervene", False)
            
            if should_intervene:
                return {
                    "status": "intervention",
                    "should_intervene": True,
                    "message": response_json.get("intervention_message", "토론 진행에 개입해야 할 것 같습니다. 주제에 집중해주시기 바랍니다."),
                    "reason": response_json.get("reason", "intervention_needed")
                }
            else:
                return {
                    "status": "monitoring",
                    "should_intervene": False
                }
        except Exception as e:
            logger.error(f"Error parsing intervention response: {str(e)}")
            # JSON 파싱 실패 시 기본 응답
            return {
                "status": "monitoring",
                "should_intervene": False
            }
    
    def _generate_summary(self, dialogue_state: Any) -> Dict[str, Any]:
        """
        토론 중간 요약 생성
        
        Args:
            dialogue_state: 현재 대화 상태
            
        Returns:
            생성된 요약 메시지
        """
        topic = dialogue_state.get("topic", "the topic")
        current_stage = dialogue_state.get("current_stage", "")
        speaking_history = dialogue_state.get("speaking_history", [])
        
        # 현재 단계에 따라 다른 요약 생성
        summary_type = ""
        if "summary_1" in current_stage.lower():
            summary_type = "after opening arguments"
        elif "summary_2" in current_stage.lower():
            summary_type = "after rebuttals"
        elif "summary_3" in current_stage.lower():
            summary_type = "after cross-examination"
        
        # 최근 메시지 추출 (단계별로 필터링)
        recent_stage_messages = []
        for msg in speaking_history:
            # 요약 단계 이전의 메시지만 포함
            if msg.get("stage") in self._get_previous_stages(current_stage):
                recent_stage_messages.append(msg)
        
        # 발언 추출
        recent_pro_messages = [msg.get("text", "") for msg in recent_stage_messages if msg.get("role") == "pro"]
        recent_con_messages = [msg.get("text", "") for msg in recent_stage_messages if msg.get("role") == "con"]
        
        # 발언을 문자열로 결합
        pro_arguments = ""
        for msg in recent_pro_messages:
            pro_arguments += msg + "\n"
            
        con_arguments = ""
        for msg in recent_con_messages:
            con_arguments += msg + "\n"
        
        # 프롬프트 작성
        system_prompt = """
You are the moderator of a formal debate. Your task is to create a balanced, fair summary of the arguments presented so far.
You should not show any bias toward either side of the debate and should accurately represent both positions.
Write a complete, comprehensive summary without cutting off in the middle.
"""

        # 4번째 지시사항 조건부 추가
        fourth_instruction = ""
        if 'summary_3' in current_stage.lower():
            fourth_instruction = "4. For the final summary (after cross-examination), ask participants to prepare their closing statements"
        else:
            fourth_instruction = ""

        user_prompt = f"""
You are the moderator of a debate on: "{topic}".

TASK: Create a summary {summary_type}. You should:
1. Summarize the key points made by both sides
2. Highlight areas of agreement and disagreement
3. Remain completely neutral and objective
{fourth_instruction}

PRO side arguments:
{pro_arguments}

CON side arguments:
{con_arguments}

Create a concise, balanced summary. Ensure your response is complete - do not stop mid-sentence.

Important: Write your summary in the SAME LANGUAGE as the debate topic. If the topic is in Korean, write in Korean. If in English, write in English, etc.
"""
        
        # LLM 호출
        try:
            summary = self.llm_manager.generate_response(
                system_prompt=system_prompt, 
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            summary = ""
        
        # LLM 응답이 비어있는 경우 기본 응답 사용
        if not summary:
            if "summary_1" in current_stage.lower():
                summary = f"""지금까지 '{topic}'에 대한 찬반 측의 입론을 들었습니다.

찬성 측에서는 주로 [찬성 측 핵심 포인트 요약]을 제시했습니다.
반대 측에서는 [반대 측 핵심 포인트 요약]을 주장했습니다.

이제 양측의 반론 단계로 넘어가겠습니다. 찬성 측부터 상대측 주장에 대한 반론을 제시해주시기 바랍니다."""
            elif "summary_2" in current_stage.lower():
                summary = f"""양측의 반론을 모두 들었습니다.

찬성 측은 [찬성 측 반론 요약]을 통해 반대 측 주장에 대응했습니다.
반대 측은 [반대 측 반론 요약]으로 찬성 측 입장을 반박했습니다.

이제 상호 질의응답 시간을 갖겠습니다. 먼저 반대 측에서 찬성 측에게 질문을 시작해주세요."""
            elif "summary_3" in current_stage.lower():
                summary = f"""질의응답 단계를 마쳤습니다.

토론 과정에서 양측은 [주요 쟁점 요약]에 대해 다양한 의견을 주고받았습니다.

이제 최종 결론 발표로 넘어가겠습니다. 찬성 측부터 최종 입장과 주요 논점을 정리해서 발표해주시기 바랍니다."""
            else:
                summary = f"""지금까지 '{topic}'에 대한 토론을 진행했습니다. 양측 모두 훌륭한 논점을 제시해 주셨습니다."""
        
        return {
            "status": "success",
            "message": summary
        }
    
    def _get_previous_stages(self, current_stage: str) -> List[str]:
        """현재 단계 이전의 모든 단계 반환"""
        from ...dialogue.types.debate_dialogue import DebateStage
        
        try:
            stage_sequence = DebateStage.STAGE_SEQUENCE
            current_index = stage_sequence.index(current_stage)
            return stage_sequence[:current_index]
        except (ValueError, AttributeError):
            return []
    
    def _generate_conclusion(self, dialogue_state: Any) -> Dict[str, Any]:
        """
        토론 마무리 생성
        
        Args:
            dialogue_state: 현재 대화 상태
            
        Returns:
            생성된 마무리 메시지
        """
        topic = dialogue_state.get("topic", "the topic")
        speaking_history = dialogue_state.get("speaking_history", [])
        
        # 찬성/반대 최종 결론 추출
        pro_conclusions = [msg.get("text", "") for msg in speaking_history 
                         if msg.get("stage") == "pro_conclusion"]
        con_conclusions = [msg.get("text", "") for msg in speaking_history 
                         if msg.get("stage") == "con_conclusion"]
        
        # 발언을 문자열로 결합
        pro_final_text = ""
        for text in pro_conclusions:
            pro_final_text += text + "\n"
            
        con_final_text = ""
        for text in con_conclusions:
            con_final_text += text + "\n"
        
        # 프롬프트 작성
        system_prompt = """
You are the moderator concluding a formal debate. Your task is to create a final closing statement that is fair, balanced, and does not reveal any bias toward either side.
You should thank all participants, summarize key points, and end the debate professionally.
Write a complete, comprehensive closing statement without cutting off in the middle.
"""

        user_prompt = f"""
You are the moderator concluding a debate on: "{topic}".

TASK: Create a closing statement that:
1. Thanks all participants for their contributions
2. Summarizes the strongest arguments from both sides without bias
3. Acknowledges the complexity of the issue
4. Avoids declaring a winner
5. Ends on a positive, forward-looking note

PRO side final statements:
{pro_final_text}

CON side final statements:
{con_final_text}

Write a balanced, respectful closing statement to end the debate. Ensure your response is complete - do not stop mid-sentence.

Important: Write your conclusion in the SAME LANGUAGE as the debate topic. If the topic is in Korean, write in Korean. If in English, write in English, etc.
"""
        
        # LLM 호출
        try:
            conclusion = self.llm_manager.generate_response(
                system_prompt=system_prompt, 
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1500
            )
        except Exception as e:
            logger.error(f"Error generating conclusion: {str(e)}")
            conclusion = ""
        
        # LLM 응답이 비어있는 경우 기본 응답 사용
        if not conclusion:
            conclusion = f"""'{topic}'에 대한 토론을 마무리하겠습니다.
            
양측 모두 설득력 있는 주장과 근거를 제시해 주셨습니다. 

찬성 측은 [찬성 측 주요 논점 요약]을 중심으로 논의를 전개했고,
반대 측은 [반대 측 주요 논점 요약]을 강조했습니다.

이 주제는 단순히 한쪽의 승리로 결론짓기 어려운 복잡한 사안임이 분명합니다. 
토론을 통해 우리 모두 다양한 관점에서 이 문제를 바라볼 수 있었습니다.

모든 참가자 여러분의 통찰력 있는 의견과 열정적인 참여에 감사드립니다.
이것으로 오늘의 토론을 마치겠습니다. 감사합니다."""
        
        return {
            "status": "success",
            "message": conclusion
        }
    
    def _check_if_intervention_needed(self, message: Dict[str, Any]) -> bool:
        """
        모더레이터 개입이 필요한지 확인
        
        Args:
            message: 검사할 메시지
            
        Returns:
            개입 필요 여부
        """
        if not message or "text" not in message:
            return False
        
        message_text = message.get("text", "")
        current_stage = message.get("stage", "")
        
        # 시스템 프롬프트
        system_prompt = """
You are a debate moderator who must decide when to intervene in a discussion.
You should only intervene if the conversation becomes unproductive, disrespectful, or goes significantly off-topic.
You will analyze a message and decide whether moderator intervention is needed.
"""

        # 유저 프롬프트
        user_prompt = f"""
You are moderating a debate. Analyze this message to determine if you need to intervene.

TASK: Evaluate if this message requires moderation. Intervene ONLY if:
1. The message contains disrespectful language or personal attacks
2. The speaker is significantly off-topic
3. The message is excessively long (taking too much speaking time)
4. The message contains factually incorrect information that could derail the debate

Message: "{message_text}"
Current debate stage: {current_stage}

Return a JSON with your decision:
{{"should_intervene": true/false, "reason": "brief explanation if intervention is needed"}}

Important: If you decide to intervene, write your intervention message in the SAME LANGUAGE as the debate topic.
"""
        
        try:
            # LLM 호출
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=300
            )
            
            # JSON 파싱
            import json
            import re
            
            # JSON 형식 찾기
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                response_json = json.loads(json_str)
                
                return response_json.get("should_intervene", False)
            
        except Exception as e:
            logger.error(f"Error checking if intervention needed: {str(e)}")
        
        # 기본적으로 개입 불필요로 판단
        return False
    
    def _check_transition_to_closing(self, dialogue_state: Any) -> Dict[str, bool]:
        """
        마무리 단계로 전환 여부 확인
        
        Args:
            dialogue_state: 현재 대화 상태
            
        Returns:
            전환 결정 결과
        """
        # 각 질의응답 단계에서 충분한 턴이 지나면 다음 단계로 진행
        current_stage = dialogue_state.get("current_stage", "")
        speaking_history = dialogue_state.get("speaking_history", [])
        
        # 현재 단계의 메시지만 필터링
        stage_messages = [msg for msg in speaking_history if msg.get("stage") == current_stage]
        
        # QA 단계에서 6턴 이상 진행됐는지 확인
        if "qa" in current_stage.lower() and len(stage_messages) >= 6:
            return {
                "should_transition": True,
                "reason": "qa_session_completed"
            }
        
        # If we need to generate a transition message, make sure it uses the same language as the topic
        if "qa" in current_stage.lower() and len(stage_messages) >= 4:
            topic = dialogue_state.get("topic", "the topic")
            
            system_prompt = """
You are a debate moderator deciding whether it's time to move to the next phase of the debate.
Analyze the conversation flow and decide if it's appropriate to transition.
"""

            user_prompt = f"""
You are moderating a debate on: "{topic}"

TASK: Analyze the current Q&A session and determine if it's time to move to the next phase.
Consider:
1. Have the key issues been addressed?
2. Is the conversation becoming repetitive?
3. Have both sides had equal opportunity to speak?

Return a JSON with your decision:
{{"should_transition": true/false, "reason": "brief explanation", "transition_message": "your transition message if needed"}}

Important: If you decide to transition, write your transition message in the SAME LANGUAGE as the debate topic.
"""
            
            # Rest of the method implementation...
        
        return {
            "should_transition": False,
            "reason": "qa_session_ongoing"
        }
    
    def _determine_next_speaker(self, dialogue_state: Any, participants: Dict[str, List[str]], current_stage: str) -> Dict[str, str]:
        """
        다음 발언자 결정
        
        Args:
            dialogue_state: 현재 대화 상태
            participants: 역할별 참가자 목록
            current_stage: 현재 토론 단계
            
        Returns:
            다음 발언자 정보
        """
        # 모더레이터가 항상 발언해야 하는 단계
        moderator_stages = [
            "opening", 
            "moderator_summary_1", 
            "moderator_summary_2", 
            "moderator_summary_3", 
            "closing"
        ]
        
        if any(stage in current_stage.lower() for stage in moderator_stages):
            return {
                "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
                "role": "moderator"
            }
        
        # QA 단계 특별 처리
        if "con_to_pro_qa" in current_stage.lower():
            return self._determine_qa_speaker(dialogue_state, participants, "con", "pro")
        elif "pro_to_con_qa" in current_stage.lower():
            return self._determine_qa_speaker(dialogue_state, participants, "pro", "con")
        
        # 각 단계별로 적절한 참가자 선택
        if "pro_argument" in current_stage.lower() or "pro_rebuttal" in current_stage.lower() or "pro_conclusion" in current_stage.lower():
            return self._select_next_role_speaker(dialogue_state, participants, "pro", current_stage)
        elif "con_argument" in current_stage.lower() or "con_rebuttal" in current_stage.lower() or "con_conclusion" in current_stage.lower():
            return self._select_next_role_speaker(dialogue_state, participants, "con", current_stage)
        
        # 기본값
        return {
            "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
            "role": "moderator"
        }
    
    def _determine_qa_speaker(self, dialogue_state: Any, participants: Dict[str, List[str]], questioner_role: str, answerer_role: str) -> Dict[str, str]:
        """
        QA 단계의 다음 발언자 결정
        
        Args:
            dialogue_state: 현재 대화 상태
            participants: 역할별 참가자 목록
            questioner_role: 질문자 역할
            answerer_role: 응답자 역할
            
        Returns:
            다음 발언자 정보
        """
        current_stage = dialogue_state.get("current_stage", "")
        speaking_history = dialogue_state.get("speaking_history", [])
        
        # 현재 단계의 발언 기록만 필터링
        qa_messages = [msg for msg in speaking_history if msg.get("stage") == current_stage]
        
        # QA 단계가 처음 시작하는 경우
        if not qa_messages:
            # 질문자 역할에서 첫 번째 참가자 선택
            if participants.get(questioner_role):
                return {
                    "speaker_id": participants[questioner_role][0],
                    "role": questioner_role
                }
        
        # 마지막 발언자의 역할 확인
        if qa_messages:
            last_role = qa_messages[-1].get("role")
            
            # 질문 후에는 응답, 응답 후에는 질문
            if last_role == questioner_role and participants.get(answerer_role):
                return {
                    "speaker_id": participants[answerer_role][0],
                    "role": answerer_role
                }
            elif last_role == answerer_role and participants.get(questioner_role):
                return {
                    "speaker_id": participants[questioner_role][0],
                    "role": questioner_role
                }
        
        # 기본값 (모더레이터 개입)
        return {
            "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
            "role": "moderator"
        }
    
    def _select_next_role_speaker(self, dialogue_state: Any, participants: Dict[str, List[str]], role: str, current_stage: str) -> Dict[str, str]:
        """
        특정 역할의 다음 발언자 선택
        
        Args:
            dialogue_state: 현재 대화 상태
            participants: 역할별 참가자 목록
            role: 발언자 역할
            current_stage: 현재 토론 단계
            
        Returns:
            다음 발언자 정보
        """
        speaking_history = dialogue_state.get("speaking_history", [])
        
        # 현재 단계에서 이미 발언한 참가자 필터링
        spoken_participants = set(
            msg.get("speaker_id") for msg in speaking_history 
            if msg.get("stage") == current_stage and msg.get("role") == role
        )
        
        # 아직 발언하지 않은 참가자 선택
        for participant_id in participants.get(role, []):
            if participant_id not in spoken_participants:
                return {
                    "speaker_id": participant_id,
                    "role": role
                }
        
        # 모든 참가자가 이미 발언한 경우
        return {
            "speaker_id": dialogue_state.get("moderator_id", "Moderator"),
            "role": "moderator"
        } 