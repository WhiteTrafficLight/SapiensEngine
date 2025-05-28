"""
철학자 스타일 토론 메시지 생성 테스트

이 모듈은 주어진 토론 주제에 대해 다양한 철학자들의 스타일로
찬성/반대 입장의 토론 메시지를 생성하는 기능을 테스트합니다.
"""

import sys
import os
import json
from typing import Dict, List, Any, Tuple
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

# LLMManager 임포트
from src.models.llm.llm_manager import LLMManager

class PhilosopherStyleGenerator:
    """
    다양한 철학자들의 스타일로 토론 메시지를 생성하는 클래스
    """
    
    def __init__(self):
        """초기화"""
        self.llm_manager = LLMManager()
        
        # 철학자별 기본 특성 정의
        self.philosopher_characteristics = {
            "nietzsche": {
                "name": "Friedrich Nietzsche",
                "key_concepts": "will to power, übermensch, eternal recurrence, revaluation of values, nihilism",
                "style": "aphoristic, poetic, provocative, challenging traditional morality, questioning conventional wisdom",
                "works": "Thus Spoke Zarathustra, Beyond Good and Evil, On the Genealogy of Morality"
            },
            "hegel": {
                "name": "Georg Wilhelm Friedrich Hegel",
                "key_concepts": "dialectic, Absolute Spirit, thesis-antithesis-synthesis, historical development, Zeitgeist",
                "style": "systematic, complex, abstract, conceptual, historically oriented, emphasizing process and contradiction",
                "works": "Phenomenology of Spirit, Science of Logic, Elements of the Philosophy of Right"
            },
            "camus": {
                "name": "Albert Camus",
                "key_concepts": "absurdism, revolt, suicide, meaninglessness, authenticity, the stranger",
                "style": "clear, literary, existential, philosophical fiction, examining life's contradictions",
                "works": "The Myth of Sisyphus, The Stranger, The Rebel, The Plague"
            },
            "marx": {
                "name": "Karl Marx",
                "key_concepts": "historical materialism, class struggle, alienation, capitalism critique, commodity fetishism, dialectical materialism",
                "style": "analytical, critique-oriented, historically grounded, focused on material conditions and economic structures",
                "works": "The Communist Manifesto, Das Kapital, Economic and Philosophic Manuscripts of 1844"
            }
        }
    
    def generate_philosophical_argument(
        self, 
        topic: str,
        philosopher: str,
        position: str,
        reference_argument: str = None
    ) -> str:
        """
        특정 철학자의 스타일로 토론 메시지 생성
        
        Args:
            topic: 토론 주제
            philosopher: 철학자 ID (nietzsche, hegel, camus, marx)
            position: 찬성(pro) 또는 반대(con)
            reference_argument: 참조할 기존 논증 (선택 사항)
            
        Returns:
            생성된 토론 메시지
        """
        if philosopher.lower() not in self.philosopher_characteristics:
            raise ValueError(f"지원하지 않는 철학자입니다: {philosopher}")
        
        # 철학자 정보 가져오기
        phil_info = self.philosopher_characteristics[philosopher.lower()]
        
        # 시스템 프롬프트 구성
        system_prompt = f"""
당신은 독특한 스타일과 철학적 접근법을 가진 철학자 {phil_info['name']}입니다.

당신의 주요 개념: {phil_info['key_concepts']}
당신의 글쓰기 스타일: {phil_info['style']}
당신의 주요 저작: {phil_info['works']}

당신은 "{topic}"에 관한 토론에 참여하고 있습니다. 당신은 이 주제에 대해 {'찬성' if position.lower() == 'pro' else '반대'} 입장을 주장할 것입니다.

다음과 같은 토론 연설을 한국어로 작성하세요:
1. 당신의 고유한 철학적 관점과 개념을 반영
2. 당신만의 독특한 글쓰기 스타일, 어휘, 수사적 접근법 사용
3. 이 현대적 이슈를 분석하기 위해 당신의 철학적 프레임워크 적용
4. 당신의 핵심 아이디어와 가능하다면 당신의 저작을 참조
5. 서론, 주요 논점, 결론을 갖춘 일관된 논증 구성

이 현대적인 주제에 참여하면서 당신의 철학적 목소리를 진정성 있게 표현하세요.
모든 응답은 반드시 한국어로 작성해야 합니다. 문어체가 아닌 대화체로 작성해야합니다.
"""

        # 유저 프롬프트 구성
        user_prompt = f"""
다음 주제에 대해 {'찬성' if position.lower() == 'pro' else '반대'} 입장의 토론 논증을 한국어로 작성해 주세요: {topic}

트랜스휴머니즘이란 기술을 통해 인간의 지적, 신체적, 심리적 능력을 향상시켜 인간의 조건을 근본적으로 변화시키는 사상입니다. 여기에는 생명 연장, 인간-기계 결합, 유전자 조작, 인공지능과의 통합 등이 포함됩니다.

찬성 측은 이것이 인류의 진화적 도약이라고 주장하며, 반대 측은 인간성의 본질적 가치와 존엄성을 해칠 수 있다고 우려합니다.

당신의 논증은 다음을 포함해야 합니다:
- 당신의 철학적 관점을 반영하는 트랜스휴머니즘에 대한 견해
- 이 현대적 논쟁에 당신의 핵심 개념을 적용
- 당신의 진정한 목소리와 스타일 유지
- 당신의 철학과 일치하는 설득력 있고 논리적인 주장
- 약 500-700단어 길이의 논증

"""

        # 참조 논증이 있는 경우 추가
        if reference_argument:
            user_prompt += f"""
참고로, 다음은 이 주제에 대한 표준 논증입니다. 당신의 철학적 렌즈를 통해 재해석해 보세요:

참조 논증:
{reference_argument}

이 논증을 단순히 재진술하지 말고, 당신의 철학적 프레임워크에 기반한 고유한 관점을 개발하세요.
"""

        # LLM 호출
        response = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=2000
        )
        
        return response
    
    def generate_all_philosophers(
        self, 
        topic: str,
        reference_argument: str = None
    ) -> Dict[str, Dict[str, str]]:
        """
        모든 철학자에 대해 찬성/반대 입장의 토론 메시지 생성
        
        Args:
            topic: 토론 주제
            reference_argument: 참조할 기존 논증 (선택 사항)
            
        Returns:
            철학자별 찬성/반대 메시지를 포함한 딕셔너리
        """
        results = {}
        
        # 철학자별 입장 설정
        philosophers_positions = {
            "nietzsche": "pro",
            #"hegel": "pro",
            "camus": "con",
            #"marx": "con"
        }
        
        # 각 철학자에 대해 메시지 생성
        for philosopher, position in philosophers_positions.items():
            print(f"{philosopher.capitalize()} ({position}) 스타일 메시지 생성 중...")
            
            message = self.generate_philosophical_argument(
                topic=topic,
                philosopher=philosopher,
                position=position,
                reference_argument=reference_argument
            )
            
            results[philosopher] = {
                "name": self.philosopher_characteristics[philosopher]["name"],
                "position": position,
                "message": message
            }
            
            print(f"{philosopher.capitalize()} 메시지 생성 완료 ({len(message)} 자)")
        
        return results


def test_philosopher_styles():
    """철학자 스타일 메시지 생성 테스트 함수"""
    
    # 토론 주제
    topic = "트랜스 휴머니즘, 인류의 도약인가 아니면 인간성의 종말인가?"
    
    # RAG로 강화된 참조 메시지 (JSON 파일에서 로드)
    reference_message = ""
    try:
        result_file = Path("debate_rag_results.json")
        if result_file.exists():
            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "enhanced_message" in data:
                    reference_message = data["enhanced_message"]
                    print("참조 메시지를 debate_rag_results.json에서 로드했습니다.")
    except Exception as e:
        print(f"참조 메시지 로드 실패: {str(e)}")
    
    # 참조 메시지가 없는 경우 기본 메시지 사용
    if not reference_message:
        reference_message = """
트랜스휴머니즘에 관한 논쟁에서 저는 찬성의 입장을 취하고자 합니다.

트랜스휴머니즘은 기술을 통해 인간의 지적, 신체적, 정신적 능력을 향상시켜 인류의 조건을 근본적으로 개선하려는 움직임입니다. 이는 생명 연장, 질병 제거, 인지 능력 향상, 그리고 궁극적으로는 노화와 죽음의 극복까지도 포함합니다.

우선, 트랜스휴머니즘은 인간 진화의 자연스러운 연장선상에 있습니다. 인류는 도구 사용, 언어 발달, 농업혁명, 산업혁명을 거쳐 끊임없이 환경을 개조하고 자신의 능력을 확장해왔습니다. 현대 의학, 스마트폰, 인터넷은 이미 우리의 능력을 '향상'시키는 기술입니다. 트랜스휴머니즘은 이 진화적 과정의 의식적이고 적극적인 단계로 볼 수 있습니다.

둘째, 트랜스휴머니즘은 인류가 직면한 가장 근본적인 문제들에 대한 해결책을 제시합니다. 노화와 질병은 인간의 고통과 제한된 잠재력의 주요 원인입니다. 생명공학, 나노기술, 인공지능의 발전은 이러한 제약을 극복할 수 있는 가능성을 제시합니다. 예를 들어, 유전자 편집 기술 CRISPR는 유전병 치료에 혁명을 가져오고 있으며, 뇌-컴퓨터 인터페이스는 장애인들에게 새로운 가능성을 열어주고 있습니다.

셋째, 트랜스휴머니즘은 개인의 자율성과 선택의 자유를 존중합니다. 사람들은 자신의 몸과 마음을 개선하기 위한 기술을 선택적으로 사용할 수 있어야 합니다. 이는 자기결정권의 확장으로 볼 수 있으며, 개인이 자신의 잠재력을 최대한 발휘할 수 있도록 합니다.

물론 반대 측에서는 트랜스휴머니즘이 인간성의 본질을 위협하고, 사회적 불평등을 심화시키며, 예측할 수 없는 위험을 초래할 수 있다고 주장합니다. 이러한 우려는 진지하게 고려되어야 하지만, 적절한 규제와 사회적 합의를 통해 관리될 수 있습니다.

트랜스휴머니즘 기술에 대한 접근성 보장, 윤리적 가이드라인 수립, 국제적 협력을 통해 이러한 기술이 특권층만의 전유물이 되지 않도록 해야 합니다. 또한, 인간 존엄성의 개념을 확장하여 향상된 인간(트랜스휴먼)도 포함하는 새로운 윤리적 프레임워크를 발전시켜야 합니다.

결론적으로, 트랜스휴머니즘은 인류에게 전례 없는 발전과 성장의 기회를 제공합니다. 신중하고 책임감 있게 접근한다면, 이는 인간성의 종말이 아닌 인류의 새로운 도약이 될 것입니다. 우리는 기술의 발전을 두려워하기보다는, 이를 인류의 잠재력을 극대화하고 더 나은 미래를 창조하는 도구로 활용해야 합니다.
"""
        print("기본 참조 메시지를 사용합니다.")
    
    # 스타일 생성기 인스턴스 생성
    style_generator = PhilosopherStyleGenerator()
    
    # 모든 철학자에 대해 메시지 생성
    results = style_generator.generate_all_philosophers(
        topic=topic,
        reference_argument=reference_message
    )
    
    # 결과 출력
    print("\n===== 철학자별 토론 메시지 =====\n")
    
    for philosopher, data in results.items():
        print(f"===== {data['name']} ({data['position'].upper()}) =====\n")
        print(data['message'])
        print("\n" + "=" * 50 + "\n")
    
    # JSON 파일로 결과 저장
    output_file = "philosopher_styles_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"결과가 {output_file}에 저장되었습니다.")


if __name__ == "__main__":
    test_philosopher_styles() 