#!/usr/bin/env python
"""
RAG 실험 실행 스크립트

실험 설정 파일을 기반으로 RAG 실험을 실행하는 명령줄 도구
"""

import os
import sys
import argparse
import logging
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# 프로젝트 루트 경로 설정
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent.absolute()
sys.path.append(str(project_root))

# 로컬 모듈 임포트
from experiments.rag.config import ExperimentConfig, generate_experiment_variations
from experiments.rag.pipeline import ExperimentPipeline
from experiments.rag.visualization import ExperimentVisualizer


def setup_logger(log_dir: str = "./logs") -> logging.Logger:
    """
    로거 설정
    
    Args:
        log_dir: 로그 파일 저장 경로
        
    Returns:
        설정된 로거
    """
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger("rag_experiments")
    logger.setLevel(logging.INFO)
    
    # 포맷 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    log_file = os.path.join(log_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def load_test_queries(query_file: str) -> List[str]:
    """
    테스트 쿼리 로드
    
    Args:
        query_file: 쿼리 파일 경로
        
    Returns:
        쿼리 목록
    """
    if not os.path.exists(query_file):
        raise FileNotFoundError(f"쿼리 파일을 찾을 수 없음: {query_file}")
        
    # 파일 확장자에 따라 로드 방법 결정
    if query_file.endswith(".json"):
        with open(query_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 다양한 JSON 구조 지원
        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                return data
            elif all(isinstance(item, dict) and "query" in item for item in data):
                return [item["query"] for item in data]
        elif isinstance(data, dict) and "queries" in data:
            return data["queries"]
            
        raise ValueError(f"지원되지 않는 JSON 쿼리 형식: {query_file}")
        
    elif query_file.endswith(".yaml") or query_file.endswith(".yml"):
        with open(query_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                return data
            elif all(isinstance(item, dict) and "query" in item for item in data):
                return [item["query"] for item in data]
        elif isinstance(data, dict) and "queries" in data:
            return data["queries"]
            
        raise ValueError(f"지원되지 않는 YAML 쿼리 형식: {query_file}")
        
    else:  # 텍스트 파일로 간주
        with open(query_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 공백 줄 제거 및 앞뒤 공백 제거
        return [line.strip() for line in lines if line.strip()]


def run_single_experiment(config_file: str, 
                         output_dir: str, 
                         query_file: Optional[str] = None,
                         visualize: bool = False,
                         logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    단일 실험 실행
    
    Args:
        config_file: 실험 설정 파일 경로
        output_dir: 실험 결과 저장 경로
        query_file: 테스트 쿼리 파일 경로 (선택사항)
        visualize: 결과 시각화 여부
        logger: 로거
        
    Returns:
        실험 결과
    """
    if logger is None:
        logger = setup_logger()
        
    logger.info(f"단일 실험 실행: {config_file}")
    
    # 설정 파일 로드
    if config_file.endswith(".yaml") or config_file.endswith(".yml"):
        config = ExperimentConfig.from_yaml(config_file)
    else:  # .json으로 간주
        config = ExperimentConfig.load(config_file)
        
    # 쿼리 파일 로드 (있는 경우)
    if query_file and os.path.exists(query_file):
        try:
            queries = load_test_queries(query_file)
            logger.info(f"{len(queries)}개 테스트 쿼리 로드됨")
            config.test_queries = queries
        except Exception as e:
            logger.error(f"쿼리 파일 로드 실패: {str(e)}")
            
    # 쿼리가 없는 경우 기본 쿼리 설정
    if not config.test_queries:
        logger.warning("테스트 쿼리가 없음. 기본 쿼리 사용")
        config.test_queries = [
            "인공지능이란 무엇인가?",
            "벡터 데이터베이스의 장점은?",
            "RAG 시스템을 구축하는 방법"
        ]
    
    # 실험 파이프라인 초기화 및 실행
    pipeline = ExperimentPipeline(output_dir)
    result = pipeline.run_experiment(config)
    
    # 결과 시각화 (필요한 경우)
    if visualize:
        logger.info("실험 결과 시각화 생성")
        visualizer = ExperimentVisualizer(output_dir)
        
        # 실험 결과가 하나뿐이므로 개별 차트 생성이 의미 없음
        # 대신 이 실험에 대한 유사도 분포와 쿼리별 성능 분석 차트만 생성
        
        vis_dir = os.path.join(output_dir, config.experiment_id, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # 유사도 분포
        dist_path = os.path.join(vis_dir, "similarity_distribution.png")
        visualizer.generate_similarity_distribution(
            experiment_id=config.experiment_id,
            save_path=dist_path
        )
        
        # 쿼리별 성능
        query_path = os.path.join(vis_dir, "query_performance.png")
        visualizer.generate_query_performance_breakdown(
            experiment_id=config.experiment_id,
            save_path=query_path
        )
        
        logger.info(f"시각화 저장 완료: {vis_dir}")
    
    return result


def run_parameter_variations(base_config_file: str,
                           param_name: str,
                           param_values: List[Any],
                           output_dir: str,
                           query_file: Optional[str] = None,
                           visualize: bool = False,
                           logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """
    파라미터 변화에 따른 실험 실행
    
    Args:
        base_config_file: 기본 설정 파일 경로
        param_name: 변경할 파라미터 이름
        param_values: 테스트할 파라미터 값 목록
        output_dir: 실험 결과 저장 경로
        query_file: 테스트 쿼리 파일 경로 (선택사항)
        visualize: 결과 시각화 여부
        logger: 로거
        
    Returns:
        실험 결과 목록
    """
    if logger is None:
        logger = setup_logger()
        
    logger.info(f"파라미터 변화 실험: {param_name}, 값: {param_values}")
    
    # 기본 설정 파일 로드
    if base_config_file.endswith(".yaml") or base_config_file.endswith(".yml"):
        base_config = ExperimentConfig.from_yaml(base_config_file)
    else:  # .json으로 간주
        base_config = ExperimentConfig.load(base_config_file)
        
    # 쿼리 파일 로드 (있는 경우)
    if query_file and os.path.exists(query_file):
        try:
            queries = load_test_queries(query_file)
            logger.info(f"{len(queries)}개 테스트 쿼리 로드됨")
            base_config.test_queries = queries
        except Exception as e:
            logger.error(f"쿼리 파일 로드 실패: {str(e)}")
    
    # 파라미터 변화에 따른 설정 생성
    configs = generate_experiment_variations(base_config, param_name, param_values)
    logger.info(f"{len(configs)}개 실험 설정 생성됨")
    
    # 실험 파이프라인 초기화
    pipeline = ExperimentPipeline(output_dir)
    
    # 각 설정별 실험 실행
    results = []
    for idx, config in enumerate(configs):
        logger.info(f"실험 {idx+1}/{len(configs)}: {config.name}")
        result = pipeline.run_experiment(config)
        results.append(result)
    
    # 결과 시각화 (필요한 경우)
    if visualize and results:
        logger.info("파라미터 변화 실험 결과 시각화 생성")
        
        # 변화 실험 결과 디렉토리 생성 - 이름 형식 변경
        base_config_name = os.path.splitext(os.path.basename(base_config_file))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        variation_dir = os.path.join(
            output_dir, 
            f"param_variation_{base_config_name}_{param_name}-{timestamp}"
        )
        os.makedirs(variation_dir, exist_ok=True)
        
        # 결과 모음 파일 저장
        summary_path = os.path.join(variation_dir, 'variation_summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                'base_config_file': base_config_file,
                'param_name': param_name,
                'param_values': [str(v) for v in param_values],
                'results': results
            }, f, ensure_ascii=False, indent=2)
            
        # 종합 시각화 생성
        visualizer = ExperimentVisualizer(output_dir)
        visualizer.generate_dashboard(variation_dir)
        
        # 파라미터 영향 차트 생성
        impact_path = os.path.join(variation_dir, f"{param_name}_impact.png")
        visualizer.generate_parameter_impact(param_name, save_path=impact_path)
        
        logger.info(f"시각화 저장 완료: {variation_dir}")
    
    return results


def run_experiment_suite(configs_dir: str,
                        output_dir: str,
                        query_file: Optional[str] = None,
                        visualize: bool = False,
                        logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
    """
    실험 스위트 실행
    
    Args:
        configs_dir: 설정 파일 디렉토리 경로
        output_dir: 실험 결과 저장 경로
        query_file: 테스트 쿼리 파일 경로 (선택사항)
        visualize: 결과 시각화 여부
        logger: 로거
        
    Returns:
        실험 결과 목록
    """
    if logger is None:
        logger = setup_logger()
        
    logger.info(f"실험 스위트 실행: {configs_dir}")
    
    # 설정 파일 목록 가져오기
    if not os.path.isdir(configs_dir):
        logger.error(f"설정 디렉토리를 찾을 수 없음: {configs_dir}")
        return []
        
    # 모든 YAML 및 JSON 파일 찾기
    config_files = []
    for ext in [".yaml", ".yml", ".json"]:
        config_files.extend(
            [os.path.join(configs_dir, f) for f in os.listdir(configs_dir) 
             if f.endswith(ext) and os.path.isfile(os.path.join(configs_dir, f))]
        )
    
    if not config_files:
        logger.error(f"설정 파일을 찾을 수 없음: {configs_dir}")
        return []
        
    logger.info(f"{len(config_files)}개 설정 파일 발견")
    
    # 쿼리 파일 로드 (있는 경우)
    queries = None
    if query_file and os.path.exists(query_file):
        try:
            queries = load_test_queries(query_file)
            logger.info(f"{len(queries)}개 테스트 쿼리 로드됨")
        except Exception as e:
            logger.error(f"쿼리 파일 로드 실패: {str(e)}")
    
    # 실험 파이프라인 초기화
    pipeline = ExperimentPipeline(output_dir)
    
    # 각 설정 파일에 대한 실험 실행
    results = []
    for idx, config_file in enumerate(sorted(config_files)):
        logger.info(f"실험 {idx+1}/{len(config_files)}: {config_file}")
        
        try:
            # 설정 파일 로드
            if config_file.endswith(".yaml") or config_file.endswith(".yml"):
                config = ExperimentConfig.from_yaml(config_file)
            else:  # .json으로 간주
                config = ExperimentConfig.load(config_file)
                
            # 쿼리 설정 (있는 경우)
            if queries:
                config.test_queries = queries
                
            # 실험 실행
            result = pipeline.run_experiment(config)
            results.append(result)
            
        except Exception as e:
            logger.error(f"실험 실패: {config_file} - {str(e)}", exc_info=True)
    
    # 결과 시각화 (필요한 경우)
    if visualize and results:
        logger.info("실험 결과 시각화 생성")
        
        # 스위트 결과 디렉토리 생성 - 이름 형식 변경
        suite_name = os.path.basename(os.path.normpath(configs_dir))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suite_dir = os.path.join(
            output_dir, 
            f"suite_{suite_name}-{timestamp}"
        )
        os.makedirs(suite_dir, exist_ok=True)
        
        # 종합 시각화 생성
        visualizer = ExperimentVisualizer(output_dir)
        dashboard_path = visualizer.generate_dashboard(suite_dir)
        
        logger.info(f"대시보드 생성 완료: {dashboard_path}")
    
    return results


def main():
    """명령줄 인터페이스"""
    parser = argparse.ArgumentParser(description="RAG 실험 실행 도구")
    
    # 실행 모드 선택
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--config", help="단일 실험 설정 파일 경로")
    mode_group.add_argument("--configs-dir", help="여러 실험 설정 파일이 있는 디렉토리 경로")
    mode_group.add_argument("--param-variation", help="파라미터 변화 실험을 위한 기본 설정 파일 경로")
    
    # 공통 옵션
    parser.add_argument("--output-dir", default="./experiment_results",
                     help="실험 결과를 저장할 디렉토리 경로")
    parser.add_argument("--query-file", help="테스트 쿼리 파일 경로")
    parser.add_argument("--visualize", action="store_true", help="실험 결과 시각화 생성")
    parser.add_argument("--verbose", action="store_true", help="상세 로깅 활성화")
    
    # 파라미터 변화 실험 옵션
    parser.add_argument("--param-name", help="변경할 파라미터 이름")
    parser.add_argument("--param-values", help="테스트할 파라미터 값 (쉼표로 구분)")
    
    args = parser.parse_args()
    
    # 로거 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger()
    logger.setLevel(log_level)
    
    # 출력 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 실행 모드에 따른 처리
    if args.config:
        # 단일 실험 실행
        run_single_experiment(
            config_file=args.config,
            output_dir=args.output_dir,
            query_file=args.query_file,
            visualize=args.visualize,
            logger=logger
        )
        
    elif args.configs_dir:
        # 실험 스위트 실행
        run_experiment_suite(
            configs_dir=args.configs_dir,
            output_dir=args.output_dir,
            query_file=args.query_file,
            visualize=args.visualize,
            logger=logger
        )
        
    elif args.param_variation:
        # 파라미터 변화 실험
        if not args.param_name or not args.param_values:
            parser.error("파라미터 변화 실험을 위해서는 --param-name과 --param-values가 필요합니다.")
            
        # 파라미터 값 파싱
        try:
            # 문자열, 숫자, 불리언 타입 처리
            param_values = []
            for val in args.param_values.split(','):
                val = val.strip()
                if val.lower() == 'true':
                    param_values.append(True)
                elif val.lower() == 'false':
                    param_values.append(False)
                elif val.isdigit():
                    param_values.append(int(val))
                elif '.' in val and all(part.isdigit() for part in val.split('.', 1)):
                    param_values.append(float(val))
                else:
                    param_values.append(val)
        except Exception as e:
            logger.error(f"파라미터 값 파싱 실패: {str(e)}")
            sys.exit(1)
            
        run_parameter_variations(
            base_config_file=args.param_variation,
            param_name=args.param_name,
            param_values=param_values,
            output_dir=args.output_dir,
            query_file=args.query_file,
            visualize=args.visualize,
            logger=logger
        )
        
    logger.info("실험 실행 완료")


if __name__ == "__main__":
    main() 