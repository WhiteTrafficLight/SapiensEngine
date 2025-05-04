import os
import dotenv
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

# .env.local에서 OpenAI API 키 로드
dotenv_path = Path(__file__).parent.parent.parent / '.env.local'
dotenv.load_dotenv(dotenv_path)

# API 키 설정
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env.local")

# ChromaDB 클라이언트 설정
chroma_client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "vector_db"))

# 컬렉션 목록 출력
print("사용 가능한 컬렉션 목록:")
collections = chroma_client.list_collections()
for collection in collections:
    print(f"- {collection.name} (컬렉션 크기: {collection.count()})")

# 첫 번째 컬렉션이 있으면 샘플 데이터 확인
if collections:
    collection_name = collections[0].name
    embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        api_key=openai_api_key,
        model_name="text-embedding-3-small"
    )
    
    collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
    
    print(f"\n{collection_name} 컬렉션 정보:")
    print(f"총 문서 수: {collection.count()}")
    
    # 샘플 문서 가져오기 (최대 3개)
    if collection.count() > 0:
        sample_results = collection.peek(3)
        print("\n샘플 문서:")
        for i, doc_id in enumerate(sample_results["ids"]):
            print(f"\n문서 ID: {doc_id}")
            if "documents" in sample_results and len(sample_results["documents"]) > i:
                doc_text = sample_results["documents"][i]
                print(f"텍스트 (처음 200자): {doc_text[:200]}...")
            
            if "metadatas" in sample_results and len(sample_results["metadatas"]) > i:
                print(f"메타데이터: {sample_results['metadatas'][i]}")
    else:
        print("컬렉션에 문서가 없습니다.") 