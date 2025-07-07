"""
철학자 정보 API

기본 철학자 목록과 상세 정보를 제공하는 라우터
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ========================================================================
# 데이터 모델
# ========================================================================

class Philosopher(BaseModel):
    id: str
    name: str
    era: Optional[str] = None
    school: Optional[str] = None
    description: Optional[str] = None
    key_ideas: Optional[List[str]] = None

# ========================================================================
# 라우터 초기화
# ========================================================================

router = APIRouter()

# ========================================================================
# 기본 철학자 데이터
# ========================================================================

PHILOSOPHERS_DATA = [
    {
        "id": "socrates",
        "name": "Socrates",
        "era": "Ancient Greece (470-399 BCE)",
        "school": "Classical Philosophy",
        "description": "Known for the Socratic method and the idea that 'the only thing I know is that I know nothing'",
        "key_ideas": ["Know thyself", "Socratic method", "Virtue is knowledge", "Examined life"]
    },
    {
        "id": "plato",
        "name": "Plato",
        "era": "Ancient Greece (428-348 BCE)",
        "school": "Platonism",
        "description": "Student of Socrates, founded the Academy in Athens",
        "key_ideas": ["Theory of Forms", "Philosopher kings", "Allegory of the Cave", "Justice"]
    },
    {
        "id": "aristotle",
        "name": "Aristotle",
        "era": "Ancient Greece (384-322 BCE)",
        "school": "Aristotelianism",
        "description": "Student of Plato, tutor to Alexander the Great",
        "key_ideas": ["Virtue ethics", "Golden mean", "Four causes", "Logic"]
    },
    {
        "id": "kant",
        "name": "Immanuel Kant",
        "era": "Enlightenment (1724-1804)",
        "school": "German Idealism",
        "description": "Central figure of modern philosophy, known for categorical imperative",
        "key_ideas": ["Categorical imperative", "Transcendental idealism", "Synthetic a priori", "Moral autonomy"]
    },
    {
        "id": "nietzsche",
        "name": "Friedrich Nietzsche",
        "era": "19th Century (1844-1900)",
        "school": "Existentialism/Nihilism",
        "description": "Influential German philosopher and cultural critic",
        "key_ideas": ["Will to power", "Übermensch", "Eternal recurrence", "God is dead"]
    },
    {
        "id": "sartre",
        "name": "Jean-Paul Sartre",
        "era": "20th Century (1905-1980)",
        "school": "Existentialism",
        "description": "Leading figure in 20th-century French philosophy",
        "key_ideas": ["Existence precedes essence", "Bad faith", "Freedom and responsibility", "Being-for-others"]
    },
    {
        "id": "camus",
        "name": "Albert Camus",
        "era": "20th Century (1913-1960)",
        "school": "Absurdism",
        "description": "French-Algerian philosopher and Nobel Prize winner",
        "key_ideas": ["Absurdism", "The stranger", "Revolt", "The myth of Sisyphus"]
    },
    {
        "id": "simone_de_beauvoir",
        "name": "Simone de Beauvoir",
        "era": "20th Century (1908-1986)",
        "school": "Existentialism/Feminism",
        "description": "French existentialist philosopher and feminist theorist",
        "key_ideas": ["The Second Sex", "Women's liberation", "Situated ethics", "Existential feminism"]
    },
    {
        "id": "marx",
        "name": "Karl Marx",
        "era": "19th Century (1818-1883)",
        "school": "Marxism",
        "description": "German philosopher, economist, and revolutionary socialist",
        "key_ideas": ["Historical materialism", "Class struggle", "Alienation", "Communist manifesto"]
    },
    {
        "id": "rousseau",
        "name": "Jean-Jacques Rousseau",
        "era": "Enlightenment (1712-1778)",
        "school": "Social Contract Theory",
        "description": "Genevan philosopher, writer, and composer",
        "key_ideas": ["Social contract", "General will", "Natural goodness", "Education philosophy"]
    },
    {
        "id": "confucius",
        "name": "Confucius",
        "era": "Ancient China (551-479 BCE)",
        "school": "Confucianism",
        "description": "Chinese philosopher and politician of the Spring and Autumn period",
        "key_ideas": ["Ren (benevolence)", "Li (ritual propriety)", "Junzi (exemplary person)", "Filial piety"]
    },
    {
        "id": "laozi",
        "name": "Laozi",
        "era": "Ancient China (6th century BCE)",
        "school": "Taoism",
        "description": "Ancient Chinese philosopher and writer, founder of Taoism",
        "key_ideas": ["Tao (the Way)", "Wu wei (non-action)", "Yin and Yang", "Te (virtue/power)"]
    }
]

# ========================================================================
# API 엔드포인트들
# ========================================================================

@router.get("/")
@router.get("/list")
async def get_philosophers(limit: Optional[int] = None) -> Dict[str, Any]:
    """모든 철학자 목록 조회"""
    try:
        philosophers = PHILOSOPHERS_DATA.copy()
        
        if limit:
            philosophers = philosophers[:limit]
        
        # Philosopher 모델로 변환
        philosopher_objects = [Philosopher(**p) for p in philosophers]
        
        logger.info(f"📚 Returning {len(philosopher_objects)} philosophers")
        
        return {
            "philosophers": philosopher_objects,
            "total": len(philosopher_objects)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get philosophers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{philosopher_id}")
async def get_philosopher_by_id(philosopher_id: str) -> Philosopher:
    """특정 철학자 정보 조회"""
    try:
        # ID로 철학자 찾기
        philosopher_data = next(
            (p for p in PHILOSOPHERS_DATA if p["id"] == philosopher_id), 
            None
        )
        
        if not philosopher_data:
            raise HTTPException(status_code=404, detail=f"Philosopher '{philosopher_id}' not found")
        
        philosopher = Philosopher(**philosopher_data)
        
        logger.info(f"📚 Returning philosopher: {philosopher.name}")
        
        return philosopher
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get philosopher {philosopher_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/{query}")
async def search_philosophers(query: str) -> Dict[str, Any]:
    """철학자 검색"""
    try:
        query_lower = query.lower()
        
        # 이름, 학파, 시대, 주요 아이디어에서 검색
        matching_philosophers = []
        
        for p_data in PHILOSOPHERS_DATA:
            if (query_lower in p_data["name"].lower() or
                (p_data.get("school") and query_lower in p_data["school"].lower()) or
                (p_data.get("era") and query_lower in p_data["era"].lower()) or
                (p_data.get("key_ideas") and any(query_lower in idea.lower() for idea in p_data["key_ideas"]))):
                matching_philosophers.append(Philosopher(**p_data))
        
        logger.info(f"🔍 Search '{query}' found {len(matching_philosophers)} philosophers")
        
        return {
            "philosophers": matching_philosophers,
            "total": len(matching_philosophers),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to search philosophers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/by-era/{era}")
async def get_philosophers_by_era(era: str) -> Dict[str, Any]:
    """시대별 철학자 조회"""
    try:
        era_lower = era.lower()
        
        matching_philosophers = []
        for p_data in PHILOSOPHERS_DATA:
            if p_data.get("era") and era_lower in p_data["era"].lower():
                matching_philosophers.append(Philosopher(**p_data))
        
        logger.info(f"📅 Era '{era}' has {len(matching_philosophers)} philosophers")
        
        return {
            "philosophers": matching_philosophers,
            "total": len(matching_philosophers),
            "era": era
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get philosophers by era: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 