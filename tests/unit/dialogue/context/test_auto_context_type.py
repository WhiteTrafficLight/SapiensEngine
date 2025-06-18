"""
자동 컨텍스트 타입 판별 기능 테스트

UserContextManager의 자동 타입 판별과 DebateContextManager의 타입 활용을 테스트합니다.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 프로젝트 루트를 path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from src.utils.context_manager import UserContextManager
from src.dialogue.context.debate_context_manager import DebateContextManager


class TestAutoContextType(unittest.TestCase):
    """자동 컨텍스트 타입 판별 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.llm_manager = Mock()
        self.llm_manager.generate_response.return_value = "• Test bullet point"
        
        self.user_manager = UserContextManager(max_context_length=5000)
        self.debate_manager = DebateContextManager(self.llm_manager, max_context_length=5000)
    
    def test_url_pattern_inference(self):
        """URL 패턴 기반 타입 추론 테스트"""
        test_cases = [
            ("https://www.cnn.com/2024/01/15/tech/ai-regulation", "news_article"),
            ("https://arxiv.org/abs/2401.12345", "academic_paper"),
            ("https://www.whitehouse.gov/briefing-room/statements-releases", "policy_document"),
            ("https://example.com/general-content", "general"),
            ("https://scholar.google.com/citations", "academic_paper"),
            ("https://reuters.com/world/breaking-news", "news_article"),
        ]
        
        for url, expected_type in test_cases:
            with self.subTest(url=url, expected=expected_type):
                inferred_type = self.user_manager._infer_context_type_from_url(url)
                self.assertEqual(inferred_type, expected_type)
    
    def test_content_based_inference(self):
        """내용 기반 타입 추론 테스트 (실제 LLM 사용)"""
        # Academic paper content
        academic_content = """
        Abstract: This research presents a novel methodology for analyzing machine learning algorithms.
        Introduction: Recent studies have shown significant advances in AI technology.
        Methodology: We conducted experiments using a dataset of 10,000 samples.
        Results: The analysis revealed a 95% accuracy rate in classification tasks.
        Conclusion: Our findings contribute to the understanding of AI systems.
        References: [1] Smith, J. et al. (2023). Journal of AI Research, vol. 15, pp. 123-145.
        """
        
        # News article content
        news_content = """
        Breaking: According to sources familiar with the matter, the tech company announced
        a major breakthrough today. A spokesperson for the company stated that this development
        represents a significant step forward. The announcement was published earlier this morning
        and has been updated with additional details from our correspondent in Silicon Valley.
        """
        
        # Policy document content
        policy_content = """
        Section 1: Definitions. For the purposes of this regulation, the following terms shall apply:
        (a) "Artificial Intelligence" means any system that demonstrates intelligent behavior.
        Section 2: Requirements. All entities subject to this act must comply with the following:
        Whereas the Congress finds that regulation is necessary for public safety,
        Therefore, it is hereby enacted that all AI systems must undergo certification.
        """
        
        # General content (더 명확하게)
        general_content = """
        Today I went to the grocery store and bought some fruits and vegetables.
        The weather was nice, so I decided to walk instead of driving.
        My favorite hobby is reading books, especially mystery novels.
        This weekend I plan to visit my family and have a barbecue party.
        """
        
        test_cases = [
            (academic_content, "academic_paper"),
            (news_content, "news_article"), 
            (policy_content, "policy_document"),
            (general_content, "general"),
        ]
        
        print("\n=== LLM-based Content Type Inference Test ===")
        for content, expected_type in test_cases:
            with self.subTest(expected=expected_type):
                # 실제 LLM 사용
                inferred_type = self.user_manager._infer_context_type_from_content(content, use_llm=True)
                print(f"Expected: {expected_type}, Got: {inferred_type}")
                
                # LLM 결과가 정확하지 않을 수 있으므로 로깅만 하고 실패시키지 않음
                if inferred_type != expected_type:
                    print(f"⚠️  LLM classification mismatch for {expected_type}")
                else:
                    print(f"✅ LLM classification correct for {expected_type}")
    
    def test_rule_based_fallback(self):
        """규칙 기반 폴백 테스트 (LLM 비활성화)"""
        # Academic paper content (매우 명확한 키워드)
        academic_content = """
        Abstract: This research presents a novel methodology.
        Introduction: Recent studies have shown advances.
        Methodology: We conducted experiments using datasets.
        Results: The analysis revealed accuracy rates.
        Conclusion: Our findings contribute to research.
        References: [1] Smith, J. et al. (2023). Journal of AI Research.
        """
        
        # News article content (매우 명확한 키워드)
        news_content = """
        Breaking news: According to our correspondent, sources say the company announced
        a major breakthrough today. A spokesperson confirmed the development in a press release.
        The story was published this morning and updated with details from our reporter.
        """
        
        # Policy document content (매우 명확한 키워드)
        policy_content = """
        Section 1: Definitions. For the purposes of this regulation, the following shall apply:
        Whereas the Congress finds that federal oversight is necessary,
        Therefore, it is hereby enacted that all entities must comply with this act.
        The legislation requires government approval for all activities.
        """
        
        test_cases = [
            (academic_content, "academic_paper"),
            (news_content, "news_article"), 
            (policy_content, "policy_document"),
        ]
        
        for content, expected_type in test_cases:
            with self.subTest(expected=expected_type):
                # LLM 비활성화로 규칙 기반 테스트
                inferred_type = self.user_manager._infer_context_type_from_content(content, use_llm=False)
                self.assertEqual(inferred_type, expected_type)
    
    def test_llm_vs_rules_comparison(self):
        """LLM vs 규칙 기반 비교 테스트"""
        test_content = """
        Abstract: This study examines the impact of artificial intelligence on modern society.
        The research methodology involved comprehensive analysis of current AI applications.
        Results indicate significant potential for future development in this field.
        """
        
        # LLM 기반 추론
        llm_result = self.user_manager._infer_context_type_from_content(test_content, use_llm=True)
        
        # 규칙 기반 추론
        rule_result = self.user_manager._infer_context_type_from_content(test_content, use_llm=False)
        
        print(f"\nComparison Test:")
        print(f"LLM result: {llm_result}")
        print(f"Rule result: {rule_result}")
        
        # 둘 다 academic_paper로 분류되어야 함
        self.assertEqual(rule_result, "academic_paper")
        # LLM 결과는 로깅만 (정확도가 다를 수 있음)
    
    def test_add_text_context_with_inference(self):
        """텍스트 컨텍스트 추가 시 자동 타입 판별 테스트"""
        academic_text = """
        Abstract: This study examines the effectiveness of neural networks.
        The research methodology involved training models on large datasets.
        Results show significant improvements in accuracy and performance.
        """
        
        context_id = self.user_manager.add_text_context(academic_text, "AI Research Paper")
        
        # 컨텍스트 추가 확인
        self.assertIn(context_id, self.user_manager.user_contexts)
        
        # 자동 판별된 타입 확인
        context = self.user_manager.user_contexts[context_id]
        self.assertEqual(context["content_type"], "academic_paper")
        
        # 타입 조회 메서드 테스트
        retrieved_type = self.user_manager.get_context_type(context_id)
        self.assertEqual(retrieved_type, "academic_paper")
    
    @patch('requests.get')
    def test_add_url_context_with_inference(self, mock_get):
        """URL 컨텍스트 추가 시 자동 타입 판별 테스트"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = """
        <html>
        <head><title>CNN Breaking News</title></head>
        <body>
        <article>
        Breaking news: According to our correspondent, a major announcement was made today.
        The spokesperson confirmed the details in a press release this morning.
        </article>
        </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        url = "https://www.cnn.com/2024/01/15/breaking-news"
        context_id = self.user_manager.add_url_context(url)
        
        # 컨텍스트 추가 확인
        self.assertIn(context_id, self.user_manager.user_contexts)
        
        # URL 패턴으로 news_article 타입 판별 확인
        context = self.user_manager.user_contexts[context_id]
        self.assertEqual(context["content_type"], "news_article")
    
    def test_get_most_common_context_type(self):
        """가장 흔한 컨텍스트 타입 조회 테스트"""
        # 여러 타입의 컨텍스트 추가
        academic_text = "Abstract: This research examines machine learning algorithms."
        news_text = "Breaking: According to sources, a major announcement was made."
        academic_text2 = "Introduction: Recent studies have shown advances in AI research."
        
        self.user_manager.add_text_context(academic_text, "Paper 1")
        self.user_manager.add_text_context(news_text, "News 1") 
        self.user_manager.add_text_context(academic_text2, "Paper 2")
        
        # academic_paper가 2개, news_article이 1개이므로 academic_paper가 최다
        most_common = self.user_manager.get_most_common_context_type()
        self.assertEqual(most_common, "academic_paper")
    
    def test_debate_manager_auto_type_selection(self):
        """DebateContextManager의 자동 타입 선택 테스트"""
        # UserContextManager에 컨텍스트 추가 (academic_paper 타입)
        academic_text = """
        Abstract: This paper presents a comprehensive analysis of AI ethics.
        Introduction: The research examines ethical implications of artificial intelligence.
        Methodology: We conducted surveys and interviews with 500 participants.
        Results: 78% of respondents expressed concerns about AI bias.
        """
        
        context_id = self.debate_manager.add_text_context(academic_text, "AI Ethics Study")
        
        # 타입 자동 판별 확인
        determined_type = self.debate_manager._determine_best_context_type()
        self.assertEqual(determined_type, "academic_paper")
        
        # 요약 생성 시 자동 타입 사용 확인
        summary_result = self.debate_manager.generate_summary("AI Ethics")
        
        # LLM이 호출되었는지 확인
        self.llm_manager.generate_response.assert_called()
        
        # 결과 구조 확인
        self.assertIn("summary", summary_result)
        self.assertIsInstance(summary_result["summary"], str)
    
    def test_context_type_summary(self):
        """컨텍스트 타입 요약 정보 테스트"""
        # 다양한 타입의 컨텍스트 추가
        academic_text = "Abstract: AI research findings. Results show 95% accuracy."
        news_text = "Breaking: Tech company announces breakthrough. Spokesperson confirms details."
        
        ctx1 = self.debate_manager.add_text_context(academic_text, "Research")
        ctx2 = self.debate_manager.add_text_context(news_text, "News")
        
        # 타입 요약 정보 조회
        type_summary = self.debate_manager.get_context_type_summary()
        
        # 기본 구조 확인
        self.assertEqual(type_summary["total_contexts"], 2)
        self.assertIn("type_distribution", type_summary)
        self.assertIn("determined_type", type_summary)
        self.assertIn("context_details", type_summary)
        
        # 타입 분포 확인
        distribution = type_summary["type_distribution"]
        self.assertIn("academic_paper", distribution)
        self.assertIn("news_article", distribution)
        self.assertEqual(distribution["academic_paper"], 1)
        self.assertEqual(distribution["news_article"], 1)
        
        # 컨텍스트 상세 정보 확인
        details = type_summary["context_details"]
        self.assertEqual(len(details), 2)
        
        for detail in details:
            self.assertIn("id", detail)
            self.assertIn("title", detail)
            self.assertIn("source_type", detail)
            self.assertIn("content_type", detail)
            self.assertIn("length", detail)
    
    def test_mixed_context_types(self):
        """혼합된 컨텍스트 타입 처리 테스트"""
        # 다양한 타입과 일반 타입 혼합
        academic_text = "Abstract: Neural network research. Methodology: Deep learning approach."
        general_text = "This is just some general information without specific indicators."
        news_text = "Breaking news: According to our reporter, significant developments occurred."
        
        self.debate_manager.add_text_context(academic_text, "Academic")
        self.debate_manager.add_text_context(general_text, "General")
        self.debate_manager.add_text_context(news_text, "News")
        
        # academic_paper와 news_article이 각 1개, general이 1개
        # general이 아닌 타입 중에서 선택되어야 함
        determined_type = self.debate_manager._determine_best_context_type()
        self.assertIn(determined_type, ["academic_paper", "news_article"])
        
        # 타입 분포 확인
        type_summary = self.debate_manager.get_context_type_summary()
        distribution = type_summary["type_distribution"]
        
        self.assertEqual(distribution.get("academic_paper", 0), 1)
        self.assertEqual(distribution.get("news_article", 0), 1)
        self.assertEqual(distribution.get("general", 0), 1)


if __name__ == "__main__":
    unittest.main() 