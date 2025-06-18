"""
실제 URL과 LLM을 사용한 통합 테스트

Yale Journal URL에서 실제로 불렛포인트를 제대로 추출하는지 확인합니다.
"""

import unittest
import sys
import os
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.dialogue.context.debate_context_manager import DebateContextManager
from src.models.llm.llm_manager import LLMManager


class TestURLIntegration(unittest.TestCase):
    """실제 URL과 LLM을 사용한 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.cnbc_url = "https://www.cnbc.com/2025/06/18/iran-threatens-irreparable-damage-if-us-enters-israel-conflict.html"
        
        # OpenAI API 키 확인
        if not os.environ.get('OPENAI_API_KEY'):
            self.skipTest("OpenAI API key not found - set OPENAI_API_KEY environment variable")
    
    def test_cnbc_news_bullet_point_extraction(self):
        """CNBC 뉴스에서 실제 불렛포인트 추출 테스트"""
        print(f"\n=== CNBC 뉴스 불렛포인트 추출 테스트 ===")
        print(f"URL: {self.cnbc_url}")
        
        try:
            # 1. URL에서 컨텐츠 추출
            print("\n📄 URL 컨텐츠 추출 중...")
            content = self._extract_url_content(self.cnbc_url)
            print(f"✅ 컨텐츠 추출 완료: {len(content):,}자")
            
            # 컨텐츠가 실제로 추출되었는지 확인
            self.assertGreater(len(content), 500, "추출된 컨텐츠가 너무 짧음")
            
            # CNBC 뉴스 관련 키워드 포함 확인
            content_lower = content.lower()
            self.assertTrue(
                any(keyword in content_lower for keyword in ["iran", "israel", "conflict", "trump"]),
                "CNBC 뉴스 관련 키워드가 포함되지 않음"
            )
            
            # 2. ContextManager로 객관적 요약 생성
            print("\n📊 객관적 요약 생성 중...")
            llm_manager = LLMManager()
            context_manager = DebateContextManager(llm_manager)
            
            # 컨텐츠를 컨텍스트로 추가
            context_manager.add_text_context(content, "CNBC News Article")
            
            # 토론 주제 설정
            topic = "Should the U.S. take military action in Middle East conflicts?"
            
            # 객관적 요약 생성
            summary = context_manager.get_objective_summary(
                topic=topic,
                context_type="news_article"
            )
            
            print("✅ 객관적 요약 생성 완료")
            
            # 3. 결과 검증
            self._validate_summary_results(summary, content, topic)
            
            # 4. 불렛포인트 형태 확인
            bullet_points = self._extract_bullet_points_from_summary(summary)
            self._validate_bullet_points(bullet_points)
            
            # 5. 결과 출력
            self._print_results(content, summary, bullet_points)
            
            print("\n✅ 모든 검증 완료!")
            
        except Exception as e:
            self.fail(f"통합 테스트 실패: {str(e)}")
    
    def _extract_url_content(self, url: str) -> str:
        """URL에서 텍스트 컨텐츠 추출"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 스크립트, 스타일 태그 제거
            for script in soup(["script", "style"]):
                script.extract()
            
            text = soup.get_text(separator='\n')
            
            # 여러 줄바꿈 정리
            import re
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\s{3,}', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"URL 처리 실패: {str(e)}")
    
    def _validate_summary_results(self, summary: str, original_content: str, topic: str):
        """요약 결과 검증"""
        # 요약이 생성되었는지 확인
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 100, "요약이 너무 짧음")
        self.assertLess(len(summary), len(original_content), "요약이 원본보다 길면 안됨")
        
        # 핵심 키워드 포함 확인 (뉴스 기사 키워드로 변경)
        summary_lower = summary.lower()
        expected_keywords = ["iran", "israel", "conflict", "military", "trump", "khamenei"]
        found_keywords = [kw for kw in expected_keywords if kw in summary_lower]
        
        self.assertGreater(len(found_keywords), 1, 
                         f"관련 키워드가 충분히 포함되지 않음. 발견: {found_keywords}")
    
    def _extract_bullet_points_from_summary(self, summary: str) -> list:
        """요약에서 불렛포인트 추출"""
        import re
        
        bullet_points = []
        for line in summary.split('\n'):
            line = line.strip()
            if line and (line.startswith('•') or line.startswith('-') or line.startswith('*')):
                bullet_points.append(line)
        
        return bullet_points
    
    def _validate_bullet_points(self, bullet_points: list):
        """불렛포인트 검증 (뉴스 기사용)"""
        # 적절한 개수의 불렛포인트
        self.assertGreater(len(bullet_points), 2, "최소 3개 이상의 불렛포인트가 필요")
        self.assertLess(len(bullet_points), 8, "불렛포인트가 너무 많음")
        
        # 각 불렛포인트의 내용 검증 (뉴스 기사 특성 고려)
        for point in bullet_points:
            self.assertGreater(len(point), 15, f"불렛포인트가 너무 짧음: {point}")
            self.assertLess(len(point), 500, f"불렛포인트가 너무 김: {point}")  # 뉴스 기사도 상세한 설명 허용
    
    def _print_results(self, content: str, summary: str, bullet_points: list):
        """결과 출력"""
        print(f"\n=== 결과 요약 ===")
        print(f"원본 텍스트 길이: {len(content):,}자")
        print(f"요약 텍스트 길이: {len(summary):,}자")
        print(f"압축 비율: {len(summary)/len(content)*100:.1f}%")
        print(f"불렛포인트 개수: {len(bullet_points)}개")
        
        print(f"\n=== 생성된 요약 ===")
        # 요약이 길면 일부만 출력
        if len(summary) > 1000:
            print(summary[:1000] + "\n... (요약 계속)")
        else:
            print(summary)
        
        print(f"\n=== 추출된 불렛포인트 ===")
        for i, point in enumerate(bullet_points, 1):
            print(f"{i}. {point}")


class TestURLExtractionOnly(unittest.TestCase):
    """URL 추출만 테스트 (LLM 없이)"""
    
    def test_cnbc_content_extraction(self):
        """CNBC 컨텐츠 추출만 테스트"""
        url = "https://www.cnbc.com/2025/06/18/iran-threatens-irreparable-damage-if-us-enters-israel-conflict.html"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # 기본 검증
            self.assertGreater(len(text), 1000)
            self.assertIn("iran", text.lower())
            self.assertIn("israel", text.lower())
            
            print(f"✅ CNBC 컨텐츠 추출 성공: {len(text):,}자")
            
        except Exception as e:
            self.fail(f"URL 컨텐츠 추출 실패: {str(e)}")


if __name__ == '__main__':
    # API 키 확인
    if not os.environ.get('OPENAI_API_KEY'):
        print("⚠️  OpenAI API key not found")
        print("Set OPENAI_API_KEY environment variable to run LLM tests")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        print("\nRunning URL extraction test only...")
        
        # LLM 없이 URL 추출만 테스트
        suite = unittest.TestSuite()
        suite.addTest(TestURLExtractionOnly('test_cnbc_content_extraction'))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        print("✅ OpenAI API key found")
        print("Running full integration test...")
        
        # 전체 테스트 실행
        unittest.main(verbosity=2) 