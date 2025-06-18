"""
Unit tests for OpponentAnalyzer class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.agents.participant.analysis.opponent_analyzer import OpponentAnalyzer


class TestOpponentAnalyzer:
    """Test cases for OpponentAnalyzer class."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager fixture."""
        mock_llm = Mock()
        mock_llm.generate_response.return_value = "Mock LLM response"
        return mock_llm
    
    @pytest.fixture
    def philosopher_data(self):
        """Sample philosopher data fixture."""
        return {
            "name": "Socrates",
            "essence": "Know thyself",
            "debate_style": "Questioning",
            "personality": "Curious",
            "key_traits": ["wisdom", "humility"],
            "quote": "I know that I know nothing",
            "vulnerability_sensitivity": {
                "conceptual_clarity": 0.8,
                "logical_leap": 0.7,
                "overgeneralization": 0.6,
                "emotional_appeal": 0.5,
                "lack_of_concrete_evidence": 0.9
            }
        }
    
    @pytest.fixture
    def opponent_analyzer(self, mock_llm_manager, philosopher_data):
        """OpponentAnalyzer instance fixture."""
        return OpponentAnalyzer(
            llm_manager=mock_llm_manager,
            agent_id="test_socrates",
            philosopher_name="Socrates",
            philosopher_data=philosopher_data
        )
    
    def test_initialization(self, opponent_analyzer, mock_llm_manager, philosopher_data):
        """Test OpponentAnalyzer initialization."""
        assert opponent_analyzer.llm_manager == mock_llm_manager
        assert opponent_analyzer.agent_id == "test_socrates"
        assert opponent_analyzer.philosopher_name == "Socrates"
        assert opponent_analyzer.philosopher_data == philosopher_data
        assert hasattr(opponent_analyzer, 'argument_extractor')
        assert hasattr(opponent_analyzer, 'vulnerability_scorer')
        assert isinstance(opponent_analyzer.opponent_arguments, dict)
        assert isinstance(opponent_analyzer.opponent_key_points, list)
        assert isinstance(opponent_analyzer.opponent_details, dict)
    
    def test_analyze_and_score_arguments_success(self, opponent_analyzer):
        """Test successful argument analysis and scoring."""
        # Mock the argument extractor
        mock_arguments = [
            {
                "claim": "AI will replace human jobs",
                "evidence": "Studies show automation trends",
                "reasoning": "Technology advances rapidly",
                "assumptions": ["current trends continue"]
            }
        ]
        opponent_analyzer.argument_extractor.extract_arguments_from_response = Mock(
            return_value=mock_arguments
        )
        
        # Mock the vulnerability scorer
        mock_score_data = {
            "logical_strength": 0.7,
            "evidence_quality": 0.6,
            "relevance": 0.8,
            "final_vulnerability": 0.4,
            "overall_score": 0.65
        }
        opponent_analyzer.vulnerability_scorer.score_single_argument = Mock(
            return_value=mock_score_data
        )
        
        result = opponent_analyzer.analyze_and_score_arguments(
            "AI will replace human jobs because technology advances rapidly",
            "user1"
        )
        
        assert result["status"] == "success"
        assert result["speaker_id"] == "user1"
        assert result["arguments_count"] == 1
        assert len(result["scored_arguments"]) == 1
        assert "analysis_timestamp" in result
        
        # Check that arguments were stored
        assert "user1" in opponent_analyzer.opponent_arguments
        assert len(opponent_analyzer.opponent_arguments["user1"]) == 1
    
    def test_analyze_and_score_arguments_error(self, opponent_analyzer):
        """Test argument analysis with error handling."""
        # Mock the argument extractor to raise an exception
        opponent_analyzer.argument_extractor.extract_arguments_from_response = Mock(
            side_effect=Exception("Extraction failed")
        )
        
        result = opponent_analyzer.analyze_and_score_arguments(
            "Some opponent response",
            "user1"
        )
        
        assert "error" in result
        assert "Extraction failed" in result["error"]
    
    def test_analyze_user_arguments_success(self, opponent_analyzer):
        """Test successful user argument analysis."""
        # Mock the argument extractor
        mock_extracted_args = [
            {
                "claim": "Technology enhances creativity",
                "evidence": "Digital tools enable new art forms",
                "reasoning": "Artists use AI for inspiration",
                "assumptions": ["creativity is measurable"],
                "source_text": "Technology enhances human creativity",
                "argument_id": "user_arg_1"
            }
        ]
        opponent_analyzer.argument_extractor.extract_arguments_from_user_input = Mock(
            return_value=mock_extracted_args
        )
        
        # Mock the vulnerability scorer
        mock_vulnerability_data = {
            "final_vulnerability": 0.3,
            "logical_strength": 0.8,
            "evidence_quality": 0.7
        }
        opponent_analyzer.vulnerability_scorer.score_single_argument = Mock(
            return_value=mock_vulnerability_data
        )
        
        result = opponent_analyzer.analyze_user_arguments(
            "Technology enhances human creativity through digital tools",
            "user1"
        )
        
        assert result["total_arguments"] == 1
        assert result["average_vulnerability"] == 0.3
        assert "user1" in result["opponent_arguments"]
        assert len(result["opponent_arguments"]["user1"]) == 1
        assert "analysis_summary" in result
    
    def test_analyze_user_arguments_no_extraction(self, opponent_analyzer):
        """Test user argument analysis when no arguments are extracted."""
        # Mock empty extraction result
        opponent_analyzer.argument_extractor.extract_arguments_from_user_input = Mock(
            return_value=[]
        )
        
        result = opponent_analyzer.analyze_user_arguments(
            "Some user input",
            "user1"
        )
        
        assert result["total_arguments"] == 0
        assert "user1" in result["opponent_arguments"]
        assert len(result["opponent_arguments"]["user1"]) == 0
        assert "추출 실패" in result["analysis_summary"]
    
    def test_analyze_user_arguments_error(self, opponent_analyzer):
        """Test user argument analysis with error handling."""
        # Mock the argument extractor to raise an exception
        opponent_analyzer.argument_extractor.extract_arguments_from_user_input = Mock(
            side_effect=Exception("User extraction failed")
        )
        
        result = opponent_analyzer.analyze_user_arguments(
            "Some user input",
            "user1"
        )
        
        assert result["total_arguments"] == 0
        assert "오류 발생" in result["analysis_summary"]
    
    def test_extract_opponent_key_points(self, opponent_analyzer):
        """Test opponent key points extraction."""
        test_messages = [
            {"speaker_id": "user1", "text": "AI will replace jobs"},
            {"speaker_id": "user2", "text": "Technology creates opportunities"}
        ]
        
        mock_key_points = [
            "AI automation threatens employment",
            "Technology historically creates new jobs"
        ]
        
        opponent_analyzer.argument_extractor.extract_opponent_key_points = Mock(
            return_value=mock_key_points
        )
        
        opponent_analyzer.extract_opponent_key_points(test_messages)
        
        assert opponent_analyzer.opponent_key_points == mock_key_points
        assert opponent_analyzer.opponent_details["speakers"] == ["user1", "user2"]
        assert opponent_analyzer.opponent_details["message_counts"]["user1"] == 1
        assert opponent_analyzer.opponent_details["message_counts"]["user2"] == 1
    
    def test_clear_opponent_data_specific_speaker(self, opponent_analyzer):
        """Test clearing data for specific speaker."""
        # Setup some test data
        opponent_analyzer.opponent_arguments = {
            "user1": [{"claim": "test1"}],
            "user2": [{"claim": "test2"}]
        }
        
        opponent_analyzer.clear_opponent_data("user1")
        
        assert "user1" not in opponent_analyzer.opponent_arguments
        assert "user2" in opponent_analyzer.opponent_arguments
    
    def test_clear_opponent_data_all(self, opponent_analyzer):
        """Test clearing all opponent data."""
        # Setup some test data
        opponent_analyzer.opponent_arguments = {"user1": [{"claim": "test1"}]}
        opponent_analyzer.opponent_key_points = ["point1", "point2"]
        opponent_analyzer.opponent_details = {"speakers": ["user1"]}
        
        opponent_analyzer.clear_opponent_data()
        
        assert len(opponent_analyzer.opponent_arguments) == 0
        assert len(opponent_analyzer.opponent_key_points) == 0
        assert len(opponent_analyzer.opponent_details) == 0
    
    def test_get_opponent_arguments_specific_speaker(self, opponent_analyzer):
        """Test getting arguments for specific speaker."""
        test_args = [{"claim": "test argument"}]
        opponent_analyzer.opponent_arguments = {"user1": test_args, "user2": []}
        
        result = opponent_analyzer.get_opponent_arguments("user1")
        
        assert "user1" in result
        assert result["user1"] == test_args
        assert "user2" not in result
    
    def test_get_opponent_arguments_all(self, opponent_analyzer):
        """Test getting all opponent arguments."""
        test_data = {"user1": [{"claim": "test1"}], "user2": [{"claim": "test2"}]}
        opponent_analyzer.opponent_arguments = test_data
        
        result = opponent_analyzer.get_opponent_arguments()
        
        assert result == test_data
        # Ensure it's a copy, not the original
        assert result is not opponent_analyzer.opponent_arguments
    
    def test_get_opponent_key_points(self, opponent_analyzer):
        """Test getting opponent key points."""
        test_points = ["point1", "point2", "point3"]
        opponent_analyzer.opponent_key_points = test_points
        
        result = opponent_analyzer.get_opponent_key_points()
        
        assert result == test_points
        # Ensure it's a copy, not the original
        assert result is not opponent_analyzer.opponent_key_points
    
    def test_get_opponent_details(self, opponent_analyzer):
        """Test getting opponent details."""
        test_details = {"speakers": ["user1", "user2"], "message_counts": {"user1": 3}}
        opponent_analyzer.opponent_details = test_details
        
        result = opponent_analyzer.get_opponent_details()
        
        assert result == test_details
        # Ensure it's a copy, not the original
        assert result is not opponent_analyzer.opponent_details
    
    def test_update_my_key_points_from_core_arguments_dict_format(self, opponent_analyzer):
        """Test updating key points from core arguments in dict format."""
        core_arguments = [
            {"argument": "Technology enhances human capability"},
            {"argument": "AI should augment, not replace humans"}
        ]
        
        result = opponent_analyzer.update_my_key_points_from_core_arguments(core_arguments)
        
        expected = [
            "Technology enhances human capability",
            "AI should augment, not replace humans"
        ]
        assert result == expected
    
    def test_update_my_key_points_from_core_arguments_string_format(self, opponent_analyzer):
        """Test updating key points from core arguments in string format."""
        core_arguments = [
            "Direct string argument 1",
            "Direct string argument 2"
        ]
        
        result = opponent_analyzer.update_my_key_points_from_core_arguments(core_arguments)
        
        assert result == core_arguments
    
    def test_update_my_key_points_from_core_arguments_empty(self, opponent_analyzer):
        """Test updating key points with empty core arguments."""
        result = opponent_analyzer.update_my_key_points_from_core_arguments([])
        
        assert result == []
    
    def test_update_my_key_points_from_core_arguments_error(self, opponent_analyzer):
        """Test updating key points with error handling."""
        # Pass invalid data that might cause an error
        result = opponent_analyzer.update_my_key_points_from_core_arguments(None)
        
        assert result == [] 