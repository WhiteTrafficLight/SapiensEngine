"""
Web Search Retriever Module

웹 검색을 통해 실시간 정보를 검색하고 추출하는 모듈입니다.
검색 API를 활용하여 쿼리 관련 웹 페이지를 찾고, 
스크래핑을 통해 콘텐츠를 추출한 후 임베딩하여 관련도를 평가합니다.
"""

import os
import json
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup

# 조건부 임포트 - sentence_transformers
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence_transformers not available. Web retriever will operate in limited mode.")

# 조건부 임포트 - numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available. Advanced numerical operations disabled.")

# .env 파일 로드 시도 (.env.local이 있는 경우)
try:
    from dotenv import load_dotenv
    current_path = Path(__file__).resolve()
    # 상위 디렉토리를 따라가며 .env.local 탐색 (프로젝트 루트/모노레포 대응)
    for parent in [current_path.parent] + list(current_path.parents):
        env_candidate = parent / '.env.local'
        if env_candidate.exists():
            load_dotenv(env_candidate)
            logger = logging.getLogger(__name__)
            logger.info(f".env.local 파일을 로드했습니다: {env_candidate}")
            break
    # Google API 키 → SEARCH_API_KEY 매핑 (web_search_test.py와 동일)
    if os.environ.get("GOOGLE_API_KEY") and not os.environ.get("SEARCH_API_KEY"):
        os.environ["SEARCH_API_KEY"] = os.environ.get("GOOGLE_API_KEY")
except ImportError:
    pass  # python-dotenv 패키지가 설치되지 않은 경우

# API 키는 환경 변수나 설정 파일에서 가져오는 것이 좋습니다
DEFAULT_SEARCH_API_KEY = os.environ.get("SEARCH_API_KEY", "")
DEFAULT_SERP_API_KEY = os.environ.get("SERP_API_KEY", "")
DEFAULT_GOOGLE_CX = os.environ.get("GOOGLE_SEARCH_CX", "")

# 로거 설정
logger = logging.getLogger(__name__)

class WebSearchRetriever:
    """
    웹 검색을 통한 실시간 정보 검색 및 추출 클래스
    
    다양한 검색 API를 활용하여 실시간 정보를 검색하고,
    스크래핑을 통해 콘텐츠를 추출하여 임베딩 기반 관련도 평가를 수행합니다.
    """
    
    # 클래스 레벨 캐시 (여러 인스턴스에서 공유)
    _embedding_model_cache = {}
    
    def __init__(
        self,
        embedding_model: str = "BAAI/bge-large-en-v1.5",  # 기본 모델을 더 좋은 모델로 변경
        search_provider: str = "serpapi",  # 'serpapi', 'google', 'bing'
        api_key: Optional[str] = None,
        max_results: int = 5,
        cache_dir: str = "./.cache/web_search",
        cache_expiry: int = 24,  # 시간 단위
        trusted_domains: Optional[List[str]] = None
    ):
        """
        초기화 함수
        
        Args:
            embedding_model: 임베딩 모델 이름
            search_provider: 검색 제공자 ('serpapi', 'google', 'bing')
            api_key: API 키
            max_results: 최대 검색 결과 수
            cache_dir: 캐시 디렉토리
            cache_expiry: 캐시 만료 시간 (시간)
            trusted_domains: 신뢰할 수 있는 도메인 목록
        """
        self.search_provider = search_provider
        self.max_results = max_results
        self.cache_dir = cache_dir
        self.cache_expiry = cache_expiry
        
        # 캐시 디렉토리 생성
        os.makedirs(cache_dir, exist_ok=True)
        
        # API 키 설정
        if api_key:
            self.api_key = api_key
        elif search_provider == 'serpapi':
            self.api_key = DEFAULT_SERP_API_KEY
            if not self.api_key:
                logger.warning("SERP_API_KEY가 설정되지 않았습니다. SerpAPI 검색이 작동하지 않을 수 있습니다.")
        else:
            self.api_key = DEFAULT_SEARCH_API_KEY
            if not self.api_key:
                logger.warning(f"{search_provider} API 키가 설정되지 않았습니다. 검색이 작동하지 않을 수 있습니다.")
        
        # Google Custom Search의 CX 값 확인
        if search_provider == 'google' and not DEFAULT_GOOGLE_CX:
            logger.warning("GOOGLE_SEARCH_CX가 설정되지 않았습니다. Google 검색이 작동하지 않을 수 있습니다.")
            
        # 임베딩 모델 로드 (캐시 활용)
        if embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
            if embedding_model in WebSearchRetriever._embedding_model_cache:
                self.embedding_model = WebSearchRetriever._embedding_model_cache[embedding_model]
                logger.debug(f"임베딩 모델 '{embedding_model}' 캐시 재사용")
            else:
                try:
                    self.embedding_model = SentenceTransformer(embedding_model)
                    WebSearchRetriever._embedding_model_cache[embedding_model] = self.embedding_model
                    logger.info(f"임베딩 모델 '{embedding_model}' 로드 완료")
                except Exception as e:
                    logger.error(f"임베딩 모델 로드 실패: {str(e)}")
                    self.embedding_model = None
        else:
            self.embedding_model = None
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("SentenceTransformers not available. Similarity calculation disabled.")
            
        # 신뢰할 수 있는 도메인 설정
        self.trusted_domains = trusted_domains or [
            '.edu', '.gov', '.org', 'wikipedia.org', 'github.com',
            'arxiv.org', 'scholar.google.com', 'researchgate.net',
            'nature.com', 'science.org', 'ieee.org', 'acm.org'
        ]

    def _calculate_similarity_fallback(self, text1: str, text2: str) -> float:
        """기본 유사도 계산 (fallback)"""
        # 간단한 단어 기반 유사도
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

    def search(self, query: str, num_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        웹 검색을 수행하여 관련 URL 목록을 반환합니다.
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 검색 결과 수 (기본값은 self.max_results)
            
        Returns:
            검색 결과 목록 (URL, 제목, 발췌문 등 포함)
        """
        num_results = num_results or self.max_results
        
        # 캐시 확인
        cache_key = self._generate_cache_key(query)
        cached_results = self._get_from_cache(cache_key)
        
        if cached_results:
            logger.info(f"캐시에서 검색 결과 {len(cached_results)} 항목 로드")
            return cached_results[:num_results]
        
        try:
            if self.search_provider == 'serpapi':
                results = self._search_with_serpapi(query, num_results)
            elif self.search_provider == 'google':
                results = self._search_with_google_api(query, num_results)
            elif self.search_provider == 'bing':
                results = self._search_with_bing_api(query, num_results)
            else:
                raise ValueError(f"지원하지 않는 검색 제공자: {self.search_provider}")
                
            # 결과 캐싱
            if results:
                self._save_to_cache(cache_key, results)
                
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"검색 실패: {str(e)}")
            return []
    
    def _search_with_serpapi(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        SerpAPI를 사용한 웹 검색
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        try:
            # SerpAPI 호출
            base_url = "https://serpapi.com/search"
            params = {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "num": num_results + 5  # 필터링 고려 여분 요청
            }
            
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 결과 파싱
            results = []
            if "organic_results" in data:
                for item in data["organic_results"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "serpapi",
                        "date": item.get("date", ""),
                        "domain": self._extract_domain(item.get("link", "")),
                        "position": item.get("position", 0)
                    }
                    results.append(result)
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"SerpAPI 검색 실패: {str(e)}")
            return []

    def _search_with_google_api(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        Google Custom Search API를 사용한 웹 검색
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        try:
            # Google Custom Search API 호출
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": DEFAULT_GOOGLE_CX,  # Search Engine ID
                "q": query,
                "num": min(10, num_results)  # API 제한: 최대 10개
            }
            
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 결과 파싱
            results = []
            if "items" in data:
                for item in data["items"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "google_api",
                        "domain": self._extract_domain(item.get("link", "")),
                        "date": "",  # Google API는 날짜 제공 안함
                        "position": len(results) + 1
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Google API 검색 실패: {str(e)}")
            return []

    def _search_with_bing_api(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """
        Bing Search API를 사용한 웹 검색
        
        Args:
            query: 검색 쿼리
            num_results: 반환할 결과 수
            
        Returns:
            검색 결과 목록
        """
        try:
            # Bing Search API 호출
            endpoint = "https://api.bing.microsoft.com/v7.0/search"
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key
            }
            params = {
                "q": query,
                "count": num_results,
                "offset": 0,
                "mkt": "en-US"
            }
            
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # 결과 파싱
            results = []
            if "webPages" in data and "value" in data["webPages"]:
                for item in data["webPages"]["value"]:
                    result = {
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "bing_api",
                        "domain": self._extract_domain(item.get("url", "")),
                        "date": item.get("dateLastCrawled", ""),
                        "position": len(results) + 1
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Bing API 검색 실패: {str(e)}")
            return []

    def retrieve_and_extract(
        self, 
        query: str, 
        max_pages: int = 3,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        max_total_chunks: int = 50000,
        rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        웹 검색 수행, 페이지 내용 추출 및 관련 청크 반환
        
        Args:
            query: 검색 쿼리
            max_pages: 처리할 최대 페이지 수
            chunk_size: 텍스트 청크 크기
            chunk_overlap: 청크 간 중첩 크기
            max_total_chunks: 최대 청크 수 (기본 50,000)
            rerank: 관련성에 따라 재순위화 여부
            
        Returns:
            텍스트 청크 목록 (메타데이터 포함)
        """
        # API 키 확인
        if not self.api_key:
            logger.error(f"웹 검색 API 키가 설정되지 않았습니다. 검색 제공자: {self.search_provider}")
            if self.search_provider == 'serpapi':
                logger.error("환경 변수 SERP_API_KEY를 설정해주세요.")
            elif self.search_provider == 'google':
                logger.error("환경 변수 SEARCH_API_KEY와 GOOGLE_SEARCH_CX를 설정해주세요.")
            elif self.search_provider == 'bing':
                logger.error("환경 변수 SEARCH_API_KEY를 설정해주세요.")
            return []

        # 웹 검색으로 URL 목록 가져오기
        logger.info(f"웹 검색 시작: '{query}' (최대 {max_pages*2}개 결과)")
        search_results = self.search(query, max_pages * 2)  # 여유있게 요청
        
        if not search_results:
            logger.warning(f"검색 결과 없음: {query}")
            return []
        
        logger.info(f"웹 검색 결과: {len(search_results)}개 URL")
        for idx, result in enumerate(search_results[:3]):  # 처음 3개만 출력
            logger.info(f"  {idx+1}. {result.get('title', '제목 없음')} - {result.get('url', '링크 없음')}")
        
        # 신뢰도 기반 필터링 및 정렬
        filtered_results = self._filter_and_rank_by_trust(search_results)
        top_results = filtered_results[:max_pages]
        
        logger.info(f"필터링 후 상위 {len(top_results)}개 URL 처리")
        
        # 병렬로 페이지 콘텐츠 추출
        extracted_contents = []
        
        with ThreadPoolExecutor(max_workers=max_pages) as executor:
            future_to_url = {
                executor.submit(self._extract_page_content, result["url"], result): result
                for result in top_results
            }
            
            for future in future_to_url:
                try:
                    content, metadata = future.result()
                    if content:
                        extracted_contents.append((content, metadata))
                        logger.info(f"콘텐츠 추출 성공: {metadata.get('url', '알 수 없음')} ({len(content)} 자)")
                    else:
                        logger.warning(f"콘텐츠가 비어있음: {future_to_url[future].get('url', '알 수 없음')}")
                except Exception as e:
                    logger.error(f"콘텐츠 추출 실패 ({future_to_url[future].get('url', '알 수 없음')}): {str(e)}")
        
        logger.info(f"총 {len(extracted_contents)}개 페이지에서 콘텐츠 추출 완료")
        
        # 콘텐츠를 청크로 분할
        all_chunks = []
        
        total_chunks = 0

        for content, metadata in extracted_contents:
            remaining = max_total_chunks - total_chunks
            if remaining <= 0:
                break

            chunks = self._split_into_chunks(content, chunk_size, chunk_overlap, max_chunks=remaining)
            logger.info(f"페이지 '{metadata.get('title', '제목 없음')}'에서 {len(chunks)}개 청크 생성")
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_id": f"{metadata.get('domain', 'unknown')}_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
                all_chunks.append({
                    "text": chunk,
                    "metadata": chunk_metadata,
                    "source": "web",
                    "similarity": 0.0  # 재순위 전 기본값
                })
            
            total_chunks += len(chunks)
        
        logger.info(f"총 {len(all_chunks)}개 웹 청크 생성")
        
        # 쿼리 관련성에 따라 재순위화 (선택 사항)
        if rerank and self.embedding_model and all_chunks:
            ranked_chunks = self._rerank_by_relevance(query, all_chunks)
            logger.info(f"쿼리 관련성에 따라 {len(ranked_chunks)}개 청크 재순위화 완료")
            return ranked_chunks
        
        return all_chunks

    def _extract_page_content(self, url: str, search_result: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        웹 페이지 내용 추출 및 정제
        
        Args:
            url: 웹 페이지 URL
            search_result: 해당 URL의 검색 결과 정보
            
        Returns:
            (추출된 텍스트, 메타데이터) 튜플
        """
        try:
            # 캐시 확인
            cache_key = self._generate_cache_key(url)
            cached_data = self._get_from_cache(cache_key)
            
            if cached_data:
                logger.info(f"캐시에서 페이지 콘텐츠 로드: {url}")
                return cached_data.get("content", ""), cached_data.get("metadata", {})
            
            # 페이지 요청
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 불필요한 요소 제거 - 향상된 필터링
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
                element.decompose()
                
            # 광고, 구독, 소셜 미디어, 메뉴 등 필터링 강화
            for selector in [
                ".menu", ".navigation", ".nav", ".sidebar", ".footer", ".header", 
                ".ad", ".advertisement", ".banner", ".subscribe", ".newsletter",
                ".social", ".share", ".comment", ".cookie", ".popup", ".modal",
                ".widget", ".related", ".recommendation", "[role=navigation]",
                "[id*=menu]", "[class*=menu]", "[id*=nav]", "[class*=nav]",
                "[id*=sidebar]", "[class*=sidebar]"
            ]:
                for element in soup.select(selector):
                    element.decompose()
            
            # 텍스트 추출
            title = soup.title.string if soup.title else ""
            
            # 메인 콘텐츠 추출 (여러 방법 시도)
            main_content = ""
            
            # 1. article 태그 확인
            articles = soup.find_all("article")
            if articles:
                for article in articles:
                    # 짧은 텍스트가 아닌 실제 콘텐츠만 추출
                    article_text = article.get_text(separator=' ', strip=True)
                    if len(article_text) > 150:  # 충분히 긴 콘텐츠만 유지
                        main_content += article_text + "\n\n"
            
            # 2. main 태그 확인
            if not main_content:
                main = soup.find("main")
                if main:
                    main_content = main.get_text(separator=' ', strip=True)
            
            # 3. 콘텐츠 관련 div 확인 (일반적인 콘텐츠 컨테이너)
            if not main_content:
                for id_class in ["content", "main", "article", "post", "entry", "blog", "text", "body", "page"]:
                    # ID로 검색
                    content_div = soup.find("div", {"id": id_class})
                    if content_div:
                        content_text = content_div.get_text(separator=' ', strip=True)
                        if len(content_text) > 200:  # 충분히 긴 콘텐츠만 유지
                            main_content = content_text
                            break
                    
                    # 클래스로 검색
                    for div in soup.find_all("div", {"class": lambda c: c and id_class in c.lower()}):
                        content_text = div.get_text(separator=' ', strip=True)
                        if len(content_text) > 200:  # 충분히 긴 콘텐츠만 유지
                            main_content = content_text
                            break
            
            # 4. 모든 단락(p) 추출 - 길이 기준 필터링 강화
            if not main_content:
                paragraphs = []
                for p in soup.find_all("p"):
                    p_text = p.get_text(strip=True)
                    
                    # 충분히 길고, 의미 있는 텍스트만 포함
                    if len(p_text) > 80 and not any(x in p_text.lower() for x in [
                        "subscribe", "newsletter", "sign up", "cookie", "privacy policy", 
                        "terms of service", "all rights reserved", "copyright"
                    ]):
                        paragraphs.append(p_text)
                
                # 단락이 충분히 있으면 내용 결합
                if len(paragraphs) >= 2:
                    main_content = "\n\n".join(paragraphs)
            
            # 5. 최후의 방법: 본문에서 짧은 텍스트와 메뉴 관련 내용 제외
            if not main_content and soup.body:
                body_text = soup.body.get_text(separator='\n', strip=True)
                # 줄 단위로 분할하여 의미 있는 텍스트만 유지
                lines = []
                for line in body_text.split('\n'):
                    line = line.strip()
                    # 충분히 길고 링크/메뉴 텍스트가 아닌 경우만 포함
                    if (len(line) > 60 and 
                        not any(x in line.lower() for x in [
                            "click here", "read more", "learn more", "sign up", "log in", "subscribe",
                            "follow us", "contact us", "about us", "privacy", "terms", "copyright"
                        ])):
                        lines.append(line)
                
                if lines:
                    main_content = "\n".join(lines)
            
            # 텍스트 정제
            main_content = self._clean_text(main_content)
            
            # 콘텐츠 최소 길이 체크 - 의미 있는 콘텐츠가 없으면 빈 문자열 반환
            if len(main_content.split()) < 100:  # 최소 100단어 필요
                logger.warning(f"추출된 콘텐츠가 너무 짧습니다: {url}")
                return "", {"url": url, "error": "insufficient content"}
            
            # 메타데이터 추출
            metadata = {
                "url": url,
                "title": title.strip() if title else "",
                "domain": self._extract_domain(url),
                "source": search_result.get("source", "web"),
                "date_extracted": datetime.now().isoformat(),
                "search_position": search_result.get("position", 0),
                "snippet": search_result.get("snippet", ""),
                "content_length": len(main_content),
                "word_count": len(main_content.split())
            }
            
            # 발행일 추출 시도
            try:
                meta_date = soup.find("meta", {"property": "article:published_time"})
                if meta_date:
                    metadata["published_date"] = meta_date["content"]
            except:
                pass
            
            # 캐시에 저장
            if main_content:
                cache_data = {
                    "content": main_content,
                    "metadata": metadata
                }
                self._save_to_cache(cache_key, cache_data)
            
            # 메모리 정리
            del soup
            import gc
            gc.collect()

            return main_content, metadata
            
        except Exception as e:
            logger.error(f"{url} 콘텐츠 추출 실패: {str(e)}")
            return "", {"url": url, "error": str(e)}

    def _clean_text(self, text: str) -> str:
        """
        추출된 텍스트 정제 - 향상된 필터링
        
        Args:
            text: 원본 텍스트
            
        Returns:
            정제된 텍스트
        """
        if not text:
            return ""
            
        # 여러 공백 제거
        text = ' '.join(text.split())
        
        # 불필요한 문자 제거
        text = re.sub(r'[\u2800-\u28FF]+', '', text)  # 점자 문자 제거
        
        # 이메일 주소 제거
        text = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)
        
        # URL 제거
        text = re.sub(r'https?://\S+', '[URL]', text)
        
        # 특수문자 연속 3개 이상 제거
        text = re.sub(r'[^\w\s.,:;()\-–—]{3,}', ' ', text)
        
        # 줄 단위 필터링
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 너무 짧은 라인 필터링
            if len(line) < 30:
                continue
                
            # 메뉴/네비게이션 문자열 필터링
            if any(x in line.lower() for x in [
                "subscribe", "newsletter", "sign up", "cookie", "privacy policy", 
                "terms of service", "all rights reserved", "copyright", "menu", 
                "navigation", "click here", "read more", "learn more"
            ]):
                continue
                
            # 이전/다음 페이지 내비게이션 필터링
            if re.search(r'^(next|previous|page \d+|follow us|contact us)$', line.lower()):
                continue
                
            filtered_lines.append(line)
        
        # 라인 병합
        text = '\n'.join(filtered_lines)
        
        # 중복된 단락 제거
        paragraphs = text.split('\n\n')
        unique_paragraphs = []
        seen = set()
        
        for para in paragraphs:
            # 단락이 충분히 길고 이전에 나오지 않았으면 추가
            if len(para) > 80 and para not in seen:
                unique_paragraphs.append(para)
                seen.add(para)
        
        return '\n\n'.join(unique_paragraphs)

    def _split_into_chunks(self, text: str, chunk_size: int, chunk_overlap: int, max_chunks: Optional[int] = None) -> List[str]:
        """
        텍스트를 청크로 분할 - 문장 단위 분할 및 완전한 문장 시작 보장
        
        Args:
            text: 원본 텍스트
            chunk_size: 청크 크기 (문자 수)
            chunk_overlap: 청크 간 중첩 크기
            max_chunks: 최대 청크 수
            
        Returns:
            텍스트 청크 목록
        """
        if not text:
            return []
        
        # 문장 단위로 텍스트 먼저 분할
        sentences = []
        # 문장 단위 분할을 위한 패턴 - 마침표, 물음표, 느낌표 등으로 끝나는 문장
        pattern = r'(?<=[.!?])\s+'
        raw_sentences = re.split(pattern, text)
        
        # 빈 문장 제거 및 정리
        for sentence in raw_sentences:
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
        
        # 청크 조합
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            # 너무 긴 문장은 chunk_size 기준으로 분할
            if len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # 긴 문장 처리 - 단어 단위로 분할
                words = sentence.split()
                sub_chunk = []
                sub_length = 0
                
                for word in words:
                    if sub_length + len(word) + 1 <= chunk_size:
                        sub_chunk.append(word)
                        sub_length += len(word) + 1
                    else:
                        if sub_chunk:
                            chunks.append(' '.join(sub_chunk))
                            if max_chunks and len(chunks) >= max_chunks:
                                return chunks
                        sub_chunk = [word]
                        sub_length = len(word)
                
                if sub_chunk:
                    chunks.append(' '.join(sub_chunk))
                    if max_chunks and len(chunks) >= max_chunks:
                        return chunks
            
            # 일반적인 문장 처리
            elif current_length + len(sentence) + 1 <= chunk_size:
                current_chunk.append(sentence)
                current_length += len(sentence) + 1  # 공백 포함
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    
                    # 청크 수 제한 확인
                    if max_chunks and len(chunks) >= max_chunks:
                        return chunks
                
                # 오버랩 구현 - 마지막 문장 수를 기준으로
                overlap_sentences = []
                overlap_length = 0
                
                # 청크 중첩을 위해 이전 청크의 일부 문장 재사용
                overlap_count = min(3, len(current_chunk))  # 최대 3개 문장 중첩
                if overlap_count > 0:
                    overlap_sentences = current_chunk[-overlap_count:]
                    overlap_length = sum(len(s) for s in overlap_sentences) + overlap_count
                
                # 새 청크 시작
                if overlap_length <= chunk_overlap:
                    current_chunk = overlap_sentences + [sentence]
                    current_length = overlap_length + len(sentence) + 1
                else:
                    current_chunk = [sentence]
                    current_length = len(sentence)
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        # 불완전한 시작 문장 감지 및 수정
        for i in range(len(chunks)):
            # 첫 글자가 소문자이며 단어 중간인지 확인 (불완전한 문장 시작 흔적)
            if chunks[i] and chunks[i][0].islower() and not chunks[i][0].isalpha():
                words = chunks[i].split()
                if words and len(words[0]) <= 3:  # 짧은 단어라면 시작 단어 제거 가능성
                    chunks[i] = ' '.join(words[1:]) if len(words) > 1 else ""
        
        # 빈 청크 제거
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        return chunks

    def _rerank_by_relevance(self, query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        텍스트 청크를 쿼리와의 관련성에 따라 재순위화
        
        Args:
            query: 검색 쿼리
            chunks: 텍스트 청크 목록
            
        Returns:
            재순위화된 청크 목록
        """
        if not self.embedding_model or not chunks:
            return chunks
            
        try:
            # 쿼리 임베딩
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
            
            # 청크 임베딩 및 유사도 계산
            chunk_texts = [c["text"] for c in chunks]
            chunk_embeddings = self.embedding_model.encode(chunk_texts, convert_to_tensor=True)
            
            # 코사인 유사도 계산
            similarities = util.cos_sim(query_embedding, chunk_embeddings)[0].tolist()
            
            # 청크에 유사도 점수 추가 및 복합 score 계산
            for i, chunk in enumerate(chunks):
                similarity = similarities[i]
                chunk["similarity"] = float(similarity)  # 텐서를 float로 변환
                chunk["distance"] = 1.0 - float(similarity)  # 거리 = 1 - 유사도
                
                # 소스 정보가 없으면 "web"으로 설정
                if "source" not in chunk:
                    chunk["source"] = "web"
                
                # 복합 점수 계산 - 다양한 요소 고려
                # 1. 기본 유사도 (가중치: 0.7)
                composite_score = float(similarity) * 0.7
                
                # 2. 메타데이터 기반 신뢰도 점수 계산 (가중치: 0.3)
                trust_score = self._calculate_trust_score(chunk.get("metadata", {}))
                composite_score += trust_score * 0.3
                
                # 3. 키워드 일치 점수 (텍스트에 쿼리 단어가 포함된 비율)
                query_terms = set(query.lower().split())
                text_lower = chunk["text"].lower()
                if query_terms:
                    keyword_matches = sum(1 for term in query_terms if term in text_lower)
                    keyword_score = keyword_matches / len(query_terms)
                    # 키워드 점수도 최종 점수에 반영 (부스트)
                    composite_score = composite_score * (1.0 + 0.1 * keyword_score)
                
                # 4. 추가적인 도메인 점수 (edu/gov/org에 보너스)
                domain = chunk.get("metadata", {}).get("domain", "")
                if domain.endswith(".edu") or domain.endswith(".gov"):
                    composite_score *= 1.05  # 5% 보너스
                elif domain.endswith(".org"):
                    composite_score *= 1.02  # 2% 보너스
                
                # 최종 복합 점수 저장 (0-1 범위로 정규화)
                chunk["score"] = min(1.0, composite_score)
            
            # 복합 점수 기준 정렬
            sorted_chunks = sorted(chunks, key=lambda x: x["score"], reverse=True)
            
            return sorted_chunks
            
        except Exception as e:
            logger.error(f"청크 재순위화 실패: {str(e)}")
            return chunks

    def _calculate_trust_score(self, metadata: Dict[str, Any]) -> float:
        """
        콘텐츠 신뢰도 점수 계산 - 점수 산출 로직 개선
        
        Args:
            metadata: 콘텐츠 메타데이터
            
        Returns:
            0~1 사이의 신뢰도 점수
        """
        score = 0.5  # 기본 점수
        
        # 도메인 기반 신뢰도
        domain = metadata.get("domain", "")
        
        # 신뢰할 수 있는 도메인에 가산점
        for trusted in self.trusted_domains:
            if trusted in domain:
                score += 0.2
                break
        
        # 콘텐츠 길이 기반 신뢰도 (긴 콘텐츠에 가산점)
        word_count = metadata.get("word_count", 0)
        if word_count > 1000:
            score += 0.15
        elif word_count > 500:
            score += 0.1
        elif word_count > 200:
            score += 0.05
        elif word_count < 100:
            score -= 0.1  # 너무 짧은 콘텐츠 페널티
                
        # 검색 순위 기반 신뢰도
        position = metadata.get("search_position", 0)
        if position > 0:
            position_score = max(0, 0.1 - (position - 1) * 0.01)  # 1위: 0.1, 10위: 0.01
            score += position_score
            
        # 발행일 기반 신뢰도
        published_date = metadata.get("published_date", "")
        if published_date:
            try:
                date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                days_old = (datetime.now() - date).days
                
                # 최신 자료에 가산점 (1년 이내)
                if days_old < 365:
                    freshness_score = 0.1 * (1 - days_old / 365)
                    score += freshness_score
            except:
                pass
                
        return min(1.0, max(0.0, score))

    def _filter_and_rank_by_trust(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        검색 결과를 신뢰도에 따라 필터링하고 정렬
        
        Args:
            results: 검색 결과 목록
            
        Returns:
            필터링 및 정렬된 결과 목록
        """
        # 각 결과에 신뢰도 점수 추가
        for result in results:
            domain = result.get("domain", "")
            position = result.get("position", 0)
            
            # 기본 점수
            trust_score = 0.5
            
            # 도메인 신뢰도
            for trusted in self.trusted_domains:
                if trusted in domain:
                    trust_score += 0.3
                    break
            
            # 검색 순위 신뢰도
            position_score = max(0, 0.2 - (position - 1) * 0.02)
            trust_score += position_score
            
            # 최종 신뢰도 점수 저장
            result["trust_score"] = min(1.0, trust_score)
        
        # 신뢰도 낮은 결과 필터링
        filtered_results = [r for r in results if r.get("trust_score", 0) > 0.5]
        
        # 신뢰도 기준 내림차순 정렬
        filtered_results.sort(key=lambda x: x.get("trust_score", 0), reverse=True)
        
        return filtered_results or results  # 필터링 결과가 없으면 원본 반환

    def _extract_domain(self, url: str) -> str:
        """
        URL에서 도메인 추출
        
        Args:
            url: 웹 페이지 URL
            
        Returns:
            도메인 이름
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            return domain
        except:
            return ""

    def _generate_cache_key(self, text: str) -> str:
        """
        캐시 키 생성
        
        Args:
            text: 쿼리 또는 URL
            
        Returns:
            해시 기반 캐시 키
        """
        hash_object = hashlib.md5(text.encode())
        return hash_object.hexdigest()

    def _get_from_cache(self, cache_key: str) -> Any:
        """
        캐시에서 데이터 가져오기
        
        Args:
            cache_key: 캐시 키
            
        Returns:
            캐시된 데이터 또는 None
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if not os.path.exists(cache_file):
            return None
            
        # 만료 확인
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - file_time > timedelta(hours=self.cache_expiry):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None

    def _save_to_cache(self, cache_key: str, data: Any) -> None:
        """
        데이터를 캐시에 저장
        
        Args:
            cache_key: 캐시 키
            data: 저장할 데이터
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"캐시 저장 실패: {str(e)}") 