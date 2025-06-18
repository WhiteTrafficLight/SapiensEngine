"""
DebateContextManager 클래스 유닛 테스트

객관적인 컨텍스트 요약 및 관리 기능을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.dialogue.context.debate_context_manager import DebateContextManager


class MockLLMManager:
    """테스트용 Mock LLM Manager"""
    
    def __init__(self):
        self.call_count = 0
        self.last_prompt = ""
        self.last_system_prompt = ""
    
    def generate_response(self, system_prompt: str, user_prompt: str, llm_model: str = "gpt-4", max_tokens: int = 400):
        """Mock LLM 응답 생성"""
        self.call_count += 1
        self.last_prompt = user_prompt
        self.last_system_prompt = system_prompt
        
        # 주제에 따라 다른 응답 반환
        if "artificial intelligence" in user_prompt.lower():
            return """
• AI technology is rapidly advancing across multiple sectors
• Machine learning algorithms are becoming more sophisticated
• Ethical considerations around AI deployment are increasing
• Economic impacts include both job displacement and creation
• Regulatory frameworks are still developing globally
"""
        elif "climate change" in user_prompt.lower():
            return """
• Global temperatures have risen by 1.1°C since pre-industrial times
• Carbon emissions continue to increase despite international agreements
• Renewable energy adoption is accelerating worldwide
• Extreme weather events are becoming more frequent
• Economic costs of climate action versus inaction are being debated
"""
        else:
            return """
• Key finding from the provided context
• Important data point highlighted
• Expert opinion or conclusion mentioned
• Relevant evidence or statistics
• Significant implication or outcome
"""


class TestDebateContextManager(unittest.TestCase):
    """DebateContextManager 기본 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MockLLMManager()
        self.context_manager = DebateContextManager(self.mock_llm)
        
        # 테스트용 샘플 컨텍스트
        self.sample_context = """
        Artificial Intelligence (AI) has emerged as one of the most transformative technologies of our time. 
        Recent studies show that AI applications are expanding across healthcare, finance, transportation, and education.
        However, concerns about job displacement, privacy, and algorithmic bias continue to grow.
        Experts estimate that AI could contribute $13 trillion to global GDP by 2030.
        """
        
        self.short_context = "AI is a transformative technology with both benefits and risks."
        
        self.long_context = self.sample_context * 10  # 긴 컨텍스트 시뮬레이션
    
    def test_initialization(self):
        """초기화 테스트"""
        self.assertIsNotNone(self.context_manager.llm_manager)
        self.assertEqual(self.context_manager.max_summary_points, 5)
        self.assertEqual(self.context_manager.short_context_threshold, 3000)
        self.assertEqual(self.context_manager.chunk_size, 1200)
        self.assertEqual(self.context_manager.chunk_overlap, 200)
        
        # 초기 캐시는 비어있음
        self.assertEqual(len(self.context_manager.summaries), 0)
        self.assertEqual(len(self.context_manager.context_bullet_points), 0)
    
    def test_add_context_and_generate_summary(self):
        """컨텍스트 추가 및 요약 생성 테스트"""
        # 컨텍스트 추가
        self.context_manager.add_text_context(self.sample_context, "AI Research Paper")
        
        # 활성 컨텍스트 확인
        self.assertEqual(len(self.context_manager.active_contexts), 1)
        
        # 요약 생성
        result = self.context_manager.generate_summary("The impact of AI on society")
        
        # 결과 검증
        self.assertIsInstance(result, dict)
        self.assertIn("summary", result)
        self.assertGreater(len(result["summary"]), 50)
        
        # LLM 호출 확인
        self.assertGreater(self.mock_llm.call_count, 0)
    
    def test_generate_summary_without_context(self):
        """컨텍스트 없이 요약 생성 시도"""
        result = self.context_manager.generate_summary("Some topic")
        
        # 빈 요약 반환
        self.assertEqual(result["summary"], "")
        
        # LLM 호출되지 않음
        self.assertEqual(self.mock_llm.call_count, 0)
    
    def test_caching_mechanism(self):
        """캐싱 메커니즘 테스트"""
        # 컨텍스트 추가
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        topic = "AI and Society"
        
        # 첫 번째 호출
        result1 = self.context_manager.generate_summary(topic)
        first_call_count = self.mock_llm.call_count
        
        # 두 번째 호출 (캐시에서 가져와야 함)
        result2 = self.context_manager.generate_summary(topic)
        second_call_count = self.mock_llm.call_count
        
        # 결과는 동일하지만 LLM 호출 횟수는 증가하지 않음
        self.assertEqual(result1["summary"], result2["summary"])
        self.assertEqual(first_call_count, second_call_count)
    
    def test_context_type_specialization(self):
        """컨텍스트 타입별 특화 테스트"""
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        # 다른 컨텍스트 타입으로 요약 생성
        academic_result = self.context_manager.generate_summary(
            "AI Research", context_type="academic_paper"
        )
        
        news_result = self.context_manager.generate_summary(
            "AI News", context_type="news_article"
        )
        
        # 모두 성공적으로 생성되어야 함
        self.assertGreater(len(academic_result["summary"]), 50)
        self.assertGreater(len(news_result["summary"]), 50)
    
    def test_get_objective_summary(self):
        """객관적 요약 메서드 테스트"""
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        summary = self.context_manager.get_objective_summary("AI Technology")
        
        # 요약이 생성되어야 함
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 50)
    
    def test_get_context_bullet_points(self):
        """불렛 포인트 추출 테스트"""
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        bullet_points = self.context_manager.get_context_bullet_points()
        
        # 불렛 포인트가 생성되어야 함
        self.assertIsInstance(bullet_points, list)
        self.assertGreater(len(bullet_points), 0)
        self.assertLessEqual(len(bullet_points), 5)  # max_summary_points 제한
        
        # 각 포인트는 문자열이어야 함
        for point in bullet_points:
            self.assertIsInstance(point, str)
            self.assertGreater(len(point), 10)
    
    def test_get_context_for_prompt(self):
        """프롬프트용 컨텍스트 정보 반환 테스트"""
        # 컨텍스트 없는 경우
        empty_result = self.context_manager.get_context_for_prompt()
        self.assertFalse(empty_result["has_context"])
        self.assertEqual(empty_result["summary"], "")
        self.assertEqual(len(empty_result["bullet_points"]), 0)
        
        # 컨텍스트 있는 경우
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        result = self.context_manager.get_context_for_prompt(topic="AI Technology")
        
        self.assertTrue(result["has_context"])
        self.assertGreater(len(result["summary"]), 50)
        self.assertGreater(len(result["bullet_points"]), 0)
        self.assertGreater(result["context_length"], 0)
        self.assertIn(result["summarization_strategy"], ["single", "hierarchical"])
    
    def test_refresh_summaries(self):
        """요약 캐시 새로고침 테스트"""
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        # 요약 생성하여 캐시에 저장
        self.context_manager.generate_summary("AI Topic")
        self.assertGreater(len(self.context_manager.summaries), 0)
        
        # 전체 새로고침
        self.context_manager.refresh_summaries()
        self.assertEqual(len(self.context_manager.summaries), 0)
        self.assertEqual(len(self.context_manager.context_bullet_points), 0)
    
    def test_get_context_stats(self):
        """컨텍스트 통계 정보 테스트"""
        # 빈 상태
        stats = self.context_manager.get_context_stats()
        self.assertEqual(stats["total_contexts"], 0)
        self.assertEqual(stats["active_contexts"], 0)
        
        # 컨텍스트 추가 후
        self.context_manager.add_text_context(self.sample_context, "AI Paper")
        
        stats = self.context_manager.get_context_stats()
        self.assertEqual(stats["total_contexts"], 1)
        self.assertEqual(stats["active_contexts"], 1)
        self.assertGreater(stats["combined_context_length"], 100)
        self.assertIn(stats["summarization_strategy"], ["single", "hierarchical"])


class TestAdaptiveSummarization(unittest.TestCase):
    """적응적 요약 전략 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MockLLMManager()
        self.context_manager = DebateContextManager(self.mock_llm)
    
    def test_short_context_single_strategy(self):
        """짧은 컨텍스트에 대한 단일 요약 전략"""
        short_text = "AI is transformative. It has benefits and risks."
        self.context_manager.add_text_context(short_text, "Short AI Note")
        
        # 짧은 컨텍스트는 단일 전략 사용
        stats = self.context_manager.get_context_stats()
        self.assertEqual(stats["summarization_strategy"], "single")
    
    def test_long_context_hierarchical_strategy(self):
        """긴 컨텍스트에 대한 계층적 요약 전략"""
        # 긴 텍스트 생성 (threshold 초과)
        long_text = "AI technology is advancing rapidly. " * 200  # 약 4000자
        self.context_manager.add_text_context(long_text, "Long AI Document")
        
        # 긴 컨텍스트는 계층적 전략 사용
        stats = self.context_manager.get_context_stats()
        self.assertEqual(stats["summarization_strategy"], "hierarchical")


class TestTextProcessing(unittest.TestCase):
    """텍스트 처리 기능 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MockLLMManager()
        self.context_manager = DebateContextManager(self.mock_llm)
    
    def test_bullet_point_extraction(self):
        """불렛 포인트 추출 기능 테스트"""
        # 다양한 불렛 포인트 형식 테스트
        text_with_bullets = """
        • First bullet point
        - Second bullet point  
        * Third bullet point
        1. Fourth bullet point
        Regular sentence without bullet.
        • Fifth bullet point
        """
        
        bullet_points = self.context_manager._extract_bullet_points(text_with_bullets)
        
        # 불렛 포인트가 추출되어야 함
        self.assertGreater(len(bullet_points), 3)
        
        # 모든 추출된 포인트는 • 로 시작해야 함
        for point in bullet_points:
            self.assertTrue(point.startswith("• "))
    
    def test_chunk_splitting(self):
        """텍스트 청킹 기능 테스트"""
        # 긴 텍스트 생성
        long_text = "This is a sentence. " * 200  # 약 4000자
        
        chunks = self.context_manager._split_into_chunks(long_text)
        
        # 여러 청크로 분할되어야 함
        self.assertGreater(len(chunks), 1)
        
        # 각 청크는 적절한 크기여야 함
        for chunk in chunks:
            self.assertLessEqual(len(chunk), self.context_manager.chunk_size + 200)  # 약간의 여유
    
    def test_token_estimation(self):
        """토큰 수 추정 기능 테스트"""
        text = "This is a test text for token estimation."
        
        estimated_tokens = self.context_manager._estimate_tokens(text)
        
        # 대략적인 토큰 수 (1 토큰 ≈ 4자)
        expected_tokens = len(text) // 4
        self.assertEqual(estimated_tokens, expected_tokens)


class TestBackwardCompatibility(unittest.TestCase):
    """하위 호환성 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.mock_llm = MockLLMManager()
        self.context_manager = DebateContextManager(self.mock_llm)
    
    def test_generate_debate_summary_alias(self):
        """generate_debate_summary 별칭 메서드 테스트"""
        self.context_manager.add_text_context("AI content", "AI Paper")
        
        # 새 메서드
        new_result = self.context_manager.generate_summary("AI Topic")
        
        # 별칭 메서드 (하위 호환성)
        old_result = self.context_manager.generate_debate_summary("AI Topic")
        
        # 결과가 동일해야 함
        self.assertEqual(new_result["summary"], old_result["summary"])


if __name__ == '__main__':
    unittest.main(verbosity=2) 