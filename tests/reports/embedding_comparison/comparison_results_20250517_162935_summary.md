# 임베딩 모델 비교 실험 결과

실험 일시: 2025-05-17T16:29:07.162599

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
| Cases where excessive adherence to the l... | 4.51 | 6.84 | 7.67 |
| Benefits of bananas | 1.63 | 1.09 | 1.00 |
| Why people love violence | 1.07 | 1.14 | 0.62 |
| Impact of technology on interpersonal re... | 0.88 | 0.36 | 0.39 |
| How quantum physics explains consciousne... | 0.88 | 0.08 | 0.10 |

## 최상위 청크 유사도

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 0.4621 | 0.4677 | 0.6391 |
| Benefits of bananas | 0.0000 | 0.0000 | 0.0000 |
| Why people love violence | 0.0000 | 0.0000 | 0.0000 |
| Impact of technology on interpersonal re... | 0.0000 | 0.0000 | 0.0000 |
| How quantum physics explains consciousne... | 0.0000 | 0.0000 | 0.0000 |

## 평균 청크 유사도

| 쿼리 | lightweight | mixed | powerful |
|------|------|------|------|
| Cases where excessive adherence to the l... | 0.3734 | 0.3584 | 0.5599 |
| Benefits of bananas | 0.0000 | 0.0000 | 0.0000 |
| Why people love violence | 0.0000 | 0.0000 | 0.0000 |
| Impact of technology on interpersonal re... | 0.0000 | 0.0000 | 0.0000 |
| How quantum physics explains consciousne... | 0.0000 | 0.0000 | 0.0000 |

## 분석 및 결론

### 실행 시간 분석

- 가장 빠른 구성: **lightweight** (평균 1.79초)
- 가장 느린 구성: **powerful** (평균 1.96초)
- 성능 차이: 1.1배

### 유사도 분석

- 가장 높은 유사도: **powerful** (평균 0.1120)
- 가장 낮은 유사도: **mixed** (평균 0.0717)
- 유사도 차이: 1.6배

### 결론

실험 결과를 바탕으로, 다음과 같은 결론을 도출할 수 있습니다:

- **powerful** 구성이 유사도 면에서 크게 우수하므로, 약간의 속도 저하를 감수하더라도 이 구성을 사용하는 것이 권장됩니다.

> 참고: 이 결론은 제한된 쿼리 세트와 검색 조건에서 도출되었으므로, 실제 사용 환경에 따라 다를 수 있습니다.
