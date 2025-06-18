"""
Followup strategy management module for debate participants.

Handles followup strategy selection and response generation after defense.
"""

import logging
import yaml
import os
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FollowupStrategyManager:
    """팔로우업 전략 선택 및 관리를 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], 
                 strategy_styles: Dict[str, Any], llm_manager):
        """
        FollowupStrategyManager 초기화
        
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
        
        # 팔로우업 전략 히스토리
        self.followup_strategies = []
        self.last_followup_strategy = None
        
        # followup_map.yaml 경로 설정
        self._setup_followup_map_path()
    
    def _setup_followup_map_path(self):
        """followup_map.yaml 파일 경로 설정"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = current_dir
        
        # 프로젝트 루트 찾기
        while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
            parent = os.path.dirname(project_root)
            if parent == project_root:
                break
            project_root = parent
        
        self.followup_map_path = os.path.join(project_root, "philosophers", "followup_map.yaml")
    
    def select_followup_strategy(self, defense_info: Dict[str, Any], 
                               emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        팔로우업 전략 선택
        
        Args:
            defense_info: 방어 정보
            emotion_enhancement: 감정 강화 정보
            
        Returns:
            선택된 팔로우업 전략명
        """
        logger.info(f"[{self.agent_id}] Selecting followup strategy")
        
        try:
            # 1. followup_map.yaml에서 후보 전략 가져오기
            followup_candidates = self._get_followup_candidates_from_map(defense_info, emotion_enhancement)
            
            if not followup_candidates:
                logger.warning(f"[{self.agent_id}] No followup candidates found, using default FollowUpQuestion")
                return "FollowUpQuestion"
            
            logger.info(f"[{self.agent_id}] Followup candidates: {followup_candidates}")
            
            # 2. 철학자의 followup_weights 가져오기
            followup_weights = self.philosopher_data.get("followup_weights", {})
            
            if not followup_weights:
                logger.warning(f"[{self.agent_id}] No followup weights found, using first candidate")
                return followup_candidates[0]
            
            logger.info(f"[{self.agent_id}] Followup weights: {followup_weights}")
            
            # 3. 후보 전략들에 대한 가중치만 추출하고 정규화
            candidate_weights = {}
            total_weight = 0.0
            
            for strategy in followup_candidates:
                weight = followup_weights.get(strategy, 0.1)  # 기본값 0.1
                candidate_weights[strategy] = weight
                total_weight += weight
            
            if total_weight == 0:
                logger.warning(f"[{self.agent_id}] Total weight is 0, using first candidate")
                return followup_candidates[0]
            
            # 정규화
            normalized_weights = {k: v/total_weight for k, v in candidate_weights.items()}
            logger.info(f"[{self.agent_id}] Normalized weights: {normalized_weights}")
            
            # 4. 확률적 선택
            rand_val = random.random()
            cumulative = 0.0
            
            for strategy, prob in normalized_weights.items():
                cumulative += prob
                if rand_val <= cumulative:
                    logger.info(f"[{self.agent_id}] Selected followup strategy: {strategy} (prob: {prob:.3f})")
                    return strategy
            
            # 혹시나 하는 fallback
            selected = followup_candidates[0]
            logger.info(f"[{self.agent_id}] Fallback followup strategy: {selected}")
            return selected
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error selecting followup strategy: {str(e)}")
            return "FollowUpQuestion"
    
    def _get_followup_candidates_from_map(self, defense_info: Dict[str, Any], 
                                        emotion_enhancement: Dict[str, Any] = None) -> List[str]:
        """
        followup_map.yaml에서 팔로우업 후보 전략들 가져오기
        
        Args:
            defense_info: 방어 정보
            emotion_enhancement: 감정 정보
            
        Returns:
            팔로우업 후보 전략 목록
        """
        try:
            if not os.path.exists(self.followup_map_path):
                logger.warning(f"[{self.agent_id}] followup_map.yaml not found: {self.followup_map_path}")
                return ["FollowUpQuestion", "Pivot"]  # 기본값
            
            with open(self.followup_map_path, 'r', encoding='utf-8') as f:
                followup_map = yaml.safe_load(f)
            
            # 방어 전략과 RAG 사용 여부
            defense_strategy = defense_info.get("defense_strategy", "Unknown")
            rag_used = defense_info.get("rag_used", False)
            
            # 감정 상태 (없으면 neutral)
            emotion_state = "neutral"
            if emotion_enhancement:
                emotion_state = emotion_enhancement.get("emotion_type", "neutral")
            
            rag_key = "RAG_YES" if rag_used else "RAG_NO"
            
            logger.info(f"[{self.agent_id}] Followup map lookup: {defense_strategy} -> {rag_key} -> {emotion_state}")
            
            # followup_map에서 후보 찾기
            if defense_strategy in followup_map:
                strategy_map = followup_map[defense_strategy]
                if rag_key in strategy_map:
                    emotion_map = strategy_map[rag_key]
                    if emotion_state in emotion_map:
                        candidates = emotion_map[emotion_state]
                        logger.info(f"[{self.agent_id}] Found followup candidates: {candidates}")
                        return candidates if isinstance(candidates, list) else [candidates]
                    else:
                        logger.warning(f"[{self.agent_id}] Emotion state '{emotion_state}' not found in {list(emotion_map.keys())}")
                else:
                    logger.warning(f"[{self.agent_id}] RAG key '{rag_key}' not found in {list(strategy_map.keys())}")
            else:
                logger.warning(f"[{self.agent_id}] Defense strategy '{defense_strategy}' not found in {list(followup_map.keys())}")
            
            # 찾지 못한 경우 기본값
            logger.warning(f"[{self.agent_id}] No candidates found in followup map, using defaults")
            return ["FollowUpQuestion", "Pivot"]
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error getting followup candidates: {str(e)}")
            return ["FollowUpQuestion", "Pivot"]
    
    def generate_followup_response(self, topic: str, recent_messages: List[Dict[str, Any]], 
                                 stance_statements: Dict[str, str], followup_strategy: str,
                                 followup_rag_decision: Dict[str, Any], 
                                 emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        팔로우업 전략에 따른 응답 생성
        
        Args:
            topic: 토론 주제
            recent_messages: 최근 메시지 목록
            stance_statements: 입장 진술문
            followup_strategy: 선택된 팔로우업 전략
            followup_rag_decision: RAG 사용 결정
            emotion_enhancement: 감정 강화 데이터
            
        Returns:
            생성된 팔로우업 응답
        """
        logger.info(f"[{self.agent_id}] Generating followup response with strategy: {followup_strategy}")
        
        try:
            # 팔로우업 전략 정보 가져오기
            followup_info = self._get_followup_strategy_info(followup_strategy)
            
            # 상대방 정보
            defender_name = self._get_philosopher_name(recent_messages[-1].get('speaker_id', 'unknown'))
            defense_text = recent_messages[-1].get('text', '') if recent_messages else ''
            
            # 내 입장
            my_stance = stance_statements.get(self.agent_id.split('_')[-1], "")  # role 추출
            
            # 내 원래 공격 (2개 전 메시지)
            my_original_attack = ""
            if len(recent_messages) >= 2:
                my_original_attack = recent_messages[-2].get('text', '')
            
            # 시스템 프롬프트
            system_prompt = f"""
You are {self.philosopher_name}, a philosopher with this essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}

You are following up using the "{followup_strategy}" strategy after {defender_name} defended against your attack.
Strategy description: {followup_info.get('description', '')}
Strategy purpose: {followup_info.get('purpose', '')}
Style prompt: {followup_info.get('style_prompt', '')}

Your response should be:
1. SHORT and DIRECT (2-3 sentences maximum)
2. Use the {followup_strategy} approach
3. Address {defender_name} directly
4. Maintain your philosophical character

CRITICAL: Write your ENTIRE response in the SAME LANGUAGE as the debate topic.
If the topic is in Korean, respond in Korean. If in English, respond in English.
"""

            # 유저 프롬프트
            user_prompt = f"""
DEBATE TOPIC: "{topic}"
YOUR POSITION: {my_stance}

YOUR ORIGINAL ATTACK: "{my_original_attack}"
{defender_name}'S DEFENSE: "{defense_text}"

FOLLOWUP STRATEGY: {followup_strategy}
- Description: {followup_info.get('description', '')}
- Style: {followup_info.get('style_prompt', '')}
- Example approach: {followup_info.get('example', '')}

TASK: Generate a SHORT followup response (2-3 sentences max) that:
1. Uses the {followup_strategy} approach
2. Addresses {defender_name} directly by name
3. Responds to their defense strategically
4. Maintains your philosophical perspective

IMPORTANT: Write your response in the SAME LANGUAGE as the debate topic "{topic}".
If the topic contains Korean text, write in Korean. If in English, write in English.

"""

            # RAG 사용하는 경우 검색 수행
            if followup_rag_decision.get('use_rag', False):
                # RAG 검색은 외부에서 수행되어 결과가 전달됨
                rag_results = followup_rag_decision.get('results', [])
                if rag_results:
                    rag_formatted = self._format_followup_rag_results(rag_results, followup_strategy)
                    user_prompt += f"""
{rag_formatted}
INSTRUCTION: Incorporate this supporting information naturally into your {followup_strategy} response.
"""
                    logger.info(f"[{self.agent_id}] Added RAG information ({len(rag_results)} results)")

            user_prompt += f"""
Remember: Be CONCISE, DIRECT, and use the {followup_strategy} approach. 
Address {defender_name} directly and follow up strategically.
Write in the SAME LANGUAGE as the topic "{topic}".

Your {followup_strategy} followup:"""

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
            
            # 팔로우업 전략 정보 저장
            self._save_followup_strategy_info(followup_strategy, followup_rag_decision, defense_text, my_original_attack)
            
            logger.info(f"[{self.agent_id}] Generated followup response successfully")
            return response.strip()
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error generating followup response: {str(e)}")
            return f"Let me reconsider my approach to {defender_name}'s defense."
    
    def analyze_defense_response(self, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        상대방의 방어 응답 분석
        
        Args:
            recent_messages: 최근 메시지 목록
            
        Returns:
            방어 응답 분석 결과
        """
        if not recent_messages:
            return {"defense_strategy": "Unknown", "rag_used": False, "defender_id": "unknown"}
        
        last_message = recent_messages[-1]
        defender_id = last_message.get('speaker_id', 'unknown')
        defense_text = last_message.get('text', '')
        
        logger.info(f"[{self.agent_id}] Analyzing defense response from {defender_id}")
        
        # 방어자 에이전트의 실제 방어 전략 정보 가져오기 (가능하면)
        defense_info = self._get_defender_strategy_info(defender_id)
        
        if defense_info["defense_strategy"] != "Unknown":
            logger.info(f"[{self.agent_id}] Found actual defense strategy: {defense_info['defense_strategy']}")
        else:
            logger.warning(f"[{self.agent_id}] No defense strategy info found, using keyword estimation")
            # Fallback: 키워드 기반 추정
            defense_info = self._estimate_defense_strategy_from_keywords(defense_text, defender_id)
        
        defense_info["defender_id"] = defender_id
        defense_info["defense_text"] = defense_text[:200]  # 분석용 일부 텍스트
        
        return defense_info
    
    def _get_defender_strategy_info(self, defender_id: str) -> Dict[str, Any]:
        """
        방어자의 전략 정보 가져오기 (실제 구현에서는 에이전트 간 통신 필요)
        
        Args:
            defender_id: 방어자 ID
            
        Returns:
            방어 전략 정보
        """
        # 실제 구현에서는 에이전트 매니저나 공유 상태에서 정보를 가져와야 함
        # 여기서는 기본값 반환
        return {
            "defense_strategy": "Unknown",
            "rag_used": False
        }
    
    def _estimate_defense_strategy_from_keywords(self, defense_text: str, defender_id: str) -> Dict[str, Any]:
        """
        키워드 기반 방어 전략 추정
        
        Args:
            defense_text: 방어 텍스트
            defender_id: 방어자 ID
            
        Returns:
            추정된 방어 전략 정보
        """
        defense_text_lower = defense_text.lower()
        
        # 키워드 기반 전략 추정
        if any(word in defense_text_lower for word in ["clarify", "explain", "mean", "정확히", "명확히"]):
            strategy = "Clarify"
        elif any(word in defense_text_lower for word in ["accept", "agree", "right", "맞다", "동의"]):
            strategy = "Accept"
        elif any(word in defense_text_lower for word in ["counter", "however", "but", "하지만", "그러나"]):
            strategy = "Counter"
        elif any(word in defense_text_lower for word in ["redirect", "focus", "important", "중요한", "집중"]):
            strategy = "Redirect"
        else:
            strategy = "Unknown"
        
        # RAG 사용 추정 (길이와 구체성 기반)
        rag_used = len(defense_text) > 100 and any(word in defense_text_lower for word in 
                                                  ["research", "study", "data", "연구", "데이터", "조사"])
        
        logger.info(f"[{self.agent_id}] Estimated defense strategy: {strategy}, RAG used: {rag_used}")
        
        return {
            "defense_strategy": strategy,
            "rag_used": rag_used
        }
    
    def _get_followup_strategy_info(self, followup_strategy: str) -> Dict[str, Any]:
        """
        팔로우업 전략 정보 가져오기
        
        Args:
            followup_strategy: 팔로우업 전략명
            
        Returns:
            팔로우업 전략 정보
        """
        # followup_strategies.json에서 정보 가져오기
        followup_strategies = self.strategy_styles.get("followup_strategies", {})
        return followup_strategies.get(followup_strategy, {
            "description": f"Use {followup_strategy} approach",
            "purpose": f"Follow up using {followup_strategy}",
            "style_prompt": f"Apply {followup_strategy} strategy",
            "example": f"Example of {followup_strategy} followup"
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
    
    def _format_followup_rag_results(self, rag_results: List[Dict[str, Any]], 
                                   followup_strategy: str) -> str:
        """
        팔로우업용 RAG 결과 포맷팅
        
        Args:
            rag_results: RAG 검색 결과
            followup_strategy: 팔로우업 전략
            
        Returns:
            포맷팅된 RAG 결과
        """
        if not rag_results:
            return ""
        
        formatted = f"\n=== SUPPORTING INFORMATION FOR {followup_strategy.upper()} FOLLOWUP ===\n"
        
        for i, result in enumerate(rag_results[:3], 1):  # 최대 3개만 사용
            content = result.get('content', '')[:200]  # 200자로 제한
            source = result.get('source', 'Unknown')
            
            formatted += f"{i}. {content}... (Source: {source})\n"
        
        formatted += "=== END SUPPORTING INFORMATION ===\n"
        return formatted
    
    def _save_followup_strategy_info(self, followup_strategy: str, 
                                   followup_rag_decision: Dict[str, Any], 
                                   defense_text: str, original_attack: str):
        """
        팔로우업 전략 정보 저장
        
        Args:
            followup_strategy: 사용된 팔로우업 전략
            followup_rag_decision: RAG 사용 결정
            defense_text: 방어 텍스트
            original_attack: 원래 공격 텍스트
        """
        import time
        
        defense_info_summary = {
            "defense_strategy": "Unknown",  # 실제로는 분석 결과 사용
            "rag_used": False,
            "defender_id": "unknown"
        }
        
        # 팔로우업 정보 저장
        followup_info = {
            "timestamp": datetime.now().isoformat(),
            "followup_strategy": followup_strategy,
            "rag_decision": followup_rag_decision,
            "followup_plan": {
                "defense_info": defense_info_summary,
                "selected_strategy": followup_strategy,
                "emotion_state": "neutral",  # 실제로는 감정 정보 사용
                "source": "followup_system"
            }
        }
        
        self.followup_strategies.append(followup_info)
        
        # 팔로우업 전략 정보를 클래스 레벨에 저장
        self.last_followup_strategy = {
            "followup_strategy": followup_strategy,
            "rag_decision": followup_rag_decision,
            "followup_plan": {
                "defense_info": defense_info_summary,
                "emotion_state": "neutral"
            }
        }
        
        # 히스토리 크기 제한 (최대 10개)
        if len(self.followup_strategies) > 10:
            self.followup_strategies = self.followup_strategies[-10:]
        
        logger.info(f"[{self.agent_id}] Saved followup strategy info: {followup_strategy}")
    
    def get_last_followup_strategy(self) -> Optional[Dict[str, Any]]:
        """
        마지막 팔로우업 전략 정보 반환
        
        Returns:
            마지막 팔로우업 전략 정보 (없으면 None)
        """
        return self.last_followup_strategy
    
    def get_followup_history(self) -> List[Dict[str, Any]]:
        """
        팔로우업 전략 히스토리 반환
        
        Returns:
            팔로우업 전략 히스토리 목록
        """
        return self.followup_strategies.copy()
    
    def clear_followup_history(self):
        """팔로우업 전략 히스토리 정리"""
        self.followup_strategies.clear()
        self.last_followup_strategy = None
        logger.info(f"[{self.agent_id}] Cleared followup history")
    
    def get_followup_statistics(self) -> Dict[str, Any]:
        """
        팔로우업 전략 통계 반환
        
        Returns:
            팔로우업 전략 통계
        """
        if not self.followup_strategies:
            return {
                "total_followups": 0,
                "strategy_distribution": {},
                "rag_usage_rate": 0.0
            }
        
        strategy_counts = {}
        rag_usage_count = 0
        
        for followup in self.followup_strategies:
            strategy = followup["followup_strategy"]
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            if followup["rag_decision"].get("use_rag", False):
                rag_usage_count += 1
        
        return {
            "total_followups": len(self.followup_strategies),
            "strategy_distribution": strategy_counts,
            "rag_usage_rate": rag_usage_count / len(self.followup_strategies) if self.followup_strategies else 0.0,
            "last_strategy": self.last_followup_strategy["followup_strategy"] if self.last_followup_strategy else None
        } 