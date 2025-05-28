"""
Debate Emotion Inference Module

이 모듈은 토론 맥락에서 참가자의 감정 상태를 추론하고 관리하는 기능을 제공합니다.
토론 과정에서의 발언 내용, 토론 단계, 그리고 찬반 입장을 고려하여 참가자의 감정을
추론하고 이를 프롬프트에 반영해 더 자연스러운 토론 흐름을 만들어냅니다.
"""

import logging
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from src.models.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)

class EmotionIntensity(Enum):
    """감정 강도를 나타내는 열거형"""
    NEUTRAL = 0
    VERY_MILD = 1
    MILD = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5

@dataclass
class DebateEmotionState:
    """토론 참가자의 감정 상태를 나타내는 클래스"""
    primary_emotion: str  # 주 감정
    intensity: EmotionIntensity  # 감정 강도
    secondary_emotion: Optional[str] = None  # 부 감정 (선택적)
    secondary_intensity: Optional[EmotionIntensity] = None  # 부 감정 강도
    reasoning: str = ""  # 이 감정 상태로 추론한 이유
    recommended_tone: str = ""  # 권장 어조

    def to_dict(self) -> Dict[str, Any]:
        """감정 상태를 딕셔너리로 변환"""
        result = {
            "primary_emotion": self.primary_emotion,
            "intensity": self.intensity.name,
            "intensity_value": self.intensity.value,
        }
        
        if self.secondary_emotion:
            result["secondary_emotion"] = self.secondary_emotion
            if self.secondary_intensity:
                result["secondary_intensity"] = self.secondary_intensity.name
                result["secondary_intensity_value"] = self.secondary_intensity.value
        
        if self.reasoning:
            result["reasoning"] = self.reasoning
            
        if self.recommended_tone:
            result["recommended_tone"] = self.recommended_tone
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DebateEmotionState':
        """딕셔너리에서 감정 상태 객체 생성"""
        primary_emotion = data.get("primary_emotion", "neutral")
        
        # 감정 강도 처리
        intensity_name = data.get("intensity", "NEUTRAL")
        try:
            intensity = EmotionIntensity[intensity_name]
        except (KeyError, TypeError):
            intensity = EmotionIntensity.NEUTRAL
        
        # 부 감정 처리
        secondary_emotion = data.get("secondary_emotion")
        secondary_intensity = None
        
        if "secondary_intensity" in data:
            try:
                secondary_intensity = EmotionIntensity[data["secondary_intensity"]]
            except (KeyError, TypeError):
                secondary_intensity = EmotionIntensity.NEUTRAL
        
        return cls(
            primary_emotion=primary_emotion,
            intensity=intensity,
            secondary_emotion=secondary_emotion,
            secondary_intensity=secondary_intensity,
            reasoning=data.get("reasoning", ""),
            recommended_tone=data.get("recommended_tone", "")
        )

    def __str__(self) -> str:
        result = f"{self.primary_emotion} ({self.intensity.name})"
        if self.secondary_emotion:
            result += f", {self.secondary_emotion}"
            if self.secondary_intensity:
                result += f" ({self.secondary_intensity.name})"
        if self.recommended_tone:
            result += f" - Tone: {self.recommended_tone}"
        return result


class DebateEmotionManager:
    """토론 감정 상태 관리 및 추론을 담당하는 클래스"""
    
    def __init__(self, llm_manager: LLMManager):
        """
        DebateEmotionManager 초기화
        
        Args:
            llm_manager: 감정 추론에 사용할 LLM 관리자
        """
        self.llm_manager = llm_manager
        self.emotion_cache = {}  # speaker_id -> DebateEmotionState
        
    def infer_emotion(self, 
                     speaker_id: str, 
                     speaker_role: str,
                     opponent_messages: List[Dict[str, Any]],
                     debate_topic: str,
                     debate_stage: str,
                     stance_statement: str = "",
                     speaker_personality: str = "") -> DebateEmotionState:
        """
        토론 상황에서 화자의 감정 상태를 추론
        
        Args:
            speaker_id: 화자 ID
            speaker_role: 화자 역할 (pro/con)
            opponent_messages: 상대측 메시지 목록
            debate_topic: 토론 주제
            debate_stage: 현재 토론 단계
            stance_statement: 화자의 입장 진술문
            speaker_personality: 화자의 성격 또는 특성 설명
            
        Returns:
            추론된 감정 상태
        """
        # 토론 대화 이력이 너무 적으면 기본 상태 반환
        if not opponent_messages:
            return DebateEmotionState(
                primary_emotion="analytical", 
                intensity=EmotionIntensity.MODERATE,
                reasoning="상대측 발언 데이터가 충분하지 않습니다.",
                recommended_tone="분석적이고 중립적인 어조로 발언하세요."
            )
        
        # 대화 이력을 텍스트로 변환
        opponent_text = self._format_opponent_messages(opponent_messages)
        
        # 단계별 감정 프롬프트 조정
        emotion_prompt_type = self._get_emotion_prompt_for_stage(debate_stage, speaker_role)
        
        # 감정 추론 시스템 프롬프트
        system_prompt = f"""
You are analyzing the emotional state of a debate participant who is about to speak in a formal debate.
Your role is to:
1. Analyze the emotional cues from the opponent's messages
2. Consider the current debate stage: {debate_stage}
3. Infer the appropriate emotional state for a {speaker_role} side debater
4. Recommend a tone of voice that would be effective in this debate context

Your analysis should be specific to a debate setting, where emotions serve rhetorical purposes and strategic objectives.
"""

        # 감정 추론 사용자 프롬프트
        user_prompt = f"""
DEBATE CONTEXT:
- Topic: "{debate_topic}"
- Current stage: {debate_stage}
- Debater's role: {speaker_role} side
- Debater's stance statement: "{stance_statement}"
{f"- Debater's personality: {speaker_personality}" if speaker_personality else ""}

OPPONENT'S RECENT MESSAGES:
{opponent_text}

TASK:
Analyze the context and determine the most appropriate emotional state for the {speaker_role} side debater to adopt in their next response.

Consider:
1. What emotional state would be most effective given the opponent's arguments?
2. How intense should this emotion be to be persuasive without seeming irrational?
3. What tone of voice would best serve the debater's rhetorical goals at this stage?

{emotion_prompt_type}

Respond with a JSON object with the following structure:
{{
  "primary_emotion": "analytical/passionate/convinced/skeptical/frustrated/angry/surprised/impressed/intellectually_stimulated/etc",
  "intensity": "NEUTRAL/VERY_MILD/MILD/MODERATE/STRONG/VERY_STRONG",
  "reasoning": "Brief explanation of why this emotional state is appropriate",
  "recommended_tone": "Brief description of the recommended tone of voice",
  "secondary_emotion": "Optional secondary emotion if relevant"
}}
"""
        
        # LLM을 사용하여 감정 추론
        try:
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=800
            )
            
            emotion_data = self._parse_emotion_response(response)
            emotion_state = DebateEmotionState.from_dict(emotion_data)
            
            # 캐시에 감정 상태 저장
            self.emotion_cache[speaker_id] = emotion_state
            
            return emotion_state
            
        except Exception as e:
            logger.error(f"토론 감정 추론 실패: {str(e)}")
            return DebateEmotionState(
                primary_emotion="analytical", 
                intensity=EmotionIntensity.MODERATE,
                reasoning="감정 추론 중 오류가 발생했습니다.",
                recommended_tone="논리적이고 차분한 어조로 발언하세요."
            )
    
    def get_emotion_prompt_enhancement(self, 
                                      speaker_id: str, 
                                      emotion_state: Optional[DebateEmotionState] = None) -> Dict[str, str]:
        """
        Generate text to incorporate emotional state into prompts
        
        Args:
            speaker_id: Speaker ID
            emotion_state: Emotional state (if none, retrieve from cache)
            
        Returns:
            Dictionary with prompt enhancement text
        """
        # If no emotion state provided, check cache
        if emotion_state is None:
            emotion_state = self.emotion_cache.get(speaker_id)
            
        # If still no emotion state, return neutral state
        if emotion_state is None:
            emotion_state = DebateEmotionState(
                primary_emotion="analytical", 
                intensity=EmotionIntensity.MODERATE,
                recommended_tone="Address the debate with logical and clear reasoning."
            )
        
        # Generate emotion description text
        emotion_description = f"You are currently feeling {emotion_state.primary_emotion} at a {emotion_state.intensity.name.lower()} intensity."
        if emotion_state.secondary_emotion:
            emotion_description += f" You are also feeling {emotion_state.secondary_emotion}"
            if emotion_state.secondary_intensity:
                emotion_description += f" at a {emotion_state.secondary_intensity.name.lower()} intensity"
            emotion_description += "."
            
        # Expression guide based on emotion
        recommended_tone = emotion_state.recommended_tone or self._get_expression_guide(emotion_state)
        
        return {
            "emotion_description": emotion_description,
            "recommended_tone": recommended_tone,
            "emotion_state": str(emotion_state)
        }
    
    def _format_opponent_messages(self, messages: List[Dict[str, Any]]) -> str:
        """상대측 메시지를 텍스트로 포맷팅"""
        formatted_messages = ""
        for msg in messages:
            role = msg.get("role", "Unknown")
            stage = msg.get("stage", "Unknown stage")
            text = msg.get("text", "")
            formatted_messages += f"[{stage}] {role}: {text}\n\n"
        return formatted_messages.strip()
    
    def _get_emotion_prompt_for_stage(self, debate_stage: str, speaker_role: str) -> str:
        """토론 단계별 감정 프롬프트 조정"""
        
        if "argument" in debate_stage.lower():
            return """For the main argument phase, consider emotions that would help establish credibility and persuasiveness."""
            
        elif "rebuttal" in debate_stage.lower():
            return """For the rebuttal phase, consider emotions that would help effectively counter the opponent's arguments 
while maintaining logical coherence. This might include controlled indignation, intellectual urgency, or passionate conviction."""
            
        elif "qa" in debate_stage.lower():
            if "con_to_pro" in debate_stage.lower() and speaker_role == "con":
                return """As a CON side questioner, consider emotions that would make your questions penetrating and thought-provoking."""
            elif "pro_to_con" in debate_stage.lower() and speaker_role == "pro":
                return """As a PRO side questioner, consider emotions that would make your questions penetrating and thought-provoking."""
            else:
                return """As the respondent in this Q&A phase, consider emotions that would help you appear measured and reasoned while under scrutiny."""
                
        elif "conclusion" in debate_stage.lower():
            return """For the conclusion phase, consider emotions that would leave a lasting impact and effectively summarize your position."""
            
        return """Consider which emotions would be most rhetorically effective at this stage of the debate."""
    
    def _parse_emotion_response(self, response: str) -> Dict[str, Any]:
        """Parse emotion information from LLM response"""
        # If already a dictionary
        if isinstance(response, dict):
            return self._normalize_emotion_data(response)
        
        # Try to parse JSON format
        try:
            import json
            import re
            
            # Extract JSON portion from string
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return self._normalize_emotion_data(data)
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            logger.error(f"JSON parsing failed: {str(e)}\nResponse: {response[:100]}...")
        
        # Text-based parsing (last resort)
        result = {
            "primary_emotion": "analytical",
            "intensity": "MODERATE",
            "reasoning": "Using default values due to parsing failure",
            "recommended_tone": "Address the debate with logical and clear reasoning."
        }
        
        # Simple keyword matching in case JSON parsing failed
        emotion_keywords = [
            # Core analytical emotions
            "analytical", "logical", "rational", "methodical", "systematic", 
            
            # Conviction emotions
            "passionate", "enthusiastic", "fervent", "ardent", "zealous",
            "convinced", "persuaded", "swayed", "converted", "influenced",
            
            # Confidence emotions
            "confident", "assured", "self-assured", "certain", "resolute",
            
            # Doubt emotions
            "skeptical", "doubtful", "suspicious", "unconvinced", "wary",
            "uncertain", "hesitant", "ambivalent", "undecided", "torn",
            
            # Critical emotions
            "critical", "challenging", "questioning", "probing", "scrutinizing",
            
            # Concern emotions
            "concerned", "worried", "troubled", "apprehensive", "anxious",
            
            # Understanding emotions
            "empathetic", "understanding", "compassionate", "sympathetic", "receptive",
            
            # Interest emotions
            "intrigued", "curious", "interested", "fascinated", "captivated",
            "intellectually_stimulated", "mentally_engaged", "thought_provoked",
            
            # Tactical emotions
            "calculated", "strategic", "tactical", "measured", "deliberate",
            
            # Disagreement emotions
            "frustrated", "irritated", "exasperated", "annoyed", "vexed",
            "angry", "indignant", "outraged", "incensed", "offended",
            
            # Agreement emotions
            "agreeable", "amenable", "concordant", "aligned", "in_accord",
            
            # Surprise emotions
            "surprised", "astonished", "amazed", "startled", "taken_aback",
            "impressed", "awed", "dazzled", "stunned", "overwhelmed",
            
            # Professional respect
            "respectful", "admiring", "acknowledging", "deferential", "appreciative",
            
            # Defensive emotions
            "defensive", "protective", "guarded", "vigilant", "cautious",
            
            # Confusion emotions
            "confused", "perplexed", "puzzled", "bewildered", "disoriented",
            
            # Satisfaction emotions
            "satisfied", "pleased", "content", "gratified", "fulfilled",
            
            # Disappointment emotions
            "disappointed", "let_down", "disheartened", "disillusioned", "crestfallen"
        ]
        
        for keyword in emotion_keywords:
            if keyword.lower() in response.lower():
                result["primary_emotion"] = keyword
                
                # Estimate intensity
                if "very strong" in response.lower() or "extreme" in response.lower():
                    result["intensity"] = "VERY_STRONG"
                elif "strong" in response.lower():
                    result["intensity"] = "STRONG"
                elif "moderate" in response.lower() or "medium" in response.lower():
                    result["intensity"] = "MODERATE"
                elif "mild" in response.lower() or "slight" in response.lower():
                    result["intensity"] = "MILD"
                elif "very mild" in response.lower() or "minimal" in response.lower():
                    result["intensity"] = "VERY_MILD"
                break
        
        return result
    
    def _normalize_emotion_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """감정 데이터 정규화"""
        # 기본 구조 확인
        normalized = {}
        
        # 주 감정 추출
        primary_emotion = data.get("primary_emotion", 
                                data.get("emotion", 
                                      data.get("primaryEmotion", "analytical")))
        normalized["primary_emotion"] = primary_emotion.lower()
        
        # 강도 추출 및 정규화
        intensity = data.get("intensity", 
                          data.get("emotion_intensity", 
                                data.get("emotionIntensity", "MODERATE")))
        
        # 강도가 숫자인 경우
        if isinstance(intensity, (int, float)):
            # 0-5 스케일로 변환
            value = min(max(int(intensity), 0), 5)
            normalized["intensity"] = EmotionIntensity(value).name
        # 강도가 문자열인 경우
        else:
            intensity_str = str(intensity).upper()
            # 정확한 열거형 이름 확인
            try:
                EmotionIntensity[intensity_str]
                normalized["intensity"] = intensity_str
            except KeyError:
                # 이름으로 매칭 안되면 키워드로 매칭 시도
                if any(x in intensity_str for x in ["VERY_STRONG", "EXTREME", "HIGHEST"]):
                    normalized["intensity"] = "VERY_STRONG"
                elif any(x in intensity_str for x in ["STRONG", "HIGH"]):
                    normalized["intensity"] = "STRONG"
                elif any(x in intensity_str for x in ["MODERATE", "MEDIUM", "MID"]):
                    normalized["intensity"] = "MODERATE"
                elif any(x in intensity_str for x in ["MILD", "LOW"]):
                    normalized["intensity"] = "MILD"
                elif any(x in intensity_str for x in ["VERY_MILD", "VERY_LOW", "LOWEST"]):
                    normalized["intensity"] = "VERY_MILD"
                else:
                    normalized["intensity"] = "MODERATE"  # 기본값: 중간 강도
        
        # 부 감정 처리
        secondary_emotion = data.get("secondary_emotion", 
                                  data.get("secondaryEmotion"))
        if secondary_emotion:
            normalized["secondary_emotion"] = secondary_emotion.lower()
            
            # 부 감정 강도
            secondary_intensity = data.get("secondary_intensity", 
                                        data.get("secondaryIntensity", "MILD"))
            
            # 부 감정 강도 정규화
            if isinstance(secondary_intensity, (int, float)):
                value = min(max(int(secondary_intensity), 0), 5)
                normalized["secondary_intensity"] = EmotionIntensity(value).name
            else:
                intensity_str = str(secondary_intensity).upper()
                try:
                    EmotionIntensity[intensity_str]
                    normalized["secondary_intensity"] = intensity_str
                except KeyError:
                    normalized["secondary_intensity"] = "MILD"
        
        # 추론 이유
        reasoning = data.get("reasoning", 
                          data.get("reason", 
                                data.get("explanation", "")))
        normalized["reasoning"] = reasoning
        
        # 권장 어조
        recommended_tone = data.get("recommended_tone", 
                                 data.get("tone", 
                                       data.get("speaking_tone", "")))
        normalized["recommended_tone"] = recommended_tone
        
        return normalized
    
    def _get_expression_guide(self, emotion_state: DebateEmotionState) -> str:
        """Generate expression guide based on emotional state"""
        primary = emotion_state.primary_emotion.lower()
        intensity = emotion_state.intensity
        
        # Expression guides for debate context
        debate_guides = {
            # Core analytical emotions
            "analytical": {
                EmotionIntensity.VERY_MILD: "Maintain a slightly analytical tone, focusing on logic in your statements.",
                EmotionIntensity.MILD: "Present your logic calmly and with clear structure.",
                EmotionIntensity.MODERATE: "Emphasize logical structure and evidence in your analytical tone.",
                EmotionIntensity.STRONG: "Demonstrate strong analytical reasoning, clearly identifying logical weaknesses in opposing arguments.",
                EmotionIntensity.VERY_STRONG: "Systematically deconstruct opposing arguments through sophisticated analysis and logical reasoning."
            },
            
            # Conviction emotions
            "passionate": {
                EmotionIntensity.VERY_MILD: "Express slight enthusiasm for the topic in your statements.",
                EmotionIntensity.MILD: "Show appropriate passion for the topic while speaking.",
                EmotionIntensity.MODERATE: "Emphasize the importance of your position with conviction.",
                EmotionIntensity.STRONG: "Channel strong passion into your arguments, effectively using emotion.",
                EmotionIntensity.VERY_STRONG: "Appeal to the audience's emotions with a highly passionate tone while emphasizing the importance of your position."
            },
            "convinced": {
                EmotionIntensity.VERY_MILD: "Acknowledge a reasonable point made by your opponent.",
                EmotionIntensity.MILD: "Incorporate an element of your opponent's argument into your response.",
                EmotionIntensity.MODERATE: "Openly acknowledge being partly persuaded while maintaining your core position.",
                EmotionIntensity.STRONG: "Reconsider aspects of your position in light of opposing evidence.",
                EmotionIntensity.VERY_STRONG: "Show significant shift in your thinking while integrating new perspectives."
            },
            
            # Confidence emotions
            "confident": {
                EmotionIntensity.VERY_MILD: "Speak with quiet confidence.",
                EmotionIntensity.MILD: "Present your points with steady, assured delivery.",
                EmotionIntensity.MODERATE: "Use a clear and firm tone when presenting your position.",
                EmotionIntensity.STRONG: "Project strong confidence with an assertive, assured attitude.",
                EmotionIntensity.VERY_STRONG: "Express absolute certainty with an authoritative and resolute tone."
            },
            
            # Doubt emotions
            "skeptical": {
                EmotionIntensity.VERY_MILD: "Raise gentle questions about the opposing view.",
                EmotionIntensity.MILD: "Express measured doubt about your opponent's claims.",
                EmotionIntensity.MODERATE: "Systematically question the weaknesses in your opponent's arguments.",
                EmotionIntensity.STRONG: "Show strong skepticism about the validity of opposing claims.",
                EmotionIntensity.VERY_STRONG: "Highlight fundamental flaws in your opponent's logic with profound skepticism."
            },
            "uncertain": {
                EmotionIntensity.VERY_MILD: "Acknowledge some complexity in the issue being debated.",
                EmotionIntensity.MILD: "Express thoughtful consideration of multiple perspectives.",
                EmotionIntensity.MODERATE: "Admit areas of uncertainty while maintaining your core arguments.",
                EmotionIntensity.STRONG: "Openly wrestle with the complexities of the topic, showing intellectual honesty.",
                EmotionIntensity.VERY_STRONG: "Acknowledge significant uncertainty while emphasizing the principles that guide your position."
            },
            
            # Critical emotions
            "critical": {
                EmotionIntensity.VERY_MILD: "Carefully raise a few counterpoints.",
                EmotionIntensity.MILD: "Calmly point out weaknesses in the opposing argument.",
                EmotionIntensity.MODERATE: "Present clear criticisms in a systematic way.",
                EmotionIntensity.STRONG: "Deliver strong critical analysis highlighting multiple problems in the opposing position.",
                EmotionIntensity.VERY_STRONG: "Systematically dismantle the opposing argument with thorough critical analysis."
            },
            
            # Concern emotions
            "concerned": {
                EmotionIntensity.VERY_MILD: "Express mild concern about potential implications.",
                EmotionIntensity.MILD: "Voice thoughtful concerns about specific aspects of the opposing position.",
                EmotionIntensity.MODERATE: "Articulate clear worries about the consequences of the opposing view.",
                EmotionIntensity.STRONG: "Emphasize serious concerns with supporting evidence and reasoning.",
                EmotionIntensity.VERY_STRONG: "Convey profound concern about the grave implications of the opposing position."
            },
            
            # Understanding emotions
            "empathetic": {
                EmotionIntensity.VERY_MILD: "Show basic understanding of the opposing perspective.",
                EmotionIntensity.MILD: "Acknowledge the valid aspects of your opponent's concerns.",
                EmotionIntensity.MODERATE: "Demonstrate genuine understanding of the opposing viewpoint before presenting counterarguments.",
                EmotionIntensity.STRONG: "Connect emotionally with the underlying values of the opposing position while maintaining your stance.",
                EmotionIntensity.VERY_STRONG: "Show deep appreciation for opposing concerns while redirecting toward your perspective."
            },
            
            # Interest emotions
            "curious": {
                EmotionIntensity.VERY_MILD: "Show subtle interest in exploring aspects of the opposing argument.",
                EmotionIntensity.MILD: "Ask thoughtful questions that explore the opposing position.",
                EmotionIntensity.MODERATE: "Demonstrate intellectual curiosity by deeply examining interesting points from your opponent.",
                EmotionIntensity.STRONG: "Engage enthusiastically with intriguing concepts from the opposing side.",
                EmotionIntensity.VERY_STRONG: "Show profound intellectual engagement with the most compelling aspects of the opposing argument."
            },
            "intellectually_stimulated": {
                EmotionIntensity.VERY_MILD: "Express appreciation for an insightful point raised by your opponent.",
                EmotionIntensity.MILD: "Build upon interesting concepts introduced in the debate.",
                EmotionIntensity.MODERATE: "Show clear engagement with the intellectual challenge presented.",
                EmotionIntensity.STRONG: "Acknowledge how the debate has expanded your thinking.",
                EmotionIntensity.VERY_STRONG: "Demonstrate how the intellectual exchange has led to new insights while maintaining your position."
            },
            
            # Disagreement emotions
            "frustrated": {
                EmotionIntensity.VERY_MILD: "Express mild disagreement while maintaining composure.",
                EmotionIntensity.MILD: "Show restrained frustration through focused counterarguments.",
                EmotionIntensity.MODERATE: "Channel your frustration into pointed rebuttals of key opposing points.",
                EmotionIntensity.STRONG: "Express clear frustration with logical fallacies or mischaracterizations.",
                EmotionIntensity.VERY_STRONG: "Convey significant frustration while redirecting energy into systematic refutation."
            },
            "angry": {
                EmotionIntensity.VERY_MILD: "Express firm disagreement while maintaining professional tone.",
                EmotionIntensity.MILD: "Show controlled objection to particularly problematic points.",
                EmotionIntensity.MODERATE: "Convey appropriate indignation regarding serious flaws in reasoning.",
                EmotionIntensity.STRONG: "Channel righteous disagreement into powerful counterarguments.",
                EmotionIntensity.VERY_STRONG: "Transform strong objection into passionate defense of your position's principles."
            },
            
            # Agreement emotions
            "agreeable": {
                EmotionIntensity.VERY_MILD: "Acknowledge minor points of agreement before presenting your case.",
                EmotionIntensity.MILD: "Build on areas of common ground while maintaining your distinct position.",
                EmotionIntensity.MODERATE: "Emphasize shared values and goals before explaining differences.",
                EmotionIntensity.STRONG: "Actively seek synthesis between opposing viewpoints where possible.",
                EmotionIntensity.VERY_STRONG: "Focus primarily on building consensus while gently addressing remaining differences."
            },
            
            # Surprise emotions
            "surprised": {
                EmotionIntensity.VERY_MILD: "Express mild interest in unexpected points raised.",
                EmotionIntensity.MILD: "Acknowledge surprising elements in your opponent's argument.",
                EmotionIntensity.MODERATE: "Show genuine surprise at novel perspectives, then respond thoughtfully.",
                EmotionIntensity.STRONG: "Express significant surprise before recalibrating your response.",
                EmotionIntensity.VERY_STRONG: "Acknowledge being genuinely taken aback, then respond with careful reconsideration."
            },
            "impressed": {
                EmotionIntensity.VERY_MILD: "Give subtle acknowledgment to the quality of opposing arguments.",
                EmotionIntensity.MILD: "Express measured appreciation for strong points made by your opponent.",
                EmotionIntensity.MODERATE: "Openly acknowledge impressive reasoning before offering your perspective.",
                EmotionIntensity.STRONG: "Show significant respect for your opponent's argumentation skills.",
                EmotionIntensity.VERY_STRONG: "Express profound respect while maintaining your position on substantive grounds."
            },
            
            # Defensive emotions
            "defensive": {
                EmotionIntensity.VERY_MILD: "Calmly clarify potential misunderstandings of your position.",
                EmotionIntensity.MILD: "Address criticisms directly while maintaining composure.",
                EmotionIntensity.MODERATE: "Firmly defend your position against significant challenges.",
                EmotionIntensity.STRONG: "Vigorously protect your core arguments while addressing criticisms point by point.",
                EmotionIntensity.VERY_STRONG: "Mount a comprehensive defense against major criticisms while reinforcing your central thesis."
            },
            
            # Confusion emotions
            "confused": {
                EmotionIntensity.VERY_MILD: "Politely seek clarification on specific points.",
                EmotionIntensity.MILD: "Request further explanation of complex or unclear arguments.",
                EmotionIntensity.MODERATE: "Openly acknowledge confusion about certain aspects and ask for elaboration.",
                EmotionIntensity.STRONG: "Express significant difficulty following the opposing logic and request restructured explanation.",
                EmotionIntensity.VERY_STRONG: "Directly address apparent contradictions or logical inconsistencies in the opposing argument."
            },
            
            # Satisfaction emotions
            "satisfied": {
                EmotionIntensity.VERY_MILD: "Express quiet confidence in how the debate is unfolding.",
                EmotionIntensity.MILD: "Show measured satisfaction with the strength of your position.",
                EmotionIntensity.MODERATE: "Demonstrate clear confidence in how your arguments stand against opposition.",
                EmotionIntensity.STRONG: "Project strong satisfaction with the validation of your key points.",
                EmotionIntensity.VERY_STRONG: "Express profound confidence in your position given the course of the debate."
            },
            
            # Disappointment emotions
            "disappointed": {
                EmotionIntensity.VERY_MILD: "Gently note when expected counterarguments aren't addressed.",
                EmotionIntensity.MILD: "Express measured disappointment with specific aspects of the opposing argument.",
                EmotionIntensity.MODERATE: "Show clear disappointment with the level of engagement with your key points.",
                EmotionIntensity.STRONG: "Directly address significant shortcomings in the opposing approach.",
                EmotionIntensity.VERY_STRONG: "Clearly articulate profound disappointment while redirecting to substantive issues."
            }
        }
        
        # Use debate-specific guide if available
        if primary in debate_guides and intensity in debate_guides[primary]:
            return debate_guides[primary][intensity]
        
        # Otherwise generate generic guide
        if intensity == EmotionIntensity.NEUTRAL:
            return "Maintain a neutral and balanced tone in the debate."
        elif intensity == EmotionIntensity.VERY_MILD:
            return f"Subtly incorporate a {primary} element in your debate approach."
        elif intensity == EmotionIntensity.MILD:
            return f"Use a mild {primary} tone to support your logical persuasion."
        elif intensity == EmotionIntensity.MODERATE:
            return f"Effectively utilize a moderate {primary} quality to enhance your persuasiveness."
        elif intensity == EmotionIntensity.STRONG:
            return f"Make {primary} a key element of your debate strategy while maintaining logical consistency."
        elif intensity == EmotionIntensity.VERY_STRONG:
            return f"Strategically employ a very strong {primary} quality, but avoid appearing overly emotional."
        
        return "Present your arguments with logical and persuasive reasoning."


# 토론 감정 추론 함수 (편의상 래퍼 함수)
def infer_debate_emotion(
    llm_manager: LLMManager,
    speaker_id: str,
    speaker_role: str,
    opponent_messages: List[Dict[str, Any]],
    debate_topic: str,
    debate_stage: str,
    stance_statement: str = "",
    speaker_personality: str = ""
) -> Dict[str, Any]:
    """
    토론 맥락에서 참가자의 감정을 추론하는 함수
    
    Args:
        llm_manager: LLM 관리자 인스턴스
        speaker_id: 화자 ID
        speaker_role: 화자 역할 (pro/con)
        opponent_messages: 상대측 메시지 목록
        debate_topic: 토론 주제
        debate_stage: 현재 토론 단계
        stance_statement: 화자의 입장 진술문
        speaker_personality: 화자의 성격 설명
        
    Returns:
        감정 상태 및 프롬프트 향상 정보를 담은 딕셔너리
    """
    emotion_manager = DebateEmotionManager(llm_manager)
    emotion_state = emotion_manager.infer_emotion(
        speaker_id=speaker_id,
        speaker_role=speaker_role,
        opponent_messages=opponent_messages,
        debate_topic=debate_topic,
        debate_stage=debate_stage,
        stance_statement=stance_statement,
        speaker_personality=speaker_personality
    )
    
    prompt_enhancement = emotion_manager.get_emotion_prompt_enhancement(
        speaker_id=speaker_id,
        emotion_state=emotion_state
    )
    
    result = {
        "emotion_state": emotion_state.to_dict(),
        "prompt_enhancement": prompt_enhancement
    }
    
    return result


# 감정 추론 결과를 프롬프트에 적용하는 함수
def apply_debate_emotion_to_prompt(
    system_prompt: str,
    user_prompt: str,
    emotion_data: Dict[str, Any]
) -> Tuple[str, str]:
    """
    토론 감정 추론 결과를 프롬프트에 적용하는 함수
    
    Args:
        system_prompt: 원본 시스템 프롬프트
        user_prompt: 원본 사용자 프롬프트
        emotion_data: infer_debate_emotion의 반환값
        
    Returns:
        감정이 적용된 (system_prompt, user_prompt) 튜플
    """
    if not emotion_data or "prompt_enhancement" not in emotion_data:
        return system_prompt, user_prompt
    
    enhancement = emotion_data["prompt_enhancement"]
    
    # 시스템 프롬프트에 감정 설명 추가
    enhanced_system_prompt = system_prompt
    emotion_description = enhancement.get("emotion_description", "")
    recommended_tone = enhancement.get("recommended_tone", "")
    
    if emotion_description and recommended_tone:
        # 시스템 프롬프트 끝에 감정 정보 추가
        if enhanced_system_prompt.strip().endswith("."):
            enhanced_system_prompt += "\n\n"
        else:
            enhanced_system_prompt += ".\n\n"
            
        enhanced_system_prompt += f"{emotion_description}\n{recommended_tone}"
    
    # 사용자 프롬프트는 그대로 유지 (필요시 여기서 수정 가능)
    enhanced_user_prompt = user_prompt
    
    return enhanced_system_prompt, enhanced_user_prompt 