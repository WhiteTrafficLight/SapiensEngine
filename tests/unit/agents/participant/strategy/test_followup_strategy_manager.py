"""
Unit tests for FollowupStrategyManager.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import yaml
from datetime import datetime
from typing import Dict, List, Any

from src.agents.participant.strategy.followup_strategy_manager import FollowupStrategyManager


class TestFollowupStrategyManager:
    """FollowupStrategyManager 테스트 클래스"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM Manager"""
        mock_llm = Mock()
        mock_llm.generate_response.return_value = "Let me follow up on that point with a question."
        return mock_llm
    
    @pytest.fixture
    def philosopher_data(self):
        """철학자 데이터"""
        return {
            "name": "Aristotle",
            "essence": "Seek the golden mean through systematic inquiry",
            "debate_style": "Systematic analysis",
            "personality": "Methodical and comprehensive",
            "followup_weights": {
                "Reattack": 0.6,
                "FollowUpQuestion": 0.8,
                "Pivot": 0.4,
                "Deepen": 0.7,
                "CounterChallenge": 0.5,
                "SynthesisProposal": 0.3
            }
        }
    
    @pytest.fixture
    def strategy_styles(self):
        """전략 스타일 데이터"""
        return {
            "followup_strategies": {
                "FollowUpQuestion": {
                    "description": "Ask a probing question",
                    "purpose": "Deepen the discussion",
                    "style_prompt": "But what about...",
                    "example": "That raises an interesting question..."
                },
                "Reattack": {
                    "description": "Launch a new attack",
                    "purpose": "Continue the offensive",
                    "style_prompt": "Furthermore...",
                    "example": "Moreover, consider this..."
                }
            }
        }
    
    @pytest.fixture
    def mock_followup_map(self):
        """Mock followup_map.yaml 데이터"""
        return {
            "Counter": {
                "RAG_YES": {
                    "neutral": ["FollowUpQuestion", "Deepen"],
                    "confident": ["Reattack", "CounterChallenge"],
                    "defensive": ["Pivot", "SynthesisProposal"]
                },
                "RAG_NO": {
                    "neutral": ["FollowUpQuestion", "Pivot"],
                    "confident": ["Reattack"],
                    "defensive": ["SynthesisProposal"]
                }
            },
            "Clarify": {
                "RAG_YES": {
                    "neutral": ["Deepen", "FollowUpQuestion"],
                    "confident": ["CounterChallenge", "Reattack"],
                    "defensive": ["Pivot"]
                },
                "RAG_NO": {
                    "neutral": ["FollowUpQuestion"],
                    "confident": ["Reattack"],
                    "defensive": ["Pivot"]
                }
            }
        }
    
    @pytest.fixture
    def followup_manager(self, philosopher_data, strategy_styles, mock_llm_manager):
        """FollowupStrategyManager 인스턴스"""
        return FollowupStrategyManager(
            agent_id="test_aristotle_agent",
            philosopher_data=philosopher_data,
            strategy_styles=strategy_styles,
            llm_manager=mock_llm_manager
        )
    
    def test_initialization(self, followup_manager, philosopher_data):
        """초기화 테스트"""
        assert followup_manager.agent_id == "test_aristotle_agent"
        assert followup_manager.philosopher_name == "Aristotle"
        assert followup_manager.philosopher_essence == philosopher_data["essence"]
        assert followup_manager.followup_strategies == []
        assert followup_manager.last_followup_strategy is None
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('os.path.exists')
    def test_select_followup_strategy_success(self, mock_exists, mock_yaml_load, mock_file,
                                            followup_manager, mock_followup_map):
        """팔로우업 전략 선택 성공 테스트"""
        # Mock 설정
        mock_exists.return_value = True
        mock_yaml_load.return_value = mock_followup_map
        
        defense_info = {
            "defense_strategy": "Counter",
            "rag_used": True
        }
        emotion_enhancement = {
            "emotion_type": "neutral"
        }
        
        strategy = followup_manager.select_followup_strategy(defense_info, emotion_enhancement)
        
        assert strategy in ["FollowUpQuestion", "Deepen"]  # mock_followup_map에서 예상되는 값
        assert isinstance(strategy, str)
    
    @patch('os.path.exists')
    def test_select_followup_strategy_no_map_file(self, mock_exists, followup_manager):
        """followup_map.yaml 파일이 없는 경우 테스트"""
        mock_exists.return_value = False
        
        defense_info = {
            "defense_strategy": "Unknown",
            "rag_used": False
        }
        
        strategy = followup_manager.select_followup_strategy(defense_info)
        
        assert strategy in ["FollowUpQuestion", "Pivot"]  # 기본값
    
    def test_select_followup_strategy_no_weights(self, strategy_styles, mock_llm_manager):
        """followup_weights가 없는 철학자 테스트"""
        philosopher_data_no_weights = {
            "name": "TestPhilosopher",
            "essence": "Test essence",
            "debate_style": "Test style",
            "personality": "Test personality"
            # followup_weights 없음
        }
        
        manager = FollowupStrategyManager(
            agent_id="test_agent",
            philosopher_data=philosopher_data_no_weights,
            strategy_styles=strategy_styles,
            llm_manager=mock_llm_manager
        )
        
        defense_info = {"defense_strategy": "Unknown", "rag_used": False}
        strategy = manager.select_followup_strategy(defense_info)
        
        assert strategy in ["FollowUpQuestion", "Pivot"]  # 기본값 또는 첫 번째 후보
    
    def test_generate_followup_response_success(self, followup_manager):
        """팔로우업 응답 생성 성공 테스트"""
        topic = "What is the nature of justice?"
        recent_messages = [
            {
                "speaker_id": "opponent_plato",
                "text": "Justice is harmony in the soul, as I have explained."
            }
        ]
        stance_statements = {
            "aristotle": "Justice is giving each their due according to merit"
        }
        followup_strategy = "FollowUpQuestion"
        followup_rag_decision = {
            "use_rag": False,
            "results": []
        }
        
        response = followup_manager.generate_followup_response(
            topic, recent_messages, stance_statements, followup_strategy, followup_rag_decision
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert followup_manager.last_followup_strategy is not None
        assert len(followup_manager.followup_strategies) == 1
    
    def test_generate_followup_response_with_rag(self, followup_manager):
        """RAG를 사용한 팔로우업 응답 생성 테스트"""
        topic = "What is the nature of justice?"
        recent_messages = [
            {
                "speaker_id": "opponent_plato",
                "text": "Justice is harmony in the soul."
            }
        ]
        stance_statements = {"aristotle": "Justice is merit-based"}
        followup_strategy = "Deepen"
        followup_rag_decision = {
            "use_rag": True,
            "results": [
                {
                    "content": "Aristotle's concept of distributive justice",
                    "source": "Nicomachean Ethics"
                },
                {
                    "content": "Merit-based allocation principles",
                    "source": "Political Philosophy"
                }
            ]
        }
        
        response = followup_manager.generate_followup_response(
            topic, recent_messages, stance_statements, followup_strategy, followup_rag_decision
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_generate_followup_response_llm_error(self, followup_manager):
        """LLM 오류 시 fallback 테스트"""
        # LLM이 예외를 발생시키도록 설정
        followup_manager.llm_manager.generate_response.side_effect = Exception("LLM Error")
        
        topic = "Test topic"
        recent_messages = [{"speaker_id": "opponent", "text": "Test defense"}]
        stance_statements = {"aristotle": "Test stance"}
        followup_strategy = "FollowUpQuestion"
        followup_rag_decision = {"use_rag": False, "results": []}
        
        response = followup_manager.generate_followup_response(
            topic, recent_messages, stance_statements, followup_strategy, followup_rag_decision
        )
        
        assert isinstance(response, str)
        assert "reconsider" in response.lower()  # fallback 메시지 확인
    
    def test_analyze_defense_response_success(self, followup_manager):
        """방어 응답 분석 성공 테스트"""
        recent_messages = [
            {
                "speaker_id": "opponent_plato",
                "text": "Let me clarify what I meant by justice as harmony."
            }
        ]
        
        analysis = followup_manager.analyze_defense_response(recent_messages)
        
        assert analysis["defender_id"] == "opponent_plato"
        assert "defense_strategy" in analysis
        assert "rag_used" in analysis
        assert "defense_text" in analysis
    
    def test_analyze_defense_response_empty_messages(self, followup_manager):
        """빈 메시지 목록에 대한 방어 응답 분석 테스트"""
        analysis = followup_manager.analyze_defense_response([])
        
        assert analysis["defense_strategy"] == "Unknown"
        assert analysis["rag_used"] is False
        assert analysis["defender_id"] == "unknown"
    
    def test_estimate_defense_strategy_from_keywords(self, followup_manager):
        """키워드 기반 방어 전략 추정 테스트"""
        test_cases = [
            ("Let me clarify what I meant", "Clarify"),
            ("I accept your point", "Accept"),
            ("However, you're wrong", "Counter"),
            ("The important thing is", "Redirect"),
            ("Unknown text", "Unknown")
        ]
        
        for defense_text, expected_strategy in test_cases:
            result = followup_manager._estimate_defense_strategy_from_keywords(
                defense_text, "test_defender"
            )
            assert result["defense_strategy"] == expected_strategy
    
    def test_get_followup_candidates_from_map_success(self, followup_manager, mock_followup_map):
        """followup_map에서 후보 가져오기 성공 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_followup_map):
            
            defense_info = {
                "defense_strategy": "Counter",
                "rag_used": True
            }
            emotion_enhancement = {
                "emotion_type": "neutral"
            }
            
            candidates = followup_manager._get_followup_candidates_from_map(
                defense_info, emotion_enhancement
            )
            
            assert candidates == ["FollowUpQuestion", "Deepen"]
    
    def test_get_followup_candidates_from_map_missing_keys(self, followup_manager, mock_followup_map):
        """followup_map에서 키가 없는 경우 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_followup_map):
            
            defense_info = {
                "defense_strategy": "NonexistentStrategy",
                "rag_used": True
            }
            emotion_enhancement = {
                "emotion_type": "neutral"
            }
            
            candidates = followup_manager._get_followup_candidates_from_map(
                defense_info, emotion_enhancement
            )
            
            assert candidates == ["FollowUpQuestion", "Pivot"]  # 기본값
    
    def test_get_philosopher_name(self, followup_manager):
        """철학자 이름 추출 테스트"""
        test_cases = [
            ("agent_socrates_1", "Socrates"),
            ("plato_agent", "Plato"),
            ("test_aristotle", "Aristotle"),
            ("unknown_philosopher", "Unknown Philosopher")
        ]
        
        for agent_id, expected_name in test_cases:
            result = followup_manager._get_philosopher_name(agent_id)
            if expected_name == "Unknown Philosopher":
                assert "Unknown" not in result or result == "Unknown Philosopher"
            else:
                assert expected_name in result
    
    def test_format_followup_rag_results(self, followup_manager):
        """팔로우업용 RAG 결과 포맷팅 테스트"""
        rag_results = [
            {
                "content": "This is a long piece of content that should be truncated to 200 characters maximum to avoid overwhelming the response generation process with too much information at once.",
                "source": "Academic Paper"
            },
            {
                "content": "Short content",
                "source": "News Article"
            }
        ]
        followup_strategy = "Deepen"
        
        formatted = followup_manager._format_followup_rag_results(rag_results, followup_strategy)
        
        assert "DEEPEN FOLLOWUP" in formatted.upper()
        assert "Academic Paper" in formatted
        assert "News Article" in formatted
        assert len(formatted.split('\n')[1]) <= 220  # 200자 + 소스 정보
    
    def test_format_followup_rag_results_empty(self, followup_manager):
        """빈 RAG 결과 포맷팅 테스트"""
        formatted = followup_manager._format_followup_rag_results([], "Deepen")
        assert formatted == ""
    
    def test_get_last_followup_strategy(self, followup_manager):
        """마지막 팔로우업 전략 정보 가져오기 테스트"""
        # 초기에는 None
        assert followup_manager.get_last_followup_strategy() is None
        
        # 팔로우업 전략 정보 저장
        followup_manager._save_followup_strategy_info(
            "FollowUpQuestion",
            {"use_rag": True},
            "Test defense",
            "Test original attack"
        )
        
        last_strategy = followup_manager.get_last_followup_strategy()
        assert last_strategy is not None
        assert last_strategy["followup_strategy"] == "FollowUpQuestion"
    
    def test_get_followup_history(self, followup_manager):
        """팔로우업 전략 히스토리 가져오기 테스트"""
        # 초기에는 빈 리스트
        assert followup_manager.get_followup_history() == []
        
        # 여러 팔로우업 전략 저장
        strategies = ["FollowUpQuestion", "Deepen", "Reattack"]
        for i, strategy in enumerate(strategies):
            followup_manager._save_followup_strategy_info(
                strategy,
                {"use_rag": i % 2 == 0},
                f"Defense {i}",
                f"Attack {i}"
            )
        
        history = followup_manager.get_followup_history()
        assert len(history) == 3
        assert history[0]["followup_strategy"] == "FollowUpQuestion"
        assert history[1]["followup_strategy"] == "Deepen"
        assert history[2]["followup_strategy"] == "Reattack"
    
    def test_clear_followup_history(self, followup_manager):
        """팔로우업 전략 히스토리 정리 테스트"""
        # 데이터 추가
        followup_manager._save_followup_strategy_info("FollowUpQuestion", {}, "Test", "Test")
        assert len(followup_manager.followup_strategies) == 1
        assert followup_manager.last_followup_strategy is not None
        
        # 정리
        followup_manager.clear_followup_history()
        assert len(followup_manager.followup_strategies) == 0
        assert followup_manager.last_followup_strategy is None
    
    def test_get_followup_statistics_empty(self, followup_manager):
        """빈 팔로우업 통계 테스트"""
        stats = followup_manager.get_followup_statistics()
        
        assert stats["total_followups"] == 0
        assert stats["strategy_distribution"] == {}
        assert stats["rag_usage_rate"] == 0.0
    
    def test_get_followup_statistics_with_data(self, followup_manager):
        """데이터가 있는 팔로우업 통계 테스트"""
        # 테스트 데이터 추가
        strategies_data = [
            ("FollowUpQuestion", True),
            ("FollowUpQuestion", False),
            ("Deepen", True),
            ("Reattack", False)
        ]
        
        for strategy, use_rag in strategies_data:
            followup_manager._save_followup_strategy_info(
                strategy,
                {"use_rag": use_rag},
                "Test defense",
                "Test attack"
            )
        
        stats = followup_manager.get_followup_statistics()
        
        assert stats["total_followups"] == 4
        assert stats["strategy_distribution"]["FollowUpQuestion"] == 2
        assert stats["strategy_distribution"]["Deepen"] == 1
        assert stats["strategy_distribution"]["Reattack"] == 1
        assert stats["rag_usage_rate"] == 0.5  # 2/4
        assert stats["last_strategy"] == "Reattack"
    
    def test_save_followup_strategy_info_history_limit(self, followup_manager):
        """팔로우업 전략 히스토리 크기 제한 테스트"""
        # 15개 전략 저장 (제한은 10개)
        for i in range(15):
            followup_manager._save_followup_strategy_info(
                f"Strategy{i}",
                {"use_rag": False},
                f"Defense {i}",
                f"Attack {i}"
            )
        
        # 최대 10개만 유지되어야 함
        assert len(followup_manager.followup_strategies) == 10
        
        # 최신 10개가 유지되어야 함
        assert followup_manager.followup_strategies[0]["followup_strategy"] == "Strategy5"
        assert followup_manager.followup_strategies[-1]["followup_strategy"] == "Strategy14"
    
    def test_get_followup_strategy_info(self, followup_manager):
        """팔로우업 전략 정보 가져오기 테스트"""
        # 존재하는 전략
        info = followup_manager._get_followup_strategy_info("FollowUpQuestion")
        assert info["description"] == "Ask a probing question"
        assert info["purpose"] == "Deepen the discussion"
        
        # 존재하지 않는 전략 (fallback)
        info = followup_manager._get_followup_strategy_info("NonexistentStrategy")
        assert "NonexistentStrategy" in info["description"]
        assert "follow up" in info["purpose"].lower()
    
    @pytest.mark.parametrize("defense_strategy,rag_used,emotion,expected_in", [
        ("Counter", True, "neutral", ["FollowUpQuestion", "Deepen"]),
        ("Counter", False, "confident", ["Reattack"]),
        ("Clarify", True, "defensive", ["Pivot"]),
        ("Unknown", False, "neutral", ["FollowUpQuestion", "Pivot"])
    ])
    def test_followup_strategy_selection_scenarios(self, followup_manager, mock_followup_map,
                                                 defense_strategy, rag_used, emotion, expected_in):
        """다양한 시나리오에서 팔로우업 전략 선택 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_followup_map):
            
            defense_info = {
                "defense_strategy": defense_strategy,
                "rag_used": rag_used
            }
            emotion_enhancement = {
                "emotion_type": emotion
            }
            
            # 여러 번 실행해서 예상 범위 내의 전략이 선택되는지 확인
            selected_strategies = []
            for _ in range(10):
                strategy = followup_manager.select_followup_strategy(defense_info, emotion_enhancement)
                selected_strategies.append(strategy)
            
            # 모든 선택된 전략이 예상 범위 내에 있어야 함
            for strategy in selected_strategies:
                assert strategy in expected_in or strategy in ["FollowUpQuestion", "Pivot"]  # fallback 포함
    
    def test_rag_usage_estimation(self, followup_manager):
        """RAG 사용 추정 테스트"""
        test_cases = [
            ("Short text", False),  # 짧은 텍스트
            ("This is a longer text with research data and specific studies mentioned that exceeds one hundred characters", True),  # 길고 키워드 포함
            ("Medium length text with some details but no academic keywords that is long enough to exceed the minimum character limit", False),  # 길지만 키워드 없음
            ("Comprehensive analysis based on extensive research and data from multiple studies with detailed information", True)  # 길고 키워드 포함
        ]
        
        for defense_text, expected_rag in test_cases:
            result = followup_manager._estimate_defense_strategy_from_keywords(
                defense_text, "test_defender"
            )
            assert result["rag_used"] == expected_rag
    
    def test_save_followup_strategy_info_timestamp(self, followup_manager):
        """팔로우업 전략 정보 저장 시 타임스탬프 테스트"""
        before_save = datetime.now()
        
        followup_manager._save_followup_strategy_info(
            "FollowUpQuestion",
            {"use_rag": False},
            "Test defense",
            "Test attack"
        )
        
        after_save = datetime.now()
        
        saved_info = followup_manager.followup_strategies[0]
        saved_timestamp = datetime.fromisoformat(saved_info["timestamp"])
        
        assert before_save <= saved_timestamp <= after_save
        assert "followup_strategy" in saved_info
        assert "rag_decision" in saved_info
        assert "followup_plan" in saved_info 