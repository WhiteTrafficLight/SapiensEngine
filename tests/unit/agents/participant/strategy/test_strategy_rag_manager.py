"""
Unit tests for StrategyRAGManager.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from src.agents.participant.strategy.strategy_rag_manager import StrategyRAGManager


class TestStrategyRAGManager:
    """StrategyRAGManager 테스트 클래스"""
    
    @pytest.fixture
    def philosopher_data(self):
        """철학자 데이터"""
        return {
            "name": "Kant",
            "essence": "Act only according to maxims you could will to be universal laws",
            "debate_style": "Systematic moral reasoning",
            "personality": "Rigorous and principled",
            "rag_affinity": 0.7
        }
    
    @pytest.fixture
    def strategy_rag_weights(self):
        """전략별 RAG 가중치"""
        return {
            "Clipping": 0.8,
            "Framing Shift": 0.6,
            "Reductive Paradox": 0.9,
            "Conceptual Undermining": 0.7,
            "Ethical Reversal": 0.5
        }
    
    @pytest.fixture
    def mock_rag_search_manager(self):
        """Mock RAG Search Manager"""
        mock_manager = Mock()
        mock_manager.search_philosopher_only.return_value = [
            {"content": "Kant's categorical imperative", "source": "Critique of Practical Reason"},
            {"content": "Moral duty and obligation", "source": "Groundwork"}
        ]
        mock_manager.search_web_only.return_value = [
            {"content": "Modern ethical debates", "source": "Philosophy Today"},
            {"content": "Contemporary moral issues", "source": "Ethics Journal"}
        ]
        mock_manager.search_vector_only.return_value = [
            {"content": "Deontological ethics", "source": "User Context"},
            {"content": "Moral reasoning principles", "source": "Document"}
        ]
        return mock_manager
    
    @pytest.fixture
    def rag_manager(self, philosopher_data, strategy_rag_weights, mock_rag_search_manager):
        """StrategyRAGManager 인스턴스"""
        return StrategyRAGManager(
            agent_id="test_kant_agent",
            philosopher_data=philosopher_data,
            strategy_rag_weights=strategy_rag_weights,
            rag_search_manager=mock_rag_search_manager
        )
    
    def test_initialization(self, rag_manager, philosopher_data, strategy_rag_weights):
        """초기화 테스트"""
        assert rag_manager.agent_id == "test_kant_agent"
        assert rag_manager.philosopher_data == philosopher_data
        assert rag_manager.strategy_rag_weights == strategy_rag_weights
        assert rag_manager.rag_affinity == 0.7
        
        # 통계 초기화 확인
        for strategy_type in ["attack", "defense", "followup"]:
            assert rag_manager.rag_usage_stats[strategy_type]["total"] == 0
            assert rag_manager.rag_usage_stats[strategy_type]["used"] == 0
    
    def test_determine_attack_rag_usage_high_score(self, rag_manager):
        """공격 RAG 사용 결정 - 높은 점수 테스트"""
        strategy_type = "Reductive Paradox"  # 높은 가중치 (0.9)
        target_argument = {
            "claim": "All moral actions must be based on consequences",
            "evidence": "Utilitarian theory provides comprehensive framework",
            "reasoning": "Complex philosophical reasoning with multiple assumptions",
            "assumptions": ["Consequences can be measured", "Happiness is the ultimate good", "Actions have predictable outcomes"]
        }
        
        result = rag_manager.determine_attack_rag_usage(strategy_type, target_argument)
        
        assert result["use_rag"] is True
        assert result["rag_score"] > 0.3  # 임계값보다 높음
        assert result["strategy_rag_weight"] == 0.9
        assert result["rag_affinity"] == 0.7
        assert "argument_complexity_weight" in result
        assert len(result["results"]) > 0  # RAG 검색 결과 있음
        assert result["results_count"] > 0
    
    def test_determine_attack_rag_usage_low_score(self, rag_manager):
        """공격 RAG 사용 결정 - 낮은 점수 테스트"""
        strategy_type = "Ethical Reversal"  # 낮은 가중치 (0.5)
        target_argument = {
            "claim": "Simple claim",
            "evidence": "",  # 증거 없음
            "reasoning": "Short",  # 짧은 추론
            "assumptions": []  # 가정 없음
        }
        
        result = rag_manager.determine_attack_rag_usage(strategy_type, target_argument)
        
        # 낮은 점수로 인해 RAG 사용하지 않을 가능성 높음
        assert result["rag_score"] < 0.5
        assert result["strategy_rag_weight"] == 0.5
        assert result["rag_affinity"] == 0.7
        assert result["argument_complexity_weight"] <= 0.7  # 복잡도 낮음
    
    def test_determine_defense_rag_usage_success(self, rag_manager):
        """방어 RAG 사용 결정 성공 테스트"""
        defense_strategy = "Counter"
        attack_info = {
            "attack_strategy": "Clipping",
            "rag_used": True,
            "attack_text": "Your position fails because of this counterexample"
        }
        
        result = rag_manager.determine_defense_rag_usage(defense_strategy, attack_info)
        
        assert "use_rag" in result
        assert "rag_score" in result
        assert result["defense_rag_weight"] == 0.7  # Counter 전략의 가중치
        assert result["rag_affinity"] == 0.7
        assert result["attack_rag_weight"] == 1.0  # 공격이 RAG 사용했으므로
        
        if result["use_rag"]:
            assert len(result["results"]) > 0
            assert result["results_count"] > 0
    
    def test_determine_defense_rag_usage_no_attack_rag(self, rag_manager):
        """공격이 RAG를 사용하지 않은 경우 방어 RAG 사용 결정 테스트"""
        defense_strategy = "Clarify"
        attack_info = {
            "attack_strategy": "Simple Attack",
            "rag_used": False,
            "attack_text": "You are wrong"
        }
        
        result = rag_manager.determine_defense_rag_usage(defense_strategy, attack_info)
        
        assert result["defense_rag_weight"] == 0.3  # Clarify 전략의 가중치
        assert result["attack_rag_weight"] == 0.3  # 공격이 RAG 사용하지 않았으므로
        
        # 낮은 점수로 인해 RAG 사용하지 않을 가능성 높음
        expected_score = 0.3 * 0.7 * 0.3  # defense_weight * rag_affinity * attack_weight
        assert abs(result["rag_score"] - expected_score) < 0.01
    
    def test_determine_followup_rag_usage_success(self, rag_manager):
        """팔로우업 RAG 사용 결정 성공 테스트"""
        followup_strategy = "CounterChallenge"
        defense_info = {
            "defense_strategy": "Counter",
            "rag_used": True,
            "defense_text": "I counter your argument with this evidence",
            "original_attack": "Your position is flawed"
        }
        
        result = rag_manager.determine_followup_rag_usage(followup_strategy, defense_info)
        
        assert "use_rag" in result
        assert result["followup_rag_weight"] == 0.9  # CounterChallenge 전략의 가중치
        assert result["rag_affinity"] == 0.7
        assert result["defense_rag_weight"] == 1.2  # 방어가 RAG 사용했으므로
        assert result["threshold"] == 0.4  # 팔로우업 임계값
        
        if result["use_rag"]:
            assert len(result["results"]) > 0
            assert result["results_count"] > 0
    
    def test_get_strategy_rag_weight(self, rag_manager):
        """전략별 RAG 가중치 가져오기 테스트"""
        assert rag_manager._get_strategy_rag_weight("Clipping") == 0.8
        assert rag_manager._get_strategy_rag_weight("Framing Shift") == 0.6
        assert rag_manager._get_strategy_rag_weight("Unknown Strategy") == 0.5  # 기본값
    
    def test_get_defense_strategy_rag_weight(self, rag_manager):
        """방어 전략별 RAG 가중치 가져오기 테스트"""
        assert rag_manager._get_defense_strategy_rag_weight("Counter") == 0.7
        assert rag_manager._get_defense_strategy_rag_weight("Strengthen") == 0.8
        assert rag_manager._get_defense_strategy_rag_weight("Accept") == 0.2
        assert rag_manager._get_defense_strategy_rag_weight("Unknown") == 0.5  # 기본값
    
    def test_get_followup_strategy_rag_weight(self, rag_manager):
        """팔로우업 전략별 RAG 가중치 가져오기 테스트"""
        assert rag_manager._get_followup_strategy_rag_weight("CounterChallenge") == 0.9
        assert rag_manager._get_followup_strategy_rag_weight("Reattack") == 0.8
        assert rag_manager._get_followup_strategy_rag_weight("FollowUpQuestion") == 0.4
        assert rag_manager._get_followup_strategy_rag_weight("Unknown") == 0.5  # 기본값
    
    def test_calculate_argument_complexity_weight(self, rag_manager):
        """논지 복잡도 가중치 계산 테스트"""
        # 복잡한 논지
        complex_argument = {
            "claim": "Complex philosophical claim",
            "evidence": "Extensive evidence with multiple sources",
            "reasoning": "Very long and detailed reasoning that explains the philosophical position with multiple steps and considerations that demonstrate the complexity of the argument",
            "assumptions": ["Assumption 1", "Assumption 2", "Assumption 3", "Assumption 4"]
        }
        
        complex_weight = rag_manager._calculate_argument_complexity_weight(complex_argument)
        assert complex_weight > 0.7  # 높은 복잡도
        
        # 단순한 논지
        simple_argument = {
            "claim": "Simple claim",
            "evidence": "",
            "reasoning": "Short",
            "assumptions": []
        }
        
        simple_weight = rag_manager._calculate_argument_complexity_weight(simple_argument)
        assert simple_weight == 0.5  # 기본값
    
    def test_generate_attack_rag_query(self, rag_manager):
        """공격용 RAG 쿼리 생성 테스트"""
        target_argument = {
            "claim": "Democracy is the best form of government"
        }
        
        test_cases = [
            ("Clipping", "counterexamples to Democracy is the best form of government"),
            ("Framing Shift", "alternative perspectives on Democracy is the best form of government"),
            ("Conceptual Undermining", "definitions and meanings of Democracy is the best form of government"),
            ("Unknown Strategy", "information about Democracy is the best form of government")
        ]
        
        for strategy_type, expected_prefix in test_cases:
            query = rag_manager._generate_attack_rag_query(target_argument, strategy_type)
            assert expected_prefix in query
    
    def test_generate_defense_rag_query(self, rag_manager):
        """방어용 RAG 쿼리 생성 테스트"""
        attack_text = "Your democratic ideals are flawed because they lead to mob rule"
        
        test_cases = [
            ("Counter", "counterarguments to"),
            ("Clarify", "clarification of"),
            ("Strengthen", "additional support for"),
            ("Unknown", "information about")
        ]
        
        for defense_strategy, expected_prefix in test_cases:
            query = rag_manager._generate_defense_rag_query(attack_text, defense_strategy)
            assert expected_prefix in query
    
    def test_generate_followup_rag_query(self, rag_manager):
        """팔로우업용 RAG 쿼리 생성 테스트"""
        defense_text = "I clarify that democracy has safeguards against mob rule"
        original_attack = "Democracy leads to mob rule"
        
        test_cases = [
            ("Reattack", "additional evidence supporting"),
            ("FollowUpQuestion", "questions about"),
            ("Deepen", "deeper analysis of"),
            ("Unknown", "follow up information about")
        ]
        
        for followup_strategy, expected_prefix in test_cases:
            query = rag_manager._generate_followup_rag_query(
                defense_text, followup_strategy, original_attack
            )
            assert expected_prefix in query
    
    def test_extract_key_concepts(self, rag_manager):
        """핵심 개념 추출 테스트"""
        text = "Democracy is the best form of government because it represents the will of the people"
        
        concepts = rag_manager._extract_key_concepts(text)
        
        # 불용어가 제거되고 중요한 단어들만 남아야 함
        assert "the" not in concepts
        assert "is" not in concepts
        assert "Democracy" in concepts or "democracy" in concepts
        assert len(concepts.split()) <= 5  # 최대 5개 단어
    
    def test_perform_attack_rag_search_different_strategies(self, rag_manager, mock_rag_search_manager):
        """다양한 공격 전략에 따른 RAG 검색 테스트"""
        query = "test query"
        
        # Conceptual Undermining - 철학자 검색 우선
        results = rag_manager._perform_attack_rag_search(query, "Conceptual Undermining")
        mock_rag_search_manager.search_philosopher_only.assert_called_with(query)
        assert len(results) <= 5
        
        # Clipping - 웹 검색 우선
        results = rag_manager._perform_attack_rag_search(query, "Clipping")
        mock_rag_search_manager.search_web_only.assert_called_with(query)
        assert len(results) <= 5
        
        # 기타 전략 - 벡터 검색 우선
        results = rag_manager._perform_attack_rag_search(query, "Other Strategy")
        mock_rag_search_manager.search_vector_only.assert_called_with(query)
        assert len(results) <= 5
    
    def test_perform_defense_rag_search_different_strategies(self, rag_manager, mock_rag_search_manager):
        """다양한 방어 전략에 따른 RAG 검색 테스트"""
        query = "test query"
        
        # Clarify - 벡터 검색 우선
        results = rag_manager._perform_defense_rag_search(query, "Clarify")
        mock_rag_search_manager.search_vector_only.assert_called_with(query)
        assert len(results) <= 5
        
        # Counter - 웹 검색 우선
        results = rag_manager._perform_defense_rag_search(query, "Counter")
        mock_rag_search_manager.search_web_only.assert_called_with(query)
        assert len(results) <= 5
        
        # 기타 전략 - 철학자 검색 우선
        results = rag_manager._perform_defense_rag_search(query, "Other Strategy")
        mock_rag_search_manager.search_philosopher_only.assert_called_with(query)
        assert len(results) <= 5
    
    def test_perform_followup_rag_search_different_strategies(self, rag_manager, mock_rag_search_manager):
        """다양한 팔로우업 전략에 따른 RAG 검색 테스트"""
        query = "test query"
        
        # Reattack - 웹 검색 우선
        results = rag_manager._perform_followup_rag_search(query, "Reattack")
        mock_rag_search_manager.search_web_only.assert_called_with(query)
        assert len(results) <= 5
        
        # Deepen - 철학자 검색 우선
        results = rag_manager._perform_followup_rag_search(query, "Deepen")
        mock_rag_search_manager.search_philosopher_only.assert_called_with(query)
        assert len(results) <= 5
        
        # 기타 전략 - 벡터 검색 우선
        results = rag_manager._perform_followup_rag_search(query, "Other Strategy")
        mock_rag_search_manager.search_vector_only.assert_called_with(query)
        assert len(results) <= 5
    
    def test_rag_search_error_handling(self, rag_manager, mock_rag_search_manager):
        """RAG 검색 오류 처리 테스트"""
        # 검색 매니저가 예외를 발생시키도록 설정
        mock_rag_search_manager.search_vector_only.side_effect = Exception("Search Error")
        
        results = rag_manager._perform_attack_rag_search("test query", "Other Strategy")
        
        assert results == []  # 오류 시 빈 리스트 반환
    
    def test_no_rag_search_manager(self, philosopher_data, strategy_rag_weights):
        """RAG 검색 매니저가 없는 경우 테스트"""
        manager = StrategyRAGManager(
            agent_id="test_agent",
            philosopher_data=philosopher_data,
            strategy_rag_weights=strategy_rag_weights,
            rag_search_manager=None  # None으로 설정
        )
        
        target_argument = {"claim": "Test claim"}
        result = manager.determine_attack_rag_usage("Clipping", target_argument)
        
        # RAG 사용 결정은 되지만 검색 결과는 없어야 함
        assert "use_rag" in result
        assert result["results"] == []
        assert result["results_count"] == 0
    
    def test_get_rag_usage_statistics_empty(self, rag_manager):
        """빈 RAG 사용 통계 테스트"""
        stats = rag_manager.get_rag_usage_statistics()
        
        for strategy_type in ["attack", "defense", "followup"]:
            assert stats[strategy_type]["total_decisions"] == 0
            assert stats[strategy_type]["rag_used"] == 0
            assert stats[strategy_type]["usage_rate"] == 0.0
        
        assert stats["overall"]["total_decisions"] == 0
        assert stats["overall"]["rag_used"] == 0
        assert stats["overall"]["usage_rate"] == 0.0
        assert stats["overall"]["philosopher_rag_affinity"] == 0.7
    
    def test_get_rag_usage_statistics_with_data(self, rag_manager):
        """데이터가 있는 RAG 사용 통계 테스트"""
        # 여러 RAG 사용 결정 시뮬레이션
        target_argument = {"claim": "Test", "evidence": "Evidence", "reasoning": "Long reasoning", "assumptions": ["A1", "A2"]}
        
        # 공격 RAG 사용 결정 (여러 번)
        for _ in range(5):
            rag_manager.determine_attack_rag_usage("Reductive Paradox", target_argument)  # 높은 가중치
        
        for _ in range(3):
            rag_manager.determine_attack_rag_usage("Ethical Reversal", {"claim": "Simple"})  # 낮은 가중치
        
        # 방어 RAG 사용 결정
        for _ in range(4):
            rag_manager.determine_defense_rag_usage("Counter", {"rag_used": True})
        
        stats = rag_manager.get_rag_usage_statistics()
        
        assert stats["attack"]["total_decisions"] == 8
        assert stats["defense"]["total_decisions"] == 4
        assert stats["followup"]["total_decisions"] == 0
        assert stats["overall"]["total_decisions"] == 12
        
        # 사용률은 전략과 복잡도에 따라 달라짐
        assert 0 <= stats["attack"]["usage_rate"] <= 1
        assert 0 <= stats["defense"]["usage_rate"] <= 1
        assert 0 <= stats["overall"]["usage_rate"] <= 1
    
    def test_reset_statistics(self, rag_manager):
        """통계 초기화 테스트"""
        # 일부 데이터 생성
        target_argument = {"claim": "Test"}
        rag_manager.determine_attack_rag_usage("Clipping", target_argument)
        
        # 통계에 데이터가 있는지 확인
        stats_before = rag_manager.get_rag_usage_statistics()
        assert stats_before["attack"]["total_decisions"] > 0
        
        # 초기화
        rag_manager.reset_statistics()
        
        # 초기화 후 확인
        stats_after = rag_manager.get_rag_usage_statistics()
        assert stats_after["attack"]["total_decisions"] == 0
        assert stats_after["defense"]["total_decisions"] == 0
        assert stats_after["followup"]["total_decisions"] == 0
    
    @pytest.mark.parametrize("rag_affinity,strategy_weight,complexity,expected_range", [
        (0.9, 0.9, 0.9, (0.5, 1.0)),  # 모두 높음 - RAG 사용 가능성 높음
        (0.1, 0.1, 0.1, (0.0, 0.2)),  # 모두 낮음 - RAG 사용 가능성 낮음
        (0.5, 0.8, 0.6, (0.2, 0.5)),  # 중간값들
        (0.0, 1.0, 1.0, (0.0, 0.1))   # RAG 친화도 0 - RAG 사용 안함
    ])
    def test_rag_score_calculation_ranges(self, philosopher_data, strategy_rag_weights, 
                                        rag_affinity, strategy_weight, complexity, expected_range):
        """RAG 점수 계산 범위 테스트"""
        # 철학자 RAG 친화도 설정
        philosopher_data["rag_affinity"] = rag_affinity
        
        manager = StrategyRAGManager(
            agent_id="test_agent",
            philosopher_data=philosopher_data,
            strategy_rag_weights={"TestStrategy": strategy_weight},
            rag_search_manager=None
        )
        
        # 복잡도에 맞는 논지 생성
        if complexity > 0.7:
            argument = {
                "claim": "Complex claim",
                "evidence": "Detailed evidence",
                "reasoning": "Very long reasoning with multiple steps and considerations",
                "assumptions": ["A1", "A2", "A3", "A4"]
            }
        elif complexity > 0.5:
            argument = {
                "claim": "Medium claim",
                "evidence": "Some evidence",
                "reasoning": "Medium length reasoning",
                "assumptions": ["A1", "A2"]
            }
        else:
            argument = {
                "claim": "Simple claim",
                "evidence": "",
                "reasoning": "Short",
                "assumptions": []
            }
        
        result = manager.determine_attack_rag_usage("TestStrategy", argument)
        
        assert expected_range[0] <= result["rag_score"] <= expected_range[1] 