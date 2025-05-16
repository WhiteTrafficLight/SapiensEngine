#!/usr/bin/env python3
"""
Context Tool - 컨텍스트 처리 및 벡터 DB 저장/검색 도구

Usage:
  python context_tool.py process_file <file_path> [--chunk-size=<size>] [--overlap=<ratio>] [--method=<method>]
  python context_tool.py process_url <url> [--chunk-size=<size>] [--overlap=<ratio>] [--method=<method>]
  python context_tool.py process_text <text> [--chunk-size=<size>] [--overlap=<ratio>] [--method=<method>]
  python context_tool.py search <collection_name> <query> [--results=<count>]
  python context_tool.py list_collections
  python context_tool.py collection_info <collection_name>
"""

import os
import sys
import argparse
import json
from sapiens_engine.core.context_manager import ContextManager
import textwrap

def process_file(args):
    """파일 처리 및 벡터 DB 저장"""
    cm = ContextManager(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        chunking_method=args.method,
        db_path=args.db_path
    )
    
    collection_name = cm.process_file(args.file_path)
    print(f"컬렉션 생성 완료: {collection_name}")
    return collection_name

def process_url(args):
    """URL 처리 및 벡터 DB 저장"""
    cm = ContextManager(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        chunking_method=args.method,
        db_path=args.db_path
    )
    
    collection_name = cm.process_url(args.url)
    print(f"컬렉션 생성 완료: {collection_name}")
    return collection_name

def process_text(args):
    """텍스트 처리 및 벡터 DB 저장"""
    cm = ContextManager(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        chunking_method=args.method,
        db_path=args.db_path
    )
    
    collection_name = cm.process_text(args.text)
    print(f"컬렉션 생성 완료: {collection_name}")
    return collection_name

def search(args):
    """벡터 DB 검색"""
    cm = ContextManager(db_path=args.db_path)
    
    results = cm.search(
        collection_name=args.collection_name,
        query=args.query,
        n_results=args.results
    )
    
    print(f"\n=== 검색 결과: '{args.query}' ({len(results)} 결과) ===\n")
    
    for i, result in enumerate(results):
        print(f"[{i+1}] 유사도: {1 - result['distance']:.4f}")
        
        if 'metadata' in result:
            print(f"    소스: {result['metadata'].get('source', 'N/A')}")
            print(f"    청크 ID: {result['metadata'].get('chunk_id', 'N/A')}")
            
        print("\n" + "-" * 80)
        wrapped_text = textwrap.fill(result['text'], width=80)
        print(wrapped_text)
        print("-" * 80 + "\n")
    
    return results

def list_collections(args):
    """컬렉션 목록 조회"""
    cm = ContextManager(db_path=args.db_path)
    
    collections = cm.list_collections()
    
    print(f"\n=== 컬렉션 목록 ({len(collections)}) ===\n")
    
    for i, name in enumerate(collections):
        try:
            info = cm.get_collection_info(name)
            print(f"[{i+1}] {name}: {info['count']} 청크")
            if info.get('metadata'):
                print(f"    소스: {info['metadata'].get('source', 'N/A')}")
                print(f"    유형: {info['metadata'].get('type', 'N/A')}")
        except Exception as e:
            print(f"[{i+1}] {name}: 정보 조회 실패 - {str(e)}")
        print()
    
    return collections

def collection_info(args):
    """컬렉션 정보 조회"""
    cm = ContextManager(db_path=args.db_path)
    
    info = cm.get_collection_info(args.collection_name)
    
    print(f"\n=== 컬렉션 정보: {args.collection_name} ===\n")
    print(f"청크 수: {info['count']}")
    
    if info.get('metadata'):
        print("\n메타데이터:")
        for k, v in info['metadata'].items():
            print(f"{k}: {v}")
    
    return info

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="컨텍스트 처리 및 벡터 DB 저장/검색 도구")
    subparsers = parser.add_subparsers(dest="command", help="명령")
    
    # 공통 인자
    parser.add_argument("--db-path", default="./vectordb", help="벡터 DB 경로")
    
    # 파일 처리
    parser_file = subparsers.add_parser("process_file", help="파일 처리")
    parser_file.add_argument("file_path", help="파일 경로")
    parser_file.add_argument("--chunk-size", type=int, default=500, help="청크 크기 (토큰)")
    parser_file.add_argument("--overlap", type=float, default=0.25, help="오버랩 비율 (0.0 ~ 1.0)")
    parser_file.add_argument("--method", choices=["sentence", "sliding_window"], default="sliding_window", help="청크화 방식")
    
    # URL 처리
    parser_url = subparsers.add_parser("process_url", help="URL 처리")
    parser_url.add_argument("url", help="URL")
    parser_url.add_argument("--chunk-size", type=int, default=500, help="청크 크기 (토큰)")
    parser_url.add_argument("--overlap", type=float, default=0.25, help="오버랩 비율 (0.0 ~ 1.0)")
    parser_url.add_argument("--method", choices=["sentence", "sliding_window"], default="sliding_window", help="청크화 방식")
    
    # 텍스트 처리
    parser_text = subparsers.add_parser("process_text", help="텍스트 처리")
    parser_text.add_argument("text", help="처리할 텍스트")
    parser_text.add_argument("--chunk-size", type=int, default=500, help="청크 크기 (토큰)")
    parser_text.add_argument("--overlap", type=float, default=0.25, help="오버랩 비율 (0.0 ~ 1.0)")
    parser_text.add_argument("--method", choices=["sentence", "sliding_window"], default="sliding_window", help="청크화 방식")
    
    # 검색
    parser_search = subparsers.add_parser("search", help="검색")
    parser_search.add_argument("collection_name", help="컬렉션 이름")
    parser_search.add_argument("query", help="검색 쿼리")
    parser_search.add_argument("--results", type=int, default=3, help="결과 수")
    
    # 컬렉션 목록
    subparsers.add_parser("list_collections", help="컬렉션 목록 조회")
    
    # 컬렉션 정보
    parser_info = subparsers.add_parser("collection_info", help="컬렉션 정보 조회")
    parser_info.add_argument("collection_name", help="컬렉션 이름")
    
    args = parser.parse_args()
    
    # 명령 실행
    if args.command == "process_file":
        process_file(args)
    elif args.command == "process_url":
        process_url(args)
    elif args.command == "process_text":
        process_text(args)
    elif args.command == "search":
        search(args)
    elif args.command == "list_collections":
        list_collections(args)
    elif args.command == "collection_info":
        collection_info(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 