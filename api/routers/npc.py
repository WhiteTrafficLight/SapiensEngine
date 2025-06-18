"""
NPC related API endpoints
"""
import os
import sys
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 상위 디렉토리의 src 모듈 import를 위한 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/npc", tags=["npc"])

# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def load_philosophers_data() -> Dict[str, Any]:
    """철학자 데이터 로드"""
    try:
        import yaml
        philosophers_path = os.path.join(BASE_DIR, 'config', 'philosophers.yaml')
        
        if not os.path.exists(philosophers_path):
            logger.warning(f"Philosophers file not found: {philosophers_path}")
            return {}
            
        with open(philosophers_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}
    except Exception as e:
        logger.error(f"Error loading philosophers data: {e}")
        return {}

def get_philosopher_display_name(philosopher_id: str) -> str:
    """철학자 ID를 표시용 이름으로 변환"""
    name_mapping = {
        'socrates': 'Socrates',
        'plato': 'Plato', 
        'aristotle': 'Aristotle',
        'kant': 'Immanuel Kant',
        'nietzsche': 'Friedrich Nietzsche',
        'hegel': 'Georg Wilhelm Friedrich Hegel',
        'marx': 'Karl Marx',
        'camus': 'Albert Camus',
        'sartre': 'Jean-Paul Sartre',
        'beauvoir': 'Simone de Beauvoir',
        'rousseau': 'Jean-Jacques Rousseau',
        'confucius': 'Confucius',
        'laozi': 'Laozi',
        'buddha': 'Buddha',
        'wittgenstein': 'Ludwig Wittgenstein'
    }
    return name_mapping.get(philosopher_id.lower(), philosopher_id.title())

def get_portrait_filename(philosopher_name: str) -> str:
    """철학자 이름에서 portrait 파일명 추출 (Last name 기준)"""
    # 특별한 케이스들을 위한 매핑
    special_cases = {
        'Socrates': 'Socrates',
        'Plato': 'Plato',
        'Aristotle': 'Aristotle',
        'Immanuel Kant': 'Kant',
        'Friedrich Nietzsche': 'Nietzsche', 
        'Georg Wilhelm Friedrich Hegel': 'Hegel',
        'Karl Marx': 'Marx',
        'Albert Camus': 'Camus',
        'Jean-Paul Sartre': 'Sartre',
        'Simone de Beauvoir': 'Beauvoir',
        'Jean-Jacques Rousseau': 'Rousseau',
        'Confucius': 'Confucius',
        'Laozi': 'Laozi',
        'Buddha': 'Buddha',
        'Ludwig Wittgenstein': 'Wittgenstein'
    }
    
    # 특별한 케이스 먼저 확인
    if philosopher_name in special_cases:
        return special_cases[philosopher_name]
    
    # 일반적인 경우: 마지막 단어(Last name) 사용
    parts = philosopher_name.strip().split()
    if parts:
        return parts[-1]  # 마지막 단어
    
    return philosopher_name

# ========================================================================
# API ENDPOINTS
# ========================================================================

@router.get("/get")
async def get_npc_details(id: str):
    """NPC 세부 정보 조회 - UI 표시용"""
    try:
        logger.info(f"NPC 정보 조회 요청: {id}")
        
        # 철학자 데이터 로드
        philosophers_data = load_philosophers_data()
        
        # 기본 철학자인지 확인
        philosopher_key = id.lower()
        if philosopher_key in philosophers_data:
            philosopher = philosophers_data[philosopher_key]
            
            # 응답 데이터 구성
            npc_info = {
                "id": id,
                "name": philosopher.get("name", get_philosopher_display_name(id)),
                "korean_name": philosopher.get("korean_name", ""),
                "period": philosopher.get("period", ""),
                "school": philosopher.get("school", ""),
                "description": philosopher.get("description", ""),
                "portrait_url": f"/portraits/{get_portrait_filename(philosopher.get('name', get_philosopher_display_name(id)))}.png",
                "is_default_philosopher": True
            }
            
            logger.info(f"기본 철학자 정보 반환: {id} -> {npc_info['name']}")
            return npc_info
        
        else:
            # Custom NPC의 경우 기본 정보 반환
            display_name = get_philosopher_display_name(id)
            npc_info = {
                "id": id,
                "name": display_name,
                "korean_name": "",
                "period": "Custom",
                "school": "Custom NPC",
                "description": f"Custom NPC: {display_name}",
                "portrait_url": f"/portraits/default.png",
                "is_default_philosopher": False
            }
            
            logger.info(f"Custom NPC 기본 정보 반환: {id} -> {display_name}")
            return npc_info
            
    except Exception as e:
        logger.error(f"NPC 정보 조회 중 오류: {id} - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get NPC details: {str(e)}")

@router.get("/list")
async def get_npc_list():
    """NPC 목록 조회"""
    try:
        philosophers_data = load_philosophers_data()
        
        npc_list = []
        for key, data in philosophers_data.items():
            npc_info = {
                "id": key,
                "name": data.get("name", get_philosopher_display_name(key)),
                "korean_name": data.get("korean_name", ""),
                "period": data.get("period", ""),
                "school": data.get("school", ""),
                "description": data.get("description", "")[:100] + "..." if data.get("description", "") else "",
                "portrait_url": f"/portraits/{get_portrait_filename(data.get('name', get_philosopher_display_name(key)))}.png"
            }
            npc_list.append(npc_info)
        
        logger.info(f"NPC 목록 조회 성공: {len(npc_list)}개")
        return {"npcs": npc_list}
        
    except Exception as e:
        logger.error(f"NPC 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get NPC list: {str(e)}")

@router.get("/test")
async def test_npc_endpoint():
    """NPC 엔드포인트 테스트"""
    return {
        "message": "NPC router is working!",
        "timestamp": "2024-01-01",
        "available_endpoints": [
            "GET /api/npc/get?id={npc_id}",
            "GET /api/npc/list",
            "GET /api/npc/test"
        ]
    } 