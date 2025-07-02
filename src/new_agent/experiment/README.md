# 웹서치 성능 비교 실험

Google API 직렬 검색 vs OpenAI 웹서치 툴 병렬 검색 성능 비교 실험

## 📋 실험 개요

"AI가 인간의 새로운 진화이다"라는 주제에 대해 다음 두 가지 웹서치 방법의 성능을 비교합니다:

1. **Google API 직렬 검색** (기존 방식)
   - Google Custom Search API 사용
   - 쿼리를 순차적으로 하나씩 처리
   - 전통적인 웹서치 접근법

2. **OpenAI 웹서치 툴 병렬 검색** (새로운 방식)
   - OpenAI Responses API의 web_search_preview 도구 사용
   - 여러 쿼리를 동시에 병렬 처리
   - AI 기반 지능형 웹서치

## 🧬 테스트 쿼리

AI 진화 주제에 대한 영어 쿼리 3개:
1. `"AI artificial intelligence human evolution next step technological enhancement"`
2. `"machine learning augmented human capabilities cognitive enhancement future evolution"`
3. `"artificial intelligence symbiosis human development evolutionary leap biological technology"`

## 🚀 설치 및 실행

### 1. 필수 환경 변수 설정

```bash
# Google API 설정
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_SEARCH_CX="your-google-custom-search-cx"

# OpenAI API 설정
export OPENAI_API_KEY="your-openai-api-key"
```

### 2. 의존성 설치

```bash
pip install openai requests pandas matplotlib asyncio
```

### 3. 실험 실행

```bash
cd /Users/jihoon/sapiens_engine/src/new_agent/experiment
python ai_evolution_search_test.py
```

## 📊 측정 지표

### 성능 지표
- **총 소요시간**: 모든 쿼리 처리에 걸린 총 시간
- **쿼리당 평균 시간**: 개별 쿼리 처리 시간의 평균
- **병렬 효율성**: OpenAI의 병렬 처리 효율성 (총 개별 시간 / 전체 실행 시간)
- **결과 수**: 각 방법으로 얻은 검색 결과의 총 개수
- **초당 결과 수**: 시간당 검색 결과 효율성

### 비교 분석
- **속도 비교**: 두 방법의 실행 시간 비교
- **결과 품질**: 검색 결과의 관련성과 유용성
- **성능 향상률**: 더 빠른 방법의 개선 정도 (%)

## 📁 파일 구조

```
experiment/
├── __init__.py                    # 모듈 초기화
├── google_serial_search.py        # Google API 직렬 검색 구현
├── openai_parallel_search.py      # OpenAI 병렬 검색 구현
├── performance_comparison.py      # 성능 비교 분석 도구
├── ai_evolution_search_test.py    # 메인 테스트 실행 스크립트
└── README.md                      # 사용법 설명 (이 파일)
```

## 🔧 주요 클래스

### GoogleSerialSearcher
```python
# Google API를 사용한 직렬 웹검색
searcher = GoogleSerialSearcher(api_key="...", cx="...")
result = searcher.search_multiple_queries_serial(queries, num_results=5)
```

### OpenAIParallelSearcher
```python
# OpenAI 웹서치 툴을 사용한 병렬 검색
searcher = OpenAIParallelSearcher(api_key="...")
result = searcher.search_multiple_queries_parallel_sync(queries, context_size="low")
```

### WebSearchPerformanceComparison
```python
# 성능 비교 도구
comparator = WebSearchPerformanceComparison(
    google_api_key="...", 
    google_cx="...", 
    openai_api_key="..."
)
result = comparator.run_ai_evolution_experiment(num_results=5)
```

## 📈 예상 결과

실험 실행 후 다음과 같은 결과를 확인할 수 있습니다:

```
🏆 웹서치 성능 비교 결과 요약
======================================================================
📊 시간 성능:
   🔍 Google 직렬:    8.45초
   🚀 OpenAI 병렬:    3.22초
   ⚡ 시간 차이:      5.23초
   📈 속도 비율:      2.62배

📋 결과 수:
   🔍 Google 결과:    15개
   🚀 OpenAI 결과:    3개

⚡ 효율성:
   🔍 Google 효율:    1.78 결과/초
   🚀 OpenAI 효율:    0.93 결과/초
   🎯 병렬 효율성:    2.85

🏆 승자: OpenAI Parallel
📈 성능 향상: 61.9%
======================================================================
```

## 📄 결과 저장

실험 결과는 다음 형태로 저장됩니다:

1. **JSON 파일**: `websearch_comparison_YYYYMMDD_HHMMSS.json`
   - 모든 실험 데이터와 성능 지표
   - 개별 검색 결과와 메타데이터
   - 상세 성능 분석 결과

2. **로그 파일**: `websearch_test_YYYYMMDD_HHMMSS.log`
   - 실험 실행 과정의 상세 로그
   - 디버깅과 문제 해결에 활용

## 🔍 결과 해석

### 시간 성능
- **OpenAI 병렬 검색**이 일반적으로 더 빠름 (병렬 처리 효과)
- **Google 직렬 검색**은 쿼리 수에 비례하여 시간 증가

### 결과 품질
- **Google API**: 더 많은 검색 결과, 전통적인 웹페이지 기반
- **OpenAI 웹서치**: AI가 선별한 고품질 결과, 요약 정보 포함

### 사용 권장사항
- **속도 우선**: OpenAI 병렬 검색 권장
- **결과 수 우선**: Google 직렬 검색 권장
- **품질 우선**: OpenAI 웹서치의 AI 요약 활용

## ⚠️ 주의사항

1. **API 한도**: 각 API의 사용 한도와 비용을 고려
2. **네트워크 상태**: 인터넷 연결 상태가 결과에 영향
3. **API 키 보안**: API 키를 코드에 하드코딩하지 말 것
4. **실험 재현성**: 검색 결과는 시간에 따라 변할 수 있음

## 🛠️ 문제 해결

### 일반적인 오류

1. **API 키 오류**
   ```
   ValueError: Google API 키가 설정되지 않았습니다
   ```
   → 환경 변수 `GOOGLE_API_KEY`, `GOOGLE_SEARCH_CX` 확인

2. **OpenAI API 오류**
   ```
   ValueError: OpenAI API 키가 설정되지 않았습니다
   ```
   → 환경 변수 `OPENAI_API_KEY` 확인

3. **모듈 import 오류**
   ```
   ImportError: 모듈 import 실패
   ```
   → 필수 패키지 설치 확인: `pip install openai requests`

### 성능 최적화

1. **OpenAI 컨텍스트 크기 조정**
   ```python
   # 더 빠른 검색을 위해 "low" 사용
   # 더 정확한 검색을 위해 "medium" 또는 "high" 사용
   context_size="low"  # 기본값
   ```

2. **결과 수 조정**
   ```python
   # 빠른 테스트를 위해 적은 수 사용
   num_results=3  # 기본값: 5
   ```

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 생성하거나 개발팀에 문의하세요.

---

**실험을 통해 두 웹서치 방법의 특성을 이해하고, 프로젝트에 가장 적합한 방법을 선택하세요!** 🚀 