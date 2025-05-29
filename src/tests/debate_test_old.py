"""
DebateDialogue 및 Vector Store 통합 테스트

VectorStore를 활용한 토론 컨텍스트 검색 기능이 적용된
DebateDialogue 클래스의 동작을 테스트합니다.
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
        logging.FileHandler(f"logs/debate_test_{time.strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

from src.dialogue.types.debate_dialogue import DebateDialogue, DebateStage, ParticipantRole
from src.agents.moderator.moderator_agent import ModeratorAgent
from src.agents.participant.debate_participant_agent import DebateParticipantAgent


class DebateTest:
    """토론 대화 테스트 클래스"""
    
    def __init__(self):
        """테스트 초기화"""
        self.topic = "디지털 프라이버시의 미래: 개인 정보 보호와 혁신 사이의 균형"
        
        # 컨텍스트 설정 (VectorStore에 저장될 정보)
        self.context = """
디지털 프라이버시는 개인 정보가 온라인에서 어떻게 수집, 사용, 공유되는지에 관한 개념입니다.

인터넷, 모바일 기기, IoT 기술의 확산으로 개인 데이터의 양과 종류가 기하급수적으로 증가했습니다.
이 데이터는 기업과 정부에 의해 다양한 목적으로 활용됩니다.

기업들은 개인화된 서비스 제공, 마케팅, 제품 개발 등에 데이터를 활용하여 경제적 가치를 창출합니다.
동시에 정부는 국가 안보, 범죄 예방, 사회 서비스 향상 등을 위해 데이터를 수집하고 분석합니다.

그러나 이러한 데이터 활용은 개인의 프라이버시 침해 우려를 낳고 있습니다.
무분별한 데이터 수집, 동의 없는 정보 공유, 데이터 유출 사고 등이 지속적으로 발생하고 있습니다.

주요 프라이버시 문제로는 행동 추적, 얼굴 인식 기술의 남용, 개인 정보의 상업적 거래,
데이터 보안 취약점, 빅데이터 분석을 통한 프로파일링 등이 있습니다.

이에 대응하여 GDPR(유럽), CCPA(캘리포니아) 등 각국에서 데이터 보호 규제를 강화하고 있으며,
프라이버시 중심 설계(Privacy by Design)와 같은 접근법도 주목받고 있습니다.

향후 디지털 프라이버시는 기술 혁신과 개인정보 보호 사이의 균형을 찾는 방향으로 발전할 것으로 전망됩니다.
중요한 것은 개인의 데이터 주권을 보장하면서도 데이터의 사회적, 경제적 가치를 활용할 수 있는 방안을 마련하는 것입니다.
"""
        
        # 참가자 설정
        self.participants = {
            "pro": {
                "id": "tech_advocate",
                "name": "기술 혁신 옹호자",
                "personality": "analytical",
                "style": "factual",
                "argumentation_style": "logical",
                "knowledge_level": "expert"
            },
            "con": {
                "id": "privacy_defender",
                "name": "개인정보 보호론자",
                "personality": "passionate",
                "style": "assertive",
                "argumentation_style": "emotional",
                "knowledge_level": "expert"
            }
        }
        
        # 찬반 입장 설정
        self.stance_statements = {
            "pro": "데이터 활용의 자유를 보장하여 기술 혁신과 경제 발전을 촉진해야 한다",
            "con": "엄격한 개인정보 보호 규제를 통해 시민의 디지털 프라이버시 권리를 우선시해야 한다"
        }
        
        # 대화 초기화
        self.initialize_dialogue()
        
    def initialize_dialogue(self):
        """토론 대화 및 에이전트 초기화"""
        # 채팅방 데이터 구성
        room_data = {
            "title": self.topic,
            "context": self.context,
            "participants": {
                "npcs": [
                    {"id": "tech_advocate", "name": "기술 혁신 옹호자", "role": "pro"},
                    {"id": "privacy_defender", "name": "개인정보 보호론자", "role": "con"}
                ],
                "users": []
            }
        }
        
        # 에이전트 생성
        self.agents = {}
        
        # 모더레이터 에이전트
        self.agents[ParticipantRole.MODERATOR] = ModeratorAgent(
            agent_id="moderator_001",
            name="Moderator",
            config={"stance_statements": self.stance_statements}
        )
        
        # 찬성 측 에이전트 - 올바른 키 사용
        self.agents[ParticipantRole.PRO] = DebateParticipantAgent(
            agent_id=self.participants["pro"]["id"],
            name=self.participants["pro"]["name"],
            config={
                "role": "pro",
                "personality": self.participants["pro"]["personality"],
                "style": self.participants["pro"]["style"],
                "argumentation_style": self.participants["pro"]["argumentation_style"],
                "knowledge_level": self.participants["pro"]["knowledge_level"],
                "stance_statements": self.stance_statements
            }
        )
        
        # 반대 측 에이전트 - 올바른 키 사용  
        self.agents[ParticipantRole.CON] = DebateParticipantAgent(
            agent_id=self.participants["con"]["id"],
            name=self.participants["con"]["name"],
            config={
                "role": "con",
                "personality": self.participants["con"]["personality"],
                "style": self.participants["con"]["style"],
                "argumentation_style": self.participants["con"]["argumentation_style"],
                "knowledge_level": self.participants["con"]["knowledge_level"],
                "stance_statements": self.stance_statements
            }
        )
        
        # 대화 객체 생성 (VectorStore 통합 테스트를 위한 고유 ID 사용)
        self.dialogue = DebateDialogue(room_id="test_vector_debate_001", room_data=room_data)
        
        # 에이전트 교체
        self.dialogue.agents = self.agents
        
        # 벡터 저장소 초기화 확인
        print(f"벡터 저장소 초기화 상태: {self.dialogue.vector_store is not None}")
        if self.dialogue.vector_store:
            print(f"저장된 문서 수: {len(self.dialogue.vector_store.documents)}")
    
    def run_debate_with_context_retrieval(self, max_turns: int = 5, stages_to_test: List[str] = None):
        """
        벡터 저장소 컨텍스트 검색 기능을 활용한 토론 테스트
        
        Args:
            max_turns: 최대 턴 수
            stages_to_test: 테스트할 단계 목록 (None이면 모든 단계)
        """
        print(f"\n===== 컨텍스트 검색 기능 활용 토론 테스트: {self.topic} =====\n")
        print(f"찬성: {self.participants['pro']['name']} - {self.stance_statements['pro']}")
        print(f"반대: {self.participants['con']['name']} - {self.stance_statements['con']}\n")
        
        turn = 0
        messages = []
        rag_search_results = {}
        
        # 테스트할 단계가 지정되지 않았으면 입론단계까지만 설정
        if stages_to_test is None:
            stages_to_test = [
                DebateStage.OPENING,
                DebateStage.PRO_ARGUMENT,
                DebateStage.CON_ARGUMENT
            ]
        
        # 특정 턴 수까지 또는 테스트할 모든 단계를 완료할 때까지 실행
        while turn < max_turns and self.dialogue.state["current_stage"] in stages_to_test:
            # 현재 단계 및 다음 발언자 정보 출력
            current_stage = self.dialogue.state["current_stage"]
            stage_display = self._get_stage_display(current_stage)
            print(f"\n--- 현재 단계: {stage_display} ({current_stage}) ---")
            
            # 오프닝 단계이고 이미 오프닝 메시지가 있는 경우 건너뛰기
            if current_stage == DebateStage.OPENING and len(self.dialogue.state["speaking_history"]) > 0:
                # 이미 생성된 오프닝 메시지가 있는지 확인
                opening_messages = [msg for msg in self.dialogue.state["speaking_history"] 
                                  if msg.get("stage") == DebateStage.OPENING]
                if opening_messages:
                    # 이미 생성된 오프닝 메시지 출력
                    latest_opening = opening_messages[-1]
                    print(f"\n진행자 (moderator):")
                    print(f"{latest_opening.get('text', '')}\n")
                    
                    # 메시지 기록
                    messages.append({
                        "speaker_id": latest_opening.get("speaker_id", "Moderator"),
                        "speaker_name": "진행자",
                        "role": "moderator",
                        "message": latest_opening.get("text", ""),
                        "stage": current_stage,
                        "turn": turn
                    })
                    
                    # 오프닝 단계 완료 처리 - 다음 단계로 강제 전환
                    self.dialogue.state["current_stage"] = DebateStage.PRO_ARGUMENT
                    print(f"오프닝 완료. 다음 단계로 전환: {DebateStage.PRO_ARGUMENT}")
                    
                    turn += 1
                    time.sleep(0.5)
                    continue
            
            # 응답 생성 및 관련 컨텍스트 출력
            response = self.dialogue.generate_response()
            
            # 응답 처리
            if response["status"] == "success":
                speaker_id = response["speaker_id"]
                role = response["role"]
                message = response["message"]
                
                # 발언자 이름 결정
                speaker_name = speaker_id
                if role == ParticipantRole.MODERATOR:
                    speaker_name = "진행자"
                elif role == ParticipantRole.PRO:
                    speaker_name = self.participants["pro"]["name"]
                elif role == ParticipantRole.CON:
                    speaker_name = self.participants["con"]["name"]
                
                # 메시지 출력
                print(f"\n{speaker_name} ({role}):")
                print(f"{message}\n")
                
                # RAG 검색 결과 추출 (참가자 에이전트인 경우)
                if role in ["pro", "con"] and current_stage in [DebateStage.PRO_ARGUMENT, DebateStage.CON_ARGUMENT]:
                    # 올바른 키로 에이전트 접근
                    role_key = ParticipantRole.PRO if role == "pro" else ParticipantRole.CON
                    agent = self.agents.get(role_key)
                    if agent and hasattr(agent, 'core_arguments') and hasattr(agent, 'argument_queries'):
                        rag_search_results[f"{role}_arguments"] = {
                            "speaker_id": speaker_id,
                            "speaker_name": speaker_name,
                            "stage": current_stage,
                            "core_arguments": agent.core_arguments,
                            "argument_queries": agent.argument_queries,
                            "prepared_argument": getattr(agent, 'prepared_argument', '')
                        }
                        
                        # RAG 검색 결과 간단 출력
                        print(f"=== {speaker_name}의 RAG 검색 결과 ===")
                        print(f"핵심 주장 수: {len(agent.core_arguments)}")
                        print(f"검색 쿼리 수: {len(agent.argument_queries)}")
                        for i, query_data in enumerate(agent.argument_queries):
                            for evidence in query_data.get("evidence", []):
                                query = evidence.get("query", "")
                                source = evidence.get("source", "")
                                results_count = len(evidence.get("results", []))
                                print(f"  쿼리 {i+1}: '{query}' (출처: {source}, 결과: {results_count}개)")
                        print()
                    else:
                        print(f"=== {speaker_name}의 RAG 검색 결과 없음 ===")
                        print(f"Agent: {agent}")
                        print(f"Has core_arguments: {hasattr(agent, 'core_arguments') if agent else False}")
                        print(f"Has argument_queries: {hasattr(agent, 'argument_queries') if agent else False}")
                        print()
                
                # 관련 컨텍스트 조회 (마지막 발언에 대해)
                if self.dialogue.vector_store and turn > 0:
                    results = self.dialogue.vector_store.search(message, limit=1)
                    if results:
                        print("관련 컨텍스트:")
                        for result in results:
                            print(f"- (점수: {result['score']:.4f}) {result['text']}\n")
                
                # 메시지 기록
                messages.append({
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "role": role,
                    "message": message,
                    "stage": current_stage,
                    "turn": turn
                })
                
                # 다음 턴으로 진행
                turn += 1
                
                # 잠시 대기 (출력 확인을 위해)
                time.sleep(0.5)
            elif response["status"] == "waiting_for_user":
                print("사용자 입력 대기 중... (테스트에서는 지원하지 않음)")
                break
            elif response["status"] == "error":
                print(f"에러 발생: {response.get('reason', '알 수 없는 오류')}")
                break
            else:
                print(f"처리할 수 없는 응답: {response}")
                break
        
        # 토론 결과 저장 (RAG 검색 결과 포함)
        self._save_results_with_rag(messages, rag_search_results)
        
        print(f"\n===== 토론 테스트 완료: 총 {turn}턴 진행됨 =====\n")
    
    def _get_stage_display(self, stage: str) -> str:
        """단계 코드를 표시용 이름으로 변환"""
        stage_names = {
            DebateStage.OPENING: "오프닝",
            DebateStage.PRO_ARGUMENT: "찬성측 입론",
            DebateStage.CON_ARGUMENT: "반대측 입론",
            DebateStage.MODERATOR_SUMMARY_1: "모더레이터 1차 요약",
            DebateStage.PRO_REBUTTAL: "찬성측 반론",
            DebateStage.CON_REBUTTAL: "반대측 반론",
            DebateStage.MODERATOR_SUMMARY_2: "모더레이터 2차 요약",
            DebateStage.CON_TO_PRO_QA: "반대측→찬성측 질의응답",
            DebateStage.PRO_TO_CON_QA: "찬성측→반대측 질의응답",
            DebateStage.MODERATOR_SUMMARY_3: "모더레이터 3차 요약",
            DebateStage.PRO_CONCLUSION: "찬성측 최종결론",
            DebateStage.CON_CONCLUSION: "반대측 최종결론",
            DebateStage.CLOSING: "마무리",
            DebateStage.COMPLETED: "완료"
        }
        return stage_names.get(stage, stage)
    
    def _save_results_with_rag(self, messages: List[Dict[str, Any]], rag_search_results: Dict[str, Any]):
        """토론 결과 및 RAG 검색 결과 저장"""
        result = {
            "topic": self.topic,
            "context": self.context,
            "participants": self.participants,
            "stance_statements": self.stance_statements,
            "messages": messages,
            "rag_search_results": rag_search_results,
            "timestamp": time.strftime("%Y%m%d_%H%M%S")
        }
        
        # 결과 저장 디렉토리 생성
        os.makedirs("debate_results", exist_ok=True)
        
        # 파일명 생성 및 저장
        filename = f"debate_results/debate_with_rag_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"토론 결과 및 RAG 검색 데이터가 {filename}에 저장되었습니다.")
        
        # RAG 검색 결과만 별도 파일로도 저장
        rag_filename = f"debate_results/rag_search_only_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(rag_filename, "w", encoding="utf-8") as f:
            json.dump(rag_search_results, f, ensure_ascii=False, indent=2)
        
        print(f"RAG 검색 결과만 {rag_filename}에 별도 저장되었습니다.")


def main():
    """메인 실행 함수"""
    # 토론 테스트 인스턴스 생성
    test = DebateTest()
    
    # 입론단계까지만 테스트 실행
    test.run_debate_with_context_retrieval(
        max_turns=5,
        stages_to_test=[
            DebateStage.OPENING,
            DebateStage.PRO_ARGUMENT,
            DebateStage.CON_ARGUMENT
        ]
    )


if __name__ == "__main__":
    main() 