#!/usr/bin/env python3
"""
🧠 Hybrid Progressive Strategy 토론 실험 통합 실행기

기존 복잡한 멀티에이전트 시스템을 OpenAI Tool Calling으로 단순화한 실험
"""

import os
import sys
from ai_vs_ai_debate import main as ai_vs_ai_main
from user_vs_ai_debate import main as user_vs_ai_main

def print_banner():
    """실험 배너 출력"""
    print("""
🧠 ╔══════════════════════════════════════════════════════════════════════════════╗
   ║                    Hybrid Progressive Strategy 토론 실험                    ║
   ║                                                                              ║
   ║    기존 복잡한 멀티에이전트 시스템 → OpenAI Tool Calling 단순화 실험        ║
   ╚══════════════════════════════════════════════════════════════════════════════╝

📋 실험 주제: "경제적 불평등은 필요악인가 도덕적 실패인가?"
📜 마르크스의 입론: 제공됨 (UCL 웹서치 인용 포함)
🎯 목표: 속도↑ 퀄리티↑ 복잡도↓
""")

def check_requirements():
    """실험 실행 요구사항 확인"""
    print("🔍 실험 환경 확인 중...")
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   다음 명령어로 설정하세요:")
        print("   export OPENAI_API_KEY='your_api_key_here'")
        return False
    
    # OpenAI 패키지 확인
    try:
        import openai
        print(f"✅ OpenAI 패키지 확인됨 (버전: {openai.__version__})")
    except ImportError:
        print("❌ OpenAI 패키지가 설치되지 않았습니다.")
        print("   다음 명령어로 설치하세요:")
        print("   pip install openai>=1.50.0")
        return False
    
    print("✅ 모든 요구사항이 충족되었습니다!")
    return True

def show_experiment_options():
    """실험 옵션 표시"""
    print("""
🚀 실험 옵션을 선택하세요:

1️⃣  AI vs AI 자동 토론
    📌 참가자: 아리스토텔레스(CON) vs 마르크스(PRO)
    🔄 진행: 자동으로 5라운드 공격/방어 반복
    ⚡ 특징: 완전 자동화, 분석 정보 표시

2️⃣  User vs AI 대화식 토론  
    📌 참가자: 당신(CON) vs 마르크스(PRO)
    🔄 진행: 당신 공격 → 마르크스 방어 → 반복
    ⚡ 특징: 대화형, 다중 라인 입력, 테스트 모드

3️⃣  실험 정보 및 도움말
    📖 README 보기, 요구사항, 사용법 등

0️⃣  종료
""")

def show_help():
    """도움말 표시"""
    print("""
📖 실험 도움말
══════════════════════════════════════════════════════════════════════════════════

🎯 **실험 목표**
기존의 과도하게 복잡한 멀티에이전트 토론 시스템을 OpenAI Tool Calling으로 
단순화하여 속도와 품질을 향상시키는 것입니다.

🔄 **기존 시스템의 문제점**
1. 복잡한 모듈 체인: 분석 → RAG 결정 → 전략 선택 → 응답 생성
2. 느린 속도: 여러 모듈을 순차적으로 호출
3. 정보 손실: 모듈 간 데이터 전달 과정에서 손실
4. 유지보수 어려움: 복잡한 의존성 관계

💡 **새로운 접근법: "철학자의 두뇌" 시뮬레이션**
- OpenAI가 분석부터 응답까지 한 번에 처리
- Tool Calling으로 구조화된 분석 수행
- 웹서치 통합으로 최신 정보 활용
- 철학자별 고유 정체성과 스타일 반영

📊 **측정 지표**
- 응답 생성 시간
- 논리적 일관성과 철학적 깊이  
- 웹서치 인용의 정확성
- 사용자 경험 만족도

🎮 **실험 시나리오 예시**
1. 혁신 촉진 vs 혁신 저해 논쟁
2. 역사적 사례 (소련/중국 vs 북유럽 모델)
3. 현대 기술 혁신가들의 역할

💾 **결과 저장**
모든 토론 내용이 JSON 형태로 저장되어 추후 분석 가능합니다.

⚡ **빠른 시작**
OPENAI_API_KEY만 설정하면 바로 실험 가능합니다!
""")

def main():
    """메인 실행 함수"""
    print_banner()
    
    # 환경 확인
    if not check_requirements():
        sys.exit(1)
    
    while True:
        show_experiment_options()
        
        try:
            choice = input("🎯 선택하세요 (0-3): ").strip()
            
            if choice == "1":
                print("\n🤖 AI vs AI 자동 토론 실험을 시작합니다...")
                print("=" * 60)
                ai_vs_ai_main()
                
            elif choice == "2":
                print("\n👤 User vs AI 대화식 토론 실험을 시작합니다...")
                print("=" * 60)
                user_vs_ai_main()
                
            elif choice == "3":
                show_help()
                input("\n📖 계속하려면 Enter 키를 누르세요...")
                
            elif choice == "0":
                print("\n👋 실험을 종료합니다. 좋은 하루 되세요!")
                break
                
            else:
                print("❌ 잘못된 선택입니다. 0-3 사이의 숫자를 입력해주세요.")
                
        except KeyboardInterrupt:
            print("\n\n👋 실험이 중단되었습니다.")
            break
        except EOFError:
            print("\n\n👋 실험을 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류가 발생했습니다: {str(e)}")
            continue

if __name__ == "__main__":
    main() 