"""
Attack strategy management module for debate participants.

Handles attack strategy selection, planning, and execution.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AttackStrategyManager:
    """공격 전략 선택 및 관리를 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], 
                 strategy_styles: Dict[str, Any], strategy_weights: Dict[str, float],
                 llm_manager):
        """
        AttackStrategyManager 초기화
        
        Args:
            agent_id: 에이전트 ID
            philosopher_data: 철학자 데이터
            strategy_styles: 전략 스타일 정보
            strategy_weights: 전략 가중치
            llm_manager: LLM 매니저 인스턴스
        """
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.strategy_styles = strategy_styles
        self.strategy_weights = strategy_weights
        self.llm_manager = llm_manager
        
        # 철학자 정보 추출
        self.philosopher_name = philosopher_data.get("name", "Unknown Philosopher")
        self.philosopher_essence = philosopher_data.get("essence", "")
        self.philosopher_debate_style = philosopher_data.get("debate_style", "")
        self.philosopher_personality = philosopher_data.get("personality", "")
        
        # 공격 전략 저장소
        self.attack_strategies = {}
    
    def prepare_attack_strategies_for_speaker(self, target_speaker_id: str, 
                                            opponent_arguments: Dict[str, List[Dict[str, Any]]],
                                            rag_manager=None) -> Dict[str, Any]:
        """
        특정 상대방에 대한 공격 전략들을 준비
        
        Args:
            target_speaker_id: 공격 대상 발언자 ID
            opponent_arguments: 상대방 논지 데이터
            rag_manager: RAG 매니저 (선택적)
            
        Returns:
            준비된 공격 전략 결과
        """
        logger.info(f"[{self.agent_id}] Preparing attack strategies for {target_speaker_id}")
        
        if target_speaker_id not in opponent_arguments:
            logger.warning(f"[{self.agent_id}] No arguments found for {target_speaker_id}")
            return {
                "status": "failed",
                "reason": "no_arguments_found",
                "strategies": [],
                "target_speaker_id": target_speaker_id,
                "strategies_count": 0
            }
        
        try:
            # 상대방의 취약한 논지들 가져오기 (상위 3개)
            target_arguments = opponent_arguments[target_speaker_id]
            logger.info(f"[{self.agent_id}] Found {len(target_arguments)} arguments for {target_speaker_id}")
            
            vulnerable_args = sorted(target_arguments, 
                                   key=lambda x: x.get("vulnerability_rank", 0), 
                                   reverse=True)[:3]
            
            strategies = []
            for arg_data in vulnerable_args:
                argument = arg_data["argument"]
                
                # 이 철학자에게 적합한 공격 전략 선택
                best_strategy = self.select_best_strategy_for_argument(argument)
                
                # 구체적인 공격 계획 생성
                attack_plan = self.generate_attack_plan(argument, best_strategy)
                
                # RAG 사용 여부는 외부 rag_manager에서 결정
                rag_decision = {"use_rag": False, "query": "", "results": [], "results_count": 0}
                if rag_manager:
                    rag_decision = rag_manager.determine_attack_rag_usage(best_strategy, argument)
                
                strategies.append({
                    "target_argument": argument,
                    "strategy_type": best_strategy,
                    "attack_plan": attack_plan,
                    "vulnerability_score": arg_data.get("vulnerability_rank", 0),
                    "priority": len(strategies) + 1,
                    "rag_decision": rag_decision
                })
            
            # 공격 전략 저장
            self.attack_strategies[target_speaker_id] = strategies
            logger.info(f"[{self.agent_id}] Prepared {len(strategies)} attack strategies")
            
            # RAG 사용 통계
            rag_usage_count = sum(1 for s in strategies if s["rag_decision"]["use_rag"])
            
            return {
                "status": "success",
                "strategies": strategies,
                "target_speaker_id": target_speaker_id,
                "strategies_count": len(strategies),
                "rag_usage_count": rag_usage_count
            }
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error preparing attack strategies: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "strategies": [],
                "target_speaker_id": target_speaker_id,
                "strategies_count": 0
            }
    
    def select_best_strategy_for_argument(self, argument: Dict[str, Any]) -> str:
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
        logger.info(f"[{self.agent_id}] Selected strategy: {best_strategy} (score: {strategy_scores[best_strategy]:.2f})")
        return best_strategy
    
    def generate_attack_plan(self, target_argument: Dict[str, Any], strategy_type: str) -> Dict[str, Any]:
        """
        특정 전략을 사용한 구체적인 공격 계획 생성
        
        Args:
            target_argument: 공격할 논지
            strategy_type: 사용할 전략 유형
            
        Returns:
            구체적인 공격 계획
        """
        try:
            # 전략 정보 가져오기
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
                llm_model="gpt-4o",
                max_tokens=800
            )
            
            # JSON 파싱
            json_pattern = r'\{.*?\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                attack_plan = json.loads(json_match.group(0))
                logger.info(f"[{self.agent_id}] Generated attack plan for {strategy_type}")
                return attack_plan
            else:
                logger.warning(f"[{self.agent_id}] Could not parse attack plan JSON")
                return self._get_fallback_attack_plan(target_argument, strategy_type)
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error generating attack plan: {str(e)}")
            return self._get_fallback_attack_plan(target_argument, strategy_type)
    
    def _get_fallback_attack_plan(self, target_argument: Dict[str, Any], strategy_type: str) -> Dict[str, Any]:
        """
        공격 계획 생성 실패 시 기본 계획 반환
        
        Args:
            target_argument: 공격할 논지
            strategy_type: 전략 유형
            
        Returns:
            기본 공격 계획
        """
        strategy_info = self.strategy_styles.get(strategy_type, {})
        
        return {
            "target_point": target_argument.get('claim', ''),
            "strategy_application": f"Apply {strategy_type}",
            "key_phrase": strategy_info.get('style_prompt', 'Challenge this point'),
            "expected_counter": "Opponent may defend",
            "follow_up": "Continue with philosophical reasoning"
        }
    
    def get_best_attack_strategy(self, target_speaker_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        특정 상대방에 대한 최적 공격 전략 반환
        
        Args:
            target_speaker_id: 대상 발언자 ID
            context: 현재 컨텍스트
            
        Returns:
            최적 공격 전략 (없으면 None)
        """
        if target_speaker_id not in self.attack_strategies:
            logger.warning(f"[{self.agent_id}] No attack strategies found for {target_speaker_id}")
            return None
        
        strategies = self.attack_strategies[target_speaker_id]
        if not strategies:
            return None
        
        # 가장 우선순위가 높은 전략 반환 (첫 번째)
        best_strategy = strategies[0]
        logger.info(f"[{self.agent_id}] Selected best attack strategy: {best_strategy['strategy_type']}")
        return best_strategy
    
    def clear_attack_strategies(self, speaker_id: str = None):
        """
        공격 전략 데이터 정리
        
        Args:
            speaker_id: 특정 발언자 ID (None이면 전체 정리)
        """
        if speaker_id:
            if speaker_id in self.attack_strategies:
                del self.attack_strategies[speaker_id]
                logger.info(f"[{self.agent_id}] Cleared attack strategies for {speaker_id}")
        else:
            self.attack_strategies.clear()
            logger.info(f"[{self.agent_id}] Cleared all attack strategies")
    
    def get_attack_statistics(self) -> Dict[str, Any]:
        """
        공격 전략 통계 반환
        
        Returns:
            공격 전략 통계
        """
        total_strategies = sum(len(strategies) for strategies in self.attack_strategies.values())
        strategy_types = {}
        
        for strategies in self.attack_strategies.values():
            for strategy in strategies:
                strategy_type = strategy["strategy_type"]
                strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1
        
        return {
            "total_targets": len(self.attack_strategies),
            "total_strategies": total_strategies,
            "strategy_distribution": strategy_types,
            "targets": list(self.attack_strategies.keys())
        } 