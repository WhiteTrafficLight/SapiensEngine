"""
OpenAI Integration Service

Function Calling을 활용하여 단일 API 호출로 
토론에 필요한 모든 요소를 생성하는 서비스
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List
import openai
from openai import AsyncOpenAI
from pathlib import Path
import sys

# Add project root to Python path  
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.new.models.debate_models import (
    FastDebateRequest, DebatePackage, StanceStatements, 
    ContextSummary, PhilosopherProfile, ModeratorStyle
)

logger = logging.getLogger(__name__)

class OpenAIDebateService:
    """OpenAI API를 활용한 고속 토론 생성 서비스"""
    
    def __init__(self, api_key: Optional[str] = None, use_fine_tuned: bool = False):
        self.client = AsyncOpenAI(api_key=api_key)
        self.use_fine_tuned = use_fine_tuned
        self.fine_tuned_model = "ft:gpt-4o-mini-2024-07-18:your-org::your-model-id"  # 🔥 파인튜닝 모델 사용시
        self.base_model = "gpt-4o"
        
        # 모더레이터 스타일 매핑
        self.moderator_styles = {
            "0": {"name": "Jamie the Host", "personality": "casual, friendly, young"},
            "1": {"name": "Dr. Lee", "personality": "polite, academic, professional"},  
            "2": {"name": "Zuri Show", "personality": "energetic, entertaining, YouTuber"},
            "3": {"name": "Elias of the End", "personality": "serious, weighty, formal"},
            "4": {"name": "Miss Hana", "personality": "bright, educational, cheerful"}
        }
    
    async def generate_complete_debate_package(self, request: FastDebateRequest) -> DebatePackage:
        """🚀 단일 API 호출로 완전한 토론 패키지 생성"""
        
        start_time = time.time()
        
        # Function Calling을 위한 도구 정의
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_complete_debate_package",
                    "description": "Create a complete debate package with stance statements, context summary, and opening message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "stance_statements": {
                                "type": "object",
                                "properties": {
                                    "pro": {"type": "string", "description": "Pro stance statement"},
                                    "con": {"type": "string", "description": "Con stance statement"}
                                },
                                "required": ["pro", "con"]
                            },
                            "context_summary": {
                                "type": "object", 
                                "properties": {
                                    "summary": {"type": "string", "description": "Main content summary"},
                                    "key_points": {"type": "array", "items": {"type": "string"}},
                                    "relevant_quotes": {"type": "array", "items": {"type": "string"}}
                                }
                            },
                            "opening_message": {
                                "type": "string",
                                "description": "Complete moderator opening message"
                            }
                        },
                        "required": ["stance_statements", "opening_message"]
                    }
                }
            }
        ]
        
        # 모더레이터 스타일 정보 가져오기
        moderator_info = self.moderator_styles.get(request.moderator_style.value, self.moderator_styles["0"])
        
        # 시스템 프롬프트 (파인튜닝 vs 기본 모델)
        if self.use_fine_tuned:
            system_prompt = self._get_fine_tuned_system_prompt(moderator_info)
        else:
            system_prompt = self._get_base_system_prompt(moderator_info)
        
        # 사용자 프롬프트 구성
        user_prompt = self._build_user_prompt(request)
        
        try:
            # 🔥 단일 API 호출로 모든 것 생성
            model_to_use = self.fine_tuned_model if self.use_fine_tuned else self.base_model
            
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "create_complete_debate_package"}},
                max_tokens=4000,
                temperature=0.7
            )
            
            api_time = time.time() - start_time
            
            # Function Call 결과 파싱
            debate_package = self._parse_function_call_response(response, api_time)
            
            logger.info(f"✅ Complete debate package generated in {api_time:.2f}s")
            return debate_package
            
        except Exception as e:
            logger.error(f"❌ Error generating debate package: {str(e)}")
            # 폴백: 기본 패키지 반환
            return self._create_fallback_package(request, time.time() - start_time)
    
    def _get_base_system_prompt(self, moderator_info: Dict[str, str]) -> str:
        """기본 모델용 시스템 프롬프트"""
        return f"""You are {moderator_info['name']}, a debate moderator with a {moderator_info['personality']} style.

Your task is to create a COMPLETE debate package including:
1. Balanced pro/con stance statements for the topic
2. Context summary (if context provided)  
3. Complete opening message that introduces the debate professionally
4. Brief philosopher profiles for participants

Requirements:
- Generate balanced, fair stance statements
- Create engaging, comprehensive opening message
- Match your personality style: {moderator_info['personality']}
- Write in the same language as the debate topic
- Ensure opening message is complete and doesn't cut off mid-sentence

Use the create_complete_debate_package function to return structured results."""

    def _get_fine_tuned_system_prompt(self, moderator_info: Dict[str, str]) -> str:
        """파인튜닝 모델용 간소화된 프롬프트"""
        return f"""Generate complete debate package as {moderator_info['name']} ({moderator_info['personality']})."""
    
    def _build_user_prompt(self, request: FastDebateRequest) -> str:
        """사용자 프롬프트 구성"""
        
        # 참가자 정보
        pro_participants = ", ".join(request.pro_npcs)
        con_participants = ", ".join(request.con_npcs)
        
        # 컨텍스트 처리
        context_section = ""
        if request.context.strip():
            if request.context_type.value == "url":
                # URL에서 텍스트 추출
                extracted_text = self._extract_text_from_url(request.context)
                context_section = f"\nContext (extracted from URL): {extracted_text}"
            else:
                context_section = f"\nContext: {request.context}"
        
        return f"""Create a complete debate package for this topic:

TOPIC: {request.title}
{context_section}

PARTICIPANTS:
- PRO side: {pro_participants}
- CON side: {con_participants}

REQUIREMENTS:
1. Create balanced pro/con stance statements
2. {f"Summarize the provided context" if request.context.strip() else "No context to summarize"}
3. Generate complete opening message that:
   - Introduces the topic and its importance
   - Presents both sides fairly
   - Introduces all participants
   - Sets expectations for respectful debate
   - Calls on PRO side to start first

Language: Write everything in the SAME LANGUAGE as the topic title.
Style: Match your personality and speaking style consistently.

Use the create_complete_debate_package function to provide structured output."""
    
    def _extract_text_from_url(self, url: str) -> str:
        """URL에서 텍스트 추출 (기존 시스템과 동일한 방식)"""
        try:
            import requests
            from bs4 import BeautifulSoup
            import re
            
            # User-Agent 헤더 추가하여 403 Forbidden 에러 방지
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
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\s{3,}', ' ', text)
            
            # 텍스트 길이 제한 (너무 길면 앞부분만 사용)
            max_length = 8000  # 약 8000자로 제한
            if len(text) > max_length:
                text = text[:max_length] + "... (텍스트가 길어서 일부만 표시됨)"
            
            logger.info(f"URL processing completed: {len(text)} characters extracted from {url}")
            return text
            
        except ImportError:
            logger.error("requests or BeautifulSoup not available for URL processing")
            return f"URL 처리를 위한 라이브러리가 설치되지 않았습니다. (URL: {url})"
        except Exception as e:
            logger.error(f"URL processing failed for {url}: {str(e)}")
            return f"URL 처리 실패: {str(e)} (URL: {url})"
    
    def _parse_function_call_response(self, response, api_time: float) -> DebatePackage:
        """Function Call 응답 파싱"""
        
        try:
            # Function call 결과 추출
            function_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(function_call.function.arguments)
            
            # DebatePackage 구성
            stance_statements = StanceStatements(**function_args["stance_statements"])
            
            context_summary = None
            if "context_summary" in function_args and function_args["context_summary"]:
                context_summary = ContextSummary(**function_args["context_summary"])
            
            return DebatePackage(
                stance_statements=stance_statements,
                context_summary=context_summary,
                opening_message=function_args["opening_message"],
                generation_time=api_time,
                system_version="v2_fast"
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing function call response: {str(e)}")
            # JSON 파싱 실패시 텍스트에서 추출 시도
            return self._extract_from_text_response(response, api_time)
    
    def _extract_from_text_response(self, response, api_time: float) -> DebatePackage:
        """텍스트 응답에서 정보 추출 (폴백)"""
        
        text_response = response.choices[0].message.content
        
        # 간단한 패턴 매칭으로 추출 (개선 가능)
        stance_statements = StanceStatements(
            pro="Supporting this topic has merit and deserves consideration.",
            con="This topic raises concerns that need careful examination."
        )
        
        return DebatePackage(
            stance_statements=stance_statements,
            context_summary=None,
            opening_message=text_response[:1000] if text_response else "Welcome to today's debate.",
            generation_time=api_time,
            system_version="v2_fast_fallback"
        )
    
    def _create_fallback_package(self, request: FastDebateRequest, generation_time: float) -> DebatePackage:
        """API 실패시 기본 패키지 생성"""
        
        stance_statements = StanceStatements(
            pro=f"The position supporting '{request.title}' presents compelling arguments worth considering.",
            con=f"The position opposing '{request.title}' raises important concerns that must be addressed."
        )
        
        opening_message = f"""Welcome to today's debate on '{request.title}'.
        
We have distinguished participants representing both sides of this important issue.
Today's discussion will help us explore different perspectives and deepen our understanding.

Let's begin with the pro side presenting their opening arguments."""
        
        return DebatePackage(
            stance_statements=stance_statements,
            context_summary=None,
            opening_message=opening_message,
            generation_time=generation_time,
            system_version="v2_fast_fallback"
        )

    async def test_model_performance(self, test_cases: List[FastDebateRequest]) -> Dict[str, Any]:
        """모델 성능 테스트"""
        
        results = []
        total_start = time.time()
        
        for i, request in enumerate(test_cases):
            start_time = time.time()
            
            try:
                package = await self.generate_complete_debate_package(request)
                generation_time = time.time() - start_time
                
                results.append({
                    "test_case": i + 1,
                    "topic": request.title,
                    "generation_time": generation_time,
                    "success": True,
                    "opening_length": len(package.opening_message),
                    "has_context_summary": package.context_summary is not None
                })
                
            except Exception as e:
                results.append({
                    "test_case": i + 1,
                    "topic": request.title,
                    "generation_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                })
        
        total_time = time.time() - total_start
        
        return {
            "total_time": total_time,
            "average_time": total_time / len(test_cases),
            "success_rate": sum(1 for r in results if r["success"]) / len(results),
            "results": results
        } 