import os
import re
import requests
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class UserContextManager:
    """
    Manages user-provided context that can be used in philosophical dialogues.
    Handles text files, URLs, and direct text input with automatic content type inference.
    """
    
    def __init__(self, max_context_length: int = 4000):
        """
        Initialize the context manager.
        
        Args:
            max_context_length: Maximum length of context to be included in prompts
        """
        self.max_context_length = max_context_length
        self.user_contexts = {}  # Dictionary to store user contexts by ID
        self.active_contexts = []  # List of active context IDs for current simulation
    
    def _infer_context_type_from_url(self, url: str) -> str:
        """
        URL 패턴으로 컨텍스트 타입 추론
        
        Args:
            url: URL to analyze
            
        Returns:
            Inferred context type
        """
        domain_patterns = {
            'news_article': [
                'news', 'cnn', 'bbc', 'reuters', 'cnbc', 'nbc', 'abc', 'fox',
                '/articles/', '/news/', 'newsroom', 'breaking', 'reuters.com',
                'bloomberg', 'wsj', 'nytimes', 'washingtonpost', 'guardian',
                'daily', 'times', 'herald', 'tribune', 'gazette'
            ],
            'academic_paper': [
                'arxiv', 'scholar', '.edu/', '/papers/', 'research', 'journal',
                'academic', 'pubmed', 'jstor', 'springer', 'elsevier',
                'ieee', 'acm', 'doi', 'manuscript', 'preprint', 'thesis'
            ],
            'policy_document': [
                '.gov', 'gov.', '/policy/', '/documents/', 'whitehouse',
                'congress', 'senate', 'house.gov', 'fda.gov', 'cdc.gov',
                'legislation', 'bill', 'act', 'regulation', 'directive'
            ]
        }
        
        url_lower = url.lower()
        for context_type, patterns in domain_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                logger.info(f"URL pattern matched: {context_type} for {url}")
                return context_type
        
        logger.info(f"No URL pattern matched for {url}, defaulting to general")
        return "general"
    
    def _infer_context_type_from_content(self, content: str, use_llm: bool = True) -> str:
        """
        컨텍스트 내용 분석으로 타입 추론 (LLM 우선, 규칙 기반 폴백)
        
        Args:
            content: Text content to analyze
            use_llm: Whether to use LLM for inference (default: True)
            
        Returns:
            Inferred context type
        """
        if len(content) < 50:  # 너무 짧으면 일반 텍스트
            return "general"
        
        # LLM 기반 추론 시도
        if use_llm:
            try:
                llm_result = self._infer_type_with_llm(content)
                if llm_result:
                    logger.info(f"LLM-based content analysis: {llm_result} (length: {len(content)})")
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM inference failed, falling back to rule-based: {str(e)}")
        
        # 규칙 기반 폴백
        return self._infer_type_with_rules(content)
    
    def _infer_type_with_llm(self, content: str) -> str:
        """
        LLM을 사용한 컨텍스트 타입 추론
        
        Args:
            content: Text content to analyze
            
        Returns:
            Inferred context type or None if failed
        """
        try:
            # LLM Manager 동적 임포트 (순환 임포트 방지)
            from ..models.llm.llm_manager import LLMManager
            
            llm_manager = LLMManager()
            
            # 처음 800자만 사용 (토큰 절약)
            sample_content = content[:800]
            
            system_prompt = """
You are a content classifier. Analyze the text and classify it into exactly one of these categories:
- academic_paper: Research papers, academic studies, scientific articles
- news_article: News reports, journalism, press releases
- policy_document: Legal documents, regulations, government policies
- general: Everything else (blogs, casual writing, etc.)

Reply with ONLY the category name, nothing else.
"""
            
            user_prompt = f"""
Classify this text:

{sample_content}

Category:"""
            
            response = llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-3.5-turbo",
                max_tokens=20,
                temperature=0.1  # 일관성을 위해 낮은 temperature
            )
            
            # 응답 정제
            result = response.strip().lower()
            
            # 유효한 타입인지 확인
            valid_types = ["academic_paper", "news_article", "policy_document", "general"]
            if result in valid_types:
                return result
            
            # 부분 매칭 시도
            for valid_type in valid_types:
                if valid_type in result:
                    return valid_type
            
            logger.warning(f"LLM returned invalid type: {result}")
            return None
            
        except ImportError:
            logger.warning("LLMManager not available, using rule-based inference")
            return None
        except Exception as e:
            logger.error(f"LLM inference error: {str(e)}")
            return None
    
    def _infer_type_with_rules(self, content: str) -> str:
        """
        규칙 기반 컨텍스트 타입 추론 (폴백용)
        
        Args:
            content: Text content to analyze
            
        Returns:
            Inferred context type
        """
        content_lower = content.lower()
        
        # Academic paper indicators (더 구체적으로)
        academic_indicators = [
            'abstract', 'introduction', 'methodology', 'results', 'conclusion',
            'references', 'bibliography', 'doi:', 'journal', 'volume',
            'pp.', 'et al.', 'research', 'study', 'analysis', 'hypothesis',
            'figure', 'table', 'appendix', 'manuscript', 'peer review',
            'experiment', 'dataset', 'algorithm', 'findings', 'survey'
        ]
        
        # News article indicators (더 포괄적으로)
        news_indicators = [
            'breaking', 'reporter', 'correspondent', 'newsroom', 'reuters',
            'associated press', 'ap news', 'published', 'updated', 'sources say',
            'according to', 'spokesperson', 'statement', 'press release',
            'developing story', 'live updates', 'announced', 'confirms'  # 추가
        ]
        
        # Policy document indicators
        policy_indicators = [
            'policy', 'regulation', 'directive', 'legislation', 'bill',
            'act', 'law', 'statute', 'amendment', 'section', 'subsection',
            'whereas', 'therefore', 'hereby', 'enacted', 'congress',
            'senate', 'government', 'official', 'federal', 'state'
        ]
        
        # Count indicators
        academic_score = sum(1 for indicator in academic_indicators if indicator in content_lower)
        news_score = sum(1 for indicator in news_indicators if indicator in content_lower)
        policy_score = sum(1 for indicator in policy_indicators if indicator in content_lower)
        
        # 길이에 따른 가중치 적용 (짧은 텍스트에 더 관대하게)
        length_factor = min(1.0, len(content) / 500)  # 500자 기준으로 정규화
        min_threshold = max(1, int(2 * length_factor))  # 최소 1개 이상 (기존 2에서 조정)
        
        # Determine type based on highest score
        scores = {
            'academic_paper': academic_score,
            'news_article': news_score,
            'policy_document': policy_score
        }
        
        max_score = max(scores.values())
        if max_score >= min_threshold:  # 동적 임계값 사용
            inferred_type = max(scores, key=scores.get)
            logger.info(f"Rule-based content analysis: {inferred_type} (scores: {scores}, threshold: {min_threshold}, length: {len(content)})")
            return inferred_type
        
        logger.info(f"Rule-based content analysis: general (scores too low: {scores}, threshold: {min_threshold}, length: {len(content)})")
        return "general"
    
    def add_text_context(self, text: str, title: str = "User Input") -> str:
        """
        Add directly provided text as context with automatic type inference.
        
        Args:
            text: The text content to add
            title: A title for this context
            
        Returns:
            The ID of the added context
        """
        context_id = f"ctx_{len(self.user_contexts) + 1}"
        
        # 🆕 내용 기반 타입 판별
        inferred_type = self._infer_context_type_from_content(text)
        
        self.user_contexts[context_id] = {
            "title": title,
            "type": "text",
            "content_type": inferred_type,  # 🆕 추가
            "content": text,
            "source": "user_input",
            "excerpt_length": min(len(text), self.max_context_length)
        }
        
        if context_id not in self.active_contexts:
            self.active_contexts.append(context_id)
        
        logger.info(f"Added text context '{title}' with inferred type: {inferred_type}")
        return context_id
    
    def add_file_context(self, file_path: str) -> str:
        """
        Add context from a text file with automatic type inference.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            The ID of the added context
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_name = os.path.basename(file_path)
            context_id = f"ctx_{len(self.user_contexts) + 1}"
            
            # 🆕 파일 확장자와 내용 기반 타입 판별
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.pdf':
                # PDF는 일반적으로 academic paper일 가능성이 높음
                inferred_type = "academic_paper"
            else:
                inferred_type = self._infer_context_type_from_content(content)
            
            self.user_contexts[context_id] = {
                "title": file_name,
                "type": "file",
                "content_type": inferred_type,  # 🆕 추가
                "content": content,
                "source": file_path,
                "excerpt_length": min(len(content), self.max_context_length)
            }
            
            if context_id not in self.active_contexts:
                self.active_contexts.append(context_id)
            
            logger.info(f"Added file context '{file_name}' with inferred type: {inferred_type}")
            return context_id
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    def add_url_context(self, url: str) -> str:
        """
        Add context from a URL with automatic type inference.
        
        Args:
            url: URL to extract content from
            
        Returns:
            The ID of the added context
        """
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
                
            # Get main text content
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Get page title
            title = soup.title.string if soup.title else url
            
            context_id = f"ctx_{len(self.user_contexts) + 1}"
            
            # Truncate content if needed
            truncated_content = content[:self.max_context_length]
            
            # 🆕 URL 패턴과 내용 기반 타입 판별 (URL 우선)
            inferred_type = self._infer_context_type_from_url(url)
            if inferred_type == "general" and truncated_content:
                # URL 패턴으로 판별 안되면 내용으로 재시도
                content_type = self._infer_context_type_from_content(truncated_content)
                if content_type != "general":
                    inferred_type = content_type
            
            self.user_contexts[context_id] = {
                "title": title,
                "type": "url",
                "content_type": inferred_type,  # 🆕 추가
                "content": truncated_content,
                "source": url,
                "excerpt_length": min(len(content), self.max_context_length)
            }
            
            if context_id not in self.active_contexts:
                self.active_contexts.append(context_id)
            
            logger.info(f"Added URL context '{title}' with inferred type: {inferred_type}")
            return context_id
            
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            raise
    
    def get_context_type(self, context_id: str) -> Optional[str]:
        """
        Get the inferred content type for a specific context.
        
        Args:
            context_id: ID of the context
            
        Returns:
            The inferred content type or None if context not found
        """
        context = self.user_contexts.get(context_id)
        if context:
            return context.get("content_type", "general")
        return None
    
    def get_active_context_types(self) -> Dict[str, str]:
        """
        Get content types for all active contexts.
        
        Returns:
            Dictionary mapping context_id to content_type
        """
        types = {}
        for ctx_id in self.active_contexts:
            context_type = self.get_context_type(ctx_id)
            if context_type:
                types[ctx_id] = context_type
        return types
    
    def get_most_common_context_type(self) -> str:
        """
        Get the most common content type among active contexts.
        
        Returns:
            The most common content type or "general" if no active contexts
        """
        if not self.active_contexts:
            return "general"
        
        type_counts = {}
        for ctx_id in self.active_contexts:
            context_type = self.get_context_type(ctx_id)
            if context_type:
                type_counts[context_type] = type_counts.get(context_type, 0) + 1
        
        if type_counts:
            most_common = max(type_counts, key=type_counts.get)
            logger.info(f"Most common context type: {most_common} (counts: {type_counts})")
            return most_common
        
        return "general"
    
    def set_active_contexts(self, context_ids: List[str]):
        """
        Set which contexts should be active for the current simulation.
        
        Args:
            context_ids: List of context IDs to activate
        """
        # Verify all IDs exist
        for ctx_id in context_ids:
            if ctx_id not in self.user_contexts:
                raise ValueError(f"Context ID {ctx_id} does not exist")
                
        self.active_contexts = context_ids.copy()
    
    def get_relevant_contexts(self, topic: str, max_contexts: int = 3) -> List[Dict[str, Any]]:
        """
        Get contexts most relevant to the given topic.
        
        Args:
            topic: The topic to find relevant contexts for
            max_contexts: Maximum number of contexts to return
            
        Returns:
            List of relevant context dictionaries
        """
        if not self.active_contexts:
            return []
            
        # Simple keyword matching for now - in the future this could use embeddings
        scored_contexts = []
        keywords = re.findall(r'\b\w+\b', topic.lower())
        
        for ctx_id in self.active_contexts:
            context = self.user_contexts.get(ctx_id)
            if not context:
                continue
                
            content = context["content"].lower()
            score = sum(1 for keyword in keywords if keyword in content)
            scored_contexts.append((score, ctx_id))
            
        # Sort by relevance (descending)
        scored_contexts.sort(reverse=True)
        
        # Return the most relevant contexts
        result = []
        for _, ctx_id in scored_contexts[:max_contexts]:
            context = self.user_contexts[ctx_id].copy()
            # Calculate a short excerpt for display
            excerpt = self._generate_excerpt(context["content"], topic)
            context["excerpt"] = excerpt
            result.append(context)
            
        return result
    
    def get_all_contexts(self) -> List[Dict[str, Any]]:
        """
        Get all stored contexts.
        
        Returns:
            List of all context dictionaries
        """
        result = []
        for ctx_id, context in self.user_contexts.items():
            ctx_copy = context.copy()
            ctx_copy["id"] = ctx_id
            ctx_copy["active"] = ctx_id in self.active_contexts
            result.append(ctx_copy)
            
        return result
    
    def clear_contexts(self):
        """Clear all stored contexts."""
        self.user_contexts = {}
        self.active_contexts = []
    
    def remove_context(self, context_id: str):
        """
        Remove a specific context.
        
        Args:
            context_id: ID of the context to remove
        """
        if context_id in self.user_contexts:
            del self.user_contexts[context_id]
            
        if context_id in self.active_contexts:
            self.active_contexts.remove(context_id)
    
    def _generate_excerpt(self, content: str, topic: str, length: int = 200) -> str:
        """
        Generate a relevant excerpt from content.
        
        Args:
            content: Full content text
            topic: Topic to find relevant parts for
            length: Target length of excerpt
            
        Returns:
            A relevant excerpt from the content
        """
        # Very simplified relevance-based excerpt:
        keywords = set(re.findall(r'\b\w+\b', topic.lower()))
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Score sentences by keyword matches
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            matches = sum(1 for word in re.findall(r'\b\w+\b', sentence.lower()) if word in keywords)
            scored_sentences.append((matches, i, sentence))
            
        # Sort by most relevant
        scored_sentences.sort(reverse=True)
        
        # Take top sentences until we hit length limit
        excerpt = ""
        current_length = 0
        used_sentences = set()
        
        for _, i, sentence in scored_sentences:
            if i in used_sentences:
                continue
                
            if current_length + len(sentence) <= length or current_length == 0:
                excerpt += sentence + " "
                current_length += len(sentence) + 1
                used_sentences.add(i)
                
            if current_length >= length:
                break
                
        return excerpt.strip() 
 