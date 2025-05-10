"""
다양한 대화 형식을 지원하는 모듈
- 기본 대화 (standard)
- 찬반 토론 (debate)
- 소크라테스식 대화 (socratic)
- 패널 토론 (panel)
"""

from .dialogue_factory import DialogueFactory

# 외부에서 사용할 주요 클래스 및 함수 노출
__all__ = ['DialogueFactory'] 