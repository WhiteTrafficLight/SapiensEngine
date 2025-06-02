"""
새로운 구조의 Sapiens Engine API Server
- 라우터 기반 모듈화된 구조
- 도메인별 엔드포인트 분리
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

# 라우터 임포트
from routers import debug, philosophers, chat, npc
# TODO: 다른 라우터들도 순차적으로 추가
# from routers import chat, debate, dialogue, moderator, npc, rooms

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Sapiens Engine API (New Structure)",
    description="철학자 AI와의 대화 및 토론 시스템 - 리팩토링된 구조",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 구체적인 오리진으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (초상화)
# API 폴더에서 실행되므로 상위 디렉토리의 portraits를 참조
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTRAITS_DIR = os.path.join(BASE_DIR, "portraits")
if os.path.isdir(PORTRAITS_DIR):
    app.mount("/portraits", StaticFiles(directory=PORTRAITS_DIR), name="portraits")
    logger.info(f"Mounted portraits from {PORTRAITS_DIR} at /portraits")
else:
    logger.error(f"Portraits directory not found: {PORTRAITS_DIR}")
    # 대안 경로들 시도
    alternative_paths = [
        os.path.join(os.getcwd(), "portraits"),
        os.path.join(os.getcwd(), "..", "portraits"),
        "/Users/jihoon/sapiens_engine/portraits"
    ]
    for alt_path in alternative_paths:
        if os.path.isdir(alt_path):
            app.mount("/portraits", StaticFiles(directory=alt_path), name="portraits")
            logger.info(f"Mounted portraits from alternative path: {alt_path}")
            break
    else:
        logger.warning("Could not find portraits directory in any expected location")

# 라우터 등록
app.include_router(
    philosophers.router, 
    prefix="/api", 
    tags=["철학자"]
)

app.include_router(
    debug.router, 
    prefix="/api", 
    tags=["디버그"]
)

app.include_router(
    chat.router, 
    prefix="/api", 
    tags=["채팅"]
)

app.include_router(
    npc.router, 
    prefix="/api", 
    tags=["NPC"]
)

# TODO: 다른 라우터들도 순차적으로 추가
# app.include_router(chat.router, prefix="/api", tags=["채팅"])
# app.include_router(debate.router, prefix="/api", tags=["토론"])
# app.include_router(dialogue.router, prefix="/api", tags=["대화시스템"])
# app.include_router(moderator.router, prefix="/api", tags=["모더레이터"])
# app.include_router(rooms.router, prefix="/api", tags=["방관리"])

@app.get("/")
def read_root():
    """API 루트 엔드포인트"""
    return {
        "message": "Sapiens Engine API - New Structure",
        "version": "2.0.0",
        "status": "operational",
        "available_endpoints": {
            "philosophers": "/api/philosophers",
            "debug": "/api/debug/system-status",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Sapiens Engine API (New Structure)")
    logger.info("📚 Available at: http://localhost:8000")
    logger.info("📖 API Docs: http://localhost:8000/docs")
    
    # 기존 api_server.py를 대체하므로 동일한 포트 사용
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000,  # 8001 → 8000으로 변경
        reload=True,
        log_level="info"
    ) 