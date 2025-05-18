# RAG (Retrieval Augmented Generation) 실험

이 디렉토리는 다양한 RAG 알고리즘과 파라미터 조합에 대한 실험을 구조화하고 그 성능을 측정하기 위한 프레임워크를 포함합니다.

## 실험 목표

RAG 시스템의 성능과 비용 최적화를 위한 다양한 구성요소 조합을 테스트하고 분석합니다:

1. **검색 정확도 개선**: 사용자 쿼리에 가장 관련성 높은 정보를 검색하는 능력 향상
2. **시스템 효율성 최적화**: 응답 시간, 계산 비용, 리소스 사용량 측면에서 효율적인 구성 발견
3. **다양한 도메인 적응성 평가**: 다양한 주제와 문서 유형에서의 RAG 시스템 성능 평가
4. **최적의 비용 대비 성능 지점 찾기**: 성능과 계산 비용 간의 최적 균형점 식별

## 실험 파라미터

### 1. 문서 청크화 (Document Chunking)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `chunk_size` | 각 청크의 크기 (토큰 또는 문자 단위) | 100-1000 |
| `chunk_overlap` | 인접 청크 간 중복 정도 | 0-50% |
| `chunking_strategy` | 텍스트 분할 방법 | "text_splitter", "paragraph", "sentence", "semantic" |
| `chunk_metadata` | 청크에 포함할 메타데이터 | "source", "page_num", "token_count" |

### 2. 임베딩 모델 (Embedding Models)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `embedding_model` | 텍스트 임베딩 생성에 사용할 모델 | "all-MiniLM-L6-v2", "all-mpnet-base-v2", "BAAI/bge-large-en-v1.5" |
| `embedding_dims` | 임베딩 벡터 차원 | 384, 768, 1024 |
| `query_embedding_model` | 쿼리 임베딩에 사용할 모델 (이중 모델 구성 시) | 동일한 모델 목록 |
| `doc_embedding_model` | 문서 임베딩에 사용할 모델 (이중 모델 구성 시) | 동일한 모델 목록 |

### 3. 검색 알고리즘 (Retrieval Algorithms)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `search_algorithm` | 관련 문서 검색에 사용할 알고리즘 | "top_k", "semantic", "hybrid", "threshold" |
| `top_k` | 반환할 최상위 결과 수 | 3-10 |
| `similarity_threshold` | 최소 유사도 임계값 | 0.5-0.9 |
| `similarity_metric` | 유사도 계산 방법 | "cosine", "dot_product", "euclidean" |
| `reranker_model` | 검색 후 재순위화에 사용할 모델 | "none", "cross-encoder/ms-marco-MiniLM-L-6-v2" |

### 4. 쿼리 강화 (Query Enhancement)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `query_enhancement` | 쿼리 강화 활성화 여부 | true, false |
| `enhancement_type` | 쿼리 강화 방법 | "none", "expansion", "rephrasing", "decomposition", "hybrid" |
| `enhancement_model` | 쿼리 강화에 사용할 모델 | "gpt-3.5-turbo", "gpt-4", "claude-3-sonnet" |
| `expansion_terms` | 추가할 확장 용어 수 | 3-10 |

### 5. 웹 검색 통합 (Web Search Integration)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `web_search_enabled` | 웹 검색 통합 활성화 여부 | true, false |
| `search_provider` | 웹 검색 제공자 | "google", "bing", "serpapi" |
| `max_results` | 검색할 최대 결과 수 | 3-10 |
| `web_content_max_tokens` | 웹 콘텐츠당 최대 토큰 수 | 500-2000 |

### 6. 결과 융합 (Result Fusion)

| 파라미터 | 설명 | 가능한 값 |
|---------|------|----------|
| `fusion_strategy` | 여러 소스의 결과를 결합하는 방법 | "interleave", "weighted", "ranked_fusion" |
| `local_weight` | 로컬 문서 결과 가중치 | 0.0-1.0 |
| `web_weight` | 웹 검색 결과 가중치 | 0.0-1.0 |

## 평가 지표 (Evaluation Metrics)

| 지표 | 설명 | 단위 |
|-----|------|-----|
| `avg_similarity` | 검색된 청크의 평균 유사도 | 0-1 |
| `top_chunk_similarity` | 최상위 청크 유사도 | 0-1 |
| `retrieval_precision` | 관련 문서 검색 정확도 | 0-1 |
| `retrieval_recall` | 관련 문서 검색 재현율 | 0-1 |
| `query_latency` | 쿼리 처리 시간 | ms |
| `memory_usage` | 메모리 사용량 | MB |
| `token_usage` | API 호출에 사용된 토큰 수 | count |
| `estimated_cost` | 예상 API 비용 | USD |

## 실험 프로세스

1. **데이터 준비**: 테스트 문서 및 쿼리 세트 구성
2. **실험 구성**: 테스트할 파라미터 조합 정의
3. **실험 실행**: 각 구성에 대한 실험 자동화
4. **결과 수집**: 성능 지표 측정 및 저장
5. **분석 및 시각화**: 결과 분석 및 인사이트 도출
6. **최적 구성 도출**: 목표에 가장 적합한 파라미터 조합 식별

## 사용 예시

```bash
# 기본 실험 실행
python -m experiments.rag.run_experiment --config configs/basic_config.yaml

# 임베딩 모델 비교 실험
python -m experiments.rag.run_experiment --configs-dir configs/embedding_models/

# 결과 시각화 및 분석
python -m experiments.rag.visualize --results-dir results/embedding_experiment/
```

## 결과 저장 구조

```
results/
├── experiment_20240517_123045/
│   ├── config.json        # 실험 구성
│   ├── results.json       # 상세 결과
│   ├── metrics.json       # 성능 지표 요약
│   └── visualizations/    # 시각화 결과
└── experiment_20240517_143022/
    ├── ...
``` 