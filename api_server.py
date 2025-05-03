# api_server.py 수정
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union, Set
import logging
import uvicorn
import os
import yaml
from fastapi.staticfiles import StaticFiles
import openai
import requests
from slugify import slugify
import time
import asyncio
import random
import aiohttp
from uuid import uuid4
from datetime import datetime
from types import SimpleNamespace
import json

# Sapiens Engine 임포트
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.config_loader import ConfigLoader

# NPC 임포트 부분 제거하고 직접 필요한 설명 생성

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# YAML 파일 로드 함수
def load_yaml_file(file_path):
    """YAML 파일을 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}")
        return {}

# 철학자 정보 로드
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHILOSOPHERS_FILE = os.path.join(BASE_DIR, "sapiens_engine/config/philosophers.yaml")
logger.info(f"Loading philosophers from: {PHILOSOPHERS_FILE}")
philosophers_data = load_yaml_file(PHILOSOPHERS_FILE)
if not philosophers_data:
    logger.warning("Failed to load philosophers data. Using hardcoded descriptions.")

# 철학자 초상화 매핑
PORTRAITS_MAP = {
    "socrates": "Socrates.png",
    "plato": "Plato.png",
    "aristotle": "Aristotle.png",
    "kant": "Kant.png",
    "nietzsche": "Nietzsche.png",
    "hegel": "Hegel.png",
    "marx": "Marx.png",
    "sartre": "Sartre.png",
    "camus": "Camus.png",
    "beauvoir": "Beauvoir.png",
    "rousseau": "Rousseau.png",
    "confucius": "Confucius.png",
    "laozi": "Laozi.png",
    "buddha": "Buddha.png",
    "wittgenstein": "Wittgenstein.png"
}

# 요청 모델 정의
class InitialChatRequest(BaseModel):
    philosopher: str
    topic: str
    context: Optional[str] = ""
    user_message: Optional[str] = None

# 채팅방 생성 요청 모델 추가
class ChatRoomCreationRequest(BaseModel):
    title: str
    context: Optional[str] = ""
    contextUrl: Optional[str] = None
    contextFileContent: Optional[str] = None
    maxParticipants: int
    npcs: List[str]
    isPublic: Optional[bool] = True
    currentUser: Optional[str] = None
    # 새 필드 추가
    generateInitialMessage: Optional[bool] = True
    llmProvider: Optional[str] = "openai"
    llmModel: Optional[str] = "gpt-4o"

# 대화 생성 요청 모델 추가
class ChatGenerateRequest(BaseModel):
    npc_descriptions: Optional[str] = None
    npcs: Optional[List[str]] = []  # 필수 필드를 Optional로 설정
    topic: Optional[str] = ""
    context: Optional[str] = ""
    previous_dialogue: Optional[str] = ""
    llm_provider: Optional[str] = "openai"
    llm_model: Optional[str] = "gpt-4o"
    api_key: Optional[str] = None  # 클라이언트에서 받은 API 키

# 응답 모델 정의
class ChatResponse(BaseModel):
    response: str
    philosopher: str
    metadata: Optional[Dict[str, Any]] = None

# Portrait generation request model
class PortraitRequest(BaseModel):
    npc_name: str
    role: str
    reference_philosophers: List[str]
    voice_style: str  # include user-specified voice style for expression

# NPC 생성 요청 모델 및 엔드포인트 추가
class NpcCreateRequest(BaseModel):
    name: str
    role: str
    voice_style: str
    reference_philosophers: List[str]
    communication_style: str
    debate_approach: str
    created_by: str
    created_at: str

# NPC 간 자동 대화 생성을 위한 요청 클래스
class DialogueGenerateRequest(BaseModel):
    participants: List[str]  # NPC ID 목록
    topic: str
    rounds: Optional[int] = 3  # 대화 라운드 수
    context: Optional[str] = ""  # 추가 컨텍스트

# 자동 대화 요청 모델
class AutoConversationRequest(BaseModel):
    room_id: str
    npcs: List[str]
    topic: Optional[str] = ""
    delay_range: Optional[List[int]] = [15, 25]

# 자동 대화 응답 모델
class AutoConversationResponse(BaseModel):
    status: str
    room_id: str
    message: Optional[str] = None

# 자동 대화 활성화 상태 추적 (서버 메모리에 저장)
active_auto_conversations = {}

# 파일 상단에 추가할 전역 캐시 변수
# NPC 캐시 설정
npc_cache = {}  # ID를 키로 사용하는 캐시 딕셔너리
npc_cache_ttl = 60 * 10  # 캐시 유효 시간: 10분

# FastAPI 앱 초기화
app = FastAPI(title="Sapiens Engine API")

# 환경 설정 출력
nextjs_api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
logger.info(f"===== 시스템 환경 설정 =====")
logger.info(f"NEXTJS_API_URL: {nextjs_api_url}")
logger.info(f"OPENAI_API_KEY: {'설정됨' if os.environ.get('OPENAI_API_KEY') else '설정되지 않음'}")
logger.info(f"DEBUG 모드: {logging.getLogger().level == logging.DEBUG}")
logger.info(f"==================")

# CORS 설정 (AgoraMind 웹 앱에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 오리진으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 경로 디버깅
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"Files in current directory: {os.listdir('.')}")

# /portraits 경로로 초상화 정적 파일 서비스 - 절대 경로 사용
PORTRAITS_DIR = os.path.join(os.getcwd(), "portraits")
logger.info(f"Portrait directory path: {PORTRAITS_DIR}")
if os.path.isdir(PORTRAITS_DIR):
    app.mount("/portraits", StaticFiles(directory=PORTRAITS_DIR), name="portraits")
    logger.info(f"Mounted portraits from {PORTRAITS_DIR} at /portraits")
else:
    logger.error(f"!!! Portraits directory not found: {PORTRAITS_DIR}")
    # 오류 발생 후 서버 종료
    logger.error("Portrait directory not found - cannot serve images")

# LLM 매니저 초기화
config_loader = ConfigLoader()
llm_manager = LLMManager(config_loader)

# 철학자 설명 사전 (NPC 클래스 대신 직접 정의)
philosopher_descriptions = {
    "socrates": "Socrates was an Ancient Greek philosopher known for the Socratic method of questioning, seeking wisdom through dialogue, and the phrase 'I know that I know nothing'. His style is to ask probing questions, challenge assumptions, and use irony. Key concepts include: Socratic method, Examined life, Intellectual humility, Ethical inquiry, Dialectic.",
    "plato": "Plato was an Ancient Greek philosopher, student of Socrates, and founder of the Academy. Known for his theory of Forms, belief in objective truths, and political philosophy. His style is dialectical, making references to eternal ideals and using allegories to illustrate points. Key concepts include: Theory of Forms, The Good, The Republic, The soul, Philosopher-kings.",
    "aristotle": "Aristotle was an Ancient Greek philosopher, student of Plato, and tutor to Alexander the Great. Known for empiricism, virtue ethics, and systematic classification of knowledge. His style is methodical, analytical, and balanced, focusing on practical wisdom and the middle path. Key concepts include: Golden mean, Four causes, Virtue ethics, Eudaimonia, Practical wisdom.",
    "kant": "Kant was an 18th century German philosopher known for his work on ethics, metaphysics, epistemology, and aesthetics. His style is formal, structured, and precise, using technical terminology and emphasizing universal moral principles. Key concepts include: Categorical imperative, Duty, Phenomena vs. noumena, Synthetic a priori, Transcendental idealism.",
    "nietzsche": "Nietzsche was a 19th century German philosopher known for his critique of morality, religion, and contemporary culture. His style is bold, provocative, and poetic, using aphorisms and metaphors to challenge conventional wisdom. Key concepts include: Will to power, Eternal recurrence, Übermensch, Master-slave morality, Perspectivism.",
    "sartre": "Sartre was a 20th century French existentialist philosopher and writer who emphasized freedom, responsibility, and authenticity in human existence. His style is direct, challenging, and focused on concrete human situations. Key concepts include: Existence precedes essence, Radical freedom, Bad faith, Being-for-itself, Authenticity.",
    "camus": "Camus was a 20th century French philosopher associated with absurdism who explored how to find meaning in an indifferent universe. His style is philosophical yet accessible, using literary references and everyday examples. Key concepts include: The Absurd, Revolt, Sisyphus, Philosophical suicide, Authentic living.",
    "simone de beauvoir": "Simone de Beauvoir was a 20th century French philosopher and feminist theorist who explored ethics, politics, and the social construction of gender. Her style connects abstract concepts to lived experiences, especially regarding gender and social relationships. Key concepts include: Situated freedom, The Other, Woman as Other, Ethics of ambiguity, Reciprocal recognition.",
    "marx": "Marx was a 19th century German philosopher, economist, and political theorist who developed historical materialism and critiqued capitalism. His style is analytical and critical, focusing on material conditions and class relations. Key concepts include: Historical materialism, Class struggle, Alienation, Commodity fetishism, Dialectical materialism.",
    "rousseau": "Rousseau was an 18th century Genevan philosopher of the Enlightenment known for his work on political philosophy, education, and human nature. His style combines passionate rhetoric with systematic analysis, appealing to natural human qualities. Key concepts include: Natural state, General will, Social contract, Noble savage, Authentic self."
}

# OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.auto_conversation_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        logger.info(f"WebSocket connection established for room {room_id}")
    
    async def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            try:
                self.active_connections[room_id].remove(websocket)
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
                logger.info(f"WebSocket connection closed for room {room_id}")
            except ValueError:
                logger.warning(f"WebSocket not found in connections for room {room_id}")
    
    async def broadcast(self, message: dict, room_id: str):
        if room_id in self.active_connections:
            disconnected_ws = []
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except RuntimeError as e:
                    logger.error(f"Error broadcasting to client: {str(e)}")
                    disconnected_ws.append(connection)
            
            # 연결 종료된 웹소켓 정리
            for ws in disconnected_ws:
                await self.disconnect(ws, room_id)
    
    def start_auto_conversation(self, room_id: str, task: asyncio.Task):
        self.auto_conversation_tasks[room_id] = task
        logger.info(f"Started auto conversation for room {room_id}")
    
    def stop_auto_conversation(self, room_id: str):
        if room_id in self.auto_conversation_tasks:
            if not self.auto_conversation_tasks[room_id].done():
                self.auto_conversation_tasks[room_id].cancel()
            del self.auto_conversation_tasks[room_id]
            logger.info(f"Stopped auto conversation for room {room_id}")
            return True
        return False

# ConnectionManager 인스턴스 생성
manager = ConnectionManager()

# 채팅 메시지를 Next.js API를 통해 저장하는 함수
async def save_message_to_db(room_id: str, message: dict):
    try:
        # Next.js API 호출하여 메시지 저장
        async with aiohttp.ClientSession() as session:
            # API 엔드포인트 URL (실제 URL로 변경 필요)
            api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
            url = f"{api_url}/api/rooms"
            
            # 메시지 데이터 준비
            payload = {
                "id": room_id,
                "message": message
            }
            
            # API 호출
            async with session.put(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Message saved to database for room {room_id}: {message['id']}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to save message: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Error saving message to database: {str(e)}")
        return False

# 채팅방 메시지 가져오기
async def get_room_messages(room_id: str, limit: int = 20):
    try:
        # Next.js API 호출하여 메시지 가져오기
        async with aiohttp.ClientSession() as session:
            # API 엔드포인트 URL (실제 URL로 변경 필요)
            api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
            url = f"{api_url}/api/rooms?id={room_id}"
            
            # API 호출
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    messages = data.get("messages", [])
                    
                    # 제한된 수의 최신 메시지만 반환
                    if len(messages) > limit:
                        messages = messages[-limit:]
                    
                    logger.info(f"Retrieved {len(messages)} messages for room {room_id}")
                    return messages
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get messages: {error_text}")
                    return []
    except Exception as e:
        logger.error(f"Error retrieving messages: {str(e)}")
        return []

# 채팅방 정보 가져오기
async def get_room_data(room_id: str):
    try:
        # Next.js API 호출하여 채팅방 정보 가져오기
        async with aiohttp.ClientSession() as session:
            api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
            url = f"{api_url}/api/rooms?id={room_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Retrieved room data for {room_id}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get room data: {error_text}")
                    return {}
    except Exception as e:
        logger.error(f"Error retrieving room data: {str(e)}")
        return {}

# 자동 대화 관리 API 엔드포인트
@app.post("/api/auto-conversation", response_model=AutoConversationResponse)
async def start_auto_conversation(request: AutoConversationRequest, background_tasks: BackgroundTasks):
    """자동 대화 생성 시작"""
    room_id = request.room_id
    
    # 이미 자동 대화가 활성화된 채팅방인지 확인
    if room_id in active_auto_conversations:
        # 이전 태스크 중지
        active_auto_conversations[room_id]["active"] = False
        logger.info(f"Stopping existing auto conversation for room {room_id}")
        # 충분한 시간을 주어 태스크가 종료되도록 함
        await asyncio.sleep(1)
    
    # 새 자동 대화 상태 추적 설정
    active_auto_conversations[room_id] = {
        "active": True,
        "npcs": request.npcs,
        "topic": request.topic,
        "delay_range": request.delay_range,
        "last_message_time": time.time()
    }
    
    # 백그라운드 태스크로 자동 대화 루프 시작
    background_tasks.add_task(
        auto_conversation_loop,
        room_id,
        request.npcs,
        request.topic,
        request.delay_range
    )
    
    logger.info(f"Started auto conversation for room {room_id} with {len(request.npcs)} NPCs")
    return {"status": "started", "room_id": room_id}

@app.delete("/api/auto-conversation", response_model=AutoConversationResponse)
async def stop_auto_conversation(room_id: str):
    """자동 대화 생성 중지 - Query parameter로 room_id를 받음"""
    logger.info(f"Stopping auto conversation for room {room_id}")
    
    # active_auto_conversations 상태 디버깅
    logger.debug(f"현재 활성 대화 상태: {active_auto_conversations}")
    
    if room_id in active_auto_conversations:
        logger.info(f"해당 방의 자동 대화 정보: {active_auto_conversations[room_id]}")
        # active 플래그를 False로 설정
        active_auto_conversations[room_id]["active"] = False
        
        # active 플래그 설정 직후 상태 확인
        logger.info(f"active=False 설정 후 상태: {active_auto_conversations[room_id]}")
        
        # 바로 삭제하지 않고 active 플래그만 끔
        # 이렇게 하면 백그라운드 태스크가 자연스럽게 종료됨
        logger.info(f"Stopped auto conversation for room {room_id}")
        return {"status": "stopped", "room_id": room_id}
    else:
        logger.warning(f"No active auto conversation found for room {room_id}")
        return {"status": "not_found", "room_id": room_id, "message": "No active auto conversation found"}

# 자동 대화 생성 루프 함수
async def auto_conversation_loop(room_id: str, npcs: List[str], topic: str, delay_range: List[int]):
    """백그라운드에서 실행되는 자동 대화 생성 루프"""
    try:
        logger.debug(f"====== 자동 대화 루프 시작 - 방 ID: {room_id} ======")
        logger.debug(f"NPC 목록: {npcs}")
        logger.debug(f"주제: {topic}")
        logger.debug(f"지연 범위: {delay_range}")
        logger.debug(f"현재 활성 대화: {active_auto_conversations}")
        
        min_delay, max_delay = delay_range
        prev_npc = None
        message_count = 0
        max_messages = 50  # 안전장치: 최대 메시지 수 제한
        
        # 이전 대화 메시지를 보관할 대화 기록
        dialogue_history = ""
        
        # 루프 실행 - active 플래그가 켜져 있는 동안 계속 실행
        while active_auto_conversations.get(room_id, {}).get("active", False) and message_count < max_messages:
            try:
                logger.debug(f"====== 자동 대화 루프 사이클 {message_count+1} ======")
                # 현재 NPC 목록 가져오기 (동적 업데이트 가능)
                current_npcs = active_auto_conversations.get(room_id, {}).get("npcs", npcs)
                current_topic = active_auto_conversations.get(room_id, {}).get("topic", topic)
                
                logger.debug(f"현재 active_auto_conversations 상태: {active_auto_conversations}")
                
                if len(current_npcs) < 2:
                    logger.warning(f"Not enough NPCs for auto conversation in room {room_id}")
                    break
                
                # 먼저 채팅방의 최근 메시지를 가져옴 (최대 10개)
                if message_count == 0 or message_count % 5 == 0:  # 처음과 5회 주기로 메시지 갱신
                    try:
                        logger.debug(f"채팅방 {room_id}의 최근 메시지 가져오기")
                        recent_messages = await get_room_messages(room_id, limit=10)
                        
                        # 메시지를 대화 기록 형식으로 변환
                        if recent_messages:
                            dialogue_history = ""
                            for msg in recent_messages:
                                sender = msg.get('senderName', msg.get('sender', 'Unknown'))
                                text = msg.get('text', '')
                                if text:
                                    dialogue_history += f"{sender}: {text}\n\n"
                            
                            logger.debug(f"대화 기록 업데이트됨: {len(recent_messages)}개 메시지")
                            logger.debug(f"대화 기록 샘플: {dialogue_history[:200]}...")
                        else:
                            logger.debug(f"채팅방 {room_id}에서 가져온 메시지 없음")
                    except Exception as e:
                        logger.error(f"메시지 가져오기 오류: {str(e)}")
                
                # 이전 NPC와 다른 NPC 선택
                available_npcs = [npc for npc in current_npcs if npc != prev_npc]
                if not available_npcs:
                    available_npcs = current_npcs
                
                # 무작위로 다음 NPC 선택
                responding_npc_id = random.choice(available_npcs)
                prev_npc = responding_npc_id
                
                logger.debug(f"선택된 NPC ID: {responding_npc_id}")
                
                # NPC 정보 가져오기
                logger.info(f"Generating response from NPC: {responding_npc_id}")
                
                try:
                    # 여기서 NPC 정보를 가져올 때 디버깅 로그 추가
                    logger.info(f"📣 Getting details for NPC ID: {responding_npc_id}")
                    npc_info = await get_npc_details(responding_npc_id)
                    logger.info(f"📣 NPC 정보 가져오기 완료: {npc_info.get('name', 'Unknown')}")
                    logger.debug(f"📋 가져온 NPC 정보 전체: {npc_info}")
                except Exception as npc_err:
                    logger.error(f"NPC 정보 가져오기 실패: {str(npc_err)}")
                    # 다음 사이클로 넘어감
                    await asyncio.sleep(5)
                    continue
                
                # NPC 설명 구성 - custom NPC의 경우 추가 특성 포함
                npc_description = f"{npc_info['name']}: {npc_info.get('description', 'A philosopher with unique perspectives')}"
                
                # Custom NPC인 경우 추가 특성 포함
                if npc_info.get('is_custom', False):
                    # 추가 특성이 있으면 설명에 추가
                    additional_traits = []
                    
                    if npc_info.get('voice_style'):
                        additional_traits.append(f"Voice style: {npc_info['voice_style']}")
                    
                    if npc_info.get('debate_approach'):
                        additional_traits.append(f"Debate approach: {npc_info['debate_approach']}")
                    
                    if npc_info.get('communication_style'):
                        additional_traits.append(f"Communication style: {npc_info['communication_style']}")
                    
                    # 특성이 있으면 설명에 추가
                    if additional_traits:
                        traits_text = "; ".join(additional_traits)
                        npc_description += f". {traits_text}"
                        logger.info(f"📣 Custom NPC 추가 특성 포함: {traits_text}")
                
                # 메시지 생성 - 대화 기록 반영
                logger.info(f"Generating philosophical response for {npc_info['name']} on topic: {current_topic}")
                logger.debug(f"이전 대화 길이: {len(dialogue_history)} 문자")
                logger.info(f"📣 NPC 설명: {npc_description}")
                try:
                    response_text, _ = llm_manager.generate_philosophical_response(
                        npc_description=npc_description,
                        topic=current_topic,
                        context="",
                        previous_dialogue=dialogue_history  # 이전 메시지 기록 전달
                    )
                    logger.debug(f"LLM에서 생성된 응답: {response_text[:100]}...")
                except Exception as llm_err:
                    logger.error(f"LLM 응답 생성 실패: {str(llm_err)}")
                    # 다음 사이클로 넘어감
                    await asyncio.sleep(5)
                    continue
                
                # 응답 메시지 구성 - 더 많은 NPC 정보 포함
                message_id = f"auto-{uuid4().hex[:8]}"
                message = {
                    "id": message_id,
                    "text": response_text,
                    "sender": responding_npc_id,  # sender를 NPC ID로 설정하여 프론트엔드에서 정보를 찾을 수 있게 함
                    "senderName": npc_info.get('name', responding_npc_id.capitalize()),  # 추가: NPC 이름
                    "senderType": "npc",  # 추가: 발신자 타입
                    "isUser": False,
                    "timestamp": datetime.now().isoformat(),
                    "portrait_url": npc_info.get('portrait_url', None),  # 추가: 프로필 이미지 URL
                    "npc_id": responding_npc_id  # 추가: NPC ID 명시적 포함
                }
                
                logger.info(f"📣 최종 메시지 객체: {message}")
                logger.info(f"Generated message for {message['senderName']} in room {room_id}")
                logger.info(f"Message: {message['text'][:100]}...")
                
                # 대화 기록에 새 메시지 추가
                dialogue_history += f"{message['senderName']}: {message['text']}\n\n"
                
                # Next.js API를 통해 메시지 저장 및 브로드캐스트
                nextjs_api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
                logger.info(f"Sending message to Next.js API at {nextjs_api_url}/api/rooms")
                
                try:
                    # 메시지 저장 요청
                    async with aiohttp.ClientSession() as session:
                        # 로그에 URL과 payload 내용을 자세히 출력
                        request_payload = {
                            "message": message
                        }
                        # URL 쿼리 파라미터로 room_id 전달
                        request_url = f"{nextjs_api_url}/api/rooms?id={room_id}"
                        logger.info(f"Sending to Next.js API - URL: {request_url}")
                        logger.debug(f"전체 Payload: {request_payload}")
                        
                        api_response = await session.put(
                            request_url,
                            json=request_payload,
                            headers={
                                "Content-Type": "application/json"
                            }
                        )
                        
                        # 응답 확인
                        status_code = api_response.status
                        logger.info(f"Response status code: {status_code}")
                        
                        response_text = await api_response.text()
                        logger.debug(f"Next.js API 응답 전체: {response_text}")
                        
                        if status_code == 200:
                            try:
                                response_data = await api_response.json()
                                success = response_data.get('success', False)
                                logger.info(f"Message successfully saved to DB: {success}")
                                
                                # 성공 여부를 명확하게 출력
                                if success:
                                    logger.info(f"✅ 메시지 저장 성공 - ID: {message['id']}, 발신자: {message['senderName']}")
                                else:
                                    logger.warning(f"⚠️ 메시지 저장 실패 - ID: {message['id']}, 발신자: {message['senderName']}")
                            except Exception as json_err:
                                logger.error(f"응답 JSON 파싱 오류: {str(json_err)}")
                                success = False
                            
                            # 성공 응답일 경우 WebSocket 연결을 위한 추가 요청 (WebSocket 이벤트 발생을 위해)
                            try:
                                # 메시지가 저장되었으니 소켓 서버에 알림
                                socket_data = {
                                    "action": "broadcast",
                                    "room": room_id,
                                    "event": "new-message",
                                    "data": {
                                        "roomId": room_id,
                                        "message": message
                                    }
                                }
                                logger.debug(f"소켓 API 요청 페이로드: {socket_data}")
                                
                                socket_notify_response = await session.post(
                                    f"{nextjs_api_url}/api/socket",
                                    json=socket_data,
                                    headers={
                                        "Content-Type": "application/json"
                                    }
                                )
                                socket_status = socket_notify_response.status
                                socket_text = await socket_notify_response.text()
                                logger.info(f"Socket notification status: {socket_status}")
                                
                                try:
                                    socket_data = json.loads(socket_text)
                                    socket_success = socket_data.get('success', False)
                                    logger.info(f"Socket broadcast success: {socket_success}")
                                    
                                    if socket_success:
                                        logger.info(f"✅ 실시간 브로드캐스트 성공 - 메시지 ID: {message['id']}")
                                    else:
                                        logger.warning(f"⚠️ 실시간 브로드캐스트 실패 - 메시지 ID: {message['id']}")
                                except:
                                    logger.debug(f"Socket 응답 전체: {socket_text}")
                            except Exception as socket_err:
                                logger.error(f"Error notifying socket server: {str(socket_err)}", exc_info=True)
                        else:
                            error_text = await api_response.text()
                            logger.error(f"Failed to save message to DB. Status: {status_code}, Error: {error_text}")
                except Exception as e:
                    logger.error(f"Error sending message to Next.js API: {str(e)}", exc_info=True)
                
                # 메시지 카운트 증가
                message_count += 1
                
                # 다음 메시지 대기 시간 (기본값: 15-25초 랜덤)
                wait_time = random.randint(min_delay, max_delay)
                logger.info(f"Waiting {wait_time} seconds before next message")
                
                # 마지막 메시지 시간 업데이트
                if room_id in active_auto_conversations:
                    active_auto_conversations[room_id]["last_message_time"] = time.time()
                
                # 대기 - 사이에 active 상태가 변경되면 즉시 종료
                for i in range(wait_time):
                    if not active_auto_conversations.get(room_id, {}).get("active", False):
                        logger.debug(f"대기 중 active 상태 변경으로 루프 종료")
                        break
                    if i % 5 == 0:  # 5초마다 로그 출력
                        logger.debug(f"대기 중... {i}/{wait_time}초")
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in auto conversation cycle: {str(e)}", exc_info=True)
                # 에러 발생 시 5초 대기 후 재시도
                await asyncio.sleep(5)
        
        # 루프 종료 후 정리
        if room_id in active_auto_conversations:
            logger.info(f"Auto conversation loop completed for room {room_id} after {message_count} messages")
            # 루프가 완료되면 상태에서 제거
            del active_auto_conversations[room_id]
            
    except Exception as e:
        logger.exception(f"Unexpected error in auto conversation loop: {str(e)}")
        # 오류 발생 시 상태에서 제거
        if room_id in active_auto_conversations:
            del active_auto_conversations[room_id]

# WebSocket 엔드포인트
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received WebSocket message: {data}")
            
            if "command" in data:
                if data["command"] == "start_auto":
                    # 자동 대화 시작
                    npcs = data.get("npcs", [])
                    topic = data.get("topic", "")
                    
                    if len(npcs) < 2:
                        await websocket.send_json({
                            "type": "error",
                            "message": "At least 2 NPCs are required for auto conversation"
                        })
                    else:
                        # 이미 실행 중이면 중지
                        manager.stop_auto_conversation(room_id)
                        
                        # 새 태스크 시작
                        task = asyncio.create_task(
                            auto_conversation_loop(room_id, npcs, topic)
                        )
                        manager.start_auto_conversation(room_id, task)
                        
                elif data["command"] == "stop_auto":
                    # 자동 대화 중지
                    if manager.stop_auto_conversation(room_id):
                        await websocket.send_json({
                            "type": "auto_conversation_status",
                            "status": "stopped",
                            "room_id": room_id
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No active auto conversation to stop"
                        })
                        
            elif "message" in data:
                # 클라이언트에서 보낸 일반 메시지 처리 (필요시 구현)
                pass
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, room_id)
    except Exception as e:
        logger.exception(f"Error in WebSocket connection: {str(e)}")
        try:
            await manager.disconnect(websocket, room_id)
        except:
            pass

# 다음 NPC 선택 도우미 함수
def select_next_npc(npcs: List[str], last_speaker: str = None) -> str:
    """
    대화에서 응답할 다음 NPC 선택
    
    Args:
        npcs: 가능한 NPC 목록
        last_speaker: 이전 메시지 발신자 (있으면)
    
    Returns:
        선택된 NPC ID
    """
    if not npcs:
        raise ValueError("No NPCs available")
    
    # 이전 발신자가 없으면 랜덤 선택
    if not last_speaker:
        return random.choice(npcs)
    
    # 이전 발신자가 아닌 NPC 중에서 선택
    available_npcs = [npc for npc in npcs if last_speaker not in npc]
    if available_npcs:
        return random.choice(available_npcs)
    
    # 마지막 수단: 첫 번째 NPC 반환
    return npcs[0]

@app.get("/")
def read_root():
    return {"message": "Welcome to Sapiens Engine API"}

@app.get("/api/philosophers")
async def get_philosophers():
    """모든 사용 가능한 철학자 목록 반환"""
    philosophers_list = []
    
    # YAML 파일에서 로드한 철학자 정보 사용
    if philosophers_data:
        for key, data in philosophers_data.items():
            # build item with portrait_url
            portrait_url = None
            if key in PORTRAITS_MAP:
                portrait_url = f"http://localhost:8000/portraits/{PORTRAITS_MAP[key]}"
            item = {
                "id": key,
                "name": data.get("name", "Unknown"),
                "period": data.get("period", ""),
                "nationality": data.get("nationality", "")
            }
            if portrait_url:
                item["portrait_url"] = portrait_url
            philosophers_list.append(item)
    else:
        # YAML 파일을 로드할 수 없는 경우 기본 정보 사용
        for key, description in philosopher_descriptions.items():
            name = description.split(' was ')[0]
            philosophers_list.append({
                "id": key,
                "name": name
            })
    
    return {
        "philosophers": philosophers_list
    }

@app.get("/api/philosophers/{philosopher_id}")
async def get_philosopher_details(philosopher_id: str):
    """특정 철학자의 세부 정보 반환"""
    philosopher_id = philosopher_id.lower()
    
    # YAML 파일에서 철학자 정보 찾기
    if philosopher_id in philosophers_data:
        data = philosophers_data[philosopher_id]
        # portrait_url 추가
        portrait_url = None
        if philosopher_id in PORTRAITS_MAP:
            portrait_url = f"http://localhost:8000/portraits/{PORTRAITS_MAP[philosopher_id]}"
        response = { "id": philosopher_id, **data }
        if portrait_url:
            response["portrait_url"] = portrait_url
        return response
        
    # 기본 정보에서 찾기
    if philosopher_id in philosopher_descriptions:
        description = philosopher_descriptions[philosopher_id]
        name = description.split(' was ')[0]
        response = {
            "id": philosopher_id,
            "name": name,
            "description": description
        }
        if philosopher_id in PORTRAITS_MAP:
            response["portrait_url"] = f"http://localhost:8000/portraits/{PORTRAITS_MAP[philosopher_id]}"
        return response
        
    # 철학자를 찾을 수 없는 경우
    raise HTTPException(status_code=404, detail=f"Philosopher '{philosopher_id}' not found")

@app.post("/api/chat/initial", response_model=ChatResponse)
async def create_initial_chat(request: InitialChatRequest):
    try:
        logger.info(f"Received initial chat request: {request}")
        
        # 요청한 철학자 검색
        philosopher = request.philosopher.lower()
        
        # 철학자 설명 가져오기
        if philosopher in philosopher_descriptions:
            philosopher_description = philosopher_descriptions[philosopher]
        else:
            # 기본 설명 생성
            logger.warning(f"Philosopher {philosopher} not found in configuration")
            philosopher_description = f"{request.philosopher} is a philosopher interested in various philosophical topics."
        
        # 사용자 메시지 구성
        user_message = ""
        if request.user_message:
            user_message = f"User: {request.user_message}\n"
        
        # 응답 생성
        response_text, metadata = llm_manager.generate_philosophical_response(
            npc_description=philosopher_description,
            topic=request.topic,
            context=request.context,
            previous_dialogue=user_message
        )
        
        return ChatResponse(
            response=response_text,
            philosopher=request.philosopher,
            metadata=metadata
        )
    
    except Exception as e:
        logger.exception(f"Error generating initial chat response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portraits/generate")
async def generate_portrait(request: PortraitRequest):
    """Generate NPC portrait via OpenAI and save to static portraits folder"""
    try:
        # 스타일 일관성을 위한 참조 이미지 URL 생성
        style_image_urls = []
        for ph in request.reference_philosophers:
            pid = ph.lower()
            if pid in PORTRAITS_MAP:
                style_image_urls.append(f"http://localhost:8000/portraits/{PORTRAITS_MAP[pid]}")
        style_refs_text = ""
        if style_image_urls:
            style_refs_text = " Use the following reference images for style: " + ", ".join(style_image_urls) + "."

        # 빌드할 프롬프트: 고정된 스타일 & 철학자 얼굴 완전 병합, 음성 스타일(표정) 반영
        ref_urls = ", ".join(style_image_urls)
        const_style = "A sepia-toned charcoal portrait (chest-up), fine pencil texture on vintage paper background, soft diffuse lighting, rich warm tones."
        philosophers = ", ".join(request.reference_philosophers)
        
        # 더 명확한 블렌딩 지시사항
        blend_text = f"""Create ONE SINGLE FICTIONAL FACE that is a perfect 50/50 hybrid fusion between 
        {philosophers}. Do not show multiple separate individuals or different faces. 
        Create ONE new imaginary person with merged facial features from both philosophers."""
        
        # 표정 지시사항
        render_text = f"This merged character should have an expression/demeanor that shows: {request.voice_style}"
        
        prompt = (
            f"{const_style} {blend_text} {render_text} "
            f"The portrait should be of ONE person named {request.npc_name}, not multiple people. "
            f"Generate a square (1024x1024 pixels) high-quality PNG portrait. "
            "Provide a PNG without any text or overlays."
        )
        # OpenAI 이미지 생성 요청 with explicit model (using new openai-python v1.0 interface)
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
        # 이미지 다운로드
        img_bytes = requests.get(image_url).content
        # 파일명 생성
        filename = f"{slugify(request.npc_name)}_{int(time.time())}.png"
        filepath = os.path.join(PORTRAITS_DIR, filename)
        
        # 이미지 다운로드 및 저장
        with open(filepath, 'wb') as img_file:
            img_file.write(img_bytes)
        
        # 파일 저장 검증
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Image saved successfully: {filepath} ({file_size} bytes)")
        else:
            logger.error(f"Failed to save image: {filepath}")
            raise HTTPException(status_code=500, detail="Failed to save generated image")
        
        # 반환할 URL (절대 경로로 변경)
        return { 'url': f"http://localhost:8000/portraits/{filename}" }
    except Exception as e:
        logger.exception(f"Error generating portrait: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/npc/create")
async def create_npc(request: NpcCreateRequest):
    """Stub NPC creation endpoint: returns generated ID to Next.js"""
    new_id = str(uuid4())
    return { "id": new_id }

@app.post("/api/chat/generate")
async def generate_chat_response(request: ChatGenerateRequest):
    """대화 맥락에 따른 철학자 응답 생성"""
    try:
        logger.info(f"Received chat generate request: topic={request.topic}, npcs={request.npcs}")
        logger.info(f"Using LLM provider: {request.llm_provider}, model: {request.llm_model}")
        
        # API 키가 제공된 경우 임시로 설정
        original_api_key = None
        if request.api_key:
            logger.info("Using API key provided by client")
            original_api_key = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = request.api_key
            openai.api_key = request.api_key
        
        try:
            # 참여하는 NPC들 중에서 응답할 NPC 선택
            # 현재는 간단하게 첫 번째 또는 대화 내용에 언급된 NPC를 선택
            # 더 복잡한 전략을 구현할 수 있음
            responding_philosopher = select_responding_philosopher(request.npcs, request.previous_dialogue)
            logger.info(f"Selected responding philosopher: {responding_philosopher}")
            
            # NPC 정보 가져오기
            npc_info = await get_npc_details(responding_philosopher)
            logger.info(f"Retrieved NPC info: {npc_info.get('name', 'Unknown')}")
            
            # NPC 설명 구성 (제공된 설명 또는 기본 설명)
            npc_description = f"{npc_info['name']}: {npc_info.get('description', 'A philosopher with unique perspectives')}"
            
            # Custom NPC인 경우 추가 특성 포함
            if npc_info.get('is_custom', False):
                # 추가 특성이 있으면 설명에 추가
                additional_traits = []
                
                if npc_info.get('voice_style'):
                    additional_traits.append(f"Voice style: {npc_info['voice_style']}")
                
                if npc_info.get('debate_approach'):
                    additional_traits.append(f"Debate approach: {npc_info['debate_approach']}")
                
                if npc_info.get('communication_style'):
                    additional_traits.append(f"Communication style: {npc_info['communication_style']}")
                
                # 특성이 있으면 설명에 추가
                if additional_traits:
                    traits_text = "; ".join(additional_traits)
                    npc_description += f". {traits_text}"
                    logger.info(f"📣 Custom NPC 추가 특성 포함: {traits_text}")
            
            logger.info(f"Using NPC description: {npc_description[:150]}...")
            
            # llm_manager를 사용하여 응답 생성
            response_text, metadata = llm_manager.generate_philosophical_response(
                npc_description=npc_description,
                topic=request.topic,
                context=request.context,
                previous_dialogue=request.previous_dialogue,
                llm_provider=request.llm_provider,
                llm_model=request.llm_model
            )
            
            return {
                "response": response_text,
                "philosopher": responding_philosopher,
                "metadata": metadata
            }
        finally:
            # 원래 API 키 복원
            if original_api_key is not None:
                os.environ["OPENAI_API_KEY"] = original_api_key
                openai.api_key = original_api_key
    
    except Exception as e:
        logger.exception(f"Error generating chat response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def select_responding_philosopher(npcs: List[str], previous_dialogue: str) -> str:
    """대화 컨텍스트에 기반하여 응답할 철학자를 선택"""
    if not npcs:
        raise ValueError("No philosophers available to respond")
    
    # 간단한 응답 철학자 선택 로직:
    # 1. 이전 대화에서 특정 철학자가 언급되었는지 확인
    # 2. 언급된 철학자가 참여 철학자 목록에 있으면 해당 철학자 선택
    # 3. 없으면 첫 번째 철학자 선택
    
    # 대화에서 마지막 사용자 메시지 찾기
    user_messages = [line for line in previous_dialogue.split('\n') if line.startswith('User:')]
    if user_messages:
        last_user_message = user_messages[-1].replace('User:', '').strip().lower()
        
        # 사용자 메시지에 언급된 철학자 찾기
        for philosopher in npcs:
            if philosopher.lower() in last_user_message:
                logger.info(f"User mentioned philosopher: {philosopher}")
                return philosopher
    
    # 언급된 철학자가 없으면 첫 번째 철학자 선택
    return npcs[0]

@app.get("/api/npc/get")
async def get_npc_details(id: str):
    try:
        # 빈 ID 검증
        if not id:
            logger.warning("No NPC ID provided")
            return {"error": "NPC ID is required"}
            
        logger.info(f"Fetching NPC details for ID: {id}")
        
        # 캐시에서 확인
        cache_key = f"npc:{id}"
        current_time = time.time()
        if cache_key in npc_cache and (current_time - npc_cache[cache_key]['timestamp'] < npc_cache_ttl):
            logger.info(f"🔍 Cache hit: NPC {id} found in cache")
            return npc_cache[cache_key]['data']
        
        # MongoDB ObjectID 형식 감지
        is_mongo_id = len(id) == 24 and all(c in '0123456789abcdefABCDEF' for c in id)
        is_uuid = len(id) > 30 and id.count('-') >= 4
        
        # Custom NPC (MongoDB ID 또는 UUID)인 경우 Next.js API에서 정보 가져오기
        if is_mongo_id or is_uuid:
            logger.info(f"ID {id} appears to be a custom NPC (MongoDB or UUID)")
            
            try:
                # Next.js API에서 NPC 정보 가져오기 - 일관된 엔드포인트 사용
                nextjs_api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
                custom_npc_url = f"{nextjs_api_url}/api/npc/get?id={id}"
                logger.info(f"🔍 Fetching custom NPC info from Next.js API: {custom_npc_url}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(custom_npc_url) as response:
                        status_code = response.status
                        logger.info(f"📊 API Response status: {status_code}")
                        
                        if response.status == 200:
                            npc_data = await response.json()
                            logger.info(f"✅ Retrieved custom NPC data: {npc_data.get('name', 'Unknown')}")
                            logger.debug(f"📋 Complete NPC data: {npc_data}")
                            
                            # 필요한 필드 확인 및 기본값 설정
                            portrait_url = npc_data.get('portrait_url')
                            logger.info(f"🖼️ Portrait URL: {portrait_url}")
                            
                            # 응답 구성
                            response_data = {
                                "id": id,
                                "name": npc_data.get('name', f"Philosopher {id[:6]}"),
                                "description": npc_data.get('description', "A philosopher with unique perspectives"),
                                "key_concepts": npc_data.get('key_concepts', []),
                                "portrait_url": portrait_url,
                                "is_custom": True,
                                # 추가 정보 (프롬프트에 필요한 특성)
                                "voice_style": npc_data.get('voice_style', ""),
                                "debate_approach": npc_data.get('debate_approach', ""),
                                "communication_style": npc_data.get('communication_style', "")
                            }
                            
                            # 캐시에 저장
                            npc_cache[cache_key] = {
                                'data': response_data,
                                'timestamp': current_time
                            }
                            
                            logger.info(f"🔄 Returning and caching custom NPC data for {response_data['name']}")
                            return response_data
                        else:
                            # API 오류 시 로깅 후 기본값 사용
                            error_text = await response.text()
                            logger.warning(f"❌ Failed to get custom NPC from API: {error_text}")
                            
                            # 일반적인 404 오류면 다른 엔드포인트도 시도
                            if response.status == 404:
                                logger.info(f"🔍 Trying alternative API endpoint for custom NPC")
                                # 대체 URL - MongoDB ID로 직접 쿼리
                                alt_url = f"{nextjs_api_url}/api/npc/get-by-backend-id?id={id}"
                                logger.info(f"🔍 Trying alternative API endpoint: {alt_url}")
                                
                                async with session.get(alt_url) as alt_response:
                                    if alt_response.status == 200:
                                        npc_data = await alt_response.json()
                                        logger.info(f"✅ Retrieved custom NPC data from alternative endpoint: {npc_data.get('name', 'Unknown')}")
                                        
                                        # 응답 구성
                                        response_data = {
                                            "id": id,
                                            "name": npc_data.get('name', f"Philosopher {id[:6]}"),
                                            "description": npc_data.get('description', "A philosopher with unique perspectives"),
                                            "key_concepts": npc_data.get('key_concepts', []),
                                            "portrait_url": npc_data.get('portrait_url'),
                                            "is_custom": True,
                                            "voice_style": npc_data.get('voice_style', ""),
                                            "debate_approach": npc_data.get('debate_approach', ""),
                                            "communication_style": npc_data.get('communication_style', "")
                                        }
                                        
                                        # 캐시에 저장
                                        npc_cache[cache_key] = {
                                            'data': response_data,
                                            'timestamp': current_time
                                        }
                                        
                                        logger.info(f"🔄 Returning and caching custom NPC data from alternative source: {response_data['name']}")
                                        return response_data
            except Exception as api_err:
                logger.error(f"❌❌ Error fetching custom NPC from API: {str(api_err)}")
            
            # API 호출 실패 시 기본 정보 제공
            # 이름을 기준으로 고유한 이미지를 선택할 수 있게 함
            hash_value = sum(ord(c) for c in id) % 5  # 간단한 해시 함수
            
            philosopher_images = ["Aristotle.png", "Nietzsche.png", "Descartes.png", 
                                 "Confucius.png", "Wittgenstein.png"]
            
            selected_image = philosopher_images[hash_value]
            portrait_url = f"http://localhost:8000/portraits/{selected_image}"
            
            logger.info(f"🔄 Using default portrait for custom NPC: {portrait_url}")
            
            fallback_data = {
                "id": id,
                "name": f"Philosopher {id[:6]}",
                "description": "A philosopher with unique perspectives and ideas",
                "key_concepts": ["Unique", "Custom", "Personal"],
                "portrait_url": portrait_url,
                "is_custom": True
            }
            
            # 폴백 데이터도 캐시에 저장 (짧은 TTL 적용)
            short_ttl = 60 * 5  # 5분
            npc_cache[cache_key] = {
                'data': fallback_data,
                'timestamp': current_time - npc_cache_ttl + short_ttl
            }
            
            logger.info(f"🔄 Returning fallback data for custom NPC: {fallback_data['name']}")
            return fallback_data

        # 기본 철학자인 경우
        philosopher_id = id.lower()
        logger.info(f"Looking up philosopher with ID: {philosopher_id}")
        
        # YAML 파일에서 철학자 정보 찾기
        if philosopher_id in philosophers_data:
            data = philosophers_data[philosopher_id]
            logger.info(f"Found philosopher {philosopher_id} in YAML data")
            
            # portrait_url 추가
            portrait_url = None
            if philosopher_id in PORTRAITS_MAP:
                portrait_url = f"http://localhost:8000/portraits/{PORTRAITS_MAP[philosopher_id]}"
                
            response_data = {
                "id": philosopher_id,
                "name": data.get("name", "Unknown"),
                "description": data.get("description", ""),
                "key_concepts": data.get("key_concepts", []),
                "portrait_url": portrait_url,
                "is_custom": False
            }
            
            # 캐시에 저장
            npc_cache[cache_key] = {
                'data': response_data,
                'timestamp': current_time
            }
            
            logger.info(f"🔄 Returning and caching YAML data for philosopher: {response_data['name']}")
            return response_data
        # 기본 정보에서 찾기
        elif philosopher_id in philosopher_descriptions:
            description = philosopher_descriptions[philosopher_id]
            name = description.split(' was ')[0]
            logger.info(f"Found philosopher {philosopher_id} in hardcoded descriptions")
            
            portrait_url = None
            if philosopher_id in PORTRAITS_MAP:
                portrait_url = f"http://localhost:8000/portraits/{PORTRAITS_MAP[philosopher_id]}"
            
            response_data = {
                "id": philosopher_id,
                "name": name,
                "description": description,
                "portrait_url": portrait_url,
                "is_custom": False
            }
            
            # 캐시에 저장
            npc_cache[cache_key] = {
                'data': response_data,
                'timestamp': current_time
            }
            
            logger.info(f"🔄 Returning and caching hardcoded data for philosopher: {response_data['name']}")
            return response_data
        
        # NPC를 찾을 수 없는 경우
        logger.warning(f"NPC with ID '{id}' not found")
        # 404 대신 기본 정보 제공 (폴백 메커니즘)
        fallback_data = {
            "id": id,
            "name": id.capitalize(),
            "description": "A philosopher with unique perspectives",
            "is_custom": False
        }
        
        # 폴백 데이터는 짧은 유효 시간으로 캐시
        short_ttl = 60 * 5  # 5분
        npc_cache[cache_key] = {
            'data': fallback_data,
            'timestamp': current_time - npc_cache_ttl + short_ttl
        }
        
        logger.info(f"🔄 Returning fallback data for unknown philosopher: {fallback_data['name']}")
        return fallback_data
    except Exception as e:
        logger.exception(f"Error retrieving NPC: {str(e)}")
        # 오류 발생 시에도 기본 정보 제공
        fallback_data = {
            "id": id,
            "name": id.capitalize(),
            "description": "Information temporarily unavailable",
            "is_custom": False
        }
        logger.info(f"🔄 Returning error fallback data: {fallback_data['name']}")
        return fallback_data

# 채팅방 생성 및 초기 메시지 생성을 통합한 엔드포인트
@app.post("/api/rooms")
async def create_chat_room(request: ChatRoomCreationRequest):
    try:
        logger.info(f"Received room creation request: {request.title}")
        logger.info(f"Generate initial message: {request.generateInitialMessage}")
        logger.info(f"NPCs: {request.npcs}")
        logger.info(f"LLM Provider: {request.llmProvider}, Model: {request.llmModel}")
        
        # 1. 채팅방 생성 - 기존 로직 유지
        # 고유 ID 생성
        new_room_id = str(uuid4())
        logger.info(f"Generated new room ID: {new_room_id}")
        
        # 채팅방 객체 생성
        new_room = {
            "id": new_room_id,
            "title": request.title,
            "context": request.context,
            "participants": {
                "users": [request.currentUser] if request.currentUser else [],
                "npcs": request.npcs
            },
            "totalParticipants": len(request.npcs) + (1 if request.currentUser else 0),
            "lastActivity": datetime.now().isoformat(),
            "isPublic": request.isPublic
        }
        
        # 2. 초기 메시지 생성 로직 개선 (통합)
        initial_message = None
        if request.generateInitialMessage and request.npcs and len(request.npcs) > 0:
            logger.info(f"Generating initial message for room {new_room_id}")
            first_npc_id = request.npcs[0]
            logger.info(f"Using first NPC: {first_npc_id}")
            
            try:
                # NPC 정보 가져오기
                npc_info = await get_npc_details(first_npc_id)
                logger.info(f"Retrieved NPC info: {npc_info['name']}")
                
                # 철학자 설명 구성
                npc_description = f"{npc_info['name']}: {npc_info['description']}"
                logger.info(f"Generated NPC description: {npc_description[:100]}...")
                
                # LLM 설정 디버깅
                logger.info(f"OpenAI API key exists: {bool(os.environ.get('OPENAI_API_KEY'))}")
                logger.info(f"Using LLM provider: {request.llmProvider}")
                logger.info(f"Using LLM model: {request.llmModel}")
                
                # 초기 메시지 생성 - 최대 3번 재시도
                initial_message = ""
                max_retries = 3
                retry_count = 0
                
                while not initial_message and retry_count < max_retries:
                    try:
                        # 초기 메시지 생성
                        logger.info(f"[ATTEMPT {retry_count + 1}] Calling generate_philosophical_response with provider={request.llmProvider}, model={request.llmModel}")
                        
                        # 시작 시간 기록
                        start_time = time.time()
                        initial_message_result, metadata = llm_manager.generate_philosophical_response(
                            npc_description=npc_description,
                            topic=request.title,
                            context=request.context or "",
                            llm_provider=request.llmProvider,
                            llm_model=request.llmModel
                        )
                        # 소요 시간 계산
                        elapsed_time = time.time() - start_time
                        logger.info(f"LLM generation took {elapsed_time:.2f} seconds")
                        
                        # 응답 로깅
                        logger.info(f"LLM response (raw):\n{initial_message_result}")
                        logger.info(f"LLM metadata: {metadata}")
                        
                        # Trim the initial message
                        initial_message = initial_message_result.strip() if initial_message_result else ""
                        
                        # 빈 메시지 검증
                        if not initial_message:
                            logger.warning(f"Empty message generated, retrying ({retry_count + 1}/{max_retries})")
                            retry_count += 1
                            # 다음 시도 전 짧은 지연
                            time.sleep(0.5)
                            continue
                        
                        # "Welcome to" 메시지 필터링
                        if initial_message.lower().startswith("welcome to"):
                            logger.warning(f"'Welcome to' message generated, retrying ({retry_count + 1}/{max_retries})")
                            retry_count += 1
                            initial_message = ""
                            continue
                            
                        logger.info(f"Successfully generated message: {initial_message[:100]}...")
                            
                    except Exception as e:
                        logger.error(f"Error in message generation attempt {retry_count + 1}: {str(e)}", exc_info=True)
                        retry_count += 1
                        time.sleep(0.5)
                
                # 유효한 메시지가 생성되었는지 확인
                if initial_message:
                    # 메시지 ID 생성
                    message_id = f"welcome-{int(time.time())}"
                    
                    # 메시지 객체 생성
                    message_obj = {
                        "id": message_id,
                        "text": initial_message,
                        "sender": npc_info['name'],
                        "isUser": False,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # 응답에 초기 메시지 포함
                    new_room["initial_message"] = message_obj
                    logger.info(f"Initial message generated for room {new_room_id} from {npc_info['name']}: {initial_message[:100]}...")
                else:
                    logger.warning(f"Failed to generate valid initial message after {max_retries} attempts")
                    # 대체 메시지 생성 (정적)
                    fallback_questions = [
                        f"I find this topic of \"{request.title}\" quite fascinating. What aspects of it interest you the most?",
                        f"Let us explore \"{request.title}\" together. What questions come to mind when you consider this subject?",
                        f"The question of \"{request.title}\" has intrigued philosophers for centuries. Where shall we begin our inquiry?",
                        f"I've spent much time contemplating \"{request.title}\". What is your perspective on this matter?",
                        f"To understand \"{request.title}\", we must first examine our assumptions. What do you believe to be true about this subject?"
                    ]
                    
                    # 랜덤 질문 선택
                    fallback_message = random.choice(fallback_questions)
                    
                    message_obj = {
                        "id": f"welcome-{int(time.time())}",
                        "text": fallback_message,
                        "sender": npc_info['name'],
                        "isUser": False,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    new_room["initial_message"] = message_obj
                    logger.info(f"Using fallback message for room {new_room_id} from {npc_info['name']}: {fallback_message}")
            except Exception as e:
                logger.exception(f"Error generating initial message: {str(e)}")
                # 초기 메시지 생성 실패 시 기본 메시지 생성
                try:
                    # 응급 상황에서도 메시지를 생성해야 함
                    default_npc_name = request.npcs[0].capitalize() if request.npcs else "Philosopher"
                    fallback_message = f"I find this topic of \"{request.title}\" intriguing. What are your thoughts on it?"
                    
                    message_obj = {
                        "id": f"welcome-{int(time.time())}",
                        "text": fallback_message,
                        "sender": default_npc_name,
                        "isUser": False,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    new_room["initial_message"] = message_obj
                    logger.info(f"Using emergency fallback message for room {new_room_id} from {default_npc_name}")
                    logger.info(f"Room {new_room_id} has initial message from: {request.npcs[0]}")
                except Exception as final_err:
                    logger.critical(f"Unable to create any initial message: {str(final_err)}")
        
        # 초기 메시지 유무 최종 확인
        if "initial_message" in new_room:
            logger.info(f"Room {new_room_id} has initial message from: {new_room['initial_message']['sender']}")
        else:
            logger.warning(f"Room {new_room_id} has NO initial message")
        
        logger.info(f"Returning new room with ID: {new_room_id}")
        return new_room
    except Exception as e:
        logger.exception(f"Error creating chat room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# NPC 간 자동 대화 생성 API
@app.post("/api/dialogue/generate")
async def generate_dialogue(request: DialogueGenerateRequest):
    try:
        logger.info(f"Received dialogue generation request for topic: {request.topic}")
        logger.info(f"Participants: {request.participants}")
        logger.info(f"Rounds: {request.rounds}")
        
        # 참여자 검증 (최소 2명 이상)
        if len(request.participants) < 2:
            logger.warning("At least 2 participants are required for dialogue")
            return {"error": "At least 2 participants are required"}
            
        # NPC 정보 로드
        npc_descriptions = []
        for npc_id in request.participants:
            try:
                npc_info = await get_npc_details(npc_id)
                npc_description = f"{npc_info['name']}: {npc_info['description']}"
                npc_descriptions.append({
                    "id": npc_id,
                    "name": npc_info['name'],
                    "description": npc_description
                })
                logger.info(f"Loaded NPC {npc_info['name']} for dialogue")
            except Exception as e:
                logger.error(f"Error loading NPC {npc_id}: {str(e)}")
                # 에러 발생 시 기본 설명 추가
                npc_descriptions.append({
                    "id": npc_id,
                    "name": npc_id.capitalize(),
                    "description": f"{npc_id.capitalize()}: A philosopher with unique perspectives"
                })
        
        # 대화 기록 초기화
        dialogue_history = ""
        all_exchanges = []
        
        # NPC들 간의 대화 생성
        for round_num in range(request.rounds):
            logger.info(f"Generating dialogue round {round_num + 1}/{request.rounds}")
            
            # 각 라운드마다 2명의 NPC를 선택하여 대화 진행
            idx1 = round_num % len(npc_descriptions)
            idx2 = (round_num + 1) % len(npc_descriptions)
            npc1 = npc_descriptions[idx1]
            npc2 = npc_descriptions[idx2]
            
            logger.info(f"NPC exchange: {npc1['name']} <-> {npc2['name']}")
            
            # LLM에 대화 생성 요청
            start_time = time.time()
            dialogue_result = llm_manager.generate_dialogue_exchange(
                npc1_description=npc1['description'],
                npc2_description=npc2['description'],
                topic=request.topic,
                previous_dialogue=dialogue_history,
                source_materials=None,
                user_contexts=None
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Dialogue exchange generated in {elapsed_time:.2f} seconds")
            
            # 생성된 대화 처리
            exchanges = dialogue_result.get("exchanges", [])
            if exchanges:
                logger.info(f"Generated {len(exchanges)} dialogue exchanges")
                for exchange in exchanges:
                    # 대화 내용 추가
                    all_exchanges.append(exchange)
                    # 대화 이력 업데이트
                    dialogue_history += f"\n{exchange['speaker']}: {exchange['content']}"
            else:
                logger.warning("No dialogue exchanges generated in this round")
            
        # 결과 반환
        logger.info(f"Completed dialogue generation with {len(all_exchanges)} total exchanges")
        return {
            "topic": request.topic,
            "participants": [npc['name'] for npc in npc_descriptions],
            "rounds": request.rounds,
            "exchanges": all_exchanges,
            "raw_dialogue": dialogue_history.strip(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.exception(f"Error in dialogue generation: {str(e)}")
        return {"error": f"Failed to generate dialogue: {str(e)}"}

# 서버 실행 (독립 실행 시)
if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)