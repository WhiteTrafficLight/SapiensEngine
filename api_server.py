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
import httpx

# Sapiens Engine 임포트
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.dialogue import DialogueFactory

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
    dialogueType: Optional[str] = "free"
    npcPositions: Optional[Dict[str, str]] = None  # 찬반토론 입장 정보 (pro/con)

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

# Socket Manager 클래스 추가 - Next.js 서버에 이벤트 전달용
class SocketManager:
    def __init__(self):
        # Next.js API URL 가져오기 (기본값: localhost:3000)
        self.nextjs_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
        logger.info(f"Socket Manager initialized with Next.js URL: {self.nextjs_url}")
    
    async def emit_to_room(self, room_id: str, event: str, data: dict):
        """Next.js Socket.IO 서버를 통해 특정 방에 이벤트 발송"""
        try:
            async with aiohttp.ClientSession() as session:
                # socket API 엔드포인트
                socket_url = f"{self.nextjs_url}/api/socket"
                
                # 이벤트 데이터 구성
                payload = {
                    "action": "broadcast",
                    "room": str(room_id),
                    "event": event,
                    "data": data
                }
                
                # API 호출
                async with session.post(
                    socket_url, 
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Socket event '{event}' emitted to room {room_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to emit socket event: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error emitting socket event: {str(e)}")
            return False

# Socket Manager 인스턴스 생성
socket_manager = SocketManager()

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
async def auto_conversation_loop(room_id, current_topic, room_data, current_npcs):
    # 초기화
    global active_auto_conversations
    
    # 실행 중인 대화가 이미 있는지 확인
    if room_id not in active_auto_conversations:
        # 초기 상태 설정
        active_auto_conversations[room_id] = {
            "running": True,
            "topic": current_topic,
            "last_user_interaction": time.time(),
            "dialogue_history": [],
            "user_question_pending": False
        }
    
    additional_context = ""
    if room_data.get("context"):
        additional_context = f"Additional context: {room_data['context']}"
    
    # 대화 패턴 타입 가져오기 (기본값: free)
    dialogue_type = room_data.get("dialogueType", "free")
    
    logger.info(f"🎭 자동 대화 시작: 방 ID {room_id}, 주제: {current_topic}, 대화 패턴: {dialogue_type}")
    
    # 대화 패턴에 따른 초기화
    if dialogue_type not in active_auto_conversations[room_id]:
        if dialogue_type == "debate":
            # 찬반토론의 경우 각 NPC에게 찬성/반대 입장 할당
            active_auto_conversations[room_id]["debate_positions"] = {}
            
            # 프론트엔드에서 전달된 입장 정보가 있다면 사용
            if "npcPositions" in room_data and room_data["npcPositions"]:
                logger.info(f"🎭 클라이언트에서 전달된 찬반토론 포지션 사용: {room_data['npcPositions']}")
                
                # 입장 정보를 debate_positions로 복사
                for npc_id, position in room_data["npcPositions"].items():
                    if npc_id in current_npcs:
                        active_auto_conversations[room_id]["debate_positions"][npc_id] = position
                
                # 입장이 지정되지 않은 NPC가 있다면 기본값 할당
                for npc in current_npcs:
                    if npc not in active_auto_conversations[room_id]["debate_positions"]:
                        # 더 적은 쪽에 배정
                        pro_count = list(active_auto_conversations[room_id]["debate_positions"].values()).count("pro")
                        con_count = list(active_auto_conversations[room_id]["debate_positions"].values()).count("con")
                        default_position = "pro" if pro_count <= con_count else "con"
                        active_auto_conversations[room_id]["debate_positions"][npc] = default_position
            else:
                # 기존 로직: 번갈아가며 찬성/반대 입장 할당
                positions = ["pro", "con"]
                position_idx = 0
                
                for npc in current_npcs:
                    active_auto_conversations[room_id]["debate_positions"][npc] = positions[position_idx % len(positions)]
                    position_idx += 1
                
            logger.info(f"🎭 찬반토론 포지션 할당: {active_auto_conversations[room_id]['debate_positions']}")
            
        elif dialogue_type == "socratic":
            # 소크라테스식 대화에서는 소크라테스가 질문 역할을 하도록 함
            active_auto_conversations[room_id]["questioner"] = "socrates" if "socrates" in current_npcs else current_npcs[0]
            active_auto_conversations[room_id]["socratic_phase"] = "question"  # question, examination, refutation
            
        elif dialogue_type == "dialectical":
            # 변증법적 대화 구조 초기화
            active_auto_conversations[room_id]["dialectical_phase"] = "thesis"  # thesis, antithesis, synthesis
            active_auto_conversations[room_id]["thesis_npc"] = None
            active_auto_conversations[room_id]["antithesis_npc"] = None
    
    # ... 기존 코드 ...
    
    try:
        while active_auto_conversations.get(room_id, {}).get("running", False):
            # ... 기존 코드 ...
            
            # 응답할 NPC 선택 - 대화 패턴에 따라 달라짐
            responding_npc_id = None
            prompt_prefix = ""
            
            if dialogue_type == "free":
                # 자유토론: 기존 방식대로 무작위 NPC 선택 (다른 조건 충족 시)
                # ... 기존 NPC 선택 로직 유지 ...
                pass
                
            elif dialogue_type == "debate":
                # 찬반토론: 이전 발언자의 반대 입장을 가진 NPC 선택
                if active_auto_conversations[room_id]["dialogue_history"]:
                    last_npc = active_auto_conversations[room_id]["dialogue_history"][-1]["npc_id"]
                    last_position = active_auto_conversations[room_id]["debate_positions"].get(last_npc)
                    
                    # 반대 입장의 NPC들을 찾음
                    opposite_position = "con" if last_position == "pro" else "pro"
                    opposing_npcs = [
                        npc for npc in current_npcs 
                        if active_auto_conversations[room_id]["debate_positions"].get(npc) == opposite_position
                    ]
                    
                    if opposing_npcs:
                        responding_npc_id = random.choice(opposing_npcs)
                        position = active_auto_conversations[room_id]["debate_positions"].get(responding_npc_id)
                        prompt_prefix = f"You are taking the {position} position on this topic. Present a strong argument for your side in response to the previous speaker."
                    else:
                        # 첫 발언은 찬성 측에서 시작
                        pro_npcs = [
                            npc for npc in current_npcs 
                            if active_auto_conversations[room_id]["debate_positions"].get(npc) == "pro"
                        ]
                        if pro_npcs:
                            responding_npc_id = random.choice(pro_npcs)
                            prompt_prefix = "You are taking the pro position on this topic. Present your initial thesis and arguments supporting it."
            
            elif dialogue_type == "socratic":
                # 소크라테스식 대화: 질문자(대개 소크라테스)와 응답자 간 번갈아가며 진행
                questioner = active_auto_conversations[room_id]["questioner"]
                phase = active_auto_conversations[room_id]["socratic_phase"]
                
                if not active_auto_conversations[room_id]["dialogue_history"] or phase == "question":
                    # 대화 시작 또는 질문 단계: 질문자가 발언
                    responding_npc_id = questioner
                    prompt_prefix = "Ask a thought-provoking question that challenges assumptions about the topic."
                    active_auto_conversations[room_id]["socratic_phase"] = "examination"
                else:
                    # 검토 단계: 질문자가 아닌 다른 NPC가 응답
                    available_npcs = [npc for npc in current_npcs if npc != questioner]
                    if available_npcs:
                        responding_npc_id = random.choice(available_npcs)
                        if phase == "examination":
                            prompt_prefix = "Respond to the question, but be aware you may need to defend your answer."
                            active_auto_conversations[room_id]["socratic_phase"] = "refutation"
                        else:  # refutation
                            prompt_prefix = "Reconsider your position in light of the critique."
                            active_auto_conversations[room_id]["socratic_phase"] = "question"
            
            elif dialogue_type == "dialectical":
                # 변증법적 대화: 주장(thesis) -> 반론(antithesis) -> 종합(synthesis)
                phase = active_auto_conversations[room_id]["dialectical_phase"]
                
                if phase == "thesis" or not active_auto_conversations[room_id]["thesis_npc"]:
                    # 주장 단계
                    responding_npc_id = random.choice(current_npcs)
                    active_auto_conversations[room_id]["thesis_npc"] = responding_npc_id
                    prompt_prefix = "Present your philosophical thesis on this topic."
                    active_auto_conversations[room_id]["dialectical_phase"] = "antithesis"
                    
                elif phase == "antithesis":
                    # 반론 단계: 주장한 NPC와 다른 NPC를 선택
                    thesis_npc = active_auto_conversations[room_id]["thesis_npc"]
                    available_npcs = [npc for npc in current_npcs if npc != thesis_npc]
                    if available_npcs:
                        responding_npc_id = random.choice(available_npcs)
                        active_auto_conversations[room_id]["antithesis_npc"] = responding_npc_id
                        prompt_prefix = "Challenge and present a counter-argument to the thesis presented earlier."
                        active_auto_conversations[room_id]["dialectical_phase"] = "synthesis"
                
                elif phase == "synthesis":
                    # 종합 단계: 주장, 반론 외의 다른 NPC 또는 주장/반론 NPC 중 하나를 선택
                    thesis_npc = active_auto_conversations[room_id]["thesis_npc"]
                    antithesis_npc = active_auto_conversations[room_id]["antithesis_npc"]
                    
                    # 종합은 제3자 또는 주장/반론 NPC 중 하나가 수행
                    synthesis_candidates = current_npcs
                    if len(current_npcs) > 2:  # 충분한 NPC가 있으면 제3자 우선
                        synthesis_candidates = [npc for npc in current_npcs if npc != thesis_npc and npc != antithesis_npc]
                    
                    if synthesis_candidates:
                        responding_npc_id = random.choice(synthesis_candidates)
                        prompt_prefix = "Synthesize the thesis and antithesis into a more comprehensive understanding."
                        # 다시 처음으로 돌아감
                        active_auto_conversations[room_id]["dialectical_phase"] = "thesis"
                        active_auto_conversations[room_id]["thesis_npc"] = None
                        active_auto_conversations[room_id]["antithesis_npc"] = None
            
            # 기존 로직으로 돌아감 - responding_npc_id가 아직 선택되지 않았다면 기본 선택 로직 수행
            if not responding_npc_id:
                # ... 기존 NPC 선택 로직 ...
                pass
                
            # NPC 정보 가져오기
            npc_info = {}
            for npc in philosophers_data:
                if npc["id"].lower() == responding_npc_id.lower():
                    npc_info = npc
                    break
            
            # ... 기존 코드 ...
            
            # 프롬프트에 대화 패턴 관련 지시 추가
            if prompt_prefix:
                additional_context = f"{prompt_prefix}\n\n{additional_context}"
            
            # ... 기존 코드 ...
            
            # "npc-selected" 이벤트 발송 - 이미 구현된 부분
            socket_manager.emit_to_room(
                room_id=str(room_id),
                event="npc-selected",
                data={"npc_id": responding_npc_id, "npc_name": npc_info.get("name", responding_npc_id)}
            )
            
            # ... 기존 코드 ...
            
    except Exception as e:
        logger.error(f"자동 대화 오류: {str(e)}", exc_info=True)
        # ... 기존 코드 ...

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
        
        # *** 새 로직: NPC 선택 즉시 소켓 이벤트 발송 ***
        try:
            # npc-selected 이벤트 발송
            async with aiohttp.ClientSession() as session:
                nextjs_api_url = os.environ.get("NEXTJS_API_URL", "http://localhost:3000")
                
                # 소켓 이벤트 데이터
                npc_selected_data = {
                    "action": "broadcast",
                    "room": request.room_id,
                    "event": "npc-selected",
                    "data": {
                        "npc_id": responding_philosopher
                    }
                }
                
                logger.info(f"NPC 선택 이벤트 발송: {responding_philosopher}")
                
                # 이벤트 전송
                npc_selected_response = await session.post(
                    f"{nextjs_api_url}/api/socket",
                    json=npc_selected_data,
                    headers={"Content-Type": "application/json"}
                )
                
                # 응답 확인
                npc_selected_status = npc_selected_response.status
                if npc_selected_status != 200:
                    logger.warning(f"NPC 선택 이벤트 발송 실패: {npc_selected_status}")
        except Exception as e:
            logger.error(f"NPC 선택 이벤트 발송 중 오류: {str(e)}")
        
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
        
        # 커스텀 NPC일 경우 다양한 방법으로 이름 조회 시도
        if is_uuid:
            # 1. MongoDB 직접 조회 시도
            try:
                # MongoDB에서 NPC 조회
                db_client = get_mongo_client()
                db = db_client[MONGO_DB]
                npc_collection = db["npcs"]
                
                # backend_id 필드로 조회
                custom_npc = npc_collection.find_one({"backend_id": id})
                
                if custom_npc:
                    logger.info(f"✅ Found custom NPC: {custom_npc.get('name', 'Unknown')}")
                    logger.info(f"   _id: {custom_npc.get('_id')}, backend_id: {id}")
                    if "portrait_url" in custom_npc:
                        logger.info(f"   portrait_url: {custom_npc.get('portrait_url')}")
                    
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
                logger.error(f"❌ MongoDB 조회 오류: {str(e)}")
                
            # 2. NextJS API를 통한 조회 시도
            try:
                # 여러 가능한 URL 시도
                possible_urls = [
                    "http://localhost:3000",       # 로컬 개발 환경
                    "http://localhost:3001",       # 대체 포트
                    "http://0.0.0.0:3000",         # 대체 호스트
                    "http://127.0.0.1:3000"        # 대체 IP
                ]
                
                for url in possible_urls:
                    try:
                        async with aiohttp.ClientSession() as session:
                            # 절대 URL 구성
                            full_url = f"{url}/api/npc/get?id={id}"
                            logger.info(f"🔄 Trying NextJS API at {full_url}")
                            
                            async with session.get(full_url, timeout=2) as response:
                                if response.status == 200:
                                    data = await response.json()
                                    if data and "name" in data and data["name"]:
                                        logger.info(f"✅ Got NPC details from NextJS: {data['name']}")
                                        
                                        # 캐시에 저장
                                        npc_cache[cache_key] = {
                                            'data': data,
                                            'timestamp': current_time
                                        }
                                        
                                        return data
                    except Exception as e:
                        logger.warning(f"❌ NextJS API 호출 실패 ({url}): {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"❌ NextJS API 조회 최종 실패: {str(e)}")
                
            # 3. 마지막 수단: 기본 응답 생성
            logger.warning(f"⚠️ 심각: 커스텀 NPC({id})의 실제 이름을 찾지 못했습니다!")
            
            # 기본 응답 생성
            default_response = {
                "id": id,
                "name": f"Unknown Philosopher",
                "description": "A custom philosopher whose details could not be retrieved.",
                "is_custom": True
            }
            
            # 캐시에 저장 (재시도 방지)
            npc_cache[cache_key] = {
                'data': default_response,
                'timestamp': current_time
            }
            
            logger.info(f"📢 기본 이름 사용: {id} -> {default_response['name']}")
            return default_response

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
        logger.info(f"Dialogue type: {request.dialogueType}")
        
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
            "isPublic": request.isPublic,
            "dialogueType": request.dialogueType
        }
        
        # 찬반토론 모드일 경우 NPC 입장 정보 추가 및 진행자 메시지 생성
        if request.dialogueType == "debate":
            # 디버깅 로그 추가
            logger.info(f"[DEBUG] 토론 모드 채팅방 생성 요청 처리 시작: {request.title}")
            
            # NPC 포지션 정보 추가
            if request.npcPositions:
                new_room["npcPositions"] = request.npcPositions
                logger.info(f"[DEBUG] 찬반토론 입장 정보 설정: {request.npcPositions}")
            else:
                # NPC 포지션 자동 배정
                npcPositions = {}
                for i, npc_id in enumerate(request.npcs):
                    npcPositions[npc_id] = "pro" if i % 2 == 0 else "con"
                new_room["npcPositions"] = npcPositions
                logger.info(f"[DEBUG] 찬반토론 입장 자동 배정: {npcPositions}")
            
            # 주제에서 찬성/반대 입장 명확화
            logger.info(f"[DEBUG] 토론 주제에서 찬성/반대 입장 명확화 시작")
            try:
                stance_statements = await generate_stance_statements(request.title, request.context)
                logger.info(f"[DEBUG] 토론 주제 입장 명확화 결과: {stance_statements}")
                
                # 진행자 오프닝 메시지 생성
                if request.generateInitialMessage:
                    try:
                        logger.info(f"[DEBUG] 진행자 오프닝 메시지 생성 시작...")
                        pro_npcs = []
                        con_npcs = []
                        
                        # NPC 분류
                        for npc_id, position in new_room["npcPositions"].items():
                            if position == "pro":
                                pro_npcs.append(npc_id)
                            else:
                                con_npcs.append(npc_id)
                        
                        logger.info(f"[DEBUG] 찬성측 NPCs: {pro_npcs}")
                        logger.info(f"[DEBUG] 반대측 NPCs: {con_npcs}")
                        
                        # NPC 이름 조회 시도
                        pro_npc_names = []
                        con_npc_names = []
                        
                        for npc_id in pro_npcs:
                            try:
                                npc_info = await get_npc_details(npc_id)
                                pro_npc_names.append(npc_info.get("name", npc_id))
                                logger.info(f"[DEBUG] NPC 정보 조회 성공: {npc_id} -> {npc_info.get('name', npc_id)}")
                            except Exception as e:
                                logger.error(f"[DEBUG] NPC 정보 조회 실패: {str(e)}")
                                pro_npc_names.append(npc_id)
                        
                        for npc_id in con_npcs:
                            try:
                                npc_info = await get_npc_details(npc_id)
                                con_npc_names.append(npc_info.get("name", npc_id))
                                logger.info(f"[DEBUG] NPC 정보 조회 성공: {npc_id} -> {npc_info.get('name', npc_id)}")
                            except Exception as e:
                                logger.error(f"[DEBUG] NPC 정보 조회 실패: {str(e)}")
                                con_npc_names.append(npc_id)
                        
                        logger.info(f"[DEBUG] 이름으로 변환된 찬성측: {pro_npc_names}")
                        logger.info(f"[DEBUG] 이름으로 변환된 반대측: {con_npc_names}")
                        
                        logger.info(f"[DEBUG_MODERATOR] generate_moderator_opening 함수 호출 직전")
                        moderator_opening = await generate_moderator_opening(
                            request.title,
                            request.context,
                            stance_statements,
                            request.npcs,
                            new_room["npcPositions"],
                            pro_npc_names,  # 새로 추가: 이름 목록 전달
                            con_npc_names   # 새로 추가: 이름 목록 전달
                        )
                        logger.info(f"[DEBUG_MODERATOR] generate_moderator_opening 함수 호출 완료")
                        
                        logger.info(f"[DEBUG_MODERATOR] 생성된 모더레이터 메시지 길이: {len(moderator_opening) if moderator_opening else 0}")
                        if moderator_opening and len(moderator_opening) > 10:  # 실제 응답 확인
                            logger.info(f"[DEBUG_MODERATOR] 생성된 모더레이터 메시지 내용: {moderator_opening[:100]}...")
                            
                            # 메시지 ID 생성
                            message_id = f"moderator-{int(time.time())}"
                            
                            # 메시지 객체 생성 - 특수 모더레이터 메시지, 항상 sender는 "Moderator"로 고정
                            message_obj = {
                                "id": message_id,
                                "text": moderator_opening,
                                "sender": "Moderator",  # 고정된 시스템 송신자명
                                "isUser": False,
                                "isSystemMessage": True,  # 시스템 메시지 표시 플래그 추가
                                "timestamp": datetime.now().isoformat(),
                                "role": "moderator"  # 명확한 역할 추가
                            }
                            
                            # 응답에 초기 메시지 포함
                            logger.info(f"[DEBUG_MODERATOR] 모더레이터 메시지 객체 생성 완료, initial_message 필드에 설정")
                            logger.info(f"[DEBUG_MODERATOR] 최종 initial_message 객체: {message_obj}")
                            logger.info(f"[DEBUG_MODERATOR] 모더레이터 메시지 텍스트: {moderator_opening}")
                            logger.info(f"[DEBUG_MODERATOR] 하드코딩된 메시지 텍스트 포함 여부: {'초기메시지에용' in moderator_opening}")
                            new_room["initial_message"] = message_obj
                            logger.info(f"[DEBUG_MODERATOR] 채팅방에 initial_message 필드가 설정됨")
                            logger.info(f"[DEBUG_MODERATOR] 테스트: 'initial_message' in new_room = {'initial_message' in new_room}")
                            logger.info(f"[DEBUG_MODERATOR] new_room 객체 키 목록: {list(new_room.keys())}")
                        else:
                            logger.warning("[DEBUG_MODERATOR] 진행자 오프닝 메시지 생성 실패 - 빈 응답 또는 짧은 응답 받음")
                            # 기본 진행자 메시지 생성
                            message_obj = {
                                "id": f"moderator-{int(time.time())}",
                                "text": f"안녕하세요, '{request.title}'에 대한 토론을 시작하겠습니다. 먼저 찬성측 참가자분들의 의견을 들어보겠습니다.",
                                "sender": "Moderator",  # 고정된 시스템 송신자명
                                "isUser": False,
                                "isSystemMessage": True,  # 시스템 메시지 표시 플래그 추가
                                "timestamp": datetime.now().isoformat(),
                                "role": "moderator"  # 명확한 역할 추가
                            }
                            logger.info(f"[DEBUG_MODERATOR] 폴백 모더레이터 메시지 객체 생성 완료, initial_message 필드에 설정")
                            new_room["initial_message"] = message_obj
                            logger.info(f"[DEBUG_MODERATOR] 폴백 메시지 사용: {message_obj['text'][:100]}...")
                    except Exception as e:
                        logger.error(f"[DEBUG] 진행자 오프닝 메시지 생성 오류: {str(e)}", exc_info=True)
                        # 기본 진행자 메시지 생성
                        message_obj = {
                            "id": f"moderator-{int(time.time())}",
                            "text": f"안녕하세요, '{request.title}'에 대한 토론을 시작하겠습니다. 먼저 찬성측 참가자분들의 의견을 들어보겠습니다.",
                            "sender": "Moderator",  # 고정된 시스템 송신자명
                            "isUser": False,
                            "isSystemMessage": True,  # 시스템 메시지 표시 플래그 추가
                            "timestamp": datetime.now().isoformat(),
                            "role": "moderator"  # 명확한 역할 추가
                        }
                        new_room["initial_message"] = message_obj
                        logger.info(f"[DEBUG] 예외 발생 후 폴백 메시지 사용: {message_obj['text'][:100]}...")
                
                # 찬반토론 모드 채팅방 생성 완료
                logger.info(f"[DEBUG] 토론 모드 채팅방 생성 완료, 응답 반환")
                return new_room
            except Exception as e:
                logger.error(f"[DEBUG] 찬반토론 처리 중 오류: {str(e)}", exc_info=True)
                # 오류 발생 시 기본 채팅방으로 계속 진행
        
        # 2. 찬반토론이 아닌 경우 기존 초기 메시지 생성 로직 실행
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
        
        # 최종 응답 객체 확인
        logger.info(f"[DEBUG_FINAL] 채팅방 반환 직전 확인: 'initial_message' in new_room = {'initial_message' in new_room}")
        if 'initial_message' in new_room:
            logger.info(f"[DEBUG_FINAL] initial_message sender: {new_room['initial_message']['sender']}")
            logger.info(f"[DEBUG_FINAL] initial_message text 미리보기: {new_room['initial_message']['text'][:100]}")
            logger.info(f"[DEBUG_FINAL] initial_message isSystemMessage: {new_room['initial_message'].get('isSystemMessage')}")
            logger.info(f"[DEBUG_FINAL] initial_message role: {new_room['initial_message'].get('role')}")
            logger.info(f"[DEBUG_FINAL] 'initial_message'가 JSON 직렬화 가능한지 확인")
            import json
            try:
                json_str = json.dumps(new_room)
                logger.info(f"[DEBUG_FINAL] JSON 직렬화 성공: 길이 {len(json_str)}")
            except Exception as json_err:
                logger.error(f"[DEBUG_FINAL] JSON 직렬화 실패: {json_err}")
        
        logger.info(f"Returning new room with ID: {new_room_id}")
        return new_room
    except Exception as e:
        logger.exception(f"Error creating chat room: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 주제에서 찬성/반대 입장 추출 함수
async def generate_stance_statements(topic: str, context: str = "") -> Dict[str, str]:
    """주제에서 찬성/반대 입장을 명확한 문장으로 추출"""
    try:
        logger.info(f"Generating stance statements for topic: {topic}")
        
        system_prompt = """
        You are a debate preparation assistant. Your task is to analyze the given topic and create clear stance statements for both PRO and CON positions.
        Format your response as JSON with the following structure:
        {
            "pro_statement": "Clear statement supporting the position...",
            "con_statement": "Clear statement opposing the position..."
        }
        Keep each statement concise (1-2 sentences) and strongly articulated.
        """
        
        user_prompt = f"Topic: {topic}\n\nContext: {context}"
        
        # LLM API 호출
        response = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider="openai",
            llm_model="gpt-4o"
        )
        
        # JSON 응답 파싱
        import json
        try:
            result = json.loads(response)
            pro_statement = result.get("pro_statement", "")
            con_statement = result.get("con_statement", "")
            
            logger.info(f"Generated stance statements - PRO: {pro_statement}, CON: {con_statement}")
            
            return {
                "pro": pro_statement,
                "con": con_statement
            }
        except json.JSONDecodeError:
            logger.error(f"Failed to parse stance statements JSON: {response}")
            # 기본값 반환
            return {
                "pro": f"{topic} is true and beneficial.",
                "con": f"{topic} is false and harmful."
            }
    except Exception as e:
        logger.error(f"Error generating stance statements: {str(e)}")
        return {
            "pro": f"{topic} is true and beneficial.",
            "con": f"{topic} is false and harmful."
        }

# 진행자 오프닝 메시지 생성 함수
async def generate_moderator_opening(
    topic: str, 
    context: str = "", 
    stance_statements: Dict[str, str] = None,
    participants: List[str] = None,
    positions: Dict[str, str] = None,
    pro_participants: List[str] = None,  # 이름 변경: 찬성측 참가자들(NPC + 유저)
    con_participants: List[str] = None   # 이름 변경: 반대측 참가자들(NPC + 유저)
) -> str:
    """토론 주제에 대한 진행자 오프닝 메시지 생성 - LLM을 사용한 자연스러운 진행자 메시지
    
    Args:
        topic: 토론 주제
        context: 추가 컨텍스트
        stance_statements: 찬반 입장 문장 (pro/con)
        participants: 전체 참가자 목록
        positions: 참가자 포지션 매핑
        pro_participants: 찬성측 참가자 목록 (NPC와 유저 모두 포함)
        con_participants: 반대측 참가자 목록 (NPC와 유저 모두 포함)
    """
    try:
        logger.info(f"[MODERATOR_OPENING] 진행자 메시지 생성 시작! 주제: {topic}")
        logger.info(f"[MODERATOR_OPENING] 찬성측 참가자: {pro_participants}")
        logger.info(f"[MODERATOR_OPENING] 반대측 참가자: {con_participants}")
        
        # 이름 문자열 생성 (참가자 = NPC + User)
        pro_names_str = ", ".join(pro_participants) if pro_participants else "찬성측"
        con_names_str = ", ".join(con_participants) if con_participants else "반대측"
        
        logger.info(f"[MODERATOR_OPENING] 찬성측 이름 문자열: {pro_names_str}")
        logger.info(f"[MODERATOR_OPENING] 반대측 이름 문자열: {con_names_str}")
        
        # 첫 번째 찬성측 참가자의 이름 (첫 번째 발언자)
        first_pro_name = pro_participants[0] if pro_participants else "찬성측"
        
        # 주제 언어 감지
        topic_language = detect_language(topic)
        logger.info(f"[MODERATOR_OPENING] 감지된 주제 언어: {topic_language}")
        
        # LLM을 사용한 모더레이터 메시지 생성
        system_prompt = f"""
        You are a professional debate moderator. Your task is to create a detailed, natural-sounding opening statement for a debate on the given topic.

        IMPORTANT: If the topic is in Korean, you MUST write your ENTIRE response in Korean. If the topic is in English, write in English.
        (The detected language of the topic is: {topic_language})

        Write as if you are speaking directly to the participants and audience. Be engaging, clear, and structured.

        Your opening statement should include:
        1. A warm welcome and clear introduction of the debate topic
        2. Brief explanation of the context/background (if provided)
        3. Clear explanation of both PRO and CON positions in a balanced way
        4. Introduction of ALL participants by name on each side - IMPORTANT: Use the EXACT participant names provided, including both NPCs and human users
        5. Brief explanation of debate format and rules
        6. Encouragement for respectful, thoughtful exchange
        7. A specific invitation for the first pro-side speaker to begin (use their exact name)

        Make your statement conversational and natural, like how a real moderator would speak.
        Avoid using formulaic language - each debate opening should feel unique and tailored to the specific topic.
        
        IMPORTANT: Never mention internal IDs like "User123". Only use the display names provided in the participant lists.
        """
        
        user_prompt = f"""
        DEBATE TOPIC: {topic}

        CONTEXT: {context if context and context.strip() else "No additional context provided."}

        PRO POSITION: {stance_statements.get('pro', f"Supporting the idea that {topic}") if stance_statements else f"Supporting the idea that {topic}"}

        CON POSITION: {stance_statements.get('con', f"Opposing the idea that {topic}") if stance_statements else f"Opposing the idea that {topic}"}

        PRO SIDE PARTICIPANTS: {pro_names_str}
        CON SIDE PARTICIPANTS: {con_names_str}

        FIRST SPEAKER TO INVITE: {first_pro_name}

        IMPORTANT: When introducing participants, use their exact names as provided above.
        Do not refer to them by IDs or modify their names in any way.
        Make sure to include EVERY participant in your introduction, both NPCs and human users.
        
        CRITICAL: NEVER mention internal user IDs like "User123" in your response. Only use the display names listed above.

        Remember: The ENTIRE response must be in the language of the topic.
        If the topic contains "vs" or "versus", create a lively comparison-style debate introduction.

        Create a complete, natural-sounding moderator opening that a real person would use to start this debate.
        """
        
        # LLM API 호출
        moderator_message = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider="openai",
            llm_model="gpt-4o",
            temperature=0.7  # 'language' 파라미터 대신 temperature 파라미터 사용
        )
        
        logger.info(f"[MODERATOR_OPENING] LLM으로 생성된 모더레이터 메시지: {moderator_message[:100]}...")
        return moderator_message
    except Exception as e:
        logger.error(f"[MODERATOR_OPENING] 오류 발생: {str(e)}")
        # 오류 발생 시 더 자세한 기본 메시지 반환
        fallback_message = (
            f"안녕하세요, 오늘의 토론 주제는 \"{topic}\"입니다. "
            f"저는 이번 토론의 진행을 맡게 된 모더레이터입니다. "
        )
        
        # 컨텍스트 정보가 있으면 추가
        if context and context.strip():
            fallback_message += f"토론 배경: {context}\n\n"
        
        # 찬성/반대 입장 추가
        if stance_statements and "pro" in stance_statements:
            fallback_message += f"찬성 입장: {stance_statements['pro']}\n"
        
        if stance_statements and "con" in stance_statements:
            fallback_message += f"반대 입장: {stance_statements['con']}\n\n"
        
        # 참가자 소개
        fallback_message += f"찬성측 참가자: {pro_names_str}\n"
        fallback_message += f"반대측 참가자: {con_names_str}\n\n"
        
        # 토론 진행 방식 안내
        fallback_message += (
            f"토론은 찬성측의 주장으로 시작하여, 이후 반대측의 반론 순으로 진행됩니다. "
            f"각자의 논점을 명확히 하고 상대방의 의견을 존중하며 진행해 주시기 바랍니다.\n\n"
            f"먼저 {first_pro_name} 측에서 찬성 입장을 개진해 주시기 바랍니다."
        )
        
        return fallback_message

# 언어 감지 함수 추가
def detect_language(text: str) -> str:
    """텍스트의 언어를 감지합니다."""
    try:
        # ASCII 문자만 있으면 영어로 간주
        if all(ord(c) < 128 for c in text):
            return "en"
        
        # 한글이 포함되어 있으면 한국어로 간주
        if any('\uAC00' <= c <= '\uD7A3' for c in text):
            return "ko"
        
        # 일본어 문자가 포함되어 있으면 일본어로 간주
        if any('\u3040' <= c <= '\u30FF' for c in text):
            return "ja"
        
        # 중국어 문자가 포함되어 있으면 중국어로 간주
        if any('\u4E00' <= c <= '\u9FFF' for c in text):
            return "zh"
        
        # 기본값은 영어
        return "en"
    except Exception as e:
        logger.error(f"언어 감지 중 오류: {str(e)}")
        return "en"  # 오류 발생 시 기본값은 영어

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

# ==========================================
# 대화 형식 관련 엔드포인트
# ==========================================

# 대화 형식 객체 캐시
dialogue_instances = {}

@app.get("/api/dialogue/types")
async def get_dialogue_types():
    """사용 가능한 대화 형식 목록 반환"""
    return DialogueFactory.get_available_types()

@app.get("/api/dialogue/{room_id}/state")
async def get_dialogue_state(room_id: str):
    """채팅방의 현재 대화 상태 조회"""
    # 채팅방 정보 조회
    room = await get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    
    # 대화 형식 확인
    dialogue_type = room.get("dialogueType", "standard")
    
    # 해당 대화 객체 가져오기 또는 생성
    dialogue = _get_or_create_dialogue(room_id, dialogue_type, room)
    
    # 대화 상태 반환
    return dialogue.get_dialogue_state()

@app.post("/api/dialogue/{room_id}/next-speaker")
async def get_next_speaker(room_id: str):
    """다음 발언자 정보 조회"""
    # 채팅방 정보 조회
    room = await get_room_data(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    
    # 대화 형식 확인
    dialogue_type = room.get("dialogueType", "standard")
    logger.info(f"[DEBUG] next-speaker 요청 - Room: {room_id}, Type: {dialogue_type}")
    
    # 해당 대화 객체 가져오기 또는 생성
    dialogue = _get_or_create_dialogue(room_id, dialogue_type, room)
    
    # 다음 발언자 정보 반환
    next_speaker = dialogue.get_next_speaker()
    
    # 디버그 로깅
    logger.info(f"[DEBUG] next-speaker 응답 - ID: {next_speaker.get('speaker_id')}, Role: {next_speaker.get('role')}")
    logger.info(f"[DEBUG] 현재 speaking_history 길이: {len(dialogue.debate_state.get('speaking_history', []))}")
    
    # 현재 발언 기록 로깅 (마지막 5개)
    if dialogue_type == "debate" and hasattr(dialogue, 'debate_state'):
        history = dialogue.debate_state.get('speaking_history', [])
        last_5 = history[-5:] if len(history) >= 5 else history
        logger.info(f"[DEBUG] 최근 5개 발언 기록: {last_5}")
    
    # 소켓 서버를 통해 다음 발언자 정보 브로드캐스트
    try:
        if socket_manager:
            # 소켓 이벤트 발송 - 다음 발언자 정보
            event_data = {
                "roomId": room_id,
                "nextSpeaker": next_speaker
            }
            await socket_manager.emit_to_room(room_id, "next-speaker-update", event_data)
            logger.info(f"[DEBUG] 소켓 이벤트 발송 - next-speaker-update: {next_speaker.get('speaker_id')}, is_user: {next_speaker.get('is_user', False)}")
    except Exception as e:
        logger.error(f"[ERROR] 소켓 이벤트 발송 실패: {str(e)}")
    
    return next_speaker

@app.post("/api/dialogue/{room_id}/generate")
async def generate_dialogue_response(
    room_id: str, 
    request: Dict[str, Any] = Body(...)
):
    """대화 형식에 맞는 AI 응답 생성"""
    context = request.get("context", {})
    
    # 클라이언트에서 전달된 npc_id 사용
    npc_id = request.get("npc_id")
    if not npc_id:
        logger.warning(f"No npc_id provided in request for room {room_id}")
    else:
        logger.info(f"Using provided npc_id: {npc_id} for room {room_id}")
    
    # 채팅방 정보 조회
    room = await get_room_data(room_id)
    if not room:
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    
    # 대화 형식 확인
    dialogue_type = room.get("dialogueType", "standard")
    
    # 해당 대화 객체 가져오기 또는 생성
    dialogue = _get_or_create_dialogue(room_id, dialogue_type, room)
    
    # 최근 메시지 가져오기 (context에 없는 경우)
    if "recent_messages" not in context and room.get("messages"):
        messages = room["messages"]
        context["recent_messages"] = messages[-5:] if len(messages) > 5 else messages
    
    # 대화 형식에 맞는 응답 생성
    response_info = dialogue.generate_response(context)
    
    # 응답 생성에 필요한 정보 추출
    # 클라이언트가 제공한 npc_id가 있으면 그것을 사용, 없으면 대화 시스템이 결정한 speaker_id 사용
    speaker_id = npc_id if npc_id else response_info.get("speaker_id")
    speaker_role = response_info.get("speaker_role")
    prompt = response_info.get("prompt")
    
    logger.info(f"Generating response for speaker: {speaker_id} in room {room_id}")
    
    # 실제 응답 생성 (기존 생성 로직 활용)
    ai_response = await generate_ai_response(room_id, speaker_id, prompt)
    
    # 생성된 응답과 대화 정보 합치기
    combined_response = {
        **response_info,
        "response_text": ai_response.get("text", ""),
        "timestamp": ai_response.get("timestamp", time.time())
    }
    
    # 토론 객체의 speaking_history 업데이트
    if dialogue_type == "debate":
        try:
            # 디버그: 업데이트 전 상태 로깅
            logger.info(f"[DEBUG] 업데이트 전 speaking_history: {dialogue.debate_state.get('speaking_history', [])}")
            logger.info(f"[DEBUG] 업데이트 전 turn_count: {dialogue.debate_state.get('turn_count', 0)}")
                
            # turn_count 증가
            dialogue.debate_state["turn_count"] += 1
            
            # speaking_history에 새 메시지 추가
            dialogue.debate_state["speaking_history"].append({
                "speaker_id": speaker_id,
                "role": speaker_role,
                "timestamp": time.time(),
                "stage": dialogue.debate_state["current_stage"]
            })
            
            # 단계 전환 체크
            dialogue._check_stage_transition()
            
            # 다음 발언자 결정
            next_speaker = dialogue.get_next_speaker()
            dialogue.debate_state["next_speaker"] = next_speaker["speaker_id"]
            
            # 디버그: 업데이트 후 상태 로깅
            logger.info(f"[DEBUG] 업데이트 후 speaking_history: {dialogue.debate_state.get('speaking_history', [])}")
            logger.info(f"[DEBUG] 업데이트 후 turn_count: {dialogue.debate_state.get('turn_count', 0)}")
            logger.info(f"[DEBUG] 다음 발언자: {dialogue.debate_state['next_speaker']} (역할: {next_speaker['role']})")
            
            logger.info(f"Updated debate state for room {room_id}: turn_count={dialogue.debate_state['turn_count']}, next_speaker={dialogue.debate_state['next_speaker']}")
        except Exception as e:
            logger.error(f"Error updating debate state: {str(e)}", exc_info=True)
    
    return combined_response

@app.post("/api/dialogue/{room_id}/process-message")
async def process_dialogue_message(
    room_id: str, 
    request: Dict[str, Any] = Body(...)
):
    """사용자 메시지 처리 및 대화 상태 업데이트"""
    message = request.get("message", "")
    user_id = request.get("user_id", "")
    role = request.get("role", "")  # 사용자 역할 정보 (pro, con 등)
    
    logger.info(f"⭐ [DEBUG] Processing message for room {room_id}: user_id={user_id}, role={role}")
    logger.info(f"⭐ [DEBUG] Message content: {message[:100]}..." if len(message) > 100 else f"⭐ [DEBUG] Message content: {message}")
    
    # 채팅방 정보 조회
    room = await get_room_data(room_id)
    if not room:
        logger.error(f"❌ Room {room_id} not found")
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    
    # 대화 형식 확인
    dialogue_type = room.get("dialogueType", "standard")
    logger.info(f"⭐ [DEBUG] Room dialogue type: {dialogue_type}")
    
    # 해당 대화 객체 가져오기 또는 생성
    dialogue = _get_or_create_dialogue(room_id, dialogue_type, room)
    
    # 역할을 강제로 지정한 경우 사용하고, 그렇지 않으면 객체에서 결정
    if role and role.lower() in ["pro", "con", "neutral"]:
        logger.info(f"⭐ [DEBUG] Using client-specified role: {role} for user {user_id}")
        user_role = role.lower()
    else:
    # 메시지 처리
        user_role = dialogue._get_user_role(user_id)
        logger.info(f"⭐ [DEBUG] Determined role from dialogue: {user_role} for user {user_id}")
    
    # 현재 대화 상태 기록
    logger.info(f"⭐ [DEBUG] 대화 상태 업데이트 전: turn_count={dialogue.debate_state.get('turn_count', 0)}, speaking_history 길이={len(dialogue.debate_state.get('speaking_history', []))}")
    logger.info(f"⭐ [DEBUG] Current speaking order: {[entry.get('speaker_id') for entry in dialogue.debate_state.get('speaking_history', [])]}")
    
    # 토론 진행 상태 업데이트
    dialogue.debate_state["turn_count"] += 1
    dialogue.debate_state["speaking_history"].append({
        "speaker_id": user_id,
        "role": user_role,  # 클라이언트에서 지정한 역할 또는 객체에서 결정된 역할 사용
        "timestamp": time.time(),
        "stage": dialogue.debate_state["current_stage"]
    })
    
    # 단계 전환 체크
    dialogue._check_stage_transition()
    
    # 다음 발언자 결정
    next_speaker = dialogue.get_next_speaker()
    dialogue.debate_state["next_speaker"] = next_speaker["speaker_id"]
    
    logger.info(f"⭐ [DEBUG] After user message: next speaker is {next_speaker['speaker_id']} ({next_speaker['role']})")
    
    # 디버그: 업데이트 후 상태 로깅
    logger.info(f"⭐ [DEBUG] 업데이트 후 speaking_history: {[entry.get('speaker_id') for entry in dialogue.debate_state.get('speaking_history', [])]}")
    logger.info(f"⭐ [DEBUG] 업데이트 후 turn_count: {dialogue.debate_state.get('turn_count', 0)}")
    logger.info(f"⭐ [DEBUG] 다음 발언자: {dialogue.debate_state.get('next_speaker', 'None')} (역할: {next_speaker.get('role', 'unknown')})")
    
    # 사용자 메시지가 처리되었음을 Next.js API에 알리기 위한 이벤트 발송
    try:
        # Socket.io 이벤트 발송
        await emit_socket_event(
            room_id=room_id,
            event="user-message-processed",
            data={
                "user_id": user_id,
                "role": user_role,
                "next_speaker": next_speaker,
                "processed_timestamp": time.time()
            }
        )
        logger.info(f"⭐ [DEBUG] Socket event 'user-message-processed' emitted to room {room_id}")
    except Exception as e:
        logger.error(f"[ERROR] 소켓 이벤트 발송 실패: {str(e)}")
    
    # 다음 발언자 업데이트를 위한 소켓 이벤트 발송
    try:
        is_user_next = next_speaker.get("is_user", False)
        
        # Socket.io 이벤트 발송
        await emit_socket_event(
            room_id=room_id,
            event="next-speaker-update",
            data={
                "roomId": room_id,
                "nextSpeaker": next_speaker
            }
        )
        logger.info(f"⭐ [DEBUG] Socket event 'next-speaker-update' emitted to room {room_id}, next speaker: {next_speaker['speaker_id']}, is_user: {is_user_next}")
    except Exception as e:
        logger.error(f"[ERROR] 소켓 이벤트 발송 실패: {str(e)}")
    
    # 사용자 메시지를 데이터베이스에 저장하기 위한 함수 호출 (MongoDB API 사용)
    try:
        save_result = await save_message_to_mongodb(
            room_id=room_id,
            message_text=message,
            sender=user_id,
            is_user=True,
            role=user_role
        )
        logger.info(f"⭐ [DEBUG] 사용자 메시지 DB 저장 결과: {save_result}")
    except Exception as e:
        logger.error(f"[ERROR] 사용자 메시지 DB 저장 실패: {str(e)}")
    
    return {
        "processed": True,
        "user_id": user_id,
        "user_role": user_role,
        "message": message,
        "dialogue_type": dialogue.dialogue_type,
        "debate_stage": dialogue.debate_state["current_stage"],
        "next_speaker": next_speaker
    }

def _get_or_create_dialogue(room_id: str, dialogue_type: str, room_data: Dict[str, Any]) -> Any:
    """대화 객체 가져오기 또는 생성"""
    try:
        # 캐시에서 객체 확인
        cache_key = f"{room_id}_{dialogue_type}"
        
        # 디버그: 기존 캐시 로깅
        if 'dialogue_instances' in globals():
            logger.info(f"[DEBUG] 현재 캐싱된 dialogue_instances 키 목록: {list(dialogue_instances.keys())}")
        else: 
            logger.warning("[DEBUG] dialogue_instances가 전역 변수로 정의되지 않았습니다.")
            globals()['dialogue_instances'] = {}
            
        if cache_key in dialogue_instances:
            # 기존 인스턴스 재사용
            instance = dialogue_instances[cache_key]
            logger.info(f"[DEBUG] 캐시된 dialogue 인스턴스 사용 ({cache_key})")
            
            # 인스턴스 상태 검증
            if hasattr(instance, 'debate_state'):
                logger.info(f"[DEBUG] 캐시된 인스턴스 상태 - turn_count: {instance.debate_state.get('turn_count', 'N/A')}")
                logger.info(f"[DEBUG] 캐시된 인스턴스 상태 - speaking_history 길이: {len(instance.debate_state.get('speaking_history', []))}")
                logger.info(f"[DEBUG] 캐시된 인스턴스 상태 - current_stage: {instance.debate_state.get('current_stage', 'N/A')}")
            
            return instance
        
        # 객체 생성 전 로깅
        logger.info(f"[DEBUG] 새로운 dialogue 인스턴스 생성 필요 ({cache_key})")
        
        # 사용 가능한 대화 타입 가져오기 - 디버깅용
        available_types = DialogueFactory.get_available_types()
        logger.info(f"Available dialogue types: {list(available_types.keys())}")
        
        # 대화 타입이 유효하지 않은 경우 기본값으로 변경
        if dialogue_type not in available_types:
            logger.warning(f"Invalid dialogue type: {dialogue_type}, falling back to 'standard'")
            dialogue_type = "standard"
        
        # 객체 생성
        dialogue = DialogueFactory.create_dialogue(dialogue_type, room_id, room_data)
        
        # 생성 결과 로깅
        logger.info(f"[DEBUG] 새 인스턴스 생성됨: {type(dialogue).__name__}")
        
        # 인스턴스 초기 상태 로깅
        if hasattr(dialogue, 'debate_state'):
            logger.info(f"[DEBUG] 새 인스턴스 초기 상태 - turn_count: {dialogue.debate_state.get('turn_count', 'N/A')}")
            logger.info(f"[DEBUG] 새 인스턴스 초기 상태 - speaking_history 길이: {len(dialogue.debate_state.get('speaking_history', []))}")
            logger.info(f"[DEBUG] 새 인스턴스 초기 상태 - current_stage: {dialogue.debate_state.get('current_stage', 'N/A')}")
        
        # 캐시에 저장
        dialogue_instances[cache_key] = dialogue
        logger.info(f"[DEBUG] 새 인스턴스를 캐시에 저장 ({cache_key})")
        
        return dialogue
    
    except Exception as e:
        logger.error(f"Error creating dialogue instance: {str(e)}")
        logger.exception("Detailed error:")
        
        # 오류 발생 시 StandardDialogue 사용
        from sapiens_engine.dialogue.standard_dialogue import StandardDialogue
        logger.warning(f"Falling back to StandardDialogue for room {room_id}")
        
        # 기본 객체 생성
        fallback_dialogue = StandardDialogue(room_id, room_data)
        
        # 캐시에 저장
        cache_key = f"{room_id}_standard"
        dialogue_instances[cache_key] = fallback_dialogue
        
        return fallback_dialogue

# 새로운 AI 응답 생성 함수
async def generate_ai_response(room_id: str, speaker_id: str, prompt: str) -> Dict[str, Any]:
    """
    대화 시스템을 위한 AI 응답 생성
    
    Args:
        room_id: 채팅방 ID
        speaker_id: 응답할 NPC ID
        prompt: 응답 생성을 위한 프롬프트
    
    Returns:
        Dictionary containing the response text and metadata
    """
    try:
        logger.info(f"[DIALOGUE] AI 응답 생성 시작: speaker_id={speaker_id}, room_id={room_id}")
        logger.info(f"[DIALOGUE] 프롬프트: {prompt[:100]}...")
        
        # 채팅방 정보 조회
        room = await get_room_data(room_id)
        if not room:
            logger.error(f"[DIALOGUE] 채팅방 정보를 찾을 수 없음: {room_id}")
            return {"text": "I cannot respond at this time.", "timestamp": time.time()}
        
        # NPC ID 검증 - 잘못된 NPC ID면 처리할 수 없음
        if not speaker_id:
            logger.error(f"[DIALOGUE] 유효하지 않은 NPC ID: {speaker_id}")
            return {"text": "Invalid speaker ID", "timestamp": time.time()}
            
        # NPC 이름 조회
        try:
            npc_info = await get_npc_details(speaker_id)
            npc_name = npc_info.get("name", speaker_id)
            logger.info(f"[DIALOGUE] NPC 이름 조회 성공: {speaker_id} -> {npc_name}")
        except Exception as e:
            logger.warning(f"[DIALOGUE] NPC 이름 조회 실패: {str(e)}")
            npc_name = speaker_id
        
        # ChatGenerateRequest 객체 생성
        request = ChatGenerateRequest(
            room_id=room_id,
            npcs=[speaker_id],  # 응답할 NPC만 지정
            user_message=prompt,  # 프롬프트를 사용자 메시지로 사용
            topic=room.get("title", ""),
            context=room.get("context", ""),
            llm_provider="openai",  # 기본값
            llm_model="gpt-4o"  # 기본값
        )
        
        # generate_chat_response 함수 호출
        logger.info(f"[DIALOGUE] generate_chat_response 함수 호출 직전")
        response_data = await generate_chat_response(request)
        logger.info(f"[DIALOGUE] generate_chat_response 응답 받음: {len(response_data.get('response', ''))} 글자")
        
        # 응답 데이터 구성
        message_id = f"ai-{int(time.time() * 1000)}"
        result = {
            "id": message_id,
            "text": response_data.get("response", ""),
            "sender": npc_name,  # 화면 표시용 이름 사용
            "npc_id": speaker_id,  # 원본 NPC ID 유지 (내부 참조용)
            "isUser": False,
            "timestamp": datetime.now().isoformat(),
            "metadata": response_data.get("metadata", {}),
            "citations": response_data.get("citations", [])
        }
        
        # 메시지 저장
        try:
            logger.info(f"[DIALOGUE] 메시지 DB 저장 시작: {message_id}")
            saved = await save_message_to_db(room_id, result)
            if saved:
                logger.info(f"[DIALOGUE] 메시지 DB 저장 성공: {message_id}")
            else:
                logger.warning(f"[DIALOGUE] 메시지 DB 저장 실패: {message_id}")
        except Exception as e:
            logger.error(f"[DIALOGUE] 메시지 저장 중 오류: {str(e)}")
        
        logger.info(f"[DIALOGUE] AI 응답 생성 완료: {result['text'][:50]}...")
        return result
        
    except Exception as e:
        logger.error(f"[DIALOGUE] AI 응답 생성 오류: {str(e)}")
        # 오류 스택 트레이스 출력
        logger.exception("상세 오류:")
        # 기본 응답 반환
        return {
            "id": f"error-{int(time.time() * 1000)}",
            "text": "I apologize, but I cannot provide a proper response at this time.",
            "sender": speaker_id,
            "isUser": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# 모더레이터 오프닝 메시지 요청 모델
class ModeratorOpeningRequest(BaseModel):
    title: str
    room_id: Optional[str] = None  # 필수 필드를 Optional로 변경
    context: Optional[str] = ""
    npcs: List[str]
    npcPositions: Dict[str, str]
    proNpcIds: List[str]
    conNpcIds: List[str]
    npcNames: Optional[Dict[str, str]] = None  # NPC ID -> 이름 매핑
    userData: Optional[Dict[str, str]] = None  # 유저 ID -> 이름 매핑

# NPC 이름을 여러 소스에서 적절히.가져오는 유틸리티 함수
async def get_proper_npc_name(npc_id: str, name_mapping: Dict[str, str], nextjs_url: str = None) -> str:
    """NPC의 실제 이름을 여러 소스에서 조회하여 가져옵니다"""
    try:
        # 기본 NextJS URL 설정 (인자로 받지 않은 경우)
        if not nextjs_url:
            nextjs_url = "http://localhost:3000"  # NextJS 서버 기본 URL
            
        logger.info(f"[NPC_NAME] NPC 이름 조회 시작: {npc_id}")
            
        # 1. 먼저 이름 매핑에서 이름 찾기
        if name_mapping and npc_id in name_mapping:
            name = name_mapping[npc_id]
            if name and isinstance(name, str) and len(name.strip()) > 0:
                logger.info(f"[NPC_NAME] 매핑에서 이름 찾음: {npc_id} -> {name}")
                return name
        
        # 2. NextJS API에서 커스텀 NPC 이름 직접 조회 (MongoDB 데이터 활용)
        if len(npc_id) > 30 and '-' in npc_id:  # UUID 형태 감지
            # 여러 가능한 URL 시도
            possible_urls = [
                nextjs_url,                    # 기본 URL (인자로 전달된 것)
                "http://localhost:3000",       # 로컬 개발 환경
                "http://localhost:3001",       # 대체 포트
                "http://0.0.0.0:3000",         # 대체 호스트
                "http://127.0.0.1:3000"        # 대체 IP
            ]
            
            # 중복 제거
            possible_urls = list(set(possible_urls))
            logger.info(f"[NPC_NAME] 시도할 URL 목록: {possible_urls}")
            
            for url in possible_urls:
                try:
                    async with aiohttp.ClientSession() as session:
                        # 절대 URL 구성
                        full_url = f"{url}/api/npc/get?id={npc_id}"
                        logger.info(f"[NPC_NAME] NextJS API 호출: {full_url}")
                        
                        async with session.get(full_url, timeout=2) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data and "name" in data and data["name"]:
                                    logger.info(f"[NPC_NAME] NextJS API에서 커스텀 NPC 이름 찾음: {npc_id} -> {data['name']} (URL: {url})")
                                    return data["name"]
                                else:
                                    logger.warning(f"[NPC_NAME] NextJS API 응답에 name 필드 없음: {data}")
                            else:
                                logger.warning(f"[NPC_NAME] NextJS API 응답 오류: {response.status} (URL: {url})")
                except Exception as e:
                    logger.error(f"[NPC_NAME] NextJS API 호출 오류 ({url}): {str(e)}")
                    # 실패해도 계속 다음 URL 시도
                    continue
        
        # 3. 내부 API로 NPC 상세 정보 조회
        try:
            npc_info = await get_npc_details(npc_id)
            if npc_info and "name" in npc_info and npc_info["name"]:
                logger.info(f"[NPC_NAME] 내부 API에서 이름 찾음: {npc_id} -> {npc_info['name']}")
                return npc_info["name"]
        except Exception as e:
            logger.error(f"[NPC_NAME] 내부 API 호출 오류: {str(e)}")
        
        # 4. 기본 철학자 이름 하드코딩
        philosopher_names = {
            "socrates": "Socrates",
            "plato": "Plato",
            "aristotle": "Aristotle",
            "kant": "Kant",
            "nietzsche": "Friedrich Nietzsche",
            "marx": "Karl Marx",
            "sartre": "Jean-Paul Sartre",
            "camus": "Albert Camus", 
            "beauvoir": "Simone de Beauvoir",
            "confucius": "Confucius",
            "heidegger": "Martin Heidegger",
            "kierkegaard": "Søren Kierkegaard",
            "wittgenstein": "Ludwig Wittgenstein",
            "hume": "David Hume"
        }
        
        if npc_id.lower() in philosopher_names:
            name = philosopher_names[npc_id.lower()]
            logger.info(f"[NPC_NAME] 기본 철학자 이름 사용: {npc_id} -> {name}")
            return name
        
        # 5. UUID 형태인 경우 더 친숙한 이름 형태로 반환
        if len(npc_id) > 30 and '-' in npc_id:
            logger.warning(f"[NPC_NAME] 커스텀 NPC({npc_id})의 실제 이름을 찾지 못했습니다!")
            custom_name = f"Unknown Custom NPC"
            logger.warning(f"[NPC_NAME] UUID 형태 이름 대체: {npc_id} -> {custom_name}")
            return custom_name
        
        # 6. 마지막 대안: ID의 첫 글자를 대문자로 변환
        default_name = npc_id.capitalize()
        logger.warning(f"[NPC_NAME] 기본 이름 사용: {npc_id} -> {default_name}")
        return default_name
    
    except Exception as e:
        logger.error(f"[NPC_NAME] 이름 조회 중 오류 발생: {str(e)}")
        # 안전장치: 절대 오류가 나지 않도록 항상 문자열 반환
        return npc_id


# 모더레이터 메시지 전용 엔드포인트 추가
@app.post("/api/moderator/opening")
async def create_moderator_opening(request: ModeratorOpeningRequest):
    try:
        logger.info("[MODERATOR_ENDPOINT] 모더레이터 오프닝 메시지 생성 요청")
        logger.info(f"[MODERATOR_ENDPOINT] 요청 데이터: {request}")
        
        # 필수 필드 검증
        if not request.title:
            logger.error("[MODERATOR_ENDPOINT] 제목 누락")
            raise HTTPException(status_code=400, detail="토론 제목이 필요합니다")
        
        # NextJS URL 설정
        nextjs_url = "http://localhost:3000"  # NextJS 서버 URL
        
        # 사용자 ID -> 표시 이름 매핑 생성 (예: User123 -> WhiteTrafficLight)
        user_display_names = {}
        if request.userData:
            for user_id, display_name in request.userData.items():
                user_display_names[user_id] = display_name
                logger.info(f"[MODERATOR_ENDPOINT] 사용자 매핑: {user_id} -> {display_name}")
        
        # 찬성 측 참가자 목록 (표시 이름만 포함)
        pro_names = []
        
        # 찬성 측 처리 - 유저 ID는 표시 이름으로 대체, NPC ID는 이름으로 대체
        for participant_id in request.proNpcIds:
            # 유저인지 확인
            if request.userData and participant_id in request.userData:
                display_name = request.userData[participant_id]
                pro_names.append(display_name)
                logger.info(f"[MODERATOR_ENDPOINT] 찬성 측 유저 추가: {display_name} (ID: {participant_id})")
            else:
                # NPC인 경우 이름 가져오기
                npc_name = await get_proper_npc_name(participant_id, request.npcNames or {}, nextjs_url)
                pro_names.append(npc_name)
                logger.info(f"[MODERATOR_ENDPOINT] 찬성 측 NPC 추가: {npc_name} (ID: {participant_id})")
        
        # 반대 측 참가자 목록 (표시 이름만 포함)
        con_names = []
        
        # 반대 측 처리 - 유저 ID는 표시 이름으로 대체, NPC ID는 이름으로 대체
        for participant_id in request.conNpcIds:
            # 유저인지 확인
            if request.userData and participant_id in request.userData:
                display_name = request.userData[participant_id]
                con_names.append(display_name)
                logger.info(f"[MODERATOR_ENDPOINT] 반대 측 유저 추가: {display_name} (ID: {participant_id})")
            else:
                # NPC인 경우 이름 가져오기
                npc_name = await get_proper_npc_name(participant_id, request.npcNames or {}, nextjs_url)
                con_names.append(npc_name)
                logger.info(f"[MODERATOR_ENDPOINT] 반대 측 NPC 추가: {npc_name} (ID: {participant_id})")
        
        # 참가자 검증
        if not pro_names or not con_names:
            logger.error("[MODERATOR_ENDPOINT] 찬성과 반대 측 모두 참가자가 있어야 합니다")
            raise HTTPException(status_code=400, detail="찬성과 반대 측 모두 참가자가 있어야 합니다")
        
        logger.info(f"[MODERATOR_ENDPOINT] 최종 찬성 측 명단: {', '.join(pro_names)}")
        logger.info(f"[MODERATOR_ENDPOINT] 최종 반대 측 명단: {', '.join(con_names)}")
        
        # 모더레이터 오프닝 메시지 생성
        opening_message = await generate_moderator_opening(
            topic=request.title,
            context=request.context or "",
            pro_participants=pro_names,
            con_participants=con_names
        )
        
        logger.info("[MODERATOR_ENDPOINT] 모더레이터 오프닝 메시지 생성 완료")
        logger.info(f"[MODERATOR_ENDPOINT] 모더레이터 메시지: {opening_message[:100]}...")
        
        # 메시지 내에 "User123"이 있는지 확인하고 제거 (안전장치)
        if request.userData:
            for user_id, display_name in request.userData.items():
                if user_id in opening_message:
                    # User123과 같은 내부 ID가 메시지에 있으면 표시 이름으로 대체
                    opening_message = opening_message.replace(user_id, display_name)
                    logger.info(f"[MODERATOR_ENDPOINT] 메시지에서 사용자 ID 제거: {user_id} -> {display_name}")
        
        # 응답 형식 구성
        response_data = {
            "status": "success",
            "initial_message": {
                "text": opening_message,
                "sender": "Moderator",
                "isUser": False,
                "isSystemMessage": True,
                "role": "moderator",
            }
        }
        
        # room_id가 요청에 있다면 응답에도 포함
        if request.room_id:
            response_data["room_id"] = request.room_id
            
        return response_data
        
    except Exception as e:
        logger.error(f"[MODERATOR_ENDPOINT] 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모더레이터 메시지 생성 중 오류: {str(e)}")

# 채팅 메시지를 Next.js API를 통해 저장하는 함수
async def save_message_to_mongodb(room_id: str, message_text: str, sender: str, is_user: bool = False, role: str = None):
    """
    MongoDB에 메시지를 직접 저장하는 함수
    
    Args:
        room_id: 방 ID
        message_text: 메시지 텍스트
        sender: 발신자
        is_user: 사용자 메시지 여부
        role: 발신자 역할 (debate 모드에서 사용)
    
    Returns:
        저장 결과
    """
    try:
        # Next.js API 기본 URL
        api_url = "http://localhost:3000/api/messages"
        
        # 메시지 ID 생성
        message_id = f"user-{int(time.time()*1000)}"
        
        # 메시지 객체 구성
        message_data = {
            "id": message_id,
            "text": message_text,
            "sender": sender,
            "isUser": is_user,
            "timestamp": datetime.now().isoformat(),
        }
        
        # 역할 정보가 있으면 추가
        if role:
            message_data["role"] = role
        
        # API 요청 데이터
        request_data = {
            "roomId": room_id,
            "message": message_data,
            "isInitial": False
        }
        
        logger.info(f"✅ Sending message to MongoDB via Next.js API: {json.dumps(request_data)[:200]}...")
        
        # API 호출
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                api_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Message saved to database for room {room_id}: {message_id}")
                logger.info(f"🧪 MongoDB 저장 응답: {json.dumps(result)[:500]}")
                return {"success": True, "message_id": message_id, "response": result}
            else:
                error_text = response.text
                logger.error(f"❌ Failed to save message: {response.status_code}, {error_text}")
                return {
                    "success": False, 
                    "error": f"API returned {response.status_code}", 
                    "response": error_text[:200]
                }
    
    except Exception as e:
        logger.error(f"❌ Error saving message to MongoDB: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
        
    finally:
        logger.info(f"[DIALOGUE] 메시지 DB 저장 시도 완료: {room_id}")

# ... existing code ...