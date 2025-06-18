"""
Unit tests for DefenseStrategyManager.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import yaml
import os
from typing import Dict, List, Any

from src.agents.participant.strategy.defense_strategy_manager import DefenseStrategyManager


class TestDefenseStrategyManager:
    """DefenseStrategyManager 테스트 클래스"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM Manager"""
        mock_llm = Mock()
        mock_llm.generate_response.return_value = "I need to clarify my position on this matter."
        return mock_llm
    
    @pytest.fixture
    def philosopher_data(self):
        """철학자 데이터"""
        return {
            "name": "Plato",
            "essence": "Seek truth through reason and dialogue",
            "debate_style": "Dialectical reasoning",
            "personality": "Thoughtful and systematic",
            "defense_weights": {
                "Clarify": 0.7,
                "Accept": 0.2,
                "Counter": 0.8,
                "Redirect": 0.5,
                "Strengthen": 0.6,
                "Reframe": 0.4
            }
        }
    
    @pytest.fixture
    def strategy_styles(self):
        """전략 스타일 데이터"""
        return {
            "defense_strategies": {
                "Clarify": {
                    "description": "Clarify the position",
                    "purpose": "Remove misunderstanding",
                    "style_prompt": "Let me clarify",
                    "example": "What I meant was..."
                },
                "Counter": {
                    "description": "Counter the attack",
                    "purpose": "Refute the criticism",
                    "style_prompt": "However, consider this",
                    "example": "But that's not quite right..."
                }
            }
        }
    
    @pytest.fixture
    def mock_defense_map(self):
        """Mock defense_map.yaml 데이터"""
        return {
            "Clipping": {
                "RAG_YES": {
                    "neutral": ["Counter", "Strengthen"],
                    "confident": ["Counter", "Reframe"],
                    "defensive": ["Clarify", "Accept"]
                },
                "RAG_NO": {
                    "neutral": ["Clarify", "Counter"],
                    "confident": ["Counter"],
                    "defensive": ["Accept", "Clarify"]
                }
            },
            "Framing Shift": {
                "RAG_YES": {
                    "neutral": ["Reframe", "Counter"],
                    "confident": ["Counter", "Redirect"],
                    "defensive": ["Clarify", "Reframe"]
                },
                "RAG_NO": {
                    "neutral": ["Clarify", "Redirect"],
                    "confident": ["Redirect"],
                    "defensive": ["Accept"]
                }
            }
        }
    
    @pytest.fixture
    def defense_manager(self, philosopher_data, strategy_styles, mock_llm_manager):
        """DefenseStrategyManager 인스턴스"""
        return DefenseStrategyManager(
            agent_id="test_plato_agent",
            philosopher_data=philosopher_data,
            strategy_styles=strategy_styles,
            llm_manager=mock_llm_manager
        )
    
    def test_initialization(self, defense_manager, philosopher_data):
        """초기화 테스트"""
        assert defense_manager.agent_id == "test_plato_agent"
        assert defense_manager.philosopher_name == "Plato"
        assert defense_manager.philosopher_essence == philosopher_data["essence"]
        assert defense_manager.defense_history == []
        assert defense_manager.last_defense_strategy is None
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('os.path.exists')
    def test_select_defense_strategy_success(self, mock_exists, mock_yaml_load, mock_file, 
                                           defense_manager, mock_defense_map):
        """방어 전략 선택 성공 테스트"""
        # Mock 설정
        mock_exists.return_value = True
        mock_yaml_load.return_value = mock_defense_map
        
        attack_info = {
            "attack_strategy": "Clipping",
            "rag_used": True,
            "attacker_id": "opponent_1"
        }
        emotion_enhancement = {
            "emotion_type": "neutral"
        }
        
        strategy = defense_manager.select_defense_strategy(attack_info, emotion_enhancement)
        
        assert strategy in ["Counter", "Strengthen"]  # mock_defense_map에서 예상되는 값
        assert isinstance(strategy, str)
    
    @patch('os.path.exists')
    def test_select_defense_strategy_no_map_file(self, mock_exists, defense_manager):
        """defense_map.yaml 파일이 없는 경우 테스트"""
        mock_exists.return_value = False
        
        attack_info = {
            "attack_strategy": "Unknown",
            "rag_used": False
        }
        
        strategy = defense_manager.select_defense_strategy(attack_info)
        
        assert strategy in ["Clarify", "Accept"]  # 기본값
    
    def test_select_defense_strategy_no_weights(self, strategy_styles, mock_llm_manager):
        """defense_weights가 없는 철학자 테스트"""
        philosopher_data_no_weights = {
            "name": "TestPhilosopher",
            "essence": "Test essence",
            "debate_style": "Test style",
            "personality": "Test personality"
            # defense_weights 없음
        }
        
        manager = DefenseStrategyManager(
            agent_id="test_agent",
            philosopher_data=philosopher_data_no_weights,
            strategy_styles=strategy_styles,
            llm_manager=mock_llm_manager
        )
        
        attack_info = {"attack_strategy": "Unknown", "rag_used": False}
        strategy = manager.select_defense_strategy(attack_info)
        
        assert strategy in ["Clarify", "Accept"]  # 기본값 또는 첫 번째 후보
    
    def test_generate_defense_response_success(self, defense_manager):
        """방어 응답 생성 성공 테스트"""
        topic = "Is democracy the best form of government?"
        recent_messages = [
            {
                "speaker_id": "opponent_socrates",
                "text": "Democracy can lead to mob rule and poor decisions."
            }
        ]
        stance_statements = {
            "plato": "Democracy has flaws but is still preferable to alternatives"
        }
        defense_strategy = "Counter"
        defense_rag_decision = {
            "use_rag": False,
            "results": []
        }
        
        response = defense_manager.generate_defense_response(
            topic, recent_messages, stance_statements, defense_strategy, defense_rag_decision
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert defense_manager.last_defense_strategy is not None
        assert len(defense_manager.defense_history) == 1
    
    def test_generate_defense_response_with_rag(self, defense_manager):
        """RAG를 사용한 방어 응답 생성 테스트"""
        topic = "Is democracy the best form of government?"
        recent_messages = [
            {
                "speaker_id": "opponent_socrates",
                "text": "Democracy can lead to mob rule."
            }
        ]
        stance_statements = {"plato": "Democracy is good"}
        defense_strategy = "Counter"
        defense_rag_decision = {
            "use_rag": True,
            "results": [
                {
                    "content": "Democratic institutions provide checks and balances",
                    "source": "Political Science Research"
                },
                {
                    "content": "Historical evidence shows democratic resilience",
                    "source": "History Journal"
                }
            ]
        }
        
        response = defense_manager.generate_defense_response(
            topic, recent_messages, stance_statements, defense_strategy, defense_rag_decision
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_generate_defense_response_llm_error(self, defense_manager):
        """LLM 오류 시 fallback 테스트"""
        # LLM이 예외를 발생시키도록 설정
        defense_manager.llm_manager.generate_response.side_effect = Exception("LLM Error")
        
        topic = "Test topic"
        recent_messages = [{"speaker_id": "opponent", "text": "Test attack"}]
        stance_statements = {"plato": "Test stance"}
        defense_strategy = "Clarify"
        defense_rag_decision = {"use_rag": False, "results": []}
        
        response = defense_manager.generate_defense_response(
            topic, recent_messages, stance_statements, defense_strategy, defense_rag_decision
        )
        
        assert isinstance(response, str)
        assert "consider" in response.lower()  # fallback 메시지 확인
    
    def test_get_defense_candidates_from_map_success(self, defense_manager, mock_defense_map):
        """defense_map에서 후보 가져오기 성공 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_defense_map):
            
            attack_info = {
                "attack_strategy": "Clipping",
                "rag_used": True
            }
            emotion_enhancement = {
                "emotion_type": "neutral"
            }
            
            candidates = defense_manager._get_defense_candidates_from_map(
                attack_info, emotion_enhancement
            )
            
            assert candidates == ["Counter", "Strengthen"]
    
    def test_get_defense_candidates_from_map_missing_keys(self, defense_manager, mock_defense_map):
        """defense_map에서 키가 없는 경우 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_defense_map):
            
            attack_info = {
                "attack_strategy": "NonexistentStrategy",
                "rag_used": True
            }
            emotion_enhancement = {
                "emotion_type": "neutral"
            }
            
            candidates = defense_manager._get_defense_candidates_from_map(
                attack_info, emotion_enhancement
            )
            
            assert candidates == ["Clarify", "Accept"]  # 기본값
    
    def test_get_philosopher_name(self, defense_manager):
        """철학자 이름 추출 테스트"""
        test_cases = [
            ("agent_socrates_1", "Socrates"),
            ("plato_agent", "Plato"),
            ("test_aristotle", "Aristotle"),
            ("unknown_philosopher", "Unknown Philosopher")
        ]
        
        for agent_id, expected_name in test_cases:
            result = defense_manager._get_philosopher_name(agent_id)
            if expected_name == "Unknown Philosopher":
                assert "Unknown" not in result or result == "Unknown Philosopher"
            else:
                assert expected_name in result
    
    def test_format_defense_rag_results(self, defense_manager):
        """방어용 RAG 결과 포맷팅 테스트"""
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
        defense_strategy = "Counter"
        
        formatted = defense_manager._format_defense_rag_results(rag_results, defense_strategy)
        
        assert "COUNTER DEFENSE" in formatted.upper()
        assert "Academic Paper" in formatted
        assert "News Article" in formatted
        assert len(formatted.split('\n')[1]) <= 220  # 200자 + 소스 정보
    
    def test_format_defense_rag_results_empty(self, defense_manager):
        """빈 RAG 결과 포맷팅 테스트"""
        formatted = defense_manager._format_defense_rag_results([], "Counter")
        assert formatted == ""
    
    def test_get_last_defense_strategy(self, defense_manager):
        """마지막 방어 전략 정보 가져오기 테스트"""
        # 초기에는 None
        assert defense_manager.get_last_defense_strategy() is None
        
        # 방어 전략 정보 저장
        defense_manager._save_defense_strategy_info(
            "Counter", 
            {"use_rag": True}, 
            "Test attack"
        )
        
        last_strategy = defense_manager.get_last_defense_strategy()
        assert last_strategy is not None
        assert last_strategy["strategy_type"] == "Counter"
    
    def test_get_defense_history(self, defense_manager):
        """방어 전략 히스토리 가져오기 테스트"""
        # 초기에는 빈 리스트
        assert defense_manager.get_defense_history() == []
        
        # 여러 방어 전략 저장
        for i, strategy in enumerate(["Counter", "Clarify", "Strengthen"]):
            defense_manager._save_defense_strategy_info(
                strategy,
                {"use_rag": i % 2 == 0},
                f"Attack {i}"
            )
        
        history = defense_manager.get_defense_history()
        assert len(history) == 3
        assert history[0]["strategy_type"] == "Counter"
        assert history[1]["strategy_type"] == "Clarify"
        assert history[2]["strategy_type"] == "Strengthen"
    
    def test_clear_defense_history(self, defense_manager):
        """방어 전략 히스토리 정리 테스트"""
        # 데이터 추가
        defense_manager._save_defense_strategy_info("Counter", {}, "Test")
        assert len(defense_manager.defense_history) == 1
        assert defense_manager.last_defense_strategy is not None
        
        # 정리
        defense_manager.clear_defense_history()
        assert len(defense_manager.defense_history) == 0
        assert defense_manager.last_defense_strategy is None
    
    def test_get_defense_statistics_empty(self, defense_manager):
        """빈 방어 통계 테스트"""
        stats = defense_manager.get_defense_statistics()
        
        assert stats["total_defenses"] == 0
        assert stats["strategy_distribution"] == {}
        assert stats["rag_usage_rate"] == 0.0
    
    def test_get_defense_statistics_with_data(self, defense_manager):
        """데이터가 있는 방어 통계 테스트"""
        # 테스트 데이터 추가
        strategies_data = [
            ("Counter", True),
            ("Counter", False),
            ("Clarify", True),
            ("Strengthen", False)
        ]
        
        for strategy, use_rag in strategies_data:
            defense_manager._save_defense_strategy_info(
                strategy,
                {"use_rag": use_rag},
                "Test attack"
            )
        
        stats = defense_manager.get_defense_statistics()
        
        assert stats["total_defenses"] == 4
        assert stats["strategy_distribution"]["Counter"] == 2
        assert stats["strategy_distribution"]["Clarify"] == 1
        assert stats["strategy_distribution"]["Strengthen"] == 1
        assert stats["rag_usage_rate"] == 0.5  # 2/4
        assert stats["last_strategy"] == "Strengthen"
    
    def test_save_defense_strategy_info_history_limit(self, defense_manager):
        """방어 전략 히스토리 크기 제한 테스트"""
        # 15개 전략 저장 (제한은 10개)
        for i in range(15):
            defense_manager._save_defense_strategy_info(
                f"Strategy{i}",
                {"use_rag": False},
                f"Attack {i}"
            )
        
        # 최대 10개만 유지되어야 함
        assert len(defense_manager.defense_history) == 10
        
        # 최신 10개가 유지되어야 함
        assert defense_manager.defense_history[0]["strategy_type"] == "Strategy5"
        assert defense_manager.defense_history[-1]["strategy_type"] == "Strategy14"
    
    @pytest.mark.parametrize("attack_strategy,rag_used,emotion,expected_in", [
        ("Clipping", True, "neutral", ["Counter", "Strengthen"]),
        ("Clipping", False, "confident", ["Counter"]),
        ("Framing Shift", True, "defensive", ["Clarify", "Reframe"]),
        ("Unknown", False, "neutral", ["Clarify", "Accept"])
    ])
    def test_defense_strategy_selection_scenarios(self, defense_manager, mock_defense_map,
                                                attack_strategy, rag_used, emotion, expected_in):
        """다양한 시나리오에서 방어 전략 선택 테스트"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open()), \
             patch('yaml.safe_load', return_value=mock_defense_map):
            
            attack_info = {
                "attack_strategy": attack_strategy,
                "rag_used": rag_used
            }
            emotion_enhancement = {
                "emotion_type": emotion
            }
            
            # 여러 번 실행해서 예상 범위 내의 전략이 선택되는지 확인
            selected_strategies = []
            for _ in range(10):
                strategy = defense_manager.select_defense_strategy(attack_info, emotion_enhancement)
                selected_strategies.append(strategy)
            
            # 모든 선택된 전략이 예상 범위 내에 있어야 함
            for strategy in selected_strategies:
                assert strategy in expected_in or strategy in ["Clarify", "Accept"]  # fallback 포함 