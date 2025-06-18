"""
Defense strategy management module for debate participants.

Handles defense strategy selection and response generation.
"""

import logging
import yaml
import os
import random
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class DefenseStrategyManager:
    """방어 전략 선택 및 관리를 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], 
                 strategy_styles: Dict[str, Any], llm_manager):
        """
        DefenseStrategyManager 초기화
        
        Args:
            agent_id: 에이전트 ID
            philosopher_data: 철학자 데이터
            strategy_styles: 전략 스타일 정보
            llm_manager: LLM 매니저 인스턴스
        """
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.strategy_styles = strategy_styles
        self.llm_manager = llm_manager
        
        # 철학자 정보 추출
        self.philosopher_name = philosopher_data.get("name", "Unknown Philosopher")
        self.philosopher_essence = philosopher_data.get("essence", "")
        self.philosopher_debate_style = philosopher_data.get("debate_style", "")
        self.philosopher_personality = philosopher_data.get("personality", "")
        
        # 방어 전략 히스토리
        self.defense_history = []
        self.last_defense_strategy = None
        
        # defense_map.yaml 경로 설정
        self._setup_defense_map_path()
    
    def _setup_defense_map_path(self):
        """defense_map.yaml 파일 경로 설정"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # 프로젝트 루트 찾기
        while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
            parent = os.path.dirname(project_root)
            if parent == project_root:
                break
            project_root = parent
        
        self.defense_map_path = os.path.join(project_root, "philosophers", "defense_map.yaml")
    
    def select_defense_strategy(self, attack_info: Dict[str, Any], 
                              emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        방어 전략 선택
        
        Args:
            attack_info: 공격 정보
            emotion_enhancement: 감정 강화 정보
            
        Returns:
            선택된 방어 전략명
        """
        logger.info(f"[{self.agent_id}] Selecting defense strategy")
        
        try:
            # 1. defense_map.yaml에서 후보 전략 가져오기
            defense_candidates = self._get_defense_candidates_from_map(attack_info, emotion_enhancement)
            
            if not defense_candidates:
                logger.warning(f"[{self.agent_id}] No defense candidates found, using default Clarify")
                return "Clarify"
            
            logger.info(f"[{self.agent_id}] Defense candidates: {defense_candidates}")
            
            # 2. 철학자의 defense_weights 가져오기
            defense_weights = self.philosopher_data.get("defense_weights", {})
            
            if not defense_weights:
                logger.warning(f"[{self.agent_id}] No defense weights found, using first candidate")
                return defense_candidates[0]
            
            logger.info(f"[{self.agent_id}] Defense weights: {defense_weights}")
            
            # 3. 후보 전략들에 대한 가중치만 추출하고 정규화
            candidate_weights = {}
            total_weight = 0.0
            
            for strategy in defense_candidates:
                weight = defense_weights.get(strategy, 0.1)  # 기본값 0.1
                candidate_weights[strategy] = weight
                total_weight += weight
            
            if total_weight == 0:
                logger.warning(f"[{self.agent_id}] Total weight is 0, using first candidate")
                return defense_candidates[0]
            
            # 정규화
            normalized_weights = {k: v/total_weight for k, v in candidate_weights.items()}
            logger.info(f"[{self.agent_id}] Normalized weights: {normalized_weights}")
            
            # 4. 확률적 선택
            rand_val = random.random()
            cumulative = 0.0
            
            for strategy, prob in normalized_weights.items():
                cumulative += prob
                if rand_val <= cumulative:
                    logger.info(f"[{self.agent_id}] Selected defense strategy: {strategy} (prob: {prob:.3f})")
                    return strategy
            
            # 혹시나 하는 fallback
            selected = defense_candidates[0]
            logger.info(f"[{self.agent_id}] Fallback defense strategy: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error selecting defense strategy: {str(e)}")
            return "Clarify"
    
    def _get_defense_candidates_from_map(self, attack_info: Dict[str, Any], 
                                       emotion_enhancement: Dict[str, Any] = None) -> List[str]:
        """
        defense_map.yaml에서 방어 후보 전략들 가져오기
        
        Args:
            attack_info: 공격 정보
            emotion_enhancement: 감정 정보
            
        Returns:
            방어 후보 전략 목록
        """
        try:
            if not os.path.exists(self.defense_map_path):
                logger.warning(f"[{self.agent_id}] defense_map.yaml not found: {self.defense_map_path}")
                return ["Clarify", "Accept"]  # 기본값
            
            with open(self.defense_map_path, 'r', encoding='utf-8') as f:
                defense_map = yaml.safe_load(f)
            
            # 공격 전략과 RAG 사용 여부
            attack_strategy = attack_info.get("attack_strategy", "Unknown")
            rag_used = attack_info.get("rag_used", False)
            
            # 감정 상태 (없으면 neutral)
            emotion_state = "neutral"
            if emotion_enhancement:
                emotion_state = emotion_enhancement.get("emotion_type", "neutral")
            
            rag_key = "RAG_YES" if rag_used else "RAG_NO"
            
            logger.info(f"[{self.agent_id}] Defense map lookup: {attack_strategy} -> {rag_key} -> {emotion_state}")
            
            # defense_map에서 후보 찾기
            if attack_strategy in defense_map:
                strategy_map = defense_map[attack_strategy]
                if rag_key in strategy_map:
                    emotion_map = strategy_map[rag_key]
                    if emotion_state in emotion_map:
                        candidates = emotion_map[emotion_state]
                        logger.info(f"[{self.agent_id}] Found defense candidates: {candidates}")
                        return candidates if isinstance(candidates, list) else [candidates]
                    else:
                        logger.warning(f"[{self.agent_id}] Emotion state '{emotion_state}' not found in {list(emotion_map.keys())}")
                else:
                    logger.warning(f"[{self.agent_id}] RAG key '{rag_key}' not found in {list(strategy_map.keys())}")
            else:
                logger.warning(f"[{self.agent_id}] Attack strategy '{attack_strategy}' not found in {list(defense_map.keys())}")
            
            # 찾지 못한 경우 기본값
            logger.warning(f"[{self.agent_id}] No candidates found in defense map, using defaults")
            return ["Clarify", "Accept"]
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error getting defense candidates: {str(e)}")
            return ["Clarify", "Accept"]
    
    def generate_defense_response(self, topic: str, recent_messages: List[Dict[str, Any]], 
                                stance_statements: Dict[str, str], defense_strategy: str,
                                defense_rag_decision: Dict[str, Any], 
                                emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        방어 전략에 따른 응답 생성
        
        Args:
            topic: 토론 주제
            recent_messages: 최근 메시지 목록
            stance_statements: 입장 진술문
            defense_strategy: 선택된 방어 전략
            defense_rag_decision: RAG 사용 결정
            emotion_enhancement: 감정 강화 데이터
            
        Returns:
            생성된 방어 응답
        """
        logger.info(f"[{self.agent_id}] Generating defense response with strategy: {defense_strategy}")
        
        try:
            # 방어 전략 정보 가져오기
            defense_info = self._get_defense_strategy_info(defense_strategy)
            
            # 상대방 정보
            attacker_name = self._get_philosopher_name(recent_messages[-1].get('speaker_id', 'unknown'))
            attack_text = recent_messages[-1].get('text', '') if recent_messages else ''
            
            # 내 입장
            my_stance = stance_statements.get(self.agent_id.split('_')[-1], "")  # role 추출
            
            # 시스템 프롬프트
            system_prompt = f"""
You are {self.philosopher_name}, a philosopher with this essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}

You are responding defensively using the "{defense_strategy}" strategy.
Strategy description: {defense_info.get('description', '')}
Strategy purpose: {defense_info.get('purpose', '')}
Style prompt: {defense_info.get('style_prompt', '')}

Your response should be:
1. SHORT and DIRECT (2-3 sentences maximum)
2. Use the {defense_strategy} approach
3. Address {attacker_name} directly
4. Maintain your philosophical character

CRITICAL: Write your ENTIRE response in the SAME LANGUAGE as the debate topic.
If the topic is in Korean, respond in Korean. If in English, respond in English.
"""

            # 유저 프롬프트
            user_prompt = f"""
DEBATE TOPIC: "{topic}"
YOUR POSITION: {my_stance}

{attacker_name}'S ATTACK: "{attack_text}"

DEFENSE STRATEGY: {defense_strategy}
- Description: {defense_info.get('description', '')}
- Style: {defense_info.get('style_prompt', '')}
- Example approach: {defense_info.get('example', '')}

TASK: Generate a SHORT defensive response (2-3 sentences max) that:
1. Uses the {defense_strategy} approach
2. Addresses {attacker_name} directly by name
3. Defends against their attack effectively
4. Maintains your philosophical perspective

IMPORTANT: Write your response in the SAME LANGUAGE as the debate topic "{topic}".
If the topic contains Korean text, write in Korean. If in English, write in English.

"""

            # RAG 사용하는 경우 검색 수행
            if defense_rag_decision.get('use_rag', False):
                # RAG 검색은 외부에서 수행되어 결과가 전달됨
                rag_results = defense_rag_decision.get('results', [])
                if rag_results:
                    rag_formatted = self._format_defense_rag_results(rag_results, defense_strategy)
                    user_prompt += f"""
{rag_formatted}
INSTRUCTION: Incorporate this supporting information naturally into your {defense_strategy} response.
"""
                    logger.info(f"[{self.agent_id}] Added RAG information ({len(rag_results)} results)")

            user_prompt += f"""
Remember: Be CONCISE, DIRECT, and use the {defense_strategy} approach. 
Address {attacker_name} directly and defend effectively.
Write in the SAME LANGUAGE as the topic "{topic}".

Your {defense_strategy} defense:"""

            # 감정 강화 적용
            if emotion_enhancement:
                try:
                    from ...utility.debate_emotion_inference import apply_debate_emotion_to_prompt
                    system_prompt, user_prompt = apply_debate_emotion_to_prompt(
                        system_prompt, user_prompt, emotion_enhancement
                    )
                    logger.info(f"[{self.agent_id}] Applied emotion enhancement: {emotion_enhancement.get('emotion_type', 'unknown')}")
                except ImportError:
                    logger.warning(f"[{self.agent_id}] Could not import emotion enhancement module")

            # LLM 호출
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=400
            )
            
            # 방어 전략 정보 저장
            self._save_defense_strategy_info(defense_strategy, defense_rag_decision, attack_text)
            
            logger.info(f"[{self.agent_id}] Generated defense response successfully")
            return response.strip()
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error generating defense response: {str(e)}")
            return f"I need to consider {attacker_name}'s point more carefully before responding."
    
    def _get_defense_strategy_info(self, defense_strategy: str) -> Dict[str, Any]:
        """
        방어 전략 정보 가져오기
        
        Args:
            defense_strategy: 방어 전략명
            
        Returns:
            방어 전략 정보
        """
        # defense_strategies.json에서 정보 가져오기
        defense_strategies = self.strategy_styles.get("defense_strategies", {})
        return defense_strategies.get(defense_strategy, {
            "description": f"Use {defense_strategy} approach",
            "purpose": f"Defend using {defense_strategy}",
            "style_prompt": f"Apply {defense_strategy} strategy",
            "example": f"Example of {defense_strategy} defense"
        })
    
    def _get_philosopher_name(self, agent_id: str) -> str:
        """
        에이전트 ID에서 철학자 이름 추출
        
        Args:
            agent_id: 에이전트 ID
            
        Returns:
            철학자 이름
        """
        # 간단한 매핑 (실제로는 더 복잡한 로직이 필요할 수 있음)
        name_mapping = {
            "socrates": "Socrates",
            "plato": "Plato", 
            "aristotle": "Aristotle",
            "kant": "Kant",
            "nietzsche": "Nietzsche",
            "confucius": "Confucius"
        }
        
        for key, name in name_mapping.items():
            if key in agent_id.lower():
                return name
        
        return agent_id.replace('_', ' ').title()
    
    def _format_defense_rag_results(self, rag_results: List[Dict[str, Any]], 
                                  defense_strategy: str) -> str:
        """
        방어용 RAG 결과 포맷팅
        
        Args:
            rag_results: RAG 검색 결과
            defense_strategy: 방어 전략
            
        Returns:
            포맷팅된 RAG 결과
        """
        if not rag_results:
            return ""
        
        formatted = f"\n=== SUPPORTING INFORMATION FOR {defense_strategy.upper()} DEFENSE ===\n"
        
        for i, result in enumerate(rag_results[:3], 1):  # 최대 3개만 사용
            content = result.get('content', '')[:200]  # 200자로 제한
            source = result.get('source', 'Unknown')
            
            formatted += f"{i}. {content}... (Source: {source})\n"
        
        formatted += "=== END SUPPORTING INFORMATION ===\n"
        return formatted
    
    def _save_defense_strategy_info(self, defense_strategy: str, 
                                  defense_rag_decision: Dict[str, Any], 
                                  attack_text: str):
        """
        방어 전략 정보 저장
        
        Args:
            defense_strategy: 사용된 방어 전략
            defense_rag_decision: RAG 사용 결정
            attack_text: 공격 텍스트
        """
        import time
        from datetime import datetime
        
        defense_info = {
            'strategy_type': defense_strategy,
            'rag_decision': defense_rag_decision,
            'attack_text': attack_text[:200],  # 일부만 저장
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        # 방어 전략을 에이전트 속성에 저장
        self.last_defense_strategy = defense_info
        
        # 방어 기록도 저장 (여러 방어 전략 히스토리)
        self.defense_history.append(defense_info)
        
        # 히스토리 크기 제한 (최대 10개)
        if len(self.defense_history) > 10:
            self.defense_history = self.defense_history[-10:]
        
        logger.info(f"[{self.agent_id}] Saved defense strategy info: {defense_strategy}")
    
    def get_last_defense_strategy(self) -> Optional[Dict[str, Any]]:
        """
        마지막 방어 전략 정보 반환
        
        Returns:
            마지막 방어 전략 정보 (없으면 None)
        """
        return self.last_defense_strategy
    
    def get_defense_history(self) -> List[Dict[str, Any]]:
        """
        방어 전략 히스토리 반환
        
        Returns:
            방어 전략 히스토리 목록
        """
        return self.defense_history.copy()
    
    def clear_defense_history(self):
        """방어 전략 히스토리 정리"""
        self.defense_history.clear()
        self.last_defense_strategy = None
        logger.info(f"[{self.agent_id}] Cleared defense history")
    
    def get_defense_statistics(self) -> Dict[str, Any]:
        """
        방어 전략 통계 반환
        
        Returns:
            방어 전략 통계
        """
        if not self.defense_history:
            return {
                "total_defenses": 0,
                "strategy_distribution": {},
                "rag_usage_rate": 0.0
            }
        
        strategy_counts = {}
        rag_usage_count = 0
        
        for defense in self.defense_history:
            strategy = defense["strategy_type"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            if defense["rag_decision"].get("use_rag", False):
                rag_usage_count += 1
        
        return {
            "total_defenses": len(self.defense_history),
            "strategy_distribution": strategy_counts,
            "rag_usage_rate": rag_usage_count / len(self.defense_history) if self.defense_history else 0.0,
            "last_strategy": self.last_defense_strategy["strategy_type"] if self.last_defense_strategy else None
        } 