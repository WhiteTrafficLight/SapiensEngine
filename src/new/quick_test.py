#!/usr/bin/env python3
"""
Quick Test for Fast Debate Generation

실제 debate_topics.json의 콘텍스트를 사용하여 테스트
"""

import asyncio
import json
import time
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.new.models.debate_models import FastDebateRequest, ContextType
from src.new.services.openai_service import OpenAIDebateService

def load_debate_topics():
    """debate_topics.json 로드"""
    topics_path = Path("agoramind/data/debate_topics.json")
    with open(topics_path, 'r', encoding='utf-8') as f:
        return json.load(f)

async def quick_demo(topic_data=None):
    """빠른 테스트 실행 - 실제 콘텍스트 사용"""
    
    debate_topics = load_debate_topics()
    
    if topic_data is None:
        # 기본값: AI 위협 vs 해방 토픽 (URL 콘텍스트 포함)
        topic_data = debate_topics['categories']['science_and_technology']['topics'][0]
    
    print(f"🚀 Testing: {topic_data['title']}")
    print(f"📝 Context Type: {topic_data['context']['type']}")
    print(f"📄 Context Content: {topic_data['context']['content'][:100]}...")
    
    # ContextType 설정
    context_type = ContextType.URL if topic_data['context']['type'] == 'url' else ContextType.TEXT
    
    # FastDebateRequest 생성 - 정확한 콘텍스트 사용
    request = FastDebateRequest(
        room_id=f"test_{topic_data['title'][:20].replace(' ', '_').lower()}",
        title=topic_data['title'],
        context=topic_data['context']['content'],
        context_type=context_type,
        pro_npcs=topic_data['pro_philosophers'],
        con_npcs=topic_data['con_philosophers'],
        moderator_style=str(topic_data['moderator_style'])
    )
    
    # 서비스 초기화 및 생성
    service = OpenAIDebateService(use_fine_tuned=False)
    
    start_time = time.time()
    package = await service.generate_complete_debate_package(request)
    generation_time = time.time() - start_time
    
    # 전체 결과 출력
    print(f"\n✅ Generation completed in {generation_time:.2f} seconds")
    print(f"📝 Opening Message Length: {len(package.opening_message)} characters")
    print(f"\n🎭 FULL OPENING MESSAGE:")
    print("=" * 80)
    print(package.opening_message)
    print("=" * 80)
    
    print(f"\n📊 Stance Statements:")
    print(f"PRO: {package.stance_statements.pro}")
    print(f"CON: {package.stance_statements.con}")
    
    if package.context_summary:
        print(f"\n📄 Context Summary:")
        print(f"Summary: {package.context_summary.summary}")
        print(f"Key Points: {package.context_summary.key_points}")
    
    return package.opening_message, generation_time

async def test_multiple_topics():
    """여러 토픽 테스트 - URL과 TEXT 콘텍스트 모두 포함"""
    
    debate_topics = load_debate_topics()
    
    test_topics = [
        # URL 콘텍스트 토픽
        debate_topics['categories']['science_and_technology']['topics'][0],  # AI threat - URL
        debate_topics['categories']['global_and_current_affairs']['topics'][0],  # Climate refugees - URL
        
        # TEXT 콘텍스트 토픽  
        debate_topics['categories']['dilemma_challenge']['topics'][0],  # Puppy dilemma - TEXT
        debate_topics['categories']['dilemma_challenge']['topics'][2],  # Memory erasure - TEXT
        
        # 빈 콘텍스트 토픽
        debate_topics['categories']['self_and_philosophy']['topics'][0],  # Absolute freedom - empty
    ]
    
    results = []
    
    for i, topic in enumerate(test_topics, 1):
        print(f"\n{'='*60}")
        print(f"🧪 TEST {i}/{len(test_topics)}")
        print(f"{'='*60}")
        
        opening, time_taken = await quick_demo(topic)
        
        results.append({
            'topic': topic['title'],
            'context_type': topic['context']['type'],
            'has_context': bool(topic['context']['content'].strip()),
            'time': time_taken,
            'length': len(opening),
            'opening': opening
        })
        
        print(f"\n⏱️  Time: {time_taken:.2f}s")
        print(f"📏 Length: {len(opening)} chars")
        print(f"🔗 Context Type: {topic['context']['type']}")
        print(f"📝 Has Content: {bool(topic['context']['content'].strip())}")
    
    # 최종 요약
    print(f"\n{'='*60}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*60}")
    
    avg_time = sum(r['time'] for r in results) / len(results)
    avg_length = sum(r['length'] for r in results) / len(results)
    
    print(f"Average Generation Time: {avg_time:.2f}s")
    print(f"Average Opening Length: {avg_length:.0f} chars")
    
    # 콘텍스트 타입별 분석
    url_results = [r for r in results if r['context_type'] == 'url']
    text_results = [r for r in results if r['context_type'] == 'text']
    empty_results = [r for r in results if not r['has_context']]
    
    if url_results:
        url_avg = sum(r['time'] for r in url_results) / len(url_results)
        print(f"URL Context Average: {url_avg:.2f}s")
    
    if text_results:
        text_avg = sum(r['time'] for r in text_results) / len(text_results)
        print(f"Text Context Average: {text_avg:.2f}s")
    
    if empty_results:
        empty_avg = sum(r['time'] for r in empty_results) / len(empty_results)
        print(f"No Context Average: {empty_avg:.2f}s")
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Quick Debate Generation Test")
    print("Using actual contexts from debate_topics.json")
    
    # 단일 테스트
    # asyncio.run(quick_demo())
    
    # 다중 테스트 (URL, TEXT, 빈 콘텍스트 모두 포함)
    asyncio.run(test_multiple_topics()) 