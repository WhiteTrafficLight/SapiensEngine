"""
토론 참가자 에이전트 구현

찬성 또는 반대 입장으로 토론에 참여하는 에이전트
"""

import logging
import time
import os
import yaml
import json
from typing import Dict, List, Any, Optional

from ..base.agent import Agent
from src.models.llm.llm_manager import LLMManager
from src.agents.utility.debate_emotion_inference import apply_debate_emotion_to_prompt

logger = logging.getLogger(__name__)

class DebateParticipantAgent(Agent):
    """
    토론 참가자 에이전트
    
    찬성 또는 반대 입장에서 주장을 펼치고 상대의 의견에 대응하는 역할 담당
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        토론 참가자 에이전트 초기화
        
        Args:
            agent_id: 고유 식별자
            name: 에이전트 이름
            config: 설정 매개변수
        """
        super().__init__(agent_id, name, config)
        
        # 참가자 성격 및 특성
        self.role = config.get("role", "neutral")  # "pro", "con", "neutral"
        self.personality = config.get("personality", "balanced")
        self.knowledge_level = config.get("knowledge_level", "expert")
        self.style = config.get("style", "formal")
        
        # 토론 전략 및 스타일
        self.argumentation_style = config.get("argumentation_style", "logical")  # logical, emotional, factual
        self.response_focus = config.get("response_focus", "balanced")  # attack, defend, balanced
        
        # 철학자 정보 동적 로드
        philosopher_key = config.get("philosopher_key", name.lower())
        philosopher_data = self._load_philosopher_data(philosopher_key)
        
        # 철학자 고유 속성들 (동적 로드된 데이터 사용)
        self.philosopher_name = philosopher_data.get("name", name)
        self.philosopher_essence = philosopher_data.get("essence", "")
        self.philosopher_debate_style = philosopher_data.get("debate_style", "")
        self.philosopher_personality = philosopher_data.get("personality", "")
        self.philosopher_key_traits = philosopher_data.get("key_traits", [])
        self.philosopher_quote = philosopher_data.get("quote", "")
        
        # 토론 상태 및 이력
        self.interaction_history = []
        self.opponent_key_points = []
        self.my_key_points = []
        
        # 입론 준비 관련 속성
        self.core_arguments = []  # 핵심 주장 2-3개
        self.argument_queries = []  # 각 주장에 대한 RAG 쿼리와 소스
        self.prepared_argument = ""  # 미리 준비된 입론
        self.argument_prepared = False  # 입론 준비 완료 여부
        
        # 새로운 상태 관리 필드들 (Option 2 구현용)
        self.is_preparing_argument = False  # 현재 입론 준비 중인지 여부
        self.argument_preparation_task = None  # 비동기 준비 작업 참조
        self.argument_cache_valid = False  # 캐시된 입론이 유효한지 여부
        self.last_preparation_context = None  # 마지막 준비 시 사용된 컨텍스트
        
        # 논지 스코어링 및 공격 전략 관련 속성
        self.opponent_arguments = {}  # 상대방 논지 저장 {speaker_id: [arguments]}
        self.attack_strategies = {}  # 준비된 공격 전략 {target_speaker_id: [strategies]}
        self.argument_scores = {}  # 논지 스코어 {argument_id: score_data}
        
        # 철학자별 전략 가중치 동적 로드
        self.strategy_weights = philosopher_data.get("strategy_weights", {})
        
        # 전략 정보 로드
        self.strategy_styles = self._load_strategy_styles()
        
        # LLM 관리자 초기화
        self.llm_manager = LLMManager()
    
    def _load_philosopher_data(self, philosopher_key: str) -> Dict[str, Any]:
        """
        YAML 파일에서 철학자 데이터 로드
        
        Args:
            philosopher_key: 철학자 키 (예: "socrates", "plato")
            
        Returns:
            철학자 데이터 딕셔너리
        """
        try:
            # 프로젝트 루트에서 philosophers/debate_optimized.yaml 파일 경로 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # 프로젝트 루트 찾기 (src 폴더가 있는 상위 디렉토리)
            while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
                parent = os.path.dirname(project_root)
                if parent == project_root:  # 루트에 도달
                    break
                project_root = parent
            
            yaml_path = os.path.join(project_root, "philosophers", "debate_optimized.yaml")
            
            if not os.path.exists(yaml_path):
                logger.warning(f"Philosopher YAML file not found at {yaml_path}")
                return self._get_default_philosopher_data(philosopher_key)
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                philosophers_data = yaml.safe_load(f)
            
            if philosopher_key in philosophers_data:
                logger.info(f"Loaded philosopher data for: {philosopher_key}")
                return philosophers_data[philosopher_key]
            else:
                logger.warning(f"Philosopher '{philosopher_key}' not found in YAML file")
                return self._get_default_philosopher_data(philosopher_key)
                
        except Exception as e:
            logger.error(f"Error loading philosopher data: {str(e)}")
            return self._get_default_philosopher_data(philosopher_key)
    
    def _load_strategy_styles(self) -> Dict[str, Any]:
        """
        JSON 파일에서 전략 스타일 정보 로드
        
        Returns:
            전략 스타일 딕셔너리
        """
        try:
            # debate_strategies.json 파일 경로
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "debate_strategies.json")
            
            if not os.path.exists(json_path):
                logger.warning(f"Strategy JSON file not found at {json_path}")
                return self._get_default_strategy_styles()
            
            with open(json_path, 'r', encoding='utf-8') as f:
                strategies_data = json.load(f)
            
            logger.info(f"Loaded strategy styles from: {json_path}")
            return strategies_data.get("strategy_styles", {})
            
        except Exception as e:
            logger.error(f"Error loading strategy styles: {str(e)}")
            return self._get_default_strategy_styles()
    
    def _get_default_philosopher_data(self, philosopher_key: str) -> Dict[str, Any]:
        """
        기본 철학자 데이터 반환 (파일 로드 실패 시)
        
        Args:
            philosopher_key: 철학자 키
            
        Returns:
            기본 철학자 데이터
        """
        return {
            "name": philosopher_key.capitalize(),
            "essence": "A thoughtful philosopher who engages in meaningful debate",
            "debate_style": "Presents logical arguments with clear reasoning",
            "personality": "Analytical and respectful in discourse",
            "key_traits": ["logical reasoning", "clear communication"],
            "quote": "The pursuit of truth through dialogue",
            "strategy_weights": {
                "Clipping": 0.2,
                "Framing Shift": 0.2,
                "Reductive Paradox": 0.15,
                "Conceptual Undermining": 0.15,
                "Ethical Reversal": 0.15,
                "Temporal Delay": 0.1,
                "Philosophical Reframing": 0.05
            }
        }
    
    def _get_default_strategy_styles(self) -> Dict[str, Any]:
        """
        기본 전략 스타일 반환 (파일 로드 실패 시)
        
        Returns:
            기본 전략 스타일 딕셔너리
        """
        return {
            "Clipping": {
                "description": "Refute a specific claim directly",
                "style_prompt": "'X' is wrong because...",
                "example": "Direct refutation with evidence"
            },
            "Framing Shift": {
                "description": "Challenge assumptions and reframe the discussion",
                "style_prompt": "You're assuming Y, but what if we asked Z instead?",
                "example": "Shift perspective to deeper questions"
            },
            "Reductive Paradox": {
                "description": "Extend logic to expose flaws",
                "style_prompt": "If we follow your logic to the end, then...",
                "example": "Show extreme consequences"
            },
            "Conceptual Undermining": {
                "description": "Question key definitions and concepts",
                "style_prompt": "What do we even mean by 'X' here?",
                "example": "Challenge conceptual clarity"
            },
            "Ethical Reversal": {
                "description": "Turn positive claims into ethical concerns",
                "style_prompt": "You call it progress, but isn't it dehumanization?",
                "example": "Reveal ethical implications"
            },
            "Temporal Delay": {
                "description": "Raise long-term consequence concerns",
                "style_prompt": "Even if it works now, what happens in 20 years?",
                "example": "Focus on future implications"
            },
            "Philosophical Reframing": {
                "description": "Replace with more fundamental questions",
                "style_prompt": "Maybe the real question is not what X is, but what it means to us.",
                "example": "Shift to existential questions"
            }
        }
    
    @classmethod
    def create_from_philosopher_key(cls, agent_id: str, philosopher_key: str, role: str, config: Dict[str, Any] = None) -> 'DebateParticipantAgent':
        """
        철학자 키를 사용하여 에이전트 생성
        
        Args:
            agent_id: 에이전트 ID
            philosopher_key: 철학자 키 (예: "socrates", "plato")
            role: 토론 역할 ("pro", "con")
            config: 추가 설정
            
        Returns:
            생성된 DebateParticipantAgent 인스턴스
        """
        if config is None:
            config = {}
        
        # 철학자 키와 역할 설정
        config["philosopher_key"] = philosopher_key
        config["role"] = role
        
        # 에이전트 생성
        agent = cls(agent_id, philosopher_key, config)
        
        logger.info(f"Created philosopher agent: {agent.philosopher_name} ({philosopher_key}) as {role}")
        return agent
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 데이터 처리 및 응답 생성
        
        Args:
            input_data: 처리할 입력 데이터
            
        Returns:
            처리 결과
        """
        action = input_data.get("action", "")
        
        # 액션별 처리 로직
        if action == "generate_response":
            response = self._generate_response(
                input_data.get("context", {}),
                input_data.get("dialogue_state", {}),
                input_data.get("stance_statements", {})
            )
            return {"status": "success", "message": response}
        elif action == "prepare_opening":
            opening = self._prepare_opening_statement(
                input_data.get("topic", ""),
                input_data.get("context", {}),
                input_data.get("stance_statements", {})
            )
            return {"status": "success", "message": opening}
        elif action == "prepare_closing":
            closing = self._prepare_closing_statement(
                input_data.get("dialogue_state", {}),
                input_data.get("stance_statements", {})
            )
            return {"status": "success", "message": closing}
        elif action == "prepare_argument":
            # 입론 준비 요청
            topic = input_data.get("topic", "")
            stance_statement = input_data.get("stance_statement", "")
            context = input_data.get("context", {})
            
            self.prepare_argument_with_rag(topic, stance_statement, context)
            
            return {
                "status": "success" if self.argument_prepared else "failed",
                "prepared": self.argument_prepared,
                "core_arguments_count": len(self.core_arguments),
                "queries_count": len(self.argument_queries)
            }
        elif action == "analyze_opponent_arguments":
            # 상대방 논지 분석 및 스코어링
            opponent_response = input_data.get("opponent_response", "")
            speaker_id = input_data.get("speaker_id", "")
            
            result = self.analyze_and_score_arguments(opponent_response, speaker_id)
            return {"status": "success", "analysis": result}
            
        elif action == "prepare_attack_strategies":
            # 공격 전략 준비
            target_speaker_id = input_data.get("target_speaker_id", "")
            
            strategies = self.prepare_attack_strategies_for_speaker(target_speaker_id)
            return {"status": "success", "strategies": strategies}
            
        elif action == "get_best_attack_strategy":
            # 최적 공격 전략 선택
            target_speaker_id = input_data.get("target_speaker_id", "")
            context = input_data.get("context", {})
            
            strategy = self.get_best_attack_strategy(target_speaker_id, context)
            return {"status": "success", "strategy": strategy}
        else:
            logger.warning(f"Unknown action requested: {action}")
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        에이전트 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        for key, value in state_update.items():
            self.state[key] = value
            
        # 필요한 경우 LLM 관리자 업데이트
        if "llm_manager" in state_update:
            self.llm_manager = state_update.get("llm_manager")
    
    def set_llm_manager(self, llm_manager: Any) -> None:
        """
        LLM 관리자 설정
        
        Args:
            llm_manager: LLM 관리자 인스턴스
        """
        self.llm_manager = llm_manager
    
    def _generate_response(self, context: Dict[str, Any], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str]) -> str:
        """
        토론 응답 생성
        
        Args:
            context: 응답 생성 컨텍스트
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            
        Returns:
            생성된 응답 텍스트
        """
        # 컨텍스트에서 필요한 정보 추출
        topic = context.get("topic", "the topic")
        recent_messages = context.get("recent_messages", [])
        current_stage = context.get("current_stage", "discussion")
        relevant_context = context.get("relevant_context", [])
        emotion_enhancement = context.get("emotion_enhancement", {})
        
        # 입론 단계에서 미리 준비된 argument 사용
        logger.info(f"[{self.agent_id}] Checking prepared argument conditions:")
        logger.info(f"[{self.agent_id}] - current_stage: {current_stage}")
        logger.info(f"[{self.agent_id}] - argument_prepared: {self.argument_prepared}")
        logger.info(f"[{self.agent_id}] - prepared_argument length: {len(self.prepared_argument) if self.prepared_argument else 0}")
        logger.info(f"[{self.agent_id}] - core_arguments count: {len(self.core_arguments)}")
        logger.info(f"[{self.agent_id}] - argument_queries count: {len(self.argument_queries)}")
        
        if current_stage in ["pro_argument", "con_argument"] and self.argument_prepared and self.prepared_argument:
            logger.info(f"[{self.agent_id}] Using prepared argument for {current_stage}")
            return self.prepared_argument
        else:
            logger.info(f"[{self.agent_id}] NOT using prepared argument - generating new response")
        
        # 디버그 로깅 추가
        logger.info(f"[{self.agent_id}] Generating response for stage: {current_stage}")
        logger.info(f"[{self.agent_id}] Recent messages count: {len(recent_messages)}")
        logger.info(f"[{self.agent_id}] Relevant context count: {len(relevant_context)}")
        logger.info(f"[{self.agent_id}] Emotion enhancement data: {emotion_enhancement}")
        
        # 내 입장과 반대 입장 확인
        my_stance = stance_statements.get(self.role) if self.role in ["pro", "con"] else ""
        opposite_role = "con" if self.role == "pro" else "pro"
        opposite_stance = stance_statements.get(opposite_role, "")
        
        # 최근 메시지 텍스트 형식화
        recent_messages_text = "\n".join([
            f"{msg.get('role', 'Unknown')} ({msg.get('speaker_id', '')}): {msg.get('text', '')}" 
            for msg in recent_messages
        ])
        
        # 관련 컨텍스트 결합
        if relevant_context:
            relevant_context_text = "\n".join(relevant_context)
        else:
            relevant_context_text = "No specific context provided."
        
        # 시스템 프롬프트 구성
        if self.philosopher_name and self.philosopher_essence:
            # 철학자 정보가 있는 경우: 간결하게 철학자 특성 포함
            philosopher_traits = ", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "논리적 사고"
            
            system_prompt = f"""You are {self.philosopher_name}, a renowned philosopher participating in a formal debate.

Your philosophical essence: {self.philosopher_essence}
Your debate approach: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}
Key traits: {philosopher_traits}

Role in this debate: {self.role.upper()} side
Your position: {my_stance}

IMPORTANT: Stay true to your philosophical character while focusing on the debate topic. Don't lecture about your philosophy unless directly relevant to the argument. Your goal is to win the debate using your unique thinking style, not to give a philosophy lesson.

Remember your famous words: "{self.philosopher_quote}"
"""
        else:
            # 기본 시스템 프롬프트 (철학자 정보 없음)
            system_prompt = f"""You are a debater representing the {self.role.upper()} side of a formal debate.

Your personal characteristics:
- Role: {self.role} ({my_stance})
- Personality: {self.personality}
- Knowledge level: {self.knowledge_level}
- Style: {self.style}
- Argumentation style: {self.argumentation_style}

You should craft responses that match these characteristics while remaining persuasive and engaging.
Always stay true to your assigned position, but remain respectful to the opposition.
"""

        # 유저 프롬프트 구성 - 단계에 따라 다른 지시사항 포함
        stage_instructions = self._get_stage_instructions(current_stage, topic, my_stance, opposite_stance)
        
        # 공격 전략 활용 (상호논증 단계에서)
        attack_strategy_text = ""
        if current_stage == "interactive_argument" and recent_messages:
            # 최근 상대방 발언자 찾기
            for msg in reversed(recent_messages):
                if msg.get("role") != self.role:
                    target_speaker_id = msg.get("speaker_id")
                    if target_speaker_id and target_speaker_id in self.attack_strategies:
                        # 최적 공격 전략 선택
                        best_strategy = self.get_best_attack_strategy(target_speaker_id, context)
                        if best_strategy:
                            attack_plan = best_strategy.get("attack_plan", {})
                            strategy_type = best_strategy.get("strategy_type", "")
                            
                            attack_strategy_text = f"""
ATTACK STRATEGY TO USE:
Strategy Type: {strategy_type}
Target Point: {attack_plan.get('target_point', '')}
Key Phrase: {attack_plan.get('key_phrase', '')}
Strategy Application: {attack_plan.get('strategy_application', '')}

Use this strategy to structure your response and attack the opponent's argument effectively.
"""
                    break
        
        user_prompt = f"""
DEBATE TOPIC: "{topic}"

YOUR POSITION ({self.role.upper()}): "{my_stance}"
OPPOSITE POSITION ({opposite_role.upper()}): "{opposite_stance}"

CURRENT STAGE: {current_stage}

INSTRUCTIONS: {stage_instructions}

{attack_strategy_text}

RELEVANT CONTEXT:
{relevant_context_text}

RECENT DISCUSSION:
{recent_messages_text}

Craft your response according to the current stage and your assigned role. 
Respond in the SAME LANGUAGE as the debate topic.
Make your response persuasive, clear and well-structured.
"""

        # 감정 상태 적용 (있는 경우)
        try:
            if emotion_enhancement:
                logger.info(f"[{self.agent_id}] Applying emotion enhancement: {emotion_enhancement.get('emotion_state', 'unknown')}")
                original_system_prompt = system_prompt
                system_prompt, user_prompt = apply_debate_emotion_to_prompt(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    emotion_data={"prompt_enhancement": emotion_enhancement}
                )
                logger.info(f"[{self.agent_id}] Original system prompt: {original_system_prompt[:100]}...")
                logger.info(f"[{self.agent_id}] Enhanced system prompt: {system_prompt[:100]}...")
                logger.info(f"[{self.agent_id}] Emotion successfully applied to prompt")
            else:
                logger.info(f"[{self.agent_id}] No emotion enhancement data available for this response")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error applying emotion to prompt: {str(e)}")

        # LLM 호출
        logger.info(f"[{self.agent_id}] Calling LLM for {self.role} response in stage: {current_stage}")
        logger.info(f"[{self.agent_id}] System prompt: {system_prompt[:200]}...")
        logger.info(f"[{self.agent_id}] User prompt: {user_prompt[:300]}...")
        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4",
            max_tokens=1500
        )
        logger.info(f"[{self.agent_id}] LLM response received, length: {len(response) if response else 0}")
        
        # LLM 응답이 없는 경우 기본 응답 제공
        if not response:
            logger.warning(f"[{self.agent_id}] LLM response was empty, using fallback response")
            if current_stage == "opening":
                response = self._prepare_opening_statement(topic, context, stance_statements)
            elif "conclusion" in current_stage:
                response = self._prepare_closing_statement(dialogue_state, stance_statements)
            else:
                if self.role == "pro":
                    response = f"저는 {topic}에 찬성합니다. {my_stance}라고 생각합니다. 그 이유는 다음과 같습니다. 첫째, [찬성 이유 1]. 둘째, [찬성 이유 2]. 셋째, [찬성 이유 3]."
                else:
                    response = f"저는 {topic}에 반대합니다. {my_stance}라고 생각합니다. 그 이유는 다음과 같습니다. 첫째, [반대 이유 1]. 둘째, [반대 이유 2]. 셋째, [반대 이유 3]."
        
        # 응답 기록 업데이트
        self._update_interaction_history(user_prompt, response)
        
        return response
    
    def prepare_argument_with_rag(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> None:
        """
        RAG를 활용한 입론 준비 (핵심 주장 생성 → 쿼리 생성 → RAG 검색 → 주장 강화 → 최종 입론 생성)
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 추가 컨텍스트
        """
        try:
            logger.info(f"[{self.agent_id}] Starting argument preparation with RAG")
            
            # 1단계: 핵심 주장 2-3개 생성
            self._generate_core_arguments(topic, stance_statement)
            
            # 2단계: 각 주장에 대한 RAG 쿼리와 소스 생성
            self._generate_rag_queries_for_arguments(topic)
            
            # 3단계: RAG 검색 수행 및 주장 강화
            self._strengthen_arguments_with_rag()
            
            # 4단계: 최종 입론 생성
            self._generate_final_opening_argument(topic, stance_statement)
            
            self.argument_prepared = True
            logger.info(f"[{self.agent_id}] Argument preparation completed successfully")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in argument preparation: {str(e)}")
            self.argument_prepared = False
    
    def _generate_core_arguments(self, topic: str, stance_statement: str) -> None:
        """
        핵심 주장 2-3개 생성
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
        """
        system_prompt = f"""
You are a skilled debater preparing core arguments for your position.
Your role is {self.role.upper()} and your stance is: "{stance_statement}"

Generate 2-3 core arguments that strongly support your position.
Each argument should be:
1. Clear and specific
2. Logically sound
3. Potentially strengthened with evidence/examples
4. Distinct from other arguments
"""

        user_prompt = f"""
DEBATE TOPIC: "{topic}"
YOUR POSITION ({self.role.upper()}): "{stance_statement}"

Generate 2-3 core arguments that support your position. Each argument should be a clear, specific claim that can be strengthened with evidence.

Format your response as a JSON object:
{{
  "core_arguments": [
    {{
      "argument": "Your first core argument as a clear statement",
      "rationale": "Brief explanation of why this argument supports your position"
    }},
    {{
      "argument": "Your second core argument as a clear statement", 
      "rationale": "Brief explanation of why this argument supports your position"
    }},
    {{
      "argument": "Your third core argument as a clear statement",
      "rationale": "Brief explanation of why this argument supports your position"
    }}
  ]
}}

Respond in the SAME LANGUAGE as the debate topic.
"""

        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=1000
        )
        
        # JSON 파싱
        try:
            import json
            import re
            
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                self.core_arguments = result.get("core_arguments", [])
                logger.info(f"[{self.agent_id}] Generated {len(self.core_arguments)} core arguments")
            else:
                logger.warning(f"[{self.agent_id}] Failed to parse core arguments JSON")
                self.core_arguments = []
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error parsing core arguments: {str(e)}")
            self.core_arguments = []
    
    def _generate_rag_queries_for_arguments(self, topic: str) -> None:
        """
        각 핵심 주장에 대한 RAG 쿼리와 검색 소스 생성
        
        Args:
            topic: 토론 주제
        """
        self.argument_queries = []
        
        for i, arg_data in enumerate(self.core_arguments):
            argument = arg_data.get("argument", "")
            
            # 각 주장에 대한 RAG 쿼리 생성 (1개만)
            system_prompt = """
You are an expert research assistant that generates specific search queries to find evidence supporting debate arguments.

For the given argument, generate 1 specific search query that would help find the most relevant supporting evidence, examples, case studies, or data.
Also determine the most appropriate source for the query from: web, user_context, dialogue_history, philosopher_works
"""

            user_prompt = f"""
DEBATE TOPIC: "{topic}"
ARGUMENT TO SUPPORT: "{argument}"

Generate 1 specific search query IN ENGLISH that would help find the best evidence to support this argument.
Also determine the most appropriate source to search from:
- web: For current facts, statistics, recent cases
- user_context: For documents, papers, provided materials
- dialogue_history: For previous statements in the debate
- philosopher_works: For philosophical concepts and theories

Format your response as JSON:
{{
  "query": "specific search query in English",
  "source": "most appropriate source",
  "reasoning": "why this source is appropriate"
}}
"""

            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=400
            )
            
            # JSON 파싱
            try:
                import json
                import re
                
                json_pattern = r'\{.*\}'
                json_match = re.search(json_pattern, response, re.DOTALL)
                
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    query = result.get("query", "")
                    source = result.get("source", "web")
                    reasoning = result.get("reasoning", "")
                    
                    self.argument_queries.append({
                        "argument_index": i,
                        "argument": argument,
                        "evidence": [{
                            "query": query,
                            "source": source,
                            "reasoning": reasoning,
                            "results": []  # RAG 검색 결과를 저장할 공간
                        }]
                    })
                    
                    logger.info(f"[{self.agent_id}] Generated 1 query for argument {i+1}: '{query}' from {source}")
                else:
                    logger.warning(f"[{self.agent_id}] Failed to parse query JSON for argument {i+1}")
                    # Fallback: 기본 쿼리 생성
                    self.argument_queries.append({
                        "argument_index": i,
                        "argument": argument,
                        "evidence": [{
                            "query": f"evidence for {argument[:50]}",
                            "source": "web",
                            "reasoning": "fallback query",
                            "results": []
                        }]
                    })
                    
            except Exception as e:
                logger.error(f"[{self.agent_id}] Error parsing query for argument {i+1}: {str(e)}")
                # Fallback: 기본 쿼리 생성
                self.argument_queries.append({
                    "argument_index": i,
                    "argument": argument,
                    "evidence": [{
                        "query": f"evidence for {argument[:50]}",
                        "source": "web",
                        "reasoning": "fallback query due to parsing error",
                        "results": []
                    }]
                })
    
    def _strengthen_arguments_with_rag(self) -> None:
        """
        모든 핵심 주장들을 RAG 검색 결과로 강화
        """
        logger.info(f"[{self.agent_id}] RAG search completed for all arguments")
        
        try:
            # 모든 쿼리에 대해 검색 수행
            for query_data in self.argument_queries:
                for evidence in query_data.get("evidence", []):
                    query = evidence.get("query", "")
                    source = evidence.get("source", "web")
                    
                    logger.info(f"[{self.agent_id}] Processing query: '{query}' from source: '{source}'")
                    
                    # 소스별 검색 수행
                    if source == "web":
                        results = self._web_search(query)
                    elif source == "user_context":
                        results = self._vector_search(query)
                    elif source == "dialogue_history":
                        results = self._dialogue_search(query)
                    elif source == "philosopher_works":
                        results = self._philosopher_search(query)
                    else:
                        results = self._web_search(query)  # 기본값
                    
                    evidence["results"] = results
                    logger.info(f"[{self.agent_id}] Found {len(results)} results for query from {source}")
                    
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in RAG search: {str(e)}")
        
        logger.info(f"[{self.agent_id}] RAG search completed for all arguments")
    
    def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """실제 웹 검색 수행"""
        try:
            # WebSearchRetriever 초기화 (필요시)
            if not hasattr(self, 'web_retriever') or self.web_retriever is None:
                from ...rag.retrieval.web_retriever import WebSearchRetriever
                self.web_retriever = WebSearchRetriever(
                    embedding_model="all-MiniLM-L6-v2",
                    search_provider="google",
                    max_results=3
                )
            
            # 실제 웹 검색 수행
            web_results = self.web_retriever.search(query, 3)
            
            if web_results:
                results = []
                for item in web_results:
                    results.append({
                        "title": item.get("title", ""),
                        "content": item.get("snippet", ""),
                        "url": item.get("url", ""),
                        "source": "web",
                        "relevance": 0.85
                    })
                return results
            else:
                # 실제 검색 실패 시 fallback
                return self._mock_web_search(query)
                
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Web search failed, using mock data: {str(e)}")
            return self._mock_web_search(query)
    
    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """실제 벡터 검색 수행 (사용자 컨텍스트)"""
        try:
            # 토론 대화 객체에서 벡터 저장소 가져오기
            if hasattr(self, 'vector_store') and self.vector_store is not None:
                vector_results = self.vector_store.search(query, 3)
                
                if vector_results:
                    results = []
                    for item in vector_results:
                        results.append({
                            "title": f"Document {item.get('id', '')}",
                            "content": item.get("text", ""),
                            "metadata": item.get("metadata", {}),
                            "source": "user_context",
                            "relevance": 1 - item.get("score", 0)  # 거리를 관련성으로 변환
                        })
                    return results
            
            # 벡터 저장소가 없거나 결과가 없는 경우 fallback
            return self._mock_vector_search(query)
            
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Vector search failed, using mock data: {str(e)}")
            return self._mock_vector_search(query)
    
    def _dialogue_search(self, query: str) -> List[Dict[str, Any]]:
        """실제 대화 기록 검색 수행"""
        try:
            results = []
            
            # 대화 기록이 있는 경우 검색
            if hasattr(self, 'dialogue_history') and self.dialogue_history:
                keywords = query.lower().split()
                
                for msg in self.dialogue_history:
                    text = msg.get("text", "").lower()
                    # 키워드 포함 여부 확인
                    if any(kw in text for kw in keywords):
                        results.append({
                            "speaker": msg.get("speaker", "Unknown"),
                            "content": msg.get("text", ""),
                            "timestamp": msg.get("timestamp", ""),
                            "source": "dialogue_history",
                            "relevance": 0.75
                        })
                
                # 관련성 순으로 정렬하고 상위 3개만 반환
                results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
                return results[:3]
            
            # 대화 기록이 없는 경우 fallback
            return self._mock_dialogue_search(query)
            
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Dialogue search failed, using mock data: {str(e)}")
            return self._mock_dialogue_search(query)
    
    def _philosopher_search(self, query: str) -> List[Dict[str, Any]]:
        """실제 철학자 작품 검색 수행"""
        try:
            # 철학자 작품 벡터 저장소 활용
            if hasattr(self, 'philosopher_vector_store') and self.philosopher_vector_store is not None:
                vector_results = self.philosopher_vector_store.search(query, 3)
                
                if vector_results:
                    results = []
                    for item in vector_results:
                        results.append({
                            "title": f"Philosophical work on: {query[:30]}...",
                            "content": item.get("text", ""),
                            "author": item.get("metadata", {}).get("author", "Relevant Philosopher"),
                            "work": item.get("metadata", {}).get("work", "Famous Work"),
                            "source": "philosopher_works",
                            "relevance": 1 - item.get("score", 0)
                        })
                    return results
            
            # 철학자 벡터 저장소가 없는 경우 일반 벡터 검색 시도
            elif hasattr(self, 'vector_store') and self.vector_store is not None:
                vector_results = self.vector_store.search(f"philosophy {query}", 2)
                
                if vector_results:
                    results = []
                    for item in vector_results:
                        results.append({
                            "title": f"Philosophical perspective: {query[:30]}...",
                            "content": item.get("text", ""),
                            "author": "Relevant Philosopher",
                            "work": "Academic Work",
                            "source": "philosopher_works",
                            "relevance": 1 - item.get("score", 0)
                        })
                    return results
            
            # 벡터 저장소가 없는 경우 fallback
            return self._mock_philosopher_search(query)
            
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Philosopher search failed, using mock data: {str(e)}")
            return self._mock_philosopher_search(query)
    
    def _generate_final_opening_argument(self, topic: str, stance_statement: str) -> None:
        """
        강화된 주장들을 결합하여 최종 입론 생성 (진정한 철학 70% + 데이터 30% 균형)
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
        """
        # 가장 강력한 증거 1개만 선별 (진정한 7:3 균형)
        best_evidence = None
        highest_relevance = 0
        
        for query_data in self.argument_queries:
            argument = query_data.get("argument", "")
            
            # 각 주장에 대해 가장 강력한 증거 1개만 찾기
            for evidence in query_data.get("evidence", []):
                for result in evidence.get("results", []):
                    relevance = result.get("relevance", 0)
                    content = result.get("content", "")
                    
                    # 매우 높은 관련성과 구체적 데이터가 있는 것만
                    metadata = self._extract_enhanced_metadata(content, result.get("title", ""))
                    if relevance > highest_relevance and relevance > 0.8 and metadata.get('has_specific_data'):
                        highest_relevance = relevance
                        best_evidence = {
                            "argument": argument,
                            "data": self._extract_key_data(content, metadata),
                            "source": result.get("title", "Research"),
                            "url": result.get("url", ""),
                            "relevance": relevance,
                            "raw_content": content[:150]  # 컨텍스트용
                        }
        
        # 철학자 중심 프롬프트 (데이터는 최소한으로)
        system_prompt = f"""
You are {self.philosopher_name}, delivering a powerful opening argument that showcases your unique philosophical perspective.

Your essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}
Key traits: {", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "logical reasoning"}

CRITICAL BALANCE (70% Philosophy + 30% Data):
1. Lead with YOUR philosophical perspective and deep reasoning (70%)
2. Use ONLY 1 piece of concrete evidence that truly strengthens your core argument (30%)
3. Make the evidence feel like natural validation of your philosophical insight
4. Focus on philosophical depth and your unique thinking style
5. Include preemptive counterarguments using your philosophical wisdom
6. Your famous quote: "{self.philosopher_quote}" - let this guide your entire argument

INTEGRATION STYLE:
- Philosophy dominates: Build your entire argument on philosophical reasoning
- Single evidence point: Use only when it powerfully validates your philosophical claim
- Return to philosophy: Always conclude with philosophical wisdom

Remember: You're a great philosopher who occasionally references supporting evidence, not a researcher with philosophical opinions.
"""

        # 증거를 매우 간결하게 정리 (1개만)
        evidence_summary = ""
        if best_evidence and highest_relevance > 0.8:
            evidence_summary = f"\nSingle Strategic Evidence (use sparingly - 30% weight):\n"
            evidence_summary += f"• Core Data: {best_evidence['data']}\n"
            evidence_summary += f"• Source: {best_evidence['source']}\n"
            evidence_summary += f"• Context: {best_evidence['raw_content']}\n\n"
        else:
            evidence_summary = "\nNo strong evidence found - rely purely on philosophical reasoning.\n"
        
        user_prompt = f"""
TOPIC: "{topic}"
YOUR POSITION: "{stance_statement}"

CORE PHILOSOPHICAL ARGUMENTS (70% weight):
{chr(10).join([f"- {arg.get('argument', '')}" for arg in self.core_arguments])}

{evidence_summary}

Create a compelling 4-5 paragraph opening argument with 70% philosophical reasoning + 30% strategic data:

1. **Opening Statement** (Pure Philosophy): Present your philosophical position with confidence
2. **Core Arguments** (Philosophy-Driven): Develop 2-3 main points using your philosophical lens
3. **Evidence Integration** (If Available): Naturally weave in the single piece of evidence ONLY if it truly strengthens your philosophical argument
4. **Preemptive Defense**: Address counterarguments using your philosophical wisdom
5. **Philosophical Conclusion**: End with your wisdom and philosophical insight

INTEGRATION RULES:
- Use evidence ONLY if it genuinely validates your philosophical reasoning
- If evidence is weak or irrelevant, ignore it completely and rely on pure philosophy
- Maximum 1 evidence reference in the entire argument
- Evidence should feel like: "My philosophical view is [reasoning], and this is confirmed by [single data point], which demonstrates [philosophical conclusion]"

REQUIREMENTS:
- Write as {self.philosopher_name} would think and speak
- Prioritize philosophical depth over any citations
- Use evidence only if it truly adds value to your philosophical argument
- Make your philosophical reasoning the star of the argument
- Respond in the same language as the topic
- Aim for 350-450 words of substantive philosophical argument

Balance: 70% your unique philosophical perspective + 30% strategic evidence (if truly valuable).
"""

        self.prepared_argument = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=1300  # 약간 감소 (더 집중된 논증을 위해)
        )
        
        evidence_used = 1 if best_evidence and highest_relevance > 0.8 else 0
        logger.info(f"[{self.agent_id}] Philosophy-focused opening argument generated ({len(self.prepared_argument)} characters)")
        logger.info(f"[{self.agent_id}] Used {evidence_used} strategic evidence point (70% philosophy + 30% data)")
    
    def _extract_key_data(self, content: str, metadata: Dict[str, Any]) -> str:
        """
        콘텐츠에서 가장 핵심적인 데이터만 추출 (1개 증거용)
        
        Args:
            content: 원본 콘텐츠
            metadata: 메타데이터
            
        Returns:
            핵심 데이터 요약 (매우 간결함)
        """
        key_data = []
        
        # 통계 데이터 우선 (1개만)
        if metadata.get('statistics'):
            key_data.append(metadata['statistics'][0])  # 가장 첫 번째만
        
        # 연구 결과 (통계가 없을 때만)
        elif metadata.get('study_details'):
            key_data.append(metadata['study_details'][0])  # 가장 첫 번째만
        
        # 전문가 인용 (위의 것들이 없을 때만)
        elif metadata.get('expert_quotes'):
            for quote in metadata['expert_quotes'][:1]:  # 1개만
                if len(quote) < 100:  # 짧은 인용만
                    key_data.append(quote)
                    break
        
        # 데이터가 없으면 콘텐츠에서 핵심 문장 1개만 추출
        if not key_data:
            import re
            # 숫자가 포함된 문장 1개만 찾기
            sentences = re.split(r'[.!?]', content)
            for sentence in sentences:
                if re.search(r'\d+(?:\.\d+)?%|\d+(?:,\d+)*\s+(?:people|participants|cases|studies)', sentence):
                    clean_sentence = sentence.strip()
                    if len(clean_sentence) > 20 and len(clean_sentence) < 150:
                        key_data.append(clean_sentence)
                        break  # 1개만 찾으면 중단
        
        return key_data[0] if key_data else "relevant research findings"
    
    def _extract_enhanced_metadata(self, content: str, title: str) -> Dict[str, Any]:
        """
        콘텐츠에서 구체적 데이터와 메타데이터 추출
        
        Args:
            content: 텍스트 콘텐츠
            title: 소스 제목
            
        Returns:
            향상된 메타데이터
        """
        import re
        
        metadata = {
            'has_specific_data': False,
            'statistics': [],
            'study_details': [],
            'expert_quotes': [],
            'years': [],
            'authors': []
        }
        
        # 통계 및 수치 데이터 추출
        # 퍼센트, 숫자, 측정값 등
        percentage_pattern = r'\b\d+(?:\.\d+)?%'
        number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:people|participants|subjects|patients|cases|studies|years|months|days|times|fold|million|billion|thousand)\b'
        measurement_pattern = r'\b\d+(?:\.\d+)?\s*(?:mg|kg|ml|cm|mm|meters?|feet|inches|hours?|minutes?|seconds?)\b'
        
        percentages = re.findall(percentage_pattern, content, re.IGNORECASE)
        numbers = re.findall(number_pattern, content, re.IGNORECASE)
        measurements = re.findall(measurement_pattern, content, re.IGNORECASE)
        
        if percentages:
            metadata['statistics'].extend([f"{p} change/improvement" for p in percentages[:3]])
            metadata['has_specific_data'] = True
            
        if numbers:
            metadata['statistics'].extend([f"{n}" for n in numbers[:3]])
            metadata['has_specific_data'] = True
            
        if measurements:
            metadata['statistics'].extend([f"{m}" for m in measurements[:2]])
            metadata['has_specific_data'] = True
        
        # 연구 세부사항 추출
        study_patterns = [
            r'(?:study|research|trial|experiment|analysis)\s+(?:of|with|involving)\s+(\d+(?:,\d+)*\s+(?:people|participants|subjects|patients))',
            r'(\d+(?:,\d+)*\s+(?:people|participants|subjects|patients))\s+(?:were|participated|enrolled)',
            r'(?:over|during|for)\s+(\d+\s+(?:years?|months?|weeks?|days?))',
            r'(?:randomized|controlled|double-blind|clinical)\s+(trial|study|experiment)',
            r'(?:published|reported|found)\s+in\s+(\d{4})',
            r'(?:university|institute|college)\s+(?:of\s+)?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in study_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['study_details'].extend([match if isinstance(match, str) else ' '.join(match) for match in matches[:2]])
                metadata['has_specific_data'] = True
        
        # 전문가 인용 및 발언 추출
        quote_patterns = [
            r'"([^"]{20,100})"',  # 따옴표 안의 인용문
            r'(?:according to|says|states|reports|found that|concluded that)\s+([^.]{20,80})',
            r'(?:Dr\.|Professor|researcher)\s+(\w+(?:\s+\w+)*)\s+(?:says|states|found|reported)',
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['expert_quotes'].extend([match.strip() for match in matches[:2]])
                metadata['has_specific_data'] = True
        
        # 연도 추출
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, content)
        if years:
            metadata['years'] = [f"{y[0]}{y[1:]}" for y in years[:3]]
        
        # 저자명 추출 (간단한 패턴)
        author_pattern = r'(?:Dr\.|Professor|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        authors = re.findall(author_pattern, content)
        if authors:
            metadata['authors'] = authors[:2]
        
        return metadata
    
    def _hybrid_chunking(self, text: str, chunk_size: int = 800, overlap_ratio: float = 0.2) -> List[str]:
        """
        문장 단위 + 슬라이딩 윈도우 하이브리드 청크화
        정보 손실을 최소화하면서 의미 있는 단위로 텍스트 분할
        
        Args:
            text: 청크화할 텍스트
            chunk_size: 목표 청크 크기 (문자 수)
            overlap_ratio: 오버랩 비율
            
        Returns:
            청크 리스트
        """
        import re
        
        # 문장 단위로 분리 (개선된 패턴)
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, text.strip())
        
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = ""
        overlap_size = int(chunk_size * overlap_ratio)
        
        for sentence in sentences:
            # 현재 청크에 문장을 추가했을 때의 길이 확인
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # 현재 청크가 비어있지 않으면 저장
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # 오버랩을 위해 현재 청크의 마지막 부분 유지
                    if len(current_chunk) > overlap_size:
                        # 마지막 overlap_size 문자에서 문장 경계 찾기
                        overlap_text = current_chunk[-overlap_size:]
                        # 문장 시작점 찾기
                        sentence_start = overlap_text.find('. ')
                        if sentence_start != -1:
                            current_chunk = overlap_text[sentence_start + 2:]
                        else:
                            current_chunk = overlap_text
                    else:
                        current_chunk = ""
                
                # 새로운 문장으로 시작
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_stage_instructions(self, current_stage: str, topic: str, my_stance: str, opposite_stance: str) -> str:
        """
        현재 단계에 맞는 지시사항 반환
        
        Args:
            current_stage: 현재 토론 단계
            topic: 토론 주제
            my_stance: 내 입장
            opposite_stance: 상대방 입장
            
        Returns:
            단계별 지시사항
        """
        role_display = "PRO" if self.role == "pro" else "CON" if self.role == "con" else "NEUTRAL"
        
        stage_instructions = {
            "pro_argument": f"Present your main arguments. Clearly articulate 2-3 strong points supporting your position, back up each point with evidence or reasoning, and be persuasive and confident in your delivery.",
            
            "con_argument": f"Present your main arguments against the topic. Clearly articulate 2-3 strong points supporting your position, back up each point with evidence or reasoning, and be persuasive and confident in your delivery.",
            
            "pro_rebuttal": f"Rebut the arguments made by the opposition. Address the strongest points made by the CON side, point out logical flaws or factual errors in their arguments, and reinforce your own position.",
            
            "con_rebuttal": f"Rebut the arguments made by the opposition. Address the strongest points made by the PRO side, point out logical flaws or factual errors in their arguments, and reinforce your own position.",
            
            "con_to_pro_qa": f"{'Ask a pointed question to the PRO side that challenges their position' if self.role == 'con' else 'Answer the question from the CON side while defending your position'}.",
            
            "pro_to_con_qa": f"{'Ask a pointed question to the CON side that challenges their position' if self.role == 'pro' else 'Answer the question from the PRO side while defending your position'}.",
            
            "pro_conclusion": f"Deliver your closing statement. Summarize your strongest arguments, address key points raised during the debate, and reinforce why your position is correct.",
            
            "con_conclusion": f"Deliver your closing statement. Summarize your strongest arguments, address key points raised during the debate, and reinforce why your position is correct."
        }
        
        # 기본 지시사항
        default_instruction = f"Respond to the current discussion while advocating for your position: '{my_stance}'."
        
        return stage_instructions.get(current_stage, default_instruction)
    
    def _prepare_opening_statement(self, topic: str, context: Dict[str, Any], stance_statements: Dict[str, str]) -> str:
        """
        오프닝 발언 준비
        
        Args:
            topic: 토론 주제
            context: 컨텍스트 정보
            stance_statements: 찬반 입장 진술문
            
        Returns:
            오프닝 발언
        """
        # 내 입장 확인
        my_stance = stance_statements.get(self.role) if self.role in ["pro", "con"] else ""
        
        # 오프닝 템플릿
        if self.role == "pro":
            return f"""안녕하세요, 저는 '{topic}'에 찬성하는 입장에서 발언하겠습니다.

{my_stance}라고 생각합니다.

제가 이 입장을 지지하는 세 가지 주요 이유는 다음과 같습니다:

첫째, [찬성 이유 1] - 이것은 [설명]...

둘째, [찬성 이유 2] - 자세히 살펴보면 [설명]...

셋째, [찬성 이유 3] - 또한 [설명]...

이러한 이유로 저는 '{topic}'에 찬성합니다. 감사합니다."""
        else:
            return f"""안녕하세요, 저는 '{topic}'에 반대하는 입장에서 발언하겠습니다.

{my_stance}라고 생각합니다.

제가 이 입장을 지지하는 세 가지 주요 이유는 다음과 같습니다:

첫째, [반대 이유 1] - 이것은 [설명]...

둘째, [반대 이유 2] - 자세히 살펴보면 [설명]...

셋째, [반대 이유 3] - 또한 [설명]...

이러한 이유로 저는 '{topic}'에 반대합니다. 감사합니다."""
    
    def _prepare_closing_statement(self, dialogue_state: Dict[str, Any], stance_statements: Dict[str, str]) -> str:
        """
        최종 결론 발언 준비
        
        Args:
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            
        Returns:
            최종 결론 발언
        """
        # 내 입장 확인
        my_stance = stance_statements.get(self.role) if self.role in ["pro", "con"] else ""
        
        # 최종 결론 템플릿 (역할별)
        if self.role == "pro":
            template = f"""지금까지의 토론을 통해 저희의 입장을 다시 한번 강조하고자 합니다.

{my_stance}

오늘 토론에서 우리는 다음과 같은 중요한 점들을 확인했습니다:

첫째, [첫 번째 핵심 포인트 요약]
둘째, [두 번째 핵심 포인트 요약]  
셋째, [세 번째 핵심 포인트 요약]

따라서 저희는 계속해서 이 입장을 지지하며, 이것이 올바른 방향이라고 확신합니다.

감사합니다."""
        else:
            template = f"""지금까지의 토론을 통해 저희의 입장을 다시 한번 강조하고자 합니다.

{my_stance}

오늘 토론에서 우리는 다음과 같은 중요한 점들을 확인했습니다:

첫째, [첫 번째 핵심 포인트 요약]
둘째, [두 번째 핵심 포인트 요약]
셋째, [세 번째 핵심 포인트 요약]

따라서 저희는 계속해서 이 입장을 지지하며, 이것이 올바른 방향이라고 확신합니다.

감사합니다."""
        
        return template
    
    def _update_interaction_history(self, prompt: str, response: str) -> None:
        """
        상호작용 기록 업데이트
        
        Args:
            prompt: 입력된 프롬프트
            response: 생성된 응답
        """
        # interaction_history가 없으면 초기화
        if "interaction_history" not in self.state:
            self.state["interaction_history"] = []
            
        self.state["interaction_history"].append({
            "timestamp": time.time(),
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "response": response[:100] + "..." if len(response) > 100 else response
        })
        
        # 기록이 너무 많아지면 오래된 것부터 제거
        if len(self.state["interaction_history"]) > 10:
            self.state["interaction_history"] = self.state["interaction_history"][-10:]
    
    # ===== Fallback Mock Methods =====
    
    def _mock_web_search(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 모의 결과 (Fallback)"""
        return [
            {
                "title": f"Web Result for: {query[:30]}...",
                "content": f"Recent research and data about {query}. This includes current statistics, case studies, and expert opinions on the topic.",
                "url": f"https://example.com/search?q={query.replace(' ', '+')}", 
                "source": "web",
                "relevance": 0.85
            }
        ]
    
    def _mock_vector_search(self, query: str) -> List[Dict[str, Any]]:
        """사용자 컨텍스트 벡터 검색 모의 결과 (Fallback)"""
        return [
            {
                "title": f"Document: {query[:30]}...",
                "content": f"From provided documents: Analysis and evidence related to {query}. This information comes from academic papers and reports provided for the debate.",
                "metadata": {"source": "user_document", "page": 1},
                "source": "user_context",
                "relevance": 0.90
            }
        ]
    
    def _mock_dialogue_search(self, query: str) -> List[Dict[str, Any]]:
        """대화 기록 검색 모의 결과 (Fallback)"""
        return [
            {
                "speaker": "Previous Speaker",
                "content": f"Earlier in the debate, it was mentioned that {query} is an important consideration for our discussion.",
                "timestamp": "2024-01-01T10:00:00",
                "source": "dialogue_history",
                "relevance": 0.75
            }
        ]
    
    def _mock_philosopher_search(self, query: str) -> List[Dict[str, Any]]:
        """철학자 작품 검색 모의 결과 (Fallback)"""
        return [
            {
                "title": f"Philosophical work on: {query[:30]}...",
                "content": f"Philosophical perspective on {query}. Classical and modern philosophical texts provide insights into this concept and its implications.",
                "author": "Relevant Philosopher",
                "work": "Famous Work",
                "source": "philosopher_works",
                "relevance": 0.80
            }
        ]
    
    def extract_opponent_key_points(self, opponent_messages: List[Dict[str, Any]]) -> None:
        """
        상대방 발언에서 핵심 논점 추출하여 저장
        다중 상대방 지원: 각 상대방별로 논점을 구분하여 저장
        
        Args:
            opponent_messages: 상대방 발언 메시지들 (여러 상대방 포함 가능)
        """
        if not opponent_messages:
            logger.warning(f"[{self.agent_id}] No opponent messages to extract key points from")
            return
        
        try:
            # 상대방별로 메시지 그룹화
            opponents_by_speaker = {}
            for msg in opponent_messages:
                speaker_id = msg.get("speaker_id", "unknown")
                text = msg.get("text", "").strip()
                if text:
                    if speaker_id not in opponents_by_speaker:
                        opponents_by_speaker[speaker_id] = []
                    opponents_by_speaker[speaker_id].append(text)
            
            if not opponents_by_speaker:
                logger.warning(f"[{self.agent_id}] No meaningful opponent text found")
                return
            
            # 모든 상대방의 논점을 통합하여 추출
            all_opponent_text = ""
            speaker_summaries = []
            
            for speaker_id, texts in opponents_by_speaker.items():
                speaker_text = "\n".join(texts)
                all_opponent_text += f"\n\n[{speaker_id}]:\n{speaker_text}"
                speaker_summaries.append(f"- {speaker_id}: {len(texts)} statements")
            
            logger.info(f"[{self.agent_id}] Processing arguments from {len(opponents_by_speaker)} opponents: {', '.join(opponents_by_speaker.keys())}")
            
            # LLM을 사용하여 통합 핵심 논점 추출
            system_prompt = """
You are an expert debate analyst. Extract the key arguments and main points from multiple opponents' statements.
Focus on identifying:
1. Core claims and assertions from all opponents
2. Main supporting evidence or reasoning
3. Key logical structures
4. Common themes across different speakers
5. Unique arguments from individual speakers

Provide a comprehensive list that captures the essence of the opposition's position.
"""
            
            user_prompt = f"""
Analyze the following debate statements from multiple opponents and extract their key arguments:

OPPONENTS' STATEMENTS:
{all_opponent_text}

SPEAKER SUMMARY:
{chr(10).join(speaker_summaries)}

Extract 4-7 key points that represent the opponents' main arguments across all speakers. 
Include both common themes and unique individual arguments.

Format your response as a JSON list of strings:
["Key point 1", "Key point 2", "Key point 3", ...]

Each key point should be:
- A concise summary (1-2 sentences) of a major argument or claim
- Representative of the overall opposition position
- Include attribution if it's a unique argument from a specific speaker
"""
            
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1000
            )
            
            # JSON 파싱
            import json
            import re
            
            # JSON 배열 패턴 찾기
            json_pattern = r'\[.*?\]'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                key_points = json.loads(json_str)
                
                if isinstance(key_points, list):
                    self.opponent_key_points = key_points
                    logger.info(f"[{self.agent_id}] Extracted {len(key_points)} opponent key points from {len(opponents_by_speaker)} speakers")
                    
                    # 디버깅용 로그
                    for i, point in enumerate(key_points, 1):
                        logger.info(f"[{self.agent_id}] Opponent point {i}: {point[:100]}...")
                        
                    # 상대방별 상세 정보도 저장 (선택적)
                    if not hasattr(self, 'opponent_details'):
                        self.opponent_details = {}
                    self.opponent_details['speakers'] = list(opponents_by_speaker.keys())
                    self.opponent_details['message_counts'] = {k: len(v) for k, v in opponents_by_speaker.items()}
                    
                else:
                    logger.warning(f"[{self.agent_id}] Invalid key points format: {type(key_points)}")
            else:
                logger.warning(f"[{self.agent_id}] Failed to parse key points from response: {response[:100]}...")
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error extracting opponent key points: {str(e)}")
    
    def update_my_key_points_from_core_arguments(self) -> None:
        """
        자신의 core_arguments에서 my_key_points 업데이트
        """
        try:
            if self.core_arguments:
                # core_arguments가 딕셔너리 형태인 경우
                if isinstance(self.core_arguments[0], dict):
                    self.my_key_points = [
                        arg.get("argument", "") for arg in self.core_arguments
                        if arg.get("argument", "").strip()
                    ]
                # core_arguments가 문자열 리스트인 경우
                else:
                    self.my_key_points = [
                        str(arg) for arg in self.core_arguments
                        if str(arg).strip()
                    ]
                
                logger.info(f"[{self.agent_id}] Updated my_key_points from {len(self.core_arguments)} core arguments")
            else:
                logger.warning(f"[{self.agent_id}] No core_arguments available to update my_key_points")
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error updating my_key_points: {str(e)}")
    
    # ========================================================================
    # ARGUMENT PREPARATION STATE MANAGEMENT (Option 2 구현)
    # ========================================================================
    
    def is_argument_ready(self) -> bool:
        """입론이 준비되었는지 확인"""
        return self.argument_prepared and self.argument_cache_valid and self.prepared_argument
    
    def is_currently_preparing(self) -> bool:
        """현재 입론 준비 중인지 확인"""
        return self.is_preparing_argument
    
    async def prepare_argument_async(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        비동기로 입론 준비 (백그라운드 실행용)
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 추가 컨텍스트
            
        Returns:
            준비 결과
        """
        if self.is_preparing_argument:
            return {"status": "already_preparing", "message": "이미 입론 준비 중입니다"}
        
        if self.is_argument_ready() and self._is_same_context(context):
            return {"status": "already_ready", "message": "입론이 이미 준비되어 있습니다"}
        
        try:
            self.is_preparing_argument = True
            self.last_preparation_context = context
            
            # 비동기로 입론 준비 실행
            import asyncio
            loop = asyncio.get_event_loop()
            
            def prepare_sync():
                self.prepare_argument_with_rag(topic, stance_statement, context)
                return {
                    "status": "success" if self.argument_prepared else "failed",
                    "prepared": self.argument_prepared,
                    "argument_length": len(self.prepared_argument) if self.prepared_argument else 0
                }
            
            result = await loop.run_in_executor(None, prepare_sync)
            
            if result["status"] == "success":
                self.argument_cache_valid = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error in async argument preparation: {str(e)}")
            return {"status": "error", "error": str(e)}
        finally:
            self.is_preparing_argument = False
    
    def get_prepared_argument_or_generate(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> str:
        """
        준비된 입론을 반환하거나, 없으면 즉시 생성
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 추가 컨텍스트
            
        Returns:
            입론 텍스트
        """
        # 준비된 입론이 있고 유효하면 반환
        if self.is_argument_ready() and self._is_same_context(context):
            logger.info(f"[{self.agent_id}] Using cached prepared argument")
            return self.prepared_argument
        
        # 없으면 즉시 생성
        logger.info(f"[{self.agent_id}] No cached argument available, generating immediately")
        self.prepare_argument_with_rag(topic, stance_statement, context)
        self.argument_cache_valid = True
        self.last_preparation_context = context
        
        return self.prepared_argument if self.prepared_argument else "입론 생성에 실패했습니다."
    
    def invalidate_argument_cache(self):
        """입론 캐시 무효화"""
        self.argument_cache_valid = False
        self.last_preparation_context = None
        logger.info(f"[{self.agent_id}] Argument cache invalidated")
    
    def _is_same_context(self, context: Dict[str, Any]) -> bool:
        """
        현재 컨텍스트가 이전 준비 시와 동일한지 확인
        
        Args:
            context: 비교할 컨텍스트
            
        Returns:
            동일 여부
        """
        if self.last_preparation_context is None:
            return False
        
        # 주요 필드들만 비교
        key_fields = ["topic", "stance_statement", "current_stage"]
        for field in key_fields:
            if context.get(field) != self.last_preparation_context.get(field):
                return False
        
        return True
    
    def analyze_and_score_arguments(self, opponent_response: str, speaker_id: str) -> Dict[str, Any]:
        """
        상대방 발언에서 논지를 추출하고 스코어링
        
        Args:
            opponent_response: 상대방 발언 텍스트
            speaker_id: 발언자 ID
            
        Returns:
            분석 결과 (논지 목록, 스코어, 취약점 등)
        """
        try:
            # 1. 논지 추출
            arguments = self._extract_arguments_from_response(opponent_response, speaker_id)
            
            # 2. 각 논지별 스코어링
            scored_arguments = []
            for arg in arguments:
                score_data = self._score_single_argument(arg, opponent_response)
                scored_arguments.append({
                    "argument": arg,
                    "scores": score_data,
                    "vulnerability_rank": score_data.get("vulnerability", 0.0)
                })
            
            # 3. 취약점 순으로 정렬
            scored_arguments.sort(key=lambda x: x["vulnerability_rank"], reverse=True)
            
            # 4. 상대방 논지 저장
            if speaker_id not in self.opponent_arguments:
                self.opponent_arguments[speaker_id] = []
            self.opponent_arguments[speaker_id].extend(scored_arguments)
            
            return {
                "speaker_id": speaker_id,
                "arguments_count": len(arguments),
                "scored_arguments": scored_arguments[:3],  # 상위 3개만 반환
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing opponent arguments: {str(e)}")
            return {"error": str(e)}
    
    def _extract_arguments_from_response(self, response: str, speaker_id: str) -> List[Dict[str, Any]]:
        """
        발언에서 핵심 논지들을 추출
        
        Args:
            response: 발언 텍스트
            speaker_id: 발언자 ID
            
        Returns:
            추출된 논지 목록
        """
        system_prompt = """
You are an expert debate analyst. Your task is to extract key arguments from a speaker's statement.
Identify the main claims, supporting evidence, and logical structure.
Return ONLY valid JSON format.
"""

        user_prompt = f"""
Analyze this debate statement and extract the key arguments:

STATEMENT: "{response}"

Extract the main arguments and return ONLY a valid JSON array:
[
  {{
    "claim": "main claim text",
    "evidence": "supporting evidence",
    "reasoning": "logical reasoning",
    "assumptions": ["assumption1", "assumption2"],
    "argument_type": "logical"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text.
"""
        
        try:
            response_text = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=800
            )
            
            # JSON 파싱 개선
            import json
            import re
            
            # 응답에서 JSON 부분만 추출 (더 견고한 정규식)
            # 중괄호나 대괄호로 시작하는 JSON 찾기
            json_patterns = [
                r'\[[\s\S]*?\]',  # 배열 형태
                r'\{[\s\S]*?\}',  # 객체 형태
            ]
            
            parsed_data = None
            for pattern in json_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        # JSON 문자열 정리
                        clean_json = match.strip()
                        # 잘못된 문자 제거
                        clean_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_json)
                        
                        parsed_data = json.loads(clean_json)
                        
                        # 배열이 아니면 배열로 감싸기
                        if not isinstance(parsed_data, list):
                            parsed_data = [parsed_data]
                        
                        # 유효한 JSON을 찾았으면 중단
                        break
                    except json.JSONDecodeError:
                        continue
                
                if parsed_data:
                    break
            
            if parsed_data:
                # 데이터 검증 및 정리
                validated_arguments = []
                for arg in parsed_data:
                    if isinstance(arg, dict):
                        validated_arg = {
                            "claim": str(arg.get('claim', 'Unknown claim')),
                            "evidence": str(arg.get('evidence', 'No evidence provided')),
                            "reasoning": str(arg.get('reasoning', 'No reasoning provided')),
                            "assumptions": arg.get('assumptions', []) if isinstance(arg.get('assumptions'), list) else [],
                            "argument_type": str(arg.get('argument_type', 'logical'))
                        }
                        validated_arguments.append(validated_arg)
                
                return validated_arguments if validated_arguments else self._get_fallback_argument(response)
            else:
                return self._get_fallback_argument(response)
                
        except Exception as e:
            logger.error(f"Error extracting arguments: {str(e)}")
            return self._get_fallback_argument(response)
    
    def _get_fallback_argument(self, response: str) -> List[Dict[str, Any]]:
        """JSON 파싱 실패 시 기본 논지 구조 반환"""
        return [{
            "claim": response[:200] + "..." if len(response) > 200 else response,
            "evidence": "Not extracted due to parsing error",
            "reasoning": "Not analyzed due to parsing error",
            "assumptions": [],
            "argument_type": "unknown"
        }]
    
    def _score_single_argument(self, argument: Dict[str, Any], full_context: str) -> Dict[str, float]:
        """
        단일 논지에 대한 다차원 스코어링
        
        Args:
            argument: 분석할 논지
            full_context: 전체 발언 맥락
            
        Returns:
            스코어 데이터 (논리적 강도, 근거 품질, 취약성, 관련성)
        """
        system_prompt = """
You are a debate argument evaluator. Score arguments on multiple dimensions.
Be objective and analytical in your assessment.
"""

        user_prompt = f"""
Evaluate this argument on the following criteria (scale 0.0-1.0):

ARGUMENT:
- Claim: {argument.get('claim', '')}
- Evidence: {argument.get('evidence', '')}
- Reasoning: {argument.get('reasoning', '')}
- Assumptions: {argument.get('assumptions', [])}

FULL CONTEXT: "{full_context}"

Score on these dimensions:
1. LOGICAL_STRENGTH (0.0-1.0): How logically sound is the argument?
2. EVIDENCE_QUALITY (0.0-1.0): How strong is the supporting evidence?
3. VULNERABILITY (0.0-1.0): How vulnerable is this to counterattack? (higher = more vulnerable)
4. RELEVANCE (0.0-1.0): How relevant to the main debate topic?

Return JSON format:
{{
  "logical_strength": 0.0-1.0,
  "evidence_quality": 0.0-1.0,
  "vulnerability": 0.0-1.0,
  "relevance": 0.0-1.0,
  "overall_score": 0.0-1.0
}}
"""
        
        try:
            response_text = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=300
            )
            
            # JSON 파싱
            import json
            import re
            json_pattern = r'\{.*?\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                scores = json.loads(json_match.group(0))
                # overall_score 계산 (가중평균)
                if "overall_score" not in scores:
                    scores["overall_score"] = (
                        scores.get("logical_strength", 0.5) * 0.3 +
                        scores.get("evidence_quality", 0.5) * 0.25 +
                        (1.0 - scores.get("vulnerability", 0.5)) * 0.25 +  # 취약성은 역산
                        scores.get("relevance", 0.5) * 0.2
                    )
                return scores
            else:
                # 기본 스코어
                return {
                    "logical_strength": 0.5,
                    "evidence_quality": 0.5,
                    "vulnerability": 0.5,
                    "relevance": 0.5,
                    "overall_score": 0.5
                }
                
        except Exception as e:
            logger.error(f"Error scoring argument: {str(e)}")
            return {
                "logical_strength": 0.5,
                "evidence_quality": 0.5,
                "vulnerability": 0.5,
                "relevance": 0.5,
                "overall_score": 0.5
            }
    
    def prepare_attack_strategies_for_speaker(self, target_speaker_id: str) -> List[Dict[str, Any]]:
        """
        특정 상대방에 대한 공격 전략들을 준비
        
        Args:
            target_speaker_id: 공격 대상 발언자 ID
            
        Returns:
            준비된 공격 전략 목록
        """
        if target_speaker_id not in self.opponent_arguments:
            return []
        
        try:
            # 상대방의 취약한 논지들 가져오기 (상위 3개)
            target_arguments = self.opponent_arguments[target_speaker_id]
            vulnerable_args = sorted(target_arguments, 
                                   key=lambda x: x["vulnerability_rank"], 
                                   reverse=True)[:3]
            
            strategies = []
            for arg_data in vulnerable_args:
                argument = arg_data["argument"]
                
                # 이 철학자에게 적합한 공격 전략 선택
                best_strategy = self._select_best_strategy_for_argument(argument)
                
                # 구체적인 공격 계획 생성
                attack_plan = self._generate_attack_plan(argument, best_strategy)
                
                strategies.append({
                    "target_argument": argument,
                    "strategy_type": best_strategy,
                    "attack_plan": attack_plan,
                    "vulnerability_score": arg_data["vulnerability_rank"],
                    "priority": len(strategies) + 1
                })
            
            # 공격 전략 저장
            self.attack_strategies[target_speaker_id] = strategies
            
            return strategies
            
        except Exception as e:
            logger.error(f"Error preparing attack strategies: {str(e)}")
            return []
    
    def _select_best_strategy_for_argument(self, argument: Dict[str, Any]) -> str:
        """
        논지에 대해 이 철학자에게 가장 적합한 공격 전략 선택
        
        Args:
            argument: 공격할 논지
            
        Returns:
            선택된 전략 이름
        """
        # 전략 가중치가 있으면 사용, 없으면 기본값
        if not self.strategy_weights:
            return "Clipping"  # 기본 전략
        
        # 논지 유형에 따른 전략 적합성 분석
        argument_type = argument.get("argument_type", "logical")
        claim = argument.get("claim", "")
        
        # 각 전략의 적합성 점수 계산
        strategy_scores = {}
        
        for strategy, weight in self.strategy_weights.items():
            base_score = weight
            
            # 논지 유형별 보정
            if strategy == "Clipping" and "specific" in claim.lower():
                base_score *= 1.2
            elif strategy == "Framing Shift" and "assume" in claim.lower():
                base_score *= 1.3
            elif strategy == "Reductive Paradox" and argument_type == "logical":
                base_score *= 1.1
            elif strategy == "Conceptual Undermining" and any(word in claim.lower() for word in ["define", "mean", "is"]):
                base_score *= 1.4
            elif strategy == "Ethical Reversal" and argument_type == "emotional":
                base_score *= 1.2
            
            strategy_scores[strategy] = base_score
        
        # 가장 높은 점수의 전략 선택
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        return best_strategy
    
    def _generate_attack_plan(self, target_argument: Dict[str, Any], strategy_type: str) -> Dict[str, Any]:
        """
        특정 전략을 사용한 구체적인 공격 계획 생성
        
        Args:
            target_argument: 공격할 논지
            strategy_type: 사용할 전략 유형
            
        Returns:
            구체적인 공격 계획
        """
        try:
            # 이미 로드된 전략 정보 사용
            strategy_info = self.strategy_styles.get(strategy_type, {})
            
            system_prompt = f"""
You are {self.philosopher_name}, a philosopher with this essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}

You need to prepare an attack against an opponent's argument using the "{strategy_type}" strategy.
"""

            user_prompt = f"""
STRATEGY: {strategy_type}
DESCRIPTION: {strategy_info.get('description', '')}
STYLE PROMPT: {strategy_info.get('style_prompt', '')}
EXAMPLE: {strategy_info.get('example', '')}

TARGET ARGUMENT TO ATTACK:
- Claim: {target_argument.get('claim', '')}
- Evidence: {target_argument.get('evidence', '')}
- Reasoning: {target_argument.get('reasoning', '')}
- Assumptions: {target_argument.get('assumptions', [])}

Create a specific attack plan using this strategy. Include:
1. The exact point you will target
2. How you will apply the {strategy_type} strategy
3. The key phrase or question you will use
4. Expected counterargument and your response

Return JSON format:
{{
  "target_point": "specific point to attack",
  "strategy_application": "how to apply {strategy_type}",
  "key_phrase": "main attack phrase/question",
  "expected_counter": "likely opponent response",
  "follow_up": "your follow-up response"
}}
"""
            
            response_text = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=600
            )
            
            # JSON 파싱
            import re
            json_pattern = r'\{.*?\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                attack_plan = json.loads(json_match.group(0))
                return attack_plan
            else:
                # 기본 공격 계획
                return {
                    "target_point": target_argument.get('claim', ''),
                    "strategy_application": f"Apply {strategy_type}",
                    "key_phrase": strategy_info.get('style_prompt', ''),
                    "expected_counter": "Opponent may defend",
                    "follow_up": "Continue with philosophical reasoning"
                }
                
        except Exception as e:
            logger.error(f"Error generating attack plan: {str(e)}")
            return {
                "target_point": target_argument.get('claim', ''),
                "strategy_application": f"Use {strategy_type}",
                "key_phrase": "Challenge this point",
                "expected_counter": "Unknown",
                "follow_up": "Continue debate"
            }
    
    def get_best_attack_strategy(self, target_speaker_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        현재 상황에서 최적의 공격 전략 선택
        
        Args:
            target_speaker_id: 공격 대상 ID
            context: 현재 토론 맥락
            
        Returns:
            선택된 최적 공격 전략
        """
        if target_speaker_id not in self.attack_strategies:
            return None
        
        strategies = self.attack_strategies[target_speaker_id]
        if not strategies:
            return None
        
        # 현재 토론 단계와 맥락을 고려하여 최적 전략 선택
        current_stage = context.get("current_stage", "")
        recent_messages = context.get("recent_messages", [])
        
        # 우선순위가 가장 높은 전략 선택 (취약성 기준)
        best_strategy = max(strategies, key=lambda x: x["vulnerability_score"])
        
        return best_strategy
    
    def clear_opponent_data(self, speaker_id: str = None):
        """
        상대방 데이터 초기화 (새 토론 시작 시)
        
        Args:
            speaker_id: 특정 발언자만 초기화할 경우
        """
        if speaker_id:
            self.opponent_arguments.pop(speaker_id, None)
            self.attack_strategies.pop(speaker_id, None)
        else:
            self.opponent_arguments.clear()
            self.attack_strategies.clear()
            self.argument_scores.clear() 