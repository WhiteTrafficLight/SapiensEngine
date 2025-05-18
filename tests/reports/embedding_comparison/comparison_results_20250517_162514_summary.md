# 임베딩 모델 비교 실험 결과

실험 일시: 2025-05-17T16:24:57.801249

검색 제공자: google
최대 결과 수: 1

## 모델 구성

| 구성 | 쿼리 모델 | 문서 모델 |
|------|---------|----------|
| lightweight | all-MiniLM-L6-v2 | all-MiniLM-L6-v2 |
| mixed | BAAI/bge-large-en-v1.5 | all-MiniLM-L6-v2 |
| powerful | BAAI/bge-large-en-v1.5 | BAAI/bge-large-en-v1.5 |

## 실행 시간 요약 (초)

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 3.67 | 2.65 | 6.81 |
| Benefits of bananas | 0.32 | 0.28 | 0.30 |
| Why people love violence | 0.29 | 0.30 | 0.30 |
| Impact of technology on interpersonal re... | 0.28 | 0.31 | 0.30 |
| How quantum physics explains consciousne... | 0.31 | 0.29 | 0.29 |

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

- 가장 빠른 구성: **mixed** (평균 0.76초)
- 가장 느린 구성: **powerful** (평균 1.60초)
- 성능 차이: 2.1배

### 유사도 분석

- 가장 높은 유사도: **lightweight** (평균 0.0000)
- 가장 낮은 유사도: **lightweight** (평균 0.0000)
- 유사도 차이: 0.0배

### 결론

실험 결과를 바탕으로, 다음과 같은 결론을 도출할 수 있습니다:

- 속도와 유사도 사이의 균형을 고려할 때, 중간 수준의 구성(balanced)이 가장 효율적인 선택일 수 있습니다.

> 참고: 이 결론은 제한된 쿼리 세트와 검색 조건에서 도출되었으므로, 실제 사용 환경에 따라 다를 수 있습니다.
