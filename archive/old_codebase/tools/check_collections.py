#!/usr/bin/env python3
"""
ChromaDB 컬렉션 확인 스크립트

벡터 데이터베이스의 컬렉션 목록과 각 컬렉션의 항목 수를 보여줍니다.
"""

import sys
from pathlib import Path
import chromadb
import argparse

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

def check_collections(db_path: str = "./vectordb"):
    """
    ChromaDB 컬렉션과 항목 수를 확인합니다.
    
    Args:
        db_path: 벡터 DB 경로
    """
    print(f"ChromaDB 데이터베이스 경로: {db_path}")
    
    # ChromaDB 클라이언트 초기화
    client = chromadb.PersistentClient(path=db_path)
    
    # 컬렉션 목록 가져오기
    collections = client.list_collections()
    
    print(f"총 {len(collections)}개의 컬렉션이 있습니다:")
    print("=" * 50)
    
    for coll in collections:
        # 컬렉션 정보 가져오기
        collection = client.get_collection(name=coll.name)
        count = collection.count()
        
        print(f"컬렉션 이름: {coll.name}")
        print(f"항목 수: {count}")
        
        # 메타데이터 샘플 가져오기
        if count > 0:
            sample = collection.get(limit=1)
            print(f"첫 번째 항목 ID: {sample['ids'][0]}")
            if 'metadatas' in sample and sample['metadatas']:
                print(f"메타데이터 샘플: {sample['metadatas'][0]}")
            if 'documents' in sample and sample['documents']:
                doc_sample = sample['documents'][0]
                # 너무 긴 문서는 잘라서 표시
                if len(doc_sample) > 150:
                    doc_sample = doc_sample[:150] + "..."
                print(f"문서 샘플: {doc_sample}")
        
        print("-" * 50)
    
    print("=" * 50)
    
    return collections

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ChromaDB 컬렉션 확인')
    parser.add_argument('--db_path', type=str, default="./vectordb",
                      help='벡터 DB 경로')
    
    args = parser.parse_args()
    
    check_collections(args.db_path) 