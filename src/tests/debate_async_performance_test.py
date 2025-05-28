"""
비동기 병렬 토론 시스템 성능 테스트

1번 개선사항: 더 세밀한 병렬화 (RAG 작업 분해)
4번 개선사항: 스트리밍 초기화 (실시간 진행 상황 표시)

실제 트랜스휴머니즘 토론 데이터로 검증
위치: src/tests/debate_async_performance_test.py
"""

import asyncio
import time
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_async_performance_main():
    """비동기 병렬 토론 시스템 성능 테스트 메인"""
    
    print("=" * 80)
    print("🚀 비동기 병렬 토론 시스템 성능 테스트")
    print("=" * 80)
    print()
    
    # 실제 트랜스휴머니즘 토론 데이터 사용
    room_data = create_transhumanism_room_data()
    
    # 테스트 메뉴
    while True:
        print("\n📋 테스트 메뉴:")
        print("1. 동기 vs 비동기 성능 비교")
        print("2. 스트리밍 초기화 테스트")
        print("3. 세밀한 병렬화 테스트 (실제 철학자)")
        print("4. 전체 통합 테스트")
        print("5. 성능 메트릭 조회")
        print("6. 실제 토론 실행 (입론까지)")
        print("0. 종료")
        
        choice = input("\n선택하세요 (0-6): ").strip()
        
        if choice == '0':
            print("👋 테스트를 종료합니다.")
            break
        elif choice == '1':
            asyncio.run(test_sync_vs_async_performance(room_data))
        elif choice == '2':
            asyncio.run(test_streaming_initialization(room_data))
        elif choice == '3':
            asyncio.run(test_fine_grained_parallelization(room_data))
        elif choice == '4':
            asyncio.run(test_full_integration(room_data))
        elif choice == '5':
            asyncio.run(test_performance_metrics(room_data))
        elif choice == '6':
            asyncio.run(test_actual_debate_execution(room_data))
        else:
            print("❌ 잘못된 선택입니다.")

def create_transhumanism_room_data():
    """실제 트랜스휴머니즘 토론 데이터 생성 (debate_test_new.py와 동일)"""
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
            },
            "users": []
        },
        "moderator": {
            "agent_id": "debate_moderator",
            "name": "토론 진행자",
            "style": "neutral"
        }
    }

async def test_sync_vs_async_performance(room_data: Dict[str, Any]):
    """동기 vs 비동기 성능 비교 테스트"""
    print("\n" + "=" * 60)
    print("📊 동기 vs 비동기 성능 비교 테스트")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        # 1. 동기 초기화 테스트
        print("\n🔄 동기 초기화 테스트 시작...")
        sync_start = time.time()
        
        sync_debate = DebateDialogue(
            room_id="test_sync_room",
            room_data=room_data,
            use_async_init=False,  # 동기 초기화
            enable_streaming=False
        )
        
        sync_time = time.time() - sync_start
        print(f"✅ 동기 초기화 완료: {sync_time:.2f}초")
        print(f"   생성된 에이전트: {list(sync_debate.agents.keys())}")
        
        # 2. 비동기 초기화 테스트 (에이전트 매핑 문제 해결)
        print("\n⚡ 비동기 초기화 테스트 시작...")
        async_start = time.time()
        
        # 먼저 동기로 에이전트 생성
        async_debate = DebateDialogue(
            room_id="test_async_room",
            room_data=room_data,
            use_async_init=False,  # 일단 동기로 에이전트 생성
            enable_streaming=False
        )
        
        # 그 다음 비동기 작업만 따로 테스트
        print(f"   에이전트 생성 완료: {list(async_debate.agents.keys())}")
        
        # 실제 병렬 처리 테스트 (입론 준비)
        from src.dialogue.parallel.rag_parallel import RAGParallelProcessor
        
        rag_processor = RAGParallelProcessor(max_workers=4)
        
        # 니체와 카뮈 에이전트 가져오기 (올바른 방식)
        from src.dialogue.types.debate_dialogue import ParticipantRole
        
        nietzsche_agent = async_debate.agents.get(ParticipantRole.PRO)  # "pro" 키로 접근
        camus_agent = async_debate.agents.get(ParticipantRole.CON)      # "con" 키로 접근
        
        if not nietzsche_agent or not camus_agent:
            print(f"❌ 철학자 에이전트를 찾을 수 없습니다.")
            print(f"   사용 가능한 에이전트: {list(async_debate.agents.keys())}")
            return
        
        print(f"   니체 에이전트: {nietzsche_agent.name} (ID: {nietzsche_agent.agent_id})")
        print(f"   카뮈 에이전트: {camus_agent.name} (ID: {camus_agent.agent_id})")
        
        # 병렬 입론 준비 테스트
        print("\n🔥 병렬 입론 준비 시작...")
        
        # 니체와 카뮈의 입론을 병렬로 준비
        tasks = [
            rag_processor.process_argument_preparation_parallel(
                agent=nietzsche_agent,
                topic=room_data['title'],
                stance_statement=async_debate.stance_statements.get('pro', '트랜스휴머니즘을 지지한다'),
                context={"role": "pro", "philosopher": "nietzsche"}
            ),
            rag_processor.process_argument_preparation_parallel(
                agent=camus_agent,
                topic=room_data['title'],
                stance_statement=async_debate.stance_statements.get('con', '트랜스휴머니즘을 반대한다'),
                context={"role": "con", "philosopher": "camus"}
            )
        ]
        
        parallel_results = await asyncio.gather(*tasks)
        
        async_time = time.time() - async_start
        print(f"✅ 비동기 병렬 처리 완료: {async_time:.2f}초")
        
        # 3. 성능 비교 결과
        print("\n📈 성능 비교 결과:")
        print(f"   동기 초기화:     {sync_time:.2f}초")
        print(f"   비동기 병렬처리: {async_time:.2f}초")
        
        if async_time < sync_time:
            improvement = ((sync_time - async_time) / sync_time) * 100
            print(f"   🎉 성능 개선:     {improvement:.1f}% 단축")
        else:
            degradation = ((async_time - sync_time) / sync_time) * 100
            print(f"   ⚠️  성능 저하:     {degradation:.1f}% 증가")
        
        # 4. 병렬 처리 결과 분석
        print(f"\n🔍 병렬 처리 결과 분석:")
        for i, result in enumerate(parallel_results):
            philosopher = "니체" if i == 0 else "카뮈"
            if result.get('status') == 'success':
                print(f"   {philosopher}: ✅ 성공")
                print(f"     - 핵심 논점: {len(result.get('core_arguments', []))}개")
                print(f"     - 증거 자료: {len(result.get('evidence_results', []))}개")
                print(f"     - 최종 입론: {len(result.get('final_argument', ''))}자")
            else:
                print(f"   {philosopher}: ❌ 실패 - {result.get('error', 'Unknown error')}")
        
        # 리소스 정리
        rag_processor.cleanup()
        sync_debate.cleanup_resources()
        async_debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_streaming_initialization(room_data: Dict[str, Any]):
    """스트리밍 초기화 테스트"""
    print("\n" + "=" * 60)
    print("📡 스트리밍 초기화 테스트")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        print("\n🎬 스트리밍 초기화 시작...")
        
        # 스트리밍 활성화된 토론 생성
        debate = DebateDialogue(
            room_id="test_streaming_room",
            room_data=room_data,
            use_async_init=True,
            enable_streaming=True
        )
        
        # 초기화 실행 (콘솔 출력으로 진행 상황 확인)
        result = await debate.initialize_async()
        
        print(f"\n✅ 스트리밍 초기화 완료!")
        print(f"   상태: {result.get('status')}")
        print(f"   총 시간: {result.get('total_time', 0):.2f}초")
        print(f"   스트리밍 활성화: {result.get('streaming_enabled', False)}")
        
        # 진행 상황 요약 조회
        progress = debate.get_initialization_progress()
        print(f"\n📊 최종 진행 상황:")
        print(f"   진행률: {progress.get('progress_percentage', 0):.1f}%")
        print(f"   완료된 작업: {progress.get('completed_tasks', 0)}")
        print(f"   실패한 작업: {progress.get('failed_tasks', 0)}")
        print(f"   총 소요 시간: {progress.get('elapsed_time', 0):.2f}초")
        
        # 이벤트 히스토리 조회
        history = debate.get_initialization_history()
        print(f"\n📜 이벤트 히스토리 ({len(history)}개 이벤트):")
        for event in history[-5:]:  # 최근 5개 이벤트만 표시
            event_type = event.get('event_type', 'unknown')
            timestamp = event.get('timestamp', 0)
            print(f"   - {event_type} (시간: {timestamp:.2f})")
        
        # 리소스 정리
        debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")

async def test_fine_grained_parallelization(room_data: Dict[str, Any]):
    """세밀한 병렬화 테스트 (실제 철학자 에이전트 사용)"""
    print("\n" + "=" * 60)
    print("🔧 세밀한 병렬화 테스트 (실제 니체 vs 카뮈)")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue
        from src.dialogue.parallel.rag_parallel import RAGParallelProcessor
        
        print("\n🎭 실제 철학자 에이전트로 RAG 병렬 처리 테스트...")
        
        # 실제 토론 시스템 생성
        debate = DebateDialogue(
            room_id="test_real_philosophers",
            room_data=room_data,
            use_async_init=False,  # 에이전트 먼저 생성
            enable_streaming=False
        )
        
        print(f"✅ 토론 시스템 초기화 완료")
        print(f"   주제: {room_data['title']}")
        print(f"   찬성: {room_data['participants']['pro']['name']} (니체)")
        print(f"   반대: {room_data['participants']['con']['name']} (카뮈)")
        
        # RAG 병렬 처리기 생성
        rag_processor = RAGParallelProcessor(max_workers=4)
        
        # 실제 에이전트들 가져오기
        from src.dialogue.types.debate_dialogue import ParticipantRole
        pro_agent = debate.agents.get(ParticipantRole.PRO)
        con_agent = debate.agents.get(ParticipantRole.CON)
        
        if not pro_agent or not con_agent:
            print("❌ 에이전트를 찾을 수 없습니다.")
            print(f"   사용 가능한 에이전트: {list(debate.agents.keys())}")
            return
        
        print(f"\n🤖 에이전트 정보:")
        print(f"   찬성 에이전트: {pro_agent.name} ({pro_agent.agent_id})")
        print(f"   반대 에이전트: {con_agent.name} ({con_agent.agent_id})")
        
        # 진행 상황 추적을 위한 콜백
        progress_events = []
        
        def progress_callback(subtask_name: str, status: str, details: Dict[str, Any] = None):
            progress_events.append({
                "subtask": subtask_name,
                "status": status,
                "details": details,
                "timestamp": time.time()
            })
            print(f"   📝 {subtask_name}: {status}")
            if details and status == "completed":
                if "result" in details:
                    result_info = details["result"]
                    if isinstance(result_info, list):
                        print(f"      → {len(result_info)}개 항목")
                    elif isinstance(result_info, str):
                        print(f"      → {len(result_info)}자")
                elif "results_count" in details:
                    print(f"      → {details['results_count']}개 결과")
        
        # 1. 니체 (찬성측) 병렬 입론 준비 테스트
        print(f"\n🦅 니체의 병렬 입론 준비 시작...")
        print(f"   입장: {debate.stance_statements.get('pro', '찬성 입장')}")
        
        start_time = time.time()
        
        nietzsche_result = await rag_processor.process_argument_preparation_parallel(
            agent=pro_agent,
            topic=room_data['title'],
            stance_statement=debate.stance_statements.get('pro', '트랜스휴머니즘을 지지한다'),
            context={"role": ParticipantRole.PRO, "philosopher": "nietzsche"},
            progress_callback=progress_callback
        )
        
        nietzsche_time = time.time() - start_time
        
        print(f"\n✅ 니체 입론 준비 완료: {nietzsche_time:.2f}초")
        print(f"   상태: {nietzsche_result.get('status')}")
        print(f"   핵심 논점: {len(nietzsche_result.get('core_arguments', []))}")
        print(f"   검색 결과: {nietzsche_result.get('search_results_count', 0)}")
        print(f"   증거 수: {len(nietzsche_result.get('evidence_results', []))}")
        print(f"   최종 입론 길이: {len(nietzsche_result.get('final_argument', ''))}")
        
        # 니체의 핵심 논점 출력
        core_args = nietzsche_result.get('core_arguments', [])
        if core_args:
            print(f"\n🎯 니체의 핵심 논점:")
            for i, arg in enumerate(core_args, 1):
                print(f"   {i}. {arg}")
        
        # 2. 카뮈 (반대측) 병렬 입론 준비 테스트
        print(f"\n🌊 카뮈의 병렬 입론 준비 시작...")
        print(f"   입장: {debate.stance_statements.get('con', '반대 입장')}")
        
        progress_events.clear()  # 이벤트 리스트 초기화
        start_time = time.time()
        
        camus_result = await rag_processor.process_argument_preparation_parallel(
            agent=con_agent,
            topic=room_data['title'],
            stance_statement=debate.stance_statements.get('con', '트랜스휴머니즘을 반대한다'),
            context={"role": ParticipantRole.CON, "philosopher": "camus"},
            progress_callback=progress_callback
        )
        
        camus_time = time.time() - start_time
        
        print(f"\n✅ 카뮈 입론 준비 완료: {camus_time:.2f}초")
        print(f"   상태: {camus_result.get('status')}")
        print(f"   핵심 논점: {len(camus_result.get('core_arguments', []))}")
        print(f"   검색 결과: {camus_result.get('search_results_count', 0)}")
        print(f"   증거 수: {len(camus_result.get('evidence_results', []))}")
        print(f"   최종 입론 길이: {len(camus_result.get('final_argument', ''))}")
        
        # 카뮈의 핵심 논점 출력
        core_args = camus_result.get('core_arguments', [])
        if core_args:
            print(f"\n🎯 카뮈의 핵심 논점:")
            for i, arg in enumerate(core_args, 1):
                print(f"   {i}. {arg}")
        
        # 3. 성능 비교 및 분석
        print(f"\n📊 성능 분석:")
        print(f"   니체 처리 시간: {nietzsche_time:.2f}초")
        print(f"   카뮈 처리 시간: {camus_time:.2f}초")
        print(f"   평균 처리 시간: {(nietzsche_time + camus_time) / 2:.2f}초")
        
        # 4. 최종 입론 미리보기
        if nietzsche_result.get('final_argument'):
            print(f"\n📜 니체의 입론 미리보기:")
            argument = nietzsche_result['final_argument']
            preview = argument[:200] + "..." if len(argument) > 200 else argument
            print(f"   {preview}")
        
        if camus_result.get('final_argument'):
            print(f"\n📜 카뮈의 입론 미리보기:")
            argument = camus_result['final_argument']
            preview = argument[:200] + "..." if len(argument) > 200 else argument
            print(f"   {preview}")
        
        # 리소스 정리
        rag_processor.cleanup()
        debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_full_integration(room_data: Dict[str, Any]):
    """전체 통합 테스트"""
    print("\n" + "=" * 60)
    print("🎯 전체 통합 테스트")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        print("\n🌟 모든 개선사항이 적용된 토론 시스템 테스트...")
        
        # 모든 개선사항 활성화
        debate = DebateDialogue(
            room_id="test_full_integration",
            room_data=room_data,
            use_async_init=True,
            enable_streaming=True
        )
        
        # 초기화 실행
        print("\n🚀 통합 초기화 시작...")
        start_time = time.time()
        
        result = await debate.initialize_async()
        
        total_time = time.time() - start_time
        
        print(f"\n🎉 통합 테스트 완료!")
        print(f"   총 시간: {total_time:.2f}초")
        print(f"   상태: {result.get('status')}")
        print(f"   스트리밍: {result.get('streaming_enabled')}")
        
        # 성능 메트릭 조회
        metrics = debate.get_performance_metrics()
        print(f"\n📈 성능 메트릭:")
        print(f"   RAG 워커 수: {metrics.get('rag_processor_workers')}")
        print(f"   참가자 수: {sum(metrics.get('participants_count', {}).values())}")
        print(f"   에이전트 수: {metrics.get('agents_count')}")
        print(f"   벡터 저장소: {'✅' if metrics.get('vector_store_available') else '❌'}")
        print(f"   현재 단계: {metrics.get('current_stage')}")
        
        # 초기화 진행 상황
        progress = metrics.get('initialization_progress', {})
        if progress:
            print(f"\n📊 초기화 진행 상황:")
            print(f"   진행률: {progress.get('progress_percentage', 0):.1f}%")
            print(f"   완료 작업: {progress.get('completed_tasks', 0)}")
            print(f"   실패 작업: {progress.get('failed_tasks', 0)}")
            print(f"   활성 상태: {'✅' if progress.get('is_active') else '❌'}")
        
        # 리소스 정리
        debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")

async def test_performance_metrics(room_data: Dict[str, Any]):
    """성능 메트릭 조회 테스트"""
    print("\n" + "=" * 60)
    print("📊 성능 메트릭 조회 테스트")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue
        
        # 토론 시스템 생성
        debate = DebateDialogue(
            room_id="test_metrics_room",
            room_data=room_data,
            use_async_init=True,
            enable_streaming=True
        )
        
        # 초기화 전 메트릭
        print("\n📋 초기화 전 메트릭:")
        pre_metrics = debate.get_performance_metrics()
        print_metrics(pre_metrics)
        
        # 초기화 실행
        print("\n⚡ 초기화 실행 중...")
        await debate.initialize_async()
        
        # 초기화 후 메트릭
        print("\n📋 초기화 후 메트릭:")
        post_metrics = debate.get_performance_metrics()
        print_metrics(post_metrics)
        
        # 리소스 정리
        debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")

def print_metrics(metrics: Dict[str, Any]):
    """메트릭 정보를 보기 좋게 출력"""
    print(f"   방 ID: {metrics.get('room_id')}")
    print(f"   스트리밍: {'✅' if metrics.get('streaming_enabled') else '❌'}")
    print(f"   RAG 워커: {metrics.get('rag_processor_workers')}개")
    
    participants = metrics.get('participants_count', {})
    print(f"   참가자:")
    print(f"     - 찬성: {participants.get('pro', 0)}명")
    print(f"     - 반대: {participants.get('con', 0)}명")
    print(f"     - 모더레이터: {participants.get('moderator', 0)}명")
    print(f"     - 사용자: {participants.get('user', 0)}명")
    
    print(f"   에이전트: {metrics.get('agents_count')}개")
    print(f"   벡터 저장소: {'✅' if metrics.get('vector_store_available') else '❌'}")
    print(f"   현재 단계: {metrics.get('current_stage')}")
    print(f"   턴 수: {metrics.get('turn_count')}")
    print(f"   진행 중: {'✅' if metrics.get('playing') else '❌'}")
    
    # 초기화 진행 상황 (있는 경우)
    init_progress = metrics.get('initialization_progress')
    if init_progress:
        print(f"   초기화 진행률: {init_progress.get('progress_percentage', 0):.1f}%")

async def test_actual_debate_execution(room_data: Dict[str, Any]):
    """실제 토론 실행 테스트 (입론까지)"""
    print("\n" + "=" * 60)
    print("🎯 실제 토론 실행 테스트 (니체 vs 카뮈)")
    print("=" * 60)
    
    try:
        from src.dialogue.types.debate_dialogue import DebateDialogue, DebateStage
        
        print(f"\n🎭 트랜스휴머니즘 토론 시작...")
        print(f"   주제: {room_data['title']}")
        print(f"   찬성: 니체 (위버멘쉬 철학)")
        print(f"   반대: 카뮈 (부조리주의)")
        
        # 스트리밍과 비동기 초기화 모두 활성화
        debate = DebateDialogue(
            room_id="test_actual_debate",
            room_data=room_data,
            use_async_init=True,
            enable_streaming=True
        )
        
        # 비동기 초기화 실행
        print(f"\n⚡ 토론 초기화 중...")
        init_result = await debate.initialize_async()
        
        if init_result.get('status') != 'success':
            print(f"❌ 초기화 실패: {init_result.get('error')}")
            return
        
        print(f"✅ 초기화 완료: {init_result.get('total_time', 0):.2f}초")
        
        # 입장 진술문 출력
        stance_statements = debate.stance_statements
        print(f"\n📋 입장 진술문:")
        print(f"   찬성 (니체): {stance_statements.get('pro', '')}")
        print(f"   반대 (카뮈): {stance_statements.get('con', '')}")
        
        # 토론 진행 (입론까지)
        max_turns = 5
        turn = 0
        messages = []
        
        stages_to_test = [
            DebateStage.OPENING,
            DebateStage.PRO_ARGUMENT, 
            DebateStage.CON_ARGUMENT
        ]
        
        print(f"\n🚀 토론 시작!")
        print("=" * 40)
        
        while turn < max_turns and debate.state["current_stage"] in stages_to_test:
            current_stage = debate.state["current_stage"]
            
            # 단계 표시
            stage_names = {
                DebateStage.OPENING: "🎙️ 오프닝",
                DebateStage.PRO_ARGUMENT: "🦅 니체의 입론",
                DebateStage.CON_ARGUMENT: "🌊 카뮈의 입론"
            }
            stage_name = stage_names.get(current_stage, current_stage)
            
            print(f"\n[{stage_name}]")
            print("-" * 30)
            
            # 응답 생성
            response = debate.generate_response()
            
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
                
                # 메시지 기록
                messages.append({
                    "turn": turn,
                    "stage": current_stage,
                    "speaker": speaker_name,
                    "role": role,
                    "message": message
                })
                
                turn += 1
                time.sleep(1)  # 출력 간격
                
            elif response["status"] == "waiting_for_user":
                print(f"⏳ 사용자 입력 대기 중...")
                break
            else:
                print(f"❌ 응답 생성 실패: {response}")
                break
        
        # 결과 요약
        print("=" * 40)
        print(f"✅ 토론 테스트 완료!")
        print(f"   총 턴 수: {turn}")
        print(f"   현재 단계: {debate.state['current_stage']}")
        print(f"   생성된 메시지: {len(messages)}개")
        
        # 성능 메트릭
        metrics = debate.get_performance_metrics()
        print(f"\n📊 성능 메트릭:")
        print(f"   에이전트 수: {metrics.get('agents_count')}")
        print(f"   벡터 저장소: {'✅' if metrics.get('vector_store_available') else '❌'}")
        print(f"   스트리밍: {'✅' if metrics.get('streaming_enabled') else '❌'}")
        
        # 메시지 요약 출력
        if messages:
            print(f"\n📜 토론 요약:")
            for msg in messages:
                speaker = msg['speaker'].replace('🎙️ ', '').replace('🦅 ', '').replace('🌊 ', '')
                preview = msg['message'][:100] + "..." if len(msg['message']) > 100 else msg['message']
                print(f"   {msg['turn']+1}. {speaker}: {preview}")
        
        # 리소스 정리
        debate.cleanup_resources()
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_async_performance_main() 