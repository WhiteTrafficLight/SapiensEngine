"""
Sapiens Engine API Routers
도메인별로 분리된 FastAPI 라우터들
"""

from . import debug
from . import philosophers

# TODO: 다른 라우터들도 순차적으로 추가
# from . import chat
# from . import debate  
# from . import dialogue
# from . import moderator
# from . import npc
# from . import rooms

__all__ = [
    "debug",
    "philosophers",
    # TODO: 추가할 라우터들
    # "chat",
    # "debate", 
    # "dialogue",
    # "moderator",
    # "npc", 
    # "rooms"
] 