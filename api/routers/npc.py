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
        'Confucius (Kong Fuzi)': 'Confucius',
        'Laozi': 'Laozi',
        'Buddha': 'Buddha',
        'Ludwig Wittgenstein': 'Wittgenstein'
    }
    
    # 특별한 케이스 먼저 확인
    if philosopher_name in special_cases:
        return special_cases[philosopher_name]
    
    # 괄호가 있는 경우 괄호 앞 부분만 사용
    name = philosopher_name.split('(')[0].strip()
    
    # 일반적인 경우: 마지막 단어(Last name) 사용
    parts = name.strip().split()
    if parts:
        return parts[-1]  # 마지막 단어
    
    return name

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
                "portrait_url": f"/philosophers_portraits/{get_portrait_filename(philosopher.get('name', get_philosopher_display_name(id)))}.png",
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
                "portrait_url": f"/philosophers_portraits/default.png",
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
                "portrait_url": f"/philosophers_portraits/{get_portrait_filename(data.get('name', get_philosopher_display_name(key)))}.png"
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

"""
Custom NPC 관리 API

사용자 정의 철학자/NPC 생성, 조회, 수정, 삭제를 담당하는 라우터
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ========================================================================
# 데이터 모델
# ========================================================================

class CustomNPC(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    era: Optional[str] = None
    school: Optional[str] = None
    key_ideas: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    creator: Optional[str] = None
    is_public: bool = False

class CreateNPCRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    personality: Optional[str] = Field(None, max_length=500)
    era: Optional[str] = Field(None, max_length=100)
    school: Optional[str] = Field(None, max_length=100)
    key_ideas: Optional[List[str]] = None
    is_public: bool = False

class UpdateNPCRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    personality: Optional[str] = Field(None, max_length=500)
    era: Optional[str] = Field(None, max_length=100)
    school: Optional[str] = Field(None, max_length=100)
    key_ideas: Optional[List[str]] = None
    is_public: Optional[bool] = None

# ========================================================================
# 라우터 초기화
# ========================================================================

router = APIRouter()

# ========================================================================
# 임시 데이터 저장소 (실제로는 데이터베이스 사용)
# ========================================================================

# 샘플 Custom NPC 데이터
SAMPLE_NPCS = [
    {
        "id": "modern_ai_philosopher",
        "name": "AI Ethics Philosopher",
        "description": "A contemporary thinker focused on the ethical implications of artificial intelligence",
        "personality": "Analytical, cautious, and deeply concerned with technological impact on humanity",
        "era": "21st Century",
        "school": "Digital Ethics",
        "key_ideas": ["AI alignment", "Technological responsibility", "Digital rights", "Machine consciousness"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "creator": "system",
        "is_public": True
    },
    {
        "id": "environmental_philosopher",
        "name": "Eco-Philosopher",
        "description": "A philosopher dedicated to environmental ethics and sustainability",
        "personality": "Passionate, urgent, and holistic in thinking",
        "era": "Contemporary",
        "school": "Environmental Ethics",
        "key_ideas": ["Deep ecology", "Sustainable living", "Intergenerational justice", "Biosphere ethics"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "creator": "system",
        "is_public": True
    }
]

# 메모리 저장소 (프로덕션에서는 데이터베이스로 교체)
custom_npcs_store = {npc["id"]: npc for npc in SAMPLE_NPCS}

# ========================================================================
# API 엔드포인트들
# ========================================================================

@router.get("/list")
async def get_custom_npcs() -> Dict[str, Any]:
    """모든 Custom NPC 목록 조회"""
    try:
        npcs = list(custom_npcs_store.values())
        
        # CustomNPC 모델로 변환
        npc_objects = [CustomNPC(**npc) for npc in npcs]
        
        logger.info(f"🤖 Returning {len(npc_objects)} custom NPCs")
        
        return {
            "npcs": npc_objects,
            "total": len(npc_objects),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get custom NPCs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{npc_id}")
async def get_custom_npc(npc_id: str) -> CustomNPC:
    """특정 Custom NPC 조회"""
    try:
        if npc_id not in custom_npcs_store:
            raise HTTPException(status_code=404, detail=f"Custom NPC '{npc_id}' not found")
        
        npc_data = custom_npcs_store[npc_id]
        npc = CustomNPC(**npc_data)
        
        logger.info(f"🤖 Returning custom NPC: {npc.name}")
        
        return npc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get custom NPC {npc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_custom_npc(request: CreateNPCRequest) -> CustomNPC:
    """새로운 Custom NPC 생성"""
    try:
        # ID 생성 (간단한 방법, 실제로는 UUID 사용)
        npc_id = request.name.lower().replace(" ", "_").replace("-", "_")
        
        # 중복 확인
        if npc_id in custom_npcs_store:
            raise HTTPException(status_code=400, detail=f"NPC with name '{request.name}' already exists")
        
        # 현재 시간
        current_time = datetime.now().isoformat() + "Z"
        
        # 새 NPC 데이터 생성
        npc_data = {
            "id": npc_id,
            "name": request.name,
            "description": request.description,
            "personality": request.personality,
            "era": request.era,
            "school": request.school,
            "key_ideas": request.key_ideas or [],
            "created_at": current_time,
            "updated_at": current_time,
            "creator": "user",  # 실제로는 인증된 사용자 ID
            "is_public": request.is_public
        }
        
        # 저장소에 추가
        custom_npcs_store[npc_id] = npc_data
        
        npc = CustomNPC(**npc_data)
        
        logger.info(f"✅ Created custom NPC: {npc.name}")
        
        return npc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create custom NPC: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{npc_id}")
async def update_custom_npc(npc_id: str, request: UpdateNPCRequest) -> CustomNPC:
    """Custom NPC 정보 업데이트"""
    try:
        if npc_id not in custom_npcs_store:
            raise HTTPException(status_code=404, detail=f"Custom NPC '{npc_id}' not found")
        
        # 기존 데이터 가져오기
        npc_data = custom_npcs_store[npc_id].copy()
        
        # 업데이트할 필드만 변경
        update_data = request.dict(exclude_unset=True)
        npc_data.update(update_data)
        npc_data["updated_at"] = datetime.now().isoformat() + "Z"
        
        # 저장소에 업데이트
        custom_npcs_store[npc_id] = npc_data
        
        npc = CustomNPC(**npc_data)
        
        logger.info(f"✅ Updated custom NPC: {npc.name}")
        
        return npc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update custom NPC {npc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{npc_id}")
async def delete_custom_npc(npc_id: str) -> Dict[str, Any]:
    """Custom NPC 삭제"""
    try:
        if npc_id not in custom_npcs_store:
            raise HTTPException(status_code=404, detail=f"Custom NPC '{npc_id}' not found")
        
        # 시스템 NPC는 삭제 불가
        npc_data = custom_npcs_store[npc_id]
        if npc_data.get("creator") == "system":
            raise HTTPException(status_code=403, detail="Cannot delete system NPCs")
        
        # 삭제
        del custom_npcs_store[npc_id]
        
        logger.info(f"🗑️ Deleted custom NPC: {npc_id}")
        
        return {
            "success": True,
            "message": f"Custom NPC '{npc_id}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete custom NPC {npc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{query}")
async def search_custom_npcs(query: str) -> Dict[str, Any]:
    """Custom NPC 검색"""
    try:
        query_lower = query.lower()
        
        matching_npcs = []
        for npc_data in custom_npcs_store.values():
            if (query_lower in npc_data["name"].lower() or
                (npc_data.get("description") and query_lower in npc_data["description"].lower()) or
                (npc_data.get("school") and query_lower in npc_data["school"].lower()) or
                (npc_data.get("key_ideas") and any(query_lower in idea.lower() for idea in npc_data["key_ideas"]))):
                matching_npcs.append(CustomNPC(**npc_data))
        
        logger.info(f"🔍 Search '{query}' found {len(matching_npcs)} custom NPCs")
        
        return {
            "npcs": matching_npcs,
            "total": len(matching_npcs),
            "query": query,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to search custom NPCs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 