# RAG 실험 설정 파라미터 참조 가이드

이 문서는 RAG(Retrieval Augmented Generation) 실험에 사용되는 모든 설정 파라미터에 대한 참조 가이드입니다. 각 파라미터의 의미, 가능한 값, 기본값을 설명합니다.

## 목차

1. [기본 정보 파라미터](#기본-정보-파라미터)
2. [청크화 설정 파라미터](#청크화-설정-파라미터)
3. [임베딩 모델 파라미터](#임베딩-모델-파라미터)
4. [검색 알고리즘 기본 파라미터](#검색-알고리즘-기본-파라미터)
5. [검색 알고리즘 추가 파라미터](#검색-알고리즘-추가-파라미터)
6. [쿼리 강화 파라미터](#쿼리-강화-파라미터)
7. [웹 검색 통합 파라미터](#웹-검색-통합-파라미터)
8. [결과 융합 파라미터](#결과-융합-파라미터)
9. [테스트 데이터 파라미터](#테스트-데이터-파라미터)
10. [설정 파일 예제](#설정-파일-예제)

## 기본 정보 파라미터

실험의 기본 정보를 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `experiment_id` | 실험의 고유 식별자 | 문자열 | 자동 생성된 UUID |
| `name` | 실험 이름 | 문자열 | `experiment_{experiment_id}` |
| `description` | 실험에 대한 설명 | 문자열 | `""` (빈 문자열) |
| `timestamp` | 실험 시작 시간 | ISO 형식 날짜시간 | 현재 시간 |

## 청크화 설정 파라미터

문서를 청크(조각)로 나누는 방법을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 구현된 값 | 기본값 |
|----------|------|-----------|--------|
| `chunk_size` | 각 청크의 최대 토큰 수 | 정수 (100~2000 권장) | 500 |
| `chunk_overlap` | 인접한 청크 간 중복 비율 | 0.0~1.0 사이 실수 (예: 0.25는 25% 오버랩) | 0.25 (25%) |
| `chunking_strategy` | 청크화 방법 (내부적으로는 `chunking_method`로 전달됨) | "sentence", "sliding_window", "hybrid" | "sliding_window" |
| `chunk_metadata` | 청크에 포함할 메타데이터 | 문자열 목록 | ["source", "page_num"] |

### 구현된 청크화 전략 설명

| 전략 이름 | 실제 구현 이름 | 설명 | 
|-----------|--------------|------|
| `"sentence"` | 문장 단위 청크화 | RecursiveCharacterTextSplitter를 사용하여 문장 및 단락 구분자를 기준으로 텍스트 분할 |
| `"sliding_window"` | 슬라이딩 윈도우 | SentenceTransformersTokenTextSplitter를 사용하여 토큰 수를 기준으로 텍스트 분할 |
| `"hybrid"` | 하이브리드 청크화 | 문장 단위로 분리한 후 토큰 수를 고려하여 청크 생성, 문장 경계를 유지하면서 토큰 수와 오버랩 적용 |

> **중요**: `chunking_strategy` 파라미터는 `ContextManager` 클래스 내부에서 `chunking_method`로 처리됩니다. 설정 파일에서는 `chunking_strategy`로 지정하세요.

## 임베딩 모델 파라미터

문서와 쿼리를 벡터로 변환하는 임베딩 모델을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `embedding_model` | 기본 임베딩 모델 | 임베딩 모델 이름 | "BAAI/bge-large-en-v1.5" |
| `embedding_dims` | 임베딩 차원 수 | 정수 | 1024 |
| `query_embedding_model` | 쿼리 전용 임베딩 모델 (지정하지 않으면 `embedding_model` 사용) | 임베딩 모델 이름 | None |
| `doc_embedding_model` | 문서 전용 임베딩 모델 (지정하지 않으면 `embedding_model` 사용) | 임베딩 모델 이름 | None |

### 대표적인 임베딩 모델 옵션

| 모델 이름 | 차원 | 특징 |
|-----------|------|------|
| "BAAI/bge-large-en-v1.5" | 1024 | 영어 전용 대형 모델 |
| "BAAI/bge-base-en-v1.5" | 768 | 영어 전용 기본 모델 |
| "BAAI/bge-large-ko-v1.5" | 1024 | 한국어 지원 대형 모델 |
| "BAAI/bge-base-ko-v1.5" | 768 | 한국어 지원 기본 모델 |
| "intfloat/multilingual-e5-large" | 1024 | 다국어 지원 대형 모델 |
| "sentence-transformers/all-MiniLM-L6-v2" | 384 | 경량 다국어 모델 |

## 검색 알고리즘 기본 파라미터

검색 알고리즘의 기본 동작을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `search_algorithm` | 사용할 검색 알고리즘 | "top_k", "threshold", "adjacent_chunks", "merged_chunks", "semantic_window", "hybrid", "mmr", "conversational" | "top_k" |
| `top_k` | 반환할 최대 결과 수 | 정수 (1~20 권장) | 5 |
| `similarity_threshold` | 유사도 임계값 (이 값 이상의 유사도를 가진 결과만 반환) | 0~1 사이 실수 | 0.6 |
| `similarity_metric` | 유사도 계산 방식 | "cosine", "dot_product", "euclidean" | "cosine" |
| `reranker_model` | 결과 재정렬에 사용할 모델 | 모델 이름 또는 "none" | "none" |

### 검색 알고리즘 설명

| 알고리즘 | 설명 | 주요 파라미터 |
|----------|------|--------------|
| "top_k" | 가장 기본적인 검색 방식으로, 유사도가 가장 높은 상위 K개 청크 반환 | `top_k` |
| "threshold" | 임계값 이상의 유사도를 가진 청크만 반환 | `similarity_threshold`, `top_k` |
| "adjacent_chunks" | 검색된 청크의 앞뒤 청크도 함께 반환 | `top_k`, `neighbor_threshold` |
| "merged_chunks" | 유사한 인접 청크를 하나로 병합하여 반환 | `top_k`, `similarity_threshold` |
| "semantic_window" | 각 청크 주변에 의미적으로 관련된 청크를 동적으로 포함 | `top_k`, `window_size`, `window_threshold` |
| "hybrid" | 벡터 기반 의미적 검색과 키워드 기반 검색을 결합 | `top_k`, `semantic_weight` |
| "mmr" | 다양성과 관련성의 균형을 맞추는 Maximum Marginal Relevance 알고리즘 | `top_k`, `lambda_param`, `initial_results` |
| "conversational" | 대화 맥락을 고려한 검색 알고리즘 | `top_k`, `history_weight` |

## 검색 알고리즘 추가 파라미터

특정 검색 알고리즘에 필요한 추가 파라미터입니다.

| 파라미터 | 설명 | 사용 알고리즘 | 가능한 값 | 기본값 |
|----------|------|--------------|-----------|--------|
| `neighbor_threshold` | 인접 청크 포함 임계값 | adjacent_chunks | 0~1 사이 실수 | 0.5 |
| `window_size` | 의미적 윈도우 크기 (앞뒤로 몇 개의 청크를 고려할지) | semantic_window | 정수 (1~10 권장) | 5 |
| `window_threshold` | 윈도우 포함 임계값 | semantic_window | 0~1 사이 실수 | 0.6 |
| `semantic_weight` | 의미적 검색 가중치 (하이브리드 검색에서 벡터 검색의 비중) | hybrid | 0~1 사이 실수 (높을수록 의미적 검색 중시) | 0.7 |
| `lambda_param` | MMR 알고리즘의 람다 파라미터 | mmr | 0~1 사이 실수 (높을수록 관련성 중시, 낮을수록 다양성 중시) | 0.7 |
| `initial_results` | MMR 계산을 위한 초기 풀 크기 | mmr | 정수 (10~30 권장) | 20 |
| `history_weight` | 대화 이력 가중치 | conversational | 0~1 사이 실수 | 0.3 |

## 쿼리 강화 파라미터

쿼리를 강화하는 방법을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `query_enhancement` | 쿼리 강화 사용 여부 | true, false | false |
| `enhancement_type` | 쿼리 강화 방식 | "none", "expansion", "rephrasing", "decomposition", "hybrid" | "none" |
| `enhancement_model` | 쿼리 강화에 사용할 모델 | 모델 이름 | "gpt-3.5-turbo" |
| `expansion_terms` | 확장 용어 수 (expansion 방식에서 사용) | 정수 (3~10 권장) | 5 |

### 쿼리 강화 방식 설명

| 강화 방식 | 설명 | 예시 |
|-----------|------|------|
| "none" | 강화하지 않음 | 원본 쿼리 그대로 사용 |
| "expansion" | 키워드 확장 | "AI 안전성" → "AI 안전성 위험 위협 미래 통제 정책" |
| "rephrasing" | 쿼리 재구성 | "AI 위험성은?" → "인공지능 기술의 잠재적 위험과 부작용은 무엇인가?" |
| "decomposition" | 쿼리 분해 | "트랜스포머 모델 구조와 작동 방식" → ["트랜스포머 모델의 기본 구조", "어텐션 메커니즘 작동 원리", "인코더-디코더 아키텍처"] |
| "hybrid" | 혼합 방식 | 위 방식들의 조합 |

## 웹 검색 통합 파라미터

웹 검색을 통합하는 방법을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `web_search_enabled` | 웹 검색 사용 여부 | true, false | false |
| `search_provider` | 웹 검색 제공자 | "google", "bing", "serpapi" | "google" |
| `max_results` | 검색 결과 최대 수 | 정수 (3~10 권장) | 5 |
| `web_content_max_tokens` | 웹 컨텐츠 최대 토큰 수 | 정수 (500~2000 권장) | 1000 |

## 결과 융합 파라미터

로컬 문서와 웹 검색 결과를 융합하는 방법을 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `fusion_strategy` | 결과 융합 전략 | "weighted", "interleave", "ranked_fusion" | "weighted" |
| `local_weight` | 로컬 결과 가중치 | 0~1 사이 실수 | 0.7 |
| `web_weight` | 웹 결과 가중치 | 0~1 사이 실수 | 0.3 |

### 융합 전략 설명

| 전략 | 설명 | 주요 파라미터 |
|------|------|--------------|
| "weighted" | 각 소스(로컬/웹)의 결과에 가중치를 적용하여 통합 | `local_weight`, `web_weight` |
| "interleave" | 각 소스에서 번갈아가며 결과를 선택 | - |
| "ranked_fusion" | 각 소스의 결과를 순위 기반으로 통합 | - |

## 테스트 데이터 파라미터

실험에 사용할 데이터를 설정하는 파라미터입니다.

| 파라미터 | 설명 | 가능한 값 | 기본값 |
|----------|------|-----------|--------|
| `data_sources` | 문서 소스 경로 목록 | 파일 경로 목록 (PDF, TXT, URL 등) | [] (빈 목록) |
| `test_queries` | 테스트 쿼리 목록 | 문자열 목록 | [] (빈 목록) |

## 설정 파일 예제

### 기본 Top-K 검색 설정 (YAML)

```yaml
experiment_id: top_k_01
name: "Top-K 검색 알고리즘 테스트"
description: "간단한 Top-K 검색 알고리즘을 사용한 RAG 실험"
search_algorithm: "top_k"
top_k: 5
chunk_size: 500
chunk_overlap: 50
chunking_strategy: "text_splitter"
embedding_model: "BAAI/bge-large-en-v1.5"
query_enhancement: false
web_search_enabled: false
data_sources:
  - "data/papers/ai_safety.pdf"
  - "data/papers/transformer_models.pdf"
test_queries:
  - "인공지능 안전성의 주요 위험 요소는 무엇인가?"
  - "트랜스포머 모델의 어텐션 메커니즘은 어떻게 작동하는가?"
```

### 의미적 윈도우 검색 설정 (YAML)

```yaml
experiment_id: semantic_window_01
name: "의미적 윈도우 검색 알고리즘 테스트"
description: "각 청크 주변에 의미적 윈도우를 형성하는 검색 알고리즘"
search_algorithm: "semantic_window"
top_k: 3
window_size: 5
window_threshold: 0.6
chunk_size: 400
chunk_overlap: 50
chunking_strategy: "text_splitter"
embedding_model: "BAAI/bge-large-en-v1.5"
data_sources:
  - "data/papers/ai_safety.pdf"
  - "data/papers/transformer_models.pdf"
test_queries:
  - "신경망의 발전 역사는 어떻게 되는가?"
```

### 웹 검색 통합 설정 (YAML)

```yaml
experiment_id: web_hybrid_01
name: "웹 검색 통합 하이브리드 테스트"
description: "로컬 문서와 웹 검색 결과를 통합하는 실험"
search_algorithm: "hybrid"
top_k: 5
semantic_weight: 0.7
chunk_size: 500
chunk_overlap: 50
chunking_strategy: "text_splitter"
embedding_model: "BAAI/bge-large-en-v1.5"
web_search_enabled: true
search_provider: "google"
max_results: 5
fusion_strategy: "weighted"
local_weight: 0.6
web_weight: 0.4
data_sources:
  - "data/papers/ai_safety.pdf"
test_queries:
  - "최근 AI 안전성 연구 동향은 무엇인가?"
``` 