"""
RAG 병렬 처리 모듈

RAG 검색과 처리 작업을 세밀하게 병렬화하여 성능을 최적화
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor
import yaml
import os

logger = logging.getLogger(__name__)

class RAGParallelProcessor:
    """RAG 작업 병렬 처리기"""
    
    def __init__(self, max_workers: int = 4, sequential_search: bool = False):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.sequential_search = sequential_search  # RAG 검색 직렬 처리 플래그
        
    async def process_argument_preparation_parallel(
        self, 
        agent, 
        topic: str, 
        stance_statement: str, 
        context: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        입론 준비를 병렬로 처리
        
        Args:
            agent: 참가자 에이전트
            topic: 토론 주제
            stance_statement: 입장 진술문
            context: 컨텍스트 정보
            progress_callback: 진행 상황 콜백 함수
            
        Returns:
            처리 결과
        """
        try:
            # 1단계: 핵심 논점 추출 (빠른 작업)
            if progress_callback:
                progress_callback("core_arguments", "started", {"description": "핵심 논점 추출 중"})
            
            core_arguments_task = asyncio.create_task(
                self._extract_core_arguments_async(agent, topic, stance_statement)
            )
            
            # 2단계: 병렬 검색 작업들 준비
            search_tasks = []
            
            # 웹 검색 태스크
            if hasattr(agent, 'web_search_retriever') and agent.web_search_retriever:
                search_tasks.append(
                    self._web_search_async(agent.web_search_retriever, topic, stance_statement, progress_callback)
                )
            
            # 벡터 검색 태스크
            if hasattr(agent, 'vector_store') and agent.vector_store:
                search_tasks.append(
                    self._vector_search_async(agent.vector_store, topic, stance_statement, progress_callback)
                )
            
            # 대화 기록 검색 태스크
            if hasattr(agent, 'dialogue_history') and agent.dialogue_history:
                search_tasks.append(
                    self._dialogue_history_search_async(agent.dialogue_history, topic, progress_callback)
                )
            
            # 철학자 작품 검색 태스크
            if hasattr(agent, 'config') and agent.config.get('philosopher_name'):
                search_tasks.append(
                    self._philosopher_works_search_async(agent.config.get('philosopher_name'), topic, progress_callback)
                )
            
            # 3단계: 핵심 논점 완료 대기
            core_arguments = await core_arguments_task
            if progress_callback:
                progress_callback("core_arguments", "completed", {"result": core_arguments})
            
            # 4단계: 검색 작업 실행 (직렬/병렬 선택)
            if progress_callback:
                search_mode = "sequential" if self.sequential_search else "parallel"
                progress_callback("search_execution", "started", {
                    "search_count": len(search_tasks),
                    "mode": search_mode
                })
            
            search_results = []
            if search_tasks:
                if self.sequential_search:
                    # 직렬 처리: 하나씩 순차적으로 실행
                    logger.info(f"🔄 Sequential RAG search mode: processing {len(search_tasks)} searches one by one")
                    for i, task in enumerate(search_tasks, 1):
                        if progress_callback:
                            progress_callback("search_execution", "progress", {
                                "current": i,
                                "total": len(search_tasks),
                                "message": f"Executing search {i}/{len(search_tasks)}"
                            })
                        result = await task
                        search_results.append(result)
                else:
                    # 병렬 처리: 모든 검색 동시 실행
                    logger.info(f"⚡ Parallel RAG search mode: processing {len(search_tasks)} searches concurrently")
                    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            if progress_callback:
                progress_callback("search_execution", "completed", {"results_count": len(search_results)})

            # 5단계: 검색 결과 통합 및 필터링
            if progress_callback:
                progress_callback("evidence_integration", "started", {"description": "증거 통합 및 필터링"})
            
            evidence_results = await self._integrate_evidence_async(search_results, core_arguments, progress_callback)
            
            if progress_callback:
                progress_callback("evidence_integration", "completed", {"evidence_count": len(evidence_results)})
            
            # 6단계: 최종 입론 생성
            if progress_callback:
                progress_callback("final_argument", "started", {"description": "최종 입론 생성"})
            
            final_argument = await self._generate_final_argument_async(
                agent, core_arguments, evidence_results, topic, stance_statement, progress_callback
            )
            
            if progress_callback:
                progress_callback("final_argument", "completed", {"argument_length": len(final_argument)})
            
            return {
                "status": "success",
                "core_arguments": core_arguments,
                "evidence_results": evidence_results,
                "final_argument": final_argument,
                "search_results_count": len(search_results),
                "search_mode": "sequential" if self.sequential_search else "parallel"
            }
            
        except Exception as e:
            logger.error(f"Error in parallel argument preparation: {str(e)}")
            if progress_callback:
                progress_callback("error", "failed", {"error": str(e)})
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _extract_core_arguments_async(self, agent, topic: str, stance_statement: str) -> List[str]:
        """핵심 논점 추출 (비동기)"""
        loop = asyncio.get_event_loop()
        
        def extract_core_arguments():
            if hasattr(agent, '_extract_core_arguments'):
                return agent._extract_core_arguments(topic, stance_statement)
            else:
                # 기본 핵심 논점 생성
                return [
                    f"{stance_statement}의 첫 번째 근거",
                    f"{stance_statement}의 두 번째 근거",
                    f"{stance_statement}의 세 번째 근거"
                ]
        
        return await loop.run_in_executor(self.executor, extract_core_arguments)
    
    async def _web_search_async(self, web_retriever, topic: str, stance_statement: str, progress_callback: Optional[callable]) -> Dict[str, Any]:
        """웹 검색 (비동기)"""
        try:
            if progress_callback:
                progress_callback("web_search", "started", {"query": topic})
            
            loop = asyncio.get_event_loop()
            
            def web_search():
                query = f"{topic} {stance_statement}"
                return web_retriever.search(query, max_results=3)
            
            results = await loop.run_in_executor(self.executor, web_search)
            
            if progress_callback:
                progress_callback("web_search", "completed", {"results_count": len(results)})
            
            return {
                "type": "web_search",
                "results": results,
                "query": f"{topic} {stance_statement}"
            }
            
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            if progress_callback:
                progress_callback("web_search", "failed", {"error": str(e)})
            return {"type": "web_search", "results": [], "error": str(e)}
    
    async def _vector_search_async(self, vector_store, topic: str, stance_statement: str, progress_callback: Optional[callable]) -> Dict[str, Any]:
        """벡터 검색 (비동기)"""
        try:
            if progress_callback:
                progress_callback("vector_search", "started", {"query": topic})
            
            loop = asyncio.get_event_loop()
            
            def vector_search():
                query = f"{topic} {stance_statement}"
                return vector_store.search(query, limit=3)
            
            results = await loop.run_in_executor(self.executor, vector_search)
            
            if progress_callback:
                progress_callback("vector_search", "completed", {"results_count": len(results)})
            
            return {
                "type": "vector_search",
                "results": results,
                "query": f"{topic} {stance_statement}"
            }
            
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            if progress_callback:
                progress_callback("vector_search", "failed", {"error": str(e)})
            return {"type": "vector_search", "results": [], "error": str(e)}
    
    async def _dialogue_history_search_async(self, dialogue_history: List[Dict], topic: str, progress_callback: Optional[callable]) -> Dict[str, Any]:
        """대화 기록 검색 (비동기)"""
        try:
            if progress_callback:
                progress_callback("dialogue_search", "started", {"history_count": len(dialogue_history)})
            
            loop = asyncio.get_event_loop()
            
            def dialogue_search():
                # 토론 주제와 관련된 대화 기록 필터링
                relevant_messages = []
                topic_keywords = topic.lower().split()
                
                for msg in dialogue_history[-10:]:  # 최근 10개 메시지만
                    text = msg.get('text', '').lower()
                    if any(keyword in text for keyword in topic_keywords):
                        relevant_messages.append(msg)
                
                return relevant_messages[:3]  # 최대 3개
            
            results = await loop.run_in_executor(self.executor, dialogue_search)
            
            if progress_callback:
                progress_callback("dialogue_search", "completed", {"results_count": len(results)})
            
            return {
                "type": "dialogue_history",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Dialogue history search error: {str(e)}")
            if progress_callback:
                progress_callback("dialogue_search", "failed", {"error": str(e)})
            return {"type": "dialogue_history", "results": [], "error": str(e)}
    
    async def _philosopher_works_search_async(self, philosopher_name: str, topic: str, progress_callback: Optional[callable]) -> Dict[str, Any]:
        """철학자 작품 검색 (비동기)"""
        try:
            if progress_callback:
                progress_callback("philosopher_search", "started", {"philosopher": philosopher_name})
            
            loop = asyncio.get_event_loop()
            
            def philosopher_search():
                # 철학자별 관련 작품/인용구 검색 (실제로는 DB나 파일에서 가져와야 함)
                philosopher_quotes = {
                    "nietzsche": [
                        "신은 죽었다. 그리고 우리가 그를 죽였다.",
                        "괴물과 싸우는 자는 그 과정에서 자신이 괴물이 되지 않도록 조심해야 한다.",
                        "무엇이 나를 죽이지 못한다면 나를 더 강하게 만든다."
                    ],
                    "camus": [
                        "시지프스는 행복해야 한다고 상상해야 한다.",
                        "삶이 무의미하다고 해서 살 가치가 없는 것은 아니다.",
                        "진정한 철학적 문제는 오직 하나뿐이다. 바로 자살이다."
                    ]
                }
                
                quotes = philosopher_quotes.get(philosopher_name.lower(), [])
                return [{"text": quote, "source": philosopher_name} for quote in quotes[:3]]
            
            results = await loop.run_in_executor(self.executor, philosopher_search)
            
            if progress_callback:
                progress_callback("philosopher_search", "completed", {"results_count": len(results)})
            
            return {
                "type": "philosopher_works",
                "results": results,
                "philosopher": philosopher_name
            }
            
        except Exception as e:
            logger.error(f"Philosopher works search error: {str(e)}")
            if progress_callback:
                progress_callback("philosopher_search", "failed", {"error": str(e)})
            return {"type": "philosopher_works", "results": [], "error": str(e)}
    
    async def _integrate_evidence_async(self, search_results: List[Any], core_arguments: List[str], progress_callback: Optional[callable]) -> List[Dict[str, Any]]:
        """검색 결과 통합 및 필터링 (비동기)"""
        try:
            loop = asyncio.get_event_loop()
            
            def integrate_evidence():
                all_evidence = []
                
                for result in search_results:
                    if isinstance(result, Exception):
                        continue
                    
                    if isinstance(result, dict) and 'results' in result:
                        evidence_type = result.get('type', 'unknown')
                        for item in result['results']:
                            if isinstance(item, dict):
                                all_evidence.append({
                                    "type": evidence_type,
                                    "content": item.get('text', item.get('content', '')),
                                    "source": item.get('source', item.get('url', 'Unknown')),
                                    "relevance_score": self._calculate_relevance(
                                        item.get('text', item.get('content', '')), 
                                        core_arguments
                                    )
                                })
                
                # 관련성 점수로 정렬하고 상위 결과만 선택
                all_evidence.sort(key=lambda x: x['relevance_score'], reverse=True)
                
                # 최대 1개의 강력한 증거만 선택 (기존 정책 유지)
                filtered_evidence = []
                for evidence in all_evidence:
                    if evidence['relevance_score'] > 0.8 and len(filtered_evidence) < 1:
                        # 구체적인 데이터가 있는지 확인
                        content = evidence['content'].lower()
                        if any(keyword in content for keyword in ['연구', '조사', '통계', '데이터', '%', '명', '건']):
                            filtered_evidence.append(evidence)
                
                return filtered_evidence
            
            return await loop.run_in_executor(self.executor, integrate_evidence)
            
        except Exception as e:
            logger.error(f"Evidence integration error: {str(e)}")
            if progress_callback:
                progress_callback("evidence_integration", "failed", {"error": str(e)})
            return []
    
    def _calculate_relevance(self, text: str, core_arguments: List[str]) -> float:
        """텍스트와 핵심 논점 간의 관련성 점수 계산"""
        if not text or not core_arguments:
            return 0.0
        
        text_lower = text.lower()
        total_score = 0.0
        
        for argument in core_arguments:
            argument_words = argument.lower().split()
            matches = sum(1 for word in argument_words if word in text_lower)
            if argument_words:
                score = matches / len(argument_words)
                total_score += score
        
        return total_score / len(core_arguments) if core_arguments else 0.0
    
    async def _generate_final_argument_async(
        self, 
        agent, 
        core_arguments: List[str], 
        evidence_results: List[Dict[str, Any]], 
        topic: str, 
        stance_statement: str,
        progress_callback: Optional[callable]
    ) -> str:
        """최종 입론 생성 (비동기)"""
        try:
            if progress_callback:
                progress_callback("final_argument", "started", {"core_args_count": len(core_arguments)})
            
            loop = asyncio.get_event_loop()
            
            def generate_final_argument():
                if hasattr(agent, '_generate_final_opening_argument'):
                    # 실제 메서드는 topic과 stance_statement만 받음
                    return agent._generate_final_opening_argument(topic, stance_statement)
                else:
                    # 기본 입론 생성 (증거 포함)
                    argument_parts = []
                    argument_parts.append(f"주제 '{topic}'에 대한 입장을 밝히겠습니다.")
                    argument_parts.append(f"입장: {stance_statement}")
                    
                    # 핵심 논점 추가
                    if core_arguments:
                        argument_parts.append("\n핵심 논점:")
                        for i, arg in enumerate(core_arguments, 1):
                            argument_parts.append(f"{i}. {arg}")
                    
                    # 증거 추가
                    if evidence_results:
                        argument_parts.append("\n근거:")
                        for evidence in evidence_results:
                            content = evidence.get('content', '')[:200]  # 200자 제한
                            source = evidence.get('source', 'Unknown')
                            argument_parts.append(f"- {content} (출처: {source})")
                    
                    return "\n".join(argument_parts)
            
            result = await loop.run_in_executor(self.executor, generate_final_argument)
            
            if progress_callback:
                progress_callback("final_argument", "completed", {"argument_length": len(result)})
            
            return result
            
        except Exception as e:
            logger.error(f"Final argument generation error: {str(e)}")
            if progress_callback:
                progress_callback("final_argument", "failed", {"error": str(e)})
            
            # 오류 시 기본 입론 반환
            return f"{stance_statement}에 대한 기본 입론입니다."
    
    def cleanup(self):
        """리소스 정리"""
        self.executor.shutdown(wait=True)

class PhilosopherDataLoader:
    """철학자 데이터 병렬 로딩"""
    
    @staticmethod
    async def load_philosopher_data_async() -> Dict[str, Any]:
        """철학자 데이터 비동기 로딩"""
        loop = asyncio.get_event_loop()
        
        def load_data():
            philosophers_file = os.path.join(os.getcwd(), "philosophers", "debate_optimized.yaml")
            try:
                with open(philosophers_file, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
            except Exception as e:
                logger.warning(f"Failed to load philosopher data: {e}")
                return {}
        
        return await loop.run_in_executor(None, load_data) 