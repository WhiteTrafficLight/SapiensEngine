# Sapiens Engine

에이전트 기반 대화 및 검색 증강 엔진

## 프로젝트 구조

```
src/
├── agents/                  # 모든 에이전트 관련 코드
│   ├── base/                # 기본 에이전트 추상 클래스
│   ├── moderator/           # 중재자 에이전트
│   ├── participant/         # 참여자 에이전트
│   ├── specialty/           # 전문 분야별 에이전트
│   ├── utility/             # 유틸리티 에이전트 (감정, 유머 등)
│   └── configs/             # 에이전트 구성 설정
│
├── rag/                     # RAG 관련 모듈
│   ├── retrieval/           # 검색 관련 (문서, 웹 등)
│   ├── generation/          # 생성 관련
│   ├── evaluation/          # 평가 관련
│   └── pipeline/            # 파이프라인 구성
│
├── dialogue/                # 대화 관리
│   ├── types/               # 대화 유형별 구현
│   ├── state/               # 대화 상태 관리
│   └── strategies/          # 대화 전략
│
├── utils/                   # 공통 유틸리티
│   ├── config/              # 설정 관리
│   ├── logging/             # 로깅
│   └── nlp/                 # NLP 유틸리티
│
├── models/                  # 모델 관련
│   ├── llm/                 # LLM 래퍼 및 관리
│   ├── embedding/           # 임베딩 모델
│   └── specialized/         # 감정, 유머 등 특수 모델
│
└── api/                     # API 인터페이스
    ├── rest/                # REST API
    └── websocket/           # 웹소켓 API
```

## 설치 방법

```bash
pip install -r requirements.txt
```

## 사용 예시

```python
from src.agents.factory import AgentFactory
from src.dialogue.state.dialogue_state import DialogueState

# 대화 상태 초기화
dialogue_state = DialogueState(
    dialogue_id="debate_001",
    dialogue_type="debate",
    topic="인공지능의 위험성"
)

# 에이전트 팩토리를 통한 에이전트 생성
factory = AgentFactory()
agents = factory.create_agents("debate")

# 각 에이전트 역할 확인
for role, agent in agents.items():
    print(f"역할: {role}, 이름: {agent.name}")
```

## 주요 기능

- 다양한 대화 유형별 에이전트 제공
- 웹 검색 및 로컬 문서 통합 검색 기능
- 대화 상태 관리 및 컨텍스트 유지
- 감정 및 유머 등 특수 능력 제공

# 철학자 찬반토론 실험 (Philosopher Debate Experiment)

이 Streamlit 애플리케이션은 철학자들 간의 찬반토론을 실험하고 프롬프팅 기법을 테스트하기 위한 도구입니다.

## 기능

- 철학자들을 찬성/반대 측으로 선택 가능
- 사용자도 토론에 참여 가능
- 토론 진행자의 오프닝 멘트 자동 생성
- 철학자들의 주장 자동 생성
- 실시간으로 토론 진행 상황 확인
- 토론 종료 후 진행자의 요약 생성

## 설치 및 실행

1. 의존성 설치:
```bash
pip install streamlit openai
```

2. OpenAI API 키 설정:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

3. 애플리케이션 실행:
```bash
streamlit run debate_experiment.py
```

## 사용 방법

1. 토론 주제를 입력합니다.
2. 필요한 경우 배경 설명을 추가합니다.
3. 찬성측과 반대측 철학자들을 선택합니다.
4. 원하는 경우 사용자가 토론에 참여할 수 있습니다.
5. "토론 시작" 버튼을 클릭하여 토론을 시작합니다.
6. 토론이 진행됨에 따라 "다음 발언" 버튼을 클릭하여 다음 단계로 진행합니다.
7. 사용자 차례에는 메시지를 입력하여 토론에 참여합니다.

## 목적

이 도구는 다음 목적으로 설계되었습니다:
- 찬반토론 프롬프팅 기법 실험
- 발언 순서 로직 테스트
- 철학자별 특성이 반영된 응답 생성 검증
- 모더레이터 오프닝 및 요약 생성 최적화

실험 결과는 향후 프론트엔드 애플리케이션과 연동될 예정입니다. 