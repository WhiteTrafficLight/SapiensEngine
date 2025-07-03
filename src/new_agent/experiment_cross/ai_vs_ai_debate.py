"""
AI vs AI 자동 토론 실험: 아리스토텔레스 vs 마르크스
Hybrid Progressive Strategy 적용 - 복잡한 멀티에이전트 시스템을 OpenAI Tool Calling으로 단순화
"""

import os
import time
from debate_tools import DebateExperiment

class AIvsAIDebateExperiment(DebateExperiment):
    """AI vs AI 자동 토론 실험"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.max_rounds = 5  # 최대 라운드 수
        self.current_round = 0
        
    def run_experiment(self, use_web_search: bool = True):
        """자동 토론 실험 실행"""
        print("🤖 AI vs AI 자동 토론 실험 시작!")
        print(f"📋 주제: {self.context.topic}")
        print(f"🔬 웹서치 사용: {'예' if use_web_search else '아니오'}")
        print(f"🔄 최대 라운드: {self.max_rounds}")
        print("\n" + "="*80)
        
        # 1. 마르크스의 입론 출력
        self.print_message("마르크스 (Karl Marx)", self.marx_opening, "OPENING")
        self.log_exchange("마르크스", self.marx_opening, "opening", None, None, None)
        
        # 2. 현재 논증: 마르크스의 입론으로 시작
        current_argument = self.marx_opening
        current_defender = "marx"
        current_attacker = "aristotle"
        
        # 3. 자동 토론 루프
        while self.current_round < self.max_rounds:
            self.current_round += 1
            print(f"\n🔄 라운드 {self.current_round}/{self.max_rounds}")
            print(f"⚔️  {self.debate_tool.philosophers[current_attacker].korean_name} → {self.debate_tool.philosophers[current_defender].korean_name}")
            
            try:
                # 3-1. 공격자가 현재 논증 분석
                print(f"🔍 {self.debate_tool.philosophers[current_attacker].korean_name}가 논증 분석 중...")
                analysis_result = self.debate_tool.analyze_opponent_argument(
                    current_attacker, current_argument, self.context
                )
                
                if analysis_result["status"] != "success":
                    print(f"❌ 분석 실패: {analysis_result.get('message', 'Unknown error')}")
                    break
                
                analysis = analysis_result["analysis"]
                print(f"✅ 분석 완료 - 취약성 점수: {analysis.get('vulnerability_score', 0.0):.2f}")
                print(f"🎯 공격 전략: {analysis.get('attack_strategy', 'Unknown')}")
                
                # 3-2. 공격 응답 생성
                print(f"⚔️  {self.debate_tool.philosophers[current_attacker].korean_name}가 공격 중...")
                attack_result = self.debate_tool.generate_attack_response(
                    current_attacker, analysis, current_argument, self.context, use_web_search
                )
                
                if attack_result["status"] != "success":
                    print(f"❌ 공격 생성 실패")
                    break
                
                attack_message = attack_result["response"]
                attack_citations = attack_result.get("citations", [])
                
                # 공격 메시지 출력
                self.print_message(
                    f"{self.debate_tool.philosophers[current_attacker].korean_name} ({self.debate_tool.philosophers[current_attacker].name})",
                    attack_message,
                    "ATTACK",
                    attack_citations,
                    analysis,
                    {
                        "rag_used": attack_result.get("rag_used", False),
                        "rag_decision_reason": attack_result.get("rag_decision_reason", ""),
                        "attack_strategy": attack_result.get("attack_strategy", "Unknown"),
                        "target": attack_result.get("target", "Unknown")
                    }
                )
                
                # 기록 저장
                self.log_exchange(
                    self.debate_tool.philosophers[current_attacker].korean_name,
                    attack_message,
                    "attack",
                    attack_citations,
                    {**analysis, **attack_result}  # 분석과 공격 결과 모두 저장
                )
                
                # 짧은 대기
                time.sleep(2)
                
                # 3-3. 방어자가 방어 응답 생성
                print(f"🛡️  {self.debate_tool.philosophers[current_defender].korean_name}가 방어 중...")
                defense_result = self.debate_tool.generate_defense_response(
                    current_defender, attack_message, self.context, use_web_search
                )
                
                if defense_result["status"] != "success":
                    print(f"❌ 방어 생성 실패")
                    break
                
                defense_message = defense_result["response"]
                defense_citations = defense_result.get("citations", [])
                
                # 방어 메시지 출력
                self.print_message(
                    f"{self.debate_tool.philosophers[current_defender].korean_name} ({self.debate_tool.philosophers[current_defender].name})",
                    defense_message,
                    "DEFENSE",
                    defense_citations,
                    None,  # 방어에는 분석 정보 없음
                    {
                        "rag_used": defense_result.get("rag_used", False),
                        "rag_decision_reason": defense_result.get("rag_decision_reason", ""),
                        "defense_strategy": defense_result.get("defense_strategy", "Unknown"),
                        "attack_type_detected": defense_result.get("attack_type_detected", "Unknown"),
                        "attacker": defense_result.get("attacker", "Unknown")
                    }
                )
                
                # 기록 저장
                self.log_exchange(
                    self.debate_tool.philosophers[current_defender].korean_name,
                    defense_message,
                    "defense",
                    defense_citations,
                    defense_result  # 방어 결과 정보 저장
                )
                
                # 3-4. 다음 라운드를 위한 역할 교체
                current_argument = defense_message  # 방어 메시지가 다음 공격 대상
                current_attacker, current_defender = current_defender, current_attacker  # 역할 교체
                
                # 라운드 간 대기
                time.sleep(3)
                
            except KeyboardInterrupt:
                print("\n\n⏹️  사용자에 의해 실험이 중단되었습니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {str(e)}")
                break
        
        # 4. 실험 완료
        print(f"\n🏁 실험 완료!")
        print(f"📊 총 {self.current_round}라운드 진행됨")
        print(f"💬 총 {len(self.debate_history)}개의 발언 기록됨")
        
        # 5. 결과 저장
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"src/new_agent/experiment_cross/ai_vs_ai_result_{timestamp}.json"
        self.save_results(filename)
        
        return self.debate_history

def main():
    """메인 실행 함수"""
    # OpenAI API 키 설정
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수를 설정해주세요.")
        return
    
    print("🤖 AI vs AI 토론 실험을 시작합니다!")
    print("=" * 60)
    print("📌 실험 설정:")
    print("   - 주제: 경제적 불평등은 필요악인가 도덕적 실패인가?")
    print("   - 참가자: 마르크스(PRO) vs 아리스토텔레스(CON)")
    print("   - 시작: 마르크스의 입론")
    print("   - 진행: 아리스토텔레스 공격 → 마르크스 방어 → 반복")
    print("   - 종료: 5라운드 또는 Ctrl+C")
    print("=" * 60)
    
    # 웹서치 사용 여부 선택
    use_web = input("\n🌐 웹서치를 사용하시겠습니까? (y/n, 기본값 y): ").strip().lower()
    use_web_search = use_web != 'n'
    
    print(f"\n⚡ 실험 시작! (웹서치: {'ON' if use_web_search else 'OFF'})")
    print("   중단하려면 Ctrl+C를 누르세요.\n")
    
    # 실험 실행
    experiment = AIvsAIDebateExperiment(api_key)
    experiment.run_experiment(use_web_search)

if __name__ == "__main__":
    main() 