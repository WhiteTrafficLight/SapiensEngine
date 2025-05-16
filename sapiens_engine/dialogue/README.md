# Dialogue 모듈

Sapiens Engine의 대화 관리 모듈입니다. 다양한 형태의 대화와 토론을 관리하고 진행합니다.

## 감정 추론 모듈 사용법

`emotion_inference.py` 모듈은 최근 대화 이력을 기반으로 NPC의 감정 상태를 추론하고, 이를 프롬프트에 반영하여 더 자연스러운 대화를 생성하는 기능을 제공합니다.

### 기본 사용법

```python
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.dialogue.emotion_inference import infer_emotion_from_context, apply_emotion_to_prompt

# LLM 매니저 초기화
llm_manager = LLMManager(config_loader)

# 최근 대화 이력
recent_messages = [
    {
        "speaker_id": "socrates",
        "speaker_name": "소크라테스",
        "text": "당신의 주장은 논리적으로 모순이 있어 보입니다. 어떻게 설명하시겠습니까?"
    },
    {
        "speaker_id": "nietzsche",
        "speaker_name": "니체",
        "text": "진리란 것은 단지 세계를 해석하는 방식일 뿐입니다. 당신의 논리라는 것도 결국 권력에의 의지의 표현이죠."
    },
    {
        "speaker_id": "socrates",
        "speaker_name": "소크라테스",
        "text": "그렇다면 당신의 해석도 단지 하나의 관점에 불과하지 않습니까? 어떻게 자신의 주장을 특권화할 수 있습니까?"
    }
]

# 니체의 다음 발언을 위한 감정 추론
emotion_data = infer_emotion_from_context(
    llm_manager=llm_manager,
    speaker_id="nietzsche",
    speaker_name="니체",
    recent_messages=recent_messages,
    topic="진리와 인식론에 관한 토론",
    speaker_personality="허무주의적 철학자, 힘에의 의지, 반형이상학적 관점"
)

# 원래 프롬프트
system_prompt = "당신은 철학자 니체입니다. 허무주의, 힘에의 의지, 초인 등의 개념으로 유명합니다."
user_prompt = "소크라테스가 당신의 주장에 의문을 제기했습니다. 어떻게 대응하시겠습니까?"

# 감정 정보가 반영된 프롬프트
enhanced_system_prompt, enhanced_user_prompt = apply_emotion_to_prompt(
    system_prompt, user_prompt, emotion_data
)

# 향상된 프롬프트를 사용하여 응답 생성
response = llm_manager.generate_response(
    system_prompt=enhanced_system_prompt,
    user_prompt=enhanced_user_prompt
)
```

### 감정 상태 객체

감정 상태는 `EmotionState` 클래스로 표현됩니다:

```python
@dataclass
class EmotionState:
    primary_emotion: str  # 주 감정 (happy, sad, angry 등)
    intensity: EmotionIntensity  # 감정 강도
    secondary_emotion: Optional[str] = None  # 부 감정 (선택적)
    secondary_intensity: Optional[EmotionIntensity] = None  # 부 감정 강도
    reasoning: str = ""  # 이 감정 상태로 추론한 이유
```

감정 강도는 다음과 같은 열거형으로 표현됩니다:

```python
class EmotionIntensity(Enum):
    NEUTRAL = 0
    VERY_MILD = 1
    MILD = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5
```

### EmotionManager 직접 사용

더 세밀한 제어가 필요한 경우 `EmotionManager` 클래스를 직접 사용할 수 있습니다:

```python
from sapiens_engine.dialogue.emotion_inference import EmotionManager

# 감정 관리자 초기화
emotion_manager = EmotionManager(llm_manager)

# 감정 추론
emotion_state = emotion_manager.infer_emotion(
    speaker_id="nietzsche",
    speaker_name="니체",
    recent_history=recent_messages,
    topic="진리와 인식론에 관한 토론",
    speaker_personality="허무주의적 철학자"
)

# 추론된 감정 상태 사용
print(f"니체의 현재 감정: {emotion_state}")
print(f"주 감정: {emotion_state.primary_emotion} ({emotion_state.intensity.name})")
if emotion_state.secondary_emotion:
    print(f"부 감정: {emotion_state.secondary_emotion}")
print(f"추론 근거: {emotion_state.reasoning}")

# 프롬프트 향상 텍스트 생성
enhancement = emotion_manager.get_emotion_prompt_enhancement(
    speaker_id="nietzsche",
    emotion_state=emotion_state
)

# 향상된 프롬프트에 적용
system_prompt += f"\n\n{enhancement['emotion_description']} {enhancement['expression_guide']}"
```

### 대화 시스템에 통합

감정 추론 모듈은 다음과 같은 방식으로 대화 시스템에 통합할 수 있습니다:

1. **발화 전 감정 추론**: NPC의 발화 생성 전에 감정 추론을 수행하여 현재 감정 상태를 파악합니다.
2. **프롬프트 강화**: 추론된 감정 상태를 프롬프트에 반영하여 감정적으로 더 적절한 응답을 유도합니다.
3. **감정 기록 관리**: 대화 참여자별로 감정 상태 기록을 유지하여 감정 변화를 추적합니다.
4. **UI 강화**: 추론된 감정을 UI에 표시하여 사용자 경험을 향상시킵니다.

예시 통합 코드:

```python
class DialogueManager:
    def __init__(self, llm_manager):
        self.llm_manager = llm_manager
        self.emotion_manager = EmotionManager(llm_manager)
        self.message_history = []
        
    def generate_next_message(self, speaker_id, speaker_name, speaker_personality=""):
        # 최근 메시지 3-5개 가져오기
        recent_history = self.message_history[-5:] if len(self.message_history) > 5 else self.message_history
        
        # 감정 추론
        emotion_state = self.emotion_manager.infer_emotion(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            recent_history=recent_history,
            speaker_personality=speaker_personality
        )
        
        # 프롬프트 로드 및 감정 적용
        prompt_data = load_prompt('dialogue', 'standard_response', 
                                 speaker_id=speaker_id, 
                                 speaker_name=speaker_name)
        
        # 감정 상태 반영
        enhancement = self.emotion_manager.get_emotion_prompt_enhancement(
            speaker_id=speaker_id,
            emotion_state=emotion_state
        )
        
        system_prompt = prompt_data["system_prompt"]
        user_prompt = prompt_data["user_prompt"]
        
        # 감정 정보 추가
        system_prompt += f"\n\n{enhancement['emotion_description']} {enhancement['expression_guide']}"
        
        # 응답 생성
        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # 새 메시지 저장
        new_message = {
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "text": response,
            "emotion": emotion_state.to_dict()
        }
        
        self.message_history.append(new_message)
        return new_message 