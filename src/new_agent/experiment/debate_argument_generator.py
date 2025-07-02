#!/usr/bin/env python3
"""
토론 입론 생성 실험

기존 토론 주제와 철학자 특성을 활용하여 
OpenAI 웹서치 툴로 근거를 보강한 입론을 자동 생성하는 실험
"""

import os
import sys
import json
import yaml
import time
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
import openai

# 현재 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'debate_argument_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

logger = logging.getLogger(__name__)

class DebateArgumentGenerator:
    """
    토론 입론 생성기
    
    웹서치 기반으로 철학자의 특성에 맞는 입론을 자동 생성
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        입론 생성기 초기화
        
        Args:
            openai_api_key: OpenAI API 키
        """
        self.api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다. OPENAI_API_KEY 환경변수를 설정해주세요.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        self.debate_data = None
        self.philosopher_data = None
        self.generation_history = []
        
        logger.info("Debate Argument Generator 초기화 완료")
    
    def load_debate_data(self, debate_json_path: str = "../../new/data/pregenerated_debates.json"):
        """토론 데이터 로드"""
        try:
            with open(debate_json_path, 'r', encoding='utf-8') as f:
                self.debate_data = json.load(f)
            
            topics_count = len(self.debate_data.get('topics', {}))
            logger.info(f"✅ 토론 데이터 로드 완료: {topics_count}개 주제")
            return True
            
        except Exception as e:
            logger.error(f"❌ 토론 데이터 로드 실패: {str(e)}")
            return False
    
    def load_philosopher_data(self, philosopher_yaml_path: str = "../../../philosophers/debate_optimized.yaml"):
        """철학자 데이터 로드"""
        try:
            with open(philosopher_yaml_path, 'r', encoding='utf-8') as f:
                self.philosopher_data = yaml.safe_load(f)
            
            philosophers_count = len(self.philosopher_data) if self.philosopher_data else 0
            logger.info(f"✅ 철학자 데이터 로드 완료: {philosophers_count}명")
            return True
            
        except Exception as e:
            logger.error(f"❌ 철학자 데이터 로드 실패: {str(e)}")
            return False
    
    def get_random_debate_setup(self) -> Optional[Dict[str, Any]]:
        """랜덤한 토론 설정 반환"""
        if not self.debate_data or not self.philosopher_data:
            logger.error("데이터가 로드되지 않았습니다.")
            return None
        
        # 랜덤 주제 선택
        topics = self.debate_data.get('topics', {})
        if not topics:
            logger.error("토론 주제가 없습니다.")
            return None
        
        topic_id = random.choice(list(topics.keys()))
        topic_data = topics[topic_id]
        
        # 찬반 중 랜덤 선택
        stance = random.choice(['pro', 'con'])
        
        # 해당 입장의 철학자 중 랜덤 선택
        if stance == 'pro':
            philosophers = topic_data['original_data'].get('pro_philosophers', [])
        else:
            philosophers = topic_data['original_data'].get('con_philosophers', [])
        
        if not philosophers:
            logger.error(f"주제 {topic_id}의 {stance} 철학자가 없습니다.")
            return None
        
        philosopher_name = random.choice(philosophers)
        
        # 철학자 정보 가져오기
        philosopher_info = self.philosopher_data.get(philosopher_name)
        if not philosopher_info:
            logger.error(f"철학자 {philosopher_name}의 정보가 없습니다.")
            return None
        
        return {
            'topic_id': topic_id,
            'topic_data': topic_data,
            'stance': stance,
            'philosopher_name': philosopher_name,
            'philosopher_info': philosopher_info
        }
    
    def create_argument_prompt(self, setup: Dict[str, Any]) -> str:
        """입론 생성을 위한 프롬프트 생성"""
        
        topic_data = setup['topic_data']
        philosopher_info = setup['philosopher_info']
        stance = setup['stance']
        
        # 기본 정보 추출
        title = topic_data.get('title', '알 수 없는 주제')
        context = topic_data['original_data'].get('context', {}).get('content', '')
        
        # 생성된 데이터에서 스탠스 진술과 컨텍스트 요약 가져오기
        generated_data = topic_data.get('generated_data', {})
        stance_statements = generated_data.get('stance_statements', {})
        context_summary = generated_data.get('context_summary', {})
        
        stance_statement = stance_statements.get(stance, '입장이 명시되지 않음')
        context_summary_text = context_summary.get('summary', '') if context_summary else ''
        key_points = context_summary.get('key_points', []) if context_summary else []
        
        # 철학자 특성
        essence = philosopher_info.get('essence', '')
        debate_style = philosopher_info.get('debate_style', '')
        personality = philosopher_info.get('personality', '')
        key_traits = philosopher_info.get('key_traits', [])
        signature_quote = philosopher_info.get('quote', '')
        
        # 입장 영어 변환
        stance_position = "supporting" if stance == "pro" else "opposing"
        
        prompt = f"""You are {setup['philosopher_name']} participating in a philosophical debate.

**Debate Topic**: {title}

**Context**: 
{context if context else context_summary_text}

**Key Issues**:
{chr(10).join([f"• {point}" for point in key_points]) if key_points else "No specific issues provided"}

**Your Position**: You are {stance_position} the topic. {stance_statement}

**Your Philosophical Identity**:
• Essence: {essence}
• Debate Style: {debate_style}
• Personality: {personality}
• Key Traits: {', '.join(key_traits) if key_traits else 'No traits provided'}
• Signature Quote: "{signature_quote}"

**Task**:
Deliver a compelling and authentic opening statement for this debate that truly sounds like YOU speaking. Your argument should flow naturally and embody your unique philosophical voice, reasoning style, and personality.

Your opening statement should include (but not be formatted as structured sections):
- A clear core argument that reflects your philosophical perspective
- Two major lines of reasoning that support your position
- A powerful conclusion that reinforces your stance

**Critical Requirements**:
1. **Authentic Voice**: Write as if you are actually speaking these words in your characteristic style. Use language, tone, and rhetorical patterns that match your philosophical persona.

2. **Web Research Integration**: Use web search to find recent studies, statistics, expert opinions, contemporary examples, or current events that strengthen your arguments. Weave these seamlessly into your natural speaking style.

3. **Philosophical Consistency**: Ensure your reasoning aligns with your philosophical framework and methodology.

4. **Natural Flow**: Avoid rigid formatting. Make it sound like a real debate opening - passionate, persuasive, and authentically yours.

Remember: This should sound like {setup['philosopher_name']} actually delivering an opening statement, not a formal academic paper. Let your philosophical personality shine through every sentence."""

        return prompt
    
    def generate_argument(self, setup: Dict[str, Any]) -> Dict[str, Any]:
        """웹서치 기반 입론 생성"""
        
        start_time = time.time()
        
        logger.info(f"🎭 입론 생성 시작:")
        logger.info(f"   주제: {setup['topic_data'].get('title', 'Unknown')}")
        logger.info(f"   철학자: {setup['philosopher_name']}")
        logger.info(f"   입장: {setup['stance']}")
        
        try:
            prompt = self.create_argument_prompt(setup)
            
            logger.info("🔍 OpenAI 웹서치 도구를 활용한 입론 생성 중...")
            
            response = self.client.responses.create(
                model="gpt-4o",
                tools=[{ 
                    "type": "web_search_preview",
                    "search_context_size": "medium"
                }],
                input=prompt
            )
            
            end_time = time.time()
            generation_time = end_time - start_time
            
            # 응답 처리
            raw_output = []
            generated_argument = ""
            
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'model_dump'):
                        raw_output.append(output_item.model_dump())
                    elif hasattr(output_item, '__dict__'):
                        raw_output.append(output_item.__dict__)
                    else:
                        raw_output.append(str(output_item))
            
            # output_text 추출
            if hasattr(response, 'output_text'):
                generated_argument = response.output_text
            
            result = {
                'setup': setup,
                'prompt': prompt,
                'generated_argument': generated_argument,
                'raw_openai_response': raw_output,
                'generation_time': generation_time,
                'timestamp': datetime.now().isoformat(),
                'model': "gpt-4o",
                'success': True
            }
            
            self.generation_history.append(result)
            
            logger.info(f"✅ 입론 생성 완료 ({generation_time:.2f}초)")
            logger.info(f"📝 생성된 입론 길이: {len(generated_argument)} 문자")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            generation_time = end_time - start_time
            
            logger.error(f"❌ 입론 생성 실패: {str(e)}")
            
            error_result = {
                'setup': setup,
                'prompt': self.create_argument_prompt(setup),
                'generated_argument': "",
                'raw_openai_response': [],
                'generation_time': generation_time,
                'timestamp': datetime.now().isoformat(),
                'model': "gpt-4o",
                'success': False,
                'error': str(e)
            }
            
            self.generation_history.append(error_result)
            return error_result
    
    def run_multiple_experiments(self, num_experiments: int = 3) -> List[Dict[str, Any]]:
        """여러 실험 실행"""
        
        logger.info(f"🔬 {num_experiments}개의 입론 생성 실험 시작")
        
        results = []
        
        for i in range(num_experiments):
            logger.info(f"\n--- 실험 {i+1}/{num_experiments} ---")
            
            # 랜덤 설정 생성
            setup = self.get_random_debate_setup()
            if not setup:
                logger.error(f"실험 {i+1} 설정 생성 실패")
                continue
            
            # 입론 생성
            result = self.generate_argument(setup)
            results.append(result)
            
            # 잠시 대기 (API 레이트 리밋 방지)
            if i < num_experiments - 1:
                time.sleep(2)
        
        logger.info(f"\n🏁 모든 실험 완료: {len(results)}개 입론 생성됨")
        
        return results
    
    def export_results_to_json(self, filename: Optional[str] = None) -> str:
        """결과를 JSON 파일로 내보내기"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debate_arguments_{timestamp}.json"
        
        export_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_experiments": len(self.generation_history),
                "successful_generations": len([r for r in self.generation_history if r.get('success', False)]),
                "model": "gpt-4o"
            },
            "results": self.generation_history
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 결과가 {filename}에 저장되었습니다.")
        return filename
    
    def print_argument_sample(self, result: Dict[str, Any]):
        """생성된 입론 샘플 출력"""
        
        if not result.get('success', False):
            print(f"❌ 생성 실패: {result.get('error', 'Unknown error')}")
            return
        
        setup = result['setup']
        
        print(f"\n{'='*80}")
        print(f"🎭 철학자: {setup['philosopher_name']}")
        print(f"📝 주제: {setup['topic_data'].get('title', 'Unknown')}")
        print(f"🎯 입장: {'찬성' if setup['stance'] == 'pro' else '반대'}")
        print(f"⏱️  생성 시간: {result['generation_time']:.2f}초")
        print(f"{'='*80}")
        
        argument = result['generated_argument']
        if argument:
            print(f"\n📜 생성된 입론:\n")
            print(argument)
        else:
            print("❌ 입론이 생성되지 않았습니다.")
        
        # 웹서치 사용 여부 확인
        raw_response = result.get('raw_openai_response', [])
        web_search_used = any(
            item.get('type') == 'web_search_call' 
            for item in raw_response 
            if isinstance(item, dict)
        )
        
        print(f"\n🔍 웹서치 활용: {'✅ 사용됨' if web_search_used else '❌ 사용되지 않음'}")
        print(f"📊 응답 항목 수: {len(raw_response)}")
        
        print(f"{'='*80}\n")


def main():
    """메인 테스트 실행 함수"""
    
    print("🎭 토론 입론 자동 생성 실험")
    print("=" * 60)
    print("기능: 웹서치 기반 철학자별 맞춤 입론 생성")
    print("=" * 60)
    
    # API 키 확인
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    print("✅ OpenAI API 키 확인 완료")
    
    try:
        # 생성기 초기화
        generator = DebateArgumentGenerator(openai_api_key)
        
        # 데이터 로드
        print("\n📚 데이터 로딩 중...")
        
        debate_loaded = generator.load_debate_data()
        philosopher_loaded = generator.load_philosopher_data()
        
        if not debate_loaded or not philosopher_loaded:
            print("❌ 필요한 데이터 파일을 로드할 수 없습니다.")
            return
        
        print("✅ 모든 데이터 로딩 완료")
        
        # 실험 실행
        print("\n🔬 입론 생성 실험 시작...")
        
        # 먼저 1개 테스트
        setup = generator.get_random_debate_setup()
        if setup:
            print(f"\n🎯 선택된 실험 설정:")
            print(f"   주제: {setup['topic_data'].get('title')}")
            print(f"   철학자: {setup['philosopher_name']}")
            print(f"   입장: {'찬성' if setup['stance'] == 'pro' else '반대'}")
            
            result = generator.generate_argument(setup)
            generator.print_argument_sample(result)
        
        # 추가 실험 여부 묻기
        response = input("\n추가 실험을 진행하시겠습니까? (y/n): ").lower().strip()
        
        if response == 'y':
            num_experiments = int(input("실험 횟수를 입력하세요 (권장: 2-5): ") or "3")
            
            print(f"\n🔬 {num_experiments}개 추가 실험 진행...")
            additional_results = generator.run_multiple_experiments(num_experiments)
            
            # 결과 샘플 출력
            for i, result in enumerate(additional_results[:2], 1):  # 처음 2개만 출력
                print(f"\n--- 실험 {i} 결과 ---")
                generator.print_argument_sample(result)
        
        # 결과 저장
        filename = generator.export_results_to_json()
        
        print(f"\n💾 실험 결과 저장 완료: {filename}")
        print("✅ 모든 실험 완료!")
        
    except Exception as e:
        logger.error(f"실험 실행 중 오류: {str(e)}")
        print(f"❌ 실험 실행 중 오류: {str(e)}")


if __name__ == "__main__":
    main() 