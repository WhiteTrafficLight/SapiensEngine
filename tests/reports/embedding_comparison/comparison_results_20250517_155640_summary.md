# 임베딩 모델 비교 실험 결과

실험 일시: 2025-05-17T15:55:15.921099

검색 제공자: google
최대 결과 수: 3

## 모델 구성

| 구성 | 쿼리 모델 | 문서 모델 |
|------|---------|----------|
| lightweight | all-MiniLM-L6-v2 | all-MiniLM-L6-v2 |
| mixed | BAAI/bge-large-en-v1.5 | all-MiniLM-L6-v2 |
| powerful | BAAI/bge-large-en-v1.5 | BAAI/bge-large-en-v1.5 |

## 실행 시간 요약 (초)

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 3.35 | 73.78 | 5.48 |
| Benefits of bananas | 0.20 | 0.20 | 0.20 |
| Why people love violence | 0.19 | 0.23 | 0.20 |
| Impact of technology on interpersonal re... | 0.19 | 0.20 | 0.21 |
| How quantum physics explains consciousne... | 0.20 | 0.20 | 0.20 |

## 최상위 청크 유사도

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 0.0000 | 0.0000 | 0.0000 |
| Benefits of bananas | 0.0000 | 0.0000 | 0.0000 |
| Why people love violence | 0.0000 | 0.0000 | 0.0000 |
| Impact of technology on interpersonal re... | 0.0000 | 0.0000 | 0.0000 |
| How quantum physics explains consciousne... | 0.0000 | 0.0000 | 0.0000 |

## 평균 청크 유사도

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 0.0000 | 0.0000 | 0.0000 |
| Benefits of bananas | 0.0000 | 0.0000 | 0.0000 |
| Why people love violence | 0.0000 | 0.0000 | 0.0000 |
| Impact of technology on interpersonal re... | 0.0000 | 0.0000 | 0.0000 |
| How quantum physics explains consciousne... | 0.0000 | 0.0000 | 0.0000 |

## 분석 및 결론

### 실행 시간 분석

- 가장 빠른 구성: **lightweight** (평균 0.83초)
- 가장 느린 구성: **mixed** (평균 14.92초)
- 성능 차이: 18.1배

### 유사도 분석

- 가장 높은 유사도: **lightweight** (평균 0.0000)
- 가장 낮은 유사도: **lightweight** (평균 0.0000)
- 유사도 차이: 0.0배

### 결론

실험 결과를 바탕으로, 다음과 같은 결론을 도출할 수 있습니다:

- 유사도 차이가 크지 않은 반면, **lightweight** 구성이 속도 면에서 매우 우수하므로 이 구성을 사용하는 것이 효율적입니다.

> 참고: 이 결론은 제한된 쿼리 세트와 검색 조건에서 도출되었으므로, 실제 사용 환경에 따라 다를 수 있습니다.
