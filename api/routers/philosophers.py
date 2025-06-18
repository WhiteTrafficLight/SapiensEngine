"""
철학자 관련 API 엔드포인트
- 철학자 목록 조회
- 철학자 상세 정보 조회
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import os
import yaml

router = APIRouter()
logger = logging.getLogger(__name__)

# 철학자 데이터 로드
def load_philosophers_data():
    """철학자 데이터를 YAML 파일에서 로드"""
    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        PHILOSOPHERS_FILE = os.path.join(BASE_DIR, "config/philosophers.yaml")
        
        with open(PHILOSOPHERS_FILE, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading philosophers data: {e}")
        return []

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

@router.get("/philosophers")
async def get_philosophers():
    """철학자 목록 조회"""
    try:
        philosophers_data = load_philosophers_data()
        
        if not philosophers_data:
            logger.warning("No philosophers data found")
            return []
        
        # 철학자 목록 정리 - 딕셔너리 구조로 처리
        philosophers_list = []
        for key, data in philosophers_data.items():  # 딕셔너리로 처리
            philosopher_info = {
                "id": key,  # 키가 id
                "name": data.get("name", ""),
                "korean_name": data.get("korean_name", ""),  # 추가하면 좋겠지만 없을 수도
                "period": data.get("period", ""),
                "school": data.get("school", ""),  # 추가하면 좋겠지만 없을 수도
                "description": data.get("description", "")[:200] + "..." if data.get("description", "") else "",
                "portrait_url": f"/portraits/{PORTRAITS_MAP.get(key, 'default.png')}"
            }
            philosophers_list.append(philosopher_info)
        
        logger.info(f"철학자 목록 조회 성공: {len(philosophers_list)}명")
        return {"philosophers": philosophers_list}
        
    except Exception as e:
        logger.error(f"철학자 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"철학자 목록을 가져오는 중 오류가 발생했습니다: {str(e)}")

@router.get("/philosophers/{philosopher_id}")
async def get_philosopher_details(philosopher_id: str):
    """특정 철학자의 상세 정보 조회"""
    try:
        philosophers_data = load_philosophers_data()
        
        if not philosophers_data:
            raise HTTPException(status_code=404, detail="철학자 데이터를 찾을 수 없습니다")
        
        # 철학자 검색 - 딕셔너리에서 키로 직접 접근
        philosopher_id_lower = philosopher_id.lower()
        if philosopher_id_lower not in philosophers_data:
            raise HTTPException(status_code=404, detail=f"철학자 '{philosopher_id}'를 찾을 수 없습니다")
        
        data = philosophers_data[philosopher_id_lower]
        
        # 상세 정보 구성
        philosopher_details = {
            "id": philosopher_id_lower,
            "name": data.get("name", ""),
            "korean_name": data.get("korean_name", ""),  
            "period": data.get("period", ""),
            "school": data.get("school", ""),
            "description": data.get("description", ""),
            "key_concepts": data.get("key_concepts", []),
            "famous_quotes": data.get("famous_quotes", []),
            "major_works": data.get("major_works", []),
            "portrait_url": f"/portraits/{PORTRAITS_MAP.get(philosopher_id_lower, 'default.png')}",
            "communication_style": data.get("communication_style", {}),
            "debate_approach": data.get("debate_approach", {})
        }
        
        logger.info(f"철학자 상세 정보 조회 성공: {philosopher_id}")
        return philosopher_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"철학자 상세 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"철학자 정보를 가져오는 중 오류가 발생했습니다: {str(e)}") 