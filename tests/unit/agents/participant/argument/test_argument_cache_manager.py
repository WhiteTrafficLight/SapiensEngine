"""
Unit tests for ArgumentCacheManager class.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.agents.participant.argument.argument_cache_manager import ArgumentCacheManager


class TestArgumentCacheManager:
    """ArgumentCacheManager 클래스 테스트"""
    
    @pytest.fixture
    def cache_manager(self):
        """ArgumentCacheManager 인스턴스"""
        return ArgumentCacheManager(agent_id="test_agent")
    
    @pytest.fixture
    def mock_argument_generator(self):
        """Mock ArgumentGenerator"""
        mock = Mock()
        mock.generate_core_arguments = Mock(return_value=[
            {
                "id": "arg_1",
                "argument": "Test argument",
                "reasoning": "Test reasoning",
                "evidence_used": 0,
                "evidence_sources": [],
                "strengthened": False
            }
        ])
        mock.generate_final_opening_argument = Mock(return_value="Final test argument")
        return mock
    
    @pytest.fixture
    def mock_rag_enhancer(self):
        """Mock RAGArgumentEnhancer"""
        mock = Mock()
        mock.generate_rag_queries_for_arguments = Mock(side_effect=lambda topic, args: args)
        mock.strengthen_arguments_with_rag = Mock(side_effect=lambda args: args)
        return mock
    
    def test_initialization(self, cache_manager):
        """초기화 테스트"""
        assert cache_manager.agent_id == "test_agent"
        assert cache_manager.prepared_argument == ""
        assert cache_manager.argument_ready == False
        assert cache_manager.is_preparing == False
        assert cache_manager.last_context is None
        assert cache_manager.argument_preparation_task is None
    
    def test_is_argument_ready_false_initially(self, cache_manager):
        """초기 상태에서 입론 준비 완료 여부 테스트"""
        assert cache_manager.is_argument_ready() == False
    
    def test_is_argument_ready_true_when_prepared(self, cache_manager):
        """입론 준비 완료 시 테스트"""
        cache_manager.prepared_argument = "Test argument"
        cache_manager.argument_ready = True
        
        assert cache_manager.is_argument_ready() == True
    
    def test_is_argument_ready_false_when_empty_argument(self, cache_manager):
        """빈 입론일 때 테스트"""
        cache_manager.prepared_argument = ""
        cache_manager.argument_ready = True
        
        assert cache_manager.is_argument_ready() == False
    
    def test_is_currently_preparing_false_initially(self, cache_manager):
        """초기 상태에서 준비 중 여부 테스트"""
        assert cache_manager.is_currently_preparing() == False
    
    def test_is_currently_preparing_true_when_preparing(self, cache_manager):
        """준비 중일 때 테스트"""
        cache_manager.is_preparing = True
        
        assert cache_manager.is_currently_preparing() == True
    
    def test_invalidate_argument_cache(self, cache_manager):
        """캐시 무효화 테스트"""
        # Set up cache with data
        cache_manager.prepared_argument = "Test argument"
        cache_manager.argument_ready = True
        cache_manager.last_context = {"topic": "test"}
        
        # Invalidate
        cache_manager.invalidate_argument_cache()
        
        # Verify cache is cleared
        assert cache_manager.prepared_argument == ""
        assert cache_manager.argument_ready == False
        assert cache_manager.last_context is None
    
    def test_invalidate_argument_cache_with_running_task(self, cache_manager):
        """실행 중인 작업이 있을 때 캐시 무효화 테스트"""
        # Mock running task
        mock_task = Mock()
        mock_task.done.return_value = False
        cache_manager.argument_preparation_task = mock_task
        
        cache_manager.invalidate_argument_cache()
        
        # Verify task was cancelled
        mock_task.cancel.assert_called_once()
    
    def test_is_same_context_no_previous_context(self, cache_manager):
        """이전 컨텍스트가 없을 때 테스트"""
        context = {"topic": "test", "stance_statement": "test stance"}
        
        assert cache_manager._is_same_context(context) == False
    
    def test_is_same_context_same_context(self, cache_manager):
        """동일한 컨텍스트 테스트"""
        context = {
            "topic": "AI Ethics",
            "stance_statement": "AI should be regulated",
            "debate_stage": "opening"
        }
        cache_manager.last_context = context.copy()
        
        assert cache_manager._is_same_context(context) == True
    
    def test_is_same_context_different_context(self, cache_manager):
        """다른 컨텍스트 테스트"""
        cache_manager.last_context = {
            "topic": "AI Ethics",
            "stance_statement": "AI should be regulated",
            "debate_stage": "opening"
        }
        
        different_context = {
            "topic": "Climate Change",
            "stance_statement": "Immediate action required",
            "debate_stage": "opening"
        }
        
        assert cache_manager._is_same_context(different_context) == False
    
    def test_is_same_context_partial_difference(self, cache_manager):
        """일부 필드가 다른 컨텍스트 테스트"""
        cache_manager.last_context = {
            "topic": "AI Ethics",
            "stance_statement": "AI should be regulated",
            "debate_stage": "opening"
        }
        
        partial_different_context = {
            "topic": "AI Ethics",
            "stance_statement": "AI should be regulated",
            "debate_stage": "rebuttal"  # Different stage
        }
        
        assert cache_manager._is_same_context(partial_different_context) == False
    
    @pytest.mark.asyncio
    async def test_prepare_argument_async_cached_result(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """캐시된 결과 반환 테스트"""
        # Set up cached argument
        cache_manager.prepared_argument = "Cached argument"
        cache_manager.argument_ready = True
        cache_manager.last_context = {
            "topic": "test",
            "stance_statement": "test stance",
            "debate_stage": "opening"
        }
        
        context = cache_manager.last_context.copy()
        
        result = await cache_manager.prepare_argument_async(
            "test", "test stance", context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert result["status"] == "cached"
        assert result["argument"] == "Cached argument"
        assert result["preparation_time"] == 0.0
        
        # Verify generators were not called
        mock_argument_generator.generate_core_arguments.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_prepare_argument_async_new_preparation(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """새로운 입론 준비 테스트"""
        topic = "AI Ethics"
        stance = "AI should be regulated"
        context = {"topic": topic, "stance_statement": stance, "debate_stage": "opening"}
        
        result = await cache_manager.prepare_argument_async(
            topic, stance, context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert result["status"] == "success"
        assert result["argument"] == "Final test argument"
        assert result["preparation_time"] > 0
        assert "core_arguments" in result
        
        # Verify cache was updated
        assert cache_manager.prepared_argument == "Final test argument"
        assert cache_manager.argument_ready == True
        assert cache_manager.last_context == context
        
        # Verify generators were called
        mock_argument_generator.generate_core_arguments.assert_called_once_with(topic, stance)
        mock_argument_generator.generate_final_opening_argument.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_prepare_argument_async_exception_handling(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """예외 처리 테스트"""
        mock_argument_generator.generate_core_arguments.side_effect = Exception("Test error")
        
        topic = "test"
        stance = "test stance"
        context = {"topic": topic, "stance_statement": stance}
        
        result = await cache_manager.prepare_argument_async(
            topic, stance, context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert result["status"] == "error"
        assert result["argument"] == ""
        assert result["preparation_time"] == 0.0
        assert "error" in result
        assert "Test error" in result["error"]
    
    def test_get_prepared_argument_or_generate_cached(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """캐시된 입론 반환 테스트"""
        # Set up cached argument
        cache_manager.prepared_argument = "Cached argument"
        cache_manager.argument_ready = True
        cache_manager.last_context = {
            "topic": "test",
            "stance_statement": "test stance",
            "debate_stage": "opening"
        }
        
        context = cache_manager.last_context.copy()
        
        argument, metadata = cache_manager.get_prepared_argument_or_generate(
            "test", "test stance", context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert argument == "Cached argument"
        assert metadata["status"] == "cached"
        assert metadata["preparation_time"] == 0.0
        
        # Verify generators were not called
        mock_argument_generator.generate_core_arguments.assert_not_called()
    
    def test_get_prepared_argument_or_generate_immediate(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """즉시 생성 테스트"""
        topic = "Climate Change"
        stance = "Immediate action required"
        context = {"topic": topic, "stance_statement": stance, "debate_stage": "opening"}
        
        argument, metadata = cache_manager.get_prepared_argument_or_generate(
            topic, stance, context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert argument == "Final test argument"
        assert metadata["status"] == "generated"
        assert metadata["preparation_time"] > 0
        assert "core_arguments" in metadata
        
        # Verify cache was updated
        assert cache_manager.prepared_argument == "Final test argument"
        assert cache_manager.argument_ready == True
        assert cache_manager.last_context == context
        
        # Verify generators were called
        mock_argument_generator.generate_core_arguments.assert_called_once_with(topic, stance)
    
    def test_get_prepared_argument_or_generate_exception(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """예외 발생 시 폴백 테스트"""
        mock_argument_generator.generate_core_arguments.side_effect = Exception("Generation failed")
        
        topic = "test"
        stance = "test stance"
        context = {"topic": topic, "stance_statement": stance}
        
        argument, metadata = cache_manager.get_prepared_argument_or_generate(
            topic, stance, context, mock_argument_generator, mock_rag_enhancer
        )
        
        assert metadata["status"] == "fallback"
        assert "As a philosopher, I believe" in argument
        assert stance in argument
        assert "error" in metadata
    
    def test_get_preparation_status_initial(self, cache_manager):
        """초기 준비 상태 테스트"""
        status = cache_manager.get_preparation_status()
        
        assert status["is_ready"] == False
        assert status["is_preparing"] == False
        assert status["has_cached_argument"] == False
        assert status["last_context"] is None
    
    def test_get_preparation_status_with_cache(self, cache_manager):
        """캐시가 있는 상태 테스트"""
        cache_manager.prepared_argument = "Test argument"
        cache_manager.argument_ready = True
        cache_manager.last_context = {"topic": "test"}
        
        status = cache_manager.get_preparation_status()
        
        assert status["is_ready"] == True
        assert status["has_cached_argument"] == True
        assert status["last_context"] == {"topic": "test"}
    
    def test_get_preparation_status_with_timing(self, cache_manager):
        """타이밍 정보가 있는 상태 테스트"""
        start_time = datetime.now()
        cache_manager.preparation_start_time = start_time
        cache_manager.preparation_end_time = datetime.now()
        
        status = cache_manager.get_preparation_status()
        
        assert "last_preparation_time" in status
        assert status["last_preparation_time"] >= 0
    
    @pytest.mark.asyncio
    async def test_prepare_argument_async_already_preparing(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """이미 준비 중일 때 테스트"""
        # Mock ongoing task - create a proper coroutine
        async def mock_task():
            return {
                "status": "success",
                "argument": "Previous task result",
                "preparation_time": 1.0
            }
        
        cache_manager.is_preparing = True
        cache_manager.argument_preparation_task = asyncio.create_task(mock_task())
        
        result = await cache_manager.prepare_argument_async(
            "test", "test stance", {}, mock_argument_generator, mock_rag_enhancer
        )
        
        assert result["status"] == "success"
        assert result["argument"] == "Previous task result"
    
    @pytest.mark.asyncio
    async def test_prepare_argument_async_cancelled_task(self, cache_manager, mock_argument_generator, mock_rag_enhancer):
        """취소된 작업 처리 테스트"""
        # Mock cancelled task - create a proper coroutine that raises CancelledError
        async def mock_cancelled_task():
            raise asyncio.CancelledError()
        
        cache_manager.is_preparing = True
        cache_manager.argument_preparation_task = asyncio.create_task(mock_cancelled_task())
        
        result = await cache_manager.prepare_argument_async(
            "test", "test stance", {}, mock_argument_generator, mock_rag_enhancer
        )
        
        # When previous task is cancelled, a new task is started and should succeed
        assert result["status"] == "success"
        assert result["argument"] == "Final test argument"
        assert result["preparation_time"] > 0
    
    @pytest.mark.parametrize("context1,context2,expected", [
        (
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "opening"},
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "opening"},
            True
        ),
        (
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "opening"},
            {"topic": "Climate", "stance_statement": "pro", "debate_stage": "opening"},
            False
        ),
        (
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "opening"},
            {"topic": "AI", "stance_statement": "con", "debate_stage": "opening"},
            False
        ),
        (
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "opening"},
            {"topic": "AI", "stance_statement": "pro", "debate_stage": "rebuttal"},
            False
        ),
    ])
    def test_is_same_context_parametrized(self, cache_manager, context1, context2, expected):
        """다양한 컨텍스트 비교 테스트"""
        cache_manager.last_context = context1
        
        assert cache_manager._is_same_context(context2) == expected


if __name__ == "__main__":
    pytest.main([__file__]) 