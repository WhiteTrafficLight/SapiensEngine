"""
실험 결과 평가를 위한 메트릭 및 지표 계산 유틸리티
"""

import time
import numpy as np
import psutil
from typing import List, Dict, Any, Optional, Tuple, Union


class ExperimentMetrics:
    """실험 결과 평가 지표 계산 클래스"""
    
    @staticmethod
    def calculate_similarity_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        유사도 관련 지표 계산
        
        Args:
            results: 검색 결과 목록
            
        Returns:
            유사도 지표가 포함된 딕셔너리
        """
        if not results:
            return {
                "avg_similarity": 0.0,
                "top_chunk_similarity": 0.0,
                "min_similarity": 0.0,
                "max_similarity": 0.0,
                "median_similarity": 0.0
            }
        
        # 유사도 추출
        similarities = [r.get("similarity", 0.0) for r in results]
        
        # 결과가 없거나 유사도가 없는 경우
        if not similarities:
            return {
                "avg_similarity": 0.0,
                "top_chunk_similarity": 0.0,
                "min_similarity": 0.0,
                "max_similarity": 0.0,
                "median_similarity": 0.0
            }
            
        return {
            "avg_similarity": float(np.mean(similarities)),
            "top_chunk_similarity": float(similarities[0]) if similarities else 0.0,
            "min_similarity": float(np.min(similarities)),
            "max_similarity": float(np.max(similarities)),
            "median_similarity": float(np.median(similarities))
        }
    
    @staticmethod
    def calculate_performance_metrics(start_time: float, 
                                    end_time: float, 
                                    token_usage: Dict[str, int] = None) -> Dict[str, Any]:
        """
        성능 관련 지표 계산
        
        Args:
            start_time: 시작 시간 (time.time() 값)
            end_time: 종료 시간 (time.time() 값)
            token_usage: 토큰 사용량 (선택사항)
            
        Returns:
            성능 지표가 포함된 딕셔너리
        """
        # 기본 성능 지표
        metrics = {
            "execution_time": end_time - start_time,
            "memory_usage": psutil.Process().memory_info().rss / (1024 * 1024)  # MB 단위
        }
        
        # 토큰 사용량 및 비용 추정
        if token_usage:
            metrics.update({
                "token_usage": token_usage,
                "estimated_cost": ExperimentMetrics.estimate_api_cost(token_usage)
            })
            
        return metrics
    
    @staticmethod
    def calculate_retrieval_metrics(retrieved_ids: List[str], 
                                   relevant_ids: List[str],
                                   k: int = None) -> Dict[str, float]:
        """
        검색 정확도 관련 지표 계산
        
        Args:
            retrieved_ids: 검색된 문서/청크 ID 목록
            relevant_ids: 관련성 있는 문서/청크 ID 목록 (정답 세트)
            k: 정확도 계산에 사용할 상위 k개 결과 (기본값: 모든 결과)
            
        Returns:
            검색 정확도 지표가 포함된 딕셔너리
        """
        if not retrieved_ids or not relevant_ids:
            return {
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "mrr": 0.0
            }
            
        # 상위 k개 결과로 제한
        if k is not None and k < len(retrieved_ids):
            retrieved_ids = retrieved_ids[:k]
            
        # 관련 문서 수
        retrieved_relevant = [doc_id for doc_id in retrieved_ids if doc_id in relevant_ids]
        num_retrieved_relevant = len(retrieved_relevant)
        
        # 정밀도 (Precision): 검색된 문서 중 관련 문서의 비율
        precision = num_retrieved_relevant / len(retrieved_ids) if retrieved_ids else 0.0
        
        # 재현율 (Recall): 관련 문서 중 검색된 문서의 비율
        recall = num_retrieved_relevant / len(relevant_ids) if relevant_ids else 0.0
        
        # F1 점수: 정밀도와 재현율의 조화 평균
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # MRR (Mean Reciprocal Rank): 첫 번째 관련 문서의 순위 역수의 평균
        mrr = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_ids:
                mrr = 1.0 / (i + 1)
                break
                
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "mrr": mrr
        }
    
    @staticmethod
    def estimate_api_cost(token_usage: Dict[str, int]) -> float:
        """
        API 토큰 사용량에 따른 비용 추정
        
        Args:
            token_usage: 모델별 토큰 사용량
                예: {"gpt-3.5-turbo": {"prompt": 500, "completion": 300}}
                
        Returns:
            추정 비용 (USD)
        """
        # 모델별 비용 테이블 (USD/1K 토큰)
        cost_table = {
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075}
        }
        
        total_cost = 0.0
        
        for model, usage in token_usage.items():
            if model in cost_table:
                model_costs = cost_table[model]
                
                # 입력 토큰 비용
                prompt_tokens = usage.get("prompt", 0)
                total_cost += (prompt_tokens / 1000) * model_costs["prompt"]
                
                # 출력 토큰 비용
                completion_tokens = usage.get("completion", 0)
                total_cost += (completion_tokens / 1000) * model_costs["completion"]
        
        return total_cost


class PerformanceTimer:
    """실험 성능 측정을 위한 타이머 유틸리티"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.checkpoints = {}
        
    def start(self):
        """타이머 시작"""
        self.start_time = time.time()
        self.checkpoints = {"start": self.start_time}
        return self.start_time
        
    def checkpoint(self, name: str):
        """중간 시점 기록"""
        if not self.start_time:
            self.start()
            
        checkpoint_time = time.time()
        self.checkpoints[name] = checkpoint_time
        return checkpoint_time
        
    def stop(self):
        """타이머 종료"""
        self.end_time = time.time()
        self.checkpoints["end"] = self.end_time
        return self.end_time
        
    def get_execution_time(self) -> float:
        """전체 실행 시간"""
        if not self.start_time:
            return 0.0
            
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
        
    def get_checkpoint_time(self, name: str) -> float:
        """특정 체크포인트까지의 시간"""
        if name not in self.checkpoints or not self.start_time:
            return 0.0
            
        return self.checkpoints[name] - self.start_time
        
    def get_interval(self, start_name: str, end_name: str) -> float:
        """두 체크포인트 사이의 시간"""
        if (start_name not in self.checkpoints or 
            end_name not in self.checkpoints):
            return 0.0
            
        return self.checkpoints[end_name] - self.checkpoints[start_name]
        
    def get_all_intervals(self) -> Dict[str, float]:
        """모든 체크포인트 간격"""
        if not self.checkpoints:
            return {}
            
        intervals = {}
        checkpoint_names = list(self.checkpoints.keys())
        
        for i in range(len(checkpoint_names) - 1):
            start_name = checkpoint_names[i]
            end_name = checkpoint_names[i + 1]
            interval_name = f"{start_name}_to_{end_name}"
            intervals[interval_name] = self.checkpoints[end_name] - self.checkpoints[start_name]
            
        return intervals 