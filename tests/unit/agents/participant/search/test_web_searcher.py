"""
WebSearcher 단위 테스트

WebSearcher 클래스의 기능을 테스트합니다.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.participant.search.web_searcher import WebSearcher


class TestWebSearcher(unittest.TestCase):
    """WebSearcher 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = {
            "web_crawling": False,
            "search_provider": "google",
            "max_results": 3,
            "embedding_model": "all-MiniLM-L6-v2"
        }
        self.web_searcher = WebSearcher(self.config)
    
    def test_initialization(self):
        """초기화 테스트"""
        self.assertEqual(self.web_searcher.web_crawling, False)
        self.assertEqual(self.web_searcher.search_provider, "google")
        self.assertEqual(self.web_searcher.max_results, 3)
        self.assertEqual(self.web_searcher.embedding_model, "all-MiniLM-L6-v2")
        self.assertIsNone(self.web_searcher.web_retriever)
    
    def test_get_source_type(self):
        """소스 타입 반환 테스트"""
        self.assertEqual(self.web_searcher._get_source_type(), "web")
    
    def test_get_search_stats(self):
        """검색 통계 정보 반환 테스트"""
        stats = self.web_searcher.get_search_stats()
        
        expected_keys = [
            "search_type", "crawling_enabled", "search_provider", 
            "max_results", "embedding_model"
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        self.assertEqual(stats["search_type"], "web")
        self.assertEqual(stats["crawling_enabled"], False)
        self.assertEqual(stats["search_provider"], "google")
    
    @patch('src.agents.participant.search.web_searcher.logger')
    def test_search_with_no_retriever_import_error(self, mock_logger):
        """WebSearchRetriever import 실패 시 테스트"""
        with patch('src.agents.participant.search.web_searcher.WebSearcher._initialize_web_retriever_basic', 
                   side_effect=ImportError("No module named 'bs4'")):
            
            result = self.web_searcher.search("test query")
            
            self.assertEqual(result, [])
            mock_logger.warning.assert_called()
    
    @patch('src.agents.participant.search.web_searcher.WebSearcher._initialize_web_retriever_basic')
    def test_search_snippet_only_success(self, mock_init):
        """스니펫 검색 성공 테스트"""
        # Mock WebSearchRetriever
        mock_retriever = Mock()
        mock_retriever.search.return_value = [
            {
                "title": "Test Title",
                "snippet": "Test content",
                "url": "https://example.com",
            }
        ]
        self.web_searcher.web_retriever = mock_retriever
        
        result = self.web_searcher.search("test query")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Test Title")
        self.assertEqual(result[0]["content"], "Test content")
        self.assertEqual(result[0]["url"], "https://example.com")
        self.assertEqual(result[0]["source_type"], "web")
        self.assertEqual(result[0]["relevance_score"], 0.85)
    
    @patch('src.agents.participant.search.web_searcher.WebSearcher._initialize_web_retriever_advanced')
    def test_search_with_crawling_success(self, mock_init):
        """크롤링 검색 성공 테스트"""
        # 크롤링 활성화
        self.web_searcher.web_crawling = True
        
        # Mock WebSearchRetriever
        mock_retriever = Mock()
        mock_retriever.retrieve_and_extract.return_value = [
            {
                "text": "Extracted content",
                "metadata": {
                    "title": "Web Content",
                    "url": "https://example.com",
                    "domain": "example.com",
                    "word_count": 100
                },
                "similarity": 0.9,
                "score": 0.85
            }
        ]
        self.web_searcher.web_retriever = mock_retriever
        
        result = self.web_searcher.search("test query")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Web Content")
        self.assertEqual(result[0]["content"], "Extracted content")
        self.assertEqual(result[0]["url"], "https://example.com")
        self.assertEqual(result[0]["source_type"], "web")
        self.assertEqual(result[0]["relevance_score"], 0.9)
    
    @patch('src.agents.participant.search.web_searcher.WebSearcher._initialize_web_retriever_basic')
    def test_search_no_results(self, mock_init):
        """검색 결과 없음 테스트"""
        # Mock WebSearchRetriever
        mock_retriever = Mock()
        mock_retriever.search.return_value = []
        self.web_searcher.web_retriever = mock_retriever
        
        result = self.web_searcher.search("test query")
        
        self.assertEqual(result, [])
    
    @patch('src.agents.participant.search.web_searcher.WebSearcher._initialize_web_retriever_basic')
    def test_search_exception_handling(self, mock_init):
        """검색 중 예외 발생 테스트"""
        # Mock WebSearchRetriever가 예외 발생
        mock_retriever = Mock()
        mock_retriever.search.side_effect = Exception("Search failed")
        self.web_searcher.web_retriever = mock_retriever
        
        result = self.web_searcher.search("test query")
        
        self.assertEqual(result, [])
    
    def test_format_results(self):
        """결과 포맷팅 테스트"""
        raw_results = [
            {
                "title": "Test Title",
                "content": "Test content",
                "url": "https://example.com",
                "relevance_score": 0.8
            }
        ]
        
        formatted = self.web_searcher._format_results(raw_results)
        
        self.assertEqual(len(formatted), 1)
        result = formatted[0]
        
        self.assertEqual(result["title"], "Test Title")
        self.assertEqual(result["content"], "Test content")
        self.assertEqual(result["url"], "https://example.com")
        self.assertEqual(result["source_type"], "web")
        self.assertEqual(result["relevance_score"], 0.8)
        self.assertIn("metadata", result)


class TestWebSearcherIntegration(unittest.TestCase):
    """WebSearcher 통합 테스트 (실제 의존성 사용)"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = {
            "web_crawling": False,
            "search_provider": "google",
            "max_results": 1,
            "embedding_model": "all-MiniLM-L6-v2"
        }
    
    @unittest.skip("실제 API 호출이 필요한 테스트 - 필요시 활성화")
    def test_real_web_search(self):
        """실제 웹 검색 테스트 (API 키 필요)"""
        web_searcher = WebSearcher(self.config)
        result = web_searcher.search("artificial intelligence")
        
        # API 키가 없으면 빈 결과 반환
        self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main() 