"""
개선된 찬반토론 대화 형식을 구현하는 클래스

찬성/반대 입장, 모더레이터, 대화 상태 관리와 벡터 DB 및 에이전트 소통을 분리하여
모듈화된 구조로 대화 진행을 관리합니다.
"""

# ============================================================================
# IMPORTS & DEPENDENCIES
# ============================================================================

import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

from ..state.dialogue_state import DialogueState
from ...agents.base.agent import Agent
from ...agents.participant.user_participant import UserParticipant
from ...rag.retrieval.vector_store import VectorStore
from ...agents.utility.debate_emotion_inference import infer_debate_emotion, apply_debate_emotion_to_prompt
from ...models.llm.llm_manager import LLMManager  # LLMManager import 추가

# 새로운 개선사항 임포트 (고급 기능)
from ..events.initialization_events import (
    get_event_stream, 
    InitializationEventType, 
    TaskProgressTracker,
    create_console_listener
)
from ..parallel.rag_parallel import RAGParallelProcessor, PhilosopherDataLoader

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

class DebateStage:
    """토론 단계 정의"""
    # 기본 단계
    OPENING = "opening"  # 모더레이터 오프닝
    
    # 입론 단계
    PRO_ARGUMENT = "pro_argument"  # 찬성측 입론
    CON_ARGUMENT = "con_argument"  # 반대측 입론
    MODERATOR_SUMMARY_1 = "moderator_summary_1"  # 모더레이터 1차 요약
    
    # 상호논증 단계 (반론 단계 제거하고 바로 상호논증으로)
    INTERACTIVE_ARGUMENT = "interactive_argument"  # 상호논증 단계
    MODERATOR_SUMMARY_2 = "moderator_summary_2"  # 모더레이터 2차 요약
    
    # 결론 단계
    PRO_CONCLUSION = "pro_conclusion"  # 찬성측 최종결론
    CON_CONCLUSION = "con_conclusion"  # 반대측 최종결론
    CLOSING = "closing"  # 모더레이터 끝인사말
    
    # 완료
    COMPLETED = "completed"
    
    # 단계 진행 순서
    STAGE_SEQUENCE = [
        OPENING,
        PRO_ARGUMENT,
        CON_ARGUMENT,
        MODERATOR_SUMMARY_1,
        INTERACTIVE_ARGUMENT,  # 반론 단계들 제거하고 바로 상호논증
        MODERATOR_SUMMARY_2,   # 기존 MODERATOR_SUMMARY_3를 SUMMARY_2로 변경
        PRO_CONCLUSION,
        CON_CONCLUSION,
        CLOSING,
        COMPLETED
    ]
    
    @classmethod
    def next_stage(cls, current_stage: str) -> str:
        """현재 단계 다음의 단계 반환"""
        try:
            current_index = cls.STAGE_SEQUENCE.index(current_stage)
            if current_index < len(cls.STAGE_SEQUENCE) - 1:
                return cls.STAGE_SEQUENCE[current_index + 1]
        except ValueError:
            pass
        return cls.COMPLETED

class ParticipantRole:
    """참가자 역할 정의"""
    PRO = "pro"
    CON = "con"
    NEUTRAL = "neutral"
    MODERATOR = "moderator"
    USER = "user"  # 유저 역할 명시적 추가

# ============================================================================
# MAIN DEBATE DIALOGUE CLASS
# ============================================================================

class DebateDialogue:
    """찬반토론 대화 형식 구현"""
    
    # ========================================================================
    # INITIALIZATION METHODS
    # ========================================================================
    
    def __init__(self, room_id: str, room_data: Dict[str, Any] = None, use_async_init: bool = False, enable_streaming: bool = False):
        """
        토론 대화 초기화
        
        Args:
            room_id: 방 고유 식별자
            room_data: 방 설정 데이터
            use_async_init: 비동기 초기화 사용 여부 (현재는 사용하지 않음 - Option 2 구현)
            enable_streaming: 스트리밍 활성화 여부
        """
        self.room_id = room_id
        self.room_data = room_data or {}
        self.enable_streaming = enable_streaming
        self.dialogue_type = self.room_data.get('dialogueType', 'debate')  # dialogue_type 추가
        
        # 기본 초기화
        self.participants = self._initialize_participants()
        self.user_participants = self._initialize_user_participants()
        self.state = self._initialize_dialogue_state()
        self.vector_store = self._initialize_vector_store()
        
        # LLM 관리자 먼저 초기화 (stance_statements에서 사용)
        self.llm_manager = LLMManager()
        
        self.stance_statements = self._generate_stance_statements()  # agents 초기화 전에 생성
        self.agents = self._initialize_agents()  # stance_statements 이후에 초기화
        
        # Option 2: 오프닝만 즉시 준비, 입론은 On-Demand
        # 모더레이터 오프닝만 미리 준비
        self._prepare_moderator_opening_only()
        
        # 백그라운드 준비 관련 상태
        self.background_preparation_tasks = {}  # 에이전트별 백그라운드 준비 작업
        
        # 기타 초기화
        self.playing = True
        
        # 스트리밍 관련 초기화 (기존 코드 유지)
        self.event_stream = None
        self.streaming_listeners = []
        self.initialization_progress = {"progress_percentage": 100.0, "completed_tasks": 1, "failed_tasks": 0}
        self.initialization_history = []
        
        if enable_streaming:
            try:
                from ..streaming.event_stream import EventStream
                self.event_stream = EventStream()
            except ImportError:
                logger.warning("EventStream not available, streaming disabled")
                self.enable_streaming = False
        
        # RAG 병렬 처리기 (사용하지 않지만 호환성 유지)
        try:
            from ..parallel.rag_parallel import RAGParallelProcessor
            self.rag_processor = RAGParallelProcessor(max_workers=4)
        except ImportError:
            logger.warning("RAGParallelProcessor not available")
            self.rag_processor = None
        
        logger.info(f"DebateDialogue initialized for room {room_id} with Option 2 (on-demand preparation)")
    
    # ========================================================================
    # ASYNC INITIALIZATION METHODS (고급 기능)
    # ========================================================================
    
    async def initialize_async(self) -> Dict[str, Any]:
        """
        비동기 병렬 초기화 - 시간 소요가 큰 작업들을 병렬로 처리
        스트리밍 이벤트와 세밀한 병렬화 지원
        
        Returns:
            초기화 결과 정보
        """
        logger.info(f"Starting enhanced async parallel initialization for room {self.room_id}")
        start_time = time.time()
        
        # 스트리밍 이벤트 시작
        if self.event_stream:
            self.event_stream.emit_event(
                InitializationEventType.STARTED,
                {
                    "room_id": self.room_id,
                    "total_tasks": 4,  # stance_statements, pro_argument, con_argument, moderator_opening
                    "start_time": start_time
                }
            )
        
        try:
            # 에이전트 먼저 초기화 (다른 작업들이 의존함)
            self.agents = self._initialize_agents()
            logger.info("Agents initialized")
            
            # 1단계: 찬반 입장 진술문 먼저 생성 (다른 작업들이 의존함)
            stance_tracker = TaskProgressTracker("stance_statements", self.event_stream) if self.event_stream else None
            if stance_tracker:
                stance_tracker.start(["pro_stance", "con_stance"])
            
            stance_result = await self._generate_stance_statements_async_enhanced(stance_tracker)
            
            if stance_result.get('status') != 'success':
                logger.error("Failed to generate stance statements")
                if self.event_stream:
                    self.event_stream.emit_event(
                        InitializationEventType.FAILED,
                        {"error": "Failed to generate stance statements", "room_id": self.room_id}
                    )
                return {
                    "status": "error",
                    "error": "Failed to generate stance statements",
                    "room_id": self.room_id
                }
            
            # 2단계: 병렬 작업 정의 (stance_statements 완료 후)
            tasks = []
            task_trackers = []
            
            # Pro 측 입론 준비 (에이전트가 있는 경우에만)
            if ParticipantRole.PRO in self.agents:
                pro_tracker = TaskProgressTracker("pro_argument", self.event_stream) if self.event_stream else None
                task_trackers.append(pro_tracker)
                tasks.append(self._prepare_pro_argument_async_enhanced(pro_tracker))
            else:
                tasks.append(self._create_dummy_task("pro_argument", None))
            
            # Con 측 입론 준비 (에이전트가 있는 경우에만)
            if ParticipantRole.CON in self.agents:
                con_tracker = TaskProgressTracker("con_argument", self.event_stream) if self.event_stream else None
                task_trackers.append(con_tracker)
                tasks.append(self._prepare_con_argument_async_enhanced(con_tracker))
            else:
                tasks.append(self._create_dummy_task("con_argument", None))
            
            # 모더레이터 오프닝 준비
            if ParticipantRole.MODERATOR in self.agents:
                moderator_tracker = TaskProgressTracker("moderator_opening", self.event_stream) if self.event_stream else None
                task_trackers.append(moderator_tracker)
                tasks.append(self._prepare_moderator_opening_async_enhanced(moderator_tracker))
            else:
                tasks.append(self._create_dummy_task("moderator_opening", None))
            
            # 병렬 작업 실행
            logger.info(f"Starting {len(tasks)} parallel tasks with enhanced RAG processing")
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 모든 결과 통합 (stance_statements + 병렬 작업들)
            all_results = [stance_result] + list(parallel_results)
            
            # 결과 처리
            initialization_results = self._process_async_results(all_results)
            
            # 최종 설정
            self.playing = True
            
            total_time = time.time() - start_time
            logger.info(f"Enhanced async initialization completed in {total_time:.2f} seconds")
            
            # 스트리밍 이벤트 완료
            if self.event_stream:
                self.event_stream.emit_event(
                    InitializationEventType.COMPLETED,
                    {
                        "room_id": self.room_id,
                        "total_time": total_time,
                        "results_summary": initialization_results
                    }
                )
            
            return {
                "status": "success",
                "total_time": total_time,
                "results": initialization_results,
                "room_id": self.room_id,
                "streaming_enabled": self.enable_streaming
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced async initialization: {str(e)}")
            
            # 스트리밍 이벤트 실패
            if self.event_stream:
                self.event_stream.emit_event(
                    InitializationEventType.FAILED,
                    {"error": str(e), "room_id": self.room_id}
                )
            
            return {
                "status": "error",
                "error": str(e),
                "room_id": self.room_id
            }
    
    async def _generate_stance_statements_async_enhanced(self, progress_tracker: Optional[TaskProgressTracker]) -> Dict[str, Any]:
        """
        찬반 입장 진술문 생성 (개선된 버전 - 스트리밍 지원)
        """
        try:
            if progress_tracker:
                progress_tracker.start(["pro_stance", "con_stance"])
            
            loop = asyncio.get_event_loop()
            
            def generate_stance_statements():
                if progress_tracker:
                    progress_tracker.update_subtask("pro_stance", "started", {"description": "찬성 입장 진술문 생성"})
                
                # 기존 동기 메서드 호출
                result = self._generate_stance_statements()
                
                if progress_tracker:
                    progress_tracker.update_subtask("pro_stance", "completed", {"stance": result.get("pro", "")})
                    progress_tracker.update_subtask("con_stance", "completed", {"stance": result.get("con", "")})
                
                return result
            
            self.stance_statements = await loop.run_in_executor(None, generate_stance_statements)
            
            if progress_tracker:
                progress_tracker.complete({"stance_statements": self.stance_statements})
            
            return {
                "status": "success",
                "task": "stance_statements",
                "result": self.stance_statements
            }
            
        except Exception as e:
            logger.error(f"Error generating stance statements: {str(e)}")
            if progress_tracker:
                progress_tracker.fail(str(e))
            return {
                "status": "error",
                "task": "stance_statements",
                "error": str(e)
            }
    
    async def _prepare_pro_argument_async_enhanced(self, progress_tracker: Optional[TaskProgressTracker]) -> Dict[str, Any]:
        """
        찬성측 입론 준비 (개선된 버전 - 세밀한 병렬화와 스트리밍 지원)
        """
        try:
            if progress_tracker:
                progress_tracker.start([
                    "core_arguments", "parallel_search", "evidence_integration", "final_argument"
                ])
            
            pro_agents = self._get_participants_by_role(ParticipantRole.PRO)
            if not pro_agents:
                if progress_tracker:
                    progress_tracker.fail("No pro agents available")
                return {"status": "error", "task": "pro_argument", "error": "No pro agents available"}
            
            # 첫 번째 찬성 에이전트 사용
            agent_id = pro_agents[0]
            agent = self.agents.get(agent_id)
            
            if not agent:
                if progress_tracker:
                    progress_tracker.fail(f"Agent {agent_id} not found")
                return {"status": "error", "task": "pro_argument", "error": f"Agent {agent_id} not found"}
            
            # 토론 주제와 찬성 입장 진술문
            topic = self.room_data.get('topic', '토론 주제')
            pro_stance = self.stance_statements.get("pro", "찬성 입장")
            
            # 진행 상황 콜백 함수 정의
            def progress_callback(subtask_name: str, status: str, details: Dict[str, Any] = None):
                if progress_tracker:
                    progress_tracker.update_subtask(subtask_name, status, details)
            
            # RAG 병렬 처리기를 사용하여 입론 준비
            result = await self.rag_processor.process_argument_preparation_parallel(
                agent=agent,
                topic=topic,
                stance_statement=pro_stance,
                context={"role": ParticipantRole.PRO},
                progress_callback=progress_callback
            )
            
            if result.get("status") == "success":
                # 에이전트에 결과 저장
                if hasattr(agent, 'opening_argument'):
                    agent.opening_argument = result.get("final_argument", "")
                
                if progress_tracker:
                    progress_tracker.complete({
                        "agent_id": agent_id,
                        "argument_length": len(result.get("final_argument", "")),
                        "evidence_count": len(result.get("evidence_results", []))
                    })
                
                return {
                    "status": "success",
                    "task": "pro_argument",
                    "agent_id": agent_id,
                    "result": result
                }
            else:
                error_msg = result.get("error", "Unknown error in argument preparation")
                if progress_tracker:
                    progress_tracker.fail(error_msg)
                return {
                    "status": "error",
                    "task": "pro_argument",
                    "error": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error preparing pro argument: {str(e)}")
            if progress_tracker:
                progress_tracker.fail(str(e))
            return {
                "status": "error",
                "task": "pro_argument",
                "error": str(e)
            }
    
    async def _prepare_con_argument_async_enhanced(self, progress_tracker: Optional[TaskProgressTracker]) -> Dict[str, Any]:
        """
        반대측 입론 준비 (개선된 버전 - 세밀한 병렬화와 스트리밍 지원)
        """
        try:
            if progress_tracker:
                progress_tracker.start([
                    "core_arguments", "parallel_search", "evidence_integration", "final_argument"
                ])
            
            con_agents = self._get_participants_by_role(ParticipantRole.CON)
            if not con_agents:
                if progress_tracker:
                    progress_tracker.fail("No con agents available")
                return {"status": "error", "task": "con_argument", "error": "No con agents available"}
            
            # 첫 번째 반대 에이전트 사용
            agent_id = con_agents[0]
            agent = self.agents.get(agent_id)
            
            if not agent:
                if progress_tracker:
                    progress_tracker.fail(f"Agent {agent_id} not found")
                return {"status": "error", "task": "con_argument", "error": f"Agent {agent_id} not found"}
            
            # 토론 주제와 반대 입장 진술문
            topic = self.room_data.get('topic', '토론 주제')
            con_stance = self.stance_statements.get("con", "반대 입장")
            
            # 진행 상황 콜백 함수 정의
            def progress_callback(subtask_name: str, status: str, details: Dict[str, Any] = None):
                if progress_tracker:
                    progress_tracker.update_subtask(subtask_name, status, details)
            
            # RAG 병렬 처리기를 사용하여 입론 준비
            result = await self.rag_processor.process_argument_preparation_parallel(
                agent=agent,
                topic=topic,
                stance_statement=con_stance,
                context={"role": ParticipantRole.CON},
                progress_callback=progress_callback
            )
            
            if result.get("status") == "success":
                # 에이전트에 결과 저장
                if hasattr(agent, 'opening_argument'):
                    agent.opening_argument = result.get("final_argument", "")
                
                if progress_tracker:
                    progress_tracker.complete({
                        "agent_id": agent_id,
                        "argument_length": len(result.get("final_argument", "")),
                        "evidence_count": len(result.get("evidence_results", []))
                    })
                
                return {
                    "status": "success",
                    "task": "con_argument",
                    "agent_id": agent_id,
                    "result": result
                }
            else:
                error_msg = result.get("error", "Unknown error in argument preparation")
                if progress_tracker:
                    progress_tracker.fail(error_msg)
                return {
                    "status": "error",
                    "task": "con_argument",
                    "error": error_msg
                }
            
        except Exception as e:
            logger.error(f"Error preparing con argument: {str(e)}")
            if progress_tracker:
                progress_tracker.fail(str(e))
            return {
                "status": "error",
                "task": "con_argument",
                "error": str(e)
            }
    
    async def _prepare_moderator_opening_async_enhanced(self, progress_tracker: Optional[TaskProgressTracker]) -> Dict[str, Any]:
        """
        모더레이터 오프닝 준비 (개선된 버전 - 스트리밍 지원)
        """
        try:
            if progress_tracker:
                progress_tracker.start(["context_preparation", "opening_generation"])
            
            moderator_agents = self._get_participants_by_role(ParticipantRole.MODERATOR)
            if not moderator_agents:
                if progress_tracker:
                    progress_tracker.fail("No moderator agents available")
                return {"status": "error", "task": "moderator_opening", "error": "No moderator agents available"}
            
            agent_id = moderator_agents[0]
            agent = self.agents.get(agent_id)
            
            if not agent:
                if progress_tracker:
                    progress_tracker.fail(f"Moderator agent {agent_id} not found")
                return {"status": "error", "task": "moderator_opening", "error": f"Moderator agent {agent_id} not found"}
            
            loop = asyncio.get_event_loop()
            
            def prepare_moderator_opening():
                if progress_tracker:
                    progress_tracker.update_subtask("context_preparation", "started", {"description": "컨텍스트 준비"})
                
                # 토론 컨텍스트 준비
                topic = self.room_data.get('topic', '토론 주제')
                context = self.room_data.get('context', '')
                pro_stance = self.stance_statements.get("pro", "찬성 입장")
                con_stance = self.stance_statements.get("con", "반대 입장")
                
                if progress_tracker:
                    progress_tracker.update_subtask("context_preparation", "completed", {
                        "topic": topic,
                        "context_length": len(context)
                    })
                    progress_tracker.update_subtask("opening_generation", "started", {"description": "오프닝 메시지 생성"})
                
                # 모더레이터 오프닝 생성
                if hasattr(agent, 'prepare_opening'):
                    opening = agent.prepare_opening(topic, context, pro_stance, con_stance)
                else:
                    # 기본 오프닝 생성
                    opening = f"안녕하세요. 오늘은 '{topic}'에 대해 토론하겠습니다. 찬성측은 '{pro_stance}', 반대측은 '{con_stance}' 입장입니다."
                
                if progress_tracker:
                    progress_tracker.update_subtask("opening_generation", "completed", {
                        "opening_length": len(opening)
                    })
                
                return opening
            
            opening = await loop.run_in_executor(None, prepare_moderator_opening)
            
            # 에이전트에 결과 저장
            if hasattr(agent, 'opening_message'):
                agent.opening_message = opening
            
            if progress_tracker:
                progress_tracker.complete({
                    "agent_id": agent_id,
                    "opening_length": len(opening)
                })
            
            return {
                "status": "success",
                "task": "moderator_opening",
                "agent_id": agent_id,
                "result": opening
            }
            
        except Exception as e:
            logger.error(f"Error preparing moderator opening: {str(e)}")
            if progress_tracker:
                progress_tracker.fail(str(e))
            return {
                "status": "error",
                "task": "moderator_opening",
                "error": str(e)
            }
    
    async def _create_dummy_task(self, task_name: str, data: Any) -> Dict[str, Any]:
        """더미 태스크 생성 (병렬 처리 구조 유지용)"""
        await asyncio.sleep(0.01)  # 최소 지연
        return {
            "task": task_name,
            "status": "skipped",
            "reason": "Not applicable",
            "data": data
        }
    
    def _process_async_results(self, results: List[Any]) -> Dict[str, Any]:
        """비동기 작업 결과 처리"""
        processed_results = {}
        total_success = 0
        total_errors = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {str(result)}")
                total_errors += 1
                continue
            
            if isinstance(result, dict):
                task_name = result.get("task", "unknown")
                status = result.get("status", "unknown")
                
                processed_results[task_name] = result
                
                if status == "success":
                    total_success += 1
                elif status == "error":
                    total_errors += 1
                    logger.error(f"Task {task_name} failed: {result.get('error', 'Unknown error')}")
                else:
                    logger.info(f"Task {task_name} was {status}")
        
        logger.info(f"Async results: {total_success} successful, {total_errors} errors")
        
        return {
            "total_tasks": len(results),
            "successful": total_success,
            "errors": total_errors,
            "details": processed_results
        }
    
    # ========================================================================
    # BASIC INITIALIZATION HELPER METHODS
    # ========================================================================
    
    def _initialize_participants(self) -> Dict[str, List[str]]:
        """참가자 정보 초기화 - 다중 참가자 지원"""
        participants = {
            ParticipantRole.PRO: [],
            ParticipantRole.CON: [],
            ParticipantRole.NEUTRAL: [],
            ParticipantRole.USER: [],
            ParticipantRole.MODERATOR: []
        }
        
        # room_data에서 참가자 정보 추출
        participants_data = self.room_data.get('participants', {})
        
        # PRO 측 참가자 추가 (다중 지원)
        if 'pro' in participants_data:
            pro_data = participants_data['pro']
            
            # 단일 참가자인 경우 (기존 호환성)
            if isinstance(pro_data, dict) and 'character_id' in pro_data:
                character_id = pro_data.get('character_id', 'pro_agent')
                participants[ParticipantRole.PRO].append(character_id)
                logger.info(f"Added single PRO participant: {character_id}")
            
            # 다중 참가자인 경우 (새로운 구조)
            elif isinstance(pro_data, list):
                for i, participant in enumerate(pro_data):
                    character_id = participant.get('character_id', f'pro_agent_{i+1}')
                    participants[ParticipantRole.PRO].append(character_id)
                    logger.info(f"Added PRO participant {i+1}: {character_id}")
            
            # 잘못된 형식인 경우 기본값
            else:
                participants[ParticipantRole.PRO].append('pro_agent')
                logger.warning("Invalid PRO data format, using default pro_agent")
        
        # CON 측 참가자 추가 (다중 지원)
        if 'con' in participants_data:
            con_data = participants_data['con']
            
            # 단일 참가자인 경우 (기존 호환성)
            if isinstance(con_data, dict) and 'character_id' in con_data:
                character_id = con_data.get('character_id', 'con_agent')
                participants[ParticipantRole.CON].append(character_id)
                logger.info(f"Added single CON participant: {character_id}")
            
            # 다중 참가자인 경우 (새로운 구조)
            elif isinstance(con_data, list):
                for i, participant in enumerate(con_data):
                    character_id = participant.get('character_id', f'con_agent_{i+1}')
                    participants[ParticipantRole.CON].append(character_id)
                    logger.info(f"Added CON participant {i+1}: {character_id}")
            
            # 잘못된 형식인 경우 기본값
            else:
                participants[ParticipantRole.CON].append('con_agent')
                logger.warning("Invalid CON data format, using default con_agent")
        
        # 사용자 참가자 추가 (있는 경우)
        if 'users' in participants_data:
            for user_id in participants_data['users']:
                participants[ParticipantRole.USER].append(user_id)
        
        # 모더레이터 추가
        participants[ParticipantRole.MODERATOR].append("moderator")
        
        logger.info(f"Initialized participants - PRO: {len(participants[ParticipantRole.PRO])}, CON: {len(participants[ParticipantRole.CON])}, USER: {len(participants[ParticipantRole.USER])}")
        
        return participants
    
    def _initialize_user_participants(self) -> Dict[str, UserParticipant]:
        """사용자 참가자 객체들 초기화"""
        user_participants = {}
        
        # room_data에서 사용자 정보 추출
        participants_data = self.room_data.get('participants', {})
        users_data = participants_data.get('users', [])
        
        # 각 사용자에 대해 UserParticipant 객체 생성
        for user_id in users_data:
            # 사용자별 설정이 있는지 확인
            user_config = participants_data.get('user_configs', {}).get(user_id, {})
            
            # 기본 사용자명 설정 (실제로는 DB에서 가져와야 함)
            username = user_config.get('username', user_id)
            
            # 사용자 역할 결정 (PRO/CON 측에 속해있는지 확인)
            user_role = "neutral"
            if user_id in self.participants.get(ParticipantRole.PRO, []):
                user_role = "pro"
            elif user_id in self.participants.get(ParticipantRole.CON, []):
                user_role = "con"
            
            # UserParticipant 객체 생성
            user_participant = UserParticipant(
                user_id=user_id,
                username=username,
                config={
                    "role": user_role,
                    "display_name": user_config.get('display_name', username),
                    "avatar_url": user_config.get('avatar_url', ''),
                    "participation_style": user_config.get('participation_style', 'active'),
                    "preferences": user_config.get('preferences', {}),
                    "permissions": user_config.get('permissions', {
                        "can_speak": True,
                        "can_moderate": False,
                        "can_invite": False,
                        "can_change_topic": False
                    })
                }
            )
            
            # 대화 참여 상태 설정
            user_participant.current_dialogue_id = self.room_id
            
            user_participants[user_id] = user_participant
            logger.info(f"Initialized UserParticipant: {user_id} ({username}) as {user_role}")
        
        return user_participants
    
    def _initialize_dialogue_state(self) -> Dict[str, Any]:
        """대화 상태 초기화"""
        return {
            "current_stage": DebateStage.OPENING,
            "turn_count": 0,
            "speaking_history": [],
            "key_points": [], 
            "next_speaker": None,
            "last_update_time": time.time(),
            "moderator_id": "moderator"  # 대문자 "Moderator"에서 소문자 "moderator"로 수정
        }
    
    # ========================================================================
    # VECTOR STORE & CONTEXT PROCESSING
    # ========================================================================
    
    def _initialize_vector_store(self) -> Optional[VectorStore]:
        """벡터 저장소 초기화 (컨텍스트가 있는 경우)"""
        context = self.room_data.get('context', '')
        if context:
            try:
                # 벡터 저장소 생성 및 문서 청크화 후 저장
                vector_store = VectorStore(store_path=f"data/vector_store/{self.room_id}")
                
                # 컨텍스트를 여러 단락으로 분할 (더 효과적인 검색을 위해)
                paragraphs = self._split_context_to_paragraphs(context)
                
                # 벡터 저장소에 단락들 추가
                vector_store.add_documents(paragraphs)
                
                logger.info(f"Vector store initialized with context ({len(context)} chars), {len(paragraphs)} paragraphs")
                return vector_store
            except Exception as e:
                logger.error(f"Error initializing vector store: {str(e)}")
                return None
        return None
        
    def _split_context_to_paragraphs(self, context: str) -> List[str]:
        """컨텍스트를 단락으로 분할"""
        # 빈 줄을 기준으로 단락 분할
        paragraphs = [p.strip() for p in context.split('\n\n') if p.strip()]
        
        # 단락이 너무 긴 경우 추가 분할 (약 500자 단위)
        result = []
        for p in paragraphs:
            if len(p) > 500:
                # 문장 단위로 분할하여 적절한 크기로 조합
                sentences = [s.strip() for s in p.split('.') if s.strip()]
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < 500:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            result.append(current_chunk)
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    result.append(current_chunk)
            else:
                result.append(p)
        
        return result
    
    def _initialize_agents(self) -> Dict[str, Agent]:
        """대화에 필요한 에이전트 초기화 - 다중 참가자 지원"""
        try:
            # 직접 필요한 에이전트들 생성
            from ...agents.moderator.moderator_agent import ModeratorAgent
            from ...agents.participant.debate_participant_agent import DebateParticipantAgent
            
            # 토론 최적화 철학자 속성 로드
            import yaml
            import os
            
            philosophers_file = os.path.join(os.getcwd(), "philosophers", "debate_optimized.yaml")
            try:
                with open(philosophers_file, 'r', encoding='utf-8') as file:
                    debate_philosophers = yaml.safe_load(file)
                logger.info(f"Loaded debate-optimized philosopher data from {philosophers_file}")
            except Exception as e:
                logger.warning(f"Failed to load debate philosophers file: {e}")
                debate_philosophers = {}
            
            agents = {}
            
            # 모더레이터 에이전트 생성 (기본 설정)
            moderator_config = self.room_data.get('moderator', {})
            agents[ParticipantRole.MODERATOR] = ModeratorAgent(
                agent_id=moderator_config.get("agent_id", "moderator_001"),
                name=moderator_config.get("name", "Moderator"),
                config={
                    "stance_statements": self.stance_statements,
                    "style": moderator_config.get("style", "neutral"),
                    "style_id": moderator_config.get("style_id", "0"),  # 기본값 "0" (Casual Young Moderator)
                    "personality": moderator_config.get("personality", "balanced")
                }
            )
            
            # 참가자 정보에서 철학자 에이전트 생성 (다중 지원)
            participants_data = self.room_data.get('participants', {})
            
            # PRO 측 에이전트들 생성 (다중 지원)
            if 'pro' in participants_data:
                pro_data = participants_data['pro']
                
                # 단일 참가자인 경우 (기존 호환성)
                if isinstance(pro_data, dict) and 'character_id' in pro_data:
                    character_id = pro_data.get('character_id', 'pro_agent')
                    philosopher_attrs = debate_philosophers.get(character_id, {})
                    
                    pro_config = {
                        "role": ParticipantRole.PRO,
                        "stance_statements": self.stance_statements,
                        "personality": pro_data.get("personality", "balanced"),
                        "style": pro_data.get("style", "formal"),
                        "argumentation_style": pro_data.get("argumentation_style", "logical"),
                        "philosopher_name": philosopher_attrs.get("name", pro_data.get("name", "Pro Participant")),
                        "philosopher_essence": philosopher_attrs.get("essence", ""),
                        "philosopher_debate_style": philosopher_attrs.get("debate_style", ""),
                        "philosopher_personality": philosopher_attrs.get("personality", ""),
                        "philosopher_key_traits": philosopher_attrs.get("key_traits", []),
                        "philosopher_quote": philosopher_attrs.get("quote", "")
                    }
                    
                    agents[character_id] = DebateParticipantAgent(
                        agent_id=character_id,
                        name=philosopher_attrs.get("name", pro_data.get("name", "Pro Participant")),
                        config=pro_config
                    )
                    
                    # 역할별 대표 에이전트도 설정 (하위 호환성)
                    agents[ParticipantRole.PRO] = agents[character_id]
                    
                    logger.info(f"Created single PRO agent: {character_id} ({philosopher_attrs.get('name', 'Unknown')})")
                
                # 다중 참가자인 경우 (새로운 구조)
                elif isinstance(pro_data, list):
                    first_agent = None
                    for i, participant in enumerate(pro_data):
                        character_id = participant.get('character_id', f'pro_agent_{i+1}')
                        philosopher_attrs = debate_philosophers.get(character_id, {})
                        
                        pro_config = {
                            "role": ParticipantRole.PRO,
                            "stance_statements": self.stance_statements,
                            "personality": participant.get("personality", "balanced"),
                            "style": participant.get("style", "formal"),
                            "argumentation_style": participant.get("argumentation_style", "logical"),
                            "philosopher_name": philosopher_attrs.get("name", participant.get("name", f"Pro Participant {i+1}")),
                            "philosopher_essence": philosopher_attrs.get("essence", ""),
                            "philosopher_debate_style": philosopher_attrs.get("debate_style", ""),
                            "philosopher_personality": philosopher_attrs.get("personality", ""),
                            "philosopher_key_traits": philosopher_attrs.get("key_traits", []),
                            "philosopher_quote": philosopher_attrs.get("quote", "")
                        }
                        
                        agent = DebateParticipantAgent(
                            agent_id=character_id,
                            name=philosopher_attrs.get("name", participant.get("name", f"Pro Participant {i+1}")),
                            config=pro_config
                        )
                        
                        agents[character_id] = agent
                        
                        # 첫 번째 에이전트를 대표 에이전트로 설정 (하위 호환성)
                        if first_agent is None:
                            first_agent = agent
                            agents[ParticipantRole.PRO] = agent
                        
                        logger.info(f"Created PRO agent {i+1}: {character_id} ({philosopher_attrs.get('name', 'Unknown')})")
            
            # CON 측 에이전트들 생성 (다중 지원)
            if 'con' in participants_data:
                con_data = participants_data['con']
                
                # 단일 참가자인 경우 (기존 호환성)
                if isinstance(con_data, dict) and 'character_id' in con_data:
                    character_id = con_data.get('character_id', 'con_agent')
                    philosopher_attrs = debate_philosophers.get(character_id, {})
                    
                    con_config = {
                        "role": ParticipantRole.CON,
                        "stance_statements": self.stance_statements,
                        "personality": con_data.get("personality", "balanced"),
                        "style": con_data.get("style", "formal"),
                        "argumentation_style": con_data.get("argumentation_style", "logical"),
                        "philosopher_name": philosopher_attrs.get("name", con_data.get("name", "Con Participant")),
                        "philosopher_essence": philosopher_attrs.get("essence", ""),
                        "philosopher_debate_style": philosopher_attrs.get("debate_style", ""),
                        "philosopher_personality": philosopher_attrs.get("personality", ""),
                        "philosopher_key_traits": philosopher_attrs.get("key_traits", []),
                        "philosopher_quote": philosopher_attrs.get("quote", "")
                    }
                    
                    agents[character_id] = DebateParticipantAgent(
                        agent_id=character_id,
                        name=philosopher_attrs.get("name", con_data.get("name", "Con Participant")),
                        config=con_config
                    )
                    
                    # 역할별 대표 에이전트도 설정 (하위 호환성)
                    agents[ParticipantRole.CON] = agents[character_id]
                    
                    logger.info(f"Created single CON agent: {character_id} ({philosopher_attrs.get('name', 'Unknown')})")
                
                # 다중 참가자인 경우 (새로운 구조)
                elif isinstance(con_data, list):
                    first_agent = None
                    for i, participant in enumerate(con_data):
                        character_id = participant.get('character_id', f'con_agent_{i+1}')
                        philosopher_attrs = debate_philosophers.get(character_id, {})
                        
                        con_config = {
                            "role": ParticipantRole.CON,
                            "stance_statements": self.stance_statements,
                            "personality": participant.get("personality", "balanced"),
                            "style": participant.get("style", "formal"),
                            "argumentation_style": participant.get("argumentation_style", "logical"),
                            "philosopher_name": philosopher_attrs.get("name", participant.get("name", f"Con Participant {i+1}")),
                            "philosopher_essence": philosopher_attrs.get("essence", ""),
                            "philosopher_debate_style": philosopher_attrs.get("debate_style", ""),
                            "philosopher_personality": philosopher_attrs.get("personality", ""),
                            "philosopher_key_traits": philosopher_attrs.get("key_traits", []),
                            "philosopher_quote": philosopher_attrs.get("quote", "")
                        }
                        
                        agent = DebateParticipantAgent(
                            agent_id=character_id,
                            name=philosopher_attrs.get("name", participant.get("name", f"Con Participant {i+1}")),
                            config=con_config
                        )
                        
                        agents[character_id] = agent
                        
                        # 첫 번째 에이전트를 대표 에이전트로 설정 (하위 호환성)
                        if first_agent is None:
                            first_agent = agent
                            agents[ParticipantRole.CON] = agent
                        
                        logger.info(f"Created CON agent {i+1}: {character_id} ({philosopher_attrs.get('name', 'Unknown')})")
            
            # 사용자 에이전트들 추가 (UserParticipant 객체들을 agents 딕셔너리에 포함)
            for user_id, user_participant in self.user_participants.items():
                agents[user_id] = user_participant
                logger.info(f"Added user agent: {user_id} ({user_participant.username})")
            
            logger.info(f"Successfully initialized {len(agents)} agents (including {len(self.user_participants)} users)")
            return agents
            
        except Exception as e:
            logger.error(f"Error initializing agents: {str(e)}")
            # 기본 에이전트 생성으로 fallback
            from ...agents.participant.debate_participant_agent import DebateParticipantAgent
            from ...agents.moderator.moderator_agent import ModeratorAgent
            
            fallback_agents = {
                ParticipantRole.MODERATOR: ModeratorAgent("moderator_001", "Moderator", {"stance_statements": self.stance_statements}),
                ParticipantRole.PRO: DebateParticipantAgent("pro_agent", "Pro Participant", {"role": ParticipantRole.PRO, "stance_statements": self.stance_statements}),
                ParticipantRole.CON: DebateParticipantAgent("con_agent", "Con Participant", {"role": ParticipantRole.CON, "stance_statements": self.stance_statements})
            }
            
            # 사용자 에이전트들도 fallback에 추가
            fallback_agents.update(self.user_participants)
            
            return fallback_agents
    
    def _prepare_participant_arguments(self) -> None:
        """
        모든 참가자 에이전트의 입론 미리 준비 (다중 참가자 지원)
        """
        import time
        
        topic = self.room_data.get('title', '')
        
        # Pro 측 모든 참가자들의 입론 준비
        pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
        for participant_id in pro_participants:
            # 개별 에이전트 또는 역할별 대표 에이전트 찾기
            participant_agent = self.agents.get(participant_id) or self.agents.get(ParticipantRole.PRO)
            
            if participant_agent:
                try:
                    logger.info(f"Preparing argument for PRO participant: {participant_id}")
                    
                    # 벡터 저장소와 대화 기록을 에이전트에 전달
                    if hasattr(participant_agent, '__dict__'):
                        participant_agent.vector_store = self.vector_store
                        participant_agent.dialogue_history = self.state.get("speaking_history", [])
                    
                    # 입론 준비 요청
                    preparation_result = participant_agent.process({
                        "action": "prepare_argument",
                        "topic": topic,
                        "stance_statement": self.stance_statements.get("pro", ""),
                        "context": self.room_data.get('context', {})
                    })
                    
                    logger.info(f"PRO participant {participant_id} argument preparation result: {preparation_result}")
                    
                    # API 레이트 리미트 방지를 위한 지연
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error preparing PRO argument for {participant_id}: {str(e)}")
        
        # Con 측 모든 참가자들의 입론 준비
        con_participants = self._get_participants_by_role(ParticipantRole.CON)
        for participant_id in con_participants:
            # 개별 에이전트 또는 역할별 대표 에이전트 찾기
            participant_agent = self.agents.get(participant_id) or self.agents.get(ParticipantRole.CON)
            
            if participant_agent:
                try:
                    logger.info(f"Preparing argument for CON participant: {participant_id}")
                    
                    # 벡터 저장소와 대화 기록을 에이전트에 전달
                    if hasattr(participant_agent, '__dict__'):
                        participant_agent.vector_store = self.vector_store
                        participant_agent.dialogue_history = self.state.get("speaking_history", [])
                    
                    # 입론 준비 요청
                    preparation_result = participant_agent.process({
                        "action": "prepare_argument",
                        "topic": topic,
                        "stance_statement": self.stance_statements.get("con", ""),
                        "context": self.room_data.get('context', {})
                    })
                    
                    logger.info(f"CON participant {participant_id} argument preparation result: {preparation_result}")
                    
                    # API 레이트 리미트 방지를 위한 지연
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error preparing CON argument for {participant_id}: {str(e)}")
        
        logger.info("All participant argument preparation completed")
    
    def _generate_stance_statements(self) -> Dict[str, str]:
        """주제에서 찬성/반대 입장 명확화"""
        topic = self.room_data.get('title', '')
        context = self.room_data.get('context', '')
            
        # 인스턴스 변수 사용 (중복 초기화 제거)
        llm_manager = self.llm_manager
        
        # 시스템 프롬프트 구성
        system_prompt = """
You are a neutral, balanced, and objective assistant that can formulate clear debate positions.
For a given debate topic, your task is to create two balanced position statements:
1. A compelling PRO (for/in favor) position statement
2. A compelling CON (against/opposed) position statement

Both statements should be thoughtful, substantive, and of similar strength.
DO NOT include any extraneous text, your response will be parsed programmatically.
"""

        # 유저 프롬프트 구성
        user_prompt = f"""
DEBATE TOPIC: "{topic}"

ADDITIONAL CONTEXT (if available):
{context if context else "No additional context provided."}

Create a balanced pair of position statements for this debate topic:
1. PRO (for/in favor) position statement - a concise statement (~1-2 sentences) arguing in favor of the topic
2. CON (against/opposed) position statement - a concise statement (~1-2 sentences) arguing against the topic

Your response MUST follow this exact format:
{{
  "pro": "The PRO position statement...",
  "con": "The CON position statement..."
}}

Important: 
- Write your statements in the SAME LANGUAGE as the debate topic.
- Make both positions equally compelling and substantive.
- Ensure positions are clear, balanced, and represent opposing viewpoints.
- Provide complete statements that are not cutoff mid-sentence.
"""

        try:
            # LLM 호출
            stance_response = llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4",
                max_tokens=1000
            )
            
            # JSON 파싱
            import json
            import re
            
            # 만약 response가 JSON 형식이 아니라면 파싱을 위해 처리
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, stance_response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                stance_json = json.loads(json_str)
                
                # 유효한 응답인지 확인
                if "pro" in stance_json and "con" in stance_json:
                    logger.info("Successfully generated stance statements using LLM")
                    return stance_json
            
            # 파싱 실패 또는 필요한 키가 없는 경우
            logger.warning(f"Failed to parse LLM response for stance statements: {stance_response[:100]}...")
            
        except Exception as e:
            logger.error(f"Error generating stance statements with LLM: {str(e)}")
        
            # 실패 시 기본값 반환
            logger.warning("Using default stance statements due to LLM failure")
            return {
                "pro": f"{topic}에 찬성하는 입장",
                "con": f"{topic}에 반대하는 입장"
            }
    
    def _get_participants_by_role(self, role: str) -> List[str]:
        """채팅방 데이터에서 역할별 참가자 목록 추출 (다중 참가자 지원)"""
        if not self.room_data:
            return []
        
        participants = []
        if 'participants' in self.room_data:
            participants_data = self.room_data['participants']
            
            # 새로운 다중 참가자 구조 지원
            if role == ParticipantRole.PRO and 'pro' in participants_data:
                pro_data = participants_data['pro']
                
                # 단일 참가자인 경우
                if isinstance(pro_data, dict) and 'character_id' in pro_data:
                    character_id = pro_data.get('character_id', 'pro_agent')
                    participants.append(character_id)
                
                # 다중 참가자인 경우
                elif isinstance(pro_data, list):
                    for i, participant in enumerate(pro_data):
                        character_id = participant.get('character_id', f'pro_agent_{i+1}')
                        participants.append(character_id)
                        
            elif role == ParticipantRole.CON and 'con' in participants_data:
                con_data = participants_data['con']
                
                # 단일 참가자인 경우
                if isinstance(con_data, dict) and 'character_id' in con_data:
                    character_id = con_data.get('character_id', 'con_agent')
                    participants.append(character_id)
                
                # 다중 참가자인 경우
                elif isinstance(con_data, list):
                    for i, participant in enumerate(con_data):
                        character_id = participant.get('character_id', f'con_agent_{i+1}')
                        participants.append(character_id)
            
            # 기존 NPC 구조도 지원 (하위 호환성)
            if 'npcs' in participants_data:
                for npc in participants_data['npcs']:
                    if npc.get('role') == role:
                        participants.append(npc.get('id'))
        
        return participants
    
    # ========================================================================
    # CORE DEBATE RESPONSE GENERATION
    # ========================================================================
    
    def generate_response(self) -> Dict[str, Any]:
        """
        토론 응답 생성 (Option 2: On-Demand + Background Pre-loading)
        
        Returns:
            응답 생성 결과
        """
        try:
            # 대화 일시정지 상태 체크
            if not self.playing:
                return {
                    "status": "paused",
                    "message": "토론이 일시정지 상태입니다.",
                    "playing": self.playing
                }
            
            # 다음 발언자 결정
            next_speaker_info = self.get_next_speaker()
            
            if next_speaker_info["speaker_id"] is None:
                return {
                    "status": "completed",
                    "message": "토론이 완료되었습니다.",
                    "current_stage": self.state["current_stage"]
                }
            
            speaker_id = next_speaker_info["speaker_id"]
            role = next_speaker_info["role"]
            current_stage = self.state["current_stage"]
            
            logger.info(f"Generating response for {speaker_id} ({role}) in stage {current_stage}")
            
            # 에이전트 가져오기
            agent = self.agents.get(speaker_id)
            if not agent:
                return {
                    "status": "error",
                    "message": f"에이전트 {speaker_id}를 찾을 수 없습니다."
                }
            
            # 응답 생성
            if current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
                # 입론 단계: Option 2 로직 적용
                message = self._get_argument_for_speaker(speaker_id, role)
                
                # 다음 발언자 백그라운드 준비 시작
                self._start_next_speaker_preparation()
                
            else:
                # 기타 단계: 기존 방식 사용
                context = self._build_response_context(speaker_id, role)
                
                # 모더레이터인 경우 참가자 정보 추가
                if role == ParticipantRole.MODERATOR:
                    pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                    con_participants = self._get_participants_by_role(ParticipantRole.CON)
                    
                    # 모더레이터에게 전달할 데이터 구성
                    moderator_data = {
                        "action": "generate_response",
                        "context": context,
                        "dialogue_state": {
                            **self.state,
                            "topic": self.room_data.get('title', 'the topic'),
                            "participants_info": {
                                "pro": pro_participants,
                                "con": con_participants
                            }
                        },
                        "stance_statements": self.stance_statements
                    }
                    
                    try:
                        result = agent.process(moderator_data)
                    except Exception as agent_error:
                        logger.error(f"Exception in moderator agent.process: {str(agent_error)}")
                        result = {"status": "error", "message": f"모더레이터 처리 중 예외 발생: {str(agent_error)}"}
                else:
                    # 일반 참가자인 경우
                    try:
                        result = agent.process({
                            "action": "generate_response",
                            "context": context,
                            "dialogue_state": self.state,
                            "stance_statements": self.stance_statements
                        })
                    except Exception as agent_error:
                        logger.error(f"Exception in agent.process: {str(agent_error)}")
                        result = {"status": "error", "message": f"에이전트 처리 중 예외 발생: {str(agent_error)}"}
                
                if result.get("status") == "success":
                    message = result.get("message", "응답 생성에 실패했습니다.")
                else:
                    error_msg = result.get("message", "Unknown error")
                    logger.error(f"Agent process failed: {error_msg}")
                    message = f"응답 생성 중 오류가 발생했습니다: {error_msg}"
            
            # 대화 상태 업데이트
            self.state["turn_count"] += 1
            self.state["last_update_time"] = time.time()
            
            # 발언 기록 추가
            self.state["speaking_history"].append({
                "turn": self.state["turn_count"],
                "speaker_id": speaker_id,
                "role": role,
                "stage": current_stage,
                "message": message,
                "timestamp": time.time()
            })
            
            return {
                "status": "success",
                "speaker_id": speaker_id,
                "role": role,
                "message": message,
                "current_stage": current_stage,
                "turn_count": self.state["turn_count"]
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "status": "error",
                "message": f"응답 생성 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _start_next_speaker_preparation(self) -> None:
        """다음 발언자의 백그라운드 준비 시작"""
        try:
            # 현재 단계에서 다음에 올 발언자들 예측
            current_stage = self.state["current_stage"]
            
            if current_stage == DebateStage.OPENING:
                # 오프닝 후 → 찬성측 첫 번째 발언자 준비
                pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                if pro_participants:
                    next_speaker_info = {
                        "speaker_id": pro_participants[0],
                        "role": ParticipantRole.PRO
                    }
                    asyncio.create_task(self._prepare_next_speaker_in_background(next_speaker_info))
                    
            elif current_stage == DebateStage.PRO_ARGUMENT:
                # 찬성측 입론 중 → 다음 찬성측 또는 반대측 첫 번째 준비
                pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                con_participants = self._get_participants_by_role(ParticipantRole.CON)
                
                # 현재 찬성측 발언 순서 확인
                pro_speaking_count = len([
                    h for h in self.state.get("speaking_history", [])
                    if h.get("stage") == DebateStage.PRO_ARGUMENT and h.get("role") == ParticipantRole.PRO
                ])
                
                if pro_speaking_count < len(pro_participants):
                    # 다음 찬성측 준비
                    next_speaker_info = {
                        "speaker_id": pro_participants[pro_speaking_count],
                        "role": ParticipantRole.PRO
                    }
                    asyncio.create_task(self._prepare_next_speaker_in_background(next_speaker_info))
                elif con_participants:
                    # 반대측 첫 번째 준비
                    next_speaker_info = {
                        "speaker_id": con_participants[0],
                        "role": ParticipantRole.CON
                    }
                    asyncio.create_task(self._prepare_next_speaker_in_background(next_speaker_info))
                    
            elif current_stage == DebateStage.CON_ARGUMENT:
                # 반대측 입론 중 → 다음 반대측 준비
                con_participants = self._get_participants_by_role(ParticipantRole.CON)
                
                con_speaking_count = len([
                    h for h in self.state.get("speaking_history", [])
                    if h.get("stage") == DebateStage.CON_ARGUMENT and h.get("role") == ParticipantRole.CON
                ])
                
                if con_speaking_count < len(con_participants):
                    next_speaker_info = {
                        "speaker_id": con_participants[con_speaking_count],
                        "role": ParticipantRole.CON
                    }
                    asyncio.create_task(self._prepare_next_speaker_in_background(next_speaker_info))
                    
        except Exception as e:
            logger.error(f"Error starting next speaker preparation: {str(e)}")
    
    def _build_response_context(self, speaker_id: str, role: str) -> Dict[str, Any]:
        """응답 생성을 위한 컨텍스트 구성"""
        current_stage = self.state["current_stage"]
        
        # 단계별로 필요한 컨텍스트 최적화
        if current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
            # 입론 단계에서는 이전 대화 기록 없이 주제와 입장만 제공
            recent_messages = []
            
        elif current_stage in [DebateStage.INTERACTIVE_ARGUMENT, DebateStage.MODERATOR_SUMMARY_2]:
            # 상호논증 단계에서는 현재 QA 세션의 메시지만 포함 + 이전 중요 메시지 일부
            qa_messages = [
                msg for msg in self.state["speaking_history"] 
                if msg.get("stage") == current_stage
            ]
            
            # QA가 진행 중이면 현재 QA 세션의 메시지만, 시작 시에는 이전 단계 요약 포함
            if qa_messages:
                recent_messages = qa_messages
            else:
                # QA 세션 시작 시 - 이전 요약 포함
                summary_stage = DebateStage.MODERATOR_SUMMARY_1
                summary_messages = [
                    msg for msg in self.state["speaking_history"] 
                    if msg.get("stage") == summary_stage
                ]
                recent_messages = summary_messages
            
        else:
            # 그 외 단계(모더레이터 요약 등)에서는 이전 단계의 메시지 모두 포함
            # 현재 단계 직전 단계의 메시지들
            prev_stage_index = DebateStage.STAGE_SEQUENCE.index(current_stage) - 1
            if prev_stage_index >= 0:
                prev_stage = DebateStage.STAGE_SEQUENCE[prev_stage_index]
                stage_messages = [
                    msg for msg in self.state["speaking_history"]
                    if msg.get("stage") == prev_stage
                ]
                # 최근 5개로 제한
                recent_messages = stage_messages[-5:]
            else:
                recent_messages = []
        
        # 관련 벡터 검색 (벡터 저장소가 있는 경우)
        relevant_context = []
        if self.vector_store:
            # 현재 토론 단계와 역할에 맞는 쿼리 구성
            if current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
                # 입론 단계에서는 주제 자체를 쿼리로 사용
                query = self.room_data.get('title', '')
                if role == ParticipantRole.PRO:
                    query += " " + self.stance_statements.get("pro", "")
                else:
                    query += " " + self.stance_statements.get("con", "")
            else:
                # 다른 단계에서는 최근 발언을 쿼리로 사용
                query_messages = recent_messages[-2:] if recent_messages else []
                query = " ".join([msg.get("text", "") for msg in query_messages])
                
                # 쿼리가 비어있으면 주제 사용
                if not query.strip():
                    query = self.room_data.get('title', '')
            
            search_results = self.vector_store.search(query, limit=3)
            relevant_context = [result.get('text', '') for result in search_results]
        
        # 감정 컨텍스트 추가 (반론과 QA 단계에서만)
        emotion_enhancement = {}
        if current_stage in [DebateStage.INTERACTIVE_ARGUMENT, DebateStage.MODERATOR_SUMMARY_2]:
            logger.info(f"Attempting to add emotion enhancement for {speaker_id} in stage {current_stage}")
            try:
                # 상대측 발언 추출 (감정 추론에 사용)
                opponent_role = ParticipantRole.CON if role == ParticipantRole.PRO else ParticipantRole.PRO
                logger.info(f"Identified opponent role as {opponent_role} for speaker with role {role}")
                
                # 상대측 메시지 수집
                if current_stage in [DebateStage.INTERACTIVE_ARGUMENT, DebateStage.MODERATOR_SUMMARY_2]:
                    # 상호논증 단계에서는 상대측 입론 사용
                    opponent_stage = DebateStage.CON_ARGUMENT if role == ParticipantRole.PRO else DebateStage.PRO_ARGUMENT
                    logger.info(f"Using opponent messages from stage {opponent_stage} for rebuttal")
                    opponent_messages = [
                        msg for msg in self.state["speaking_history"] 
                        if msg.get("stage") == opponent_stage and msg.get("role") == opponent_role
                    ]
                else:
                    # QA 단계에서는 현재 QA 세션의 상대측 메시지 사용
                    logger.info(f"Using opponent messages from current QA session stage {current_stage}")
                    opponent_messages = [
                        msg for msg in self.state["speaking_history"] 
                        if msg.get("stage") == current_stage and msg.get("role") == opponent_role
                    ]
                
                logger.info(f"Found {len(opponent_messages)} opponent messages for emotion inference")
                
                # 인스턴스 변수 사용 (중복 초기화 제거)
                llm_manager = self.llm_manager
                
                # 화자의 입장 진술문 가져오기
                speaker_stance = self.stance_statements.get(role.lower(), "") if role.lower() in ["pro", "con"] else ""
                logger.info(f"Using speaker stance statement: {speaker_stance[:50]}...")
                
                # 감정 추론 호출
                if opponent_messages and llm_manager:
                    logger.info(f"Calling infer_debate_emotion for {speaker_id}")
                    emotion_data = infer_debate_emotion(
                        llm_manager=llm_manager,
                        speaker_id=speaker_id,
                        speaker_role=role.lower(),
                        opponent_messages=opponent_messages,
                        debate_topic=self.room_data.get('title', ''),
                        debate_stage=current_stage,
                        stance_statement=speaker_stance
                    )
                    
                    # 결과에서 프롬프트 향상 정보 추출
                    if "prompt_enhancement" in emotion_data:
                        emotion_enhancement = emotion_data["prompt_enhancement"]
                        logger.info(f"Applied emotion inference for {speaker_id} in {current_stage}. Emotion: {emotion_enhancement.get('emotion_state', 'unknown')}")
                    else:
                        logger.warning(f"No prompt_enhancement data found in emotion inference result")
                else:
                    logger.warning(f"Skipping emotion inference - No opponent messages or LLM manager available")
            except Exception as e:
                logger.error(f"Error inferring emotion: {str(e)}", exc_info=True)
                
        else:
            logger.info(f"Skipping emotion inference for stage {current_stage} - Not a rebuttal or QA stage")
        
        return {
            "topic": self.room_data.get('title', ''),
            "recent_messages": recent_messages,
            "relevant_context": relevant_context,
            "current_stage": self.state["current_stage"],
            "turn_count": self.state["turn_count"],
            "emotion_enhancement": emotion_enhancement
        }
    
    def get_next_speaker(self) -> Dict[str, Any]:
        """
        토론 단계와 순서에 따른 다음 발언자 결정
        
        Returns:
            다음 발언자 정보
        """
        current_stage = self.state["current_stage"]
        
        if current_stage == DebateStage.COMPLETED:
            return {
                "speaker_id": None, 
                "role": None, 
                "status": "completed",
                "is_user": False
            }
        
        # 각 단계별 다음 발언자 결정
        if current_stage == DebateStage.OPENING:
            next_speaker = self._get_next_opening_speaker()
        elif current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
            next_speaker = self._get_next_argument_speaker(current_stage)
        elif current_stage in [DebateStage.MODERATOR_SUMMARY_1, DebateStage.MODERATOR_SUMMARY_2]:
            next_speaker = {"speaker_id": self.state["moderator_id"], "role": ParticipantRole.MODERATOR}
        elif current_stage == DebateStage.INTERACTIVE_ARGUMENT:
            next_speaker = self._get_next_interactive_speaker()
        elif current_stage in [DebateStage.PRO_CONCLUSION, DebateStage.CON_CONCLUSION]:
            next_speaker = self._get_next_conclusion_speaker(current_stage)
        elif current_stage == DebateStage.CLOSING:
            next_speaker = {"speaker_id": self.state["moderator_id"], "role": ParticipantRole.MODERATOR}
        else:
            # 기본값: 모더레이터
            next_speaker = {"speaker_id": self.state["moderator_id"], "role": ParticipantRole.MODERATOR}
        
        # 사용자인지 여부 결정
        is_user = next_speaker["speaker_id"] in self.user_participants
        
        logger.info(f"Next speaker in room {self.room_id}: {next_speaker['speaker_id']} ({next_speaker['role']}), is_user: {is_user}")
                
        return {
            "speaker_id": next_speaker["speaker_id"],
            "role": next_speaker["role"],
            "dialogue_type": self.dialogue_type,
            "debate_stage": current_stage,
            "status": "ready",
                    "is_user": is_user
                }
        
    def _get_next_opening_speaker(self) -> Dict[str, str]:
        """오프닝 단계의 다음 발언자 결정"""
        speaking_history = self.state["speaking_history"]
        roles_spoken = [entry.get("role") for entry in speaking_history if entry.get("stage") == DebateStage.OPENING]
        
        # 모더레이터가 아직 발언하지 않았다면
        if ParticipantRole.MODERATOR not in roles_spoken:
            return {
                "speaker_id": self.state["moderator_id"],
                "role": ParticipantRole.MODERATOR
            }
        
        # 모더레이터 발언 후 다음 단계로 전환
        self.state["current_stage"] = DebateStage.PRO_ARGUMENT
        return self._get_next_argument_speaker(DebateStage.PRO_ARGUMENT)
    
    def _get_next_argument_speaker(self, stage: str) -> Dict[str, str]:
        """입론 단계의 다음 발언자 결정"""
        if stage == DebateStage.PRO_ARGUMENT:
            role = ParticipantRole.PRO
            participants = self.participants.get(ParticipantRole.PRO, [])
        else:  # CON_ARGUMENT
            role = ParticipantRole.CON
            participants = self.participants.get(ParticipantRole.CON, [])
        
        if not participants:
            # 참가자가 없으면 다음 단계로
            self._advance_to_next_stage()
            return self.get_next_speaker()
        
        # 현재 단계에서 발언한 참가자들 확인
        stage_speakers = [msg.get("speaker_id") for msg in self.state["speaking_history"] 
                         if msg.get("stage") == stage and msg.get("role") == role]
        
        # 아직 발언하지 않은 참가자 찾기
        for participant in participants:
            if participant not in stage_speakers:
                return {"speaker_id": participant, "role": role}
        
        # 모든 참가자가 발언했으면 다음 단계로
        self._advance_to_next_stage()
        return self.get_next_speaker()
    
    def _get_next_interactive_speaker(self) -> Dict[str, str]:
        """상호논증 단계의 다음 발언자 결정"""
        # 간단한 번갈아가며 발언 로직
        stage_messages = [msg for msg in self.state["speaking_history"] 
                         if msg.get("stage") == DebateStage.INTERACTIVE_ARGUMENT]
        
        # 발언 수에 따라 찬성/반대 번갈아가며
        turn_count = len(stage_messages)
        
        if turn_count % 2 == 0:  # 짝수 턴: 찬성측
            participants = self.participants.get(ParticipantRole.PRO, [])
            role = ParticipantRole.PRO
        else:  # 홀수 턴: 반대측
            participants = self.participants.get(ParticipantRole.CON, [])
            role = ParticipantRole.CON
        
        if participants:
            # 해당 측에서 가장 적게 발언한 참가자 선택
            participant_counts = {}
            for p in participants:
                count = len([msg for msg in stage_messages 
                           if msg.get("speaker_id") == p and msg.get("role") == role])
                participant_counts[p] = count
            
            # 가장 적게 발언한 참가자 선택
            next_participant = min(participant_counts.keys(), key=lambda x: participant_counts[x])
            return {"speaker_id": next_participant, "role": role}
        
        # 참가자가 없으면 다음 단계로
        self._advance_to_next_stage()
        return self.get_next_speaker()
    
    def _get_next_conclusion_speaker(self, stage: str) -> Dict[str, str]:
        """결론 단계의 다음 발언자 결정"""
        if stage == DebateStage.PRO_CONCLUSION:
            role = ParticipantRole.PRO
            participants = self.participants.get(ParticipantRole.PRO, [])
        else:  # CON_CONCLUSION
            role = ParticipantRole.CON
            participants = self.participants.get(ParticipantRole.CON, [])
        
        if not participants:
            # 참가자가 없으면 다음 단계로
            self._advance_to_next_stage()
            return self.get_next_speaker()
        
        # 현재 단계에서 발언한 참가자들 확인
        stage_speakers = [msg.get("speaker_id") for msg in self.state["speaking_history"] 
                         if msg.get("stage") == stage and msg.get("role") == role]
        
        # 아직 발언하지 않은 참가자 찾기
        for participant in participants:
            if participant not in stage_speakers:
                return {"speaker_id": participant, "role": role}
        
        # 모든 참가자가 발언했으면 다음 단계로
        self._advance_to_next_stage()
        return self.get_next_speaker()
    
    def _advance_to_next_stage(self):
        """다음 단계로 전환"""
        current_stage = self.state["current_stage"]
        try:
            current_index = DebateStage.STAGE_SEQUENCE.index(current_stage)
            if current_index < len(DebateStage.STAGE_SEQUENCE) - 1:
                next_stage = DebateStage.STAGE_SEQUENCE[current_index + 1]
                self.state["current_stage"] = next_stage
                logger.info(f"Advanced from {current_stage} to {next_stage}")
            else:
                self.state["current_stage"] = DebateStage.COMPLETED
                logger.info(f"Debate completed")
        except ValueError:
            logger.error(f"Unknown stage: {current_stage}")
            self.state["current_stage"] = DebateStage.COMPLETED
    
    # === 대화 제어 메서드들 ===
    
    def pause(self) -> Dict[str, Any]:
        """
        대화 일시정지
        
        Returns:
            일시정지 결과
        """
        self.playing = False
        logger.info(f"Debate dialogue paused for room {self.room_id}")
        return {
            "status": "paused",
            "message": "토론이 일시정지되었습니다.",
            "playing": self.playing
        }
    
    def resume(self) -> Dict[str, Any]:
        """
        대화 재개
        
        Returns:
            재개 결과
        """
        self.playing = True
        logger.info(f"Debate dialogue resumed for room {self.room_id}")
        return {
            "status": "resumed",
            "message": "토론이 재개되었습니다.",
            "playing": self.playing
        }
    
    def toggle_playing(self) -> Dict[str, Any]:
        """
        대화 상태 토글 (재생 중이면 정지, 정지 중이면 재생)
        
        Returns:
            토글 결과
        """
        if self.playing:
            return self.pause()
        else:
            return self.resume()
    
    def is_playing(self) -> bool:
        """
        현재 대화 진행 상태 확인
        
        Returns:
            재생 중 여부
        """
        return self.playing
    
    def get_playing_status(self) -> Dict[str, Any]:
        """
        대화 진행 상태 정보 반환
        
        Returns:
            상태 정보
        """
        return {
            "playing": self.playing,
            "status": "playing" if self.playing else "paused",
            "room_id": self.room_id,
            "current_stage": self.state["current_stage"],
            "turn_count": self.state["turn_count"]
        }
    
    def get_dialogue_state(self) -> Dict[str, Any]:
        """
        현재 대화 상태 반환
        
        Returns:
            대화 상태 정보
        """
        return {
            "room_id": self.room_id,
            "dialogue_type": self.dialogue_type,
            "current_stage": self.state["current_stage"],
            "turn_count": self.state["turn_count"],
            "next_speaker": self.state["next_speaker"],
            "stance_statements": self.stance_statements,
            "speaking_history_count": len(self.state["speaking_history"]),
            "playing": self.playing,
            "status": "playing" if self.playing else "paused"
        }
    
    def get_user_participant(self, user_id: str) -> Optional[UserParticipant]:
        """특정 사용자의 UserParticipant 객체 반환"""
        return self.user_participants.get(user_id)
    
    def get_all_user_participants(self) -> Dict[str, UserParticipant]:
        """모든 사용자 참가자 객체들 반환"""
        return self.user_participants.copy()
    
    def add_user_participant(self, user_id: str, username: str, config: Dict[str, Any] = None) -> UserParticipant:
        """새로운 사용자 참가자 추가"""
        if user_id in self.user_participants:
            logger.warning(f"User {user_id} already exists in dialogue")
            return self.user_participants[user_id]
        
        # UserParticipant 객체 생성
        user_participant = UserParticipant(user_id, username, config or {})
        user_participant.current_dialogue_id = self.room_id
        
        # 참가자 목록에 추가
        self.user_participants[user_id] = user_participant
        self.participants[ParticipantRole.USER].append(user_id)
        
        # 에이전트 목록에도 추가
        self.agents[user_id] = user_participant
        
        logger.info(f"Added new user participant: {user_id} ({username})")
        return user_participant
    
    def remove_user_participant(self, user_id: str) -> bool:
        """사용자 참가자 제거"""
        if user_id not in self.user_participants:
            logger.warning(f"User {user_id} not found in dialogue")
            return False
        
        # 사용자 객체에서 대화 떠나기 처리
        user_participant = self.user_participants[user_id]
        user_participant.process({"action": "leave_dialogue"})
        
        # 각 목록에서 제거
        del self.user_participants[user_id]
        if user_id in self.participants[ParticipantRole.USER]:
            self.participants[ParticipantRole.USER].remove(user_id)
        if user_id in self.agents:
            del self.agents[user_id]
        
        logger.info(f"Removed user participant: {user_id}")
        return True
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """사용자 선호도 업데이트"""
        user_participant = self.get_user_participant(user_id)
        if user_participant:
            user_participant.update_preferences(preferences)
            logger.info(f"Updated preferences for user {user_id}")
            return True
        return False
    
    # 새로운 개선사항 관련 메서드들
    
    def add_streaming_listener(self, listener_func: callable):
        """스트리밍 이벤트 리스너 추가"""
        if self.event_stream:
            self.event_stream.add_listener(listener_func)
            logger.info(f"Added streaming listener for room {self.room_id}")
        else:
            logger.warning("Event stream not available - streaming not enabled")
    
    def remove_streaming_listener(self, listener_func: callable):
        """스트리밍 이벤트 리스너 제거"""
        if self.event_stream:
            self.event_stream.remove_listener(listener_func)
            logger.info(f"Removed streaming listener for room {self.room_id}")
    
    def get_initialization_progress(self) -> Dict[str, Any]:
        """초기화 진행 상황 조회"""
        if self.event_stream:
            return self.event_stream.get_progress_summary()
        else:
                return {
                "room_id": self.room_id,
                "streaming_enabled": False,
                "message": "Streaming not enabled"
            }
    
    def get_initialization_history(self) -> List[Dict[str, Any]]:
        """초기화 이벤트 히스토리 조회"""
        if self.event_stream:
            return self.event_stream.get_event_history()
        else:
            return []
    
    def cleanup_resources(self):
        """리소스 정리"""
        try:
            # RAG 병렬 처리기 정리
            if self.rag_processor:
                self.rag_processor.cleanup()
                logger.info(f"Cleaned up RAG processor for room {self.room_id}")
            
            # 이벤트 스트림 정리
            if self.event_stream:
                from ..events.initialization_events import cleanup_event_stream
                cleanup_event_stream(self.room_id)
                logger.info(f"Cleaned up event stream for room {self.room_id}")
            
            logger.info(f"Resource cleanup completed for room {self.room_id}")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {str(e)}")
    
    def __del__(self):
        """소멸자 - 리소스 정리"""
        try:
            self.cleanup_resources()
        except Exception as e:
            logger.error(f"Error in destructor: {str(e)}")
    
    # 성능 모니터링 메서드들
    
    # ========================================================================
    # PERFORMANCE MONITORING & METRICS
    # ========================================================================
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        metrics = {
            "room_id": self.room_id,
            "streaming_enabled": self.enable_streaming,
            "rag_processor_workers": self.rag_processor.max_workers if self.rag_processor else 0,
            "participants_count": {
                "pro": len(self.participants.get(ParticipantRole.PRO, [])),
                "con": len(self.participants.get(ParticipantRole.CON, [])),
                "moderator": len(self.participants.get(ParticipantRole.MODERATOR, [])),
                "user": len(self.participants.get(ParticipantRole.USER, []))
            },
            "agents_count": len(self.agents),
            "vector_store_available": self.vector_store is not None,
            "current_stage": self.state.get("current_stage", "unknown"),
            "turn_count": self.state.get("turn_count", 0),
            "playing": self.playing
        }
        
        # 초기화 진행 상황 추가
        if self.event_stream:
            progress = self.event_stream.get_progress_summary()
            metrics["initialization_progress"] = progress
        
        return metrics
    
    def _extract_opponent_key_points_for_interactive_stage(self) -> None:
        """
        상호논증 단계 시작 전에 각 에이전트가 상대방 논점을 추출하도록 함
        다중 참가자 지원: 상대편의 모든 참가자 논점을 추출
        """
        try:
            # 찬성측 입론 메시지들 수집 (모든 찬성측 참가자)
            pro_messages = [
                msg for msg in self.state["speaking_history"] 
                if msg.get("stage") == DebateStage.PRO_ARGUMENT and msg.get("role") == ParticipantRole.PRO
            ]
            
            # 반대측 입론 메시지들 수집 (모든 반대측 참가자)
            con_messages = [
                msg for msg in self.state["speaking_history"] 
                if msg.get("stage") == DebateStage.CON_ARGUMENT and msg.get("role") == ParticipantRole.CON
            ]
            
            # 찬성측 모든 에이전트에게 반대측 논점 추출 요청
            pro_participants = self.participants.get(ParticipantRole.PRO, [])
            for participant_id in pro_participants:
                # 개별 에이전트 또는 역할별 대표 에이전트 찾기
                agent = self.agents.get(participant_id) or self.agents.get(ParticipantRole.PRO)
                
                if agent and con_messages and hasattr(agent, 'extract_opponent_key_points'):
                    agent.extract_opponent_key_points(con_messages)
                    # 자신의 핵심 논점도 업데이트
                    if hasattr(agent, 'update_my_key_points_from_core_arguments'):
                        agent.update_my_key_points_from_core_arguments()
                    logger.info(f"PRO participant {participant_id} extracted opponent key points from {len(con_messages)} CON messages")
            
            # 반대측 모든 에이전트에게 찬성측 논점 추출 요청
            con_participants = self.participants.get(ParticipantRole.CON, [])
            for participant_id in con_participants:
                # 개별 에이전트 또는 역할별 대표 에이전트 찾기
                agent = self.agents.get(participant_id) or self.agents.get(ParticipantRole.CON)
                
                if agent and pro_messages and hasattr(agent, 'extract_opponent_key_points'):
                    agent.extract_opponent_key_points(pro_messages)
                    # 자신의 핵심 논점도 업데이트
                    if hasattr(agent, 'update_my_key_points_from_core_arguments'):
                        agent.update_my_key_points_from_core_arguments()
                    logger.info(f"CON participant {participant_id} extracted opponent key points from {len(pro_messages)} PRO messages")
            
            logger.info("Opponent key points extraction completed for all participants in interactive argument stage")
            
        except Exception as e:
            logger.error(f"Error extracting opponent key points: {str(e)}")
    
    # === 메시지 처리 메서드들 ===
    
    def process_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        사용자 메시지 처리
        
        Args:
            message: 사용자 메시지
            user_id: 사용자 ID
            
        Returns:
            처리 결과
        """
        # 대화 일시정지 상태 체크
        if not self.playing:
                return {
                "status": "paused",
                "message": "토론이 일시정지 상태입니다.",
                "playing": self.playing
            }
        
        # 사용자 참가자 확인
        user_participant = self.get_user_participant(user_id)
        if not user_participant:
                return {
                "status": "error",
                "reason": "user_not_found",
                "message": f"사용자 {user_id}를 찾을 수 없습니다."
            }
        
        # 현재 발언자가 이 사용자인지 확인
        next_speaker_info = self.get_next_speaker()
        if next_speaker_info.get("speaker_id") != user_id:
                return {
                "status": "error",
                "reason": "not_your_turn",
                "message": f"현재 {next_speaker_info.get('speaker_id')}의 차례입니다.",
                "next_speaker": next_speaker_info.get("speaker_id")
            }
        
        # 사용자 역할 확인
        user_role = self._get_user_role(user_id)
        current_stage = self.state["current_stage"]
        
        # 메시지를 speaking_history에 추가
        self.state["speaking_history"].append({
            "speaker_id": user_id,
            "role": user_role,
            "timestamp": time.time(),
            "stage": current_stage,
            "text": message
        })
        
        # 턴 카운트 증가
        self.state["turn_count"] += 1
        
        # 사용자 참가자 객체에 메시지 처리 요청
        user_participant.process({
            "action": "send_message",
            "message": message,
            "stage": current_stage,
            "dialogue_context": {
                "topic": self.room_data.get('title', ''),
                "stance_statements": self.stance_statements,
                "recent_messages": self.state["speaking_history"][-5:]
            }
        })
        
        logger.info(f"Processed user message from {user_id} in stage {current_stage}")
        
        return {
            "status": "success",
            "speaker_id": user_id,
            "role": user_role,
            "message": message,
            "stage": current_stage,
            "turn_count": self.state["turn_count"]
        }
    
    def _get_user_role(self, user_id: str) -> str:
        """사용자의 역할 확인"""
        # 각 역할별 참가자 목록에서 사용자 찾기
        for role, participants in self.participants.items():
            if user_id in participants:
                return role
        
        # 기본값
        return ParticipantRole.USER
    
    # ========================================================================
    # OPTION 2: ON-DEMAND ARGUMENT PREPARATION WITH BACKGROUND PRE-LOADING
    # ========================================================================
    
    def _prepare_moderator_opening_only(self) -> None:
        """모더레이터 오프닝만 미리 준비 (Option 2)"""
        try:
            moderator_agent = self.agents.get(ParticipantRole.MODERATOR)
            if moderator_agent:
                topic = self.room_data.get('title', '토론 주제')
                
                # 참가자 정보 수집
                pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                con_participants = self._get_participants_by_role(ParticipantRole.CON)
                
                # 모더레이터 오프닝 준비 - generate_introduction 액션 사용
                result = moderator_agent.process({
                    "action": "generate_introduction",
                    "dialogue_state": {
                        "topic": topic,
                        "stance_statements": self.stance_statements,
                        "participants_info": {
                            "pro": pro_participants,
                            "con": con_participants
                        }
                    }
                })
                
                if result.get("status") == "success":
                    logger.info("Moderator opening prepared successfully")
                else:
                    logger.warning("Failed to prepare moderator opening")
            else:
                logger.warning("No moderator agent found")
                
        except Exception as e:
            logger.error(f"Error preparing moderator opening: {str(e)}")
    
    async def _prepare_next_speaker_in_background(self, next_speaker_info: Dict[str, Any]) -> None:
        """
        다음 발언자의 입론을 백그라운드에서 미리 준비
        
        Args:
            next_speaker_info: 다음 발언자 정보
        """
        try:
            speaker_id = next_speaker_info.get("speaker_id")
            role = next_speaker_info.get("role")
            
            if not speaker_id or role not in [ParticipantRole.PRO, ParticipantRole.CON]:
                return
            
            # 이미 준비 중이면 스킵
            if speaker_id in self.background_preparation_tasks:
                return
            
            agent = self.agents.get(speaker_id)
            if not agent or not hasattr(agent, 'prepare_argument_async'):
                return
            
            # 이미 준비되어 있으면 스킵
            if hasattr(agent, 'is_argument_ready') and agent.is_argument_ready():
                return
            
            topic = self.room_data.get('title', '토론 주제')
            stance_statement = self.stance_statements.get(role, '')
            context = {
                "topic": topic,
                "role": role,
                "current_stage": self.state.get("current_stage")
            }
            
            logger.info(f"Starting background preparation for {speaker_id} ({role})")
            
            # 백그라운드에서 입론 준비 시작
            task = asyncio.create_task(
                agent.prepare_argument_async(topic, stance_statement, context)
            )
            self.background_preparation_tasks[speaker_id] = task
            
            # 완료 후 정리
            def cleanup_task(future):
                if speaker_id in self.background_preparation_tasks:
                    del self.background_preparation_tasks[speaker_id]
                
                if future.exception():
                    logger.error(f"Background preparation failed for {speaker_id}: {future.exception()}")
                else:
                    result = future.result()
                    logger.info(f"Background preparation completed for {speaker_id}: {result.get('status')}")
            
            task.add_done_callback(cleanup_task)
            
        except Exception as e:
            logger.error(f"Error starting background preparation: {str(e)}")
    
    def _get_argument_for_speaker(self, speaker_id: str, role: str) -> str:
        """
        발언자의 입론을 가져오기 (준비된 것이 있으면 사용, 없으면 즉시 생성)
        
        Args:
            speaker_id: 발언자 ID
            role: 발언자 역할
            
        Returns:
            입론 텍스트
        """
        agent = self.agents.get(speaker_id)
        if not agent:
            return "에이전트를 찾을 수 없습니다."
        
        topic = self.room_data.get('title', '토론 주제')
        stance_statement = self.stance_statements.get(role, '')
        context = {
            "topic": topic,
            "role": role,
            "current_stage": self.state.get("current_stage")
        }
        
        # 새로운 메서드 사용 (준비된 것이 있으면 사용, 없으면 즉시 생성)
        if hasattr(agent, 'get_prepared_argument_or_generate'):
            return agent.get_prepared_argument_or_generate(topic, stance_statement, context)
        else:
            # 기존 방식 fallback
            result = agent.process({
                "action": "prepare_argument",
                "topic": topic,
                "stance_statement": stance_statement,
                "context": context
            })
            
            if result.get("status") == "success" and hasattr(agent, 'prepared_argument'):
                return agent.prepared_argument
            else:
                return "입론 생성에 실패했습니다."