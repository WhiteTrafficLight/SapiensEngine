"""
Debug 관련 API 엔드포인트
- 대화 상태 조회
- 토큰 계산  
- 시스템 상태 확인
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import tiktoken

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/debug/conversation/{room_id}")
async def debug_conversation_state(room_id: str):
    """채팅방의 대화 상태 디버깅 정보 조회"""
    try:
        # 대화 상태 조회 로직 (원본에서 이전)
        # TODO: 원본 함수에서 로직 복사
        return {
            "room_id": room_id,
            "status": "debug_info_placeholder"
        }
    except Exception as e:
        logger.error(f"Debug conversation state error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debug/tokencount")
async def debug_token_count(text: str):
    """텍스트의 토큰 수 계산"""
    try:
        # 토큰 계산 로직
        try:
            encoding = tiktoken.encoding_for_model("gpt-4")
            token_count = len(encoding.encode(text))
        except:
            # tiktoken이 없는 경우 근사치 계산
            token_count = len(text.split()) * 1.3
            
        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "token_count": int(token_count),
            "character_count": len(text),
            "word_count": len(text.split())
        }
    except Exception as e:
        logger.error(f"Token count error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/system-status")
async def get_system_status():
    """시스템 상태 확인"""
    try:
        import os
        import psutil
        
        return {
            "openai_api_key": "설정됨" if os.environ.get('OPENAI_API_KEY') else "설정되지 않음",
            "memory_usage": f"{psutil.virtual_memory().percent}%",
            "cpu_usage": f"{psutil.cpu_percent()}%",
            "active_conversations": "TODO: 구현 필요"
        }
    except Exception as e:
        logger.error(f"System status error: {str(e)}")
        return {"error": str(e)} 