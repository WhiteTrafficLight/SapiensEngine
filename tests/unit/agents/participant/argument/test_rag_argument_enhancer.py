"""
Unit tests for RAGArgumentEnhancer class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agents.participant.argument.rag_argument_enhancer import RAGArgumentEnhancer


class TestRAGArgumentEnhancer:
    """RAGArgumentEnhancer 클래스 테스트"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM Manager"""
        mock = Mock()
        mock.generate_response = Mock()
        return mock
    
    @pytest.fixture
    def mock_rag_search_manager(self):
        """Mock RAG Search Manager"""
        mock = Mock()
        mock.search_web_only = Mock(return_value=[])
        mock.search_vector_only = Mock(return_value=[])
        mock.search_philosopher_only = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def philosopher_data(self):
        """테스트용 철학자 데이터"""
        return {
            "name": "Plato",
            "essence": "Reality exists in the realm of Forms",
            "debate_style": "Dialectical reasoning and allegory",
            "personality": "Idealistic, systematic, metaphysical",
            "key_traits": ["idealistic", "systematic", "metaphysical"],
            "quote": "The cave allegory reveals the nature of reality"
        }
    
    @pytest.fixture
    def rag_enhancer(self, mock_llm_manager, mock_rag_search_manager, philosopher_data):
        """RAGArgumentEnhancer 인스턴스"""
        return RAGArgumentEnhancer(
            agent_id="test_plato",
            philosopher_data=philosopher_data,
            rag_search_manager=mock_rag_search_manager,
            llm_manager=mock_llm_manager
        )
    
    def test_initialization(self, rag_enhancer, philosopher_data):
        """초기화 테스트"""
        assert rag_enhancer.agent_id == "test_plato"
        assert rag_enhancer.philosopher_name == "Plato"
        assert rag_enhancer.philosopher_essence == philosopher_data["essence"]
        assert rag_enhancer.rag_search_manager is not None
        assert rag_enhancer.llm_manager is not None
    
    def test_generate_rag_queries_for_arguments_success(self, rag_enhancer, mock_llm_manager):
        """RAG 쿼리 생성 성공 테스트"""
        # Mock LLM response with valid JSON
        mock_response = '''
        [
          {
            "query": "educational psychology research on critical thinking",
            "source_type": "web",
            "evidence_type": "research",
            "purpose": "Find studies on critical thinking development"
          },
          {
            "query": "historical examples of philosophical education impact",
            "source_type": "philosopher",
            "evidence_type": "historical",
            "purpose": "Find historical cases of philosophical education benefits"
          }
        ]
        '''
        mock_llm_manager.generate_response.return_value = mock_response
        
        # Test data
        topic = "Philosophical education"
        core_arguments = [
            {
                "id": "arg_1",
                "argument": "Critical thinking is essential",
                "reasoning": "Develops analytical skills",
                "approach": "logical"
            }
        ]
        
        # Test
        result = rag_enhancer.generate_rag_queries_for_arguments(topic, core_arguments)
        
        # Assertions
        assert len(result) == 1
        assert "rag_queries" in result[0]
        assert len(result[0]["rag_queries"]) == 2
        
        query1 = result[0]["rag_queries"][0]
        assert query1["query"] == "educational psychology research on critical thinking"
        assert query1["source_type"] == "web"
        assert query1["evidence_type"] == "research"
        
        query2 = result[0]["rag_queries"][1]
        assert query2["source_type"] == "philosopher"
        assert query2["evidence_type"] == "historical"
        
        # Verify LLM was called
        mock_llm_manager.generate_response.assert_called_once()
        call_args = mock_llm_manager.generate_response.call_args
        assert "Plato" in call_args[1]["system_prompt"]
        assert topic in call_args[1]["user_prompt"]
    
    def test_generate_rag_queries_invalid_json(self, rag_enhancer, mock_llm_manager):
        """잘못된 JSON 응답 처리 테스트"""
        mock_llm_manager.generate_response.return_value = "Invalid JSON response"
        
        topic = "Ethics"
        core_arguments = [{"id": "arg_1", "argument": "Test", "reasoning": "Test"}]
        
        result = rag_enhancer.generate_rag_queries_for_arguments(topic, core_arguments)
        
        assert len(result) == 1
        assert result[0]["rag_queries"] == []
    
    def test_generate_rag_queries_llm_exception(self, rag_enhancer, mock_llm_manager):
        """LLM 예외 처리 테스트"""
        mock_llm_manager.generate_response.side_effect = Exception("API Error")
        
        topic = "Justice"
        core_arguments = [{"id": "arg_1", "argument": "Test", "reasoning": "Test"}]
        
        result = rag_enhancer.generate_rag_queries_for_arguments(topic, core_arguments)
        
        assert len(result) == 1
        assert result[0]["rag_queries"] == []
    
    def test_strengthen_arguments_with_rag_success(self, rag_enhancer, mock_rag_search_manager, mock_llm_manager):
        """RAG를 통한 주장 강화 성공 테스트"""
        # Mock search results
        mock_search_results = [
            {
                "content": "Research shows that 85% of students improve critical thinking through philosophy courses",
                "source": "Academic Research",
                "title": "Philosophy Education Impact Study",
                "url": "https://example.com/study",
                "relevance": 0.9
            }
        ]
        mock_rag_search_manager.search_web_only.return_value = mock_search_results
        
        # Mock LLM strengthening response
        mock_strengthened_response = """
        STRENGTHENED_ARGUMENT: Critical thinking is essential for intellectual development, as evidenced by research
        STRENGTHENED_REASONING: Develops analytical skills, with studies showing 85% improvement in students
        """
        mock_llm_manager.generate_response.return_value = mock_strengthened_response
        
        # Test data
        core_arguments = [
            {
                "id": "arg_1",
                "argument": "Critical thinking is essential",
                "reasoning": "Develops analytical skills",
                "rag_queries": [
                    {
                        "query": "critical thinking research",
                        "source_type": "web",
                        "evidence_type": "research"
                    }
                ]
            }
        ]
        
        # Test
        result = rag_enhancer.strengthen_arguments_with_rag(core_arguments)
        
        # Assertions
        assert len(result) == 1
        strengthened_arg = result[0]
        
        assert strengthened_arg["strengthened"] == True
        assert strengthened_arg["evidence_used"] == 1
        assert strengthened_arg["evidence_sources"] == ["Academic Research"]
        assert "evidenced by research" in strengthened_arg["argument"]
        assert "85% improvement" in strengthened_arg["reasoning"]
        
        # Verify search was called
        mock_rag_search_manager.search_web_only.assert_called_once_with("critical thinking research")
        
        # Verify LLM strengthening was called
        mock_llm_manager.generate_response.assert_called_once()
    
    def test_strengthen_arguments_no_evidence_found(self, rag_enhancer, mock_rag_search_manager):
        """증거를 찾지 못한 경우 테스트"""
        # Mock empty search results
        mock_rag_search_manager.search_web_only.return_value = []
        
        core_arguments = [
            {
                "id": "arg_1",
                "argument": "Original argument",
                "reasoning": "Original reasoning",
                "rag_queries": [
                    {
                        "query": "test query",
                        "source_type": "web",
                        "evidence_type": "research"
                    }
                ]
            }
        ]
        
        result = rag_enhancer.strengthen_arguments_with_rag(core_arguments)
        
        assert len(result) == 1
        assert result[0]["strengthened"] == False
        assert result[0]["argument"] == "Original argument"
        assert result[0]["reasoning"] == "Original reasoning"
    
    def test_perform_rag_search_for_argument_web(self, rag_enhancer, mock_rag_search_manager):
        """웹 검색 수행 테스트"""
        mock_search_results = [
            {
                "content": "Test content",
                "source": "web",
                "title": "Test Title",
                "url": "https://test.com",
                "relevance": 0.8
            }
        ]
        mock_rag_search_manager.search_web_only.return_value = mock_search_results
        
        argument = {
            "rag_queries": [
                {
                    "query": "test web query",
                    "source_type": "web",
                    "evidence_type": "research"
                }
            ]
        }
        
        result = rag_enhancer._perform_rag_search_for_argument(argument)
        
        assert len(result) == 1
        evidence = result[0]
        assert evidence["content"] == "Test content"
        assert evidence["source"] == "web"
        assert evidence["query"] == "test web query"
        assert evidence["evidence_type"] == "research"
        
        mock_rag_search_manager.search_web_only.assert_called_once_with("test web query")
    
    def test_perform_rag_search_for_argument_vector(self, rag_enhancer, mock_rag_search_manager):
        """벡터 검색 수행 테스트"""
        mock_search_results = [
            {
                "content": "Vector content",
                "source": "vector_db",
                "title": "Vector Document",
                "relevance": 0.7
            }
        ]
        mock_rag_search_manager.search_vector_only.return_value = mock_search_results
        
        argument = {
            "rag_queries": [
                {
                    "query": "test vector query",
                    "source_type": "vector",
                    "evidence_type": "historical"
                }
            ]
        }
        
        result = rag_enhancer._perform_rag_search_for_argument(argument)
        
        assert len(result) == 1
        assert result[0]["content"] == "Vector content"
        assert result[0]["source"] == "vector_db"
        
        mock_rag_search_manager.search_vector_only.assert_called_once_with("test vector query")
    
    def test_perform_rag_search_for_argument_philosopher(self, rag_enhancer, mock_rag_search_manager):
        """철학자 검색 수행 테스트"""
        mock_search_results = [
            {
                "content": "Philosophical wisdom",
                "source": "philosopher_works",
                "title": "Ancient Philosophy",
                "author": "Aristotle"
            }
        ]
        mock_rag_search_manager.search_philosopher_only.return_value = mock_search_results
        
        argument = {
            "rag_queries": [
                {
                    "query": "test philosopher query",
                    "source_type": "philosopher",
                    "evidence_type": "expert"
                }
            ]
        }
        
        result = rag_enhancer._perform_rag_search_for_argument(argument)
        
        assert len(result) == 1
        assert result[0]["content"] == "Philosophical wisdom"
        assert result[0]["source"] == "philosopher_works"
        
        mock_rag_search_manager.search_philosopher_only.assert_called_once_with("test philosopher query")
    
    def test_strengthen_single_argument_with_evidence(self, rag_enhancer, mock_llm_manager):
        """단일 주장 강화 테스트"""
        mock_response = """
        STRENGTHENED_ARGUMENT: Enhanced argument with evidence support
        STRENGTHENED_REASONING: Enhanced reasoning incorporating research findings
        """
        mock_llm_manager.generate_response.return_value = mock_response
        
        argument = "Original argument"
        reasoning = "Original reasoning"
        evidence_list = [
            {
                "content": "Research shows 90% effectiveness in educational settings",
                "source": "Academic Study",
                "title": "Education Research"
            }
        ]
        
        result = rag_enhancer._strengthen_single_argument_with_evidence(argument, reasoning, evidence_list)
        
        assert result["argument"] == "Enhanced argument with evidence support"
        assert result["reasoning"] == "Enhanced reasoning incorporating research findings"
        
        # Verify LLM was called with evidence
        mock_llm_manager.generate_response.assert_called_once()
        call_args = mock_llm_manager.generate_response.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Original argument" in user_prompt
        assert "90% effectiveness" in user_prompt
    
    def test_strengthen_single_argument_invalid_response(self, rag_enhancer, mock_llm_manager):
        """잘못된 강화 응답 처리 테스트"""
        mock_llm_manager.generate_response.return_value = "Invalid response format"
        
        argument = "Test argument"
        reasoning = "Test reasoning"
        evidence_list = [{"content": "Test evidence", "source": "test"}]
        
        result = rag_enhancer._strengthen_single_argument_with_evidence(argument, reasoning, evidence_list)
        
        # Should return original argument and reasoning
        assert result["argument"] == "Test argument"
        assert result["reasoning"] == "Test reasoning"
    
    def test_extract_key_data_with_statistics(self, rag_enhancer):
        """통계가 포함된 데이터 추출 테스트"""
        content = "The study found that 75% of participants showed improvement. Other findings were also significant."
        evidence = {"source": "research"}
        
        result = rag_enhancer._extract_key_data(content, evidence)
        
        assert "75% of participants showed improvement" in result
    
    def test_extract_key_data_without_statistics(self, rag_enhancer):
        """통계가 없는 데이터 추출 테스트"""
        content = "This is a meaningful sentence about philosophical concepts and their applications in modern society."
        evidence = {"source": "research"}
        
        result = rag_enhancer._extract_key_data(content, evidence)
        
        assert "philosophical concepts and their applications" in result
    
    def test_extract_key_data_empty_content(self, rag_enhancer):
        """빈 내용 처리 테스트"""
        content = ""
        evidence = {"source": "research"}
        
        result = rag_enhancer._extract_key_data(content, evidence)
        
        assert result == "relevant research findings"
    
    @pytest.mark.parametrize("source_type,expected_method", [
        ("web", "search_web_only"),
        ("vector", "search_vector_only"),
        ("philosopher", "search_philosopher_only"),
        ("unknown", "search_web_only"),  # Default fallback
    ])
    def test_search_method_routing(self, rag_enhancer, mock_rag_search_manager, source_type, expected_method):
        """검색 메서드 라우팅 테스트"""
        argument = {
            "rag_queries": [
                {
                    "query": "test query",
                    "source_type": source_type,
                    "evidence_type": "test"
                }
            ]
        }
        
        rag_enhancer._perform_rag_search_for_argument(argument)
        
        # Verify correct search method was called
        getattr(mock_rag_search_manager, expected_method).assert_called_once_with("test query")


if __name__ == "__main__":
    pytest.main([__file__]) 