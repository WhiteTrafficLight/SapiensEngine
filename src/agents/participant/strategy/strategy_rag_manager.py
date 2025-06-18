"""
Strategy RAG management module for debate participants.

Handles RAG usage decisions and search operations for different strategies.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class StrategyRAGManager:
    """전략별 RAG 사용 결정 및 관리를 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], 
                 strategy_rag_weights: Dict[str, float], rag_search_manager=None):
        """
        StrategyRAGManager 초기화
        
        Args:
            agent_id: 에이전트 ID
            philosopher_data: 철학자 데이터
            strategy_rag_weights: 전략별 RAG 가중치
            rag_search_manager: RAG 검색 매니저 인스턴스
        """
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.strategy_rag_weights = strategy_rag_weights
        self.rag_search_manager = rag_search_manager
        
        # 철학자 RAG 친화도
        self.rag_affinity = philosopher_data.get("rag_affinity", 0.5)
        
        # RAG 사용 통계
        self.rag_usage_stats = {
            "attack": {"total": 0, "used": 0},
            "defense": {"total": 0, "used": 0},
            "followup": {"total": 0, "used": 0}
        }
    
    def determine_attack_rag_usage(self, strategy_type: str, target_argument: Dict[str, Any]) -> Dict[str, Any]:
        """
        공격 전략에 대한 RAG 사용 여부 결정
        
        Args:
            strategy_type: 공격 전략 유형
            target_argument: 공격 대상 논지
            
        Returns:
            RAG 사용 결정 결과
        """
        logger.info(f"[{self.agent_id}] Determining attack RAG usage for {strategy_type}")
        
        try:
            # 1. 전략별 RAG 가중치
            strategy_rag_weight = self._get_strategy_rag_weight(strategy_type)
            
            # 2. 철학자 RAG 친화도
            rag_affinity = self.rag_affinity
            
            # 3. 논지 복잡도에 따른 가중치
            argument_complexity_weight = self._calculate_argument_complexity_weight(target_argument)
            
            # 4. 세 값의 곱
            rag_score = strategy_rag_weight * rag_affinity * argument_complexity_weight
            
            # 5. 임계값 비교 (0.3으로 설정)
            threshold = 0.3
            use_rag = rag_score >= threshold
            
            # 통계 업데이트
            self.rag_usage_stats["attack"]["total"] += 1
            if use_rag:
                self.rag_usage_stats["attack"]["used"] += 1
            
            logger.info(f"[{self.agent_id}] Attack RAG decision: {use_rag} (score: {rag_score:.3f})")
            
            result = {
                "use_rag": use_rag,
                "rag_score": rag_score,
                "threshold": threshold,
                "strategy_rag_weight": strategy_rag_weight,
                "rag_affinity": rag_affinity,
                "argument_complexity_weight": argument_complexity_weight,
                "query": "",
                "results": [],
                "results_count": 0
            }
            
            # RAG 사용이 결정되면 검색 수행
            if use_rag and self.rag_search_manager:
                query = self._generate_attack_rag_query(target_argument, strategy_type)
                search_results = self._perform_attack_rag_search(query, strategy_type)
                
                result["query"] = query
                result["results"] = search_results
                result["results_count"] = len(search_results)
                
                logger.info(f"[{self.agent_id}] Attack RAG search completed: {len(search_results)} results")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error determining attack RAG usage: {str(e)}")
            return {
                "use_rag": False,
                "rag_score": 0.0,
                "threshold": 0.3,
                "error": str(e),
                "query": "",
                "results": [],
                "results_count": 0
            }
    
    def determine_defense_rag_usage(self, defense_strategy: str, attack_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        방어 전략에 대한 RAG 사용 여부 결정
        
        Args:
            defense_strategy: 방어 전략
            attack_info: 공격 정보
            
        Returns:
            RAG 사용 결정 결과
        """
        logger.info(f"[{self.agent_id}] Determining defense RAG usage for {defense_strategy}")
        
        try:
            # 1. 방어 전략별 RAG 가중치
            defense_rag_weight = self._get_defense_strategy_rag_weight(defense_strategy)
            
            # 2. 철학자 RAG 친화도
            rag_affinity = self.rag_affinity
            
            # 3. 공격의 RAG 사용 여부에 따른 가중치
            attack_rag_weight = 1.0 if attack_info.get("rag_used", False) else 0.3
            
            # 4. 세 값의 곱
            rag_score = defense_rag_weight * rag_affinity * attack_rag_weight
            
            # 5. 임계값 비교 (0.3으로 설정)
            threshold = 0.3
            use_rag = rag_score >= threshold
            
            # 통계 업데이트
            self.rag_usage_stats["defense"]["total"] += 1
            if use_rag:
                self.rag_usage_stats["defense"]["used"] += 1
            
            logger.info(f"[{self.agent_id}] Defense RAG decision: {use_rag} (score: {rag_score:.3f})")
            
            result = {
                "use_rag": use_rag,
                "rag_score": rag_score,
                "threshold": threshold,
                "defense_rag_weight": defense_rag_weight,
                "rag_affinity": rag_affinity,
                "attack_rag_weight": attack_rag_weight,
                "query": "",
                "results": [],
                "results_count": 0
            }
            
            # RAG 사용이 결정되면 검색 수행
            if use_rag and self.rag_search_manager:
                attack_text = attack_info.get("attack_text", "")
                query = self._generate_defense_rag_query(attack_text, defense_strategy)
                search_results = self._perform_defense_rag_search(query, defense_strategy)
                
                result["query"] = query
                result["results"] = search_results
                result["results_count"] = len(search_results)
                
                logger.info(f"[{self.agent_id}] Defense RAG search completed: {len(search_results)} results")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error determining defense RAG usage: {str(e)}")
            return {
                "use_rag": False,
                "rag_score": 0.0,
                "threshold": 0.3,
                "error": str(e),
                "query": "",
                "results": [],
                "results_count": 0
            }
    
    def determine_followup_rag_usage(self, followup_strategy: str, defense_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        팔로우업 전략에 대한 RAG 사용 여부 결정
        
        Args:
            followup_strategy: 팔로우업 전략
            defense_info: 방어 정보
            
        Returns:
            RAG 사용 결정 결과
        """
        logger.info(f"[{self.agent_id}] Determining followup RAG usage for {followup_strategy}")
        
        try:
            # 1. 팔로우업 전략별 RAG 가중치
            followup_rag_weight = self._get_followup_strategy_rag_weight(followup_strategy)
            
            # 2. 철학자 RAG 친화도
            rag_affinity = self.rag_affinity
            
            # 3. 방어의 RAG 사용 여부에 따른 가중치 (방어가 RAG 사용했으면 더 적극적으로 RAG 사용)
            defense_rag_weight = 1.2 if defense_info.get("rag_used", False) else 0.8
            
            # 4. 세 값의 곱
            rag_score = followup_rag_weight * rag_affinity * defense_rag_weight
            
            # 5. 임계값 비교 (0.4로 설정 - 팔로우업은 조금 더 관대하게)
            threshold = 0.4
            use_rag = rag_score >= threshold
            
            # 통계 업데이트
            self.rag_usage_stats["followup"]["total"] += 1
            if use_rag:
                self.rag_usage_stats["followup"]["used"] += 1
            
            logger.info(f"[{self.agent_id}] Followup RAG decision: {use_rag} (score: {rag_score:.3f})")
            
            result = {
                "use_rag": use_rag,
                "rag_score": rag_score,
                "threshold": threshold,
                "followup_rag_weight": followup_rag_weight,
                "rag_affinity": rag_affinity,
                "defense_rag_weight": defense_rag_weight,
                "query": "",
                "results": [],
                "results_count": 0
            }
            
            # RAG 사용이 결정되면 검색 수행
            if use_rag and self.rag_search_manager:
                defense_text = defense_info.get("defense_text", "")
                original_attack = defense_info.get("original_attack", "")
                query = self._generate_followup_rag_query(defense_text, followup_strategy, original_attack)
                search_results = self._perform_followup_rag_search(query, followup_strategy)
                
                result["query"] = query
                result["results"] = search_results
                result["results_count"] = len(search_results)
                
                logger.info(f"[{self.agent_id}] Followup RAG search completed: {len(search_results)} results")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error determining followup RAG usage: {str(e)}")
            return {
                "use_rag": False,
                "rag_score": 0.0,
                "threshold": 0.4,
                "error": str(e),
                "query": "",
                "results": [],
                "results_count": 0
            }
    
    def _get_strategy_rag_weight(self, strategy_type: str) -> float:
        """
        전략별 RAG 가중치 가져오기
        
        Args:
            strategy_type: 전략 유형
            
        Returns:
            RAG 가중치
        """
        strategy_weights = self.strategy_rag_weights.get(strategy_type, {})
        
        # 만약 값이 딕셔너리가 아니라 float이면 그대로 반환
        if isinstance(strategy_weights, (int, float)):
            return float(strategy_weights)
        
        # 값이 딕셔너리면 철학자 RAG 스탯과 내적 계산
        if isinstance(strategy_weights, dict):
            # 철학자 RAG 스탯 가져오기
            philosopher_rag_stats = self.philosopher_data.get("rag_stats", {})
            
            if not philosopher_rag_stats:
                # RAG 스탯이 없으면 기본값 반환
                return 0.5
            
            # 벡터 내적 계산: Σ(strategy_weight[i] × philosopher_rag_stat[i])
            rag_score = 0.0
            stat_names = ["data_respect", "conceptual_precision", "systematic_logic", "pragmatic_orientation", "rhetorical_independence"]
            
            for stat_name in stat_names:
                strategy_weight = strategy_weights.get(stat_name, 0.0)
                philosopher_stat = philosopher_rag_stats.get(stat_name, 0.0)
                rag_score += strategy_weight * philosopher_stat
            
            # 정규화 (0.0 ~ 1.0 범위로)
            return max(0.0, min(1.0, rag_score))
        
        # 기본값
        return 0.5
    
    def _get_defense_strategy_rag_weight(self, defense_strategy: str) -> float:
        """
        방어 전략별 RAG 가중치 가져오기
        
        Args:
            defense_strategy: 방어 전략
            
        Returns:
            RAG 가중치
        """
        # 방어 전략별 기본 가중치
        defense_weights = {
            "Clarify": 0.3,
            "Accept": 0.2,
            "Counter": 0.7,
            "Redirect": 0.5,
            "Strengthen": 0.8,
            "Reframe": 0.6
        }
        return defense_weights.get(defense_strategy, 0.5)
    
    def _get_followup_strategy_rag_weight(self, followup_strategy: str) -> float:
        """
        팔로우업 전략별 RAG 가중치 가져오기
        
        Args:
            followup_strategy: 팔로우업 전략
            
        Returns:
            RAG 가중치
        """
        # 팔로우업 전략별 기본 가중치
        followup_weights = {
            "Reattack": 0.8,
            "FollowUpQuestion": 0.4,
            "Pivot": 0.6,
            "Deepen": 0.7,
            "CounterChallenge": 0.9,
            "SynthesisProposal": 0.5
        }
        return followup_weights.get(followup_strategy, 0.5)
    
    def _calculate_argument_complexity_weight(self, argument: Dict[str, Any]) -> float:
        """
        논지 복잡도에 따른 가중치 계산
        
        Args:
            argument: 논지 정보
            
        Returns:
            복잡도 가중치
        """
        # 논지의 복잡도를 여러 요소로 평가
        complexity_score = 0.5  # 기본값
        
        # 증거의 존재 여부
        if argument.get("evidence"):
            complexity_score += 0.2
        
        # 추론의 복잡성 (길이 기반)
        reasoning = argument.get("reasoning", "")
        if len(reasoning) > 100:
            complexity_score += 0.2
        
        # 가정의 수
        assumptions = argument.get("assumptions", [])
        if len(assumptions) > 2:
            complexity_score += 0.1
        
        return min(complexity_score, 1.0)  # 최대 1.0으로 제한
    
    def _generate_attack_rag_query(self, target_argument: Dict[str, Any], strategy_type: str) -> str:
        """
        공격용 RAG 쿼리 생성
        
        Args:
            target_argument: 공격 대상 논지
            strategy_type: 공격 전략
            
        Returns:
            검색 쿼리
        """
        claim = target_argument.get("claim", "")
        
        # 전략별 쿼리 접두사
        strategy_prefixes = {
            "Clipping": "counterexamples to",
            "Framing Shift": "alternative perspectives on",
            "Reductive Paradox": "logical contradictions in",
            "Conceptual Undermining": "definitions and meanings of",
            "Ethical Reversal": "ethical implications of"
        }
        
        prefix = strategy_prefixes.get(strategy_type, "information about")
        return f"{prefix} {claim}"
    
    def _generate_defense_rag_query(self, attack_text: str, defense_strategy: str) -> str:
        """
        방어용 RAG 쿼리 생성
        
        Args:
            attack_text: 공격 텍스트
            defense_strategy: 방어 전략
            
        Returns:
            검색 쿼리
        """
        # 공격 텍스트에서 핵심 키워드 추출
        keywords = self._extract_key_concepts(attack_text)
        
        # 방어 전략별 접두사
        strategy_prefixes = {
            "Clarify": "clarification of",
            "Accept": "supporting evidence for",
            "Counter": "counterarguments to",
            "Redirect": "related issues about",
            "Strengthen": "additional support for",
            "Reframe": "alternative framing of"
        }
        
        prefix = strategy_prefixes.get(defense_strategy, "information about")
        return f"{prefix} {keywords}"
    
    def _generate_followup_rag_query(self, defense_text: str, followup_strategy: str, original_attack: str) -> str:
        """
        팔로우업용 RAG 쿼리 생성
        
        Args:
            defense_text: 방어 텍스트
            followup_strategy: 팔로우업 전략
            original_attack: 원래 공격
            
        Returns:
            검색 쿼리
        """
        # 방어 텍스트와 원래 공격에서 핵심 키워드 추출
        defense_keywords = self._extract_key_concepts(defense_text)
        attack_keywords = self._extract_key_concepts(original_attack)
        
        # 팔로우업 전략별 접두사
        strategy_prefixes = {
            "Reattack": "additional evidence supporting",
            "FollowUpQuestion": "questions about",
            "Pivot": "related issues concerning",
            "Deepen": "deeper analysis of",
            "CounterChallenge": "challenges to",
            "SynthesisProposal": "synthesis perspectives on"
        }
        
        prefix = strategy_prefixes.get(followup_strategy, "follow up information about")
        combined_keywords = f"{attack_keywords} {defense_keywords}"
        
        return f"{prefix} {combined_keywords}"
    
    def _extract_key_concepts(self, text: str) -> str:
        """
        텍스트에서 핵심 개념 추출
        
        Args:
            text: 입력 텍스트
            
        Returns:
            핵심 개념들
        """
        # 간단한 키워드 추출 (실제로는 더 정교한 NLP 기법 사용 가능)
        words = text.split()
        
        # 불용어 제거 및 중요 단어 필터링
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        important_words = [word for word in words if len(word) > 3 and word.lower() not in stop_words]
        
        # 상위 5개 단어만 사용
        return " ".join(important_words[:5])
    
    def _perform_attack_rag_search(self, query: str, strategy_type: str) -> List[Dict[str, Any]]:
        """
        공격용 RAG 검색 수행
        
        Args:
            query: 검색 쿼리
            strategy_type: 전략 유형
            
        Returns:
            검색 결과
        """
        if not self.rag_search_manager:
            return []
        
        try:
            # 전략에 따라 다른 검색 소스 사용
            if strategy_type in ["Conceptual Undermining", "Ethical Reversal"]:
                # 철학자 검색 우선
                results = self.rag_search_manager.search_philosopher_only(query)
            elif strategy_type in ["Clipping", "Framing Shift"]:
                # 웹 검색 우선
                results = self.rag_search_manager.search_web_only(query)
            else:
                # 벡터 검색 우선
                results = self.rag_search_manager.search_vector_only(query)
            
            return results[:5]  # 최대 5개 결과만 반환
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in attack RAG search: {str(e)}")
            return []
    
    def _perform_defense_rag_search(self, query: str, defense_strategy: str) -> List[Dict[str, Any]]:
        """
        방어용 RAG 검색 수행
        
        Args:
            query: 검색 쿼리
            defense_strategy: 방어 전략
            
        Returns:
            검색 결과
        """
        if not self.rag_search_manager:
            return []
        
        try:
            # 방어 전략에 따라 다른 검색 소스 사용
            if defense_strategy in ["Clarify", "Strengthen"]:
                # 벡터 검색 우선 (정확한 정보)
                results = self.rag_search_manager.search_vector_only(query)
            elif defense_strategy in ["Counter", "Reframe"]:
                # 웹 검색 우선 (다양한 관점)
                results = self.rag_search_manager.search_web_only(query)
            else:
                # 철학자 검색 우선
                results = self.rag_search_manager.search_philosopher_only(query)
            
            return results[:5]  # 최대 5개 결과만 반환
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in defense RAG search: {str(e)}")
            return []
    
    def _perform_followup_rag_search(self, query: str, followup_strategy: str) -> List[Dict[str, Any]]:
        """
        팔로우업용 RAG 검색 수행
        
        Args:
            query: 검색 쿼리
            followup_strategy: 팔로우업 전략
            
        Returns:
            검색 결과
        """
        if not self.rag_search_manager:
            return []
        
        try:
            # 팔로우업 전략에 따라 다른 검색 소스 사용
            if followup_strategy in ["Reattack", "CounterChallenge"]:
                # 웹 검색 우선 (추가 증거)
                results = self.rag_search_manager.search_web_only(query)
            elif followup_strategy in ["Deepen", "SynthesisProposal"]:
                # 철학자 검색 우선 (깊은 통찰)
                results = self.rag_search_manager.search_philosopher_only(query)
            else:
                # 벡터 검색 우선
                results = self.rag_search_manager.search_vector_only(query)
            
            return results[:5]  # 최대 5개 결과만 반환
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in followup RAG search: {str(e)}")
            return []
    
    def get_rag_usage_statistics(self) -> Dict[str, Any]:
        """
        RAG 사용 통계 반환
        
        Returns:
            RAG 사용 통계
        """
        stats = {}
        
        for strategy_type, data in self.rag_usage_stats.items():
            total = data["total"]
            used = data["used"]
            usage_rate = used / total if total > 0 else 0.0
            
            stats[strategy_type] = {
                "total_decisions": total,
                "rag_used": used,
                "usage_rate": usage_rate
            }
        
        # 전체 통계
        total_all = sum(data["total"] for data in self.rag_usage_stats.values())
        used_all = sum(data["used"] for data in self.rag_usage_stats.values())
        overall_rate = used_all / total_all if total_all > 0 else 0.0
        
        stats["overall"] = {
            "total_decisions": total_all,
            "rag_used": used_all,
            "usage_rate": overall_rate,
            "philosopher_rag_affinity": self.rag_affinity
        }
        
        return stats
    
    def reset_statistics(self):
        """RAG 사용 통계 초기화"""
        for strategy_type in self.rag_usage_stats:
            self.rag_usage_stats[strategy_type] = {"total": 0, "used": 0}
        
        logger.info(f"[{self.agent_id}] Reset RAG usage statistics") 