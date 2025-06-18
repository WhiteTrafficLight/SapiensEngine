"""
Unit tests for ArgumentExtractor class.
"""

import pytest
import json
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from src.agents.participant.analysis.argument_extractor import ArgumentExtractor


class TestArgumentExtractor:
    """Test cases for ArgumentExtractor class."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager fixture."""
        mock_llm = Mock()
        mock_llm.generate_response.return_value = '[{"claim": "Test claim", "evidence": "Test evidence", "reasoning": "Test reasoning", "assumptions": ["Test assumption"], "argument_type": "logical"}]'
        return mock_llm
    
    @pytest.fixture
    def argument_extractor(self, mock_llm_manager):
        """ArgumentExtractor instance fixture."""
        return ArgumentExtractor(
            llm_manager=mock_llm_manager,
            agent_id="test_socrates",
            philosopher_name="Socrates"
        )
    
    def test_initialization(self, argument_extractor, mock_llm_manager):
        """Test ArgumentExtractor initialization."""
        assert argument_extractor.llm_manager == mock_llm_manager
        assert argument_extractor.agent_id == "test_socrates"
        assert argument_extractor.philosopher_name == "Socrates"
    
    def test_extract_arguments_from_response_success(self, argument_extractor):
        """Test successful argument extraction from response."""
        response = "AI will replace human jobs because automation is advancing rapidly."
        speaker_id = "user1"
        
        result = argument_extractor.extract_arguments_from_response(response, speaker_id)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure of first argument
        first_arg = result[0]
        assert "claim" in first_arg
        assert "evidence" in first_arg
        assert "reasoning" in first_arg
        assert "assumptions" in first_arg
        assert "argument_type" in first_arg
        
        # Verify LLM was called
        argument_extractor.llm_manager.generate_response.assert_called_once()
    
    def test_extract_arguments_from_response_json_parse_error(self, argument_extractor):
        """Test argument extraction with JSON parse error."""
        # Mock LLM to return invalid JSON
        argument_extractor.llm_manager.generate_response.return_value = "Invalid JSON response"
        
        result = argument_extractor.extract_arguments_from_response("test response", "user1")
        
        # Should return fallback argument
        assert isinstance(result, list)
        assert len(result) == 1
        assert "claim" in result[0]
        assert "parsing error" in result[0]["evidence"].lower()
    
    def test_extract_arguments_from_response_llm_error(self, argument_extractor):
        """Test argument extraction with LLM error."""
        # Mock LLM to raise an exception
        argument_extractor.llm_manager.generate_response.side_effect = Exception("LLM failed")
        
        result = argument_extractor.extract_arguments_from_response("test response", "user1")
        
        # Should return fallback argument
        assert isinstance(result, list)
        assert len(result) == 1
        assert "claim" in result[0]
    
    def test_extract_arguments_from_user_input_success(self, argument_extractor):
        """Test successful argument extraction from user input."""
        # Mock LLM response for user input
        mock_response = '{"arguments": [{"claim": "Technology enhances creativity", "evidence": "Digital tools", "reasoning": "Artists use AI", "assumptions": ["creativity measurable"]}]}'
        argument_extractor.llm_manager.generate_response.return_value = mock_response
        
        user_response = "Technology enhances human creativity through digital tools"
        speaker_id = "user1"
        
        result = argument_extractor.extract_arguments_from_user_input(user_response, speaker_id)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure
        first_arg = result[0]
        assert "claim" in first_arg
        assert "evidence" in first_arg
        assert "reasoning" in first_arg
        assert "assumptions" in first_arg
        assert "source_text" in first_arg
        assert "argument_id" in first_arg
        
        assert first_arg["source_text"] == user_response
    
    def test_extract_arguments_from_user_input_json_parse_error(self, argument_extractor):
        """Test user input extraction with JSON parse error."""
        # Mock LLM to return invalid JSON
        argument_extractor.llm_manager.generate_response.return_value = "Invalid JSON"
        
        result = argument_extractor.extract_arguments_from_user_input("test input", "user1")
        
        # Should return empty list
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_arguments_from_user_input_llm_error(self, argument_extractor):
        """Test user input extraction with LLM error."""
        # Mock LLM to raise an exception
        argument_extractor.llm_manager.generate_response.side_effect = Exception("LLM failed")
        
        result = argument_extractor.extract_arguments_from_user_input("test input", "user1")
        
        # Should return empty list
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_opponent_key_points_success(self, argument_extractor):
        """Test successful opponent key points extraction."""
        # Mock LLM response for key points
        mock_response = '["AI threatens employment", "Technology creates opportunities", "Automation changes job market"]'
        argument_extractor.llm_manager.generate_response.return_value = mock_response
        
        opponent_messages = [
            {"speaker_id": "user1", "text": "AI will replace jobs"},
            {"speaker_id": "user2", "text": "Technology creates new opportunities"},
            {"speaker_id": "user1", "text": "Automation is inevitable"}
        ]
        
        result = argument_extractor.extract_opponent_key_points(opponent_messages)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Verify LLM was called
        argument_extractor.llm_manager.generate_response.assert_called_once()
    
    def test_extract_opponent_key_points_empty_messages(self, argument_extractor):
        """Test opponent key points extraction with empty messages."""
        result = argument_extractor.extract_opponent_key_points([])
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_opponent_key_points_no_text(self, argument_extractor):
        """Test opponent key points extraction with messages without text."""
        opponent_messages = [
            {"speaker_id": "user1", "text": ""},
            {"speaker_id": "user2"}  # No text field
        ]
        
        result = argument_extractor.extract_opponent_key_points(opponent_messages)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_opponent_key_points_json_parse_error(self, argument_extractor):
        """Test opponent key points extraction with JSON parse error."""
        # Mock LLM to return invalid JSON
        argument_extractor.llm_manager.generate_response.return_value = "Invalid JSON response"
        
        opponent_messages = [
            {"speaker_id": "user1", "text": "Some meaningful text"}
        ]
        
        result = argument_extractor.extract_opponent_key_points(opponent_messages)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_opponent_key_points_llm_error(self, argument_extractor):
        """Test opponent key points extraction with LLM error."""
        # Mock LLM to raise an exception
        argument_extractor.llm_manager.generate_response.side_effect = Exception("LLM failed")
        
        opponent_messages = [
            {"speaker_id": "user1", "text": "Some meaningful text"}
        ]
        
        result = argument_extractor.extract_opponent_key_points(opponent_messages)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_extract_key_concept_success(self, argument_extractor):
        """Test successful key concept extraction."""
        text = "Artificial intelligence and machine learning will transform society"
        
        result = argument_extractor.extract_key_concept(text)
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Should extract a meaningful word, not a stop word
        assert result.lower() not in ['the', 'and', 'or', 'but', 'in', 'on', 'at']
    
    def test_extract_key_concept_empty_text(self, argument_extractor):
        """Test key concept extraction with empty text."""
        result = argument_extractor.extract_key_concept("")
        
        assert result == "concept"
    
    def test_extract_key_concept_short_words(self, argument_extractor):
        """Test key concept extraction with only short words."""
        text = "a an the in on at"
        
        result = argument_extractor.extract_key_concept(text)
        
        assert result == "concept"
    
    def test_extract_key_concept_error_handling(self, argument_extractor):
        """Test key concept extraction with error handling."""
        # Pass None to trigger error
        result = argument_extractor.extract_key_concept(None)
        
        assert result == "concept"
    
    def test_parse_json_response_valid_array(self, argument_extractor):
        """Test JSON response parsing with valid array."""
        response = '[{"claim": "test", "evidence": "test"}]'
        
        result = argument_extractor._parse_json_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["claim"] == "test"
    
    def test_parse_json_response_valid_object(self, argument_extractor):
        """Test JSON response parsing with valid object."""
        response = '{"claim": "test", "evidence": "test"}'
        
        result = argument_extractor._parse_json_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["claim"] == "test"
    
    def test_parse_json_response_invalid_json(self, argument_extractor):
        """Test JSON response parsing with invalid JSON."""
        response = "Invalid JSON string"
        
        result = argument_extractor._parse_json_response(response)
        
        assert result is None
    
    def test_clean_json_response_with_markdown(self, argument_extractor):
        """Test JSON response cleaning with markdown code blocks."""
        response = '```json\n{"test": "value"}\n```'
        
        result = argument_extractor._clean_json_response(response)
        
        assert result == '{"test": "value"}'
    
    def test_clean_json_response_with_backticks(self, argument_extractor):
        """Test JSON response cleaning with backticks."""
        response = '```{"test": "value"}```'
        
        result = argument_extractor._clean_json_response(response)
        
        assert result == '{"test": "value"}'
    
    def test_clean_json_response_no_markdown(self, argument_extractor):
        """Test JSON response cleaning without markdown."""
        response = '{"test": "value"}'
        
        result = argument_extractor._clean_json_response(response)
        
        assert result == '{"test": "value"}'
    
    def test_get_fallback_argument(self, argument_extractor):
        """Test fallback argument generation."""
        response = "This is a test response that is quite long and should be truncated properly when used as a fallback argument claim."
        
        result = argument_extractor._get_fallback_argument(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        
        fallback_arg = result[0]
        assert "claim" in fallback_arg
        assert "evidence" in fallback_arg
        assert "reasoning" in fallback_arg
        assert "assumptions" in fallback_arg
        assert "argument_type" in fallback_arg
        
        # Check truncation
        if len(response) > 200:
            assert len(fallback_arg["claim"]) <= 203  # 200 + "..."
            assert fallback_arg["claim"].endswith("...")
    
    @pytest.mark.parametrize("response_format,expected_count", [
        ('[{"claim": "test1"}, {"claim": "test2"}]', 2),
        ('{"claim": "single test"}', 1),
        ('[]', 1),  # Empty array should return fallback argument
        ('invalid json', 1),  # Should return fallback
    ])
    def test_extract_arguments_various_formats(self, argument_extractor, response_format, expected_count):
        """Test argument extraction with various response formats."""
        # Mock LLM response
        argument_extractor.llm_manager.generate_response.return_value = response_format
        
        result = argument_extractor.extract_arguments_from_response("test", "user1")
        
        assert isinstance(result, list)
        assert len(result) == expected_count 