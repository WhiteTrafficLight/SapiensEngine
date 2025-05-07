# api_server.py 수정
from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, BackgroundTasks, Body, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional, Any, Union
import asyncio
import os
import json
import time
import logging
import uuid
import random  # 랜덤 선택을 위한 import 추가
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union, Set
import uvicorn
import yaml
from fastapi.staticfiles import StaticFiles
import openai
import requests
from slugify import slugify
import aiohttp
from uuid import uuid4
from types import SimpleNamespace
import re

# Sapiens Engine 임포트
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.config_loader import ConfigLoader

# tiktoken 추가 - 토큰 계산용
try:
    import tiktoken
except ImportError:
    logger.warning("tiktoken 패키지를 찾을 수 없습니다. 근사치 토큰 계산을 사용합니다.")

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
    room_id: str  # 룸 ID 필드 추가
    user_message: str  # 사용자 메시지 필드 추가
    topic: Optional[str] = ""
    context: Optional[str] = ""
    previous_dialogue: Optional[str] = ""  # 하위 호환성을 위해 유지
    llm_provider: Optional[str] = "openai"
    llm_model: Optional[str] = "gpt-4o"
    api_key: Optional[str] = None
    use_rag: Optional[bool] = False  # RAG 사용 여부 플래그 추가

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
            # URL 쿼리 파라미터로 room_id 전달 
            url = f"{api_url}/api/rooms?id={room_id}"
            
            # 디버깅: 저장 전 메시지 구조 출력
            logger.info(f"🧪 MongoDB 저장 전 message 객체 키: {list(message.keys())}")
            logger.info(f"🧪 citations 키 존재: {'citations' in message}")
            
            if 'citations' in message:
                logger.info(f"🧪 citations 타입: {type(message['citations'])}")
                logger.info(f"🧪 citations 내용: {json.dumps(message['citations'])[:500]}...")
            
            # 메시지 데이터 준비
            payload = {
                "message": message
            }
            
            # API 호출 직전 페이로드 확인
            logger.info(f"🧪 API 호출 페이로드: {json.dumps(payload)[:1000]}...")
            
            # API 호출
            async with session.put(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"✅ Message saved to database for room {room_id}: {message['id']}")
                    
                    # 응답 확인
                    try:
                        response_data = await response.json()
                        logger.info(f"🧪 MongoDB 저장 응답: {json.dumps(response_data)}")
                    except:
                        response_text = await response.text()
                        logger.info(f"🧪 MongoDB 저장 응답 텍스트: {response_text[:500]}")
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to save message: Status {response.status}, Error: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"❌ Error saving message to database: {str(e)}")
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

@app.get("/api/auto-conversation/status")
async def check_auto_conversation_status(room_id: str):
    """자동 대화 상태 확인 - Query parameter로 room_id를 받음"""
    logger.info(f"Checking auto conversation status for room {room_id}")
    
    if room_id in active_auto_conversations:
        is_active = active_auto_conversations[room_id].get("active", False)
        logger.info(f"Room {room_id} auto conversation status: {'active' if is_active else 'inactive'}")
        return {
            "room_id": room_id,
            "active": is_active,
            "npcs": active_auto_conversations[room_id].get("npcs", []),
            "topic": active_auto_conversations[room_id].get("topic", "")
        }
    else:
        logger.info(f"Room {room_id} has no auto conversation record")
        return {"room_id": room_id, "active": False}

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
        
        # 누가 언급되었는지 추적하는 변수
        mentioned_npc = None
        # 사용자 질문을 추적하는 변수
        last_user_question = None
        # 사용자 질문에 대답했는지 추적
        user_question_answered = True
        
        # 룸 데이터 가져오기 - 사용자 정보 포함
        room_data = await get_room_data(room_id)
        
        # 사용자 이름 매핑 초기화 (sender ID -> username)
        user_name_mapping = {}
        
        # 방에 있는 사용자 정보 추출
        if room_data and 'participants' in room_data and 'users' in room_data['participants']:
            users = room_data['participants'].get('users', [])
            logger.info(f"룸 {room_id}의 사용자: {users}")
            
            # 사용자 ID -> 이름 매핑 구성
            for user in users:
                if isinstance(user, dict) and 'id' in user and 'username' in user:
                    user_name_mapping[user['id']] = user['username']
                elif isinstance(user, str):
                    # ID만 있는 경우 임시 이름 사용
                    user_name_mapping[user] = f"User_{user[:4]}"
        
        logger.info(f"사용자 이름 매핑: {user_name_mapping}")
        
        # 컨텍스트에 사용자 정보 추가
        user_context = ""
        if user_name_mapping:
            user_context = "현재 대화에 참여 중인 사용자:\n"
            for user_id, username in user_name_mapping.items():
                user_context += f"- {username}\n"
        
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
                
                # 먼저 채팅방의 최근 메시지를 가져옴 (최대 20개)
                # 매 메시지마다 대화 컨텍스트를 업데이트하여 연속성 보장
                try:
                    logger.debug(f"채팅방 {room_id}의 최근 메시지 가져오기")
                    recent_messages = await get_room_messages(room_id, limit=20)
                    
                    # 메시지를 대화 기록 형식으로 변환 및 사용자 질문/언급된 NPC 확인
                    if recent_messages:
                        dialogue_history = ""
                        mentioned_npc = None
                        last_user_question = None
                        
                        # 최근 메시지 역순으로 확인하여 사용자 질문 찾기
                        user_messages = [msg for msg in recent_messages if msg.get('isUser', False)]
                        if user_messages:
                            # 가장 최근 사용자 메시지
                            latest_user_msg = user_messages[-1]
                            user_text = latest_user_msg.get('text', '').strip()
                            user_id = latest_user_msg.get('sender', '')
                            
                            # 메시지가 질문인지 확인 (한국어/영어 물음표 또는 특정 질문 패턴)
                            is_question = '?' in user_text or '?' in user_text or '할까' in user_text or '인가요' in user_text or '인가' in user_text or '할까요' in user_text or '해요' in user_text or '해' in user_text or '해줄래' in user_text
                            
                            if is_question and not user_question_answered:
                                last_user_question = user_text
                                logger.info(f"사용자 질문 감지: {last_user_question}")
                                
                                # 질문에서 언급된 NPC 찾기
                                for npc_id in current_npcs:
                                    # NPC 정보 가져오기
                                    npc_info = await get_npc_details(npc_id)
                                    npc_name = npc_info.get('name', '').strip()
                                    
                                    # 이름이 질문에 있는지 확인 (다양한 형태)
                                    name_variations = [
                                        npc_name, 
                                        npc_name + "님", 
                                        "@" + npc_name, 
                                        npc_id
                                    ]
                                    
                                    for name_var in name_variations:
                                        if name_var.lower() in user_text.lower():
                                            mentioned_npc = npc_id
                                            logger.info(f"사용자가 언급한 NPC 발견: {mentioned_npc} ({npc_name})")
                                            break
                                    
                                    if mentioned_npc:
                                        break
                            
                        # 대화 기록 구성
                        for msg in recent_messages:
                            # 발신자 이름 결정 - 사용자 메시지인 경우 실제 username 사용
                            if msg.get('isUser', False):
                                user_id = msg.get('sender', '')
                                # 실제 username이 있으면 사용, 없으면 기본값
                                sender_name = user_name_mapping.get(user_id, msg.get('senderName', 'User'))
                            else:
                                # NPC 메시지는 기존대로 처리
                                sender_name = msg.get('senderName')
                                # senderName이 없는 경우 처리
                                if not sender_name:
                                    try:
                                        npc_id = msg.get('sender')
                                        if npc_id and npc_id in current_npcs:
                                            npc_info = await get_npc_details(npc_id)
                                            sender_name = npc_info.get('name', npc_id.capitalize())
                                        else:
                                            sender_name = msg.get('sender', 'Unknown').capitalize()
                                    except:
                                        sender_name = msg.get('sender', 'Unknown').capitalize()
                            
                            text = msg.get('text', '')
                            if text:
                                # 대화 기록에 이름과 메시지 내용 추가
                                dialogue_history += f"{sender_name}: {text}\n\n"
                        
                        # 대화 기록 구성 완료 후 NPC ID 변환 처리
                        try:
                            # ID-이름 매핑 생성
                            id_name_mapping = await create_npc_id_name_mapping(current_npcs)
                            
                            # 대화 내용 전체에서 ID를 이름으로 변환
                            original_dialogue = dialogue_history
                            dialogue_history = replace_ids_with_names(dialogue_history, id_name_mapping)
                            
                            if original_dialogue != dialogue_history:
                                logger.info(f"대화 기록에서 NPC ID가 이름으로 변환되었습니다.")
                                logger.debug(f"변환 전 샘플: {original_dialogue[:200]}...")
                                logger.debug(f"변환 후 샘플: {dialogue_history[:200]}...")
                        except Exception as e:
                            logger.error(f"대화 기록 ID-이름 변환 오류: {str(e)}")
                        
                        logger.debug(f"대화 기록 업데이트됨: {len(recent_messages)}개 메시지")
                        logger.debug(f"대화 기록 샘플: {dialogue_history[:200]}...")
                    else:
                        logger.debug(f"채팅방 {room_id}에서 가져온 메시지 없음")
                except Exception as e:
                    logger.error(f"메시지 가져오기 오류: {str(e)}")
                
                # NPC 선택 로직 개선
                responding_npc_id = None
                
                # 사용자 질문에서 언급된 NPC가 있으면 그 NPC가 응답
                if mentioned_npc and mentioned_npc in current_npcs:
                    responding_npc_id = mentioned_npc
                    user_question_answered = True  # 질문에 응답 표시
                    logger.info(f"사용자가 언급한 {responding_npc_id}가 응답합니다")
                # 그렇지 않으면 이전 NPC와 다른 NPC 무작위 선택
                else:
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
                
                # 스타일 정보가 있으면 추가
                if npc_info.get('style'):
                    npc_description += f". Style: {npc_info['style']}"
                
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
                
                # 메시지 생성 - 대화 기록 반영 및 사용자 질문에 직접 응답하도록 개선
                logger.info(f"Generating philosophical response for {npc_info['name']} on topic: {current_topic}")
                logger.debug(f"이전 대화 길이: {len(dialogue_history)} 문자")
                logger.info(f"📣 NPC 설명: {npc_description}")
                
                # 응답 생성을 위한 추가 컨텍스트 구성
                additional_context = user_context
                
                # 사용자 질문이 있고 현재 NPC가 언급된 NPC라면, 그 질문에 직접 응답하도록 가이드
                if mentioned_npc == responding_npc_id and last_user_question:
                    additional_context += f"\n\nIMPORTANT: The user has directly asked you a question: '{last_user_question}'. Please respond to this question specifically and directly."
                    logger.info(f"사용자 질문에 직접 응답하도록 안내: {last_user_question}")
                
                try:
                    # 칸트의 경우 자동으로 RAG 활성화
                    use_rag = False
                    if responding_npc_id.lower() == 'kant':
                        use_rag = True
                        logger.info(f"🔍 칸트 응답을 위해 RAG 자동 활성화됨")
                    
                    response_text, _ = llm_manager.generate_philosophical_response(
                        npc_description=npc_description,
                        topic=current_topic,
                        context=additional_context,
                        previous_dialogue=dialogue_history,  # 이전 메시지 기록 전달
                        npc_id=responding_npc_id,  # npc_id 파라미터 추가
                        use_rag=use_rag  # 칸트인 경우에만 RAG 활성화
                    )
                    logger.debug(f"LLM에서 생성된 응답: {response_text[:100]}...")
                    
                    # NPC ID를 이름으로 변환하는 후처리 추가
                    try:
                        # 대화에 참여하는 모든 NPC의 ID-이름 매핑 생성
                        id_name_mapping = await create_npc_id_name_mapping(current_npcs)
                        
                        # 응답 텍스트에서 NPC ID를 이름으로 변환
                        original_text = response_text
                        response_text = replace_ids_with_names(response_text, id_name_mapping)
                        
                        # 변환 결과 확인
                        if original_text != response_text:
                            logger.info(f"응답 텍스트에서 NPC ID가 이름으로 변환되었습니다.")
                            logger.debug(f"원본: {original_text[:100]}...")
                            logger.debug(f"변환 후: {response_text[:100]}...")
                    except Exception as mapping_err:
                        logger.error(f"NPC ID-이름 변환 중 오류: {str(mapping_err)}")
                except Exception as llm_err:
                    logger.error(f"LLM 응답 생성 실패: {str(llm_err)}")
                    # 다음 사이클로 넘어감
                    await asyncio.sleep(5)
                    continue
                
                # 응답 메시지 구성 - 더 많은 NPC 정보 포함
                message_id = f"auto-{uuid4().hex[:8]}"
                
                # npc_name을 명확하게 결정
                npc_name = npc_info.get('name', '')
                if not npc_name:
                    npc_name = responding_npc_id.capitalize()
                
                message = {
                    "id": message_id,
                    "text": response_text,
                    "sender": responding_npc_id,  # sender를 NPC ID로 설정하여 프론트엔드에서 정보를 찾을 수 있게 함
                    "senderName": npc_name,  # 항상 이름 사용
                    "senderType": "npc",  # 추가: 발신자 타입
                    "isUser": False,
                    "timestamp": datetime.now().isoformat(),
                    "portrait_url": npc_info.get('portrait_url', None),  # 추가: 프로필 이미지 URL
                    "npc_id": responding_npc_id  # 추가: NPC ID 명시적 포함
                }
                
                logger.info(f"📣 최종 메시지 객체: {message}")
                logger.info(f"Generated message for {npc_name} in room {room_id}")
                logger.info(f"Message: {message['text'][:100]}...")
                
                # 대화 기록에 새 메시지 추가
                dialogue_history += f"{npc_name}: {message['text']}\n\n"
                
                # 언급된 NPC가 응답했다면 상태 재설정
                if mentioned_npc == responding_npc_id:
                    mentioned_npc = None
                    user_question_answered = True
                
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
                        
                        # 새 자동 대화 시작
                        task = asyncio.create_task(
                            auto_conversation_loop(room_id, npcs, topic, [15, 30])
                        )
                        manager.start_auto_conversation(room_id, task)
                        
                        await websocket.send_json({
                            "type": "auto_dialogue_status",
                            "status": "started"
                        })
                elif data["command"] == "stop_auto":
                    # 자동 대화 중지
                    stopped = manager.stop_auto_conversation(room_id)
                    await websocket.send_json({
                        "type": "auto_dialogue_status",
                        "status": "stopped" if stopped else "not_running"
                    })
            elif "type" in data and data["type"] == "send-message":
                # 메시지 수신 시 로깅
                logger.info(f"🚨 socket.id {websocket.client.port} send-message RAW data: {data}")
                
                # 필수 필드 확인
                if "roomId" not in data or "message" not in data:
                    logger.error(f"Invalid message format: {data}")
                    continue
                
                # RAG 사용 여부 필드 추출
                use_rag = data.get("useRAG", False)
                logger.info(f"🔍 RAG 사용 여부(클라이언트 요청): {'활성화' if use_rag else '비활성화'}")
                
                message_data = data["message"]
                
                # 메시지 로그
                logger.info(f"🚨 'send-message' 이벤트 수신 - 방 ID: {data['roomId']}, 메시지: {message_data}")
                
                try:
                    # DB에 메시지 저장
                    message_text = message_data.get("text", "")
                    logger.info(f"💾 MongoDB에 메시지 저장 중: {message_text[:30]}...")
                    saved = await save_message_to_db(data["roomId"], message_data)
                    
                    if saved:
                        logger.info(f"✅ 메시지가 MongoDB에 저장되었습니다.")
                    else:
                        logger.error(f"❌ 메시지 저장 실패")
                    
                    # 채팅방의 다른 사용자들에게 메시지 브로드캐스트
                    # Remove/truncate some fields before broadcasting
                    broadcast_message = {
                        "id": message_data.get("id", f"msg-{time.time()}"),
                        "text": message_text[:1000] + "..." if len(message_text) > 1000 else message_text,
                        "sender": message_data.get("sender", "Unknown")
                    }
                    
                    # 브로드캐스트
                    client_count = 0
                    logger.info(f"📢 메시지 브로드캐스트 [방 {data['roomId']}]: {json.dumps(broadcast_message)}")
                    
                    if data["roomId"] in manager.active_connections:
                        client_count = len(manager.active_connections[data["roomId"]])
                    
                    logger.info(f"📊 현재 방({data['roomId']})에 연결된 클라이언트 수: {client_count}명")
                    
                    # 본인을 제외한 모든 클라이언트에게 메시지 전송
                    for connection in manager.active_connections.get(data["roomId"], []):
                        if connection != websocket:  # 발신자에게는 메시지를 보내지 않음
                            try:
                                await connection.send_json({
                                    "type": "new-message",
                                    "roomId": data["roomId"],
                                    "message": broadcast_message
                                })
                            except Exception as e:
                                logger.error(f"브로드캐스트 오류: {str(e)}")
                    
                    logger.info(f"✅ 브로드캐스트 완료 - 발신자 제외 방송")
                    
                    # AI 응답 생성 로직
                    logger.info(f"🤖 AI 응답 생성 중... 방 ID: {data['roomId']}")
                    
                    # 자동 대화 모드인지 확인
                    is_auto_mode = data["roomId"] in active_auto_conversations and active_auto_conversations[data["roomId"]].get("active", False)
                    logger.info(f"🔍 자동 대화 모드 확인 결과: {'활성화됨' if is_auto_mode else '비활성화됨'}")
                    
                    if not is_auto_mode:
                        logger.info(f"🔍 자동 대화 모드 비활성화 - AI API 요청 시작 - 방 ID: {data['roomId']}")
                        
                        # 방 정보 가져오기
                        room_data = await get_room_data(data["roomId"])
                        
                        if not room_data or "participants" not in room_data:
                            logger.error(f"❌ 방 정보를 가져올 수 없음: {data['roomId']}")
                            continue
                        
                        # NPC 목록 가져오기
                        npcs = room_data.get("participants", {}).get("npcs", [])
                        
                        if not npcs:
                            logger.warning(f"⚠️ 방에 NPC가 없음: {data['roomId']}")
                            continue
                        
                        # 대화 주제 가져오기
                        topic = room_data.get("title", "")
                        context = room_data.get("context", "")
                        
                        # 최근 메시지 히스토리 가져오기
                        messages = await get_room_messages(data["roomId"])
                        
                        # AI 응답 요청 페이로드 구성
                        logger.info(f"🔍 메시지 수: {len(messages)}")
                        
                        # 응답할 철학자 선택
                        responding_philosopher = select_responding_philosopher(npcs, message_text)
                        logger.info(f"🎯 응답할 철학자: {responding_philosopher}")
                        
                        # 칸트의 경우 자동으로 RAG 활성화
                        if responding_philosopher.lower() == 'kant':
                            use_rag = True
                            logger.info(f"🔍 칸트 응답을 위해 RAG 자동 활성화됨")
                            
                        api_payload = {
                            "room_id": data["roomId"],
                            "user_message": message_text,
                            "npcs": npcs,
                            "topic": topic,
                            "context": context,
                            "use_rag": use_rag  # 수정된 RAG 사용 여부
                        }
                        
                        logger.info(f"📤 API 요청 페이로드: {json.dumps(api_payload)}")
                        
                        # Next.js API 서버 URL 가져오기
                        api_url = os.environ.get("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000")
                        chat_api_url = f"{api_url}/api/chat/generate"
                        
                        logger.info(f"🔗 Python API URL: {chat_api_url}")
                        
                        try:
                            # API 호출
                            async with aiohttp.ClientSession() as session:
                                async with session.post(chat_api_url, json=api_payload) as response:
                                    logger.info(f"🔍 Python API 응답 상태: {response.status} {response.reason}")
                                    
                                    if response.status == 200:
                                        ai_response = await response.json()
                                        logger.info(f"📥 Python API 응답 데이터: {json.dumps(ai_response)[:200]}...")
                                        
                                        # AI 응답 메시지 구성
                                        ai_message = {
                                            "id": f"ai-{int(time.time() * 1000)}",
                                            "text": ai_response["response"],
                                            "sender": ai_response["philosopher"],
                                            "isUser": False,
                                            "timestamp": datetime.now().isoformat()
                                        }
                                        
                                        # 디버깅을 위한 citations 상세 정보 출력
                                        logger.info(f"🧪 AI 응답 원본: {json.dumps(ai_response)[:1000]}...")
                                        logger.info(f"🧪 AI 응답에 'citations' 키 존재: {'citations' in ai_response}")
                                        if "citations" in ai_response:
                                            logger.info(f"🧪 citations 타입: {type(ai_response['citations'])}")
                                            logger.info(f"🧪 citations 갯수: {len(ai_response['citations'])}")
                                            logger.info(f"🧪 첫번째 citation: {json.dumps(ai_response['citations'][0]) if ai_response['citations'] else 'none'}")
                                            
                                            # citations 필드가 있으면 추가
                                            ai_message["citations"] = ai_response["citations"]
                                            logger.info(f"📚 AI 메시지에 {len(ai_response['citations'])}개의 인용 정보 포함됨")
                                            logger.info(f"🧪 ai_message 객체: {json.dumps(ai_message)[:1000]}...")
                                        else:
                                            logger.warning("⚠️ AI 응답에 citations 필드가 없습니다!")
                                        
                                        # 디버깅용 로그 추가
                                        logger.info(f"📋 최종 AI 메시지 객체: {json.dumps(ai_message)}")
                                        
                                        # MongoDB에 AI 메시지 저장
                                        saved = await save_message_to_db(data["roomId"], ai_message)
                                        if saved:
                                            logger.info(f"✅ AI 메시지({ai_message['id']})가 MongoDB에 저장되었습니다.")
                                        else:
                                            logger.error(f"❌ AI 메시지 저장 실패")
                                        
                                        # 모든 클라이언트에게 AI 응답 브로드캐스트
                                        logger.info(f"📢 AI 응답 브로드캐스트: {ai_message['text'][:100]}...")
                                        logger.debug(f"📢 브로드캐스트할 메시지 객체: {json.dumps(ai_message)[:500]}...")
                                        
                                        for connection in manager.active_connections.get(data["roomId"], []):
                                            try:
                                                await connection.send_json({
                                                    "type": "new-message",
                                                    "roomId": data["roomId"],
                                                    "message": ai_message
                                                })
                                            except Exception as e:
                                                logger.error(f"AI 응답 브로드캐스트 오류: {str(e)}")
                                        
                                        logger.info(f"✅ AI 응답 브로드캐스트 완료 - 모든 클라이언트에게 전송됨")
                                    else:
                                        error_text = await response.text()
                                        logger.error(f"❌ Python API 오류: {error_text}")
                        except Exception as e:
                            logger.error(f"❌ API 호출 오류: {str(e)}")
                
                except Exception as e:
                    logger.error(f"메시지 처리 중 오류: {str(e)}")
                
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

# 대화 관리자 클래스 추가
class ConversationManager:
    """대화 상태를 관리하고 토큰 제한을 처리하는 클래스"""
    
    def __init__(self):
        self.conversations = {}  # room_id를 키로 사용하는 대화 상태 저장소
        self.max_token_limit = 7000  # 토큰 제한 (GPT-4 기준 조정 가능)
        self.recent_messages_count = 10  # 항상 유지할 최근 메시지 수
        self.llm_manager = llm_manager  # 기존 llm_manager 사용
        logger.info("🔧 ConversationManager 초기화됨: 토큰 제한 %d, 최근 메시지 유지 %d개", 
                    self.max_token_limit, self.recent_messages_count)
        
    async def get_or_create_conversation(self, room_id):
        """대화 상태를 가져오거나 새로 생성"""
        if room_id not in self.conversations:
            # DB에서 기존 메시지와 방 정보 로드
            try:
                # 대화방 정보 로드
                room_data = await get_room_data(room_id)
                messages = await get_room_messages(room_id, limit=50)  # 최근 50개 메시지로 시작
                
                # 정적 정보 설정
                self.conversations[room_id] = {
                    "messages": messages,
                    "npc_descriptions": {},
                    "context": room_data.get("context", ""),
                    "topic": room_data.get("title", ""),
                    "npcs": room_data.get("npcs", []),
                    "last_summary_time": time.time()
                }
                
                # NPC 정보 불러오기
                for npc_id in self.conversations[room_id]["npcs"]:
                    await self.load_npc_description(room_id, npc_id)
                    
                logger.info(f"🔄 Room {room_id} 대화 DB에서 로드됨: {len(messages)}개 메시지, 토픽: {room_data.get('title', '없음')}")
        
                # 현재 토큰 수 계산 및 로깅
                if messages:
                    token_count = self._count_tokens_approx(messages)
                    logger.debug(f"📊 Room {room_id} 현재 토큰 수: {token_count}/{self.max_token_limit} ({token_count/self.max_token_limit*100:.1f}%)")
            except Exception as e:
                logger.error(f"Error loading conversation data for room {room_id}: {e}")
                # 오류 시 빈 대화로 초기화
                self.conversations[room_id] = {
                    "messages": [],
                    "npc_descriptions": {},
                    "context": "",
                    "topic": "",
                    "npcs": [],
                    "last_summary_time": time.time()
                }
                
        return self.conversations[room_id]
    
    async def load_npc_description(self, room_id, npc_id):
        """NPC 설명 로드"""
        conversation = await self.get_or_create_conversation(room_id)
        
        # 이미 로드된 경우 스킵
        if npc_id in conversation["npc_descriptions"]:
            return conversation["npc_descriptions"][npc_id]
            
        try:
            # NPC 정보 가져오기
            npc_info = await get_npc_details(npc_id)
            npc_description = f"{npc_info['name']}: {npc_info.get('description', 'A philosopher with unique perspectives')}"
            
            # 커스텀 NPC인 경우 추가 특성 포함
            if npc_info.get('is_custom', False):
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
                    
            # 캐시에 저장
            conversation["npc_descriptions"][npc_id] = npc_description
            logger.info(f"NPC description loaded for {npc_id}")
            
            return npc_description
        except Exception as e:
            logger.error(f"Error loading NPC description for {npc_id}: {e}")
            # 기본 설명 제공
            default_description = f"Philosopher {npc_id[:6]}: A thinker with unique perspectives"
            conversation["npc_descriptions"][npc_id] = default_description
            return default_description
    
    async def add_message(self, room_id, message_data):
        """메시지 추가 및 콘텍스트 관리"""
        conversation = await self.get_or_create_conversation(room_id)
        
        # 메시지 추가
        conversation["messages"].append(message_data)
        
        # 디버깅: 메시지 추가 후 토큰 수 계산
        token_count = self._count_tokens_approx(conversation["messages"])
        logger.debug(f"📝 메시지 추가됨 - Room {room_id}: 발신자={message_data.get('sender', 'unknown')}, 현재 토큰 수={token_count}")
        
        # DB에 메시지 저장 (기존 로직 사용)
        await save_message_to_db(room_id, message_data)
        
        # 메시지 추가 후 필요하면 콘텍스트 최적화
        await self._manage_context_window(room_id)
        
        return message_data
    
    async def _manage_context_window(self, room_id):
        """토큰 제한을 고려하여 콘텍스트 창 관리"""
        conversation = await self.get_or_create_conversation(room_id)
        messages = conversation["messages"]
        
        # 메시지가 충분히 많아졌을 때만 처리
        if len(messages) < 20:
            return
            
        # 예상 토큰 수 계산
        total_tokens = self._count_tokens_approx(messages)
        
        # 토큰 수가 제한에 근접하면 오래된 메시지 요약
        if total_tokens > self.max_token_limit * 0.8:  # 80% 임계값
            logger.info(f"⚠️ 토큰 수({total_tokens})가 제한({self.max_token_limit})의 80%에 근접 - Room {room_id} 오래된 메시지 요약")
            await self._summarize_older_messages(room_id)
    
    async def _summarize_older_messages(self, room_id):
        """오래된 메시지를 요약하여 토큰 수 줄이기"""
        conversation = await self.get_or_create_conversation(room_id)
        messages = conversation["messages"]
        
        # 최근 메시지는 보존
        recent_messages = messages[-self.recent_messages_count:]
        older_messages = messages[:-self.recent_messages_count]
        
        if len(older_messages) < 5:
            return  # 요약할 메시지가 충분하지 않으면 스킵
        
        try:
            # 오래된 메시지 포맷팅
            formatted_messages = self._format_messages_for_summary(older_messages)
            
            # 요약 생성 시작 로깅
            logger.debug(f"🔄 요약 시작 - Room {room_id}: {len(older_messages)}개 메시지 요약 중")
            before_token_count = self._count_tokens_approx(messages)
            
            # 요약 생성
            system_prompt = "Summarize the following conversation in 2-3 concise sentences, preserving key points and context."
            summary = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=formatted_messages,
                llm_provider="openai",
                llm_model="gpt-3.5-turbo"  # 요약에는 저렴한 모델 사용
            )
            
            # 요약 메시지 생성
            summary_message = {
                "id": f"summary-{uuid4()}",
                "text": f"[Previous conversation summary: {summary}]",
                "sender": "System",
                "is_summary": True,
                "isUser": False,
                "timestamp": datetime.now().isoformat()
            }
            
            # 대화 상태 업데이트 - 요약으로 대체
            conversation["messages"] = [summary_message] + recent_messages
            after_token_count = self._count_tokens_approx(conversation["messages"])
            
            logger.info(f"✅ Room {room_id} 요약 완료: {len(older_messages)}개 메시지가 요약됨")
            logger.info(f"📊 토큰 감소: {before_token_count} → {after_token_count} ({before_token_count-after_token_count}개 토큰 절약)")
            
            # 요약 메시지 DB에 저장
            await save_message_to_db(room_id, summary_message)
            
        except Exception as e:
            logger.error(f"❌ 메시지 요약 오류: {e}")
            # 오류 시 단순히 오래된 메시지 잘라내기
            conversation["messages"] = older_messages[-5:] + recent_messages  # 오래된 메시지 중 최근 5개만 유지
            logger.warning(f"⚠️ 요약 대신 오래된 메시지 {len(older_messages)-5}개 제거됨")
    
    def _format_messages_for_summary(self, messages):
        """요약을 위한 메시지 포맷팅"""
        formatted = []
        for msg in messages:
            sender = msg.get("sender", "Unknown")
            text = msg.get("text", "")
            is_user = msg.get("isUser", False)
            
            prefix = "User" if is_user else sender
            formatted.append(f"{prefix}: {text}")
            
        return "\n".join(formatted)
    
    async def get_prompt_context(self, room_id, responding_npc_id):
        """LLM에 전달할 프롬프트 컨텍스트 생성"""
        conversation = await self.get_or_create_conversation(room_id)
        
        # NPC 설명 가져오기
        npc_description = conversation["npc_descriptions"].get(responding_npc_id, "")
        if not npc_description:
            npc_description = await self.load_npc_description(room_id, responding_npc_id)
            
        # 대화 포맷팅
        messages = conversation["messages"]
        formatted_dialogue = self._format_previous_dialogue(messages)
        
        return {
            "npc_description": npc_description,
            "topic": conversation["topic"],
            "context": conversation["context"],
            "previous_dialogue": formatted_dialogue
        }
    
    def _format_previous_dialogue(self, messages):
        """대화 기록을 프롬프트용으로 포맷팅"""
        formatted = []
        
        for msg in messages:
            # 요약 메시지는 그대로 포함
            if msg.get("is_summary", False):
                formatted.append(msg["text"])
                continue
                
            sender = msg.get("sender", "Unknown")
            text = msg.get("text", "")
            is_user = msg.get("isUser", False)
            
            prefix = "User" if is_user else sender
            formatted.append(f"{prefix}: {text}")
            
        return "\n".join(formatted)
    
    def _count_tokens_approx(self, messages, model="gpt-4"):
        """메시지의 대략적인 토큰 수 계산"""
        try:
            if 'tiktoken' in globals():
                encoding = tiktoken.encoding_for_model(model)
                
                total_tokens = 0
                for msg in messages:
                    # 메시지 내용의 토큰 수 계산
                    text = msg.get("text", "")
                    tokens = len(encoding.encode(text))
                    # 메시지 메타데이터에 대한 추가 토큰
                    total_tokens += tokens + 4  # 각 메시지에 대한 오버헤드
                    
                # 전체 요청 형식에 대한 기본 토큰 추가
                total_tokens += 2
                
                return total_tokens
            else:
                # tiktoken이 없으면 문자 길이 기반 대략적인 추정치 반환
                chars = sum(len(msg.get("text", "")) for msg in messages)
                tokens_approx = chars // 4  # 영어 텍스트에서 대략 4자당 1토큰으로 추정
                logger.debug("⚠️ tiktoken 라이브러리 없음: 문자 기반 토큰 추정치 사용 (%d 문자 → %d 토큰)", chars, tokens_approx)
                return tokens_approx
        except Exception as e:
            logger.error(f"❌ 토큰 계산 오류: {e}")
            # 오류 시 문자 길이 기반 대략적인 추정치 반환
            chars = sum(len(msg.get("text", "")) for msg in messages)
            return chars // 4

# 대화 관리자 인스턴스 생성
conversation_manager = ConversationManager()

# ChatGenerateRequest 모델 수정
class ChatGenerateRequest(BaseModel):
    npc_descriptions: Optional[str] = None
    npcs: Optional[List[str]] = []  # 필수 필드를 Optional로 설정
    room_id: str  # 룸 ID 필드 추가
    user_message: str  # 사용자 메시지 필드 추가
    topic: Optional[str] = ""
    context: Optional[str] = ""
    previous_dialogue: Optional[str] = ""  # 하위 호환성을 위해 유지
    llm_provider: Optional[str] = "openai"
    llm_model: Optional[str] = "gpt-4o"
    api_key: Optional[str] = None
    use_rag: Optional[bool] = False  # RAG 사용 여부 플래그 추가

# API 엔드포인트 수정
@app.post("/api/chat/generate")
async def generate_chat_response(request: ChatGenerateRequest):
    """
    새로운 AI 채팅 응답을 생성합니다.
    """
    try:
        logger.info(f"🔄 채팅 응답 생성 요청: {request.room_id}")
        
        # 사용할 NPC 목록 확인 (우선 순위: npcs > npc_descriptions)
        npcs = request.npcs or []
        if not npcs and request.npc_descriptions:
            # 레거시 지원: 쉼표로 구분된 npc 목록 문자열을 파싱
            npcs = [npc.strip() for npc in request.npc_descriptions.split(',')]
        
        # 적어도 하나의 NPC가 필요함
        if not npcs:
            raise HTTPException(status_code=400, detail="No NPCs specified")
        
        # 사용자 메시지가 필요함
        if not request.user_message or not request.user_message.strip():
            raise HTTPException(status_code=400, detail="User message is required")
        
        # 추가 컨텍스트 정보 (빈 문자열이면 None으로 설정)
        context = request.context.strip() if request.context else None
        topic = request.topic.strip() if request.topic else None
        
        # 이전 대화 문맥 처리
        previous_dialogue = request.previous_dialogue.strip() if request.previous_dialogue else None
        
        # LLM 프로바이더 및 모델 설정
        llm_provider = request.llm_provider.lower() if request.llm_provider else None
        llm_model = request.llm_model if request.llm_model else None
        
        # API 키 처리
        api_key = request.api_key
        if api_key:
            # API 키가 제공된 경우 환경 변수 설정
            if llm_provider == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif llm_provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
        
        # 사용자 메시지 로깅
        logger.info(f"💬 user_message: {request.user_message[:50]}...")
        
        # RAG 사용 여부 확인
        use_rag = request.use_rag if request.use_rag is not None else False
        logger.info(f"🔍 RAG 사용 여부(클라이언트 요청): {use_rag}")
        
        # 응답할 철학자(NPC) 선택
        responding_philosopher = select_responding_philosopher(npcs, request.user_message)
        logger.info(f"🎯 응답할 철학자: {responding_philosopher}")
        
        # 칸트의 경우 자동으로 RAG 활성화
        if responding_philosopher.lower() == 'kant':
            use_rag = True
            logger.info(f"🔍 칸트 응답을 위해 RAG 자동 활성화됨")
        
        # 선택된 철학자에 대한 설명 로드
        philosopher_system_prompt = philosopher_descriptions.get(responding_philosopher.lower(), "")
        if not philosopher_system_prompt:
            logger.warning(f"⚠️ 철학자 설명을 찾을 수 없음: {responding_philosopher}. 기본 설명 사용.")
            philosopher_system_prompt = f"{responding_philosopher} is a philosopher with unique views."
        
        # 대화 컨텍스트 구성
        dialogue_context = ""
        if previous_dialogue:
            dialogue_context = previous_dialogue
        else:
            # 새로운 대화인 경우 사용자 메시지를 컨텍스트에 추가
            dialogue_context = f"User: {request.user_message}"
        
        # 주제가 없는 경우 컨텍스트에서 추론
        if not topic:
            dialogue_lines = dialogue_context.strip().split('\n')
            if len(dialogue_lines) > 0:
                # 첫 번째 줄에서 주제 추출 시도
                first_line = dialogue_lines[0].strip()
                # 'User:' 접두사 제거
                if first_line.lower().startswith("user:"):
                    topic = first_line.split(':', 1)[1].strip()
                else:
                    topic = first_line
            # 그래도 없으면 사용자 메시지 사용
            if not topic:
                topic = request.user_message
        
        # 사용자 메시지 로깅
        logger.info(f"💬 user_message: {request.user_message[:50]}...")
        logger.info(f"💬 topic: {topic[:50]}...")
        logger.info(f"💬 context: {context[:50] if context else 'None'}...")
        logger.info(f"💬 dialogue_context: {dialogue_context[:50]}...")
        
        # LLM Manager를 사용하여 철학적 응답 생성
        logger.debug(f"🔄 철학적 응답 생성 시작...")
        response_text, metadata = llm_manager.generate_philosophical_response(
            npc_description=philosopher_system_prompt,
            topic=topic,
            context=context or "",
            previous_dialogue=dialogue_context,
            llm_provider=llm_provider,
            llm_model=llm_model,
            use_rag=use_rag,
            npc_id=responding_philosopher.lower()
        )
        
        # 응답 로깅
        logger.info(f"✅ 응답 생성 완료: {response_text[:50]}...")
        
        # 인용 정보 확인 및 추출
        citations = metadata.get("citations", [])
        if citations:
            logger.info(f"📚 {len(citations)}개의 인용 정보가 포함되어 있습니다.")
            # 확인을 위해 첫 번째 인용 정보 로깅
            if len(citations) > 0:
                logger.info(f"📚 첫 번째 인용 정보: id={citations[0].get('id', '?')}, source={citations[0].get('source', '?')}")
                logger.debug(f"📚 인용 정보 전체 목록: {citations}")
        else:
            logger.warning("⚠️ 인용 정보가 없습니다.")
        
        # 응답 데이터 구성 - 인용 정보를 응답 객체의 최상위 수준에 포함
        response_data = {
            "response": response_text,
            "philosopher": responding_philosopher,
            "metadata": {
                "elapsed_time": metadata.get("elapsed_time", "N/A"),
                "rag_used": metadata.get("rag_used", False)
            },
            "citations": citations  # citations 필드를 직접 최상위 수준에 추가
        }
        
        # 응답 데이터 디버깅을 위해 로깅
        logger.debug(f"📤 최종 응답 데이터 구조: {list(response_data.keys())}")
        logger.debug(f"📤 응답 데이터 citations 필드 타입: {type(response_data['citations'])}")
        logger.debug(f"📤 응답 데이터 citations 항목 수: {len(response_data['citations'])}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"❌ 응답 생성 오류: {str(e)}")
        # 상세한 오류 스택트레이스 로깅
        logger.exception("상세 오류 정보:")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

def select_responding_philosopher(npcs: List[str], user_message: str) -> str:
    """대화 컨텍스트에 기반하여 응답할 철학자를 선택"""
    if not npcs:
        raise ValueError("No philosophers available to respond")
    
    # LLM을 활용한 NPC 선택 함수로 개선
    try:
        logger.info(f"📊 응답 NPC 선택 시작: '{user_message[:50]}...'")
        logger.info(f"📊 NPC 후보 목록: {', '.join(npcs)}")
        
        # NPC 세부 정보 로드 - NPC ID와 이름, 설명을 매핑
        npc_details = {}
        for npc_id in npcs:
            try:
                # 전역 npc_cache 사용
                cache_key = f"npc:{npc_id}"
                cached_info = npc_cache.get(cache_key, None)
                if cached_info and 'data' in cached_info:
                    npc_info = cached_info['data']
                else:
                    # 캐시에 없으면 직접 가져오기
                    logger.debug(f"📋 NPC {npc_id} 정보를 캐시에서 찾지 못함, DB 조회")
                    npc_info = asyncio.run(get_npc_details(npc_id))
                
                # NPC 이름, 필명, 한글 이름 등 변형 추가
                npc_name = npc_info.get('name', '')
                npc_details[npc_id] = {
                    "name": npc_name,
                    "name_lower": npc_name.lower(),
                    "ko_name": get_korean_name(npc_id, npc_name),  # 한글 이름 추가
                }
                logger.debug(f"📋 NPC {npc_id} 정보: {npc_details[npc_id]}")
            except Exception as e:
                logger.error(f"NPC {npc_id} 정보 가져오기 오류: {e}")
        
        # 1. 먼저 사용자가 직접 언급한 NPC를 찾음
        logger.info(f"🔍 1단계: 사용자 메시지에서 직접 언급된 NPC 찾기")
        mentioned_npc = find_mentioned_npc(user_message, npc_details)
        if mentioned_npc:
            logger.info(f"✅ 사용자가 직접 언급한 NPC 발견: {mentioned_npc}")
            # NPC 이름 로깅
            npc_name = npc_details.get(mentioned_npc, {}).get('name', mentioned_npc)
            logger.info(f"✅ 응답자 선택 완료: {mentioned_npc} ({npc_name})")
            return mentioned_npc
        
        # 2. 직접 언급이 없으면 LLM을 사용하여 적합한 NPC 선택
        logger.info(f"🔍 2단계: LLM을 사용하여 적합한 NPC 선택")
        selected_npc = select_npc_with_llm(user_message, npcs, npc_details)
        if selected_npc:
            # NPC 이름 로깅
            npc_name = npc_details.get(selected_npc, {}).get('name', selected_npc)
            logger.info(f"✅ LLM이 선택한 NPC: {selected_npc} ({npc_name})")
            return selected_npc
        
        # 3. LLM 선택 실패 시 랜덤 선택
        logger.info(f"🔍 3단계: 랜덤 NPC 선택")
        random_npc = random.choice(npcs)
        # NPC 이름 로깅
        npc_name = npc_details.get(random_npc, {}).get('name', random_npc)
        logger.info(f"✅ 랜덤 선택된 NPC: {random_npc} ({npc_name})")
        return random_npc
        
    except Exception as e:
        logger.error(f"NPC 선택 중 오류 발생: {e}")
        # 오류 발생 시 랜덤 선택으로 폴백
        random_npc = random.choice(npcs)
        logger.info(f"✅ 오류 후 랜덤 선택된 NPC: {random_npc}")
        return random_npc

# 한글 이름 매핑 추가
def get_korean_name(npc_id: str, english_name: str) -> str:
    """NPC의 한글 이름 반환"""
    # 기본 한글 이름 매핑
    ko_names = {
        "socrates": "소크라테스",
        "plato": "플라톤",
        "aristotle": "아리스토텔레스",
        "kant": "칸트",
        "hegel": "헤겔",
        "nietzsche": "니체",
        "marx": "마르크스",
        "sartre": "사르트르",
        "camus": "카뮈",
        "beauvoir": "보부아르",
        "confucius": "공자",
        "laozi": "노자",
        "buddha": "붓다",
        "rousseau": "루소",
        "wittgenstein": "비트겐슈타인"
    }
    
    # 먼저 ID로 찾기
    if npc_id.lower() in ko_names:
        return ko_names[npc_id.lower()]
    
    # 영어 이름의 일부가 매핑에 있는지 확인
    for en_name, ko_name in ko_names.items():
        if en_name in english_name.lower():
            return ko_name
    
    # 매핑이 없으면 영어 이름 그대로 반환
    return english_name

# 직접 언급된 NPC 찾기
def find_mentioned_npc(message: str, npc_details: Dict[str, Dict[str, str]]) -> Optional[str]:
    """사용자 메시지에서 직접 언급된 NPC ID 찾기"""
    if not message or not npc_details:
        return None
    
    logger.info(f"🔍 메시지에서 언급된 NPC 찾기: '{message}'")
    
    # LLM을 사용하여 메시지에서 언급된 NPC 찾기
    try:
        return select_npc_with_llm(message, list(npc_details.keys()), npc_details, is_direct_mention=True)
    except Exception as e:
        logger.error(f"LLM을 사용한 NPC 언급 감지 중 오류: {e}")
        return None

# LLM으로 NPC 선택
def select_npc_with_llm(user_message: str, npcs: List[str], npc_details: Dict[str, Dict[str, str]], is_direct_mention: bool = False) -> Optional[str]:
    """LLM을 사용하여 응답에 가장 적합한 NPC 선택"""
    if not npcs or not user_message:
        return None
        
    try:
        # NPC 정보 목록 생성 (ID, 이름, 한글 이름 포함)
        npc_info_list = []
        for npc_id in npcs:
            details = npc_details.get(npc_id, {})
            name = details.get("name", npc_id)
            ko_name = details.get("ko_name", "")
            
            # 각 NPC마다 다양한 식별자 정보 포함
            npc_info = f"ID: {npc_id} | 이름: {name}"
            if ko_name:
                npc_info += f" | 한글 이름: {ko_name}"
                
            npc_info_list.append(npc_info)
        
        npc_options = "\n".join(npc_info_list)
        
        mode = "직접 언급 감지" if is_direct_mention else "응답 NPC 선택"
        logger.info(f"🧠 LLM을 사용한 {mode} 시작: '{user_message[:50]}...'")
        
        # 시스템 프롬프트 구성 - 목적에 따라 다르게 조정
        if is_direct_mention:
            system_prompt = f"""
            당신은 대화에서 사용자가 직접 언급한 참여자를 감지하는 AI입니다.
            
            아래 사용자 메시지에서 직접 언급된 참여자(NPC)가 있는지 분석하세요.
            
            가능한 NPC 목록:
            {npc_options}
            
            규칙:
            1. 사용자 메시지에서 NPC의 이름이나 ID가 직접 언급된 경우에만 해당 NPC를 선택하세요.
            2. 오타가 있어도 분명히 특정 NPC를 지칭했다면 해당 NPC를 선택하세요.
            3. 직접 언급이 없으면 아무 것도 선택하지 마세요.
            4. 선택한 NPC의 ID만 정확히 반환하세요. (예: "e0c3872b-2103-4d04-8a2d-801bbd7f43cf")
            
            출력 형식:
            NPC_ID: <npc_id 또는 '없음'>
            """
        else:
            system_prompt = f"""
            당신은 대화에서 사용자 메시지에 가장 적합한 응답자를 선택하는 AI입니다.
            
            아래 사용자 메시지를 분석하고, 응답하기에 가장 적합한 참여자(NPC)를 선택하세요.
            
            가능한 NPC 목록:
            {npc_options}
            
            규칙:
            1. 사용자가 특정 철학자의 견해나 이론을 언급하면, 그 철학자를 선택합니다.
            2. 사용자의 질문이나 의견이 특정 철학자의 전문 분야와 관련있으면, 그 철학자를 선택합니다.
            3. 모든 NPC가 동등하게 응답할 수 있는 내용이면, 가장 흥미로운 관점을 제공할 수 있는 NPC를 선택합니다.
            4. 선택한 NPC의 ID만 정확히 반환하세요. (예: "e0c3872b-2103-4d04-8a2d-801bbd7f43cf")
            
            출력 형식:
            NPC_ID: <npc_id>
            """
        
        # 사용자 프롬프트
        if is_direct_mention:
            user_prompt = f"다음 메시지에서 사용자가 직접 언급한 NPC가 있는지 확인해주세요: '{user_message}'"
        else:
            user_prompt = f"다음 사용자 메시지에 응답하기에 가장 적합한 NPC를 선택해주세요: '{user_message}'"
        
        # LLM 호출 - 가벼운 모델 사용
        logger.debug(f"🧠 NPC 선택 LLM 호출 중...")
        response = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider="openai",
            llm_model="gpt-3.5-turbo"
        )
        
        logger.debug(f"🧠 LLM 원본 응답: {response}")
        
        # 정규표현식으로 ID 추출 시도
        id_match = re.search(r'NPC_ID: *(\S+)', response, re.IGNORECASE)
        if id_match:
            extracted_id = id_match.group(1).strip()
            
            # "없음" 처리 (직접 언급이 없는 경우)
            if extracted_id.lower() in ["없음", "none", "null"]:
                logger.info(f"✅ LLM 응답: 직접 언급된 NPC 없음")
                return None
                
            # ID가 유효하면 반환
            if extracted_id in npcs:
                logger.info(f"✅ LLM이 선택한 NPC ID: {extracted_id}")
                return extracted_id
            else:
                logger.warning(f"⚠️ LLM이 추출한 ID가 유효하지 않음: {extracted_id}")
        
        # 정규식으로 찾지 못한 경우 전체 응답에서 NPC ID 포함 여부 확인
        for npc_id in npcs:
            if npc_id in response:
                logger.info(f"✅ LLM 응답에서 NPC ID 발견: {npc_id}")
                return npc_id
        
        # 만약 직접 언급 검사모드였는데 찾지 못했다면 None 반환
        if is_direct_mention:
            logger.info("❌ 메시지에서 직접 언급된 NPC를 찾지 못했습니다.")
            return None
            
        # 응답 NPC 선택 모드에서는 랜덤 선택 진행
        logger.warning("❌ LLM에서 유효한 NPC를 선택하지 못했습니다.")
        return None
        
    except Exception as e:
        logger.error(f"LLM을 사용한 NPC 선택 중 오류: {e}")
        return None

@app.get("/api/npc/get")
async def get_npc_details(id: str):
    try:
        # Cache 키 생성
        cache_key = f"npc_{id}"
        current_time = time.time()
        
        # 캐시에서 조회 (만료 시간: 10분)
        if cache_key in npc_cache and (current_time - npc_cache[cache_key]['timestamp']) < 600:
            logger.info(f"🔍 Cache hit: NPC {id} found in cache")
            return npc_cache[cache_key]['data']
        
        logger.info(f"Looking up philosopher with ID: {id}")
        
        # UUID 형태인 경우 커스텀 NPC로 간주
        is_uuid = False
        try:
            uuid_obj = uuid.UUID(id)
            is_uuid = True
            logger.info(f"Detected UUID format: {id}, treating as custom NPC")
        except ValueError:
            is_uuid = False
        
        if is_uuid:
            # 커스텀 NPC 조회 로직
            custom_npc = None
            
            try:
                # MongoDB에서 NPC 조회
                db_client = get_mongo_client()
                db = db_client[MONGO_DB]
                npc_collection = db["npcs"]
                
                # backend_id 필드로 조회
                custom_npc = npc_collection.find_one({"backend_id": id})
                
                if custom_npc:
                    logger.info(f"Found custom NPC with backend_id: {id}")
                    
                    # MongoDB ObjectId를 문자열로 변환
                    custom_npc["_id"] = str(custom_npc["_id"])
                    
                    # 응답 데이터 구성
                    response_data = {
                        "id": id,
                        "name": custom_npc.get("name", "Unknown"),
                        "description": custom_npc.get("description", ""),
                        "reference_philosophers": custom_npc.get("reference_philosophers", []),
                        "communication_style": custom_npc.get("communication_style", "balanced"),
                        "debate_approach": custom_npc.get("debate_approach", "dialectical"),
                        "voice_style": custom_npc.get("voice_style", ""),
                        "portrait_url": custom_npc.get("portrait_url", ""),
                        "is_custom": True
                    }
            
                    # 캐시에 저장
                    npc_cache[cache_key] = {
                        'data': response_data,
                        'timestamp': current_time
                    }
                    
                    return response_data
            except Exception as e:
                logger.error(f"Error looking up custom NPC: {str(e)}")

        # 기본 철학자 ID 또는 커스텀 NPC를 찾지 못한 경우
        philosopher_id = id.lower()
        
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
                "style": data.get("style", ""),  # style 필드 추가
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
        else:
            # 최종적으로 찾지 못한 경우 404 응답
            return JSONResponse(
                status_code=404, 
                content={"detail": f"Philosopher or NPC with ID {id} not found"}
            )
    except Exception as e:
        logger.error(f"Error in get_npc_details: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to get NPC details: {str(e)}"}
        )

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

# 유틸리티 함수 추가 - NPC ID 이름 매핑 생성 및 변환 함수
async def create_npc_id_name_mapping(npc_ids: List[str]) -> Dict[str, str]:
    """주어진 NPC ID 목록에서 ID-이름 매핑 사전을 생성합니다."""
    mapping = {}
    
    for npc_id in npc_ids:
        try:
            # NPC 정보 가져오기
            npc_info = await get_npc_details(npc_id)
            
            # 정보가 있고 이름이 있는 경우에만 매핑 추가
            if npc_info and 'name' in npc_info:
                npc_name = npc_info.get('name')
                
                # 이름이 실제로 있는지 확인
                if npc_name and isinstance(npc_name, str) and len(npc_name.strip()) > 0:
                    # ID를 이름으로 매핑
                    mapping[npc_id] = npc_name
                    
                    # UUID 형태인 경우 추가 매핑
                    if '-' in npc_id:
                        # UUID 전체를 매핑
                        mapping[npc_id] = npc_name
                        
                        # 대화에서 흔히 언급되는 UUID 앞부분만 매핑 (예: 638e7579)
                        short_id = npc_id.split('-')[0]
                        if len(short_id) >= 8:
                            mapping[short_id] = npc_name
                            logger.debug(f"UUID 앞부분 매핑 추가: {short_id} -> {npc_name}")
                    
                    logger.debug(f"ID-이름 매핑 추가: {npc_id} -> {npc_name}")
                else:
                    logger.warning(f"NPC {npc_id}의 이름이 없거나 유효하지 않음: {npc_name}")
            else:
                logger.warning(f"NPC {npc_id}의 상세 정보가 없거나 이름이 없음")
                
        except Exception as e:
            logger.error(f"NPC 정보 가져오기 실패 (ID: {npc_id}): {str(e)}")
    
    # 매핑 전체 로깅
    logger.info(f"생성된 ID-이름 매핑: {mapping}")
    return mapping

def replace_ids_with_names(text: str, id_name_mapping: Dict[str, str]) -> str:
    """텍스트에서 NPC ID를 해당 이름으로 변환합니다."""
    if not text or not id_name_mapping:
        return text
        
    result = text
    
    # 먼저 전체 UUID 패턴 처리 (하이픈 포함된 ID 먼저)
    uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    
    # UUID 패턴을 찾아 처리
    for npc_id in id_name_mapping:
        if '-' in npc_id:  # UUID 형태만 우선 처리
            npc_name = id_name_mapping[npc_id]
            
            # UUID + 님 패턴
            result = re.sub(rf'{re.escape(npc_id)}님', f'{npc_name}님', result)
            
            # @UUID 패턴
            result = re.sub(rf'@{re.escape(npc_id)}', f'@{npc_name}', result)
            
            # UUID 단독 패턴 (단어 경계 확인)
            result = re.sub(rf'\b{re.escape(npc_id)}\b', npc_name, result)
    
    # 그 다음 하이픈이 없는 일반 ID 처리
    for npc_id, npc_name in sorted(id_name_mapping.items(), key=lambda x: len(x[0]), reverse=True):
        if '-' not in npc_id:  # 일반 ID만 처리 (UUID는 이미 처리함)
            # 다양한 패턴 처리 (ID 자체, ID님, @ID 등)
            patterns = [
                f"{npc_id}", 
                f"{npc_id}님",
                f"@{npc_id}"
            ]
            
            for pattern in patterns:
                # 단어 경계 확인 
                matches = re.finditer(r'(\b|^)' + re.escape(pattern) + r'(\b|$)', result)
                
                # 뒤에서부터 변환(인덱스가 변하지 않도록)
                positions = [(m.start(), m.end()) for m in matches]
                for start, end in reversed(positions):
                    prefix = result[:start]
                    suffix = result[end:]
                    
                    if "님" in pattern:
                        replacement = f"{npc_name}님"
                    elif "@" in pattern:
                        replacement = f"@{npc_name}"
                    else:
                        replacement = npc_name
                        
                    result = prefix + replacement + suffix
                    logger.debug(f"NPC ID {pattern}를 이름 {npc_name}으로 변환")
    
    return result

# 서버 실행 (독립 실행 시)
if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

# 대화 상태 진단용 API 엔드포인트 추가
@app.get("/api/debug/conversation/{room_id}")
async def debug_conversation_state(room_id: str):
    """대화 상태를 진단하기 위한 디버깅 엔드포인트"""
    try:
        # 대화 상태 가져오기
        conversation = await conversation_manager.get_or_create_conversation(room_id)
        
        # 토큰 수 계산
        message_count = len(conversation["messages"])
        total_tokens = conversation_manager._count_tokens_approx(conversation["messages"])
        token_percentage = (total_tokens / conversation_manager.max_token_limit) * 100
        
        # 요약된 메시지가 있는지 확인
        summary_count = sum(1 for msg in conversation["messages"] if msg.get("is_summary", False))
        
        # 응답 구성
        response = {
            "room_id": room_id,
            "topic": conversation["topic"],
            "message_count": message_count,
            "token_count": total_tokens,
            "token_limit": conversation_manager.max_token_limit,
            "token_percentage": f"{token_percentage:.1f}%",
            "summary_count": summary_count,
            "npcs": conversation["npcs"],
            "recent_messages": [
                {
                    "id": msg.get("id", "unknown"),
                    "sender": msg.get("sender", "unknown"),
                    "is_summary": msg.get("is_summary", False),
                    "length": len(msg.get("text", "")),
                    "tokens": conversation_manager._count_tokens_approx([msg])
                }
                for msg in conversation["messages"][-5:] # 최근 5개 메시지만 포함
            ],
            "server_time": datetime.now().isoformat()
        }
        
        logger.info(f"🔍 대화 상태 진단 - Room {room_id}: {message_count}개 메시지, {total_tokens}개 토큰 ({token_percentage:.1f}%)")
        return response
        
    except Exception as e:
        logger.error(f"❌ 대화 상태 진단 오류: {e}")
        raise HTTPException(status_code=500, detail=f"대화 상태를 불러올 수 없습니다: {str(e)}")

# 토큰 카운트 테스트용 API 엔드포인트 추가
@app.post("/api/debug/tokencount")
async def debug_token_count(text: str):
    """텍스트의 토큰 수를 계산하는 디버깅 엔드포인트"""
    try:
        # 텍스트를 메시지 형식으로 변환
        test_message = {"text": text}
        
        # tiktoken으로 토큰 수 계산
        token_count = 0
        char_count = len(text)
        
        if 'tiktoken' in globals():
            encoding = tiktoken.encoding_for_model("gpt-4")
            token_count = len(encoding.encode(text))
        else:
            # 근사치 계산
            token_count = char_count // 4
        
        return {
            "text_length": char_count,
            "token_count": token_count,
            "tokens_per_char": token_count / char_count if char_count > 0 else 0,
            "using_tiktoken": 'tiktoken' in globals()
        }
    except Exception as e:
        logger.error(f"❌ 토큰 계산 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=f"토큰 계산 오류: {str(e)}")