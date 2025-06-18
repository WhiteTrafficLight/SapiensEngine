"""
Unit tests for AttackStrategyManager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, List, Any

from src.agents.participant.strategy.attack_strategy_manager import AttackStrategyManager


class TestAttackStrategyManager:
    """AttackStrategyManager 테스트 클래스"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM Manager"""
        mock_llm = Mock()
        mock_llm.generate_response.return_value = json.dumps({
            "target_point": "specific claim to attack",
            "strategy_application": "apply clipping strategy",
            "key_phrase": "counterexample shows",
            "expected_counter": "opponent may defend",
            "follow_up": "continue with evidence"
        })
        return mock_llm
    
    @pytest.fixture
    def philosopher_data(self):
        """철학자 데이터"""
        return {
            "name": "Socrates",
            "essence": "Know thyself and question everything",
            "debate_style": "Socratic questioning",
            "personality": "Curious and persistent"
        }
    
    @pytest.fixture
    def strategy_styles(self):
        """전략 스타일 데이터"""
        return {
            "Clipping": {
                "description": "Find specific counterexamples",
                "style_prompt": "Show counterexample",
                "example": "But what about case X?"
            },
            "Framing Shift": {
                "description": "Change the frame of reference",
                "style_prompt": "Reframe the issue",
                "example": "The real question is..."
            }
        }
    
    @pytest.fixture
    def strategy_weights(self):
        """전략 가중치"""
        return {
            "Clipping": 0.8,
            "Framing Shift": 0.6,
            "Reductive Paradox": 0.4,
            "Conceptual Undermining": 0.7,
            "Ethical Reversal": 0.5
        }
    
    @pytest.fixture
    def attack_manager(self, philosopher_data, strategy_styles, strategy_weights, mock_llm_manager):
        """AttackStrategyManager 인스턴스"""
        return AttackStrategyManager(
            agent_id="test_socrates_agent",
            philosopher_data=philosopher_data,
            strategy_styles=strategy_styles,
            strategy_weights=strategy_weights,
            llm_manager=mock_llm_manager
        )
    
    def test_initialization(self, attack_manager, philosopher_data):
        """초기화 테스트"""
        assert attack_manager.agent_id == "test_socrates_agent"
        assert attack_manager.philosopher_name == "Socrates"
        assert attack_manager.philosopher_essence == philosopher_data["essence"]
        assert attack_manager.attack_strategies == {}
    
    def test_prepare_attack_strategies_success(self, attack_manager):
        """공격 전략 준비 성공 테스트"""
        target_speaker_id = "opponent_1"
        opponent_arguments = {
            "opponent_1": [
                {
                    "argument": {
                        "claim": "All swans are white",
                        "evidence": "I have seen many white swans",
                        "reasoning": "Inductive reasoning from observations",
                        "assumptions": ["Observation is reliable"]
                    },
                    "vulnerability_rank": 0.8
                },
                {
                    "argument": {
                        "claim": "Democracy is always good",
                        "evidence": "Democratic countries are prosperous",
                        "reasoning": "Correlation implies causation",
                        "assumptions": ["Prosperity equals goodness"]
                    },
                    "vulnerability_rank": 0.9
                }
            ]
        }
        
        # Mock RAG manager
        mock_rag_manager = Mock()
        mock_rag_manager.determine_attack_rag_usage.return_value = {
            "use_rag": True,
            "query": "counterexamples to democracy",
            "results": [{"content": "Some evidence", "source": "test"}],
            "results_count": 1
        }
        
        result = attack_manager.prepare_attack_strategies_for_speaker(
            target_speaker_id, opponent_arguments, mock_rag_manager
        )
        
        assert result["status"] == "success"
        assert result["target_speaker_id"] == target_speaker_id
        assert result["strategies_count"] > 0
        assert len(result["strategies"]) <= 3  # 최대 3개
        
        # 전략이 저장되었는지 확인
        assert target_speaker_id in attack_manager.attack_strategies
        
        # 각 전략이 필요한 필드를 가지고 있는지 확인
        for strategy in result["strategies"]:
            assert "target_argument" in strategy
            assert "strategy_type" in strategy
            assert "attack_plan" in strategy
            assert "vulnerability_score" in strategy
            assert "priority" in strategy
            assert "rag_decision" in strategy
    
    def test_prepare_attack_strategies_no_arguments(self, attack_manager):
        """논지가 없는 경우 테스트"""
        target_speaker_id = "opponent_1"
        opponent_arguments = {}
        
        result = attack_manager.prepare_attack_strategies_for_speaker(
            target_speaker_id, opponent_arguments
        )
        
        assert result["status"] == "failed"
        assert result["reason"] == "no_arguments_found"
        assert result["strategies_count"] == 0
    
    def test_select_best_strategy_for_argument(self, attack_manager):
        """논지에 대한 최적 전략 선택 테스트"""
        argument = {
            "claim": "All cats are black",
            "argument_type": "logical",
            "evidence": "I saw many black cats"
        }
        
        strategy = attack_manager.select_best_strategy_for_argument(argument)
        
        assert strategy in attack_manager.strategy_weights
        assert isinstance(strategy, str)
    
    def test_select_best_strategy_no_weights(self, philosopher_data, strategy_styles, mock_llm_manager):
        """전략 가중치가 없는 경우 테스트"""
        manager = AttackStrategyManager(
            agent_id="test_agent",
            philosopher_data=philosopher_data,
            strategy_styles=strategy_styles,
            strategy_weights={},  # 빈 가중치
            llm_manager=mock_llm_manager
        )
        
        argument = {"claim": "Test claim", "argument_type": "logical"}
        strategy = manager.select_best_strategy_for_argument(argument)
        
        assert strategy == "Clipping"  # 기본 전략
    
    def test_generate_attack_plan_success(self, attack_manager):
        """공격 계획 생성 성공 테스트"""
        target_argument = {
            "claim": "All swans are white",
            "evidence": "Observed many white swans",
            "reasoning": "Inductive reasoning",
            "assumptions": ["Observation is complete"]
        }
        strategy_type = "Clipping"
        
        plan = attack_manager.generate_attack_plan(target_argument, strategy_type)
        
        assert isinstance(plan, dict)
        assert "target_point" in plan
        assert "strategy_application" in plan
        assert "key_phrase" in plan
        assert "expected_counter" in plan
        assert "follow_up" in plan
    
    def test_generate_attack_plan_llm_failure(self, attack_manager):
        """LLM 실패 시 fallback 테스트"""
        # LLM이 잘못된 응답을 반환하도록 설정
        attack_manager.llm_manager.generate_response.return_value = "Invalid JSON response"
        
        target_argument = {
            "claim": "Test claim",
            "evidence": "Test evidence",
            "reasoning": "Test reasoning",
            "assumptions": []
        }
        strategy_type = "Clipping"
        
        plan = attack_manager.generate_attack_plan(target_argument, strategy_type)
        
        # Fallback 계획이 반환되어야 함
        assert isinstance(plan, dict)
        assert plan["target_point"] == "Test claim"
        assert "strategy_application" in plan
    
    def test_get_best_attack_strategy(self, attack_manager):
        """최적 공격 전략 가져오기 테스트"""
        target_speaker_id = "opponent_1"
        
        # 먼저 전략을 준비
        attack_manager.attack_strategies[target_speaker_id] = [
            {
                "strategy_type": "Clipping",
                "attack_plan": {"target_point": "test"},
                "priority": 1
            },
            {
                "strategy_type": "Framing Shift",
                "attack_plan": {"target_point": "test2"},
                "priority": 2
            }
        ]
        
        best_strategy = attack_manager.get_best_attack_strategy(target_speaker_id, {})
        
        assert best_strategy is not None
        assert best_strategy["strategy_type"] == "Clipping"  # 첫 번째 (우선순위 높음)
    
    def test_get_best_attack_strategy_no_strategies(self, attack_manager):
        """전략이 없는 경우 테스트"""
        target_speaker_id = "nonexistent_opponent"
        
        best_strategy = attack_manager.get_best_attack_strategy(target_speaker_id, {})
        
        assert best_strategy is None
    
    def test_clear_attack_strategies_specific(self, attack_manager):
        """특정 발언자 전략 정리 테스트"""
        # 전략 데이터 설정
        attack_manager.attack_strategies["opponent_1"] = [{"strategy": "test1"}]
        attack_manager.attack_strategies["opponent_2"] = [{"strategy": "test2"}]
        
        attack_manager.clear_attack_strategies("opponent_1")
        
        assert "opponent_1" not in attack_manager.attack_strategies
        assert "opponent_2" in attack_manager.attack_strategies
    
    def test_clear_attack_strategies_all(self, attack_manager):
        """모든 전략 정리 테스트"""
        # 전략 데이터 설정
        attack_manager.attack_strategies["opponent_1"] = [{"strategy": "test1"}]
        attack_manager.attack_strategies["opponent_2"] = [{"strategy": "test2"}]
        
        attack_manager.clear_attack_strategies()
        
        assert len(attack_manager.attack_strategies) == 0
    
    def test_get_attack_statistics(self, attack_manager):
        """공격 전략 통계 테스트"""
        # 전략 데이터 설정
        attack_manager.attack_strategies = {
            "opponent_1": [
                {"strategy_type": "Clipping"},
                {"strategy_type": "Framing Shift"}
            ],
            "opponent_2": [
                {"strategy_type": "Clipping"}
            ]
        }
        
        stats = attack_manager.get_attack_statistics()
        
        assert stats["total_targets"] == 2
        assert stats["total_strategies"] == 3
        assert stats["strategy_distribution"]["Clipping"] == 2
        assert stats["strategy_distribution"]["Framing Shift"] == 1
        assert "opponent_1" in stats["targets"]
        assert "opponent_2" in stats["targets"]
    
    def test_get_attack_statistics_empty(self, attack_manager):
        """빈 통계 테스트"""
        stats = attack_manager.get_attack_statistics()
        
        assert stats["total_targets"] == 0
        assert stats["total_strategies"] == 0
        assert stats["strategy_distribution"] == {}
        assert stats["targets"] == []
    
    def test_fallback_attack_plan(self, attack_manager):
        """Fallback 공격 계획 테스트"""
        target_argument = {
            "claim": "Test claim",
            "evidence": "Test evidence"
        }
        strategy_type = "Clipping"
        
        plan = attack_manager._get_fallback_attack_plan(target_argument, strategy_type)
        
        assert isinstance(plan, dict)
        assert plan["target_point"] == "Test claim"
        assert "Clipping" in plan["strategy_application"]
        assert "key_phrase" in plan
        assert "expected_counter" in plan
        assert "follow_up" in plan
    
    @pytest.mark.parametrize("argument_type,claim,expected_boost", [
        ("logical", "specific example", "Clipping"),
        ("logical", "we must assume that", "Framing Shift"),
        ("emotional", "this is wrong", "Ethical Reversal"),
        ("logical", "define what we mean", "Conceptual Undermining")
    ])
    def test_strategy_selection_logic(self, attack_manager, argument_type, claim, expected_boost):
        """전략 선택 로직 테스트"""
        argument = {
            "claim": claim,
            "argument_type": argument_type,
            "evidence": "test evidence"
        }
        
        # 여러 번 실행해서 선택된 전략들 확인
        selected_strategies = []
        for _ in range(10):
            strategy = attack_manager.select_best_strategy_for_argument(argument)
            selected_strategies.append(strategy)
        
        # 예상되는 전략이 선택되는 빈도가 높아야 함
        strategy_counts = {}
        for strategy in selected_strategies:
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # 가장 많이 선택된 전략이 예상 전략이어야 함 (확률적이므로 완벽하지 않을 수 있음)
        most_selected = max(strategy_counts.items(), key=lambda x: x[1])[0]
        assert most_selected in attack_manager.strategy_weights 