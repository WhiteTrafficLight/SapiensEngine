"""
User vs AI 대화식 토론 실험: 유저 vs 마르크스
Hybrid Progressive Strategy 적용 - 유저가 직접 공격하고 AI가 방어하는 대화형 시스템
"""

import os
import time
from debate_tools import DebateExperiment

class UservsAIDebateExperiment(DebateExperiment):
    """User vs AI 대화식 토론 실험"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.user_name = "사용자"
        
    def run_experiment(self, use_web_search: bool = True):
        """대화식 토론 실험 실행"""
        print("👤 User vs AI 대화식 토론 실험 시작!")
        print(f"📋 주제: {self.context.topic}")
        print(f"🔬 웹서치 사용: {'예' if use_web_search else '아니오'}")
        print("\n" + "="*80)
        
        # 1. 실험 안내
        self._print_experiment_guide()
        
        # 2. 마르크스의 입론 출력
        print("\n📜 마르크스의 입론을 먼저 보겠습니다:")
        self.print_message("마르크스 (Karl Marx)", self.marx_opening, "OPENING")
        self.log_exchange("마르크스", self.marx_opening, "opening", None, None, None)
        
        # 3. 대화식 토론 루프
        current_argument = self.marx_opening
        round_count = 0
        
        while True:
            round_count += 1
            print(f"\n🔄 라운드 {round_count}")
            print("=" * 40)
            
            try:
                # 3-1. 유저의 공격 입력받기
                user_attack = self._get_user_attack(round_count)
                
                if not user_attack:
                    print("👋 토론을 종료합니다.")
                    break
                
                # 유저 공격 기록 및 출력
                self.print_message(f"{self.user_name}", user_attack, "USER_ATTACK")
                self.log_exchange(self.user_name, user_attack, "user_attack", None, None, None)
                
                # 3-2. 마르크스의 분석 및 방어 (내부적으로만 분석, 사용자에게는 방어만 보여줌)
                print(f"🛡️  마르크스가 방어를 준비 중입니다...")
                time.sleep(1)  # 사실적인 대기 시간
                
                defense_result = self.debate_tool.generate_defense_response(
                    "marx", user_attack, self.context, use_web_search
                )
                
                if defense_result["status"] != "success":
                    print("❌ 마르크스의 방어 생성에 실패했습니다.")
                    continue
                
                defense_message = defense_result["response"]
                defense_citations = defense_result.get("citations", [])
                
                # 마르크스의 방어 출력
                self.print_message(
                    "마르크스 (Karl Marx)",
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
                    "마르크스",
                    defense_message,
                    "defense",
                    defense_citations,
                    defense_result
                )
                
                # 다음 라운드를 위해 현재 논증 업데이트
                current_argument = defense_message
                
                # 계속할지 묻기
                if not self._ask_continue():
                    break
                    
            except KeyboardInterrupt:
                print("\n\n⏹️  토론이 중단되었습니다.")
                break
            except Exception as e:
                print(f"\n❌ 오류 발생: {str(e)}")
                continue
        
        # 4. 실험 완료
        print(f"\n🏁 토론 종료!")
        print(f"📊 총 {round_count}라운드 진행됨")
        print(f"💬 총 {len(self.debate_history)}개의 발언 기록됨")
        
        # 5. 결과 저장
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"src/new_agent/experiment_cross/user_vs_ai_result_{timestamp}.json"
        self.save_results(filename)
        
        return self.debate_history
    
    def _print_experiment_guide(self):
        """실험 안내 출력"""
        print("""
📖 토론 안내:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 당신의 역할: 
   - 마르크스의 입론을 비판하고 반박하는 역할
   - 경제적 불평등이 "도덕적 실패"라는 마르크스의 주장에 도전하세요
   - 불평등이 "필요악"이라는 관점에서 공격해보세요

🎯 토론 주제: 경제적 불평등은 필요악인가 도덕적 실패인가?
   - 마르크스 입장(PRO): 경제적 불평등은 도덕적 실패
   - 당신 입장(CON): 경제적 불평등은 필요악

💡 공격 팁:
   - 불평등이 혁신을 촉진한다고 주장해보세요
   - 자원 배분의 효율성을 강조해보세요  
   - 마르크스의 논리적 허점을 지적해보세요
   - 현실적인 사례나 데이터를 활용해보세요

⌨️  입력 방법:
   - 여러 줄 입력 가능 (마지막에 빈 줄 입력하면 전송)
   - 'quit', 'exit', '종료'를 입력하면 토론 종료
   - Ctrl+C로도 중단 가능

🤖 마르크스는 웹서치를 통해 최신 정보로 반박할 예정입니다!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
    
    def _get_user_attack(self, round_count: int) -> str:
        """유저의 공격 입력받기"""
        print(f"\n💬 라운드 {round_count}: 마르크스의 {'입론' if round_count == 1 else '방어'}에 대한 당신의 반박을 입력하세요:")
        print("   (여러 줄 입력 가능, 마지막에 빈 줄을 입력하면 전송됩니다)")
        print("-" * 60)
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip().lower() in ['quit', 'exit', '종료']:
                    return None
                if line.strip() == "" and lines:  # 빈 줄이고 이미 입력이 있으면 종료
                    break
                if line.strip() != "":  # 빈 줄이 아니면 추가
                    lines.append(line)
            except EOFError:
                break
        
        user_input = "\n".join(lines).strip()
        
        if not user_input:
            print("❌ 입력이 없습니다. 다시 시도해주세요.")
            return self._get_user_attack(round_count)
        
        return user_input
    
    def _ask_continue(self) -> bool:
        """계속할지 묻기"""
        while True:
            try:
                response = input("\n🔄 계속 토론하시겠습니까? (y/n): ").strip().lower()
                if response in ['y', 'yes', '예', 'ㅇ']:
                    return True
                elif response in ['n', 'no', '아니오', 'ㄴ']:
                    return False
                else:
                    print("   y(예) 또는 n(아니오)를 입력해주세요.")
            except EOFError:
                return False
    
    def run_quick_test(self):
        """빠른 테스트 모드 (미리 정의된 공격으로)"""
        print("⚡ 빠른 테스트 모드!")
        
        # 미리 정의된 테스트 공격들
        test_attacks = [
            """마르크스님, 당신의 논리에는 치명적인 결함이 있습니다. 

경제적 불평등이 혁신을 저해한다고 하셨지만, 실제로는 정반대입니다. 실리콘밸리의 성공 사례를 보세요. 스타트업 창업자들은 바로 경제적 격차를 줄이고자 하는 동기로 혁신적인 기술을 개발합니다. 

또한 불평등이 자원배분을 왜곡한다고 하셨지만, 시장경제에서는 가격 메커니즘이 가장 효율적으로 자원을 배분합니다. 당신이 말하는 '계급투쟁'보다는 경쟁을 통한 발전이 훨씬 현실적이지 않나요?""",
            
            """마르크스님의 이상은 아름답지만 현실적이지 않습니다.

소련과 중국이 공산주의를 시도했지만 결국 시장경제로 돌아왔습니다. 이는 완전한 평등이 인간의 본성과 맞지 않음을 보여줍니다. 

북유럽 국가들조차 높은 세율과 복지제도를 유지하면서도 기본적으로는 자본주의 체제를 기반으로 합니다. 적절한 불평등은 사회 발전의 원동력이 아닐까요?""",
            
            """마르크스님, 시간이 당신을 비껴갔군요.

현대의 기술 혁신가들 - 빌 게이츠, 스티브 잡스, 엘론 머스크 - 이들은 모두 불평등한 사회에서 태어나 더 큰 불평등을 만들었지만, 동시에 인류 전체의 삶의 질을 향상시켰습니다. 

당신의 19세기 공장 노동자 관점으로는 21세기의 지식경제를 이해할 수 없을 것입니다."""
        ]
        
        # 마르크스 입론 출력
        self.print_message("마르크스 (Karl Marx)", self.marx_opening, "OPENING")
        self.log_exchange("마르크스", self.marx_opening, "opening", None, None, None)
        
        # 각 테스트 공격 수행
        for i, attack in enumerate(test_attacks, 1):
            print(f"\n🔄 테스트 라운드 {i}")
            print("=" * 40)
            
            # 유저 공격
            self.print_message(f"{self.user_name} (테스트)", attack, "USER_ATTACK")
            self.log_exchange(f"{self.user_name}_test", attack, "user_attack", None, None, None)
            
            # 마르크스 방어
            print("🛡️  마르크스가 방어 중...")
            defense_result = self.debate_tool.generate_defense_response(
                "marx", attack, self.context, True
            )
            
            if defense_result["status"] == "success":
                defense_message = defense_result["response"]
                defense_citations = defense_result.get("citations", [])
                
                self.print_message(
                    "마르크스 (Karl Marx)",
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
                
                self.log_exchange("마르크스", defense_message, "defense", defense_citations, defense_result)
            else:
                print("❌ 방어 생성 실패")
            
            time.sleep(2)
        
        # 결과 저장
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"src/new_agent/experiment_cross/quick_test_result_{timestamp}.json"
        self.save_results(filename)

def main():
    """메인 실행 함수"""
    # OpenAI API 키 설정
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수를 설정해주세요.")
        return
    
    print("👤 User vs AI 토론 실험을 시작합니다!")
    print("=" * 60)
    print("📌 실험 설정:")
    print("   - 주제: 경제적 불평등은 필요악인가 도덕적 실패인가?")
    print("   - 참가자: 당신(CON) vs 마르크스(PRO)")
    print("   - 시작: 마르크스의 입론")
    print("   - 진행: 당신 공격 → 마르크스 방어 → 반복")
    print("   - 종료: 당신이 원할 때")
    print("=" * 60)
    
    # 모드 선택
    print("\n🎮 실험 모드를 선택하세요:")
    print("   1. 대화형 모드 (직접 입력)")
    print("   2. 빠른 테스트 모드 (미리 정의된 공격)")
    
    while True:
        mode = input("\n모드 선택 (1 또는 2): ").strip()
        if mode in ['1', '2']:
            break
        print("1 또는 2를 입력해주세요.")
    
    # 웹서치 사용 여부 (빠른 테스트는 자동으로 ON)
    if mode == '1':
        use_web = input("\n🌐 웹서치를 사용하시겠습니까? (y/n, 기본값 y): ").strip().lower()
        use_web_search = use_web != 'n'
    else:
        use_web_search = True
    
    print(f"\n⚡ 실험 시작! (웹서치: {'ON' if use_web_search else 'OFF'})")
    
    # 실험 실행
    experiment = UservsAIDebateExperiment(api_key)
    
    if mode == '1':
        print("   직접 입력으로 토론하세요. 중단하려면 'quit'를 입력하세요.\n")
        experiment.run_experiment(use_web_search)
    else:
        print("   빠른 테스트 모드로 진행합니다.\n")
        experiment.run_quick_test()

if __name__ == "__main__":
    main() 