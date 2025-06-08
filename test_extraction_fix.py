#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

# Add src to path  
current_dir = Path(__file__).parent.absolute()
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from src.rag.retrieval.web_retriever import WebSearchRetriever

def test_extraction_fix():
    print("🧪 수정된 Wikipedia 추출 테스트")
    print("=" * 50)
    
    # Create retriever
    retriever = WebSearchRetriever(
        search_provider="google",
        max_results=1
    )
    
    # Test URL
    test_url = "https://en.wikipedia.org/wiki/Lee_Jae-myung"
    
    print(f"📊 테스트 URL: {test_url}")
    
    # Mock search result
    mock_search_result = {
        "title": "Lee Jae-myung - Wikipedia",
        "url": test_url,
        "snippet": "South Korean politician",
        "source": "google_api",
        "position": 1
    }
    
    print("🔍 수정된 콘텐츠 추출 테스트...")
    
    try:
        content, metadata = retriever._extract_page_content(test_url, mock_search_result)
        
        print(f"📝 콘텐츠 길이: {len(content)} 문자")
        print(f"📊 단어 수: {len(content.split())} 단어")
        print(f"🏷️  제목: {metadata.get('title', 'No title')}")
        print(f"⚙️  추출 방법: {metadata.get('extraction_method', 'Unknown')}")
        
        if content:
            print(f"✅ 추출 성공!")
            print(f"\n📄 콘텐츠 미리보기 (처음 300자):")
            print("=" * 50)
            print(content[:300] + "...")
            print("=" * 50)
            
            # retrieve_and_extract도 테스트
            print(f"\n🔄 전체 파이프라인 테스트 (retrieve_and_extract)")
            chunks = retriever.retrieve_and_extract('Lee Jae-myung', max_pages=1)
            print(f"📊 생성된 청크 수: {len(chunks)}")
            
            if chunks:
                for i, chunk in enumerate(chunks[:3]):
                    score = chunk.get("score", chunk.get("similarity", 0))
                    print(f"  청크 {i+1}: {len(chunk['text'])} 문자, 점수: {score:.3f}")
            
        else:
            print("❌ 콘텐츠가 비어있음")
            print(f"🔍 에러: {metadata.get('error', 'Unknown error')}")
            print(f"🔍 단어 수: {metadata.get('word_count', 'Unknown')}")
            
    except Exception as e:
        print(f"❌ 추출 실패: {str(e)}")
        import traceback
        print(f"🔍 상세 에러:\n{traceback.format_exc()}")

if __name__ == "__main__":
    test_extraction_fix() 