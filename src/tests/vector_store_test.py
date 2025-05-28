"""
VectorStore 구현 테스트

새로 구현한 벡터 저장소 모듈의 기능을 테스트합니다.
"""

import sys
import os
import time
from typing import Dict, Any, List
import json

# 프로젝트 루트 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, project_root)

# VectorStore 임포트
from src.rag.retrieval.vector_store import VectorStore

def test_vector_store_basic():
    """기본 기능 테스트: 문서 추가 및 검색"""
    print("\n=== 벡터 저장소 기본 기능 테스트 ===")
    
    # 저장소 생성
    vector_store = VectorStore(store_path="data/test_vector_store")
    
    # 테스트 문서
    documents = [
        "인공지능은 인간의 학습, 추론, 지각, 문제 해결 능력 등을 모방하여 설계된 컴퓨터 시스템이다.",
        "머신러닝은 알고리즘과 통계 모델을 사용하여 컴퓨터 시스템이 명시적인 지침 없이 작업을 수행하도록 하는 인공지능의 하위 분야이다.",
        "딥러닝은 특히 특징 추출과 변환, 패턴 인식 등에 중점을 둔 머신러닝의 한 방법론이다.",
        "자연어 처리는 컴퓨터와 인간 언어 간의 상호 작용을 다루는 인공지능의 한 분야이다.",
        "컴퓨터 비전은 디지털 이미지나 비디오에서 정보를 추출하는 인공지능 기술이다."
    ]
    
    # 문서 추가
    vector_store.add_documents(documents)
    print(f"추가된 문서 수: {len(vector_store.documents)}")
    
    # 검색 테스트
    queries = [
        "인공지능이란 무엇인가?",
        "머신러닝과 딥러닝의 관계",
        "컴퓨터가 언어를 이해하는 방법"
    ]
    
    for query in queries:
        results = vector_store.search(query, limit=2)
        print(f"\n쿼리: '{query}'")
        for i, result in enumerate(results):
            print(f"  결과 {i+1}: (점수: {result['score']:.4f})")
            print(f"  {result['text']}")

def test_vector_store_save_load():
    """저장 및 로딩 기능 테스트"""
    print("\n=== 벡터 저장소 저장/로딩 테스트 ===")
    
    # 임시 저장 경로
    store_path = "data/test_vector_store_save_load"
    
    # 첫 번째 인스턴스 생성 및 데이터 추가
    vs1 = VectorStore(store_path=store_path)
    
    # 테스트 문서
    documents = [
        "철학은 지혜를 사랑하는 학문으로, 존재, 지식, 가치, 이성, 마음, 언어 등에 대한 근본적인 질문을 다룬다.",
        "윤리학은 도덕적 행동과 판단에 관한 철학의 한 분야로, 옳고 그름에 대한 체계적인 접근을 시도한다.",
        "형이상학은 존재의 본질과 실재에 관한 철학적 탐구로, 시간, 공간, 가능성, 필연성 등을 다룬다.",
        "인식론은 지식의 본질, 범위, 기원에 대한 철학적 연구로, '우리는 무엇을 알 수 있는가'를 묻는다."
    ]
    
    # 문서 추가
    vs1.add_documents(documents)
    print(f"추가된 문서 수: {len(vs1.documents)}")
    
    # 검색 테스트
    query = "철학의 기본 분야"
    results_before = vs1.search(query, limit=3)
    print(f"\n저장 전 쿼리 결과: '{query}'")
    for i, result in enumerate(results_before):
        print(f"  결과 {i+1}: (점수: {result['score']:.4f})")
        print(f"  {result['text']}")
    
    # 저장소 저장
    vs1.save()
    print(f"\n벡터 저장소 저장됨: {store_path}")
    
    # 새 인스턴스 생성 및 로드
    vs2 = VectorStore(store_path=store_path)
    vs2.load()
    print(f"로딩된 문서 수: {len(vs2.documents)}")
    
    # 로딩 후 검색 테스트
    results_after = vs2.search(query, limit=3)
    print(f"\n로딩 후 쿼리 결과: '{query}'")
    for i, result in enumerate(results_after):
        print(f"  결과 {i+1}: (점수: {result['score']:.4f})")
        print(f"  {result['text']}")

def test_debate_context_retrieval():
    """토론 컨텍스트 검색 테스트"""
    print("\n=== 토론 컨텍스트 검색 테스트 ===")
    
    # 벡터 저장소 생성
    vector_store = VectorStore(store_path="data/test_debate_context")
    
    # 토론 컨텍스트 추가
    debate_context = """
트랜스휴머니즘은 기술을 통해 인간의 신체적, 인지적 한계를 극복하고자 하는 철학적, 지적 운동입니다. 

유전공학, 나노기술, 인공지능, 로봇공학 등의 발전을 통해 인간은 더 강하고, 더 오래 살며, 더 지능적인 존재로 
진화할 수 있다고 보는 시각입니다.

트랜스휴머니즘의 지지자들은 이러한 진화가 인류의 자연스러운 발전 과정이며, 
더 나은 미래를 위한 필수적인 단계라고 주장합니다.

반면 비판론자들은 이것이 인간성의 본질을 훼손하고, 새로운 윤리적, 사회적 문제를 야기할 수 있다는 
우려를 표합니다.

특히 인공지능과 유전자 조작 기술의 발전은 인간의 정체성, 평등, 자유의지에 관한 
근본적인 질문을 제기합니다.

또한 이러한 기술의 혜택이 모든 사람에게 평등하게 배분될 것인지, 
아니면 새로운 형태의 불평등을 만들어낼 것인지에 대한 논쟁도 있습니다.
    """
    
    # 컨텍스트 단락화 및 추가
    paragraphs = [p.strip() for p in debate_context.split('\n\n') if p.strip()]
    vector_store.add_documents(paragraphs)
    
    print(f"추가된 단락 수: {len(vector_store.documents)}")
    
    # 토론 중 발언 시뮬레이션
    statements = [
        "인간의 한계를 극복하는 것은 필연적인 진화의 과정입니다.",
        "인공지능과 생명공학 기술은 인간성의 본질을 위협합니다.",
        "기술 발전의 혜택이 모든 사람에게 공평하게 분배되어야 합니다."
    ]
    
    for statement in statements:
        print(f"\n발언: '{statement}'")
        print("관련 컨텍스트:")
        
        results = vector_store.search(statement, limit=1)
        for result in results:
            print(f"- (점수: {result['score']:.4f}) {result['text']}")

def main():
    """메인 실행 함수"""
    # 테스트 디렉토리 생성
    os.makedirs("data", exist_ok=True)
    
    # 기본 기능 테스트
    test_vector_store_basic()
    
    # 저장 및 로딩 테스트
    test_vector_store_save_load()
    
    # 토론 컨텍스트 검색 테스트
    test_debate_context_retrieval()
    
    print("\n모든 테스트 완료")

if __name__ == "__main__":
    main() 