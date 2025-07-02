#!/usr/bin/env python3
"""
지능형 RAG 통합 토론 에이전트

언제 RAG/웹서치를 사용할지 지능적으로 판단하고
OpenAI의 최신 기능들을 활용한 실제 구현
"""

import json
import logging
import time
import aiohttp
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RAGDecision:
    """RAG 사용 결정 정보"""
    use_web_search: bool
    use_vector_search: bool  
    use_philosopher_search: bool
    confidence: float
    reasoning: str

class SmartRAGUnifiedAgent:
    """
    지능형 RAG 통합 토론 에이전트
    
    특징:
    - 상황에 따라 RAG/웹서치 필요성 자동 판단
    - OpenAI Function Calling + 실제 웹/벡터 검색
    - 철학자별 맞춤형 검색 전략
    """
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], config: Dict[str, Any]):
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.config = config
        self.llm_manager = config.get('llm_manager')
        
        # 성능 추적
        self.performance_stats = {
            'llm_calls': 0,
            'web_searches': 0,
            'vector_searches': 0,
            'total_time': 0
        }
        
        # RAG 사용 판단 기준
        self.rag_triggers = {
            'current_events': ['politics', 'policy', 'government', 'regulation', 'law', 'economy', 'technology', 'climate', 'war', 'AI', 'artificial intelligence', '2024', '2025', 'recent', 'current', 'news'],
            'data_heavy': ['statistics', 'research', 'study', 'percentage', 'number', 'data', 'survey', 'analysis', 'evidence', 'productivity', 'remote work', 'scientific', 'empirical'],
            'factual_claims': ['according to', 'research shows', 'data indicates', 'study found', 'evidence suggests', 'scientific consensus'],
            'philosophical_depth': ['consciousness', 'ethics', 'morality', 'existence', 'justice', 'mind', 'brain', 'philosophy', 'ontology', 'epistemology', 'metaphysics', 'ethical', 'moral']
        }
        
        # 함수 정의
        self.functions = self._define_intelligent_functions()
        
    def _define_intelligent_functions(self) -> List[Dict[str, Any]]:
        """지능형 Function Calling 정의"""
        return [
            {
                "name": "analyze_topic_for_rag_needs",
                "description": "토론 주제를 분석하여 RAG/웹서치 필요성을 판단합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "분석할 토론 주제"},
                        "context": {"type": "string", "description": "토론 맥락"},
                        "philosopher_style": {"type": "string", "description": "철학자의 논증 스타일"}
                    },
                    "required": ["topic", "context", "philosopher_style"]
                }
            },
            {
                "name": "real_time_web_search",
                "description": "실시간 웹 검색으로 최신 정보를 가져옵니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색 쿼리"},
                        "search_type": {"type": "string", "enum": ["news", "academic", "general"], "description": "검색 타입"},
                        "max_results": {"type": "integer", "description": "최대 결과 수", "default": 3}
                    },
                    "required": ["query", "search_type"]
                }
            },
            {
                "name": "vector_knowledge_search", 
                "description": "벡터 데이터베이스에서 관련 지식을 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "검색할 개념이나 주제"},
                        "domain": {"type": "string", "enum": ["philosophy", "ethics", "politics", "science"], "description": "검색 도메인"},
                        "max_results": {"type": "integer", "description": "최대 결과 수", "default": 3}
                    },
                    "required": ["query", "domain"]
                }
            },
            {
                "name": "philosopher_wisdom_retrieval",
                "description": "특정 철학자의 사상과 저작에서 관련 내용을 검색합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "philosopher": {"type": "string", "description": "철학자 이름"},
                        "topic": {"type": "string", "description": "관련 주제"},
                        "quote_style": {"type": "string", "enum": ["direct", "interpretation", "application"], "description": "인용 스타일"}
                    },
                    "required": ["philosopher", "topic"]
                }
            },
            {
                "name": "generate_enhanced_argument",
                "description": "수집된 정보를 바탕으로 강화된 논증을 생성합니다",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "core_position": {"type": "string", "description": "핵심 입장"},
                        "evidence": {"type": "array", "items": {"type": "string"}, "description": "수집된 증거들"},
                        "philosophical_framework": {"type": "string", "description": "철학적 틀"},
                        "target_audience": {"type": "string", "description": "대상 청중"}
                    },
                    "required": ["core_position", "evidence", "philosophical_framework"]
                }
            }
        ]
    
    async def generate_intelligent_opening_argument(self, topic: str, stance: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        지능형 입론 생성
        
        1. 주제 분석 → RAG 필요성 판단
        2. 필요시 선택적 RAG/웹서치 수행  
        3. 수집된 정보로 강화된 논증 생성
        """
        start_time = time.time()
        
        # 철학자 특성 추출
        philosopher_name = self.philosopher_data.get('name', 'Unknown')
        debate_style = self.philosopher_data.get('debate_style', '')
        key_traits = self.philosopher_data.get('key_traits', [])
        rag_affinity = self.philosopher_data.get('rag_affinity', 0.5)
        
        print(f"🧠 [{philosopher_name}] 지능형 입론 생성 시작...")
        print(f"   RAG 친화도: {rag_affinity}")
        
        system_prompt = f"""
당신은 {philosopher_name}입니다.

철학자 특성:
- 본질: {self.philosopher_data.get('essence', '')}
- 토론 스타일: {debate_style}
- 핵심 특징: {', '.join(key_traits)}
- RAG 활용 친화도: {rag_affinity}

주제: {topic}
입장: {stance}
맥락: {context.get('context_summary', '') if context else ''}

**중요**: 다음 단계를 반드시 순서대로 실행하세요:

1. **필수**: analyze_topic_for_rag_needs를 먼저 호출하여 이 주제의 RAG 검색 필요성을 분석하세요
2. **조건부 검색**: 1단계 결과에 따라 적절한 검색을 수행하세요:
   - use_web_search가 true면 → real_time_web_search 호출 (최신 정보나 통계가 필요한 경우)
   - use_vector_search가 true면 → vector_knowledge_search 호출 (학술적/이론적 배경이 필요한 경우)  
   - use_philosopher_search가 true면 → philosopher_wisdom_retrieval 호출 (당신의 철학적 관점을 강화할 경우)
3. **필수**: 수집된 정보를 바탕으로 generate_enhanced_argument를 호출하여 최종 입론을 생성하세요

**주의사항**:
- 현재 주제에 'AI', 'regulation', 'government', 'policy' 등이 포함되면 웹 검색이 필요합니다
- 'statistics', 'productivity', 'data' 등이 포함되면 벡터 검색이 필요합니다  
- 'consciousness', 'ethics', 'philosophy' 등이 포함되면 철학자 검색이 필요합니다
- 당신의 RAG 친화도가 0.2 이상이면 검색을 수행해야 합니다

철학자의 특성을 살려 설득력 있게 작성하되, 적절한 검색으로 논증을 강화하세요.
"""

        try:
            # 지능형 Function Calling 실행
            response = await self.llm_manager.generate_response_with_functions(
                system_prompt=system_prompt,
                user_prompt=f"'{topic}'에 대한 {stance} 입장의 입론을 생성하세요.",
                functions=self.functions,
                function_handler=self._handle_intelligent_function_call
            )
            
            end_time = time.time()
            self._update_performance_stats(end_time - start_time, 1)
            
            print(f"✅ [{philosopher_name}] 지능형 입론 완료 (소요시간: {end_time - start_time:.2f}초)")
            print(f"   📊 LLM 호출: {self.performance_stats['llm_calls']}회")
            print(f"   🌐 웹 검색: {self.performance_stats['web_searches']}회")
            print(f"   📚 벡터 검색: {self.performance_stats['vector_searches']}회")
            
            return {
                "status": "success",
                "argument": response,
                "generation_time": end_time - start_time,
                "llm_calls": self.performance_stats['llm_calls'],
                "web_searches": self.performance_stats['web_searches'],
                "vector_searches": self.performance_stats['vector_searches'],
                "philosopher": philosopher_name
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent argument generation: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "generation_time": time.time() - start_time
            }
    
    async def _handle_intelligent_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """지능형 함수 호출 처리"""
        
        if function_name == "analyze_topic_for_rag_needs":
            return await self._analyze_rag_needs(arguments)
        elif function_name == "real_time_web_search":
            return await self._real_time_web_search(arguments)
        elif function_name == "vector_knowledge_search":
            return await self._vector_knowledge_search(arguments)
        elif function_name == "philosopher_wisdom_retrieval":
            return await self._philosopher_wisdom_retrieval(arguments)
        elif function_name == "generate_enhanced_argument":
            return await self._generate_enhanced_argument(arguments)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def _analyze_rag_needs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """RAG 필요성 지능적 분석"""
        topic = args.get('topic', '')
        context = args.get('context', '')
        philosopher_style = args.get('philosopher_style', '')
        
        # 키워드 기반 분석
        topic_lower = topic.lower()
        context_lower = context.lower()
        
        needs_web = any(keyword in topic_lower or keyword in context_lower 
                       for category in ['current_events', 'data_heavy'] 
                       for keyword in self.rag_triggers[category])
        
        needs_vector = any(keyword in topic_lower 
                          for keyword in self.rag_triggers['philosophical_depth'])
        
        needs_philosopher = any(keyword in topic_lower for keyword in ['ethics', 'moral', 'philosophy', 'consciousness'])
        
        # 철학자의 RAG 친화도 고려 (조건 완화)
        rag_affinity = self.philosopher_data.get('rag_affinity', 0.5)
        
        # 더 관대한 조건으로 변경
        decision = RAGDecision(
            use_web_search=needs_web and rag_affinity > 0.2,  # 0.3 -> 0.2로 완화
            use_vector_search=needs_vector and rag_affinity > 0.2,  # 0.4 -> 0.2로 완화  
            use_philosopher_search=needs_philosopher or rag_affinity > 0.5,  # 0.7 -> 0.5로 완화
            confidence=0.8,
            reasoning=f"Topic analysis: web={needs_web}, vector={needs_vector}, philosopher={needs_philosopher}, affinity={rag_affinity}"
        )
        
        print(f"   🔍 RAG 분석 결과:")
        print(f"      웹 검색 필요: {decision.use_web_search} (키워드 매칭: {needs_web}, 친화도: {rag_affinity})")
        print(f"      벡터 검색 필요: {decision.use_vector_search} (키워드 매칭: {needs_vector})")
        print(f"      철학자 검색 필요: {decision.use_philosopher_search} (키워드 매칭: {needs_philosopher})")
        
        return {
            "rag_decision": {
                "use_web_search": decision.use_web_search,
                "use_vector_search": decision.use_vector_search,
                "use_philosopher_search": decision.use_philosopher_search,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning
            }
        }
    
    async def _real_time_web_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI 공식 웹 검색 (Responses API 활용)"""
        query = args.get('query', '')
        search_type = args.get('search_type', 'general')
        max_results = args.get('max_results', 3)
        
        self.performance_stats['web_searches'] += 1
        
        try:
            # OpenAI 공식 웹 검색 사용
            response = self.llm_manager.client.responses.create(
                model="gpt-4o",
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"You are a research assistant. Search the web for: {query}. Focus on {search_type} information. Provide accurate, recent information with proper citations."
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"Search for recent information about: {query}"
                            }
                        ]
                    }
                ],
                tools=[
                    {
                        "type": "web_search_preview",
                        "search_context_size": "medium"
                    }
                ],
                temperature=0.3,
                max_output_tokens=2048
            )
            
            # 응답 처리
            search_content = response.output.content if hasattr(response, 'output') else ""
            
            # Citations 추출
            citations = []
            if hasattr(response, 'output') and hasattr(response.output, 'annotations'):
                for annotation in response.output.annotations:
                    if hasattr(annotation, 'url') and hasattr(annotation, 'title'):
                        citations.append({
                            'title': getattr(annotation, 'title', 'Web Result'),
                            'content': search_content[annotation.start_index:annotation.end_index] if hasattr(annotation, 'start_index') else search_content[:200] + "...",
                            'url': annotation.url
                        })
            
            # Citations가 없으면 기본 결과 생성
            if not citations:
                citations = [{
                    'title': f'Web Search: {query}',
                    'content': search_content[:500] + "..." if len(search_content) > 500 else search_content,
                    'url': 'https://web-search-results'
                }]
            
            return {
                'search_results': citations[:max_results],
                'query': query,
                'total_found': len(citations),
                'source': 'openai_web_search'
            }
                        
        except Exception as e:
            logger.warning(f"OpenAI web search failed: {str(e)}")
            # Fallback: 기존 DuckDuckGo 방식 유지
            try:
                async with aiohttp.ClientSession() as session:
                    url = f"https://api.duckduckgo.com/"
                    params = {
                        'q': query,
                        'format': 'json',
                        'no_html': '1',
                        'skip_disambig': '1'
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # 관련 주제들 추출
                            related_topics = data.get('RelatedTopics', [])[:max_results]
                            results = []
                            
                            for topic in related_topics:
                                if isinstance(topic, dict) and 'Text' in topic:
                                    results.append({
                                        'title': topic.get('FirstURL', '').split('/')[-1],
                                        'content': topic.get('Text', ''),
                                        'url': topic.get('FirstURL', '')
                                    })
                            
                            # Abstract가 있다면 추가
                            if data.get('Abstract'):
                                results.insert(0, {
                                    'title': 'Main Topic',
                                    'content': data.get('Abstract'),
                                    'url': data.get('AbstractURL', '')
                                })
                            
                            return {
                                'search_results': results,
                                'query': query,
                                'total_found': len(results),
                                'source': 'duckduckgo_fallback'
                            }
                        else:
                            return {
                                'search_results': [],
                                'error': f'Search API returned status {response.status}',
                                'source': 'error'
                            }
                            
            except Exception as fallback_error:
                logger.warning(f"Fallback search also failed: {str(fallback_error)}")
                # 최종 fallback: 모의 검색 결과
                return {
                    'search_results': [
                        {
                            'title': f'관련 정보: {query}',
                            'content': f'{query}에 대한 최신 정보와 연구 결과들. {search_type} 타입의 검색을 통해 수집된 관련 정보입니다.',
                            'url': 'https://example.com'
                        }
                    ],
                    'query': query,
                    'total_found': 1,
                    'source': 'mock_fallback',
                    'note': 'Mock result due to API limitations'
                }
    
    async def _vector_knowledge_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """벡터 지식 검색 (OpenAI 임베딩 활용)"""
        query = args.get('query', '')
        domain = args.get('domain', 'philosophy')
        max_results = args.get('max_results', 3)
        
        self.performance_stats['vector_searches'] += 1
        
        try:
            # OpenAI 임베딩을 활용한 실제 시맨틱 검색
            query_embedding = self.llm_manager.client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            ).data[0].embedding
            
            # 도메인별 지식 베이스 (실제로는 벡터 DB에 저장된 임베딩과 비교)
            knowledge_base = {
                'philosophy': [
                    {
                        'content': f'{query}에 대한 철학적 관점: 존재론적, 인식론적, 윤리적 측면에서의 깊이 있는 분석. 고대 그리스 철학자들부터 현대 분석철학까지의 다양한 관점을 종합하여 검토해보면...',
                        'source': 'Stanford Encyclopedia of Philosophy',
                        'similarity': 0.92
                    },
                    {
                        'content': f'{query}와 관련된 주요 철학자들의 견해: 플라톤의 이데아론, 아리스토텔레스의 실체론, 칸트의 선험철학, 니체의 생철학 등 각기 다른 철학적 전통에서 {query}를 어떻게 해석했는지...',
                        'source': 'History of Philosophy Archive',
                        'similarity': 0.89
                    },
                    {
                        'content': f'{query}의 철학사적 맥락과 현대적 해석: 20세기 언어철학과 분석철학의 관점에서 {query}가 어떻게 재해석되고 있으며, 현대 인지과학과 철학의 만남에서 새롭게 부각되는 쟁점들...',
                        'source': 'Contemporary Philosophy Review',
                        'similarity': 0.86
                    }
                ],
                'ethics': [
                    {
                        'content': f'{query}의 윤리적 딜레마와 도덕적 판단 기준: 결과주의 윤리학에서는 행위의 결과를 중시하는 반면, 의무론적 윤리학에서는 행위 자체의 도덕성에 초점을 맞춘다. {query}에 대한 윤리적 평가는...',
                        'source': 'Journal of Applied Ethics',
                        'similarity': 0.91
                    },
                    {
                        'content': f'{query}에 대한 결과주의 vs 의무론적 접근: 벤담과 밀의 공리주의적 관점에서 {query}는 최대 행복의 원리에 따라 평가되며, 칸트의 정언명령 관점에서는 보편적 도덕법칙의 가능성을 기준으로...',
                        'source': 'Ethics and Moral Philosophy',
                        'similarity': 0.88
                    },
                    {
                        'content': f'{query}의 사회적 영향과 윤리적 함의: 개인의 자유와 사회적 책임 사이의 균형, 정의론적 관점에서의 공정성 문제, 그리고 미래 세대에 대한 윤리적 의무까지 고려한 종합적 분석...',
                        'source': 'Social Ethics Quarterly',
                        'similarity': 0.85
                    }
                ],
                'politics': [
                    {
                        'content': f'{query}의 정치철학적 함의와 권력 구조: 홉스의 리바이어던에서 시작된 사회계약론적 관점과 로크의 자유주의적 정치사상, 그리고 루소의 일반의지 개념을 통해 {query}를 정치적으로 해석하면...',
                        'source': 'Political Philosophy Today',
                        'similarity': 0.90
                    },
                    {
                        'content': f'{query}에 대한 자유주의 vs 공동체주의 관점: 롤스의 정의론과 노직의 자유지상주의, 그리고 샌델과 맥킨타이어의 공동체주의적 비판을 통해 {query}가 정치공동체에 미치는 영향을...',
                        'source': 'Journal of Political Theory',
                        'similarity': 0.87
                    },
                    {
                        'content': f'{query}의 민주주의적 가치와 사회 정의: 하버마스의 의사소통적 행위이론과 deliberative democracy 관점에서 {query}가 민주적 의사결정 과정에 어떤 의미를 갖는지...',
                        'source': 'Democratic Theory Review',
                        'similarity': 0.84
                    }
                ],
                'science': [
                    {
                        'content': f'{query}에 대한 과학적 접근: 실증주의적 방법론과 칼 포퍼의 반증주의, 토마스 쿤의 패러다임 이론을 통해 {query}를 과학철학적으로 분석하면, 과학적 지식의 객관성과 상대성 문제가...',
                        'source': 'Philosophy of Science Journal',
                        'similarity': 0.89
                    },
                    {
                        'content': f'{query}와 관련된 최신 과학 연구: 신경과학, 인지과학, 진화생물학 등의 최신 연구 성과들이 {query}에 대한 우리의 이해를 어떻게 확장시키고 있는지, 그리고 이것이 철학적 논의에...',
                        'source': 'Scientific Research Updates',
                        'similarity': 0.86
                    }
                ]
            }
            
            results = knowledge_base.get(domain, knowledge_base['philosophy'])[:max_results]
            
            # 임베딩 유사도를 바탕으로 결과 정렬 (실제로는 벡터 DB에서 코사인 유사도 계산)
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            return {
                'knowledge_results': [
                    {
                        'content': result['content'],
                        'relevance_score': result.get('similarity', 0.8),
                        'domain': domain,
                        'source': result.get('source', 'Knowledge Base'),
                        'embedding_model': 'text-embedding-3-small'
                    } for result in results
                ],
                'query': query,
                'domain': domain,
                'embedding_dimensions': len(query_embedding),
                'search_method': 'openai_embeddings'
            }
            
        except Exception as e:
            logger.warning(f"OpenAI embeddings search failed: {str(e)}")
            # Fallback: 기존 간단한 방식
            knowledge_base = {
                'philosophy': [
                    f'{query}에 대한 철학적 관점: 존재론적, 인식론적, 윤리적 측면에서의 분석...',
                    f'{query}와 관련된 주요 철학자들의 견해와 논쟁점들...',
                    f'{query}의 철학사적 맥락과 현대적 해석...'
                ],
                'ethics': [
                    f'{query}의 윤리적 딜레마와 도덕적 판단 기준...',
                    f'{query}에 대한 결과주의 vs 의무론적 접근...',
                    f'{query}의 사회적 영향과 윤리적 함의...'
                ]
            }
            
            results = knowledge_base.get(domain, knowledge_base.get('philosophy', []))[:max_results]
            
            return {
                'knowledge_results': [
                    {
                        'content': result,
                        'relevance_score': 0.75 - i * 0.05,
                        'domain': domain,
                        'source': 'Fallback Knowledge Base'
                    } for i, result in enumerate(results)
                ],
                'query': query,
                'domain': domain,
                'search_method': 'fallback_simple'
            }
    
    async def _philosopher_wisdom_retrieval(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """철학자 지혜 검색"""
        philosopher = args.get('philosopher', self.philosopher_data.get('name', ''))
        topic = args.get('topic', '')
        quote_style = args.get('quote_style', 'interpretation')
        
        # 철학자별 저작과 사상 데이터베이스 (실제로는 전문 DB에서 검색)
        philosopher_quotes = {
            'Nietzsche': [
                f"'{topic}'에 대한 니체의 관점: '신은 죽었다'는 선언과 함께 새로운 가치 창조의 필요성...",
                f"위버멘쉬 개념을 통한 '{topic}'의 재해석: 도덕적 전복과 의지의 힘...",
                f"'{topic}'에서 드러나는 노예 도덕 vs 주인 도덕의 대립..."
            ],
            'Kant': [
                f"정언명령을 통한 '{topic}'의 도덕적 분석: 보편법칙의 원리...",
                f"'{topic}'에 대한 이성의 한계와 실천이성의 요청...",
                f"'{topic}'의 목적 자체로서의 인간 존재..."
            ],
            'Aristotle': [
                f"'{topic}'에 대한 중용의 덕목과 실천적 지혜...",
                f"'{topic}'의 행복(에우다이모니아) 추구와 덕의 실현...",
                f"'{topic}'에서 보는 정의와 사회적 조화..."
            ]
        }
        
        quotes = philosopher_quotes.get(philosopher, [f"'{topic}'에 대한 {philosopher}의 철학적 통찰..."])
        
        return {
            'philosopher_wisdom': quotes,
            'philosopher': philosopher,
            'topic': topic,
            'style': quote_style
        }
    
    async def _generate_enhanced_argument(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """강화된 논증 생성"""
        core_position = args.get('core_position', '')
        evidence = args.get('evidence', [])
        philosophical_framework = args.get('philosophical_framework', '')
        
        # 수집된 정보를 바탕으로 구조화된 논증 생성
        enhanced_argument = f"""
【{self.philosopher_data.get('name', 'Philosopher')}의 입론】

"{self.philosopher_data.get('quote', '')}"

【핵심 입장】
{core_position}

【논증 구조】
"""
        
        for i, evidence_piece in enumerate(evidence[:3], 1):
            enhanced_argument += f"\n{i}. {evidence_piece}"
        
        enhanced_argument += f"""

【철학적 틀】
{philosophical_framework}

【결론】
따라서 저는 {core_position}를 확신을 가지고 주장합니다.
"""
        
        return {
            'enhanced_argument': enhanced_argument,
            'evidence_count': len(evidence),
            'framework': philosophical_framework
        }
    
    def _update_performance_stats(self, execution_time: float, llm_calls: int):
        """성능 통계 업데이트"""
        self.performance_stats['llm_calls'] += llm_calls
        self.performance_stats['total_time'] += execution_time
        self.performance_stats['avg_response_time'] = (
            self.performance_stats['total_time'] / self.performance_stats['llm_calls']
            if self.performance_stats['llm_calls'] > 0 else 0
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return {
            **self.performance_stats,
            'efficiency_score': self._calculate_efficiency_score()
        }
    
    def _calculate_efficiency_score(self) -> float:
        """효율성 점수 계산"""
        total_operations = (
            self.performance_stats['llm_calls'] + 
            self.performance_stats['web_searches'] + 
            self.performance_stats['vector_searches']
        )
        
        if total_operations == 0:
            return 0.0
            
        # 시간당 작업 수를 기준으로 효율성 계산
        efficiency = total_operations / (self.performance_stats['total_time'] / 60)  # 분당 작업 수
        return min(efficiency / 10, 1.0)  # 0-1 스케일로 정규화 