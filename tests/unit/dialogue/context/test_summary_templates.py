"""
SummaryTemplates 클래스 유닛 테스트

객관적인 요약 템플릿 기능을 테스트합니다.
"""

import unittest
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.dialogue.context.summary_templates import SummaryTemplates


class TestSummaryTemplates(unittest.TestCase):
    """SummaryTemplates 클래스 테스트"""
    
    def test_get_base_template(self):
        """기본 템플릿 반환 테스트"""
        template = SummaryTemplates.get_base_template()
        
        # 템플릿이 문자열이고 비어있지 않음
        self.assertIsInstance(template, str)
        self.assertGreater(len(template), 100)
        
        # 필수 플레이스홀더 포함 확인
        self.assertIn("{context}", template)
        self.assertIn("{topic}", template)
        
        # 객관적 요약 관련 키워드 포함 확인
        template_lower = template.lower()
        self.assertIn("objective", template_lower)
        self.assertIn("bullet point", template_lower)
        self.assertIn("factual", template_lower)
    
    def test_get_template_without_context_type(self):
        """컨텍스트 타입 없이 템플릿 요청"""
        template = SummaryTemplates.get_template()
        base_template = SummaryTemplates.get_base_template()
        
        # 기본 템플릿과 동일해야 함
        self.assertEqual(template, base_template)
    
    def test_get_template_with_academic_paper(self):
        """학술 논문 타입 템플릿 테스트"""
        template = SummaryTemplates.get_template(context_type="academic_paper")
        
        # 학술 논문 관련 키워드 포함 확인
        template_lower = template.lower()
        self.assertIn("academic", template_lower)
        self.assertIn("research", template_lower)
        self.assertIn("methodological", template_lower)
        
        # 필수 플레이스홀더 포함 확인
        self.assertIn("{context}", template)
        self.assertIn("{topic}", template)
    
    def test_get_template_with_news_article(self):
        """뉴스 기사 타입 템플릿 테스트"""
        template = SummaryTemplates.get_template(context_type="news_article")
        
        # 뉴스 관련 키워드 포함 확인
        template_lower = template.lower()
        self.assertIn("news", template_lower)
        self.assertIn("article", template_lower)
        self.assertIn("stakeholder", template_lower)
        
        # 필수 플레이스홀더 포함 확인
        self.assertIn("{context}", template)
        self.assertIn("{topic}", template)
    
    def test_get_template_with_policy_document(self):
        """정책 문서 타입 템플릿 테스트"""
        template = SummaryTemplates.get_template(context_type="policy_document")
        
        # 정책 관련 키워드 포함 확인
        template_lower = template.lower()
        self.assertIn("policy", template_lower)
        self.assertIn("implementation", template_lower)
        
        # 필수 플레이스홀더 포함 확인
        self.assertIn("{context}", template)
        self.assertIn("{topic}", template)
    
    def test_get_template_with_invalid_context_type(self):
        """존재하지 않는 컨텍스트 타입으로 요청"""
        template = SummaryTemplates.get_template(context_type="invalid_type")
        base_template = SummaryTemplates.get_base_template()
        
        # 기본 템플릿으로 폴백해야 함
        self.assertEqual(template, base_template)
    
    def test_template_formatting(self):
        """템플릿 포맷팅 테스트"""
        template = SummaryTemplates.get_template()
        
        # 샘플 데이터로 포맷팅 시도
        sample_context = "This is a sample context about artificial intelligence."
        sample_topic = "AI and Society"
        
        try:
            formatted = template.format(context=sample_context, topic=sample_topic)
            
            # 포맷팅된 결과에 샘플 데이터 포함 확인
            self.assertIn(sample_context, formatted)
            self.assertIn(sample_topic, formatted)
            
            # 플레이스홀더가 모두 교체되었는지 확인
            self.assertNotIn("{context}", formatted)
            self.assertNotIn("{topic}", formatted)
            
        except KeyError as e:
            self.fail(f"Template formatting failed: {e}")
    
    def test_all_context_types_have_templates(self):
        """모든 정의된 컨텍스트 타입에 템플릿이 있는지 확인"""
        expected_types = ["academic_paper", "news_article", "policy_document"]
        
        for context_type in expected_types:
            with self.subTest(context_type=context_type):
                template = SummaryTemplates.get_template(context_type=context_type)
                
                # 템플릿이 존재하고 기본 템플릿과 다름
                self.assertIsInstance(template, str)
                self.assertGreater(len(template), 100)
                
                # 기본 템플릿과 다른지 확인 (특화된 템플릿인지)
                base_template = SummaryTemplates.get_base_template()
                self.assertNotEqual(template, base_template)
    
    def test_template_structure_consistency(self):
        """모든 템플릿의 구조 일관성 확인"""
        all_types = [None, "academic_paper", "news_article", "policy_document"]
        
        for context_type in all_types:
            with self.subTest(context_type=context_type):
                template = SummaryTemplates.get_template(context_type=context_type)
                
                # 모든 템플릿은 불렛 포인트 형식을 언급해야 함
                self.assertTrue(
                    "•" in template or "bullet" in template.lower(),
                    f"Template for {context_type} should mention bullet points"
                )
                
                # 모든 템플릿은 객관적 요약을 지향해야 함
                template_lower = template.lower()
                objective_keywords = ["objective", "neutral", "factual"]
                has_objective_keyword = any(kw in template_lower for kw in objective_keywords)
                self.assertTrue(
                    has_objective_keyword,
                    f"Template for {context_type} should promote objectivity"
                )


class TestTemplateContent(unittest.TestCase):
    """템플릿 내용 상세 테스트"""
    
    def test_base_template_content(self):
        """기본 템플릿 내용 검증"""
        template = SummaryTemplates.get_base_template()
        
        # 요약 지침 포함 확인
        expected_guidelines = [
            "3-5 key bullet points",
            "factual information",
            "1-2 sentences maximum"
        ]
        
        for guideline in expected_guidelines:
            self.assertIn(guideline, template)
    
    def test_academic_paper_specialization(self):
        """학술 논문 템플릿 특화 기능 확인"""
        template = SummaryTemplates.get_template(context_type="academic_paper")
        
        # 학술 논문 특화 요소들
        academic_elements = [
            "research findings",
            "methodological",
            "statistical evidence",
            "expert conclusions",
            "limitations"
        ]
        
        for element in academic_elements:
            self.assertIn(element, template.lower())
    
    def test_news_article_specialization(self):
        """뉴스 기사 템플릿 특화 기능 확인"""
        template = SummaryTemplates.get_template(context_type="news_article")
        
        # 뉴스 기사 특화 요소들
        news_elements = [
            "core facts",
            "events reported",
            "perspectives",
            "current developments",
            "real-world impact"
        ]
        
        for element in news_elements:
            self.assertIn(element, template.lower())
    
    def test_policy_document_specialization(self):
        """정책 문서 템플릿 특화 기능 확인"""
        template = SummaryTemplates.get_template(context_type="policy_document")
        
        # 정책 문서 특화 요소들
        policy_elements = [
            "policy positions",
            "implementation",
            "expected outcomes",
            "stakeholder impact"
        ]
        
        for element in policy_elements:
            self.assertIn(element, template.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2) 