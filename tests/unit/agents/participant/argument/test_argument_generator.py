"""
Unit tests for ArgumentGenerator class.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.agents.participant.argument.argument_generator import ArgumentGenerator


class TestArgumentGenerator:
    """ArgumentGenerator 클래스 테스트"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM Manager"""
        mock = Mock()
        mock.generate_response = Mock()
        return mock
    
    @pytest.fixture
    def philosopher_data(self):
        """테스트용 철학자 데이터"""
        return {
            "name": "Socrates",
            "essence": "Know thyself and question everything",
            "debate_style": "Socratic questioning and dialectical method",
            "personality": "Curious, humble, persistent in seeking truth",
            "key_traits": ["questioning", "dialectical", "truth-seeking"],
            "quote": "The unexamined life is not worth living"
        }
    
    @pytest.fixture
    def argument_generator(self, mock_llm_manager, philosopher_data):
        """ArgumentGenerator 인스턴스"""
        return ArgumentGenerator(
            agent_id="test_socrates",
            philosopher_data=philosopher_data,
            llm_manager=mock_llm_manager
        )
    
    def test_initialization(self, argument_generator, philosopher_data):
        """초기화 테스트"""
        assert argument_generator.agent_id == "test_socrates"
        assert argument_generator.philosopher_name == "Socrates"
        assert argument_generator.philosopher_essence == philosopher_data["essence"]
        assert argument_generator.philosopher_debate_style == philosopher_data["debate_style"]
        assert argument_generator.philosopher_personality == philosopher_data["personality"]
        assert argument_generator.philosopher_key_traits == philosopher_data["key_traits"]
        assert argument_generator.philosopher_quote == philosopher_data["quote"]
    
    def test_generate_core_arguments_success(self, argument_generator, mock_llm_manager):
        """핵심 주장 생성 성공 테스트"""
        # Mock LLM response with valid JSON
        mock_response = '''
        [
          {
            "argument": "True knowledge comes from recognizing our ignorance",
            "reasoning": "By acknowledging what we don't know, we open ourselves to learning",
            "approach": "dialectical"
          },
          {
            "argument": "Virtue is the highest form of knowledge",
            "reasoning": "Understanding good and evil leads to virtuous action",
            "approach": "ethical"
          }
        ]
        '''
        mock_llm_manager.generate_response.return_value = mock_response
        
        # Test
        topic = "The value of philosophical education"
        stance = "Philosophical education is essential for human development"
        result = argument_generator.generate_core_arguments(topic, stance)
        
        # Assertions
        assert len(result) == 2
        assert result[0]["id"] == "arg_1"
        assert result[0]["argument"] == "True knowledge comes from recognizing our ignorance"
        assert result[0]["reasoning"] == "By acknowledging what we don't know, we open ourselves to learning"
        assert result[0]["approach"] == "dialectical"
        assert result[0]["evidence_used"] == 0
        assert result[0]["evidence_sources"] == []
        assert result[0]["strengthened"] == False
        
        assert result[1]["id"] == "arg_2"
        assert result[1]["argument"] == "Virtue is the highest form of knowledge"
        
        # Verify LLM was called with correct parameters
        mock_llm_manager.generate_response.assert_called_once()
        call_args = mock_llm_manager.generate_response.call_args
        assert call_args[1]["llm_model"] == "gpt-4o"
        assert call_args[1]["max_tokens"] == 1000
        assert "Socrates" in call_args[1]["system_prompt"]
        assert topic in call_args[1]["user_prompt"]
        assert stance in call_args[1]["user_prompt"]
    
    def test_generate_core_arguments_invalid_json(self, argument_generator, mock_llm_manager):
        """잘못된 JSON 응답 처리 테스트"""
        # Mock LLM response with invalid JSON
        mock_llm_manager.generate_response.return_value = "This is not valid JSON"
        
        # Test
        topic = "AI ethics"
        stance = "AI should be regulated"
        result = argument_generator.generate_core_arguments(topic, stance)
        
        # Should return fallback arguments
        assert len(result) == 2
        assert result[0]["id"] == "arg_1"
        assert "socrates perspective" in result[0]["argument"].lower()
        assert result[0]["approach"] == "philosophical_foundation"
        
        assert result[1]["id"] == "arg_2"
        assert "logical implications" in result[1]["argument"].lower()
        assert result[1]["approach"] == "logical_analysis"
    
    def test_generate_core_arguments_llm_exception(self, argument_generator, mock_llm_manager):
        """LLM 호출 예외 처리 테스트"""
        # Mock LLM to raise exception
        mock_llm_manager.generate_response.side_effect = Exception("LLM API Error")
        
        # Test
        topic = "Climate change"
        stance = "Immediate action is required"
        result = argument_generator.generate_core_arguments(topic, stance)
        
        # Should return fallback arguments
        assert len(result) == 2
        assert all(arg["strengthened"] == False for arg in result)
        assert all(arg["evidence_used"] == 0 for arg in result)
    
    def test_get_fallback_arguments(self, argument_generator):
        """폴백 주장 생성 테스트"""
        topic = "Education reform"
        stance = "Education should be personalized"
        
        result = argument_generator._get_fallback_arguments(topic, stance)
        
        assert len(result) == 2
        assert result[0]["id"] == "arg_1"
        assert "socrates perspective" in result[0]["argument"].lower()
        assert "personalized" in result[0]["argument"].lower()
        assert result[0]["approach"] == "philosophical_foundation"
        
        assert result[1]["id"] == "arg_2"
        assert "logical implications" in result[1]["argument"].lower()
        assert "education reform" in result[1]["argument"].lower()
        assert result[1]["approach"] == "logical_analysis"
    
    def test_generate_final_opening_argument(self, argument_generator, mock_llm_manager):
        """최종 입론 생성 테스트"""
        # Mock LLM response
        mock_final_argument = """
        As Socrates, I stand before you today to argue that philosophical education is not merely beneficial, 
        but absolutely essential for human development. Through the dialectical method of questioning, 
        we discover that true wisdom begins with acknowledging our ignorance...
        """
        mock_llm_manager.generate_response.return_value = mock_final_argument
        
        # Prepare test data
        topic = "Philosophical education"
        stance = "Essential for human development"
        core_arguments = [
            {
                "id": "arg_1",
                "argument": "Knowledge through questioning",
                "reasoning": "Socratic method reveals truth",
                "evidence_used": 2,
                "evidence_sources": ["Academic Research", "Historical Examples"],
                "strengthened": True
            },
            {
                "id": "arg_2", 
                "argument": "Virtue through understanding",
                "reasoning": "Knowledge leads to ethical behavior",
                "evidence_used": 0,
                "evidence_sources": [],
                "strengthened": False
            }
        ]
        
        # Test
        result = argument_generator.generate_final_opening_argument(topic, stance, core_arguments)
        
        # Assertions
        assert result == mock_final_argument
        
        # Verify LLM was called correctly
        mock_llm_manager.generate_response.assert_called_once()
        call_args = mock_llm_manager.generate_response.call_args
        assert call_args[1]["llm_model"] == "gpt-4o"
        assert call_args[1]["max_tokens"] == 1300
        
        # Check that strengthened arguments were included in prompt
        user_prompt = call_args[1]["user_prompt"]
        assert "Knowledge through questioning" in user_prompt
        assert "지원 증거: 2개" in user_prompt
        assert "순수 철학적 논증" in user_prompt
    
    def test_generate_final_opening_argument_no_evidence(self, argument_generator, mock_llm_manager):
        """증거 없는 주장들로 최종 입론 생성 테스트"""
        mock_final_argument = "Pure philosophical argument without external evidence..."
        mock_llm_manager.generate_response.return_value = mock_final_argument
        
        topic = "Free will"
        stance = "Free will exists"
        core_arguments = [
            {
                "id": "arg_1",
                "argument": "Consciousness implies choice",
                "reasoning": "Self-awareness enables decision-making",
                "evidence_used": 0,
                "evidence_sources": [],
                "strengthened": False
            }
        ]
        
        result = argument_generator.generate_final_opening_argument(topic, stance, core_arguments)
        
        assert result == mock_final_argument
        
        # Check that evidence summary indicates no external evidence
        call_args = mock_llm_manager.generate_response.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Pure philosophical reasoning - no external evidence needed" in user_prompt
    
    @pytest.mark.parametrize("topic,stance", [
        ("Artificial Intelligence", "AI should be regulated"),
        ("Climate Change", "Immediate action required"),
        ("Social Justice", "Equality is fundamental"),
    ])
    def test_generate_core_arguments_various_topics(self, argument_generator, mock_llm_manager, topic, stance):
        """다양한 주제에 대한 핵심 주장 생성 테스트"""
        # Mock valid JSON response
        mock_response = '''
        [
          {
            "argument": "Test argument for topic",
            "reasoning": "Test reasoning",
            "approach": "test_approach"
          }
        ]
        '''
        mock_llm_manager.generate_response.return_value = mock_response
        
        result = argument_generator.generate_core_arguments(topic, stance)
        
        assert len(result) >= 1
        assert result[0]["argument"] == "Test argument for topic"
        
        # Verify topic and stance were included in the prompt
        call_args = mock_llm_manager.generate_response.call_args
        assert topic in call_args[1]["user_prompt"]
        assert stance in call_args[1]["user_prompt"]


if __name__ == "__main__":
    pytest.main([__file__]) 