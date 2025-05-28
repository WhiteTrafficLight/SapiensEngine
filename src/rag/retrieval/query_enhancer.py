"""
Query Enhancer Module (쿼리 보강 모듈)

이 모듈은 RAG 시스템의 검색 성능을 향상시키기 위한 다양한 쿼리 보강 알고리즘을 제공합니다.
단일 쿼리를 여러 다양한 방식으로 확장하여 검색 결과의 품질과 다양성을 개선합니다.

구현된 보강 방식:
1. 유의어 치환 (Paraphrasing)
2. 핵심어 추출 후 재조합 (Keyword Extraction and Recombination)
3. 의미적 확장 (Embedding-based Expansion)
4. 질문화 (Query to Question)
5. 타겟 키워드 삽입 (Target Keyword Insertion)
6. 키워드 확장 (Keyword Expansion)
7. 하이브리드 방식 (Hybrid Approach)
"""

import re
from typing import List, Dict, Any, Optional, Union, Tuple
import logging
import random
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer, util
import numpy as np

# LLM 관련 임포트
try:
    from sapiens_engine.core.llm_manager import LLMManager
except ImportError:
    from llm_manager import LLMManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NLTK 리소스 다운로드
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

class QueryEnhancer:
    """쿼리 보강을 위한 기본 클래스"""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2", llm_model: str = "gpt-3.5-turbo"):
        """
        초기화 함수
        
        Args:
            embedding_model: 임베딩에 사용할 모델 이름
            llm_model: LLM에 사용할 모델 이름
        """
        self.embedding_model_name = embedding_model
        self.llm_model_name = llm_model
        
        # 임베딩 모델 로드
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            logger.info(f"임베딩 모델 '{embedding_model}' 로드 완료")
        except Exception as e:
            logger.error(f"임베딩 모델 로드 실패: {str(e)}")
            self.embedding_model = None
            
        # LLM 매니저 초기화
        try:
            self.llm_manager = LLMManager(config={"model": llm_model, "provider": "openai"})
            logger.info(f"LLM 모델 '{llm_model}' 초기화 완료")
        except Exception as e:
            logger.error(f"LLM 모델 초기화 실패: {str(e)}")
            self.llm_manager = None
            
        # 불용어 세트 로드
        self.stopwords = set(stopwords.words('english'))
        
        # 철학/트랜스휴머니즘 관련 주요 키워드 정의
        self.domain_keywords = {
            "philosophy": [
                "ethics", "existence", "metaphysics", "ontology", "epistemology", 
                "phenomenology", "consciousness", "being", "essence", "identity",
                "freedom", "determinism", "morality", "values", "virtue"
            ],
            "transhumanism": [
                "enhancement", "augmentation", "biotechnology", "posthuman", 
                "longevity", "singularity", "nanotechnology", "cognitive enhancement",
                "genetic engineering", "cyborg", "human condition", "evolution",
                "superintelligence", "transcendence", "human limitations"
            ]
        }
    
    def enhance(self, query: str, **kwargs) -> List[str]:
        """
        쿼리를 보강합니다 (기본 구현은 원본 쿼리만 반환)
        
        Args:
            query: 원본 쿼리 문자열
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        return [query]
    
    def _preprocess_query(self, query: str) -> str:
        """
        쿼리 전처리 (불필요한 문자 제거, 소문자화 등)
        
        Args:
            query: 원본 쿼리
            
        Returns:
            전처리된 쿼리
        """
        # 소문자 변환
        query = query.lower()
        
        # 불필요한 문자 제거 (특수 제어 문자 등)
        query = re.sub(r'[^\w\s\?\!\.\,\-\']', ' ', query)
        
        # 여러 공백을 하나로 치환
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def _extract_keywords(self, query: str, min_length: int = 3, max_keywords: int = 5) -> List[str]:
        """
        쿼리에서 핵심 키워드 추출
        
        Args:
            query: 원본 쿼리
            min_length: 키워드의 최소 길이
            max_keywords: 추출할 최대 키워드 수
            
        Returns:
            추출된 키워드 목록
        """
        # 토큰화
        tokens = word_tokenize(query.lower())
        
        # 불용어 및 짧은 단어 제거
        keywords = [word for word in tokens if word not in self.stopwords and len(word) >= min_length]
        
        # 빈도수 기준 정렬
        word_freq = Counter(keywords)
        sorted_keywords = [w for w, _ in word_freq.most_common(max_keywords)]
        
        return sorted_keywords
    
    def _get_domain_keywords(self, domain: str = "all", count: int = 3) -> List[str]:
        """
        특정 도메인의 키워드 반환
        
        Args:
            domain: 키워드 도메인 ("philosophy", "transhumanism", "all")
            count: 반환할 키워드 수
            
        Returns:
            도메인 키워드 목록
        """
        if domain == "all":
            all_keywords = []
            for kw_list in self.domain_keywords.values():
                all_keywords.extend(kw_list)
            return random.sample(all_keywords, min(count, len(all_keywords)))
        elif domain in self.domain_keywords:
            domain_kws = self.domain_keywords[domain]
            return random.sample(domain_kws, min(count, len(domain_kws)))
        else:
            return []

class ParaphrasingEnhancer(QueryEnhancer):
    """유의어 치환(Paraphrasing) 기반 쿼리 보강"""
    
    def enhance(self, query: str, count: int = 2, temperature: float = 0.7, **kwargs) -> List[str]:
        """
        유의어 치환을 통해 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            count: 생성할 보강 쿼리 수
            temperature: LLM 생성 다양성 제어 (높을수록 다양)
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        if not self.llm_manager:
            logger.warning("LLM 모델이 초기화되지 않아 유의어 치환 불가")
            return [query]
        
        # 유의어 치환 프롬프트
        prompt = f"""
        I need {count} semantically similar paraphrases of the following query, 
        using synonyms and alternative phrasing while preserving the core meaning.
        Only return the paraphrases, one per line, without any explanations.
        
        QUERY: "{query}"
        """
        
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        try:
            # LLM으로 유의어 치환 생성
            response = self.llm_manager.generate_response("", prompt, temperature=temperature)
            
            # 결과 파싱
            paraphrases = [line.strip() for line in response.strip().split('\n') if line.strip()]
            
            # 따옴표 제거 및 중복 제거
            for paraphrase in paraphrases:
                paraphrase = re.sub(r'^["\'"]|["\'"]$', '', paraphrase).strip()
                if paraphrase and paraphrase.lower() != query.lower() and paraphrase not in enhanced_queries:
                    enhanced_queries.append(paraphrase)
            
            logger.info(f"유의어 치환으로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
            
        except Exception as e:
            logger.error(f"유의어 치환 실패: {str(e)}")
        
        return enhanced_queries

class KeywordExtractionEnhancer(QueryEnhancer):
    """핵심어 추출 후 재조합 기반 쿼리 보강"""
    
    def enhance(self, query: str, min_keywords: int = 3, max_keywords: int = 5, **kwargs) -> List[str]:
        """
        핵심어 추출 후 재조합하여 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            min_keywords: 최소 추출 키워드 수
            max_keywords: 최대 추출 키워드 수
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        # 핵심어 추출
        keywords = self._extract_keywords(query, min_length=3, max_keywords=max_keywords)
        
        if len(keywords) < min_keywords:
            # 키워드가 충분하지 않으면 원본 쿼리만 반환
            return enhanced_queries
        
        # 키워드만으로 간단한 쿼리 생성
        simple_query = ' '.join(keywords)
        if simple_query.lower() != query.lower():
            enhanced_queries.append(simple_query)
        
        # 핵심 키워드 AND 쿼리 생성
        and_query = ' AND '.join(keywords[:min(3, len(keywords))])
        if and_query.lower() != query.lower() and and_query not in enhanced_queries:
            enhanced_queries.append(and_query)
        
        # LLM 활용 키워드 재조합 (있는 경우)
        if self.llm_manager:
            try:
                prompt = f"""
                Create a new search query using these keywords extracted from the original query:
                {', '.join(keywords)}
                
                Original query: "{query}"
                
                Return only the new query without any explanation or additional text.
                """
                
                response = self.llm_manager.generate_response("", prompt, temperature=0.7)
                if response and response.strip():
                    enhanced_queries.append(response.strip())
            except Exception as e:
                logger.error(f"LLM 활용 키워드 재조합 실패: {str(e)}")
        
        logger.info(f"핵심어 추출 후 재조합으로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
        return enhanced_queries

class EmbeddingBasedEnhancer(QueryEnhancer):
    """의미적 확장(Embedding-based) 쿼리 보강"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 의미적 확장에 사용할 후보 문장들 (실제 구현에서는 더 큰 코퍼스 사용)
        self.candidate_sentences = [
            "How does transhumanism reduce humanity to technical problems?",
            "What are the ethical implications of human enhancement technologies?",
            "Is the human essence threatened by technological augmentation?",
            "How does technology redefine human nature and identity?",
            "What limitations of humanity does transhumanism seek to overcome?",
            "How does the concept of post-human challenge our understanding of personhood?",
            "What is the relationship between human imperfection and technological progress?",
            "How do enhancement technologies blur the line between human and machine?",
            "What philosophical perspectives critique transhumanist aspirations?",
            "How does the mechanistic view of human body influence enhancement ethics?",
            "What constitutes authenticity in an age of human augmentation?",
            "How does transhumanism conceptualize human flourishing?",
            "What are the boundaries of acceptable human modification?",
            "How do different cultural traditions view human enhancement?",
            "What is the significance of embodiment in human experience?",
        ]
    
    def enhance(self, query: str, top_k: int = 2, threshold: float = 0.7, **kwargs) -> List[str]:
        """
        임베딩 기반 의미적 유사성으로 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            top_k: 선택할 최대 유사 문장 수
            threshold: 최소 유사도 임계값
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        if not self.embedding_model:
            logger.warning("임베딩 모델이 초기화되지 않아 의미적 확장 불가")
            return [query]
        
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        try:
            # 쿼리를 임베딩 벡터로 변환
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
            
            # 후보 문장들의 임베딩 계산
            candidate_embeddings = self.embedding_model.encode(self.candidate_sentences, convert_to_tensor=True)
            
            # 코사인 유사도 계산
            similarities = util.pytorch_cos_sim(query_embedding, candidate_embeddings)[0]
            
            # CPU로 이동하여 numpy로 변환
            similarities_cpu = similarities.cpu()
            
            # 유사도가 높은 문장 선택
            top_indices = np.argsort(-similarities_cpu.numpy()).tolist()
            
            for idx in top_indices[:top_k]:
                similarity = similarities_cpu[idx].item()
                if similarity >= threshold:
                    enhanced_queries.append(self.candidate_sentences[idx])
            
            # LLM 활용 의미적 확장 (있는 경우)
            if self.llm_manager:
                try:
                    prompt = f"""
                    Generate ONE semantically similar query that captures the same meaning as:
                    "{query}"
                    
                    Make it different from these existing alternatives:
                    {enhanced_queries[1:]}
                    
                    Provide only the new query without any explanation or additional text.
                    """
                    
                    response = self.llm_manager.generate_response("", prompt, temperature=0.7)
                    if response and response.strip():
                        enhanced_queries.append(response.strip())
                except Exception as e:
                    logger.error(f"LLM 활용 의미적 확장 실패: {str(e)}")
            
            logger.info(f"의미적 확장으로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
            return enhanced_queries
            
        except Exception as e:
            logger.error(f"의미적 확장 실패: {str(e)}")
            return [query]

class QueryToQuestionEnhancer(QueryEnhancer):
    """질문화(Query to Question) 기반 쿼리 보강"""
    
    def enhance(self, query: str, question_types: int = 2, **kwargs) -> List[str]:
        """
        설명문을 질문 형태로 변환하여 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            question_types: 생성할 질문 유형 수
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        if not self.llm_manager:
            logger.warning("LLM 모델이 초기화되지 않아 질문화 불가")
            return [query]
        
        # 질문 유형 지정
        question_prefixes = [
            "How does",
            "What are the implications of",
            "Why is",
            "In what ways does",
            "To what extent does"
        ]
        
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        try:
            # LLM 활용 질문화
            prompt = f"""
            Transform this statement into {question_types} different questions that seek the same information.
            Use different question types (how, what, why, etc.) but preserve the core meaning.
            
            STATEMENT: "{query}"
            
            Output each question on a new line without numbering or any other text.
            """
            
            response = self.llm_manager.generate_response("", prompt, temperature=0.5)
            
            # 결과 파싱
            questions = [line.strip() for line in response.strip().split('\n') if line.strip() and '?' in line]
            
            # 중복 제거
            enhanced_queries.extend([q for q in questions if q.lower() != query.lower() and q not in enhanced_queries])
            
            # 질문이 생성되지 않은 경우 수동으로 생성
            if len(enhanced_queries) == 1:
                for prefix in question_prefixes[:question_types]:
                    # 문장 끝 마침표 제거 및 'is/are' 제거
                    cleaned_query = re.sub(r'\.+$', '', query)
                    cleaned_query = re.sub(r'^(is|are)\s+', '', cleaned_query, flags=re.IGNORECASE)
                    question = f"{prefix} {cleaned_query}?"
                    enhanced_queries.append(question)
            
            logger.info(f"질문화로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
            return enhanced_queries
            
        except Exception as e:
            logger.error(f"질문화 실패: {str(e)}")
            return [query]

class TargetKeywordEnhancer(QueryEnhancer):
    """타겟 키워드 삽입 기반 쿼리 보강"""
    
    def enhance(self, query: str, domain: str = "all", keyword_count: int = 2, **kwargs) -> List[str]:
        """
        타겟 키워드를 삽입하여 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            domain: 키워드 도메인 ("philosophy", "transhumanism", "all")
            keyword_count: 삽입할 키워드 수
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        # 도메인 키워드 가져오기
        domain_keywords = self._get_domain_keywords(domain, count=keyword_count*2)
        
        if not domain_keywords:
            return enhanced_queries
        
        # 원본 쿼리의 키워드 추출
        query_keywords = set(self._extract_keywords(query))
        
        # 쿼리에 없는 키워드만 선택
        new_keywords = [kw for kw in domain_keywords if kw.lower() not in query_keywords][:keyword_count]
        
        if not new_keywords:
            return enhanced_queries
        
        # 1. Boolean AND 쿼리 생성
        boolean_query = f"{query} AND {' AND '.join(new_keywords)}"
        enhanced_queries.append(boolean_query)
        
        # 2. 키워드를 추가한 쿼리 생성
        extended_query = f"{query} {' '.join(new_keywords)}"
        enhanced_queries.append(extended_query)
        
        # 3. LLM 활용 키워드 통합 (있는 경우)
        if self.llm_manager:
            try:
                prompt = f"""
                Based on the keywords {', '.join(domain_keywords)}, expand or rephrase the following query:
                "{query}"
                
                Return only the new query without any explanation or additional text.
                """
                
                response = self.llm_manager.generate_response("", prompt, temperature=0.7)
                if response and response.strip():
                    enhanced_queries.append(response.strip())
            except Exception as e:
                logger.error(f"LLM 활용 키워드 통합 실패: {str(e)}")
        
        logger.info(f"타겟 키워드 삽입으로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
        return enhanced_queries

class KeywordExpansionEnhancer(QueryEnhancer):
    """키워드 확장 기반 쿼리 보강"""
    
    def enhance(self, query: str, expansion_factor: int = 2, **kwargs) -> List[str]:
        """
        동의어 및 관련 개념으로 키워드를 확장하여 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            expansion_factor: 키워드 확장 계수
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        if not self.llm_manager:
            logger.warning("LLM 모델이 초기화되지 않아 키워드 확장 불가")
            return [query]
        
        # 원본 쿼리의 키워드 추출
        keywords = self._extract_keywords(query)
        
        if not keywords:
            return [query]
        
        enhanced_queries = [query]  # 원본 쿼리 유지
        
        try:
            # LLM으로 각 키워드의 동의어 및 관련 개념 확장
            for keyword in keywords[:3]:  # 상위 3개 키워드만 처리
                prompt = f"""
                Provide {expansion_factor} synonyms or closely related concepts for the term "{keyword}" 
                in the context of this query: "{query}"
                
                Output each synonym/concept on a new line without numbering or any other text.
                """
                
                response = self.llm_manager.generate_response("", prompt, temperature=0.5)
                
                # 결과 파싱
                expansions = [line.strip() for line in response.strip().split('\n') if line.strip()]
                
                # 각 확장 키워드로 쿼리 생성
                for expansion in expansions:
                    # 원본 키워드를 확장 키워드로 치환
                    enhanced_query = query.replace(keyword, expansion)
                    if enhanced_query != query:
                        enhanced_queries.append(enhanced_query)
            
            logger.info(f"키워드 확장으로 {len(enhanced_queries)-1}개 쿼리 생성 완료")
            return enhanced_queries
            
        except Exception as e:
            logger.error(f"키워드 확장 실패: {str(e)}")
            return [query]

class HybridEnhancer(QueryEnhancer):
    """여러 보강 방법을 조합한 하이브리드 방식"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 각 보강 전략 초기화
        self.enhancers = [
            ParaphrasingEnhancer(*args, **kwargs),
            KeywordExtractionEnhancer(*args, **kwargs),
            EmbeddingBasedEnhancer(*args, **kwargs),
            QueryToQuestionEnhancer(*args, **kwargs),
            TargetKeywordEnhancer(*args, **kwargs),
            KeywordExpansionEnhancer(*args, **kwargs)
        ]
    
    def enhance(self, query: str, max_results: int = 10, strategy: str = "balanced", **kwargs) -> List[str]:
        """
        여러 보강 방법을 조합하여 쿼리를 보강합니다.
        
        Args:
            query: 원본 쿼리
            max_results: 최대 결과 수
            strategy: 조합 전략 ("balanced", "all", "random")
            **kwargs: 추가 파라미터
            
        Returns:
            보강된 쿼리 목록
        """
        all_queries = [query]  # 원본 쿼리 유지
        
        try:
            if strategy == "all":
                # 모든 전략 결과 수집
                for enhancer in self.enhancers:
                    enhanced = enhancer.enhance(query, **kwargs)
                    all_queries.extend([q for q in enhanced if q != query])
                    
            elif strategy == "random":
                # 랜덤하게 선택된 2-3개 전략 결과 수집
                selected_enhancers = random.sample(self.enhancers, random.randint(2, 3))
                for enhancer in selected_enhancers:
                    enhanced = enhancer.enhance(query, **kwargs)
                    all_queries.extend([q for q in enhanced if q != query])
            
            else:  # "balanced" 전략 (기본값)
                # 각 전략에서 1-2개씩 결과 수집
                for enhancer in self.enhancers:
                    # 각 전략에서 2개 이상 결과가 나오는 경우에만 첫 2개 사용
                    enhanced = enhancer.enhance(query, **kwargs)
                    if len(enhanced) > 1:
                        all_queries.extend([q for q in enhanced[1:3] if q != query])
            
            # 중복 제거
            unique_queries = []
            seen = set()
            for q in all_queries:
                q_lower = q.lower()
                if q_lower not in seen:
                    unique_queries.append(q)
                    seen.add(q_lower)
            
            # 최대 결과 수 제한
            result = unique_queries[:max_results]
            
            logger.info(f"하이브리드 보강으로 {len(result)-1}개 쿼리 생성 완료")
            return result
            
        except Exception as e:
            logger.error(f"하이브리드 보강 실패: {str(e)}")
            return [query]

def enhance_query(query: str, method: str = "hybrid", **kwargs) -> List[str]:
    """
    지정된 방법으로 쿼리를 보강하는 편의 함수
    
    Args:
        query: 원본 쿼리
        method: 보강 방법 이름
        **kwargs: 해당 방법의 파라미터
        
    Returns:
        보강된 쿼리 목록
    """
    # 기본 파라미터
    llm_model = kwargs.pop('llm_model', 'gpt-3.5-turbo')
    embedding_model = kwargs.pop('embedding_model', 'all-MiniLM-L6-v2')
    
    # 방법에 따른 enhancer 선택
    enhancers = {
        "paraphrasing": ParaphrasingEnhancer,
        "keyword_extraction": KeywordExtractionEnhancer,
        "embedding_based": EmbeddingBasedEnhancer,
        "query_to_question": QueryToQuestionEnhancer,
        "target_keyword": TargetKeywordEnhancer,
        "keyword_expansion": KeywordExpansionEnhancer,
        "hybrid": HybridEnhancer
    }
    
    if method not in enhancers:
        logger.warning(f"알 수 없는 보강 방법: {method}, 하이브리드 방식으로 대체")
        method = "hybrid"
    
    # enhancer 초기화 및 실행
    enhancer = enhancers[method](llm_model=llm_model, embedding_model=embedding_model)
    return enhancer.enhance(query, **kwargs)

# 사용 예시
if __name__ == "__main__":
    # 테스트 쿼리
    test_query = "Transhumanism simplifies human existence into a technical problem"
    
    # 각 보강 방법 테스트
    print(f"원본 쿼리: {test_query}\n")
    
    for method in ["paraphrasing", "keyword_extraction", "embedding_based", 
                  "query_to_question", "target_keyword", "keyword_expansion", "hybrid"]:
        print(f"\n== {method} 보강 결과 ==")
        enhanced = enhance_query(test_query, method=method)
        for i, q in enumerate(enhanced):
            print(f"{i}. {q}") 