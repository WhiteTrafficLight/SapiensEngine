"""
실험 설정을 위한 구성 클래스 및 유틸리티
"""

import os
import json
import uuid
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ExperimentConfig:
    """
    RAG 실험 설정을 저장하고 관리하는 클래스
    """
    # 실험 기본 정보
    experiment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 청크화 설정
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunking_strategy: str = "text_splitter"  # text_splitter, paragraph, sentence, semantic
    chunk_metadata: List[str] = field(default_factory=lambda: ["source", "page_num"])
    
    # 임베딩 모델
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dims: int = 1024
    query_embedding_model: Optional[str] = None  # None이면 embedding_model과 동일
    doc_embedding_model: Optional[str] = None    # None이면 embedding_model과 동일
    
    # 검색 알고리즘
    search_algorithm: str = "top_k"  # top_k, threshold, adjacent_chunks, merged_chunks, semantic_window, hybrid, mmr, conversational
    top_k: int = 5
    similarity_threshold: float = 0.6
    similarity_metric: str = "cosine"  # cosine, dot_product, euclidean
    reranker_model: str = "none"
    
    # 추가적인 검색 알고리즘 파라미터
    neighbor_threshold: float = 0.5  # adjacent_chunks 알고리즘용
    window_size: int = 5  # semantic_window 알고리즘용
    window_threshold: float = 0.6  # semantic_window 알고리즘용
    semantic_weight: float = 0.7  # hybrid 알고리즘용
    lambda_param: float = 0.7  # mmr 알고리즘용
    initial_results: int = 20  # mmr 알고리즘용
    history_weight: float = 0.3  # conversational 알고리즘용
    
    # 쿼리 강화
    query_enhancement: bool = False
    enhancement_type: str = "none"  # none, expansion, rephrasing, decomposition, hybrid
    enhancement_model: str = "gpt-3.5-turbo"
    expansion_terms: int = 5
    
    # 웹 검색 통합
    web_search_enabled: bool = False
    search_provider: str = "google"  # google, bing, serpapi
    max_results: int = 5
    web_content_max_tokens: int = 1000
    advanced_scoring: bool = False  # 웹 검색 결과에 고급 점수 계산 사용 여부
    
    # 결과 융합
    fusion_strategy: str = "weighted"  # interleave, weighted, ranked_fusion
    local_weight: float = 0.7
    web_weight: float = 0.3
    
    # 테스트 데이터
    data_sources: List[str] = field(default_factory=list)
    test_queries: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """초기화 후 처리"""
        if not self.name:
            self.name = f"experiment_{self.experiment_id}"
        
        # 임베딩 모델 기본값 설정
        if not self.query_embedding_model:
            self.query_embedding_model = self.embedding_model
            
        if not self.doc_embedding_model:
            self.doc_embedding_model = self.embedding_model
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return asdict(self)
    
    def save(self, path: str) -> None:
        """설정을 JSON 파일로 저장"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentConfig':
        """딕셔너리에서 설정 객체 생성"""
        return cls(**data)
    
    @classmethod
    def load(cls, path: str) -> 'ExperimentConfig':
        """JSON 파일에서 설정 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'ExperimentConfig':
        """YAML 파일에서 설정 로드"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


def generate_experiment_variations(base_config: ExperimentConfig, 
                                 param_name: str, 
                                 values: List[Any]) -> List[ExperimentConfig]:
    """
    기본 설정에서 하나의 파라미터를 다양하게 변경한 설정 목록 생성
    
    Args:
        base_config: 기본 실험 설정
        param_name: 변경할 파라미터 이름
        values: 테스트할 파라미터 값 목록
        
    Returns:
        변경된 설정 객체 목록
    """
    variations = []
    
    for value in values:
        # 기본 설정 복사
        config_dict = base_config.to_dict()
        
        # 파라미터 값 변경
        config_dict[param_name] = value
        
        # 새 ID와 이름 생성
        config_dict["experiment_id"] = str(uuid.uuid4())[:8]
        config_dict["name"] = f"{base_config.name}_{param_name}_{value}"
        
        # 설정 객체 생성
        config = ExperimentConfig.from_dict(config_dict)
        variations.append(config)
    
    return variations 