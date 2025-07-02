"""
토론 참가자 에이전트 구현

찬성 또는 반대 입장으로 토론에 참여하는 에이전트
"""

import logging
import time
import os
import yaml
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from ..base.agent import Agent
from .strategy.attack_strategy_manager import AttackStrategyManager
from .strategy.defense_strategy_manager import DefenseStrategyManager
from .strategy.followup_strategy_manager import FollowupStrategyManager
from .strategy.strategy_rag_manager import StrategyRAGManager
from .argument.argument_generator import ArgumentGenerator
from .argument.rag_argument_enhancer import RAGArgumentEnhancer
from .argument.argument_cache_manager import ArgumentCacheManager
from .analysis.opponent_analyzer import OpponentAnalyzer
from .analysis.vulnerability_scorer import VulnerabilityScorer
from .analysis.argument_extractor import ArgumentExtractor
from ..base.agent import Agent
from .search.rag_search_manager import RAGSearchManager
from .search.web_searcher import WebSearcher
from .argument import ArgumentGenerator, RAGArgumentEnhancer, ArgumentCacheManager
from .strategy import AttackStrategyManager, DefenseStrategyManager, FollowupStrategyManager, StrategyRAGManager

logger = logging.getLogger(__name__)

class DebateParticipantAgent(Agent):
    """
    토론 참가자 에이전트
    
    찬성 또는 반대 입장에서 주장을 펼치고 상대의 의견에 대응하는 역할 담당
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        토론 참가자 에이전트 초기화
        
        Args:
            agent_id: 에이전트 고유 ID
            name: 에이전트 이름 (철학자 이름)
            config: 설정 딕셔너리
        """
        super().__init__(agent_id, name, config)
        
        # 기본 설정
        self.llm_manager = None
        self.web_crawling = config.get("web_crawling", None)
        
        # 토론 역할 설정
        self.role = config.get("role", "neutral")  # "pro", "con", "neutral"
        
        # 철학자 정보 로드
        philosopher_key = name.lower()
        philosopher_data = self._load_philosopher_data(philosopher_key)
        
        # 철학자 속성 설정
        self.philosopher_key = philosopher_key
        self.philosopher_name = philosopher_data.get("name", name)
        self.philosopher_essence = philosopher_data.get("essence", "")
        self.philosopher_debate_style = philosopher_data.get("debate_style", "")
        self.philosopher_personality = philosopher_data.get("personality", "")
        self.philosopher_key_traits = philosopher_data.get("key_traits", [])
        self.philosopher_quote = philosopher_data.get("quote", "")
        
        # 전략 가중치 설정
        self.strategy_weights = philosopher_data.get("strategy_weights", {})
        self.defense_weights = philosopher_data.get("defense_weights", {})
        self.followup_weights = philosopher_data.get("followup_weights", {})
        self.rag_affinity = philosopher_data.get("rag_affinity", 0.5)
        self.vulnerability_sensitivity = philosopher_data.get("vulnerability_sensitivity", {})
        
        # 토론 상태 관리
        self.current_stance = None
        self.opponent_arguments = {}
        self.my_key_points = []
        self.opponent_key_points = []
        self.core_arguments = []
        self.strengthened_arguments = []
        self.prepared_argument = ""
        self.argument_prepared = False
        self.argument_cache_valid = False
        self.is_preparing_argument = False
        self.last_preparation_context = None
        self.interaction_history = []
        
        # RAG 검색 매니저 초기화
        self._initialize_rag_search_manager(config)
        
        # 모듈 초기화
        self._initialize_strategy_modules()
        self._initialize_argument_modules()
        self._initialize_analysis_modules()
        
        logger.info(f"DebateParticipantAgent initialized: {agent_id} ({self.philosopher_name})")
        
        # 성능 측정을 위한 타임스탬프 기록
        self.performance_timestamps = {}
    
    def _initialize_strategy_modules(self):
        """Strategy 관련 모듈들 초기화"""
        try:
            # 철학자 데이터 재구성 (이미 로드된 속성들 사용)
            philosopher_data = {
                "name": self.philosopher_name,
                "essence": self.philosopher_essence,
                "debate_style": self.philosopher_debate_style,
                "personality": self.philosopher_personality,
                "key_traits": self.philosopher_key_traits,
                "quote": self.philosopher_quote,
                "defense_weights": getattr(self, 'defense_weights', {}),
                "followup_weights": getattr(self, 'followup_weights', {}),
                "rag_affinity": getattr(self, 'rag_affinity', 0.5)
            }
            
            # 전략 스타일 로드
            strategy_styles = self._load_strategy_styles()
            
            # 전략별 RAG 가중치 로드
            strategy_rag_weights = self._load_strategy_rag_weights()
            
            # AttackStrategyManager 초기화
            self.attack_strategy_manager = AttackStrategyManager(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                strategy_styles=strategy_styles,
                strategy_weights=getattr(self, 'strategy_weights', {}),
                llm_manager=self.llm_manager
            )
            
            # DefenseStrategyManager 초기화
            self.defense_strategy_manager = DefenseStrategyManager(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                strategy_styles=strategy_styles,
                llm_manager=self.llm_manager
            )
            
            # FollowupStrategyManager 초기화
            self.followup_strategy_manager = FollowupStrategyManager(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                strategy_styles=strategy_styles,
                llm_manager=self.llm_manager
            )
            
            # StrategyRAGManager 초기화
            self.strategy_rag_manager = StrategyRAGManager(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                strategy_rag_weights=strategy_rag_weights,
                rag_search_manager=self.rag_search_manager
            )
            
            logger.info(f"[{self.agent_id}] Strategy modules initialized successfully")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to initialize strategy modules: {str(e)}")
            # 실패 시 None으로 설정
            self.attack_strategy_manager = None
            self.defense_strategy_manager = None
            self.followup_strategy_manager = None
            self.strategy_rag_manager = None
    
    def _initialize_argument_modules(self):
        """Argument 관련 모듈들 초기화"""
        try:
            # 철학자 데이터 재구성 (이미 로드된 속성들 사용)
            philosopher_data = {
                "name": self.philosopher_name,
                "essence": self.philosopher_essence,
                "debate_style": self.philosopher_debate_style,
                "personality": self.philosopher_personality,
                "key_traits": self.philosopher_key_traits,
                "quote": self.philosopher_quote
            }
            
            # ArgumentGenerator 초기화
            self.argument_generator = ArgumentGenerator(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                llm_manager=self.llm_manager
            )
            
            # RAGArgumentEnhancer 초기화
            self.rag_argument_enhancer = RAGArgumentEnhancer(
                agent_id=self.agent_id,
                philosopher_data=philosopher_data,
                rag_search_manager=self.rag_search_manager,
                llm_manager=self.llm_manager
            )
            
            # ArgumentCacheManager 초기화
            self.argument_cache_manager = ArgumentCacheManager(
                agent_id=self.agent_id
            )
            
            logger.info(f"[{self.agent_id}] Argument modules initialized successfully")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to initialize argument modules: {str(e)}")
            # 실패 시 None으로 설정
            self.argument_generator = None
            self.rag_argument_enhancer = None
            self.argument_cache_manager = None
    
    def _initialize_analysis_modules(self):
        """Analysis 관련 모듈들 초기화"""
        try:
            # 철학자 데이터 재구성 (이미 로드된 속성들 사용)
            philosopher_data = {
                "name": self.philosopher_name,
                "essence": self.philosopher_essence,
                "debate_style": self.philosopher_debate_style,
                "personality": self.philosopher_personality,
                "key_traits": self.philosopher_key_traits,
                "quote": self.philosopher_quote,
                "vulnerability_sensitivity": getattr(self, 'vulnerability_sensitivity', {})
            }
            
            # OpponentAnalyzer 초기화
            self.opponent_analyzer = OpponentAnalyzer(
                llm_manager=self.llm_manager,
                agent_id=self.agent_id,
                philosopher_name=self.philosopher_name,
                philosopher_data=philosopher_data
            )
            
            logger.info(f"[{self.agent_id}] Analysis modules initialized successfully")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to initialize analysis modules: {str(e)}")
            # 실패 시 None으로 설정
            self.opponent_analyzer = None
    
    def _initialize_rag_search_manager(self, config: Dict[str, Any]):
        """RAG 검색 매니저 초기화"""
        try:
            rag_config = {
                "max_total_results": config.get("max_rag_results", 10),
                "source_weights": {
                    "web": 0.4,
                    "vector": 0.3,
                    "philosopher": 0.2,
                    "dialogue": 0.1
                },
                "web_search": {
                    "web_crawling": self.web_crawling,
                    "search_provider": config.get("search_provider", "google"),
                    "max_results": 5,
                    "embedding_model": config.get("embedding_model", "all-MiniLM-L6-v2")
                },
                "vector_search": {
                    "db_path": config.get("vector_db_path", "./vectordb"),
                    "collection_name": config.get("vector_collection", "default"),
                    "search_algorithm": "simple_top_k",
                    "max_results": 5
                },
                "philosopher_search": {
                    "db_path": config.get("vector_db_path", "./vectordb"),
                    "philosopher_collection": config.get("philosopher_collection", "philosopher_works"),
                    "max_results": 3
                }
            }
            
            self.rag_search_manager = RAGSearchManager(rag_config)
            logger.info(f"[{self.agent_id}] RAG Search Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to initialize RAG Search Manager: {str(e)}")
            self.rag_search_manager = None
    
    def _load_philosopher_data(self, philosopher_key: str) -> Dict[str, Any]:
        """
        YAML 파일에서 철학자 데이터 로드
        
        Args:
            philosopher_key: 철학자 키 (예: "socrates", "plato")
            
        Returns:
            철학자 데이터 딕셔너리
        """
        try:
            # 프로젝트 루트에서 philosophers/debate_optimized.yaml 파일 경로 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # 프로젝트 루트 찾기 (src 폴더가 있는 상위 디렉토리)
            while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
                parent = os.path.dirname(project_root)
                if parent == project_root:  # 루트에 도달
                    break
                project_root = parent
            
            yaml_path = os.path.join(project_root, "philosophers", "debate_optimized.yaml")
            
            if not os.path.exists(yaml_path):
                logger.warning(f"Philosopher YAML file not found at {yaml_path}")
                return self._get_default_philosopher_data(philosopher_key)
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                philosophers_data = yaml.safe_load(f)
            
            if philosopher_key in philosophers_data:
                logger.info(f"Loaded philosopher data for: {philosopher_key}")
                return philosophers_data[philosopher_key]
            else:
                logger.warning(f"Philosopher '{philosopher_key}' not found in YAML file")
                return self._get_default_philosopher_data(philosopher_key)
                
        except Exception as e:
            logger.error(f"Error loading philosopher data: {str(e)}")
            return self._get_default_philosopher_data(philosopher_key)
    
    def _load_strategy_styles(self) -> Dict[str, Any]:
        """
        JSON 파일에서 전략 스타일 정보 로드
        
        Returns:
            전략 스타일 딕셔너리
        """
        try:
            # 프로젝트 루트에서 philosophers/debate_strategies.json 파일 경로 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # 프로젝트 루트 찾기 (src 폴더가 있는 상위 디렉토리)
            while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
                parent = os.path.dirname(project_root)
                if parent == project_root:  # 루트에 도달
                    break
                project_root = parent
            
            json_path = os.path.join(project_root, "philosophers", "debate_strategies.json")
            
            if not os.path.exists(json_path):
                logger.warning(f"Strategy JSON file not found at {json_path}")
                return self._get_default_strategy_styles()
            
            with open(json_path, 'r', encoding='utf-8') as f:
                strategies_data = json.load(f)
            
            logger.info(f"Loaded strategy styles from: {json_path}")
            return strategies_data.get("strategy_styles", {})
            
        except Exception as e:
            logger.error(f"Error loading strategy styles: {str(e)}")
            return self._get_default_strategy_styles()
    
    def _load_strategy_rag_weights(self) -> Dict[str, Any]:
        """
        YAML 파일에서 전략별 RAG 가중치 로드
        
        Returns:
            전략별 RAG 가중치 딕셔너리
        """
        try:
            # 프로젝트 루트에서 philosophers/strategy_rag_weights.yaml 파일 경로 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # 프로젝트 루트 찾기 (src 폴더가 있는 상위 디렉토리)
            while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
                parent = os.path.dirname(project_root)
                if parent == project_root:  # 루트에 도달
                    break
                project_root = parent
            
            yaml_path = os.path.join(project_root, "philosophers", "strategy_rag_weights.yaml")
            
            if not os.path.exists(yaml_path):
                logger.warning(f"Strategy RAG weights YAML file not found at {yaml_path}")
                return self._get_default_strategy_rag_weights()
            
            with open(yaml_path, 'r', encoding='utf-8') as f:
                rag_weights_data = yaml.safe_load(f)
            
            logger.info(f"Loaded strategy RAG weights from: {yaml_path}")
            return rag_weights_data.get("strategy_rag_weights", {})
            
        except Exception as e:
            logger.error(f"Error loading strategy RAG weights: {str(e)}")
            return self._get_default_strategy_rag_weights()
    
    def _get_default_strategy_rag_weights(self) -> Dict[str, Any]:
        """
        기본 전략별 RAG 가중치 반환 (파일 로드 실패 시)
        
        Returns:
            기본 전략별 RAG 가중치 딕셔너리
        """
        return {
            "Clipping": {
                "data_respect": 0.5,
                "conceptual_precision": 0.2,
                "systematic_logic": 0.2,
                "pragmatic_orientation": 0.4,
                "rhetorical_independence": -0.2
            },
            "Framing Shift": {
                "data_respect": 0.2,
                "conceptual_precision": 0.5,
                "systematic_logic": 0.3,
                "pragmatic_orientation": 0.1,
                "rhetorical_independence": -0.3
            },
            "Reductive Paradox": {
                "data_respect": 0.3,
                "conceptual_precision": 0.2,
                "systematic_logic": 0.5,
                "pragmatic_orientation": 0.1,
                "rhetorical_independence": -0.3
            },
            "Conceptual Undermining": {
                "data_respect": 0.1,
                "conceptual_precision": 0.6,
                "systematic_logic": 0.3,
                "pragmatic_orientation": 0.05,
                "rhetorical_independence": -0.2
            },
            "Ethical Reversal": {
                "data_respect": 0.1,
                "conceptual_precision": 0.2,
                "systematic_logic": 0.2,
                "pragmatic_orientation": 0.5,
                "rhetorical_independence": -0.1
            },
            "Temporal Delay": {
                "data_respect": 0.5,
                "conceptual_precision": 0.2,
                "systematic_logic": 0.2,
                "pragmatic_orientation": 0.2,
                "rhetorical_independence": -0.2
            },
            "Philosophical Reframing": {
                "data_respect": 0.05,
                "conceptual_precision": 0.4,
                "systematic_logic": 0.5,
                "pragmatic_orientation": 0.05,
                "rhetorical_independence": -0.3
            }
        }
    
    def _determine_rag_usage_for_strategy(self, strategy_type: str) -> Dict[str, Any]:
        """
        특정 전략에 대한 RAG 사용 여부 판별
        
        Args:
            strategy_type: 공격 전략 타입
            
        Returns:
            RAG 사용 결정 결과
        """
        print(f"   🧮 [{self.philosopher_name}] RAG 사용 판별:")
        print(f"      🎯 전략: {strategy_type}")
        
        try:
            # 1. 전략별 RAG 가중치 로드
            if not hasattr(self, 'strategy_rag_weights'):
                self.strategy_rag_weights = self._load_strategy_rag_weights()
            
            strategy_weights = self.strategy_rag_weights.get(strategy_type, {})
            if not strategy_weights:
                print(f"      ❌ 전략 '{strategy_type}'에 대한 RAG 가중치 없음 - RAG 사용 안함")
                return {
                    "use_rag": False,
                    "rag_score": 0.0,
                    "threshold": 0.5,
                    "reason": "no_strategy_weights",
                    "calculation_details": {}
                }
            
            # 2. 철학자 RAG 스탯 가져오기
            philosopher_key = getattr(self, 'philosopher_key', self.name.lower())
            philosopher_data = self._load_philosopher_data(philosopher_key)
            rag_stats = philosopher_data.get("rag_stats", {})
            
            if not rag_stats:
                print(f"      ❌ 철학자 '{philosopher_key}'에 대한 RAG 스탯 없음 - RAG 사용 안함")
                return {
                    "use_rag": False,
                    "rag_score": 0.0,
                    "threshold": 0.5,
                    "reason": "no_philosopher_rag_stats",
                    "calculation_details": {}
                }
            
            # 3. 벡터 내적 계산: rag_score = Σ(strategy_weight[i] × philosopher_rag_stat[i])
            print(f"      📊 전략 가중치: {strategy_weights}")
            print(f"      🎭 철학자 스탯: {rag_stats}")
            
            rag_score = 0.0
            calculation_details = {}
            
            print(f"      🔢 계산 과정:")
            for stat_name in ["data_respect", "conceptual_precision", "systematic_logic", "pragmatic_orientation", "rhetorical_independence"]:
                strategy_weight = strategy_weights.get(stat_name, 0.0)
                philosopher_stat = rag_stats.get(stat_name, 0.0)
                contribution = strategy_weight * philosopher_stat
                rag_score += contribution
                calculation_details[stat_name] = {
                    "strategy_weight": strategy_weight,
                    "philosopher_stat": philosopher_stat,
                    "contribution": contribution
                }
                print(f"         • {stat_name}: {strategy_weight:.3f} × {philosopher_stat:.3f} = {contribution:.3f}")
            
            print(f"      📈 합계:")
            print(f"         • RAG 점수: {rag_score:.3f}")
            
            # 4. 임계값 비교 (0.5로 설정)
            threshold = 0.5
            use_rag = rag_score >= threshold
            
            print(f"         • 임계값: {threshold}")
            print(f"         • 결정: {'RAG 사용' if use_rag else 'RAG 사용 안함'} ({rag_score:.3f} {'≥' if use_rag else '<'} {threshold})")
            print()
            
            return {
                "use_rag": use_rag,
                "rag_score": rag_score,
                "threshold": threshold,
                "reason": "calculated" if use_rag else "below_threshold",
                "calculation_details": calculation_details
            }
            
        except Exception as e:
            logger.error(f"Error determining RAG usage for strategy '{strategy_type}': {str(e)}")
            print(f"      ❌ RAG 판별 오류: {str(e)} - RAG 사용 안함")
            return {
                "use_rag": False,
                "rag_score": 0.0,
                "threshold": 0.5,
                "reason": "error",
                "error": str(e),
                "calculation_details": {}
            }
    
    def _get_default_philosopher_data(self, philosopher_key: str) -> Dict[str, Any]:
        """
        기본 철학자 데이터 반환 (파일 로드 실패 시)
        
        Args:
            philosopher_key: 철학자 키
            
        Returns:
            기본 철학자 데이터
        """
        return {
            "name": philosopher_key.capitalize(),
            "essence": "A thoughtful philosopher who engages in meaningful debate",
            "debate_style": "Presents logical arguments with clear reasoning",
            "personality": "Analytical and respectful in discourse",
            "key_traits": ["logical reasoning", "clear communication"],
            "quote": "The pursuit of truth through dialogue",
            "strategy_weights": {
                "Clipping": 0.2,
                "Framing Shift": 0.2,
                "Reductive Paradox": 0.15,
                "Conceptual Undermining": 0.15,
                "Ethical Reversal": 0.15,
                "Temporal Delay": 0.1,
                "Philosophical Reframing": 0.05
            }
        }
    
    def _get_default_strategy_styles(self) -> Dict[str, Any]:
        """
        기본 전략 스타일 반환 (파일 로드 실패 시)
        
        Returns:
            기본 전략 스타일 딕셔너리
        """
        return {
            "Clipping": {
                "description": "Refute a specific claim directly",
                "style_prompt": "'X' is wrong because...",
                "example": "Direct refutation with evidence"
            },
            "Framing Shift": {
                "description": "Challenge assumptions and reframe the discussion",
                "style_prompt": "You're assuming Y, but what if we asked Z instead?",
                "example": "Shift perspective to deeper questions"
            },
            "Reductive Paradox": {
                "description": "Extend logic to expose flaws",
                "style_prompt": "If we follow your logic to the end, then...",
                "example": "Show extreme consequences"
            },
            "Conceptual Undermining": {
                "description": "Question key definitions and concepts",
                "style_prompt": "What do we even mean by 'X' here?",
                "example": "Challenge conceptual clarity"
            },
            "Ethical Reversal": {
                "description": "Turn positive claims into ethical concerns",
                "style_prompt": "You call it progress, but isn't it dehumanization?",
                "example": "Reveal ethical implications"
            },
            "Temporal Delay": {
                "description": "Raise long-term consequence concerns",
                "style_prompt": "Even if it works now, what happens in 20 years?",
                "example": "Focus on future implications"
            },
            "Philosophical Reframing": {
                "description": "Replace with more fundamental questions",
                "style_prompt": "Maybe the real question is not what X is, but what it means to us.",
                "example": "Shift to existential questions"
            }
        }
    
    @classmethod
    def create_from_philosopher_key(cls, agent_id: str, philosopher_key: str, role: str, config: Dict[str, Any] = None) -> 'DebateParticipantAgent':
        """
        철학자 키를 사용하여 에이전트 생성
        
        Args:
            agent_id: 에이전트 ID
            philosopher_key: 철학자 키 (예: "socrates", "plato")
            role: 토론 역할 ("pro", "con")
            config: 추가 설정
            
        Returns:
            생성된 DebateParticipantAgent 인스턴스
        """
        if config is None:
            config = {}
        
        # 철학자 키와 역할 설정
        config["philosopher_key"] = philosopher_key
        config["role"] = role
        
        # 에이전트 생성
        agent = cls(agent_id, philosopher_key, config)
        
        logger.info(f"Created philosopher agent: {agent.philosopher_name} ({philosopher_key}) as {role}")
        return agent
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        에이전트로 요청 처리
        
        Args:
            input_data: 처리할 입력 데이터
            
        Returns:
            처리 결과
        """
        # RAG 정보 초기화 (모든 액션 시작 전)
        self.rag_info = {
            "rag_used": False,
            "rag_source_count": 0,
            "rag_sources": []
        }
        
        action = input_data.get("action", "")
        
        # 성능 측정 시작
        start_time = time.time()
        action_key = f"{self.agent_id}_{action}"
        
        # 로그 메시지 개선 - analyze_opponent_arguments의 경우 대상 발언자 표시
        if action == "analyze_opponent_arguments":
            target_speaker = input_data.get("speaker_id", "unknown")
            print(f"🕐 [{self.philosopher_name}] → {target_speaker} 논지 분석 시작: {time.strftime('%H:%M:%S', time.localtime(start_time))}")
        else:
            print(f"🕐 [{self.philosopher_name}] {action} 시작: {time.strftime('%H:%M:%S', time.localtime(start_time))}")
        
        try:
            result = None
            
            if action == "prepare_argument":
                result = self._prepare_argument(input_data)
            elif action == "generate_response":
                result = self._generate_response(input_data)
            elif action == "analyze_opponent_arguments":
                result = self.analyze_and_score_arguments(
                    input_data.get("opponent_response", ""),
                    input_data.get("speaker_id", "unknown")
                )
            elif action == "prepare_attack_strategies":
                strategies = self.prepare_attack_strategies_for_speaker(
                    input_data.get("target_speaker_id", "unknown")
                )
                # 딕셔너리 형태로 감싸서 반환
                result = {
                    "status": "success",
                    "strategies": strategies,
                    "strategies_count": len(strategies),
                    "rag_usage_count": sum(1 for s in strategies if s.get("rag_decision", {}).get("use_rag", False))
                }
            elif action == "get_best_attack_strategy":
                result = self.get_best_attack_strategy(
                    input_data.get("target_speaker_id", "unknown"),
                    input_data.get("context", {})
                )
            else:
                result = {"status": "error", "message": f"Unknown action: {action}"}
            
            # 결과에 RAG 정보 포함
            if result and isinstance(result, dict) and result.get("status") == "success":
                result.update(self.rag_info)
            
            # 성능 측정 종료
            end_time = time.time()
            duration = end_time - start_time
            self.performance_timestamps[action_key] = {
                "start": start_time,
                "end": end_time,
                "duration": duration
            }
            
            # 완료 로그 메시지도 개선
            if action == "analyze_opponent_arguments":
                target_speaker = input_data.get("speaker_id", "unknown")
                print(f"✅ [{self.philosopher_name}] → {target_speaker} 논지 분석 완료: {time.strftime('%H:%M:%S', time.localtime(end_time))} (소요시간: {duration:.2f}초)")
            else:
                print(f"✅ [{self.philosopher_name}] {action} 완료: {time.strftime('%H:%M:%S', time.localtime(end_time))} (소요시간: {duration:.2f}초)")
            
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            # 실패 로그 메시지도 개선
            if action == "analyze_opponent_arguments":
                target_speaker = input_data.get("speaker_id", "unknown")
                print(f"❌ [{self.philosopher_name}] → {target_speaker} 논지 분석 실패: {time.strftime('%H:%M:%S', time.localtime(end_time))} (소요시간: {duration:.2f}초) - {str(e)}")
            else:
                print(f"❌ [{self.philosopher_name}] {action} 실패: {time.strftime('%H:%M:%S', time.localtime(end_time))} (소요시간: {duration:.2f}초) - {str(e)}")
            
            logger.error(f"Error in {action}: {str(e)}")
            return {"status": "error", "message": f"처리 중 오류가 발생했습니다: {str(e)}"}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 측정 결과 요약 반환"""
        summary = {
            "agent_id": self.agent_id,
            "philosopher_name": self.philosopher_name,
            "total_actions": len(self.performance_timestamps),
            "actions": {}
        }
        
        total_time = 0
        for action_key, timing in self.performance_timestamps.items():
            action_name = action_key.replace(f"{self.agent_id}_", "")
            summary["actions"][action_name] = {
                "duration": timing["duration"],
                "start_time": time.strftime('%H:%M:%S', time.localtime(timing["start"])),
                "end_time": time.strftime('%H:%M:%S', time.localtime(timing["end"]))
            }
            total_time += timing["duration"]
        
        summary["total_time"] = total_time
        return summary
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        에이전트 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        for key, value in state_update.items():
            self.state[key] = value
            
        # 필요한 경우 LLM 관리자 업데이트
        if "llm_manager" in state_update:
            self.llm_manager = state_update.get("llm_manager")
    
    def set_llm_manager(self, llm_manager: Any) -> None:
        """
        LLM 관리자 설정 및 모듈 재초기화
        
        Args:
            llm_manager: LLM 관리자 인스턴스
        """
        self.llm_manager = llm_manager
        
        # LLM 매니저가 설정되면 모든 모듈 재초기화
        if llm_manager is not None:
            logger.info(f"[{self.agent_id}] LLM Manager set, reinitializing all modules...")
            
            # 각 모듈들을 올바른 LLM 매니저로 재초기화
            self._initialize_strategy_modules()
            self._initialize_argument_modules()
            self._initialize_analysis_modules()
            
            logger.info(f"[{self.agent_id}] All modules reinitialized with LLM Manager")
    
    def _generate_response(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        응답 생성 처리
        
        Args:
            input_data: 응답 생성에 필요한 데이터
            
        Returns:
            생성된 응답
        """
        context = input_data.get("context", {})
        dialogue_state = input_data.get("dialogue_state", {})
        stance_statements = input_data.get("stance_statements", {})
        
        # dialogue_state를 인스턴스 변수에 저장하여 다른 메서드에서 접근 가능하도록 함
        self._current_dialogue_state = dialogue_state
        
        response = self._generate_response_internal(context, dialogue_state, stance_statements)
        return {"status": "success", "message": response}
    
    def _generate_response_internal(self, context: Dict[str, Any], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str]) -> str:
        """
        토론 응답 생성
        
        Args:
            context: 응답 생성 컨텍스트
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            
        Returns:
            생성된 응답 텍스트
        """
        # 🎯 dialogue_state를 저장하여 다른 메서드들에서 접근 가능하도록 함
        self._current_dialogue_state = dialogue_state
        
        current_stage = context.get("current_stage", "")
        topic = context.get("topic", "")
        recent_messages = context.get("recent_messages", [])
        emotion_enhancement = context.get("emotion_enhancement", {})
        
        # 상호논증 단계에서는 짧고 직접적인 공격/질문 형태로 생성
        if current_stage == "interactive_argument":
            return self._generate_interactive_argument_response(
                topic, recent_messages, dialogue_state, stance_statements, emotion_enhancement
            )
        
        # 기존 로직 유지 (입론, 결론 등)
        # ... existing code ...
    
    def _generate_interactive_argument_response(self, topic: str, recent_messages: List[Dict[str, Any]], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str], emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        상호논증 단계에서 응답 생성 - 대화 관리자의 단계 관리에 의존
        
        Args:
            topic: 토론 주제
            recent_messages: 최근 메시지 목록
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            emotion_enhancement: 감정 강화 데이터 (선택적)
            
        Returns:
            생성된 응답 텍스트
        """
        # 대화 관리자가 이미 상황을 판단했으므로 단순히 응답 생성
        # 최근 상황에 따라 공격/방어/팔로우업 결정
        
        # 최근 메시지 분석으로 현재 상황 간단 판단
        situation = self._simple_situation_analysis(recent_messages)
        
        if situation == "defending":
            return self._generate_defense_response(topic, recent_messages, dialogue_state, stance_statements, emotion_enhancement)
        elif situation == "following_up":
            return self._generate_followup_response(topic, recent_messages, dialogue_state, stance_statements, emotion_enhancement)
        else:  # attacking (기본값)
            return self._generate_attack_response(topic, recent_messages, dialogue_state, stance_statements, emotion_enhancement)
    
    def _simple_situation_analysis(self, recent_messages: List[Dict[str, Any]]) -> str:
        """
        간단한 상황 분석 - 대화 관리자의 단계 관리를 보완
        
        Args:
            recent_messages: 최근 메시지 목록
            
        Returns:
            상황 ("attacking", "defending", "following_up")
        """
        if len(recent_messages) < 1:
            return "attacking"
        
        # 마지막 메시지 분석
        last_message = recent_messages[-1]
        last_speaker = last_message.get('speaker_id', '')
        my_agent_id = getattr(self, 'agent_id', self.name.lower())
        
        # 상대방이 마지막에 발언했고, 그 전에 내가 발언했으면 팔로우업
        if len(recent_messages) >= 2:
            second_last_message = recent_messages[-2]
            second_last_speaker = second_last_message.get('speaker_id', '')
            
            # 상대방이 마지막 발언, 내가 그 전 발언 → 팔로우업
            if (last_speaker != my_agent_id and 
                second_last_speaker == my_agent_id):
                return "following_up"
        
        # 상대방이 마지막에 발언했으면 방어
        if last_speaker != my_agent_id and last_speaker != "moderator":
            return "defending"
        
        # 기본적으로 공격
        return "attacking"
    
    def _is_defending_against_attack(self, recent_messages: List[Dict[str, Any]]) -> bool:
        """
        최근 메시지에서 상대방이 나를 공격했는지 확인
        
        Args:
            recent_messages: 최근 메시지 목록
            
        Returns:
            방어 상황 여부
        """
        if not recent_messages:
            return False
        
        # 가장 최근 메시지가 상대방의 공격인지 확인
        last_message = recent_messages[-1]
        last_speaker = last_message.get('speaker_id', '')
        last_role = last_message.get('role', '')
        
        # 내가 아닌 다른 참가자의 발언이고, 모더레이터가 아니면 공격으로 간주
        opposite_role = "con" if self.role == "pro" else "pro"
        
        return (last_role == opposite_role and 
                last_speaker != "moderator" and 
                last_speaker != self.agent_id)
    
    def _generate_defense_response(self, topic: str, recent_messages: List[Dict[str, Any]], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str], emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        방어 응답 생성
        
        Args:
            topic: 토론 주제
            recent_messages: 최근 메시지 목록
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            emotion_enhancement: 감정 강화 데이터 (선택적)
            
        Returns:
            생성된 방어 응답
        """
        print(f"🛡️ [{self.philosopher_name}] 방어 응답 생성 시작")
        
        # 1. 상대방 공격 분석
        attack_info = self._analyze_incoming_attack(recent_messages)
        
        # 2. 방어 전략 선택 - 모듈 사용
        defense_strategy = self.defense_strategy_manager.select_defense_strategy(attack_info, emotion_enhancement)
        
        # 3. 방어용 RAG 사용 여부 결정
        defense_rag_decision = self._determine_defense_rag_usage(defense_strategy, attack_info)
        
        # 4. 방어 응답 생성 - 모듈 사용
        defense_response = self.defense_strategy_manager.generate_defense_response(
            topic, recent_messages, stance_statements, defense_strategy, 
            attack_info, emotion_enhancement
        )
        
        print(f"🛡️ [{self.philosopher_name}] 방어 응답 생성 완료 - 전략: {defense_strategy}")
        return defense_response
    
    def _generate_attack_response(self, topic: str, recent_messages: List[Dict[str, Any]], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str], emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        공격 응답 생성 (기존 로직)
        """
        # 상대방 에이전트 정보 찾기 (개선된 로직)
        opposite_role = "con" if self.role == "pro" else "pro"
        target_agent_name = None
        target_agent_id = None
        
        # 1. 최근 메시지에서 상대방 에이전트 찾기 (모더레이터 제외)
        for msg in reversed(recent_messages):
            msg_role = msg.get('role', '')
            msg_speaker_id = msg.get('speaker_id', '')
            
            # 오직 상대편 역할의 참가자만 찾기 (모더레이터 제외)
            if msg_role == opposite_role and msg_speaker_id and msg_speaker_id != "moderator":
                target_agent_id = msg_speaker_id
                break
        
        # 2. target_agent_id가 없으면 dialogue_state에서 찾기
        if not target_agent_id:
            # dialogue_state의 구조 확인을 위한 디버깅
            print(f"   🔍 디버깅: dialogue_state 키들: {list(dialogue_state.keys())}")
            
            # 여러 가능한 경로에서 참가자 정보 찾기
            participants = None
            
            # 경로 1: dialogue_state['participants']
            if 'participants' in dialogue_state:
                participants = dialogue_state['participants']
                print(f"   🔍 디버깅: participants 구조: {participants}")
            
            # 경로 2: dialogue_state에서 직접 pro/con 찾기
            elif opposite_role in dialogue_state:
                participants = {opposite_role: dialogue_state[opposite_role]}
                print(f"   🔍 디버깅: 직접 찾은 {opposite_role}: {participants}")
            
            if participants:
                opposite_participants = participants.get(opposite_role, [])
                print(f"   🔍 디버깅: {opposite_role} 참가자들: {opposite_participants}")
                
                if opposite_participants:
                    # 첫 번째 상대방 선택
                    if isinstance(opposite_participants, list) and len(opposite_participants) > 0:
                        target_agent_id = opposite_participants[0]
                    elif isinstance(opposite_participants, str):
                        target_agent_id = opposite_participants
                    
                    print(f"   🔍 디버깅: 선택된 target_agent_id: {target_agent_id}")
        
        # 3. 여전히 없으면 실제 참가자에서 상대방 찾기
        if not target_agent_id:
            # 실제 참가자 목록에서 상대방 찾기
            try:
                # dialogue_state에서 모든 참가자 정보 가져오기
                all_participants = []
                
                # speaking_history에서 실제 참가자들 추출
                speaking_history = dialogue_state.get('speaking_history', [])
                if speaking_history:
                    for msg in speaking_history:
                        speaker_id = msg.get('speaker_id', '')
                        role = msg.get('role', '')
                        if speaker_id and role in ['pro', 'con'] and speaker_id != self.agent_id:
                            if role == opposite_role and speaker_id not in all_participants:
                                all_participants.append(speaker_id)
                
                # 상대방 역할의 첫 번째 참가자 선택
                if all_participants:
                    target_agent_id = all_participants[0]
                    print(f"   🔍 디버깅: speaking_history에서 찾은 상대방: {target_agent_id}")
                else:
                    # fallback: 기본 상대방 설정
                    if self.role == "pro":
                        target_agent_id = "con_participant"  # 찬성측의 상대방
                    elif self.role == "con":
                        target_agent_id = "pro_participant"  # 반대측의 상대방
                    else:
                        target_agent_id = "opponent"
                    
                    print(f"   🔍 디버깅: 기본값으로 설정된 target_agent_id: {target_agent_id}")
                    
            except Exception as e:
                print(f"   ❌ 상대방 찾기 오류: {str(e)}")
                target_agent_id = "opponent"
        
        # 4. 철학자 이름 찾기 (개선된 로직)
        target_agent_name = self._get_philosopher_name(target_agent_id)
        
        # 최근 메시지 텍스트 형식화
        recent_messages_text = "\n".join([
            f"{msg.get('role', 'Unknown')} ({msg.get('speaker_id', '')}): {msg.get('text', '')}" 
            for msg in recent_messages[-3:]  # 최근 3개만
        ])
        
        # 내 입장과 반대 입장 확인
        my_stance = stance_statements.get(self.role) if self.role in ["pro", "con"] else ""
        opposite_stance = stance_statements.get(opposite_role, "")
        
        # 공격 전략 가져오기 (준비된 것이 있으면)
        attack_strategy = None
        target_argument_info = None
        
        if target_agent_id and hasattr(self, 'attack_strategies') and target_agent_id in self.attack_strategies:
            strategies = self.attack_strategies[target_agent_id]
            if strategies:
                attack_strategy = strategies[0]  # 첫 번째 전략 사용
                target_argument_info = attack_strategy.get('target_argument', {})
                
                # 🎯 상호논증 전략 정보 출력
                strategy_type = attack_strategy.get('strategy_type', 'Unknown')
                target_claim = target_argument_info.get('claim', 'Unknown claim')[:100] + "..." if len(target_argument_info.get('claim', '')) > 100 else target_argument_info.get('claim', 'Unknown claim')
                vulnerability_score = attack_strategy.get('vulnerability_score', 0.0)
                
                print(f"🎯 [{self.philosopher_name}] 상호논증 전략:")
                print(f"   📍 공격 대상: {target_agent_name}")
                print(f"   🗡️  사용 전략: {strategy_type}")
                print(f"   🎯 대상 논지: {target_claim}")
                print(f"   ⚡ 취약성 점수: {vulnerability_score:.2f}")
                
                # 전략 세부 정보도 출력
                attack_plan = attack_strategy.get('attack_plan', {})
                if attack_plan:
                    target_point = attack_plan.get('target_point', '')
                    key_phrase = attack_plan.get('key_phrase', '')
                    if target_point:
                        print(f"   🔍 공격 포인트: {target_point[:80]}...")
                    if key_phrase:
                        print(f"   💬 핵심 공격구: {key_phrase[:60]}...")
        else:
            print(f"🎯 [{self.philosopher_name}] 상호논증 전략:")
            print(f"   📍 공격 대상: {target_agent_name}")
            print(f"   🗡️  사용 전략: 일반적 반박 (준비된 전략 없음)")
            print(f"   🎯 대상 논지: 최근 발언 전체")
            print(f"   💡 상대방 ID: {target_agent_id} (디버깅용)")
        
        # 시스템 프롬프트 구성 - 상호논증에 특화
        system_prompt = f"""
You are {self.philosopher_name}, a philosopher with this essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}

This is the INTERACTIVE ARGUMENT phase of the debate. Your responses should be:
1. SHORT and DIRECT (2-3 sentences maximum)
2. AGGRESSIVE and CHALLENGING
3. Focus on ATTACKING specific points made by your opponent
4. Ask POINTED QUESTIONS that expose weaknesses
5. Use your philosophical approach to challenge their logic

CRITICAL: Write your ENTIRE response in the SAME LANGUAGE as the debate topic. 
If the topic is in Korean, respond in Korean. If in English, respond in English.

You are directly confronting {target_agent_name}. Address them by name and attack their specific arguments.
"""

        # 유저 프롬프트 구성
        user_prompt = f"""
DEBATE TOPIC: "{topic}"

YOUR POSITION: {my_stance}
OPPONENT'S POSITION: {opposite_stance}

TARGET OPPONENT: {target_agent_name}

RECENT EXCHANGE:
{recent_messages_text}

TASK: Generate a SHORT, DIRECT response (2-3 sentences max) that:
1. Directly addresses {target_agent_name} by name
2. Attacks a specific point they made
3. Asks a challenging question OR points out a logical flaw
4. Uses your philosophical style to challenge them

IMPORTANT: Write your response in the SAME LANGUAGE as the debate topic "{topic}".
If the topic contains Korean text, write in Korean. If in English, write in English.

"""

        # 공격 전략이 있으면 추가
        if attack_strategy:
            strategy_type = attack_strategy.get('strategy_type', '')
            strategy_description = attack_strategy.get('attack_plan', {}).get('strategy_application', '')
            key_phrases = [attack_strategy.get('attack_plan', {}).get('key_phrase', '')]
            
            user_prompt += f"""
ATTACK STRATEGY: Use the "{strategy_type}" approach
Strategy Description: {strategy_description}
Key Phrases to Consider: {', '.join(key_phrases[:3])}
"""
            
            # RAG 결과가 있으면 추가
            rag_decision = attack_strategy.get('rag_decision', {})
            if rag_decision.get('use_rag') and rag_decision.get('results'):
                rag_formatted = self._format_attack_rag_results(rag_decision['results'], strategy_type)
                if rag_formatted:
                    user_prompt += f"""
{rag_formatted}
INSTRUCTION: Incorporate this evidence naturally into your {strategy_type} attack.
"""
                    print(f"   📚 [{self.philosopher_name}] RAG 정보 프롬프트에 포함됨")
                else:
                    print(f"   📚 [{self.philosopher_name}] RAG 결과 포맷팅 실패")
            else:
                print(f"   📚 [{self.philosopher_name}] RAG 사용 안함 또는 결과 없음")

        user_prompt += f"""
Remember: Be CONCISE, DIRECT, and CONFRONTATIONAL. This is rapid-fire debate, not a long speech.
Address {target_agent_name} directly and challenge their specific arguments.
Write in the SAME LANGUAGE as the topic "{topic}".

Your response:"""

        # 감정 강화 적용 (선택적)
        if emotion_enhancement:
            from ...agents.utility.debate_emotion_inference import apply_debate_emotion_to_prompt
            system_prompt, user_prompt = apply_debate_emotion_to_prompt(system_prompt, user_prompt, emotion_enhancement)
        
        try:
            # LLM 호출 - 짧은 응답을 위해 max_tokens 제한
            response = self.llm_manager.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=10000  
            )
            
            if response:
                return response.strip()
            else:
                return f"{target_agent_name}님, 그 논리에는 명백한 허점이 있습니다. 어떻게 설명하시겠습니까?"
                
        except Exception as e:
            logger.error(f"Error generating interactive argument response: {str(e)}")
            return f"{target_agent_name}님, 그 주장에 대해 더 구체적인 근거를 제시해 주시기 바랍니다."
    
    def _analyze_incoming_attack(self, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        들어오는 공격 분석 - 공격자 에이전트의 실제 전략 정보 가져오기
        
        Args:
            recent_messages: 최근 메시지 목록
            
        Returns:
            공격 정보 분석 결과
        """
        if not recent_messages:
            return {"attack_strategy": "Unknown", "rag_used": False, "attacker_id": "unknown"}
        
        last_message = recent_messages[-1]
        attacker_id = last_message.get('speaker_id', 'unknown')
        attack_text = last_message.get('text', '')
        
        print(f"   🔍 [{self.philosopher_name}] 공격 정보 분석:")
        print(f"      👤 공격자: {attacker_id}")
        
        # 공격자 에이전트의 실제 전략 정보 가져오기
        attack_info = self._get_attacker_strategy_info(attacker_id)
        
        if attack_info["attack_strategy"] != "Unknown":
            print(f"      ✅ 실제 공격 전략 발견: {attack_info['attack_strategy']}")
            print(f"      📚 공격 RAG 사용: {attack_info['rag_used']}")
        else:
            print(f"      ❌ 공격 전략 정보 없음 - 키워드 추정 사용")
            # Fallback: 키워드 기반 추정 (기존 로직)
            attack_info = self._estimate_attack_strategy_from_keywords(attack_text, attacker_id)
        
        attack_info["attacker_id"] = attacker_id
        attack_info["attack_text"] = attack_text[:200]  # 분석용 일부 텍스트
        
        return attack_info
    
    def _get_attacker_strategy_info(self, attacker_id: str) -> Dict[str, Any]:
        """
        공격자 에이전트의 실제 사용한 전략 정보 가져오기
        
        Args:
            attacker_id: 공격자 에이전트 ID
            
        Returns:
            공격 전략 정보
        """
        try:
            # 1. 토론 매니저나 글로벌 상태에서 공격자 에이전트 참조 가져오기
            attacker_agent = self._get_attacker_agent_reference(attacker_id)
            
            if attacker_agent is None:
                print(f"         ❌ 공격자 에이전트 참조 없음")
                return {"attack_strategy": "Unknown", "rag_used": False}
            
            # 2. 공격자의 최근 사용한 전략 정보 가져오기
            recent_attack_strategy = self._get_recent_attack_strategy(attacker_agent, attacker_id)
            
            if recent_attack_strategy:
                strategy_type = recent_attack_strategy.get('strategy_type', 'Unknown')
                rag_decision = recent_attack_strategy.get('rag_decision', {})
                rag_used = rag_decision.get('use_rag', False)
                
                print(f"         ✅ 공격자 전략 정보:")
                print(f"            🗡️ 전략: {strategy_type}")
                print(f"            📚 RAG: {rag_used}")
                print(f"            ⚡ 취약성 점수: {recent_attack_strategy.get('vulnerability_score', 0.0):.2f}")
                
                return {
                    "attack_strategy": strategy_type,
                    "rag_used": rag_used,
                    "vulnerability_score": recent_attack_strategy.get('vulnerability_score', 0.0),
                    "attack_plan": recent_attack_strategy.get('attack_plan', {}),
                    "source": "actual_attacker_data"
                }
            else:
                print(f"         ❌ 공격자의 최근 전략 정보 없음")
                return {"attack_strategy": "Unknown", "rag_used": False}
                
        except Exception as e:
            logger.error(f"Error getting attacker strategy info: {str(e)}")
            print(f"         ❌ 공격자 전략 정보 조회 오류: {str(e)}")
            return {"attack_strategy": "Unknown", "rag_used": False}
    
    def _get_attacker_agent_reference(self, attacker_id: str):
        """
        공격자 에이전트 참조 가져오기
        
        Args:
            attacker_id: 공격자 ID
            
        Returns:
            공격자 에이전트 객체 또는 None
        """
        try:
            # 방법 1: dialogue_state에서 agents 정보 가져오기 (최우선)
            if hasattr(self, '_current_dialogue_state') and self._current_dialogue_state:
                agents = self._current_dialogue_state.get('agents', {})
                if attacker_id in agents:
                    return agents[attacker_id]
            
            # 방법 2: 토론 대화 매니저에서 참가자 정보 가져오기 (가장 일반적)
            if hasattr(self, '_debate_dialogue_manager'):
                participants = getattr(self._debate_dialogue_manager, 'participants', {})
                if attacker_id in participants:
                    return participants[attacker_id]
            
            # 방법 3: 글로벌 에이전트 레지스트리에서 가져오기 (만약 있다면)
            if hasattr(self, '_agent_registry'):
                registry = getattr(self._agent_registry, 'agents', {})
                if attacker_id in registry:
                    return registry[attacker_id]
            
            # 방법 4: 부모 객체나 컨텍스트에서 가져오기
            if hasattr(self, '_context') and self._context:
                context_participants = self._context.get('participants', {})
                if attacker_id in context_participants:
                    return context_participants[attacker_id]
            
            # 방법 5: 클래스 레벨 레지스트리 (만약 구현되어 있다면)
            if hasattr(self.__class__, '_agent_instances'):
                instances = getattr(self.__class__, '_agent_instances', {})
                if attacker_id in instances:
                    return instances[attacker_id]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting attacker agent reference: {str(e)}")
            return None
    
    def _get_recent_attack_strategy(self, attacker_agent, target_speaker_id: str) -> Dict[str, Any]:
        """
        공격자 에이전트의 최근 사용한 공격 전략 가져오기
        
        Args:
            attacker_agent: 공격자 에이전트 객체
            target_speaker_id: 공격 대상 (나 자신)
            
        Returns:
            최근 공격 전략 정보
        """
        try:
            # 공격자의 attack_strategies에서 나에 대한 전략 가져오기
            if hasattr(attacker_agent, 'attack_strategies'):
                attack_strategies = getattr(attacker_agent, 'attack_strategies', {})
                
                # 나(target_speaker_id)에 대한 공격 전략들
                my_id = getattr(self, 'agent_id', self.name.lower())
                if my_id in attack_strategies:
                    strategies = attack_strategies[my_id]
                    if strategies and len(strategies) > 0:
                        # 가장 최근 사용한 전략 (첫 번째 또는 가장 높은 우선순위)
                        return strategies[0]
            
            # 최근 사용한 전략 기록이 있는지 확인 (만약 별도로 저장한다면)
            if hasattr(attacker_agent, 'last_used_strategy'):
                last_strategy = getattr(attacker_agent, 'last_used_strategy', None)
                if last_strategy:
                    return last_strategy
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting recent attack strategy: {str(e)}")
            return None
    
    def _estimate_attack_strategy_from_keywords(self, attack_text: str, attacker_id: str) -> Dict[str, Any]:
        """
        키워드 기반 공격 전략 추정 (Fallback 방법)
        
        Args:
            attack_text: 공격 텍스트
            attacker_id: 공격자 ID
            
        Returns:
            추정된 공격 정보
        """
        attack_text_lower = attack_text.lower()
        
        print(f"         🔄 키워드 기반 전략 추정 시작")
        
        # 공격 전략 추정 (키워드 기반)
        attack_strategy = "Unknown"
        if any(word in attack_text_lower for word in ['wrong', 'incorrect', 'false', 'error']):
            attack_strategy = "Clipping"
        elif any(word in attack_text_lower for word in ['assume', 'framework', 'perspective']):
            attack_strategy = "FramingShift"
        elif any(word in attack_text_lower for word in ['extreme', 'consequence', 'lead to']):
            attack_strategy = "ReductiveParadox"
        elif any(word in attack_text_lower for word in ['define', 'mean', 'concept']):
            attack_strategy = "ConceptualUndermining"
        elif any(word in attack_text_lower for word in ['ethical', 'moral', 'wrong']):
            attack_strategy = "EthicalReversal"
        elif any(word in attack_text_lower for word in ['future', 'long-term', 'eventually']):
            attack_strategy = "TemporalDelay"
        elif any(word in attack_text_lower for word in ['fundamental', 'real question', 'deeper']):
            attack_strategy = "PhilosophicalReframing"
        
        # RAG 사용 여부 추정 (구체적 데이터/인용 있으면 RAG 사용으로 추정)
        rag_used = any(indicator in attack_text_lower for indicator in [
            'study', 'research', 'data', 'statistics', 'according to', 'evidence', 'findings'
        ])
        
        print(f"         📊 추정 결과: {attack_strategy} (RAG: {rag_used})")
        
        return {
            "attack_strategy": attack_strategy,
            "rag_used": rag_used,
            "source": "keyword_estimation"
        }
    
    def _select_defense_strategy(self, attack_info: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> str:
        """방어 전략 선택 - 모듈로 위임"""
        return self.defense_strategy_manager.select_defense_strategy(attack_info, emotion_enhancement)
    
    def _get_defense_candidates_from_map(self, attack_info: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> List[str]:
        """방어 후보 전략 목록 - 모듈로 위임"""
        return self.defense_strategy_manager._get_defense_candidates_from_map(attack_info, emotion_enhancement)
    
    def _determine_defense_rag_usage(self, defense_strategy: str, attack_info: Dict[str, Any]) -> Dict[str, Any]:
        """방어 RAG 사용 결정 - 모듈로 위임"""
        return self.strategy_rag_manager.determine_defense_rag_usage(defense_strategy, attack_info)
    
    def _get_defense_strategy_rag_weight(self, defense_strategy: str) -> float:
        """방어 전략 RAG 가중치 - 모듈로 위임"""
        return self.strategy_rag_manager._get_defense_strategy_rag_weight(defense_strategy)
    
    def _generate_defense_response_with_strategy(self, topic: str, recent_messages: List[Dict[str, Any]], stance_statements: Dict[str, str], defense_strategy: str, defense_rag_decision: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> str:
        """전략별 방어 응답 생성 - 모듈로 위임"""
        return self.defense_strategy_manager.generate_defense_response(
            topic, recent_messages, stance_statements, defense_strategy, 
            {'attack_info': defense_rag_decision}, emotion_enhancement
        )
    
    def _get_defense_strategy_info(self, defense_strategy: str) -> Dict[str, Any]:
        """방어 전략 정보 - 모듈로 위임"""
        return self.defense_strategy_manager._get_defense_strategy_info(defense_strategy)
    
    def _perform_defense_rag_search(self, attack_text: str, defense_strategy: str) -> List[Dict[str, Any]]:
        """방어 RAG 검색 - 모듈로 위임"""
        return self.strategy_rag_manager._perform_defense_rag_search(attack_text, defense_strategy)
    
    def _generate_defense_rag_query(self, attack_text: str, defense_strategy: str) -> str:
        """방어 RAG 쿼리 생성 - 모듈로 위임"""
        return self.strategy_rag_manager._generate_defense_rag_query(attack_text, defense_strategy)
    
    def _format_defense_rag_results(self, rag_results: List[Dict[str, Any]], defense_strategy: str) -> str:
        """방어 RAG 결과 포맷팅 - 모듈로 위임"""
        return self.defense_strategy_manager._format_defense_rag_results(rag_results, defense_strategy)
    
    def _get_philosopher_name(self, agent_id: str) -> str:
        """
        에이전트 ID로부터 철학자 이름 찾기
        
        Args:
            agent_id: 에이전트 ID
            
        Returns:
            철학자 이름
        """
        try:
            import yaml
            import os
            
            # 프로젝트 루트에서 philosophers/debate_optimized.yaml 파일 경로 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # 프로젝트 루트 찾기 (src 폴더가 있는 상위 디렉토리)
            while project_root and not os.path.exists(os.path.join(project_root, "philosophers")):
                parent = os.path.dirname(project_root)
                if parent == project_root:  # 루트에 도달
                    break
                project_root = parent
            
            yaml_path = os.path.join(project_root, "philosophers", "debate_optimized.yaml")
            
            if os.path.exists(yaml_path):
                with open(yaml_path, 'r', encoding='utf-8') as file:
                    philosophers = yaml.safe_load(file)
                
                if agent_id in philosophers:
                    return philosophers[agent_id].get("name", agent_id)
            
            # YAML에서 찾지 못한 경우 기본 매핑
            name_mapping = {
                "nietzsche": "니체",
                "camus": "카뮈", 
                "hegel": "헤겔",
                "socrates": "소크라테스",
                "plato": "플라톤",
                "aristotle": "아리스토텔레스"
            }
            
            return name_mapping.get(agent_id.lower(), agent_id.capitalize())
            
        except Exception as e:
            logger.warning(f"Error getting philosopher name for {agent_id}: {str(e)}")
            # 기본 매핑으로 fallback
            name_mapping = {
                "nietzsche": "니체",
                "camus": "카뮈", 
                "hegel": "헤겔",
                "socrates": "소크라테스",
                "plato": "플라톤",
                "aristotle": "아리스토텔레스"
            }
            return name_mapping.get(agent_id.lower(), agent_id.capitalize())
    
    def prepare_argument_with_rag(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> None:
        """RAG를 활용한 논증 준비 - 최적화된 방식 (LLM 호출 50% 절약)"""
        print(f"📝 [{self.philosopher_name}] 최적화된 RAG 논증 준비 시작")
        
        # ===== 기존 방식 (주석 처리) =====
        # 1. 핵심 논증 생성 - 모듈 사용
        # core_arguments = self.argument_generator.generate_core_arguments(topic, stance_statement)
        
        # 2. RAG 쿼리 생성 및 강화 - 모듈 사용
        # enhanced_arguments = self.rag_argument_enhancer.strengthen_arguments_with_rag(core_arguments)
        
        # ===== 새로운 최적화 방식 =====
        # 1. 핵심 논증과 RAG 쿼리를 한 번에 생성 (LLM 호출 1번 절약)
        core_arguments_with_queries = self.argument_generator.generate_arguments_with_queries(topic, stance_statement)
        
        # 2. RAG 검색으로 논증 강화 (쿼리 생성 단계 스킵)
        enhanced_arguments = self.rag_argument_enhancer.strengthen_arguments_with_rag(core_arguments_with_queries)
        
        # 3. 최종 논증 생성 - 모듈 사용
        final_argument = self.argument_generator.generate_final_opening_argument(
            topic, stance_statement, enhanced_arguments
        )
        
        # 4. 캐시에 저장
        self.argument_cache_manager.cache_prepared_argument(final_argument, topic, stance_statement, context)
        
        print(f"📝 [{self.philosopher_name}] 최적화된 RAG 논증 준비 완료 (LLM 호출 1회 절약)")
        
        # 성능 통계 로깅
        total_queries = sum(len(arg.get("rag_queries", [])) for arg in enhanced_arguments)
        strengthened_count = sum(1 for arg in enhanced_arguments if arg.get("strengthened", False))
        print(f"   📊 생성된 쿼리: {total_queries}개")
        print(f"   💪 강화된 논증: {strengthened_count}/{len(enhanced_arguments)}개")
    
    def _generate_core_arguments(self, topic: str, stance_statement: str) -> None:
        """핵심 논증 생성 - 모듈로 위임"""
        return self.argument_generator.generate_core_arguments(topic, stance_statement)
    
    def _generate_rag_queries_for_arguments(self, topic: str) -> None:
        """논증용 RAG 쿼리 생성 - 모듈로 위임"""
        if hasattr(self, 'core_arguments') and self.core_arguments:
            return self.rag_argument_enhancer.generate_rag_queries_for_arguments(topic, self.core_arguments)
    
    def _strengthen_arguments_with_rag(self) -> None:
        """RAG로 논증 강화 - 모듈로 위임"""
        if hasattr(self, 'core_arguments') and self.core_arguments:
            self.strengthened_arguments = self.rag_argument_enhancer.strengthen_arguments_with_rag(self.core_arguments)
    
    def _actually_strengthen_arguments(self) -> None:
        """실제 논증 강화 - 모듈로 위임 (deprecated)"""
        self._strengthen_arguments_with_rag()
    
    def _strengthen_single_argument_with_evidence(self, argument: str, reasoning: str, evidence_list: List[Dict[str, Any]]) -> Dict[str, str]:
        """단일 논증 강화 - 모듈로 위임"""
        return self.rag_argument_enhancer._strengthen_single_argument_with_evidence(argument, reasoning, evidence_list)
    
    def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 - 모듈로 위임"""
        return self.rag_argument_enhancer._web_search(query)
    
    def _vector_search(self, query: str) -> List[Dict[str, Any]]:
        """벡터 검색 - 모듈로 위임"""
        return self.rag_argument_enhancer._vector_search(query)
    
    def _philosopher_search(self, query: str) -> List[Dict[str, Any]]:
        """철학자 검색 - 모듈로 위임"""
        return self.rag_argument_enhancer._philosopher_search(query)

    def _extract_key_data(self, content: str, metadata: Dict[str, Any]) -> str:
        """핵심 데이터 추출 - 모듈로 위임"""
        return self.rag_argument_enhancer._extract_key_data(content, metadata)
    
    def _generate_final_opening_argument(self, topic: str, stance_statement: str) -> None:
        """최종 오프닝 논증 생성 - 모듈로 위임"""
        if hasattr(self, 'strengthened_arguments') and self.strengthened_arguments:
            return self.argument_generator.generate_final_opening_argument(
                topic, stance_statement, self.strengthened_arguments
            )

    def _extract_enhanced_metadata(self, content: str, title: str) -> Dict[str, Any]:
        """
        콘텐츠에서 구체적 데이터와 메타데이터 추출
        
        Args:
            content: 텍스트 콘텐츠
            title: 소스 제목
            
        Returns:
            향상된 메타데이터
        """
        import re
        
        metadata = {
            'has_specific_data': False,
            'statistics': [],
            'study_details': [],
            'expert_quotes': [],
            'years': [],
            'authors': []
        }
        
        # 통계 및 수치 데이터 추출
        # 퍼센트, 숫자, 측정값 등
        percentage_pattern = r'\b\d+(?:\.\d+)?%'
        number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:people|participants|subjects|patients|cases|studies|years|months|days|times|fold|million|billion|thousand)\b'
        measurement_pattern = r'\b\d+(?:\.\d+)?\s*(?:mg|kg|ml|cm|mm|meters?|feet|inches|hours?|minutes?|seconds?)\b'
        
        percentages = re.findall(percentage_pattern, content, re.IGNORECASE)
        numbers = re.findall(number_pattern, content, re.IGNORECASE)
        measurements = re.findall(measurement_pattern, content, re.IGNORECASE)
        
        if percentages:
            metadata['statistics'].extend([f"{p} change/improvement" for p in percentages[:3]])
            metadata['has_specific_data'] = True
            
        if numbers:
            metadata['statistics'].extend([f"{n}" for n in numbers[:3]])
            metadata['has_specific_data'] = True
            
        if measurements:
            metadata['statistics'].extend([f"{m}" for m in measurements[:2]])
            metadata['has_specific_data'] = True
        
        # 연구 세부사항 추출
        study_patterns = [
            r'(?:study|research|trial|experiment|analysis)\s+(?:of|with|involving)\s+(\d+(?:,\d+)*\s+(?:people|participants|subjects|patients))',
            r'(\d+(?:,\d+)*\s+(?:people|participants|subjects|patients))\s+(?:were|participated|enrolled)',
            r'(?:over|during|for)\s+(\d+\s+(?:years?|months?|weeks?|days?))',
            r'(?:randomized|controlled|double-blind|clinical)\s+(trial|study|experiment)',
            r'(?:published|reported|found)\s+in\s+(\d{4})',
            r'(?:university|institute|college)\s+(?:of\s+)?(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in study_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['study_details'].extend([match if isinstance(match, str) else ' '.join(match) for match in matches[:2]])
                metadata['has_specific_data'] = True
        
        # 전문가 인용 및 발언 추출
        quote_patterns = [
            r'"([^"]{20,100})"',  # 따옴표 안의 인용문
            r'(?:according to|says|states|reports|found that|concluded that)\s+([^.]{20,80})',
            r'(?:Dr\.|Professor|researcher)\s+(\w+(?:\s+\w+)*)\s+(?:says|states|found|reported)',
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['expert_quotes'].extend([match.strip() for match in matches[:2]])
                metadata['has_specific_data'] = True
        
        # 연도 추출
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, content)
        if years:
            metadata['years'] = [f"{y[0]}{y[1:]}" for y in years[:3]]
        
        # 저자명 추출 (간단한 패턴)
        author_pattern = r'(?:Dr\.|Professor|by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        authors = re.findall(author_pattern, content)
        if authors:
            metadata['authors'] = authors[:2]
        
        return metadata
    
    def _hybrid_chunking(self, text: str, chunk_size: int = 800, overlap_ratio: float = 0.2) -> List[str]:
        """
        문장 단위 + 슬라이딩 윈도우 하이브리드 청크화
        정보 손실을 최소화하면서 의미 있는 단위로 텍스트 분할
        
        Args:
            text: 청크화할 텍스트
            chunk_size: 목표 청크 크기 (문자 수)
            overlap_ratio: 오버랩 비율
            
        Returns:
            청크 리스트
        """
        import re
        
        # 문장 단위로 분리 (개선된 패턴)
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, text.strip())
        
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = ""
        overlap_size = int(chunk_size * overlap_ratio)
        
        for sentence in sentences:
            # 현재 청크에 문장을 추가했을 때의 길이 확인
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # 현재 청크가 비어있지 않으면 저장
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                    # 오버랩을 위해 현재 청크의 마지막 부분 유지
                    if len(current_chunk) > overlap_size:
                        # 마지막 overlap_size 문자에서 문장 경계 찾기
                        overlap_text = current_chunk[-overlap_size:]
                        # 문장 시작점 찾기
                        sentence_start = overlap_text.find('. ')
                        if sentence_start != -1:
                            current_chunk = overlap_text[sentence_start + 2:]
                        else:
                            current_chunk = overlap_text
                    else:
                        current_chunk = ""
                
                # 새로운 문장으로 시작
                current_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_stage_instructions(self, current_stage: str, topic: str, my_stance: str, opposite_stance: str) -> str:
        """
        현재 단계에 맞는 지시사항 반환
        
        Args:
            current_stage: 현재 토론 단계
            topic: 토론 주제
            my_stance: 내 입장
            opposite_stance: 상대방 입장
            
        Returns:
            단계별 지시사항
        """
        role_display = "PRO" if self.role == "pro" else "CON" if self.role == "con" else "NEUTRAL"
        
        stage_instructions = {
            "pro_argument": f"Present your main arguments. Clearly articulate 2-3 strong points supporting your position, back up each point with evidence or reasoning, and be persuasive and confident in your delivery.",
            
            "con_argument": f"Present your main arguments against the topic. Clearly articulate 2-3 strong points supporting your position, back up each point with evidence or reasoning, and be persuasive and confident in your delivery.",
            
            "pro_rebuttal": f"Rebut the arguments made by the opposition. Address the strongest points made by the CON side, point out logical flaws or factual errors in their arguments, and reinforce your own position.",
            
            "con_rebuttal": f"Rebut the arguments made by the opposition. Address the strongest points made by the PRO side, point out logical flaws or factual errors in their arguments, and reinforce your own position.",
            
            "con_to_pro_qa": f"{'Ask a pointed question to the PRO side that challenges their position' if self.role == 'con' else 'Answer the question from the CON side while defending your position'}.",
            
            "pro_to_con_qa": f"{'Ask a pointed question to the CON side that challenges their position' if self.role == 'pro' else 'Answer the question from the PRO side while defending your position'}.",
            
            "pro_conclusion": f"Deliver your closing statement. Summarize your strongest arguments, address key points raised during the debate, and reinforce why your position is correct.",
            
            "con_conclusion": f"Deliver your closing statement. Summarize your strongest arguments, address key points raised during the debate, and reinforce why your position is correct."
        }
        
        # 기본 지시사항
        default_instruction = f"Respond to the current discussion while advocating for your position: '{my_stance}'."
        
        return stage_instructions.get(current_stage, default_instruction)
    
    
    def _prepare_closing_statement(self, dialogue_state: Dict[str, Any], stance_statements: Dict[str, str]) -> str:
        """
        최종 결론 발언 준비
        
        Args:
            dialogue_state: 현재 대화 상태
            stance_statements: 찬반 입장 진술문
            
        Returns:
            최종 결론 발언
        """
        # 내 입장 확인
        my_stance = stance_statements.get(self.role) if self.role in ["pro", "con"] else ""
        
        # 최종 결론 템플릿 (역할별)
        if self.role == "pro":
            template = f"""지금까지의 토론을 통해 저희의 입장을 다시 한번 강조하고자 합니다.

{my_stance}

오늘 토론에서 우리는 다음과 같은 중요한 점들을 확인했습니다:

첫째, [첫 번째 핵심 포인트 요약]
둘째, [두 번째 핵심 포인트 요약]  
셋째, [세 번째 핵심 포인트 요약]

따라서 저희는 계속해서 이 입장을 지지하며, 이것이 올바른 방향이라고 확신합니다.

감사합니다."""
        else:
            template = f"""지금까지의 토론을 통해 저희의 입장을 다시 한번 강조하고자 합니다.

{my_stance}

오늘 토론에서 우리는 다음과 같은 중요한 점들을 확인했습니다:

첫째, [첫 번째 핵심 포인트 요약]
둘째, [두 번째 핵심 포인트 요약]
셋째, [세 번째 핵심 포인트 요약]

따라서 저희는 계속해서 이 입장을 지지하며, 이것이 올바른 방향이라고 확신합니다.

감사합니다."""
        
        return template
    
    def _update_interaction_history(self, prompt: str, response: str) -> None:
        """
        상호작용 기록 업데이트
        
        Args:
            prompt: 입력된 프롬프트
            response: 생성된 응답
        """
        # interaction_history가 없으면 초기화
        if "interaction_history" not in self.state:
            self.state["interaction_history"] = []
            
        self.state["interaction_history"].append({
            "timestamp": time.time(),
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "response": response[:100] + "..." if len(response) > 100 else response
        })
        
        # 기록이 너무 많아지면 오래된 것부터 제거
        if len(self.state["interaction_history"]) > 10:
            self.state["interaction_history"] = self.state["interaction_history"][-10:]
        
    def extract_opponent_key_points(self, opponent_messages: List[Dict[str, Any]]) -> None:
        """
        상대방 발언에서 핵심 논점 추출하여 저장
        다중 상대방 지원: 각 상대방별로 논점을 구분하여 저장
        
        Args:
            opponent_messages: 상대방 발언 메시지들 (여러 상대방 포함 가능)
        """
        if self.opponent_analyzer:
            self.opponent_analyzer.extract_opponent_key_points(opponent_messages)
            # 결과를 기존 속성에 동기화
            self.opponent_key_points = self.opponent_analyzer.get_opponent_key_points()
            self.opponent_arguments = self.opponent_analyzer.get_opponent_arguments()
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")

    def update_my_key_points_from_core_arguments(self) -> None:
        """
        자신의 core_arguments에서 my_key_points 업데이트
        """
        if self.opponent_analyzer:
            self.my_key_points = self.opponent_analyzer.update_my_key_points_from_core_arguments(self.core_arguments)
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")

    def clear_opponent_data(self, speaker_id: str = None):
        """
        상대방 데이터 정리
        
        Args:
            speaker_id: 특정 발언자 ID (None이면 전체 정리)
        """
        if self.opponent_analyzer:
            self.opponent_analyzer.clear_opponent_data(speaker_id)
            # 기존 속성도 동기화
            self.opponent_arguments = self.opponent_analyzer.get_opponent_arguments()
            self.opponent_key_points = self.opponent_analyzer.get_opponent_key_points()
        else:
            # 폴백: 직접 정리
            if speaker_id:
                if speaker_id in self.opponent_arguments:
                    del self.opponent_arguments[speaker_id]
            else:
                self.opponent_arguments.clear()
                self.opponent_key_points.clear()

    def _extract_key_concept(self, text: str) -> str:
        """
        텍스트에서 핵심 개념을 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 핵심 개념
        """
        if self.opponent_analyzer:
            return self.opponent_analyzer.argument_extractor.extract_key_concept(text)
        else:
            # 폴백: 간단한 추출
            words = text.split()
            return words[0] if words else "concept"
    
    # ========================================================================
    # ARGUMENT PREPARATION STATE MANAGEMENT (Option 2 구현)
    # ========================================================================
    
    def is_argument_ready(self) -> bool:
        """논증 준비 상태 확인 - 모듈로 위임"""
        return self.argument_cache_manager.is_argument_ready()
    
    def is_currently_preparing(self) -> bool:
        """현재 준비 중인지 확인 - 모듈로 위임"""
        return self.argument_cache_manager.is_currently_preparing()
    
    async def prepare_argument_async(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """비동기 논증 준비 - 모듈로 위임"""
        return await self.argument_cache_manager.prepare_argument_async(
            topic, stance_statement, context, self.prepare_argument_with_rag
        )

    def get_prepared_argument_or_generate(self, topic: str, stance_statement: str, context: Dict[str, Any] = None) -> tuple[str, Dict[str, Any]]:
        """준비된 논증 가져오기 또는 생성 - 모듈로 위임"""
        return self.argument_cache_manager.get_prepared_argument_or_generate(
            topic, stance_statement, context, self.argument_generator, self.rag_argument_enhancer
        )
    
    def invalidate_argument_cache(self):
        """논증 캐시 무효화 - 모듈로 위임"""
        self.argument_cache_manager.invalidate_argument_cache()
    
    def _is_same_context(self, context: Dict[str, Any]) -> bool:
        """컨텍스트 동일성 확인 - 모듈로 위임"""
        return self.argument_cache_manager._is_same_context(context)
    
    def analyze_and_score_arguments(self, opponent_response: str, speaker_id: str) -> Dict[str, Any]:
        """
        상대방 발언에서 논지를 추출하고 스코어링
        
        Args:
            opponent_response: 상대방 발언 텍스트
            speaker_id: 발언자 ID
            
        Returns:
            분석 결과 (논지 목록, 스코어, 취약점 등)
        """
        if self.opponent_analyzer:
            return self.opponent_analyzer.analyze_and_score_arguments(opponent_response, speaker_id)
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")
            return {"error": "OpponentAnalyzer not available"}

    def extract_arguments_from_user_input(self, user_response: str, speaker_id: str) -> List[Dict[str, Any]]:
        """
        유저 입력에서 LLM을 사용해 논지를 추출합니다.
        
        Args:
            user_response: 유저의 입력 텍스트
            speaker_id: 유저 ID
            
        Returns:
            List[Dict]: 추출된 논지들 (최대 3개)
        """
        if self.opponent_analyzer:
            return self.opponent_analyzer.argument_extractor.extract_arguments_from_user_input(user_response, speaker_id)
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")
            return []

    def analyze_user_arguments(self, user_response: str, speaker_id: str) -> Dict[str, Any]:
        """
        유저 입력을 분석하여 논지를 추출하고 취약성을 평가합니다.
        
        Args:
            user_response: 유저의 입력 텍스트  
            speaker_id: 유저 ID
            
        Returns:
            Dict: 분석 결과 (기존 analyze_and_score_arguments와 동일한 포맷)
        """
        if self.opponent_analyzer:
            return self.opponent_analyzer.analyze_user_arguments(user_response, speaker_id)
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")
            return {
                'opponent_arguments': {speaker_id: []},
                'total_arguments': 0,
                'analysis_summary': f"OpponentAnalyzer not available"
            }
    
    def prepare_attack_strategies_for_speaker(self, target_speaker_id: str) -> List[Dict[str, Any]]:
        """공격 전략 준비 - 모듈로 위임"""
        # OpponentAnalyzer에서 최신 opponent_arguments 가져오기
        if self.opponent_analyzer:
            opponent_arguments = self.opponent_analyzer.get_opponent_arguments()
            
            if opponent_arguments and target_speaker_id in opponent_arguments:
                result = self.attack_strategy_manager.prepare_attack_strategies_for_speaker(
                    target_speaker_id, 
                    opponent_arguments,
                    self.strategy_rag_manager
                )
                
                if result.get("status") == "success":
                    return result.get("strategies", [])
                else:
                    logger.error(f"[{self.agent_id}] Attack strategy preparation failed: {result.get('reason', 'unknown')}")
                    return []
            else:
                logger.warning(f"[{self.agent_id}] No arguments found for target speaker: {target_speaker_id}")
                return []
        else:
            logger.error(f"[{self.agent_id}] OpponentAnalyzer not initialized")
            return []
    
    def get_best_attack_strategy(self, target_speaker_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """최적 공격 전략 선택 - 모듈로 위임"""
        return self.attack_strategy_manager.get_best_attack_strategy(target_speaker_id, context)
    
    def _prepare_argument(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입론 준비 처리
        
        Args:
            input_data: 입론 준비에 필요한 데이터
            
        Returns:
            준비 결과 (RAG 정보 포함)
        """
        topic = input_data.get("topic", "")
        stance_statement = input_data.get("stance_statement", "")
        context = input_data.get("context", {})
        
        self.prepare_argument_with_rag(topic, stance_statement, context)
        
        return {
            "status": "success" if self.argument_prepared else "failed",
            "message": self.prepared_argument if self.prepared_argument else "입론 생성에 실패했습니다.",
            "prepared": self.argument_prepared,
            "core_arguments_count": len(self.core_arguments),
            "queries_count": len(self.argument_queries),
            # RAG 정보 추가
            "rag_used": self.rag_info.get("rag_used", False),
            "rag_source_count": self.rag_info.get("rag_source_count", 0),
            "rag_sources": self.rag_info.get("rag_sources", [])
        }
    
    def _generate_attack_rag_query_for_strategy(self, target_argument: Dict[str, Any], strategy_type: str) -> str:
        """공격 RAG 쿼리 생성 - 모듈로 위임"""
        return self.strategy_rag_manager._generate_attack_rag_query(target_argument, strategy_type)
    
    def _perform_attack_rag_search(self, query: str, strategy_type: str) -> List[Dict[str, Any]]:
        """공격 RAG 검색 - 모듈로 위임"""
        return self.strategy_rag_manager._perform_attack_rag_search(query, strategy_type)
    
    def _filter_and_rank_search_results(self, results: List[Dict[str, Any]], query: str, strategy_type: str) -> List[Dict[str, Any]]:
        """검색 결과 필터링 및 순위 - 기존 로직 유지 (전략별 특화)"""
        if not results:
            return []
        
        try:
            # 각 결과에 대해 관련성 점수 계산
            scored_results = []
            for result in results:
                relevance_score = self._calculate_result_relevance(result, query, strategy_type)
                result['relevance_score'] = relevance_score
                scored_results.append(result)
                        
            # 관련성 점수로 정렬
            scored_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
            # 상위 결과만 반환 (전략별로 다른 개수)
            strategy_limits = {
                "Logical_Fallacy": 3,
                "Evidence_Challenge": 4,
                "Assumption_Challenge": 3,
                "Scope_Challenge": 2,
                "Precedent_Challenge": 3
            }
            
            limit = strategy_limits.get(strategy_type, 3)
            return scored_results[:limit]
            
        except Exception as e:
            logger.error(f"Error filtering search results: {str(e)}")
            return results[:3]  # 기본값

    def _calculate_result_relevance(self, result: Dict[str, Any], query: str, strategy_type: str) -> float:
        """검색 결과 관련성 점수 계산 - 기존 로직 유지 (전략별 특화)"""
        try:
            score = 0.0
            
            # 기본 텍스트 매칭
            title = result.get('title', '').lower()
            content = result.get('content', result.get('snippet', '')).lower()
            query_lower = query.lower()
            
            # 쿼리 키워드가 제목에 있으면 높은 점수
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 2:  # 짧은 단어 제외
                    if word in title:
                        score += 2.0
                    if word in content:
                        score += 1.0
            
            # 전략별 키워드 가중치
            strategy_keywords = {
                "Logical_Fallacy": ["fallacy", "logic", "reasoning", "argument", "error"],
                "Evidence_Challenge": ["evidence", "proof", "data", "study", "research"],
                "Assumption_Challenge": ["assumption", "premise", "basis", "foundation"],
                "Scope_Challenge": ["scope", "limit", "boundary", "context", "range"],
                "Precedent_Challenge": ["precedent", "history", "past", "example", "case"]
            }
            
            keywords = strategy_keywords.get(strategy_type, [])
            for keyword in keywords:
                if keyword in content:
                    score += 1.5
                if keyword in title:
                    score += 2.5
            
            # 철학자 도메인 키워드 추가 점수
            philosopher_keywords = self._get_philosopher_domain_keywords()
            for keyword in philosopher_keywords:
                if keyword.lower() in content:
                    score += 1.0
                if keyword.lower() in title:
                    score += 1.5
            
            # 콘텐츠 길이 고려 (너무 짧거나 긴 것 페널티)
            content_length = len(content)
            if 50 <= content_length <= 500:
                score += 0.5
            elif content_length < 20:
                score -= 1.0
            elif content_length > 1000:
                score -= 0.5
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating relevance: {str(e)}")
            return 0.0

    def _get_philosopher_domain_keywords(self) -> List[str]:
        """철학자 도메인 키워드 - 기존 로직 유지"""
        try:
            # 철학자별 도메인 키워드
            philosopher_domains = {
                "socrates": ["ethics", "virtue", "knowledge", "wisdom", "questioning"],
                "aristotle": ["logic", "ethics", "politics", "metaphysics", "virtue"],
                "plato": ["justice", "ideal", "forms", "republic", "knowledge"],
                "kant": ["duty", "categorical", "imperative", "moral", "reason"],
                "mill": ["utility", "happiness", "liberty", "harm", "individual"],
                "rawls": ["justice", "fairness", "veil", "ignorance", "equality"],
                "nozick": ["rights", "liberty", "property", "minimal", "state"],
                "singer": ["utility", "animal", "rights", "effective", "altruism"]
            }
        
            philosopher_key = getattr(self, 'philosopher_key', self.name.lower())
            return philosopher_domains.get(philosopher_key, ["philosophy", "ethics", "reasoning"])
            
        except Exception as e:
            logger.error(f"Error getting philosopher keywords: {str(e)}")
            return ["philosophy", "ethics", "reasoning"]
    
    def _format_attack_rag_results(self, rag_results: List[Dict[str, Any]], strategy_type: str) -> str:
        """공격 RAG 결과 포맷팅 - 모듈로 위임"""
        return self.strategy_rag_manager._format_attack_rag_results(rag_results, strategy_type)
    
    def _generate_followup_response(self, topic: str, recent_messages: List[Dict[str, Any]], dialogue_state: Dict[str, Any], stance_statements: Dict[str, str], emotion_enhancement: Dict[str, Any] = None) -> str:
        """
        팔로우업 응답 생성 - 모듈 사용
        """
        print(f"🔄 [{self.philosopher_name}] 팔로우업 응답 생성 시작")
        
        # 1. 상대방 방어 분석 - 모듈 사용
        defense_info = self.followup_strategy_manager.analyze_defense_response(recent_messages)
        
        # 2. 팔로우업 전략 선택 - 모듈 사용
        followup_strategy = self.followup_strategy_manager.select_followup_strategy(defense_info, emotion_enhancement)
        
        # 3. 팔로우업 응답 생성 - 모듈 사용
        followup_response = self.followup_strategy_manager.generate_followup_response(
            topic, recent_messages, stance_statements, followup_strategy, 
            defense_info, emotion_enhancement
        )
        
        print(f"🔄 [{self.philosopher_name}] 팔로우업 응답 생성 완료 - 전략: {followup_strategy}")
        return followup_response
    
    def _analyze_defense_response(self, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """방어 응답 분석 - 모듈로 위임"""
        return self.followup_strategy_manager.analyze_defense_response(recent_messages)
    
    def _get_defender_strategy_info(self, defender_id: str) -> Dict[str, Any]:
        """방어자 전략 정보 - 모듈로 위임"""
        return self.followup_strategy_manager._get_defender_strategy_info(defender_id)
    
    def _estimate_defense_strategy_from_keywords(self, defense_text: str, defender_id: str) -> Dict[str, Any]:
        """키워드 기반 방어 전략 추정 - 모듈로 위임"""
        return self.followup_strategy_manager._estimate_defense_strategy_from_keywords(defense_text, defender_id)
    
    def _select_followup_strategy(self, defense_info: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> str:
        """팔로우업 전략 선택 - 모듈로 위임"""
        return self.followup_strategy_manager.select_followup_strategy(defense_info, emotion_enhancement)
    
    def _get_followup_candidates_from_map(self, defense_info: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> List[str]:
        """팔로우업 후보 전략 목록 - 모듈로 위임"""
        return self.followup_strategy_manager._get_followup_candidates_from_map(defense_info, emotion_enhancement)
    
    def _determine_followup_rag_usage(self, followup_strategy: str, defense_info: Dict[str, Any]) -> Dict[str, Any]:
        """팔로우업 RAG 사용 결정 - 모듈로 위임"""
        return self.strategy_rag_manager.determine_followup_rag_usage(followup_strategy, defense_info)
    
    def _get_followup_strategy_rag_weight(self, followup_strategy: str) -> float:
        """팔로우업 전략 RAG 가중치 - 모듈로 위임"""
        return self.strategy_rag_manager._get_followup_strategy_rag_weight(followup_strategy)
    
    def _generate_followup_response_with_strategy(self, topic: str, recent_messages: List[Dict[str, Any]], stance_statements: Dict[str, str], followup_strategy: str, followup_rag_decision: Dict[str, Any], emotion_enhancement: Dict[str, Any] = None) -> str:
        """전략별 팔로우업 응답 생성 - 모듈로 위임"""
        return self.followup_strategy_manager.generate_followup_response(
            topic, recent_messages, stance_statements, followup_strategy, 
            followup_rag_decision, emotion_enhancement
        )
    
    def _get_followup_strategy_info(self, followup_strategy: str) -> Dict[str, Any]:
        """팔로우업 전략 정보 - 모듈로 위임"""
        return self.followup_strategy_manager._get_followup_strategy_info(followup_strategy)
    
    def _perform_followup_rag_search(self, defense_text: str, followup_strategy: str, original_attack: str) -> List[Dict[str, Any]]:
        """팔로우업 RAG 검색 - 모듈로 위임"""
        return self.strategy_rag_manager._perform_followup_rag_search(defense_text, followup_strategy)
    
    def _generate_followup_rag_query(self, defense_text: str, followup_strategy: str, original_attack: str) -> str:
        """팔로우업 RAG 쿼리 생성 - 모듈로 위임"""
        return self.strategy_rag_manager._generate_followup_rag_query(defense_text, followup_strategy, original_attack)
    
    def _format_followup_rag_results(self, rag_results: List[Dict[str, Any]], followup_strategy: str) -> str:
        """팔로우업 RAG 결과 포맷팅 - 모듈로 위임"""
        return self.followup_strategy_manager._format_followup_rag_results(rag_results, followup_strategy)