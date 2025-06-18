"""
Emotion Inference Module

이 모듈은 대화 맥락에서 NPC의 감정 상태를 추론하고 관리하는 기능을 제공합니다.
최근 대화 이력을 분석하여 현재 발화자의 감정을 추론하고, 이를 프롬프트에 반영하여
더 자연스러운 대화 흐름을 만들어냅니다.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.prompts import load_prompt

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
class EmotionState:
    """NPC의 감정 상태를 나타내는 클래스"""
    primary_emotion: str  # 주 감정
    intensity: EmotionIntensity  # 감정 강도
    secondary_emotion: Optional[str] = None  # 부 감정 (선택적)
    secondary_intensity: Optional[EmotionIntensity] = None  # 부 감정 강도
    reasoning: str = ""  # 이 감정 상태로 추론한 이유

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
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionState':
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
            reasoning=data.get("reasoning", "")
        )

    def __str__(self) -> str:
        result = f"{self.primary_emotion} ({self.intensity.name})"
        if self.secondary_emotion:
            result += f", {self.secondary_emotion}"
            if self.secondary_intensity:
                result += f" ({self.secondary_intensity.name})"
        return result


class EmotionManager:
    """감정 상태 관리 및 추론을 담당하는 클래스"""
    
    def __init__(self, llm_manager: LLMManager):
        """
        EmotionManager 초기화
        
        Args:
            llm_manager: 감정 추론에 사용할 LLM 관리자
        """
        self.llm_manager = llm_manager
        self.emotion_cache = {}  # speaker_id -> EmotionState
        
    def infer_emotion(self, 
                     speaker_id: str, 
                     speaker_name: str,
                     recent_history: List[Dict[str, Any]], 
                     topic: str = "",
                     speaker_personality: str = "") -> EmotionState:
        """
        대화 이력을 기반으로 화자의 감정 상태를 추론
        
        Args:
            speaker_id: 화자 ID
            speaker_name: 화자 이름
            recent_history: 최근 대화 이력 (최근 3-5턴)
            topic: 대화 주제
            speaker_personality: 화자의 성격 또는 특성 설명
            
        Returns:
            추론된 감정 상태
        """
        # 대화 이력이 너무 적으면 기본 상태 반환
        if len(recent_history) < 2:
            return EmotionState(
                primary_emotion="neutral", 
                intensity=EmotionIntensity.NEUTRAL,
                reasoning="대화 이력이 충분하지 않습니다."
            )
        
        # 대화 이력을 텍스트로 변환
        conversation_text = self._format_conversation_history(recent_history)
        
        # 감정 추론 프롬프트 로드
        try:
            prompt_data = load_prompt('emotions', 'emotion_inference', 
                                    speaker_id=speaker_id,
                                    speaker_name=speaker_name,
                                    topic=topic,
                                    personality=speaker_personality,
                                    conversation_history=conversation_text)
        except Exception as e:
            logger.error(f"감정 추론 프롬프트 로드 실패: {e}")
            # 기본 프롬프트 사용
            prompt_data = {
                "system_prompt": "다음 대화 이력에 기반하여 화자의 현재 감정 상태를 추론하세요.",
                "user_prompt": f"화자: {speaker_name}\n대화 이력:\n{conversation_text}\n\n화자의 현재 감정 상태는 무엇인가요?"
            }
        
        # LLM을 사용하여 감정 추론
        try:
            response = self.llm_manager.generate_response(
                system_prompt=prompt_data["system_prompt"],
                user_prompt=prompt_data["user_prompt"],
                json_format=True
            )
            
            emotion_data = self._parse_emotion_response(response)
            emotion_state = EmotionState.from_dict(emotion_data)
            
            # 캐시에 감정 상태 저장
            self.emotion_cache[speaker_id] = emotion_state
            
            return emotion_state
            
        except Exception as e:
            logger.error(f"감정 추론 실패: {e}")
            return EmotionState(
                primary_emotion="neutral", 
                intensity=EmotionIntensity.NEUTRAL,
                reasoning="감정 추론 중 오류가 발생했습니다."
            )
    
    def get_emotion_prompt_enhancement(self, 
                                      speaker_id: str, 
                                      emotion_state: Optional[EmotionState] = None) -> Dict[str, str]:
        """
        감정 상태를 프롬프트에 반영할 수 있는 텍스트 생성
        
        Args:
            speaker_id: 화자 ID
            emotion_state: 감정 상태 (없으면 캐시에서 검색)
            
        Returns:
            프롬프트 향상을 위한 텍스트 딕셔너리
        """
        # 감정 상태가 없으면 캐시에서 검색
        if emotion_state is None:
            emotion_state = self.emotion_cache.get(speaker_id)
            
        # 캐시에도 없으면 중립 상태 반환
        if emotion_state is None:
            emotion_state = EmotionState(
                primary_emotion="neutral", 
                intensity=EmotionIntensity.NEUTRAL
            )
        
        # 감정 설명 텍스트 생성
        emotion_description = f"당신은 현재 {emotion_state.primary_emotion} 감정을 {emotion_state.intensity.name.lower()} 강도로 느끼고 있습니다."
        if emotion_state.secondary_emotion:
            emotion_description += f" 또한, {emotion_state.secondary_emotion} 감정도 "
            if emotion_state.secondary_intensity:
                emotion_description += f"{emotion_state.secondary_intensity.name.lower()} 강도로 "
            emotion_description += "느끼고 있습니다."
            
        # 감정에 따른 발화 스타일 지침
        expression_guide = self._get_expression_guide(emotion_state)
        
        return {
            "emotion_description": emotion_description,
            "expression_guide": expression_guide,
            "emotion_state": str(emotion_state)
        }
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """대화 이력을 텍스트로 포맷팅"""
        formatted_history = ""
        for entry in history:
            speaker = entry.get("speaker_name", entry.get("speaker_id", "알 수 없음"))
            text = entry.get("text", "")
            formatted_history += f"{speaker}: {text}\n\n"
        return formatted_history.strip()
    
    def _parse_emotion_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답에서 감정 정보 파싱"""
        # 이미 딕셔너리인 경우
        if isinstance(response, dict):
            return self._normalize_emotion_data(response)
        
        # JSON 형식 파싱 시도
        try:
            import json
            data = json.loads(response)
            return self._normalize_emotion_data(data)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 텍스트 기반 파싱 (최후의 수단)
        result = {
            "primary_emotion": "neutral",
            "intensity": "NEUTRAL",
            "reasoning": "감정 파싱 실패로 기본값 사용"
        }
        
        # 텍스트에서 감정 단어 검색
        emotion_keywords = {
            "기쁨": "happy", "행복": "happy", "즐거움": "happy",
            "슬픔": "sad", "우울": "sad", "비통": "sad",
            "화남": "angry", "분노": "angry", "짜증": "angry",
            "공포": "fearful", "두려움": "fearful", "불안": "fearful",
            "놀람": "surprised", "충격": "surprised",
            "혐오": "disgusted", "역겨움": "disgusted",
            "지루함": "bored", "무관심": "bored",
            "궁금함": "curious", "호기심": "curious",
            "감사": "grateful", "고마움": "grateful",
            "기대": "anticipating", "희망": "hopeful",
            "중립": "neutral", "냉정": "neutral"
        }
        
        for korean, english in emotion_keywords.items():
            if korean in response:
                result["primary_emotion"] = english
                
                # 강도 추정
                if "매우" in response or "강한" in response or "극도의" in response:
                    result["intensity"] = "VERY_STRONG"
                elif "상당한" in response or "강한" in response:
                    result["intensity"] = "STRONG"
                elif "적당한" in response or "중간" in response:
                    result["intensity"] = "MODERATE"
                elif "약한" in response or "미약한" in response:
                    result["intensity"] = "MILD"
                elif "아주 약한" in response or "매우 미약한" in response:
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
                                      data.get("primaryEmotion", "neutral")))
        normalized["primary_emotion"] = primary_emotion.lower()
        
        # 강도 추출 및 정규화
        intensity = data.get("intensity", 
                          data.get("emotion_intensity", 
                                data.get("emotionIntensity", "NEUTRAL")))
        
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
                    normalized["intensity"] = "NEUTRAL"
        
        # 부 감정 처리
        secondary_emotion = data.get("secondary_emotion", 
                                  data.get("secondaryEmotion"))
        if secondary_emotion:
            normalized["secondary_emotion"] = secondary_emotion.lower()
            
            # 부 감정 강도
            secondary_intensity = data.get("secondary_intensity", 
                                        data.get("secondaryIntensity", "NEUTRAL"))
            
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
                    normalized["secondary_intensity"] = "NEUTRAL"
        
        # 추론 이유
        reasoning = data.get("reasoning", 
                          data.get("reason", 
                                data.get("explanation", "")))
        normalized["reasoning"] = reasoning
        
        return normalized
    
    def _get_expression_guide(self, emotion_state: EmotionState) -> str:
        """감정 상태에 따른 표현 지침 생성"""
        primary = emotion_state.primary_emotion.lower()
        intensity = emotion_state.intensity
        
        # 기본 표현 지침
        guides = {
            "happy": {
                EmotionIntensity.VERY_MILD: "약간의 밝은 어조를 유지하세요.",
                EmotionIntensity.MILD: "미소를 띤 표현을 사용하세요.",
                EmotionIntensity.MODERATE: "긍정적인 단어를 더 많이 사용하고 활기찬 어조를 유지하세요.",
                EmotionIntensity.STRONG: "열정적이고 생동감 있는 표현을 사용하세요. 감탄사를 활용하세요.",
                EmotionIntensity.VERY_STRONG: "매우 흥분된 어조로 말하고, 감탄사와 긍정적인 강조를 많이 사용하세요."
            },
            "sad": {
                EmotionIntensity.VERY_MILD: "약간 가라앉은 어조를 사용하세요.",
                EmotionIntensity.MILD: "조금 망설이거나 주저하는 표현을 사용하세요.",
                EmotionIntensity.MODERATE: "우울한 어휘를 사용하고 느린 표현 방식을 채택하세요.",
                EmotionIntensity.STRONG: "상심하고 낙담한 표현을 사용하세요. 간간이 침묵을 표시하세요.",
                EmotionIntensity.VERY_STRONG: "깊은 슬픔을 드러내는 표현과 소외감, 절망감을 표현하세요."
            },
            "angry": {
                EmotionIntensity.VERY_MILD: "약간의 짜증을 표현하세요.",
                EmotionIntensity.MILD: "약간 직설적인 표현을 사용하세요.",
                EmotionIntensity.MODERATE: "불만이 담긴 단어를 사용하고 짧은 대답을 하세요.",
                EmotionIntensity.STRONG: "날카로운 질문과 강한 비난의 표현을 사용하세요.",
                EmotionIntensity.VERY_STRONG: "매우 격양된 어조로 짧고 강렬한 문장을 사용하세요."
            },
            "fearful": {
                EmotionIntensity.VERY_MILD: "약간의 불안감을 드러내세요.",
                EmotionIntensity.MILD: "조심스러운 표현과 의심스러운 어조를 사용하세요.",
                EmotionIntensity.MODERATE: "불안함이 담긴 단어를 사용하고 걱정을 표현하세요.",
                EmotionIntensity.STRONG: "두려움과 긴장감이 강하게 드러나는 표현을 사용하세요.",
                EmotionIntensity.VERY_STRONG: "극도의 공포와 불안을 표현하는 단절적인 문장을 사용하세요."
            },
            "surprised": {
                EmotionIntensity.VERY_MILD: "약간의 놀람을 표현하세요.",
                EmotionIntensity.MILD: "관심이 증가한 어조로 말하세요.",
                EmotionIntensity.MODERATE: "놀람을 나타내는 표현과 질문을 사용하세요.",
                EmotionIntensity.STRONG: "강한 놀람을 나타내는 감탄사와 질문을 사용하세요.",
                EmotionIntensity.VERY_STRONG: "매우 놀라고 충격받은 표현을 사용하세요."
            },
            "curious": {
                EmotionIntensity.VERY_MILD: "약간의 관심을 표현하세요.",
                EmotionIntensity.MILD: "호기심 어린 질문을 던지세요.",
                EmotionIntensity.MODERATE: "적극적으로 질문하고 탐구하는 어조를 사용하세요.",
                EmotionIntensity.STRONG: "많은 질문과 깊은 호기심을 표현하세요.",
                EmotionIntensity.VERY_STRONG: "매우 열정적으로 탐구하고 깊이 파고드는 질문을 하세요."
            }
        }
        
        # 기본 감정에 대한 지침이 있으면 사용
        if primary in guides and intensity in guides[primary]:
            return guides[primary][intensity]
        
        # 그 외의 경우 범용적인 지침 생성
        if intensity == EmotionIntensity.NEUTRAL:
            return "중립적이고 균형 잡힌 어조를 유지하세요."
        elif intensity == EmotionIntensity.VERY_MILD:
            return f"매우 약한 {primary} 감정을 드러내세요."
        elif intensity == EmotionIntensity.MILD:
            return f"약한 {primary} 감정을 표현하세요."
        elif intensity == EmotionIntensity.MODERATE:
            return f"중간 정도의 {primary} 감정을 분명히 표현하세요."
        elif intensity == EmotionIntensity.STRONG:
            return f"강한 {primary} 감정을 확실하게 드러내세요."
        elif intensity == EmotionIntensity.VERY_STRONG:
            return f"매우 강한 {primary} 감정을 극명하게 표현하세요."
        
        return "자연스러운 감정 표현을 사용하세요."


# 감정 추론 함수 (편의상 래퍼 함수)
def infer_emotion_from_context(
    llm_manager: LLMManager,
    speaker_id: str,
    speaker_name: str,
    recent_messages: List[Dict[str, Any]],
    topic: str = "",
    speaker_personality: str = ""
) -> Dict[str, Any]:
    """
    대화 맥락에서 NPC의 감정을 추론하는 함수
    
    Args:
        llm_manager: LLM 관리자 인스턴스
        speaker_id: 화자 ID
        speaker_name: 화자 이름
        recent_messages: 최근 대화 메시지 목록 (3-5턴)
        topic: 대화 주제
        speaker_personality: 화자의 성격 설명
        
    Returns:
        감정 상태 및 프롬프트 향상 정보를 담은 딕셔너리
    """
    emotion_manager = EmotionManager(llm_manager)
    emotion_state = emotion_manager.infer_emotion(
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        recent_history=recent_messages,
        topic=topic,
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
def apply_emotion_to_prompt(
    system_prompt: str,
    user_prompt: str,
    emotion_data: Dict[str, Any]
) -> Tuple[str, str]:
    """
    감정 추론 결과를 프롬프트에 적용하는 함수
    
    Args:
        system_prompt: 원본 시스템 프롬프트
        user_prompt: 원본 사용자 프롬프트
        emotion_data: infer_emotion_from_context의 반환값
        
    Returns:
        감정이 적용된 (system_prompt, user_prompt) 튜플
    """
    if not emotion_data or "prompt_enhancement" not in emotion_data:
        return system_prompt, user_prompt
    
    enhancement = emotion_data["prompt_enhancement"]
    
    # 시스템 프롬프트에 감정 설명 추가
    enhanced_system_prompt = system_prompt
    emotion_description = enhancement.get("emotion_description", "")
    expression_guide = enhancement.get("expression_guide", "")
    
    if emotion_description and expression_guide:
        # 시스템 프롬프트 끝에 감정 정보 추가
        if enhanced_system_prompt.strip().endswith("."):
            enhanced_system_prompt += "\n\n"
        else:
            enhanced_system_prompt += ".\n\n"
            
        enhanced_system_prompt += f"{emotion_description} {expression_guide}"
    
    # 사용자 프롬프트는 그대로 유지 (필요시 여기서 수정 가능)
    enhanced_user_prompt = user_prompt
    
    return enhanced_system_prompt, enhanced_user_prompt 