"""
새로운 DebateDialogue RAG 기능 테스트

주제: 트랜스휴머니즘 - 인간의 새로운 도약인가 아니면 종말인가?
찬성: 니체 (Friedrich Nietzsche)
반대: 카뮈 (Albert Camus)
"""

import sys
import os
import time
import logging
from typing import Dict, Any, List
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/debate_test_new_{time.strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

# 필요한 모듈 import (dependency 문제 우회)
try:
    from src.dialogue.types.debate_dialogue import DebateDialogue, DebateStage, ParticipantRole
    from src.agents.moderator.moderator_agent import ModeratorAgent
    from src.agents.participant.debate_participant_agent import DebateParticipantAgent
except ImportError as e:
    print(f"Import error: {e}")
    print("일부 의존성이 누락되었습니다. 패키지를 설치해주세요.")
    sys.exit(1)


class TranshumanismDebateTest:
    """트랜스휴머니즘 토론 테스트 클래스"""
    
    def __init__(self):
        """트랜스휴머니즘 토론 테스트 초기화"""
        # 대화 초기화
        self.initialize_dialogue()
        
    def initialize_dialogue(self):
        """토론 대화 및 에이전트 초기화"""
        # 새로운 room_data 구조 사용
        room_data = self.create_room_data()
        
        print(f"🎭 토론 초기화: {room_data['title']}")
        print(f"📚 컨텍스트 길이: {len(room_data['context'])} 문자")
        print(f"👥 참가자: {room_data['participants']['pro']['name']} vs {room_data['participants']['con']['name']}")
        
        # 대화 객체 생성 - 이제 room_data에서 자동으로 에이전트 생성됨
        self.dialogue = DebateDialogue(room_id="transhumanism_debate_001", room_data=room_data)
        
        # 더 이상 별도의 에이전트 설정 불필요 - room_data에서 자동 처리
        # self._setup_philosopher_agents() 제거됨
        
        # 초기화 상태 확인
        print(f"📊 벡터 저장소: {'활성화됨' if self.dialogue.vector_store else '비활성화됨'}")
        if self.dialogue.vector_store:
            print(f"📄 저장된 문서 수: {len(self.dialogue.vector_store.documents)}")
        print(f"🤖 생성된 에이전트:")
        for role, agent in self.dialogue.agents.items():
            print(f"   - {role}: {agent.name} ({agent.agent_id})")
        print()
    
    def create_room_data(self):
        """트랜스휴머니즘 토론을 위한 방 데이터 생성"""
        return {
            "title": "트랜스휴머니즘: 인간의 새로운 도약인가 아니면 종말인가?",
            "context": """
트랜스휴머니즘은 기술을 통해 인간의 신체적, 인지적 능력을 향상시키려는 철학적, 과학적 운동입니다.

## 주요 기술 영역:
- 유전자 편집 (CRISPR-Cas9)
- 신경 인터페이스 및 뇌-컴퓨터 연결
- 인공 장기 및 사이보그 기술
- 수명 연장 및 불멸 연구
- 인공지능과의 융합

## 찬성 논리:
- 인간 능력의 근본적 향상 가능
- 질병과 노화 극복
- 우주 탐사 등 극한 환경 적응
- 개인의 자유 선택권 확대

## 반대 논리:
- 인간 본질의 상실 우려
- 사회적 불평등 심화 가능성
- 예측 불가능한 부작용
- 기술 의존성 증가

## 현재 발전 현황:
- 일론 머스크의 뉴럴링크 뇌 임플란트 실험
- 구글의 생명 연장 프로젝트 Calico
- 중국의 유전자 편집 아기 실험 논란
- AI와 인간 능력 비교 연구

이 토론에서는 인간의 기술적 진화가 새로운 가능성인지, 아니면 위험한 길인지를 깊이 있게 논의합니다.
            """,
            "participants": {
                "pro": {
                    "character_id": "nietzsche",
                    "name": "프리드리히 니체",
                    "personality": "passionate",
                    "style": "poetic",
                    "argumentation_style": "philosophical",
                    "knowledge_areas": ["philosophy", "human_enhancement", "will_to_power"],
                    "character_traits": {
                        "core_philosophy": "위버멘쉬(Übermensch) - 인간은 극복되어야 할 존재",
                        "key_concepts": ["권력에의 의지", "영원회귀", "가치의 재평가"],
                        "famous_quotes": [
                            "인간은 극복되어야 할 어떤 것이다",
                            "신은 죽었다, 그리고 우리가 그를 죽였다"
                        ]
                    },
                    "speaking_style": "열정적이고 시적인 표현, 강렬한 메타포 사용"
                },
                "con": {
                    "character_id": "camus",
                    "name": "알베르 카뮈",
                    "personality": "absurdist",
                    "style": "existential",
                    "argumentation_style": "absurdist",
                    "knowledge_areas": ["existentialism", "absurdism", "human_condition"],
                    "character_traits": {
                        "core_philosophy": "부조리한 세계에서의 인간 조건",
                        "key_concepts": ["부조리", "반항", "인간의 존엄"],
                        "famous_quotes": [
                            "진정한 철학적 문제는 단 하나, 자살이다",
                            "부조리한 인간이란 자신의 조건을 생각하는 인간이다"
                        ]
                    },
                    "speaking_style": "차분하고 성찰적인 어조, 실존적 질문 제기"
                }
            },
            "moderator": {
                "agent_id": "debate_moderator",
                "name": "토론 진행자",
                "style": 1
            }
        }
    
    def _setup_philosopher_agents(self):
        """철학자 캐릭터 설정은 이제 room_data를 통해 자동으로 처리됨"""
        # 더 이상 필요하지 않음 - room_data에서 자동으로 에이전트 생성
        logger.info("Philosopher agents are now automatically created from room_data participants info")
        pass
    
    def run_transhumanism_debate(self, max_turns: int = 5):
        """
        트랜스휴머니즘 토론 실행 (입론단계까지)
        
        Args:
            max_turns: 최대 턴 수
        """
        print("🚀 트랜스휴머니즘 토론 시작!")
        print("=" * 60)
        
        turn = 0
        messages = []
        rag_search_results = {}
        
        # 입론단계까지만 테스트
        stages_to_test = [
            DebateStage.OPENING,
            DebateStage.PRO_ARGUMENT, 
            DebateStage.CON_ARGUMENT
        ]
        
        while turn < max_turns and self.dialogue.state["current_stage"] in stages_to_test:
            current_stage = self.dialogue.state["current_stage"]
            stage_display = self._get_stage_display(current_stage)
            
            print(f"\n🎯 [{stage_display}] 단계")
            print("-" * 40)
            
            # 오프닝 처리 (이미 생성된 경우)
            if current_stage == DebateStage.OPENING and len(self.dialogue.state["speaking_history"]) > 0:
                opening_messages = [msg for msg in self.dialogue.state["speaking_history"] 
                                  if msg.get("stage") == DebateStage.OPENING]
                if opening_messages:
                    latest_opening = opening_messages[-1]
                    print(f"🎙️ 진행자:")
                    print(f"{latest_opening.get('text', '')}\n")
                    
                    messages.append({
                        "speaker_id": "moderator",
                        "speaker_name": "진행자",
                        "role": "moderator", 
                        "message": latest_opening.get("text", ""),
                        "stage": current_stage,
                        "turn": turn
                    })
                    
                    # 다음 단계로 전환
                    self.dialogue.state["current_stage"] = DebateStage.PRO_ARGUMENT
                    turn += 1
                    continue
            
            # 응답 생성
            try:
                response = self.dialogue.generate_response()
                
                if response["status"] == "success":
                    speaker_id = response["speaker_id"] 
                    role = response["role"]
                    message = response["message"]
                    
                    # 발언자 이름 결정
                    if role == "moderator":
                        speaker_name = "🎙️ 진행자"
                    elif role == "pro":
                        speaker_name = "🦅 니체"
                    elif role == "con":
                        speaker_name = "🌊 카뮈"
                    else:
                        speaker_name = speaker_id
                    
                    # 메시지 출력
                    print(f"{speaker_name}:")
                    print(f"{message}\n")
                    
                    # RAG 검색 결과 추출 및 실제 웹검색 확인
                    if role in ["pro", "con"] and current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
                        role_key = ParticipantRole.PRO if role == "pro" else ParticipantRole.CON
                        agent = self.dialogue.agents.get(role_key)
                        
                        if agent:
                            print(f"🔍 {speaker_name}의 RAG 분석:")
                            print(f"   에이전트 ID: {agent.agent_id}")
                            print(f"   핵심 주장: {len(getattr(agent, 'core_arguments', []))}")
                            print(f"   검색 쿼리: {len(getattr(agent, 'argument_queries', []))}")
                            print(f"   준비된 입론: {'예' if getattr(agent, 'prepared_argument', '') else '아니오'}")
                            
                            # 실제 웹검색 여부 확인
                            if hasattr(agent, 'web_retriever'):
                                print(f"   웹검색 도구: 활성화됨 ✅")
                            else:
                                print(f"   웹검색 도구: 비활성화됨 ❌")
                            
                            # RAG 결과 저장
                            rag_search_results[f"{role}_arguments"] = {
                                "speaker_id": speaker_id,
                                "speaker_name": speaker_name.replace("🦅 ", "").replace("🌊 ", ""),
                                "stage": current_stage,
                                "core_arguments": getattr(agent, 'core_arguments', []),
                                "argument_queries": getattr(agent, 'argument_queries', []),
                                "prepared_argument": getattr(agent, 'prepared_argument', ''),
                                "web_search_active": hasattr(agent, 'web_retriever')
                            }
                            
                            # 검색 결과 상세 정보
                            argument_queries = getattr(agent, 'argument_queries', [])
                            for i, query_data in enumerate(argument_queries):
                                for evidence in query_data.get("evidence", []):
                                    query = evidence.get("query", "")
                                    source = evidence.get("source", "")
                                    results = evidence.get("results", [])
                                    
                                    print(f"   쿼리 {i+1}: '{query}'")
                                    print(f"           출처: {source}")
                                    print(f"           결과: {len(results)}개")
                                    
                                    # 실제 검색 결과가 있는지 확인
                                    if results:
                                        for j, result in enumerate(results[:2]):  # 처음 2개만 출력
                                            title = result.get("title", "제목 없음")
                                            content = result.get("content", "")[:100]
                                            print(f"             {j+1}. {title}")
                                            print(f"                {content}...")
                            print()
                    
                    # 메시지 기록
                    messages.append({
                        "speaker_id": speaker_id,
                        "speaker_name": speaker_name.replace("🦅 ", "").replace("🌊 ", "").replace("🎙️ ", ""),
                        "role": role,
                        "message": message,
                        "stage": current_stage,
                        "turn": turn
                    })
                    
                    turn += 1
                    time.sleep(1)  # 출력 간격
                    
                else:
                    print(f"❌ 응답 생성 실패: {response}")
                    break
                    
            except Exception as e:
                print(f"💥 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()
                break
        
        # 결과 저장
        self._save_transhumanism_results(messages, rag_search_results)
        
        print("=" * 60)
        print(f"✅ 트랜스휴머니즘 토론 완료: 총 {turn}턴")
        print()
    
    def _get_stage_display(self, stage: str) -> str:
        """단계 표시명 반환"""
        stage_names = {
            DebateStage.OPENING: "오프닝",
            DebateStage.PRO_ARGUMENT: "니체의 입론",
            DebateStage.CON_ARGUMENT: "카뮈의 입론",
        }
        return stage_names.get(stage, stage)
    
    def _save_transhumanism_results(self, messages: List[Dict[str, Any]], rag_search_results: Dict[str, Any]):
        """트랜스휴머니즘 토론 결과 저장"""
        # dialogue 객체에서 정보 가져오기
        room_data = self.dialogue.room_data
        topic = room_data.get('title', '트랜스휴머니즘 토론')
        context = room_data.get('context', '')
        stance_statements = self.dialogue.stance_statements
        
        result = {
            "topic": topic,
            "theme": "트랜스휴머니즘 철학 토론",
            "participants": {
                "pro": {
                    "name": room_data.get('participants', {}).get('pro', {}).get('name', '프리드리히 니체'),
                    "philosophy": "위버멘쉬, 힘에의 의지", 
                    "stance": stance_statements.get("pro", "")
                },
                "con": {
                    "name": room_data.get('participants', {}).get('con', {}).get('name', '알베르 카뮈'),
                    "philosophy": "부조리주의, 실존주의",
                    "stance": stance_statements.get("con", "")
                }
            },
            "context": context,
            "messages": messages,
            "rag_search_results": rag_search_results,
            "web_search_analysis": self._analyze_web_search_usage(rag_search_results),
            "timestamp": time.strftime("%Y%m%d_%H%M%S")
        }
        
        # 결과 저장 디렉토리 생성
        os.makedirs("debate_results", exist_ok=True)
        
        # 전체 결과 저장
        filename = f"debate_results/transhumanism_debate_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"📄 토론 결과 저장: {filename}")
        
        # RAG 검색 결과만 별도 저장
        rag_filename = f"debate_results/rag_analysis_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(rag_filename, "w", encoding="utf-8") as f:
            json.dump({
                "topic": topic,
                "rag_search_results": rag_search_results,
                "web_search_analysis": result["web_search_analysis"]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"🔍 RAG 분석 결과: {rag_filename}")
    
    def _analyze_web_search_usage(self, rag_search_results: Dict[str, Any]) -> Dict[str, Any]:
        """웹검색 사용 분석"""
        analysis = {
            "total_queries": 0,
            "web_queries": 0,
            "other_queries": 0,
            "actual_search_results": 0,
            "search_sources": {},
            "web_search_active": False
        }
        
        for side, data in rag_search_results.items():
            if "web_search_active" in data:
                analysis["web_search_active"] = data["web_search_active"]
            
            argument_queries = data.get("argument_queries", [])
            for query_data in argument_queries:
                for evidence in query_data.get("evidence", []):
                    analysis["total_queries"] += 1
                    source = evidence.get("source", "unknown")
                    
                    if source == "web":
                        analysis["web_queries"] += 1
                    else:
                        analysis["other_queries"] += 1
                    
                    analysis["search_sources"][source] = analysis["search_sources"].get(source, 0) + 1
                    
                    results = evidence.get("results", [])
                    analysis["actual_search_results"] += len(results)
        
        return analysis


def main():
    """메인 실행 함수"""
    print("🤖 트랜스휴머니즘 철학 토론 시작")
    print("   니체 vs 카뮈: 기술을 통한 인간 진화의 찬반")
    print()
    
    try:
        # 토론 테스트 인스턴스 생성
        test = TranshumanismDebateTest()
        
        # 입론단계까지 토론 실행
        test.run_transhumanism_debate(max_turns=5)
        
    except Exception as e:
        print(f"💥 테스트 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 