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
import os
import re
import requests
from bs4 import BeautifulSoup

from ..state.dialogue_state import DialogueState
from ...agents.base.agent import Agent
from ...agents.participant.user_participant import UserParticipant
from ...rag.retrieval.vector_store import VectorStore
from ...agents.utility.debate_emotion_inference import infer_debate_emotion, apply_debate_emotion_to_prompt
from ...models.llm.llm_manager import LLMManager  # LLMManager import 추가

# 🆕 DebateContextManager 추가
from ..context.debate_context_manager import DebateContextManager

# 새로운 개선사항 임포트 (고급 기능)
from ..events.initialization_events import (
    get_event_stream, 
    InitializationEventType, 
    TaskProgressTracker,
    create_console_listener
)
from ..parallel.rag_parallel import RAGParallelProcessor, PhilosopherDataLoader
from ...utils.pdf_processor import process_pdf

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

# LLM 작업별 최적화 전략 (일단 모두 gpt-4o로 통일)
LLM_STRATEGY = {
    # 고품질 필요 (창의성, 논리성)
    "opening_argument": {"model": "gpt-4o", "max_tokens": 8000},
    "conclusion": {"model": "gpt-4o", "max_tokens": 6000},
    
    # 중간 품질 (분석, 전략)
    "attack_strategy": {"model": "gpt-4o", "max_tokens": 4000},
    "defense_response": {"model": "gpt-4o", "max_tokens": 3000},
    "argument_analysis": {"model": "gpt-4o", "max_tokens": 3000},
    
    # 빠른 처리 (간단한 작업)
    "interactive_response": {"model": "gpt-4o", "max_tokens": 1500},
    "rag_query_generation": {"model": "gpt-4o", "max_tokens": 500},
    "keyword_extraction": {"model": "gpt-4o", "max_tokens": 200},
    
    # 기본값
    "default": {"model": "gpt-4o", "max_tokens": 4000}
}

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
    MODERATOR = "moderator"
    OBSERVER = "observer"  # USER → OBSERVER로 변경, 중립 관전자 역할

# ============================================================================
# MAIN DEBATE DIALOGUE CLASS
# ============================================================================

class DebateDialogue:
    """찬반토론 대화 형식 구현"""
    
    # ========================================================================
    # INITIALIZATION METHODS
    # ========================================================================
    
    def __init__(self, room_id: str = None, room_data: Dict[str, Any] = None, use_async_init: bool = True, enable_streaming: bool = False, 
                 title: str = None, context: str = "", pro_participants: List[str] = None, con_participants: List[str] = None, 
                 user_ids: List[str] = None, moderator_style: str = "Jamie the Host", message_callback: callable = None, 
                 sequential_rag_search: bool = True):
        """
        토론 대화 초기화
        
        Args:
            room_id: 방 고유 식별자 (기존 방식)
            room_data: 방 설정 데이터 (기존 방식)
            title: 토론 주제 (새 방식)
            context: 토론 컨텍스트 (새 방식)
            pro_participants: 찬성측 참가자 ID 리스트 (새 방식)
            con_participants: 반대측 참가자 ID 리스트 (새 방식)
            user_ids: 사용자 ID 리스트 (새 방식)
            moderator_style: 모더레이터 스타일 (새 방식)
            message_callback: 메시지 생성 시 호출될 콜백 함수 (새 방식)
            use_async_init: 비동기 초기화 사용 여부
            enable_streaming: 스트리밍 활성화 여부
            sequential_rag_search: RAG 검색을 직렬로 처리할지 여부 (False=병렬, True=직렬)
        """
        # 콜백 함수 저장
        self.message_callback = message_callback
        
        # 새 방식 매개변수가 제공된 경우 room_data 구성
        if title is not None:
            room_data = {
                'title': title,
                'context': context,
                'participants': {
                    'pro': [{'id': pid} for pid in (pro_participants or [])],
                    'con': [{'id': pid} for pid in (con_participants or [])],
                    'users': user_ids or []
                },
                'moderator_style': moderator_style
            }
            # room_id가 없으면 기본값 생성
            if room_id is None:
                room_id = f"debate_{int(time.time())}"
        
        # 기존 초기화 로직
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
        
        # 🆕 DebateContextManager 초기화 및 요약 생성
        self.context_manager = self._initialize_context_manager()
        self.context_summary = self._generate_context_summary()
        
        self.stance_statements = self._generate_stance_statements()  # agents 초기화 전에 생성
        self.agents = self._initialize_agents()  # stance_statements 이후에 초기화
        
        # Option 2: 오프닝만 즉시 준비, 입론은 On-Demand
        # 모더레이터 오프닝만 미리 준비
        self._prepare_moderator_opening_only()
        
        # 논지 분석 상태 추적 시스템 초기화
        self._initialize_analysis_tracking()
        
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
            self.rag_processor = RAGParallelProcessor(max_workers=4, sequential_search=sequential_rag_search)
            logger.info(f"RAG Processor initialized - Search mode: {'Sequential' if sequential_rag_search else 'Parallel'}")
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
                    "total_tasks": 2,  # stance_statements, moderator_opening (입론 준비 제거)
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
            
            # ===== 입론 준비 부분 주석 처리 시작 =====
            # 이제 각 에이전트가 실시간으로 자신만의 입론을 생성하도록 함
            
            # # Pro 측 입론 준비 (에이전트가 있는 경우에만)
            # if ParticipantRole.PRO in self.agents:
            #     pro_tracker = TaskProgressTracker("pro_argument", self.event_stream) if self.event_stream else None
            #     task_trackers.append(pro_tracker)
            #     tasks.append(self._prepare_pro_argument_async_enhanced(pro_tracker))
            # else:
            #     tasks.append(self._create_dummy_task("pro_argument", None))
            
            # # Con 측 입론 준비 (에이전트가 있는 경우에만)
            # if ParticipantRole.CON in self.agents:
            #     con_tracker = TaskProgressTracker("con_argument", self.event_stream) if self.event_stream else None
            #     task_trackers.append(con_tracker)
            #     tasks.append(self._prepare_con_argument_async_enhanced(con_tracker))
            # else:
            #     tasks.append(self._create_dummy_task("con_argument", None))
            
            # ===== 입론 준비 부분 주석 처리 끝 =====
            
            # 모더레이터 오프닝 준비만 유지
            if ParticipantRole.MODERATOR in self.agents:
                moderator_tracker = TaskProgressTracker("moderator_opening", self.event_stream) if self.event_stream else None
                task_trackers.append(moderator_tracker)
                tasks.append(self._prepare_moderator_opening_async_enhanced(moderator_tracker))
            else:
                tasks.append(self._create_dummy_task("moderator_opening", None))
            
            # 병렬 작업 실행 (모더레이터 오프닝만)
            logger.info(f"Starting {len(tasks)} parallel tasks (moderator opening only)")
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 모든 결과 통합 (stance_statements + 병렬 작업들)
            all_results = [stance_result] + list(parallel_results)
            
            # 결과 처리
            initialization_results = self._process_async_results(all_results)
            
            # 최종 설정
            self.playing = True
            
            total_time = time.time() - start_time
            logger.info(f"Enhanced async initialization completed in {total_time:.2f} seconds (without pre-generating arguments)")
            
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
        """참가자 정보 초기화 - 통일된 배열 기반 처리"""
        participants = {
            ParticipantRole.PRO: [],
            ParticipantRole.CON: [],
            ParticipantRole.MODERATOR: [],
            ParticipantRole.OBSERVER: [],
        }
        
        # room_data에서 참가자 정보 추출
        participants_data = self.room_data.get('participants', {})
        user_ids = set(participants_data.get('users', []))  # 사용자 ID 목록
        
        # PRO 측 참가자 추가 (배열 기반 통일 처리)
        if 'pro' in participants_data:
            pro_data = participants_data['pro']
            
            # 단일 객체를 배열로 변환 (하위 호환성)
            if not isinstance(pro_data, list):
                pro_data = [pro_data] if pro_data else []
            
            for i, participant in enumerate(pro_data):
                # ID 통일: id -> character_id -> philosopher_key 순으로 확인
                participant_id = (
                    participant.get('id') or 
                    participant.get('character_id') or 
                    participant.get('philosopher_key') or 
                    f'pro_agent_{i+1}'
                )
                participants[ParticipantRole.PRO].append(participant_id)
                
                # 사용자인지 확인
                if participant_id in user_ids:
                    logger.info(f"Added PRO participant {i+1}: {participant_id} (USER)")
                else:
                    logger.info(f"Added PRO participant {i+1}: {participant_id} (AI)")
        
        # CON 측 참가자 추가 (배열 기반 통일 처리)
        if 'con' in participants_data:
            con_data = participants_data['con']
            
            # 단일 객체를 배열로 변환 (하위 호환성)
            if not isinstance(con_data, list):
                con_data = [con_data] if con_data else []
            
            for i, participant in enumerate(con_data):
                # ID 통일: id -> character_id -> philosopher_key 순으로 확인
                participant_id = (
                    participant.get('id') or 
                    participant.get('character_id') or 
                    participant.get('philosopher_key') or 
                    f'con_agent_{i+1}'
                )
                participants[ParticipantRole.CON].append(participant_id)
                
                # 사용자인지 확인
                if participant_id in user_ids:
                    logger.info(f"Added CON participant {i+1}: {participant_id} (USER)")
                else:
                    logger.info(f"Added CON participant {i+1}: {participant_id} (AI)")
        
        # PRO/CON에 포함되지 않은 사용자만 OBSERVER 역할로 추가
        assigned_users = set()
        assigned_users.update(participants[ParticipantRole.PRO])
        assigned_users.update(participants[ParticipantRole.CON])
        
        for user_id in user_ids:
            if user_id not in assigned_users:
                participants[ParticipantRole.OBSERVER].append(user_id)
                logger.info(f"Added neutral OBSERVER participant: {user_id}")
        
        # 모더레이터 추가
        participants[ParticipantRole.MODERATOR].append("moderator")
        
        logger.info(f"Initialized participants - PRO: {len(participants[ParticipantRole.PRO])}, CON: {len(participants[ParticipantRole.CON])}, OBSERVER: {len(participants[ParticipantRole.OBSERVER])}")
        
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
            user_role = "observer"  # 기본값: 관전자
            if user_id in self.participants.get(ParticipantRole.PRO, []):
                user_role = "pro"
            elif user_id in self.participants.get(ParticipantRole.CON, []):
                user_role = "con"
            elif user_id in self.participants.get(ParticipantRole.OBSERVER, []):
                user_role = "observer"  # 중립 관전자
            
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
            "moderator_id": "moderator",  # 대문자 "Moderator"에서 소문자 "moderator"로 수정
            # 논지 분석 상태 추적 시스템
            "argument_analysis_status": {},  # {speaker_id: {target_speaker_id: completion_status}}
            "analysis_completion_tracker": {}  # {speaker_id: {target_speaker_id: True/False}}
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
                
                # 컨텍스트 타입 판별 및 처리
                processed_text = self._process_context_by_type(context)
                
                # 컨텍스트를 슬라이딩 윈도우 방식으로 청크화
                paragraphs = self._split_context_to_paragraphs(processed_text)
                
                # 벡터 저장소에 단락들 추가
                vector_store.add_documents(paragraphs)
                
                logger.info(f"Vector store initialized with context ({len(processed_text)} chars), {len(paragraphs)} chunks")
                return vector_store
            except Exception as e:
                logger.error(f"Error initializing vector store: {str(e)}")
                return None
        return None
        
    def _process_context_by_type(self, context: str) -> str:
        """컨텍스트 타입에 따라 적절히 처리"""
        context = context.strip()
        
        # PDF 파일 경로인지 확인
        if context.lower().endswith('.pdf') and os.path.exists(context):
            logger.info(f"Processing PDF file: {context}")
            return self._process_pdf_context(context)
        
        # URL인지 확인
        elif context.startswith(('http://', 'https://')):
            logger.info(f"Processing URL: {context}")
            return self._process_url_context(context)
        
        # 일반 텍스트
        else:
            logger.info("Processing text context")
            return context
    
    def _process_pdf_context(self, pdf_path: str) -> str:
        """PDF 파일을 텍스트로 변환"""
        try:
            # 이미 import된 process_pdf 함수 사용
            text = process_pdf(
                pdf_path,
                use_grobid=False,  # Grobid 서버가 실행 중인 경우 True로 설정
                extraction_method="pymupdf"
            )
            
            if not text:
                raise ValueError("PDF에서 텍스트를 추출할 수 없습니다.")
                
            logger.info(f"PDF processing completed: {len(text)} characters extracted")
            return text
            
        except ImportError:
            logger.warning("pdf_processor module not available, using basic extraction")
            return self._process_pdf_basic(pdf_path)
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            return f"PDF 처리 실패: {str(e)}"
    
    def _process_pdf_basic(self, pdf_path: str) -> str:
        """기본 PDF 처리 (폴백용)"""
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
            
            # 여러 줄바꿈 정리
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text
            
        except ImportError:
            logger.error("pdfplumber not available for PDF processing")
            return "PDF 처리를 위한 라이브러리가 설치되지 않았습니다."
        except Exception as e:
            logger.error(f"Basic PDF processing failed: {str(e)}")
            return f"PDF 처리 실패: {str(e)}"
    
    def _process_url_context(self, url: str) -> str:
        """URL에서 텍스트 추출"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
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
            
            logger.info(f"URL processing completed: {len(text)} characters extracted")
            return text
            
        except ImportError:
            logger.error("requests or BeautifulSoup not available for URL processing")
            return "URL 처리를 위한 라이브러리가 설치되지 않았습니다."
        except Exception as e:
            logger.error(f"URL processing failed: {str(e)}")
            return f"URL 처리 실패: {str(e)}"
    
    def _split_context_to_paragraphs(self, context: str) -> List[str]:
        """컨텍스트를 슬라이딩 윈도우 방식으로 청크화"""
        try:
            # context_manager의 청크화 방식 사용
            from ...rag.retrieval.context_manager import ContextManager
            
            # 임시 ContextManager 생성 (청크화만 사용)
            context_manager = ContextManager(
                chunk_size=500,  # 토큰 단위
                chunk_overlap=0.25,  # 25% 오버랩
                chunking_method="hybrid"  # 문장 경계 보존 + 슬라이딩 윈도우
            )
            
            # 슬라이딩 윈도우 청크화 수행
            chunks = context_manager.chunk_text(context)
            
            logger.info(f"Sliding window chunking completed: {len(chunks)} chunks with 25% overlap")
            return chunks
            
        except ImportError as e:
            logger.warning(f"ContextManager not available, using fallback chunking: {str(e)}")
            # 기존 방식으로 폴백
            return self._split_context_fallback(context)
        except Exception as e:
            logger.error(f"Error in sliding window chunking: {str(e)}")
            # 기존 방식으로 폴백
            return self._split_context_fallback(context)
    
    def _split_context_fallback(self, context: str) -> List[str]:
        """기존 청크화 방식 (폴백용)"""
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
        """대화에 필요한 에이전트 초기화 - 통일된 배열 기반 처리"""
        try:
            # 직접 필요한 에이전트들 생성
            from ...agents.moderator.moderator_agent import ModeratorAgent
            from ...agents.participant.debate_participant_agent import DebateParticipantAgent
            
            agents = {}
            
            # 모더레이터 에이전트 생성 (기본 설정)
            moderator_config = self.room_data.get('moderator', {})
            moderator_agent = ModeratorAgent(
                agent_id=moderator_config.get("agent_id", "moderator_001"),
                name=moderator_config.get("name", "Moderator"),
                config={
                    "stance_statements": self.stance_statements,
                    "style": moderator_config.get("style", "neutral"),
                    "style_id": moderator_config.get("style_id", "0"),  # 기본값 "0" (Casual Young Moderator)
                    "personality": moderator_config.get("personality", "balanced"),
                    "context_summary": getattr(self, 'context_summary', {})  # context_summary 추가
                }
            )
            
            # ✅ 모더레이터에 LLM Manager 설정
            moderator_agent.set_llm_manager(self.llm_manager)
            agents[ParticipantRole.MODERATOR] = moderator_agent
            
            # 참가자 정보에서 철학자 에이전트 생성 (배열 기반 통일 처리)
            participants_data = self.room_data.get('participants', {})
            
            # PRO 측 에이전트들 생성 (배열 기반 통일 처리)
            if 'pro' in participants_data:
                pro_data = participants_data['pro']
                
                # 단일 객체를 배열로 변환 (하위 호환성)
                if not isinstance(pro_data, list):
                    pro_data = [pro_data] if pro_data else []
                
                first_agent = None
                for i, participant in enumerate(pro_data):
                    # ID 통일: id -> character_id -> philosopher_key 순으로 확인
                    participant_id = (
                        participant.get('id') or 
                        participant.get('character_id') or 
                        participant.get('philosopher_key') or 
                        f'pro_agent_{i+1}'
                    )
                    
                    # philosopher_key는 데이터 로드용 (participant_id와 동일값 사용)
                    philosopher_key = (
                        participant.get('philosopher_key') or
                        participant.get('character_id') or
                        participant.get('id') or
                        participant_id
                    )
                    
                    # 에이전트 생성
                    agent = DebateParticipantAgent.create_from_philosopher_key(
                        agent_id=participant_id,
                        philosopher_key=philosopher_key,
                        role=ParticipantRole.PRO,
                        config={
                            "stance_statements": self.stance_statements,
                            "personality": participant.get("personality", "balanced"),
                            "style": participant.get("style", "formal"),
                            "argumentation_style": participant.get("argumentation_style", "logical")
                        }
                    )
                    
                    # ✅ PRO 에이전트에 LLM Manager 설정
                    agent.set_llm_manager(self.llm_manager)
                    
                    agents[participant_id] = agent
                    
                    # 첫 번째 에이전트를 대표 에이전트로 설정 (하위 호환성)
                    if first_agent is None:
                        first_agent = agent
                        agents[ParticipantRole.PRO] = agent
                    
                    logger.info(f"Created PRO agent {i+1}: {participant_id} ({agent.philosopher_name})")
            
            # CON 측 에이전트들 생성 (배열 기반 통일 처리)
            if 'con' in participants_data:
                con_data = participants_data['con']
                
                # 단일 객체를 배열로 변환 (하위 호환성)
                if not isinstance(con_data, list):
                    con_data = [con_data] if con_data else []
                
                first_agent = None
                for i, participant in enumerate(con_data):
                    # 사용자 참가자는 건너뛰기 (별도 처리)
                    if participant.get('is_user', False):
                        continue
                    
                    # ID 통일: id -> character_id -> philosopher_key 순으로 확인
                    participant_id = (
                        participant.get('id') or 
                        participant.get('character_id') or 
                        participant.get('philosopher_key') or 
                        f'con_agent_{i+1}'
                    )
                    
                    # philosopher_key는 데이터 로드용 (participant_id와 동일값 사용)
                    philosopher_key = (
                        participant.get('philosopher_key') or
                        participant.get('character_id') or
                        participant.get('id') or
                        participant_id
                    )
                    
                    # 에이전트 생성
                    agent = DebateParticipantAgent.create_from_philosopher_key(
                        agent_id=participant_id,
                        philosopher_key=philosopher_key,
                        role=ParticipantRole.CON,
                        config={
                            "stance_statements": self.stance_statements,
                            "personality": participant.get("personality", "balanced"),
                            "style": participant.get("style", "formal"),
                            "argumentation_style": participant.get("argumentation_style", "logical")
                        }
                    )
                    
                    # ✅ CON 에이전트에 LLM Manager 설정
                    agent.set_llm_manager(self.llm_manager)
                    
                    agents[participant_id] = agent
                    
                    # 첫 번째 에이전트를 대표 에이전트로 설정 (하위 호환성)
                    if first_agent is None:
                        first_agent = agent
                        agents[ParticipantRole.CON] = agent
                    
                    logger.info(f"Created CON agent {i+1}: {participant_id} ({agent.philosopher_name})")
            
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
            
            # fallback 에이전트들 생성
            moderator_fallback = ModeratorAgent("moderator_001", "Moderator", {
                "stance_statements": self.stance_statements,
                "context_summary": getattr(self, 'context_summary', {})  # context_summary 추가
            })
            pro_fallback = DebateParticipantAgent("pro_agent", "Pro Participant", {"role": ParticipantRole.PRO, "stance_statements": self.stance_statements})
            con_fallback = DebateParticipantAgent("con_agent", "Con Participant", {"role": ParticipantRole.CON, "stance_statements": self.stance_statements})
            
            # ✅ fallback 에이전트들에도 LLM Manager 설정
            moderator_fallback.set_llm_manager(self.llm_manager)
            pro_fallback.set_llm_manager(self.llm_manager)
            con_fallback.set_llm_manager(self.llm_manager)
            
            fallback_agents = {
                ParticipantRole.MODERATOR: moderator_fallback,
                ParticipantRole.PRO: pro_fallback,
                ParticipantRole.CON: con_fallback
            }
            
            # 사용자 에이전트들도 fallback에 추가
            fallback_agents.update(self.user_participants)
            
            logger.warning(f"Using fallback agents due to initialization error")
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
        #context = self.room_data.get('context', '')
            
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
{self.context_summary if self.context_summary else "No additional context provided."}

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
                llm_model="gpt-4o",
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
        """역할별 참가자 목록 반환 (이미 초기화된 데이터 사용)"""
        return self.participants.get(role, [])
    
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
                message, rag_info = self._get_argument_for_speaker(speaker_id, role)
                
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
                        # dialogue_state에 participants 정보와 agents 참조 추가
                        enhanced_dialogue_state = {
                            **self.state,
                            "participants": self.participants,  # 참가자 정보 추가
                            "agents": self.agents  # 에이전트 참조 추가
                        }
                        
                        result = agent.process({
                            "action": "generate_response",
                            "context": context,
                            "dialogue_state": enhanced_dialogue_state,
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
                
                # 다른 단계에서 RAG 정보 추출 (participant agents에서만)
                rag_info = {}
                if role in [ParticipantRole.PRO, ParticipantRole.CON] and hasattr(agent, 'process'):
                    rag_info = {
                        "rag_used": result.get("rag_used", False),
                        "rag_source_count": result.get("rag_source_count", 0),
                        "rag_sources": result.get("rag_sources", [])
                    }
            
            # 대화 상태 업데이트
            self.state["turn_count"] += 1
            self.state["last_update_time"] = time.time()
            
            # 메시지 생성 및 저장
            message_obj = {
                "id": f"{speaker_id}-{int(time.time())}",
                "text": message,
                "speaker_id": speaker_id,
                "role": role,
                "stage": current_stage,
                "timestamp": time.time(),
                "turn_number": self.state["turn_count"],
                **rag_info  # RAG 정보 포함
            }
            
            # 발언 기록에 추가 (한 번만)
            self.state["speaking_history"].append(message_obj)
            
            # 🎯 메시지 콜백 호출 (WebSocket 전송)
            message_type = f"{role}_{current_stage}"
            if role == ParticipantRole.MODERATOR:
                message_type = f"moderator_{current_stage}"
            elif current_stage == DebateStage.PRO_ARGUMENT:
                message_type = "pro_argument"
            elif current_stage == DebateStage.CON_ARGUMENT:
                message_type = "con_argument"
            
            self._call_message_callback(speaker_id, message, message_type, current_stage)
            
            # 상호논증 단계에서 사이클 상태 업데이트
            if current_stage == DebateStage.INTERACTIVE_ARGUMENT and 'interactive_cycle_state' in self.state:
                cycle_state = self.state['interactive_cycle_state']
                current_step = cycle_state.get('cycle_step', 'unknown')
                
                # 단계별 사이클 상태 전환
                if current_step == 'attack':
                    # 공격 완료 → 방어로 전환
                    cycle_state['cycle_step'] = 'defense'
                    logger.info(f"Cycle state updated: attack → defense")
                elif current_step == 'defense':
                    # 방어 완료 → 팔로우업으로 전환
                    cycle_state['cycle_step'] = 'followup'
                    logger.info(f"Cycle state updated: defense → followup")
                elif current_step == 'followup':
                    # 팔로우업 완료 → 현재 사이클 완료하고 다음 사이클로 전환
                    current_cycle = cycle_state.get('current_cycle', 0)
                    attack_order = cycle_state.get('attack_order', [])
                    
                    # 현재 사이클 완료 기록
                    cycle_state['cycles_completed'].append({
                        'cycle': current_cycle,
                        'attacker': cycle_state.get('current_attacker'),
                        'defender': cycle_state.get('current_defender'),
                        'completed_at': time.time()
                    })
                    
                    logger.info(f"Cycle {current_cycle + 1} completed: {cycle_state.get('current_attacker')} → {cycle_state.get('current_defender')}")
                    
                    # 다음 사이클로 이동
                    cycle_state['current_cycle'] += 1
                    next_cycle_index = cycle_state['current_cycle']
                    
                    # 다음 사이클이 있는지 확인
                    if next_cycle_index < len(attack_order):
                        # 다음 공격자 정보 가져오기
                        next_attack_info = attack_order[next_cycle_index]
                        next_attacker_id = next_attack_info['attacker_id']
                        next_attacker_role = next_attack_info['attacker_role']
                        
                        # 역할을 한국어로 변환
                        role_korean = "찬성" if next_attacker_role == "pro" else "반대"
                        
                        # 다음 공격자 이름 가져오기
                        next_attacker_name = "알 수 없음"
                        if next_attacker_id in self.agents:
                            agent = self.agents[next_attacker_id]
                            next_attacker_name = getattr(agent, 'philosopher_name', getattr(agent, 'name', next_attacker_id))
                        
                        # 모더레이터 메시지 생성
                        moderator_message = f"이제 {role_korean}측 {next_attacker_name}의 차례입니다. 발언해주시죠."
                        
                        # 모더레이터 메시지를 speaking_history에 추가
                        moderator_msg_obj = {
                            "speaker_id": "moderator",
                            "role": ParticipantRole.MODERATOR,
                            "text": moderator_message,
                            "stage": current_stage,
                            "timestamp": time.time(),
                            "turn": self.state["turn_count"] + 1,
                            "type": "cycle_transition"
                        }
                        
                        self.state["speaking_history"].append(moderator_msg_obj)
                        self.state["turn_count"] += 1
                        
                        logger.info(f"Moderator cycle transition message: {moderator_message}")
                    
                    cycle_state['cycle_step'] = 'attack'  # 다음 사이클의 공격 단계로
                    
                    logger.info(f"Cycle state updated: followup → attack (next cycle {cycle_state['current_cycle'] + 1})")
                    
                    # 모든 사이클이 완료되었는지 확인
                    if cycle_state['current_cycle'] >= len(attack_order):
                        logger.info(f"All {len(attack_order)} cycles completed, interactive argument phase will end")
            
            # 논지 분석 및 공격 전략 준비 (완전히 백그라운드에서 실행 - 결과를 기다리지 않음)
            if role in [ParticipantRole.PRO, ParticipantRole.CON] and current_stage in [
                DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT, 
                DebateStage.INTERACTIVE_ARGUMENT
            ]:
                # 백그라운드 태스크로 즉시 실행 (결과를 기다리지 않음)
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    # fire-and-forget 방식으로 백그라운드 실행
                    loop.create_task(self._trigger_argument_analysis_async(speaker_id, message, role))
                    logger.info(f"Started background argument analysis for {speaker_id}")
                except RuntimeError:
                    # 이벤트 루프가 없으면 새 스레드에서 이벤트 루프 생성하여 실행
                    import threading
                    
                    def run_analysis_in_new_loop():
                        try:
                            # 새 이벤트 루프 생성
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            
                            # 논지 분석 실행
                            new_loop.run_until_complete(
                                self._trigger_argument_analysis_async(speaker_id, message, role)
                            )
                            
                            logger.info(f"Background argument analysis completed for {speaker_id}")
                        except Exception as e:
                            logger.error(f"Error in background argument analysis: {str(e)}")
                        finally:
                            # 이벤트 루프 정리
                            try:
                                new_loop.close()
                            except:
                                pass
                    
                    # 새 스레드에서 실행 (백그라운드)
                    analysis_thread = threading.Thread(target=run_analysis_in_new_loop, daemon=True)
                    analysis_thread.start()
                    logger.info(f"Started background argument analysis thread for {speaker_id}")
                except Exception as e:
                    logger.error(f"Failed to start background argument analysis: {str(e)}")
            
            # 다음 단계로 진행할지 확인
            should_advance, next_stage = self._should_advance_stage(current_stage)
            if should_advance:
                self.state["current_stage"] = next_stage
                logger.info(f"Advanced to next stage: {next_stage}")
            
            return {
                "status": "success",
                "message": message,
                "speaker_id": speaker_id,
                "speaker_role": role,
                "current_stage": self.state["current_stage"],
                "turn_count": self.state["turn_count"],
                "playing": self.playing
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "status": "error",
                "message": f"응답 생성 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _start_next_speaker_preparation(self) -> None:
        """다음 발언자 준비를 백그라운드에서 시작"""
        try:
            current_stage = self.state["current_stage"]
            
            if current_stage == DebateStage.OPENING:
                # 오프닝 후 → 찬성측 첫 번째 발언자 준비
                pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                if pro_participants:
                    next_speaker_info = {
                        "speaker_id": pro_participants[0],
                        "role": ParticipantRole.PRO
                    }
                    self._safe_create_background_task(next_speaker_info)
                    
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
                    self._safe_create_background_task(next_speaker_info)
                elif con_participants:
                    # 반대측 첫 번째 준비
                    next_speaker_info = {
                        "speaker_id": con_participants[0],
                        "role": ParticipantRole.CON
                    }
                    self._safe_create_background_task(next_speaker_info)
                    
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
                    self._safe_create_background_task(next_speaker_info)
                    
        except Exception as e:
            logger.error(f"Error starting next speaker preparation: {str(e)}")
    
    def _safe_create_background_task(self, next_speaker_info: Dict[str, Any]) -> None:
        """이벤트 루프가 있을 때만 백그라운드 태스크 생성"""
        try:
            import asyncio
            # 현재 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            if loop and not loop.is_closed():
                asyncio.create_task(self._prepare_next_speaker_in_background(next_speaker_info))
            else:
                logger.info("No running event loop found, skipping background task creation")
        except RuntimeError:
            # 이벤트 루프가 없는 경우
            logger.info("No event loop running, skipping background speaker preparation")
        except Exception as e:
            logger.error(f"Error creating background task: {str(e)}")
    
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
        다음 발언자 결정
        
        Returns:
            다음 발언자 정보 또는 대기 상태
        """
        current_stage = self.state["current_stage"]
        
        try:
            if current_stage == DebateStage.OPENING:
                next_speaker_info = self._get_next_opening_speaker()
            elif current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
                next_speaker_info = self._get_next_argument_speaker(current_stage)
            elif current_stage == DebateStage.INTERACTIVE_ARGUMENT:
                next_speaker_info = self._get_next_interactive_speaker()
            elif current_stage in [DebateStage.PRO_CONCLUSION, DebateStage.CON_CONCLUSION]:
                next_speaker_info = self._get_next_conclusion_speaker(current_stage)
            elif current_stage in [DebateStage.MODERATOR_SUMMARY_1, DebateStage.MODERATOR_SUMMARY_2, DebateStage.CLOSING]:
                next_speaker_info = {"speaker_id": "moderator", "role": ParticipantRole.MODERATOR}
            elif current_stage == DebateStage.COMPLETED:
                next_speaker_info = {"speaker_id": None, "role": None, "status": "completed"}
            else:
                logger.warning(f"Unknown stage: {current_stage}")
                next_speaker_info = {"speaker_id": None, "role": None, "status": "error"}
            
            # 대기 상태 확인
            if next_speaker_info.get("status") == "waiting_for_analysis":
                logger.info(f"Speaker waiting for analysis: {next_speaker_info}")
                return {
                    "status": "waiting",
                    "speaker_id": next_speaker_info.get("speaker_id"),
                    "role": next_speaker_info.get("role"),
                    "message": next_speaker_info.get("message", "분석 완료 대기 중"),
                    "current_stage": current_stage,
                    "can_proceed": False
                }
            
            # 정상 진행
            self.state["next_speaker"] = next_speaker_info
                
            return {
                "status": "ready",
                "speaker_id": next_speaker_info.get("speaker_id"),
                "role": next_speaker_info.get("role"),
                "current_stage": current_stage,
                "can_proceed": True
            }
            
        except Exception as e:
            logger.error(f"Error determining next speaker: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "current_stage": current_stage,
                "can_proceed": False
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
        
        logger.info(f"[DEBUG] _get_next_argument_speaker - stage: {stage}, role: {role}, participants: {participants}")
        
        if not participants:
            # 참가자가 없으면 다음 단계로
            logger.warning(f"[DEBUG] No participants for {role} in {stage}, advancing to next stage")
            self._advance_to_next_stage()
            return self.get_next_speaker()
        
        # 현재 단계에서 발언한 참가자들 확인 - 더 정확한 필터링
        stage_speakers = []
        for msg in self.state["speaking_history"]:
            msg_stage = msg.get("stage")
            msg_role = msg.get("role") 
            msg_speaker = msg.get("speaker_id")
            
            logger.info(f"[DEBUG] History entry: speaker={msg_speaker}, stage={msg_stage}, role={msg_role}")
            
            # 정확히 같은 stage와 role인 경우만 카운트
            if msg_stage == stage and msg_role == role and msg_speaker:
                stage_speakers.append(msg_speaker)
        
        logger.info(f"[DEBUG] Stage speakers for {stage}/{role}: {stage_speakers}")
        logger.info(f"[DEBUG] All participants for {role}: {participants}")
        
        # 아직 발언하지 않은 참가자 찾기 - 순서대로
        for participant in participants:
            if participant not in stage_speakers:
                logger.info(f"[DEBUG] Found next speaker: {participant} (role: {role})")
                return {"speaker_id": participant, "role": role}
        
        # 모든 참가자가 발언했으면 다음 단계로
        logger.info(f"[DEBUG] All participants have spoken in {stage}, advancing to next stage")
        self._advance_to_next_stage()
        return self.get_next_speaker()
    
    def _get_next_interactive_speaker(self) -> Dict[str, str]:
        """상호논증 단계의 다음 발언자 결정 - 공격-방어-팔로우업 사이클 관리"""
        stage_messages = [msg for msg in self.state["speaking_history"] 
                         if msg.get("stage") == DebateStage.INTERACTIVE_ARGUMENT]
        
        # 상호논증 상태 초기화 (처음이면)
        if 'interactive_cycle_state' not in self.state:
            self.state['interactive_cycle_state'] = {
                'current_cycle': 0,  # 현재 사이클 번호
                'cycle_step': 'attack',  # attack, defense, followup
                'current_attacker': None,
                'current_defender': None,
                'attack_order': self._generate_attack_order(),  # 공격 순서
                'cycles_completed': []  # 완료된 사이클들
            }
        
        cycle_state = self.state['interactive_cycle_state']
        attack_order = cycle_state['attack_order']
        
        # 모든 사이클이 완료되었으면 다음 단계로
        if cycle_state['current_cycle'] >= len(attack_order):
            logger.info("All interactive argument cycles completed, advancing to next stage")
            self._advance_to_next_stage()
            return self.get_next_speaker()
        
        current_cycle = cycle_state['current_cycle']
        current_step = cycle_state['cycle_step']
        
        # 현재 사이클의 공격자와 방어자 정보
        if current_cycle < len(attack_order):
            attacker_info = attack_order[current_cycle]
            attacker_id = attacker_info['attacker_id']
            attacker_role = attacker_info['attacker_role']
            defender_role = 'con' if attacker_role == 'pro' else 'pro'
            defender_participants = self.participants.get(defender_role, [])
            
            # 방어자 선택 (해당 역할의 첫 번째 참가자)
            defender_id = defender_participants[0] if defender_participants else None
        else:
            # 모든 사이클 완료
            self._advance_to_next_stage()
            return self.get_next_speaker()
        
        logger.info(f"Cycle {current_cycle + 1}/{len(attack_order)}: {current_step} step")
        logger.info(f"Attacker: {attacker_id} ({attacker_role}), Defender: {defender_id} ({defender_role})")
        
        # 단계별 다음 발언자 결정
        if current_step == 'attack':
            # 공격 단계
            cycle_state['current_attacker'] = attacker_id
            cycle_state['current_defender'] = defender_id
            
            # 분석 완료 여부 확인
            if self._can_speaker_proceed_with_analysis(attacker_id):
                logger.info(f"[{attacker_id}] attacking - analysis completed")
                # attack 단계에서는 공격자가 실제로 공격하고, 다음 턴에서 defense로 전환
                return {"speaker_id": attacker_id, "role": attacker_role}
            else:
                logger.info(f"[{attacker_id}] waiting for analysis completion")
            return {
                    "speaker_id": attacker_id, 
                    "role": attacker_role, 
                    "status": "waiting_for_analysis",
                    "message": f"{attacker_id}이(가) 상대방 논지 분석 완료를 기다리고 있습니다."
                }
        
        elif current_step == 'defense':
            # 방어 단계
            if defender_id:
                return {"speaker_id": defender_id, "role": defender_role}
            else:
                # 방어자가 없으면 팔로우업으로 넘어감
                cycle_state['cycle_step'] = 'followup'
                return {"speaker_id": attacker_id, "role": attacker_role}
        
        elif current_step == 'followup':
            # 팔로우업 단계 (공격자가 팔로우업 응답 생성)
            return {"speaker_id": attacker_id, "role": attacker_role}
        
        # Fallback
        logger.warning(f"Unexpected interactive argument state: {current_step}")
        return {"speaker_id": None, "role": None}
    
    def _generate_attack_order(self) -> List[Dict[str, str]]:
        """공격 순서 생성 - 반대측과 찬성측이 번갈아가며 공격"""
        pro_participants = self.participants.get(ParticipantRole.PRO, [])
        con_participants = self.participants.get(ParticipantRole.CON, [])
        
        attack_order = []
        
        # 최대 참가자 수만큼 사이클 생성
        max_participants = max(len(pro_participants), len(con_participants))
        
        for i in range(max_participants):
            # 반대측 공격 (CON이 먼저)
            if i < len(con_participants):
                attack_order.append({
                    'attacker_id': con_participants[i],
                    'attacker_role': 'con'
                })
            
            # 찬성측 공격 (PRO가 다음)
            if i < len(pro_participants):
                attack_order.append({
                    'attacker_id': pro_participants[i],
                    'attacker_role': 'pro'
                })
        
        # 공격 순서 로깅
        order_description = []
        for a in attack_order:
            order_description.append(f"{a['attacker_id']}({a['attacker_role']})")
        logger.info(f"Generated attack order: {order_description}")
        return attack_order
    
    def get_interactive_cycle_status(self) -> Dict[str, Any]:
        """상호논증 사이클 상태 조회 (디버깅용)"""
        if 'interactive_cycle_state' not in self.state:
            return {"status": "not_initialized"}
        
        cycle_state = self.state['interactive_cycle_state']
        return {
            "current_cycle": cycle_state.get('current_cycle', 0),
            "total_cycles": len(cycle_state.get('attack_order', [])),
            "cycle_step": cycle_state.get('cycle_step', 'unknown'),
            "current_attacker": cycle_state.get('current_attacker'),
            "current_defender": cycle_state.get('current_defender'),
            "attack_order": cycle_state.get('attack_order', []),
            "cycles_completed": cycle_state.get('cycles_completed', [])
        }
    
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
        self.participants[ParticipantRole.OBSERVER].append(user_id)
        
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
        if user_id in self.participants[ParticipantRole.OBSERVER]:
            self.participants[ParticipantRole.OBSERVER].remove(user_id)
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
                "observer": len(self.participants.get(ParticipantRole.OBSERVER, []))  # user → observer
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
        
        # 🔧 상호논증 단계에서 사이클 상태 업데이트 (generate_response와 동일한 로직 추가)
        if current_stage == DebateStage.INTERACTIVE_ARGUMENT and 'interactive_cycle_state' in self.state:
            cycle_state = self.state['interactive_cycle_state']
            current_step = cycle_state.get('cycle_step', 'unknown')
            
            # 단계별 사이클 상태 전환
            if current_step == 'attack':
                # 공격 완료 → 방어로 전환
                cycle_state['cycle_step'] = 'defense'
                logger.info(f"[process_message] Cycle state updated: attack → defense")
            elif current_step == 'defense':
                # 방어 완료 → 팔로우업으로 전환
                cycle_state['cycle_step'] = 'followup'
                logger.info(f"[process_message] Cycle state updated: defense → followup")
            elif current_step == 'followup':
                # 팔로우업 완료 → 현재 사이클 완료하고 다음 사이클로 전환
                current_cycle = cycle_state.get('current_cycle', 0)
                attack_order = cycle_state.get('attack_order', [])
                
                # 현재 사이클 완료 기록
                cycle_state['cycles_completed'].append({
                    'cycle': current_cycle,
                    'attacker': cycle_state.get('current_attacker'),
                    'defender': cycle_state.get('current_defender'),
                    'completed_at': time.time()
                })
                
                logger.info(f"[process_message] Cycle {current_cycle + 1} completed: {cycle_state.get('current_attacker')} → {cycle_state.get('current_defender')}")
                
                # 다음 사이클로 이동
                cycle_state['current_cycle'] += 1
                cycle_state['cycle_step'] = 'attack'  # 다음 사이클의 공격 단계로
                
                logger.info(f"[process_message] Cycle state updated: followup → attack (next cycle {cycle_state['current_cycle'] + 1})")
                
                # 모든 사이클이 완료되었는지 확인
                if cycle_state['current_cycle'] >= len(attack_order):
                    logger.info(f"[process_message] All {len(attack_order)} cycles completed, interactive argument phase will end")
        
        # 🔧 논지 분석 및 공격 전략 준비 (사용자 메시지에 대해서도 백그라운드 분석 시작)
        if user_role in [ParticipantRole.PRO, ParticipantRole.CON] and current_stage in [
            DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT, 
            DebateStage.INTERACTIVE_ARGUMENT
        ]:
            # 백그라운드 태스크로 즉시 실행 (결과를 기다리지 않음)
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                # fire-and-forget 방식으로 백그라운드 실행
                loop.create_task(self._trigger_argument_analysis_async(user_id, message, user_role))
                logger.info(f"[process_message] Started background argument analysis for {user_id}")
            except RuntimeError:
                # 이벤트 루프가 없으면 새 스레드에서 이벤트 루프 생성하여 실행
                import threading
                
                def run_analysis_in_new_loop():
                    try:
                        # 새 이벤트 루프 생성
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        
                        # 논지 분석 실행
                        new_loop.run_until_complete(
                            self._trigger_argument_analysis_async(user_id, message, user_role)
                        )
                        
                        logger.info(f"[process_message] Background argument analysis completed for {user_id}")
                    except Exception as e:
                        logger.error(f"[process_message] Error in background argument analysis: {str(e)}")
                    finally:
                        # 이벤트 루프 정리
                        try:
                            new_loop.close()
                        except:
                            pass
                
                # 새 스레드에서 실행 (백그라운드)
                analysis_thread = threading.Thread(target=run_analysis_in_new_loop, daemon=True)
                analysis_thread.start()
                logger.info(f"[process_message] Started background argument analysis thread for {user_id}")
            except Exception as e:
                logger.error(f"[process_message] Failed to start background argument analysis: {str(e)}")
        
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
        return ParticipantRole.OBSERVER
    
    # ========================================================================
    # OPTION 2: ON-DEMAND ARGUMENT PREPARATION WITH BACKGROUND PRE-LOADING
    # ========================================================================
    
    def _prepare_moderator_opening_only(self) -> None:
        """모더레이터 오프닝만 미리 준비 (Option 2)"""
        try:
            moderator_agent = self.agents.get(ParticipantRole.MODERATOR)
            if moderator_agent:
                topic = self.room_data.get('title', '토론 주제')
                
                # 참가자 정보 수집 - 올바른 순서로
                pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
                con_participants = self._get_participants_by_role(ParticipantRole.CON)
                
                logger.info(f"[DEBUG] Moderator opening - PRO: {pro_participants}, CON: {con_participants}")
                
                # 모더레이터 오프닝 준비 - generate_introduction 액션 사용
                result = moderator_agent.process({
                    "action": "generate_introduction",
                    "topic": topic,  # 직접 topic 전달
                    "stance_statements": self.stance_statements,
                    "participants_info": {
                        "pro": pro_participants,  # 찬성측 참가자
                        "con": con_participants   # 반대측 참가자
                    }
                })
                
            if result.get("status") == "success":
                logger.info("Moderator opening prepared successfully")
            else:
                logger.warning("Failed to prepare moderator opening")
                
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
    
    def _get_argument_for_speaker(self, speaker_id: str, role: str) -> tuple[str, Dict[str, Any]]:
        """
        발언자의 입론을 가져오기 (준비된 것이 있으면 사용, 없으면 즉시 생성)
        
        Args:
            speaker_id: 발언자 ID
            role: 발언자 역할
            
        Returns:
            (입론 텍스트, RAG 정보)
        """
        agent = self.agents.get(speaker_id)
        if not agent:
            return "에이전트를 찾을 수 없습니다.", {}
        
        topic = self.room_data.get('title', '토론 주제')
        stance_statement = self.stance_statements.get(role, '')
        context = {
            "topic": topic,
            "role": role,
            "current_stage": self.state.get("current_stage")
        }
        
        # 새로운 메서드 사용 (준비된 것이 있으면 사용, 없으면 즉시 생성)
        if hasattr(agent, 'get_prepared_argument_or_generate'):
            # 새로운 메서드가 RAG 정보도 함께 반환하는지 확인
            result = agent.get_prepared_argument_or_generate(topic, stance_statement, context)
            if isinstance(result, tuple) and len(result) == 2:
                message, rag_info = result
                return message, rag_info
            else:
                # 기존 방식 (문자열만 반환)
                message = result if isinstance(result, str) else str(result)
                return message, {}
        else:
            # 기존 방식 fallback - agent.process() 호출하여 딕셔너리 받기
            result = agent.process({
                "action": "prepare_argument",
                "topic": topic,
                "stance_statement": stance_statement,
                "context": context
            })
            
            if result.get("status") == "success":
                message = result.get("message", "입론 생성에 실패했습니다.")
                # RAG 정보 추출
                rag_info = {
                    "rag_used": result.get("rag_used", False),
                    "rag_source_count": result.get("rag_source_count", 0),
                    "rag_sources": result.get("rag_sources", [])
                }
                return message, rag_info
            else:
                return "입론 생성에 실패했습니다.", {}
    
    def _should_advance_stage(self, current_stage: str) -> tuple[bool, str]:
        """
        현재 단계에서 다음 단계로 진행할지 결정
        
        Args:
            current_stage: 현재 토론 단계
            
        Returns:
            (진행 여부, 다음 단계)
        """
        stage_sequence = DebateStage.STAGE_SEQUENCE
        current_index = stage_sequence.index(current_stage)
        
        # 각 단계별 진행 조건 확인
        if current_stage == DebateStage.OPENING:
            # 모더레이터 오프닝 완료 후 찬성측 입론으로
            return True, DebateStage.PRO_ARGUMENT
            
        elif current_stage == DebateStage.PRO_ARGUMENT:
            # 찬성측 입론 완료 후 반대측 입론으로
            pro_participants = self._get_participants_by_role(ParticipantRole.PRO)
            pro_messages = [msg for msg in self.state["speaking_history"] 
                          if msg.get("stage") == current_stage and msg.get("role") == ParticipantRole.PRO]
            
            if len(pro_messages) >= len(pro_participants):
                return True, DebateStage.CON_ARGUMENT
                
        elif current_stage == DebateStage.CON_ARGUMENT:
            # 반대측 입론 완료 후 모더레이터 요약으로
            con_participants = self._get_participants_by_role(ParticipantRole.CON)
            con_messages = [msg for msg in self.state["speaking_history"] 
                          if msg.get("stage") == current_stage and msg.get("role") == ParticipantRole.CON]
            
            if len(con_messages) >= len(con_participants):
                return True, DebateStage.MODERATOR_SUMMARY_1
                
        elif current_stage == DebateStage.MODERATOR_SUMMARY_1:
            # 모더레이터 요약 완료 후 상호논증으로
            return True, DebateStage.INTERACTIVE_ARGUMENT
            
        elif current_stage == DebateStage.INTERACTIVE_ARGUMENT:
            # 상호논증 단계에서 모든 사이클이 완료되었는지 확인
            if 'interactive_cycle_state' in self.state:
                cycle_state = self.state['interactive_cycle_state']
                attack_order = cycle_state.get('attack_order', [])
                cycles_completed = cycle_state.get('cycles_completed', [])
                
                # 실제로 완료된 사이클 수가 총 사이클 수와 같아야 다음 단계로
                if len(cycles_completed) >= len(attack_order):
                    logger.info(f"All {len(attack_order)} interactive cycles completed, advancing to next stage")
                    return True, DebateStage.MODERATOR_SUMMARY_2
                else:
                    logger.info(f"Interactive cycles in progress: {len(cycles_completed)}/{len(attack_order)} completed")
                    return False, current_stage
            else:
                # interactive_cycle_state가 없으면 초기화 필요 (일반적으로 발생하지 않음)
                return False, current_stage
        
        elif current_stage == DebateStage.MODERATOR_SUMMARY_2:
            # 두 번째 모더레이터 요약 완료 후 결론으로
            return True, DebateStage.PRO_CONCLUSION
            
        elif current_stage == DebateStage.PRO_CONCLUSION:
            # 찬성측 결론 완료 후 반대측 결론으로
            return True, DebateStage.CON_CONCLUSION
            
        elif current_stage == DebateStage.CON_CONCLUSION:
            # 반대측 결론 완료 후 모더레이터 마무리로
            return True, DebateStage.CLOSING
            
        elif current_stage == DebateStage.CLOSING:
            # 모더레이터 마무리 완료 후 토론 종료
            return True, DebateStage.COMPLETED
        
        return False, current_stage
    
    async def _trigger_argument_analysis_async(self, speaker_id: str, response_text: str, speaker_role: str):
        """
        발언 완료 후 다른 참가자들의 논지 분석 및 공격 전략 준비를 백그라운드에서 트리거
        
        Args:
            speaker_id: 발언자 ID
            response_text: 발언 내용
            speaker_role: 발언자 역할
        """
        try:
            logger.info(f"🔍 [_trigger_argument_analysis_async] 시작: speaker_id={speaker_id}, speaker_role={speaker_role}")
            
            # 상대편 참가자들 찾기
            if speaker_role == ParticipantRole.PRO:
                opponent_participants = self._get_participants_by_role(ParticipantRole.CON)
            else:
                opponent_participants = self._get_participants_by_role(ParticipantRole.PRO)
            
            logger.info(f"🔍 [_trigger_argument_analysis_async] 상대편 참가자들: {opponent_participants}")
            
            # 각 상대편 참가자에게 논지 분석 요청 (병렬 처리)
            analysis_tasks = []
            for opponent_id in opponent_participants:
                logger.info(f"🔍 [_trigger_argument_analysis_async] 상대편 {opponent_id} 처리 중...")
                
                opponent_agent = self.agents.get(opponent_id)
                if opponent_agent:
                    logger.info(f"✅ [_trigger_argument_analysis_async] 상대편 {opponent_id} 에이전트 발견, 분석 태스크 생성")
                    
                    # 각 에이전트의 분석을 별도 태스크로 실행
                    task = asyncio.create_task(self._analyze_single_opponent_async(
                        opponent_agent, opponent_id, speaker_id, response_text
                    ))
                    analysis_tasks.append(task)
                else:
                    logger.warning(f"❌ [_trigger_argument_analysis_async] 상대편 {opponent_id} 에이전트 없음 (agents: {list(self.agents.keys())})")
            
            # 모든 분석 태스크를 병렬로 실행
            if analysis_tasks:
                logger.info(f"🚀 [_trigger_argument_analysis_async] {len(analysis_tasks)}개 분석 태스크 시작")
                await asyncio.gather(*analysis_tasks, return_exceptions=True)
                logger.info(f"✅ [_trigger_argument_analysis_async] {len(analysis_tasks)}개 분석 태스크 완료")
            else:
                logger.warning(f"❌ [_trigger_argument_analysis_async] 실행할 분석 태스크가 없음")
                
        except Exception as e:
            logger.error(f"❌ [_trigger_argument_analysis_async] 오류: {str(e)}", exc_info=True)
    
    async def _analyze_single_opponent_async(self, opponent_agent, opponent_id: str, speaker_id: str, response_text: str):
        """
        단일 상대방 에이전트의 논지 분석을 비동기로 실행
        
        Args:
            opponent_agent: 상대방 에이전트 (분석을 수행하는 AI)
            opponent_id: 상대방 ID (분석을 수행하는 AI의 ID)
            speaker_id: 발언자 ID (분석 대상)
            response_text: 발언 내용 (분석할 내용)
        """
        try:
            # 사용자인지 AI인지 확인
            is_user_speaker = speaker_id in self.user_participants
            
            loop = asyncio.get_event_loop()
            
            if is_user_speaker:
                # 🎯 유저 논지 분석: AI가 유저의 논지를 분석
                logger.info(f"🔍 [{opponent_id}] 유저 {speaker_id} 논지 분석 시작")
                
                def analyze_user_sync():
                    # AI 에이전트가 유저 논지를 분석
                    return opponent_agent.analyze_user_arguments(response_text, speaker_id)
                
                analysis_result = await loop.run_in_executor(None, analyze_user_sync)
                
                arguments_count = analysis_result.get('total_arguments', 0)
                avg_vulnerability = analysis_result.get('average_vulnerability', 0.0)
                
                logger.info(f"✅ [{opponent_id}] → 유저 {speaker_id} 논지 분석 완료: "
                          f"{arguments_count}개 논지, 평균 취약성 {avg_vulnerability:.2f}")
                
                # 분석 결과를 기반으로 공격 전략 준비
                if arguments_count > 0:
                    def prepare_strategies_sync():
                        return opponent_agent.process({
                            "action": "prepare_attack_strategies",
                            "target_speaker_id": speaker_id
                        })
                    
                    strategy_result = await loop.run_in_executor(None, prepare_strategies_sync)
                    
                    strategies_count = len(strategy_result.get("strategies", []))
                    rag_usage_count = strategy_result.get("rag_usage_count", 0)
                    logger.info(f"✅ [{opponent_id}] → 유저 {speaker_id} 공격 전략 {strategies_count}개 준비 완료 (RAG 사용: {rag_usage_count}개)")
                
            else:
                # 🤖 AI vs AI 논지 분석 (기존 방식)
                logger.info(f"🔍 [{opponent_id}] AI {speaker_id} 논지 분석 시작")
                
                def analyze_sync():
                    return opponent_agent.process({
                        "action": "analyze_opponent_arguments",
                        "opponent_response": response_text,
                        "speaker_id": speaker_id
                    })
                
                analysis_result = await loop.run_in_executor(None, analyze_sync)
                
                logger.info(f"✅ [{opponent_id}] → AI {speaker_id} 논지 분석 완료: "
                          f"{analysis_result.get('arguments_count', 0)} arguments found")
                
                # 공격 전략 준비
                if analysis_result.get("status") == "success":
                    def prepare_strategies_sync():
                        return opponent_agent.process({
                            "action": "prepare_attack_strategies",
                            "target_speaker_id": speaker_id
                        })
                    
                    strategy_result = await loop.run_in_executor(None, prepare_strategies_sync)
                    
                    strategies_count = len(strategy_result.get("strategies", []))
                    rag_usage_count = strategy_result.get("rag_usage_count", 0)
                    logger.info(f"✅ [{opponent_id}] → AI {speaker_id} 공격 전략 {strategies_count}개 준비 완료 (RAG 사용: {rag_usage_count}개)")
            
            # 🎯 분석 완료 상태 업데이트 (유저든 AI든 동일하게 처리)
            self._mark_analysis_completed(opponent_id, speaker_id)
                
        except Exception as e:
            logger.error(f"❌ Error in argument analysis for {opponent_id} → {speaker_id}: {str(e)}")
    
    def get_attack_strategy_for_response(self, attacker_id: str, target_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        응답 생성 시 사용할 최적 공격 전략 가져오기
        
        Args:
            attacker_id: 공격자 ID
            target_id: 공격 대상 ID
            context: 현재 맥락
            
        Returns:
            선택된 공격 전략 (없으면 None)
        """
        try:
            attacker_agent = self.agents.get(attacker_id)
            if not attacker_agent:
                return None
            
            strategy_result = attacker_agent.process({
                "action": "get_best_attack_strategy",
                "target_speaker_id": target_id,
                "context": context
            })
            
            if strategy_result.get("status") == "success":
                return strategy_result.get("strategy")
            
        except Exception as e:
            logger.error(f"Error getting attack strategy: {str(e)}")
        
        return None
    
    def _initialize_analysis_tracking(self) -> None:
        """논지 분석 상태 추적 시스템 초기화"""
        # 모든 참가자 조합에 대해 분석 상태 초기화
        # self.participants 딕셔너리에서 직접 가져오기 (사용자 포함)
        pro_participants = self.participants.get(ParticipantRole.PRO, [])
        con_participants = self.participants.get(ParticipantRole.CON, [])
        
        # 찬성측 → 반대측 분석 상태
        for pro_id in pro_participants:
            if pro_id not in self.state["analysis_completion_tracker"]:
                self.state["analysis_completion_tracker"][pro_id] = {}
            for con_id in con_participants:
                self.state["analysis_completion_tracker"][pro_id][con_id] = False
        
        # 반대측 → 찬성측 분석 상태  
        for con_id in con_participants:
            if con_id not in self.state["analysis_completion_tracker"]:
                self.state["analysis_completion_tracker"][con_id] = {}
            for pro_id in pro_participants:
                self.state["analysis_completion_tracker"][con_id][pro_id] = False
        
        logger.info(f"Analysis tracking initialized for {len(pro_participants)} PRO vs {len(con_participants)} CON participants")
    
    def _can_speaker_proceed_with_analysis(self, speaker_id: str) -> bool:
        """해당 발언자가 모든 상대방 논지 분석을 완료했는지 확인"""
        if speaker_id not in self.state["analysis_completion_tracker"]:
            return False
        
        speaker_analysis = self.state["analysis_completion_tracker"][speaker_id]
        
        # 모든 상대방에 대한 분석이 완료되었는지 확인
        for target_id, is_completed in speaker_analysis.items():
            if not is_completed:
                logger.info(f"[{speaker_id}] waiting for analysis completion of [{target_id}]")
                return False
        
        logger.info(f"[{speaker_id}] all opponent analysis completed - can proceed")
        return True
    
    def _mark_analysis_completed(self, analyzer_id: str, target_id: str) -> None:
        """특정 분석자의 특정 대상에 대한 분석 완료 표시"""
        if analyzer_id not in self.state["analysis_completion_tracker"]:
            self.state["analysis_completion_tracker"][analyzer_id] = {}
        
        self.state["analysis_completion_tracker"][analyzer_id][target_id] = True
        logger.info(f"[{analyzer_id}] → [{target_id}] analysis marked as completed")

    def get_analysis_status(self) -> Dict[str, Any]:
        """현재 분석 상태 확인 (디버깅용)"""
        return {
            "analysis_completion_tracker": self.state.get("analysis_completion_tracker", {}),
            "current_stage": self.state.get("current_stage"),
            "participants": {
                "pro": self.participants.get(ParticipantRole.PRO, []),
                "con": self.participants.get(ParticipantRole.CON, [])
            }
        }
    
    def force_analysis_completion(self, analyzer_id: str, target_id: str = None) -> Dict[str, Any]:
        """분석 완료 강제 설정 (테스트/디버깅용)"""
        if target_id:
            self._mark_analysis_completed(analyzer_id, target_id)
            return {"status": "success", "message": f"[{analyzer_id}] → [{target_id}] analysis forced to complete"}
        else:
            # 해당 분석자의 모든 대상에 대해 완료 처리
            if analyzer_id in self.state["analysis_completion_tracker"]:
                for target in self.state["analysis_completion_tracker"][analyzer_id]:
                    self.state["analysis_completion_tracker"][analyzer_id][target] = True
                return {"status": "success", "message": f"[{analyzer_id}] all analysis forced to complete"}
            else:
                return {"status": "error", "message": f"[{analyzer_id}] not found in analysis tracker"}
    
    def _call_message_callback(self, speaker_id: str, message: str, message_type: str, stage: str):
        """메시지 콜백 호출 (안전하게)"""
        if self.message_callback:
            try:
                self.message_callback(speaker_id, message, message_type, stage)
            except Exception as e:
                logger.error(f"Error in message callback: {str(e)}")
    
    def _initialize_context_manager(self) -> Optional[DebateContextManager]:
        """DebateContextManager 초기화 및 컨텍스트 추가"""
        context = self.room_data.get('context', '')
        if not context:
            logger.info("No context provided, skipping DebateContextManager initialization")
            return None
        
        try:
            # DebateContextManager 생성
            context_manager = DebateContextManager(
                llm_manager=self.llm_manager,
                max_context_length=100000,  # 충분한 길이 설정 (8000 → 100000)
                max_summary_points=7  # 더 많은 요약 포인트
            )
            
            # 컨텍스트 타입에 따라 적절히 추가
            if context.lower().endswith('.pdf') and os.path.exists(context):
                logger.info(f"Adding PDF context to DebateContextManager: {context}")
                context_id = context_manager.add_file_context(context)
                
            elif context.startswith(('http://', 'https://')):
                logger.info(f"Adding URL context to DebateContextManager: {context}")
                context_id = context_manager.add_url_context(context)
                
            else:
                logger.info("Adding text context to DebateContextManager")
                title = self.room_data.get('title', 'Debate Context')
                context_id = context_manager.add_text_context(context, title=title)
            
            logger.info(f"DebateContextManager initialized with context_id: {context_id}")
            return context_manager
            
        except Exception as e:
            logger.error(f"Error initializing DebateContextManager: {str(e)}")
            return None
    
    def _generate_context_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약 생성 및 저장"""
        if not self.context_manager:
            logger.info("No context manager available, skipping summary generation")
            return {}
        
        try:
            # 토론 주제 가져오기
            topic = self.room_data.get('title', '토론 주제')
            
            # 자동 타입 판별된 요약 생성
            summary_result = self.context_manager.generate_summary(topic)
            
            # 추가 정보 수집
            bullet_points = self.context_manager.get_context_bullet_points(max_points=5)
            context_stats = self.context_manager.get_context_stats()
            type_summary = self.context_manager.get_context_type_summary()
            
            context_summary = {
                "objective_summary": summary_result.get("summary", ""),
                "bullet_points": bullet_points,
                "context_stats": context_stats,
                "type_summary": type_summary,
                "determined_type": type_summary.get("determined_type", "general"),
                "generation_timestamp": time.time()
            }
            
            logger.info(f"Context summary generated successfully")
            logger.info(f"Determined context type: {context_summary['determined_type']}")
            logger.info(f"Summary length: {len(context_summary['objective_summary'])} chars")
            logger.info(f"Bullet points: {len(bullet_points)} items")
            
            return context_summary
            
        except Exception as e:
            logger.error(f"Error generating context summary: {str(e)}")
            return {
                "objective_summary": "",
                "bullet_points": [],
                "context_stats": {},
                "type_summary": {},
                "determined_type": "general", 
                "error": str(e),
                "generation_timestamp": time.time()
            }
    
    # ========================================================================
    # CONTEXT SUMMARY ACCESS METHODS
    # ========================================================================
    
    def get_context_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약 정보 반환"""
        return self.context_summary if hasattr(self, 'context_summary') else {}
    
    def get_objective_summary(self) -> str:
        """객관적 요약 텍스트 반환"""
        return self.context_summary.get("objective_summary", "") if hasattr(self, 'context_summary') else ""
    
    def get_context_bullet_points(self) -> List[str]:
        """컨텍스트 핵심 포인트 반환"""
        return self.context_summary.get("bullet_points", []) if hasattr(self, 'context_summary') else []
    
    def get_determined_context_type(self) -> str:
        """자동 판별된 컨텍스트 타입 반환"""
        return self.context_summary.get("determined_type", "general") if hasattr(self, 'context_summary') else "general"
    
    def has_context_summary(self) -> bool:
        """컨텍스트 요약이 사용 가능한지 확인"""
        return (hasattr(self, 'context_summary') and 
                self.context_summary and 
                self.context_summary.get("objective_summary", "").strip())
    
    def refresh_context_summary(self) -> Dict[str, Any]:
        """컨텍스트 요약 새로고침"""
        if self.context_manager:
            self.context_summary = self._generate_context_summary()
            logger.info("Context summary refreshed")
        return self.get_context_summary()
    
    def get_context_for_prompt(self, include_summary: bool = True, include_bullets: bool = True) -> str:
        """프롬프트에 포함할 컨텍스트 정보 생성"""
        if not self.has_context_summary():
            return ""
        
        context_parts = []
        
        if include_summary:
            summary = self.get_objective_summary()
            if summary:
                context_parts.append(f"=== 컨텍스트 요약 ===\n{summary}")
        
        if include_bullets:
            bullets = self.get_context_bullet_points()
            if bullets:
                bullet_text = "\n".join(bullets)
                context_parts.append(f"=== 핵심 포인트 ===\n{bullet_text}")
        
        return "\n\n".join(context_parts)