"""
RAGSearchManager 단위 테스트

RAGSearchManager 클래스의 통합 검색 기능을 테스트합니다.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.participant.search.rag_search_manager import RAGSearchManager


class TestRAGSearchManager(unittest.TestCase):
    """RAGSearchManager 클래스 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = {
            "max_total_results": 10,
            "source_weights": {
                "web": 0.4,
                "vector": 0.3,
                "philosopher": 0.3
            },
            "web_search": {
                "web_crawling": False,
                "search_provider": "google",
                "max_results": 3
            },
            "vector_search": {
                "db_path": "./vectordb",
                "collection_name": "default",
                "search_algorithm": "simple_top_k"
            },
            "philosopher_search": {
                "db_path": "./vectordb",
                "philosopher_collection": "philosopher_works"
            }
        }
        self.manager = RAGSearchManager(self.config)
    
    def test_initialization(self):
        """초기화 테스트"""
        self.assertEqual(self.manager.max_total_results, 10)
        self.assertEqual(self.manager.source_weights["web"], 0.4)
        self.assertEqual(self.manager.source_weights["vector"], 0.3)
        self.assertEqual(self.manager.source_weights["philosopher"], 0.3)
        
        # 검색 클래스들이 초기화되었는지 확인
        self.assertIn("web", self.manager.searchers)
        self.assertIn("vector", self.manager.searchers)
        self.assertIn("philosopher", self.manager.searchers)
    
    @patch('src.agents.participant.search.rag_search_manager.WebSearcher')
    @patch('src.agents.participant.search.rag_search_manager.VectorSearcher')
    @patch('src.agents.participant.search.rag_search_manager.PhilosopherSearcher')
    def test_search_all_sources(self, mock_phil, mock_vector, mock_web):
        """모든 소스에서 검색 테스트"""
        # Mock 검색 결과 설정
        mock_web.return_value.search.return_value = [
            {"title": "Web Result", "content": "Web content", "source_type": "web", "relevance_score": 0.8, "url": "http://web.com"}
        ]
        mock_vector.return_value.search.return_value = [
            {"title": "Vector Result", "content": "Vector content", "source_type": "vector", "relevance_score": 0.9, "url": "http://vector.com"}
        ]
        mock_phil.return_value.search.return_value = [
            {"title": "Phil Result", "content": "Phil content", "source_type": "philosopher", "relevance_score": 0.7, "url": "http://phil.com"}
        ]
        
        # 새로운 매니저 인스턴스 생성 (Mock이 적용되도록)
        manager = RAGSearchManager(self.config)
        
        result = manager.search_all_sources("test query")
        
        self.assertEqual(len(result), 3)
        
        # 결과가 weighted_score 순으로 정렬되었는지 확인
        # web: 0.8 * 0.4 = 0.32, vector: 0.9 * 0.3 = 0.27, philosopher: 0.7 * 0.3 = 0.21
        self.assertEqual(result[0]["search_source"], "web")  # 0.32
        self.assertEqual(result[1]["search_source"], "vector")  # 0.27
        self.assertEqual(result[2]["search_source"], "philosopher")  # 0.21
    
    @patch('src.agents.participant.search.rag_search_manager.WebSearcher')
    def test_search_web_only(self, mock_web):
        """웹 검색만 테스트"""
        mock_web.return_value.search.return_value = [
            {"title": "Web Result", "content": "Web content", "source_type": "web", "relevance_score": 0.8}
        ]
        
        manager = RAGSearchManager(self.config)
        result = manager.search_web_only("test query")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_type"], "web")
    
    @patch('src.agents.participant.search.rag_search_manager.VectorSearcher')
    def test_search_vector_only(self, mock_vector):
        """벡터 검색만 테스트"""
        mock_vector.return_value.search.return_value = [
            {"title": "Vector Result", "content": "Vector content", "source_type": "vector", "relevance_score": 0.9}
        ]
        
        manager = RAGSearchManager(self.config)
        result = manager.search_vector_only("test query")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_type"], "vector")
    
    @patch('src.agents.participant.search.rag_search_manager.PhilosopherSearcher')
    def test_search_philosopher_only(self, mock_phil):
        """철학자 검색만 테스트"""
        mock_phil.return_value.search.return_value = [
            {"title": "Phil Result", "content": "Phil content", "source_type": "philosopher", "relevance_score": 0.7}
        ]
        
        manager = RAGSearchManager(self.config)
        result = manager.search_philosopher_only("test query")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_type"], "philosopher")
    
    @patch('src.agents.participant.search.rag_search_manager.WebSearcher')
    def test_search_with_exception(self, mock_web):
        """검색 중 예외 발생 테스트"""
        # 웹 검색에서 예외 발생
        mock_web.return_value.search.side_effect = Exception("Search failed")
        
        manager = RAGSearchManager(self.config)
        
        result = manager.search_all_sources("test query", sources=["web"])
        
        # 예외가 발생해도 빈 리스트 반환
        self.assertEqual(result, [])
    
    def test_rank_and_filter_results(self):
        """결과 순위 매기기 및 필터링 테스트"""
        results = [
            {"title": "Result 1", "weighted_score": 0.8, "url": "http://example1.com"},
            {"title": "Result 2", "weighted_score": 0.9, "url": "http://example2.com"},
            {"title": "Result 3", "weighted_score": 0.7, "url": "http://example3.com"}
        ]
        
        ranked = self.manager._rank_and_filter_results(results)
        
        # 점수 순으로 정렬되었는지 확인
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0]["weighted_score"], 0.9)  # Result 2
        self.assertEqual(ranked[1]["weighted_score"], 0.8)  # Result 1
        self.assertEqual(ranked[2]["weighted_score"], 0.7)  # Result 3
    
    def test_rank_and_filter_results_with_duplicates(self):
        """중복 URL이 있는 결과 필터링 테스트"""
        results = [
            {"title": "Result 1", "weighted_score": 0.8, "url": "http://same.com"},
            {"title": "Result 2", "weighted_score": 0.9, "url": "http://same.com"},  # 중복 URL
            {"title": "Result 3", "weighted_score": 0.7, "url": "http://different.com"}
        ]
        
        ranked = self.manager._rank_and_filter_results(results)
        
        # 중복이 제거되었는지 확인
        self.assertEqual(len(ranked), 2)
        urls = [r["url"] for r in ranked]
        self.assertIn("http://same.com", urls)
        self.assertIn("http://different.com", urls)
        
        # 높은 점수의 결과가 유지되었는지 확인
        same_url_result = next(r for r in ranked if r["url"] == "http://same.com")
        self.assertEqual(same_url_result["weighted_score"], 0.9)  # Result 2가 유지됨
    
    def test_get_search_statistics(self):
        """검색 통계 정보 반환 테스트"""
        stats = self.manager.get_search_statistics()
        
        expected_keys = [
            "available_searchers", "source_weights", "max_total_results", "searcher_stats"
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        self.assertEqual(len(stats["available_searchers"]), 3)
        self.assertEqual(stats["max_total_results"], 10)
        self.assertIn("web", stats["available_searchers"])
        self.assertIn("vector", stats["available_searchers"])
        self.assertIn("philosopher", stats["available_searchers"])
    
    def test_update_source_weights(self):
        """소스 가중치 업데이트 테스트"""
        new_weights = {"web": 0.5, "vector": 0.3, "philosopher": 0.2}
        
        self.manager.update_source_weights(new_weights)
        
        self.assertEqual(self.manager.source_weights["web"], 0.5)
        self.assertEqual(self.manager.source_weights["vector"], 0.3)
        self.assertEqual(self.manager.source_weights["philosopher"], 0.2)
    
    @patch('src.agents.participant.search.rag_search_manager.WebSearcher')
    @patch('src.agents.participant.search.rag_search_manager.VectorSearcher')
    def test_search_with_fallback(self, mock_vector, mock_web):
        """폴백 검색 테스트"""
        # Primary 소스(web)에서 결과 부족
        mock_web.return_value.search.return_value = [
            {"title": "Web Result", "weighted_score": 0.8, "url": "http://web.com"}
        ]
        
        # Fallback 소스(vector)에서 추가 결과
        mock_vector.return_value.search.return_value = [
            {"title": "Vector Result", "weighted_score": 0.7, "url": "http://vector.com"}
        ]
        
        manager = RAGSearchManager(self.config)
        
        result = manager.search_with_fallback(
            "test query", 
            primary_sources=["web"], 
            fallback_sources=["vector"], 
            min_results=2
        )
        
        # Primary + Fallback 결과가 모두 포함되었는지 확인
        self.assertEqual(len(result), 2)
        urls = [r["url"] for r in result]
        self.assertIn("http://web.com", urls)
        self.assertIn("http://vector.com", urls)


class TestRAGSearchManagerIntegration(unittest.TestCase):
    """RAGSearchManager 통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.config = {
            "max_total_results": 5,
            "source_weights": {"web": 1.0, "vector": 0.0, "philosopher": 0.0},
            "web_search": {
                "web_crawling": False,
                "search_provider": "google",
                "max_results": 2
            }
        }
    
    @unittest.skip("실제 검색 API가 필요한 테스트 - 필요시 활성화")
    def test_real_integrated_search(self):
        """실제 통합 검색 테스트"""
        manager = RAGSearchManager(self.config)
        
        result = manager.search_all_sources("artificial intelligence", sources=["web"])
        
        self.assertIsInstance(result, list)
        # API 키가 없으면 빈 결과일 수 있음
        for item in result:
            self.assertIn("title", item)
            self.assertIn("content", item)
            self.assertIn("source_type", item)


if __name__ == '__main__':
    unittest.main() 