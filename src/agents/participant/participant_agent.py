"""
대화 참여자(Participant) 에이전트 모듈

대화에 참여하여 의견을 제시하고 대화에 기여하는 에이전트 구현
"""

from typing import Dict, Any, List, Optional
from src.agents.base.agent import Agent
from src.models.llm.llm_manager import LLMManager


class ParticipantAgent(Agent):
    """
    대화 참여자 에이전트
    
    대화에 참여하여 의견을 제시하고 다른 참여자와 상호작용함
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        참여자 에이전트 초기화
        
        Args:
            agent_id: 고유 식별자
            name: 에이전트 이름
            config: 설정 매개변수
        """
        super().__init__(agent_id, name, config)
        
        # 참여자 성격 설정
        self.viewpoint = config.get("viewpoint", "neutral")  # pro, con, neutral
        self.assertiveness = config.get("parameters", {}).get("assertiveness", 0.5)
        self.emotion_level = config.get("parameters", {}).get("emotion_level", 0.3)
        
        # 특성 및 능력
        self.capabilities = config.get("capabilities", [])
        self.description = config.get("description", "")
        
        # LLM 관리자 (실제 구현에서는 주입 방식으로 설정)
        self.llm_manager = None
        
        # 참여자 상태 초기화
        self.state.update({
            "last_response_time": 0,
            "topic_opinions": {},
            "interaction_history": [],
            "current_context": {},
            "emotions": {}
        })
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 처리 및 응답 생성
        
        Args:
            input_data: 처리할 입력 데이터 (대화 상태, 현재 질문 등)
            
        Returns:
            응답 및 상태 정보
        """
        dialogue_state = input_data.get("dialogue_state")
        query = input_data.get("query", "")
        context = input_data.get("context", {})
        is_my_turn = input_data.get("is_my_turn", False)
        
        if not is_my_turn:
            return {"response": None, "status": "waiting"}
        
        # 응답 생성 (실제 구현에서는 LLM 사용)
        response = self._generate_response(query, dialogue_state, context)
        
        # 상태 업데이트
        self._update_interaction_history(query, response)
        
        return {
            "response": response,
            "viewpoint": self.viewpoint,
            "emotions": self._get_current_emotions(),
            "status": "responded"
        }
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        참여자 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        self.state.update(state_update)
    
    def set_llm_manager(self, llm_manager: LLMManager) -> None:
        """
        LLM 관리자 설정
        
        Args:
            llm_manager: LLM 관리자 인스턴스
        """
        self.llm_manager = llm_manager
    
    def _generate_response(self, query: str, dialogue_state: Any, context: Dict[str, Any]) -> str:
        """
        쿼리에 대한 응답 생성
        
        Args:
            query: 입력 쿼리
            dialogue_state: 대화 상태
            context: 추가 컨텍스트
            
        Returns:
            생성된 응답
        """
        if self.llm_manager:
            # 실제 구현: LLM을 사용하여 응답 생성
            prompt = self._construct_response_prompt(query, dialogue_state, context)
            return self.llm_manager.generate_text(prompt)
        
        # 기본 응답 (LLM 없을 경우)
        if self.viewpoint == "pro":
            return f"저는 {self.name}입니다. 해당 주제에 찬성하는 입장에서, 다음과 같은 점을 고려해볼 수 있습니다..."
        elif self.viewpoint == "con":
            return f"저는 {self.name}입니다. 해당 주제에 반대하는 입장에서, 다음과 같은 문제점을 지적하고 싶습니다..."
        else:
            return f"저는 {self.name}입니다. 중립적 관점에서 다양한 측면을 살펴보겠습니다..."
    
    def _construct_response_prompt(self, query: str, dialogue_state: Any, context: Dict[str, Any]) -> str:
        """
        응답 생성을 위한 프롬프트 구성
        
        Args:
            query: 입력 쿼리
            dialogue_state: 대화 상태
            context: 추가 컨텍스트
            
        Returns:
            구성된 프롬프트
        """
        # 실제 구현에서는 더 정교한 프롬프트 구성 필요
        topic = dialogue_state.topic if dialogue_state else "지정된 주제"
        previous_messages = dialogue_state.get_recent_messages(5) if dialogue_state else []
        
        prompt = f"""
        당신은 '{self.name}'이라는 이름의 대화 참여자입니다.
        특성: {self.description}
        관점: {self.viewpoint} ({"찬성" if self.viewpoint == "pro" else "반대" if self.viewpoint == "con" else "중립"})
        
        주제: {topic}
        
        이전 대화:
        """
        
        for msg in previous_messages:
            prompt += f"\n{msg.sender_name}: {msg.content}"
        
        prompt += f"\n\n질문/요청: {query}\n\n{self.name}으로서 응답해주세요:"
        
        return prompt
    
    def _update_interaction_history(self, query: str, response: str) -> None:
        """
        상호작용 기록 업데이트
        
        Args:
            query: 입력 쿼리
            response: 생성된 응답
        """
        import time
        
        interaction = {
            "timestamp": time.time(),
            "query": query,
            "response": response
        }
        
        history = self.state.get("interaction_history", [])
        history.append(interaction)
        
        # 최대 기록 수 제한
        if len(history) > 50:
            history = history[-50:]
            
        self.state["interaction_history"] = history
        self.state["last_response_time"] = interaction["timestamp"]
    
    def _get_current_emotions(self) -> Dict[str, float]:
        """
        현재 감정 상태 반환
        
        Returns:
            감정 상태 (감정 => 강도)
        """
        # 실제 구현에서는 대화 내용에 따라 감정 상태 업데이트
        return self.state.get("emotions", {
            "interest": 0.7,
            "agreement": 0.5 if self.viewpoint == "pro" else 0.2,
            "disagreement": 0.2 if self.viewpoint == "pro" else 0.7,
            "enthusiasm": self.assertiveness
        }) 