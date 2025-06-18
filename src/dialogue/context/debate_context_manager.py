"""
컨텍스트 매니저

UserContextManager를 확장하여 객관적인 컨텍스트 요약 및 관리 기능을 제공합니다.
"""

import logging
import re
import math
from typing import Dict, List, Any, Optional, Union
from ...utils.context_manager import UserContextManager
from .summary_templates import SummaryTemplates

logger = logging.getLogger(__name__)

class DebateContextManager(UserContextManager):
    """
    컨텍스트 매니저
    
    UserContextManager를 확장하여 객관적인 컨텍스트 요약 기능을 추가:
    - 주제 기반 컨텍스트 요약
    - 적응적 요약 전략 (길이에 따른 계층적 요약)
    - 불렛포인트 형태의 핵심 정보 추출
    """
    
    def __init__(self, llm_manager, max_context_length: int = 4000, max_summary_points: int = 5):
        """
        컨텍스트 매니저 초기화
        
        Args:
            llm_manager: LLM 관리자 (요약 생성용)
            max_context_length: 최대 컨텍스트 길이
            max_summary_points: 최대 요약 포인트 수
        """
        super().__init__(max_context_length)
        self.llm_manager = llm_manager
        self.max_summary_points = max_summary_points
        
        # 적응적 요약 설정
        self.short_context_threshold = 3000  # 3000자 미만은 단일 요약
        self.chunk_size = 2000  # 청크 크기 증대 (1200 → 2000)
        self.chunk_overlap = 300  # 청크간 오버랩 증대
        
        # 과도한 컨텍스트 보호 설정
        self.max_processable_length = 50000  # 최대 처리 가능 길이 (50KB)
        self.max_chunks_per_level = 15  # 레벨당 최대 청크 수
        self.max_llm_calls = 25  # 최대 LLM 호출 횟수 제한
        
        # 캐시된 요약들
        self.summaries = {}  # {cache_key: summary}
        self.context_bullet_points = {}  # {context_id: [bullet_points]}
        
        logger.info(f"ContextManager initialized with enhanced safeguards")
        logger.info(f"Max processable length: {self.max_processable_length:,} chars")
        logger.info(f"Max LLM calls per request: {self.max_llm_calls}")
    
    def generate_summary(self, topic: str, context_type: str = None) -> Dict[str, str]:
        """
        주제를 기반으로 객관적인 컨텍스트 요약 생성
        
        Args:
            topic: 주제
            context_type: 컨텍스트 타입 (None이면 자동 판별된 타입 사용)
        
        Returns:
            객관적 요약 딕셔너리 {"summary": summary_text}
        """
        if not self.active_contexts:
            logger.warning("No active contexts available for summary generation")
            return {"summary": ""}
        
        # 🆕 context_type이 None이면 자동 판별된 타입 사용
        if context_type is None:
            context_type = self._determine_best_context_type()
            logger.info(f"Auto-determined context type: {context_type}")
        
        # 캐시 확인 (타입 포함)
        cache_key = f"{topic}_{context_type}_{hash(str(sorted(self.active_contexts)))}"
        if cache_key in self.summaries:
            logger.info(f"Using cached summary for topic: {topic} (type: {context_type})")
            return self.summaries[cache_key]
        
        # 모든 활성 컨텍스트 통합
        combined_context = self._combine_active_contexts()
        
        if not combined_context.strip():
            logger.warning("Combined context is empty")
            return {"summary": ""}
        
        # 컨텍스트 길이 확인 및 전략 결정
        context_length = len(combined_context)
        logger.info(f"Combined context length: {context_length:,} chars")
        
        # 과도한 컨텍스트 길이 처리
        if context_length > self.max_processable_length:
            logger.warning(f"Context too long ({context_length:,} chars), truncating to {self.max_processable_length:,} chars")
            combined_context = self._truncate_context_intelligently(combined_context)
            context_length = len(combined_context)
            logger.info(f"Truncated context length: {context_length:,} chars")
        
        try:
            logger.info(f"Generating objective summary for topic: {topic} with context type: {context_type}")
            
            if context_length < self.short_context_threshold:
                # 짧은 컨텍스트: 단일 요약
                summary = self._generate_single_summary(
                    combined_context, topic, context_type
                )
            else:
                # 긴 컨텍스트: 계층적 요약
                summary = self._generate_hierarchical_summary(
                    combined_context, topic, context_type
                )
            
            result = {"summary": summary}
            logger.info(f"Generated objective summary with {len(summary.split('•')) - 1} bullet points")
            
            # 캐시에 저장
            self.summaries[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating objective summary: {str(e)}")
            return {"summary": f"요약 생성 실패: {str(e)}"}
    
    def _determine_best_context_type(self) -> str:
        """
        활성 컨텍스트들에서 최적의 컨텍스트 타입 결정
        
        Returns:
            결정된 컨텍스트 타입
        """
        if not self.active_contexts:
            return None
        
        # 가장 흔한 타입 사용 (UserContextManager의 메서드 활용)
        most_common_type = self.get_most_common_context_type()
        
        if most_common_type and most_common_type != "general":
            logger.info(f"Using most common context type: {most_common_type}")
            return most_common_type
        
        # 모든 타입이 general이거나 타입 정보가 없으면 첫 번째 컨텍스트 타입 사용
        first_context = self.user_contexts.get(self.active_contexts[0])
        if first_context:
            inferred_type = first_context.get("content_type", None)
            if inferred_type:
                logger.info(f"Using first context type: {inferred_type}")
                return inferred_type
        
        logger.info("No specific context type determined, using None (general template)")
        return None
    
    def get_context_type_summary(self) -> Dict[str, Any]:
        """
        현재 활성 컨텍스트들의 타입 분포 요약
        
        Returns:
            타입별 통계 정보
        """
        if not self.active_contexts:
            return {"total_contexts": 0, "type_distribution": {}, "determined_type": None}
        
        # 타입 분포 계산
        type_counts = {}
        for ctx_id in self.active_contexts:
            context = self.user_contexts.get(ctx_id)
            if context:
                content_type = context.get("content_type", "unknown")
                type_counts[content_type] = type_counts.get(content_type, 0) + 1
        
        # 결정된 타입
        determined_type = self._determine_best_context_type()
        
        return {
            "total_contexts": len(self.active_contexts),
            "type_distribution": type_counts,
            "determined_type": determined_type,
            "context_details": [
                {
                    "id": ctx_id,
                    "title": self.user_contexts[ctx_id].get("title", "Unknown"),
                    "source_type": self.user_contexts[ctx_id].get("type", "unknown"),
                    "content_type": self.user_contexts[ctx_id].get("content_type", "unknown"),
                    "length": len(self.user_contexts[ctx_id].get("content", ""))
                }
                for ctx_id in self.active_contexts
                if ctx_id in self.user_contexts
            ]
        }
    
    # 하위 호환성을 위한 별칭
    def generate_debate_summary(self, topic: str, stance_statements: Dict[str, str] = None, 
                               context_type: str = None) -> Dict[str, str]:
        """하위 호환성을 위한 메서드 - generate_summary 호출"""
        return self.generate_summary(topic, context_type)
    
    def _generate_single_summary(self, context: str, topic: str, context_type: str = None) -> str:
        """
        단일 요약 생성 (짧은 컨텍스트용)
        """
        try:
            template = SummaryTemplates.get_template(context_type=context_type)
            prompt = template.format(context=context, topic=topic)
            
            # 컨텍스트 길이에 따른 토큰 수 조정
            estimated_tokens = self._estimate_tokens(context)
            max_tokens = min(1200, max(400, estimated_tokens // 3))  # 입력의 1/3 정도
            
            summary = self.llm_manager.generate_response(
                system_prompt="You are a helpful assistant that creates concise, accurate summaries.",
                user_prompt=prompt,
                llm_model="gpt-4",
                max_tokens=max_tokens
            )
            
            # 불렛 포인트 추출 및 정제
            bullet_points = self._extract_bullet_points(summary)
            return "\n".join(bullet_points)
            
        except Exception as e:
            logger.error(f"Error in single summary generation: {str(e)}")
            return f"단일 요약 생성 실패: {str(e)}"
    
    def _generate_hierarchical_summary(self, context: str, topic: str, context_type: str = None) -> str:
        """
        계층적 요약 생성 (긴 컨텍스트용) - 청크 수 제한 적용
        """
        try:
            logger.info(f"Starting hierarchical summarization")
            
            # 1단계: 컨텍스트를 청크로 분할
            chunks = self._split_into_chunks(context)
            original_chunk_count = len(chunks)
            
            # 청크 수 제한 적용
            if len(chunks) > self.max_chunks_per_level:
                logger.warning(f"Too many chunks ({len(chunks)}), limiting to {self.max_chunks_per_level}")
                # 중요한 부분 우선으로 청크 선택
                chunks = self._select_most_important_chunks(chunks, self.max_chunks_per_level)
            
            logger.info(f"Processing {len(chunks)}/{original_chunk_count} chunks")
            
            # LLM 호출 횟수 확인
            estimated_calls = len(chunks) + 1  # 청크별 요약 + 최종 요약
            if estimated_calls > self.max_llm_calls:
                logger.error(f"Estimated LLM calls ({estimated_calls}) exceeds limit ({self.max_llm_calls})")
                return f"컨텍스트가 너무 길어서 요약할 수 없습니다. (예상 LLM 호출: {estimated_calls}회)"
            
            # 2단계: 각 청크별 부분 요약 생성
            partial_summaries = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} (length: {len(chunk):,} chars)")
                
                # 청크별 요약 프롬프트 생성
                chunk_prompt = self._create_chunk_summary_prompt(chunk, topic, context_type)
                
                chunk_summary = self.llm_manager.generate_response(
                    system_prompt="You are summarizing a part of a larger document. Focus on key facts and information.",
                    user_prompt=chunk_prompt,
                    llm_model="gpt-4",
                    max_tokens=400  # 청크별 토큰 수 축소 (600 → 400)
                )
                
                if chunk_summary.strip():
                    partial_summaries.append(chunk_summary)
            
            if not partial_summaries:
                logger.error("No partial summaries generated")
                return "계층적 요약 실패: 부분 요약 생성 안됨"
            
            # 3단계: 부분 요약들을 합쳐서 최종 요약 생성
            logger.info(f"Combining {len(partial_summaries)} partial summaries")
            combined_partial = "\n\n--- PARTIAL SUMMARY ---\n".join(partial_summaries)
            
            # 최종 요약 프롬프트
            final_prompt = self._create_final_summary_prompt(combined_partial, topic, context_type)
            
            final_summary = self.llm_manager.generate_response(
                system_prompt="You are creating a final summary by combining multiple partial summaries. Create a coherent, structured summary.",
                user_prompt=final_prompt,
                llm_model="gpt-4",
                max_tokens=800  # 최종 요약 토큰 수 축소 (1000 → 800)
            )
            
            # 불렛 포인트 추출 및 정제
            bullet_points = self._extract_bullet_points(final_summary)
            result = "\n".join(bullet_points)
            
            logger.info(f"Hierarchical summarization completed: {len(chunks)} chunks → {len(bullet_points)} bullet points")
            return result
            
        except Exception as e:
            logger.error(f"Error in hierarchical summary generation: {str(e)}")
            return f"계층적 요약 생성 실패: {str(e)}"
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """
        텍스트를 의미적으로 적절한 청크로 분할
        1. 문단 구조 우선 고려
        2. 다양한 구두점 인식
        3. 적절한 오버랩 적용
        """
        # 먼저 문단 단위로 시도
        paragraph_chunks = self._try_paragraph_based_chunking(text)
        if paragraph_chunks:
            return paragraph_chunks
        
        # 문단 기반이 안되면 개선된 문장 기반 분할
        return self._sentence_based_chunking(text)
    
    def _try_paragraph_based_chunking(self, text: str) -> List[str]:
        """
        문단 기반 청크화 시도
        """
        # 문단 분할 (다양한 패턴 인식)
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if len(paragraphs) < 2:
            return []  # 문단이 충분하지 않으면 실패
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 현재 청크에 문단을 추가했을 때의 길이
            potential_length = len(current_chunk) + len(paragraph) + 2  # \n\n 추가
            
            if potential_length <= self.chunk_size or not current_chunk:
                # 청크 크기 내이거나 첫 번째 문단이면 추가
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
            else:
                # 청크 크기를 초과하면 현재 청크를 저장하고 새 청크 시작
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk)
        
        # 오버랩 적용
        return self._apply_overlap_to_chunks(chunks, text)
    
    def _sentence_based_chunking(self, text: str) -> List[str]:
        """
        개선된 문장 기반 청크화
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 마지막 청크가 아니면 문장 경계에서 자르기
            if end < len(text):
                # 다양한 문장 끝 패턴 인식 (한국어 포함)
                sentence_end = self._find_best_sentence_boundary(text, start, end)
                if sentence_end > start + self.chunk_size // 3:  # 너무 짧지 않다면
                    end = sentence_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 다음 시작 위치 (오버랩 고려)
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _find_best_sentence_boundary(self, text: str, start: int, preferred_end: int) -> int:
        """
        최적의 문장 경계 찾기 (다양한 구두점 고려)
        """
        # 선호하는 구두점 순서 (강한 문장 끝 → 약한 문장 끝)
        sentence_endings = [
            r'[.!?。？！]\s+',  # 강한 문장 끝 + 공백
            r'[.!?。？！][\n\r]',  # 강한 문장 끝 + 줄바꿈
            r'[.!?。？！]$',  # 강한 문장 끝 + 텍스트 끝
            r'[.!?。？！]',  # 강한 문장 끝
            r'[;:][\s\n]',  # 세미콜론, 콜론 + 공백/줄바꿈
            r'\n\s*\n',  # 문단 경계
        ]
        
        search_start = max(start, preferred_end - self.chunk_size // 2)
        search_end = min(len(text), preferred_end + 100)  # 약간의 여유
        
        for pattern in sentence_endings:
            for match in re.finditer(pattern, text[search_start:search_end]):
                boundary = search_start + match.end()
                if start + self.chunk_size // 3 <= boundary <= preferred_end + 100:
                    return boundary
        
        # 적절한 경계를 찾지 못하면 원래 위치 반환
        return preferred_end
    
    def _apply_overlap_to_chunks(self, chunks: List[str], original_text: str) -> List[str]:
        """
        청크들에 오버랩 적용 (문단 기반 청크화용)
        """
        if not chunks or len(chunks) == 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]  # 첫 번째 청크는 그대로
        
        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            
            # 이전 청크의 마지막 부분을 현재 청크 앞에 추가
            prev_chunk = chunks[i-1]
            overlap_text = self._extract_overlap_text(prev_chunk)
            
            if overlap_text:
                overlapped_chunk = overlap_text + "\n\n" + current_chunk
            else:
                overlapped_chunk = current_chunk
            
            overlapped_chunks.append(overlapped_chunk)
        
        return overlapped_chunks
    
    def _extract_overlap_text(self, chunk: str) -> str:
        """
        청크에서 오버랩할 텍스트 추출 (마지막 문장들)
        """
        if len(chunk) <= self.chunk_overlap:
            return chunk
        
        # 마지막 부분에서 문장 경계 찾기
        overlap_start = len(chunk) - self.chunk_overlap
        sentences = re.split(r'[.!?。？！]\s+', chunk[overlap_start:])
        
        if len(sentences) > 1:
            # 완전한 문장들만 포함
            return '. '.join(sentences[1:])  # 첫 번째는 불완전할 수 있음
        else:
            # 문장 분할이 안되면 단순히 마지막 부분 사용
            return chunk[-self.chunk_overlap:]
    
    def _create_chunk_summary_prompt(self, chunk: str, topic: str, context_type: str = None) -> str:
        """청크별 요약 프롬프트 생성"""
        base_prompt = f"""
Summarize this text chunk for a debate on "{topic}".

TEXT CHUNK:
{chunk}

Create 2-3 bullet points focusing on:
- Key facts relevant to the debate topic
- Important data, statistics, or evidence
- Expert opinions or conclusions
"""
        
        base_prompt += """
Format as bullet points (•). Be concise but informative.
"""
        
        return base_prompt
    
    def _create_final_summary_prompt(self, partial_summaries: str, topic: str, context_type: str = None) -> str:
        """최종 요약 프롬프트 생성"""
        
        template = SummaryTemplates.get_template(context_type=context_type)
        return template.format(context=partial_summaries, topic=topic)
    
    def _estimate_tokens(self, text: str) -> int:
        """
        텍스트의 대략적인 토큰 수 추정 (1 토큰 ≈ 4자)
        """
        return len(text) // 4
    
    def get_context_bullet_points(self, max_points: int = None) -> List[str]:
        """
        현재 활성 컨텍스트들의 핵심 포인트를 불렛 형태로 반환
        
        Args:
            max_points: 최대 반환할 포인트 수
        
        Returns:
            불렛 포인트 리스트
        """
        max_points = max_points or self.max_summary_points
        
        if not self.active_contexts:
            return []
        
        all_bullet_points = []
        
        for ctx_id in self.active_contexts:
            if ctx_id in self.context_bullet_points:
                # 캐시된 불렛 포인트 사용
                all_bullet_points.extend(self.context_bullet_points[ctx_id])
            else:
                # 새로 생성
                context = self.user_contexts.get(ctx_id)
                if context:
                    bullet_points = self._generate_bullet_points_for_context(context)
                    self.context_bullet_points[ctx_id] = bullet_points
                    all_bullet_points.extend(bullet_points)
        
        # 중복 제거 및 길이 제한
        unique_points = []
        seen = set()
        
        for point in all_bullet_points:
            point_key = point.lower().strip("• ").strip()
            if point_key not in seen and len(unique_points) < max_points:
                unique_points.append(point)
                seen.add(point_key)
        
        return unique_points[:max_points]
    
    def get_context_for_prompt(self, topic: str = "", include_full_context: bool = False) -> Dict[str, Any]:
        """
        프롬프트에 포함할 컨텍스트 정보 반환
        
        Args:
            topic: 주제  
            include_full_context: 전체 컨텍스트 포함 여부
        
        Returns:
            프롬프트용 컨텍스트 딕셔너리
        """
        result = {
            "has_context": len(self.active_contexts) > 0,
            "summary": "",
            "bullet_points": [],
            "full_context": "",
            "context_length": 0,
            "summarization_strategy": "none"
        }
        
        if not self.active_contexts:
            return result
        
        # 컨텍스트 길이 정보 추가
        combined_context = self._combine_active_contexts()
        result["context_length"] = len(combined_context)
        result["summarization_strategy"] = "single" if len(combined_context) < self.short_context_threshold else "hierarchical"
        
        # 객관적 요약
        if topic:
            result["summary"] = self.get_objective_summary(topic)
        
        # 불렛 포인트
        result["bullet_points"] = self.get_context_bullet_points()
        
        # 전체 컨텍스트 (옵션)
        if include_full_context:
            result["full_context"] = combined_context
        
        return result
    
    def refresh_summaries(self, topic: str = None):
        """
        캐시된 요약들 새로고침
        
        Args:
            topic: 특정 주제만 새로고침 (None이면 전체)
        """
        if topic:
            # 특정 주제와 관련된 캐시만 삭제
            keys_to_remove = [key for key in self.summaries.keys() if key.startswith(topic)]
            for key in keys_to_remove:
                del self.summaries[key]
            logger.info(f"Refreshed summaries for topic: {topic}")
        else:
            # 전체 캐시 삭제
            self.summaries.clear()
            self.context_bullet_points.clear()
            logger.info("Refreshed all cached summaries")
    
    def _combine_active_contexts(self) -> str:
        """활성 컨텍스트들을 하나의 텍스트로 통합"""
        combined = []
        
        for ctx_id in self.active_contexts:
            context = self.user_contexts.get(ctx_id)
            if context:
                title = context.get("title", "Unknown")
                content = context.get("content", "")
                
                # 컨텍스트별 구분을 위한 헤더 추가
                combined.append(f"=== {title} ===")
                combined.append(content)
                combined.append("")  # 빈 줄로 구분
        
        return "\n".join(combined)
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """텍스트에서 불렛 포인트 추출 및 정제"""
        lines = text.split('\n')
        bullet_points = []
        
        for line in lines:
            line = line.strip()
            # 불렛 포인트 식별 (•, -, *, 숫자 등)
            if re.match(r'^[•\-\*]\s+|^\d+[\.\)]\s+', line):
                # 불렛 마커 정규화
                cleaned = re.sub(r'^[•\-\*\d\.\)]+\s*', '• ', line)
                if cleaned.strip() and len(cleaned) > 3:  # 의미있는 내용만
                    bullet_points.append(cleaned)
        
        # 불렛 포인트가 없으면 첫 번째 몇 문장을 불렛으로 변환
        if not bullet_points:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for i, sentence in enumerate(sentences[:self.max_summary_points]):
                if sentence.strip() and len(sentence) > 10:
                    bullet_points.append(f"• {sentence.strip()}")
        
        return bullet_points[:self.max_summary_points]
    
    def _generate_bullet_points_for_context(self, context: Dict[str, Any]) -> List[str]:
        """단일 컨텍스트에서 불렛 포인트 생성 (적응적 전략 사용)"""
        content = context.get("content", "")
        title = context.get("title", "")
        
        if not content.strip():
            return []
        
        try:
            # 컨텍스트 길이에 따른 전략 결정
            if len(content) < self.short_context_threshold:
                # 짧은 컨텍스트: 단일 요청
                prompt = f"""
Create 2-3 key bullet points from the following content:

TITLE: {title}
CONTENT: {content}

Format as:
• [Point 1]
• [Point 2]  
• [Point 3]

Focus on the most important factual information.
"""
                
                summary = self.llm_manager.generate_response(
                    system_prompt="You are a helpful assistant that extracts key points from text.",
                    user_prompt=prompt,
                    llm_model="gpt-4",
                    max_tokens=400
                )
                
                return self._extract_bullet_points(summary)
            else:
                # 긴 컨텍스트: 계층적 처리
                chunks = self._split_into_chunks(content)
                all_points = []
                
                for chunk in chunks[:3]:  # 최대 3개 청크만 처리
                    prompt = f"""
Create 1-2 key bullet points from this text chunk:

{chunk}

Format as bullet points (•). Focus on the most important information.
"""
                    
                    summary = self.llm_manager.generate_response(
                        system_prompt="You are extracting key points from a text chunk.",
                        user_prompt=prompt,
                        llm_model="gpt-4",
                        max_tokens=200
                    )
                    
                    points = self._extract_bullet_points(summary)
                    all_points.extend(points)
                
                # 중복 제거하고 최대 3개만 반환
                unique_points = []
                seen = set()
                for point in all_points:
                    point_key = point.lower().strip("• ").strip()
                    if point_key not in seen and len(unique_points) < 3:
                        unique_points.append(point)
                        seen.add(point_key)
                
                return unique_points
                
        except Exception as e:
            logger.error(f"Error generating bullet points for context {title}: {str(e)}")
            
            # 폴백: 첫 번째 문장들을 불렛으로 변환
            sentences = re.split(r'(?<=[.!?])\s+', content)
            bullet_points = []
            for sentence in sentences[:3]:
                if sentence.strip() and len(sentence) > 20:
                    bullet_points.append(f"• {sentence.strip()}")
            
            return bullet_points
    
    def get_context_stats(self) -> Dict[str, Any]:
        """컨텍스트 통계 정보 반환 (디버깅용)"""
        combined_length = len(self._combine_active_contexts()) if self.active_contexts else 0
        
        return {
            "total_contexts": len(self.user_contexts),
            "active_contexts": len(self.active_contexts),
            "combined_context_length": combined_length,
            "summarization_strategy": "single" if combined_length < self.short_context_threshold else "hierarchical",
            "short_context_threshold": self.short_context_threshold,
            "chunk_size": self.chunk_size,
            "cached_summaries": len(self.summaries),
            "cached_bullet_points": len(self.context_bullet_points),
            "max_summary_points": self.max_summary_points,
            "context_details": [
                {
                    "id": ctx_id,
                    "title": ctx.get("title", "Unknown"),
                    "type": ctx.get("type", "unknown"),
                    "length": len(ctx.get("content", "")),
                    "active": ctx_id in self.active_contexts
                }
                for ctx_id, ctx in self.user_contexts.items()
            ]
        }

    def get_objective_summary(self, topic: str = "", context_type: str = None) -> str:
        """
        객관적인 컨텍스트 요약 반환 (새로운 간편 메서드)
        
        Args:
            topic: 토론 주제
            context_type: 컨텍스트 타입
        
        Returns:
            객관적 요약 텍스트
        """
        if not topic:
            # 토론 주제가 없으면 일반적인 불렛 포인트 반환
            bullet_points = self.get_context_bullet_points()
            return "\n".join(bullet_points)
        
        # 객관적 요약 생성
        result = self.generate_summary(topic, context_type=context_type)
        return result.get("summary", "")
    
    def _truncate_context_intelligently(self, context: str) -> str:
        """
        컨텍스트를 지능적으로 자르기
        - 앞부분 (도입부) 유지
        - 중간 부분 압축
        - 끝부분 (결론) 유지
        """
        target_length = self.max_processable_length
        
        if len(context) <= target_length:
            return context
        
        # 앞부분 30%, 끝부분 30%, 중간 40% 비율로 분배
        front_size = int(target_length * 0.3)
        back_size = int(target_length * 0.3)
        middle_size = target_length - front_size - back_size
        
        # 문단 단위로 자르기 시도
        paragraphs = context.split('\n\n')
        
        # 앞부분 확보
        front_text = ""
        for para in paragraphs:
            if len(front_text) + len(para) < front_size:
                front_text += para + "\n\n"
            else:
                break
        
        # 끝부분 확보
        back_text = ""
        for para in reversed(paragraphs):
            if len(back_text) + len(para) < back_size:
                back_text = para + "\n\n" + back_text
            else:
                break
        
        # 중간 부분 샘플링
        remaining_paras = paragraphs[len(front_text.split('\n\n')):len(paragraphs)-len(back_text.split('\n\n'))]
        middle_text = ""
        
        if remaining_paras and middle_size > 0:
            # 중간 문단들을 균등하게 샘플링
            step = max(1, len(remaining_paras) // (middle_size // 200))  # 대략 200자당 1문단
            sampled_paras = remaining_paras[::step]
            
            for para in sampled_paras:
                if len(middle_text) + len(para) < middle_size:
                    middle_text += para + "\n\n"
                else:
                    break
        
        truncated = front_text + middle_text + back_text
        
        # 여전히 너무 길면 단순 자르기
        if len(truncated) > target_length:
            truncated = truncated[:target_length]
        
        logger.info(f"Context truncated: {len(context):,} → {len(truncated):,} chars")
        return truncated.strip()
    
    def _select_most_important_chunks(self, chunks: List[str], max_chunks: int) -> List[str]:
        """
        가장 중요한 청크들 선택
        - 앞부분 (도입부)
        - 중간부분 (균등 샘플링)  
        - 끝부분 (결론)
        """
        if len(chunks) <= max_chunks:
            return chunks
        
        # 앞부분 3개, 끝부분 3개, 나머지는 중간에서 균등 샘플링
        front_count = min(3, max_chunks // 3)
        back_count = min(3, max_chunks // 3)
        middle_count = max_chunks - front_count - back_count
        
        selected_chunks = []
        
        # 앞부분 추가
        selected_chunks.extend(chunks[:front_count])
        
        # 중간부분 균등 샘플링
        if middle_count > 0 and len(chunks) > front_count + back_count:
            middle_chunks = chunks[front_count:len(chunks)-back_count]
            if middle_chunks:
                step = max(1, len(middle_chunks) // middle_count)
                sampled_middle = middle_chunks[::step][:middle_count]
                selected_chunks.extend(sampled_middle)
        
        # 끝부분 추가
        if back_count > 0:
            selected_chunks.extend(chunks[-back_count:])
        
        logger.info(f"Selected {len(selected_chunks)} most important chunks from {len(chunks)} total chunks")
        return selected_chunks 