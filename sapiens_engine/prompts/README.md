# Sapiens Engine Prompts

이 디렉토리는 Sapiens Engine에서 사용되는 다양한 프롬프트 파일들을 체계적으로 관리합니다. 각 프롬프트는 특정 대화 유형, 목소리 스타일, 감정 표현 등에 특화되어 있으며, 필요에 따라 쉽게 불러와 사용할 수 있습니다.

## 디렉토리 구조

```
sapiens_engine/prompts/
├── dialogue_types/    - 다양한 대화 유형별 프롬프트 (토론, 인터뷰, 강의 등)
├── voice_styles/      - 목소리와 말투 스타일 (격식체, 비격식체, 시적, 전문적 등)
├── emotions/          - 감정 표현 (기쁨, 슬픔, 분노 등)
├── context/           - 대화 맥락 관리와 흐름 제어
├── humor/             - 유머 관련 프롬프트
├── personality/       - 성격 특성 및 캐릭터 프롬프트
├── system/            - 시스템 및 일반 지침 프롬프트
├── templates/         - 재사용 가능한 프롬프트 템플릿
└── utils/             - 프롬프트 처리 유틸리티
```

## 파일 형식

프롬프트 파일은 주로 YAML 형식으로 작성되며, 다음과 같은 구조를 가집니다:

```yaml
# 프롬프트 메타데이터
name: "프롬프트 이름"
description: "이 프롬프트가 무엇을 하는지에 대한 설명"
version: "1.0"
author: "작성자"
tags: ["토론", "중재자", "오프닝"]

# 실제 프롬프트 내용
system_prompt: |
  당신은 전문적인 토론 진행자입니다. 주어진 주제에 대한 찬반토론의 시작 멘트를 작성해 주세요.
  한국어로 자연스럽게 토론을 소개하고, 참가자들을 소개하며, 토론의 규칙을 간략히 설명해 주세요.
  찬성과 반대 입장을 명확하게 제시하고, 첫 번째 발언자(찬성측)를 지명해 주세요.

user_prompt: |
  토론 주제: ${topic}
  
  배경 정보: ${context}
  
  찬성측 참가자: ${pro_participants}
  반대측 참가자: ${con_participants}
  
  첫 번째 발언자: ${first_speaker}
  
  토론 진행자로서 위 정보를 바탕으로 토론을 시작하는 멘트를 작성해 주세요.
```

## 사용 방법

### 기본 사용법

```python
from sapiens_engine.prompts import load_prompt

# 토론 중재자 프롬프트 로드
moderator_prompt = load_prompt('debate', 'moderator')

# 시스템 프롬프트와 사용자 프롬프트 분리 사용
system_prompt = moderator_prompt['system_prompt']
user_prompt = moderator_prompt['user_prompt']

# LLM 호출 시 사용
response = llm_manager.generate_response(system_prompt, user_prompt)
```

### 변수 치환을 통한 사용

```python
# 변수 치환이 있는 프롬프트 로드
opening_prompt = load_prompt('debate', 'opening', 
                           topic="인공지능의 윤리적 문제",
                           context="최근 AI 기술의 발전에 따른 윤리적 문제가 대두되고 있습니다.",
                           pro_participants="칸트, 아리스토텔레스",
                           con_participants="니체, 사르트르",
                           first_speaker="칸트")

# 변수가 치환된 프롬프트 사용
response = llm_manager.generate_response(
    opening_prompt['system_prompt'], 
    opening_prompt['user_prompt']
)
```

## 프롬프트 개발 지침

1. **명확한 구조화**: 각 프롬프트 파일은 '시스템 지시(system_prompt)'와 '사용자 지시(user_prompt)' 부분을 명확히 구분합니다.

2. **변수 사용**: 재사용성을 높이기 위해 템플릿 변수를 적극 활용합니다. 변수는 `${variable_name}` 형식으로 사용합니다.

3. **문서화**: 각 프롬프트 파일에는 메타데이터를 포함하여 용도와 사용법을 명확히 기록합니다.

4. **버전 관리**: 프롬프트 수정 시 버전을 업데이트하고 변경 내용을 기록합니다.

5. **테스트**: 새로운 프롬프트를 추가하기 전에 다양한 입력으로 테스트하여 견고성을 확인합니다.

## 예시 프롬프트

### 토론 중재자 오프닝 (dialogue_types/debate/moderator_opening.yaml)

```yaml
name: "토론 중재자 오프닝"
description: "토론의 시작 부분에서 중재자가 사용하는 프롬프트"
version: "1.0"
tags: ["토론", "중재자", "오프닝"]

system_prompt: |
  당신은 전문적인 토론 진행자입니다. 주어진 주제에 대한 찬반토론의 시작 멘트를 작성해 주세요.
  한국어로 자연스럽게 토론을 소개하고, 참가자들을 소개하며, 토론의 규칙을 간략히 설명해 주세요.
  
user_prompt: |
  토론 주제: ${topic}
  배경 정보: ${context}
  찬성측 참가자: ${pro_participants}
  반대측 참가자: ${con_participants}
  
  토론 진행자로서 위 정보를 바탕으로 토론을 시작하는 멘트를 작성해 주세요.
```

### 감정 표현 - 공감 (emotions/empathy.yaml)

```yaml
name: "공감 표현"
description: "사용자의 감정에 공감하는 응답을 생성"
version: "1.0"
tags: ["감정", "공감", "위로"]

system_prompt: |
  당신은 사용자의 감정에 깊게 공감하고 이해하는 AI 어시스턴트입니다.
  사용자의 감정 상태를 인식하고, 진정한 공감을 표현하세요.
  지나치게 해결책을 제시하기보다는 먼저 감정을 인정하고 공감하는 데 초점을 맞추세요.
  
user_prompt: |
  사용자의 상황: ${situation}
  감지된 감정: ${emotion}
  
  위 상황과 감정에 공감하는 응답을 생성해 주세요.
``` 