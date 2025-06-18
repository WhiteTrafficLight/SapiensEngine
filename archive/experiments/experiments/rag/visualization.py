"""
실험 결과 시각화 도구

RAG 실험 결과를 다양한 차트와 그래프로 시각화하는 유틸리티
"""

import os
import json
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

# 한글 폰트 문제 해결
def configure_korean_font():
    # 시스템에 설치된 폰트 확인
    system_fonts = [f.name for f in fm.fontManager.ttflist]
    print(f"시스템에 설치된 폰트 수: {len(system_fonts)}")
    
    # 한글 폰트 목록 (OS에 따라 달라질 수 있음)
    korean_fonts = ['AppleGothic', 'Malgun Gothic', 'NanumGothic', 'NanumBarunGothic', 
                    'Noto Sans CJK KR', 'Noto Sans KR', 'Gulim', 'Dotum', 'Batang']
    
    # 사용 가능한 한글 폰트 찾기
    available_font = None
    for font in korean_fonts:
        if font in system_fonts:
            available_font = font
            print(f"사용 가능한 한글 폰트 발견: {font}")
            break
    
    if available_font:
        plt.rcParams['font.family'] = available_font
        plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
        return True
    
    # MacOS 환경에서 자주 사용되는 폰트 경로 직접 지정
    font_paths = [
        '/Library/Fonts/AppleGothic.ttf',
        '/System/Library/Fonts/AppleGothic.ttf',
        '/Library/Fonts/NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_prop = fm.FontProperties(fname=font_path)
                plt.rcParams['font.family'] = font_prop.get_name()
                plt.rcParams['axes.unicode_minus'] = False
                print(f"폰트 파일 직접 지정: {font_path}")
                return True
            except:
                pass
    
    print("한글 폰트를 찾을 수 없습니다. ASCII 텍스트로 대체됩니다.")
    return False

# 한글 텍스트 대체 함수 (폰트 문제 발생 시 사용)
def safe_text(text):
    # 한글 폰트가 설정되지 않았을 때 한글 텍스트를 ASCII로 대체
    if not hasattr(safe_text, 'font_available'):
        safe_text.font_available = configure_korean_font()
    
    # 폰트가 설정되었다면 원래 텍스트 반환
    if safe_text.font_available:
        return text
    
    # 한글 텍스트를 영어로 대체
    replacements = {
        '실험': 'Experiment',
        '비교': 'Comparison',
        '메트릭': 'Metric',
        '파라미터': 'Parameter',
        '영향': 'Impact',
        '상관관계': 'Correlation',
        '유사도': 'Similarity',
        '분포': 'Distribution',
        '빈도': 'Frequency',
        '평균': 'Mean',
        '중앙값': 'Median',
        '최소값': 'Min',
        '최대값': 'Max',
        '표준편차': 'StdDev',
        '쿼리': 'Query',
        '성능': 'Performance',
        '최고': 'Top',
        '점수': 'Score',
        '청크': 'Chunk',
        '히트맵': 'Heatmap',
        '크기': 'Size',
        '모델': 'Model',
        '임베딩': 'Embedding',
        '이': 'This',
        '에': ' for ',
        '미치는': 'affecting',
        '와': 'and',
        '별': 'by',
        '기본': 'Default',
        '가': ' is ',
    }
    
    for kr, en in replacements.items():
        text = text.replace(kr, en)
    
    return text

# 폰트 설정 실행
configure_korean_font()

class ExperimentVisualizer:
    """
    RAG 실험 결과 시각화 클래스
    
    실험 결과를 분석하고 시각화하는 다양한 메서드 제공
    """
    
    def __init__(self, results_dir: str = './experiment_results'):
        """
        초기화
        
        Args:
            results_dir: 실험 결과가 저장된 디렉토리
        """
        self.results_dir = results_dir
        self.experiments = self._load_experiments()
        self.experiment_df = self._create_experiment_dataframe()
        
        # 시각화 설정
        plt.style.use('seaborn-v0_8-whitegrid')
        
    def _load_experiments(self) -> List[Dict[str, Any]]:
        """실험 결과 로드"""
        experiments = []
        
        # 결과 디렉토리 리스트
        experiment_dirs = [
            d for d in os.listdir(self.results_dir) 
            if os.path.isdir(os.path.join(self.results_dir, d))
            and not d.startswith(".")  # 숨김 디렉토리 제외
            and not d == "logs"  # 로그 디렉토리 제외
        ]
        
        for exp_dir in sorted(experiment_dirs):
            # 결과 파일 경로
            results_path = os.path.join(self.results_dir, exp_dir, 'results.json')
            
            if os.path.exists(results_path):
                try:
                    with open(results_path, 'r', encoding='utf-8') as f:
                        experiment = json.load(f)
                        experiments.append(experiment)
                except Exception as e:
                    print(f"결과 파일 로드 실패: {results_path} - {str(e)}")
        
        print(f"{len(experiments)}개 실험 결과 로드됨")
        return experiments
    
    def _create_experiment_dataframe(self) -> pd.DataFrame:
        """실험 데이터를 DataFrame으로 변환"""
        if not self.experiments:
            return pd.DataFrame()
            
        experiment_data = []
        
        for exp in self.experiments:
            # 기본 정보
            exp_data = {
                "experiment_id": exp.get("experiment_id", ""),
                "name": exp.get("name", ""),
                "timestamp": exp.get("timestamp", "")
            }
            
            # 메트릭 정보
            metrics = exp.get("metrics", {})
            for metric_name, metric_value in metrics.items():
                exp_data[f"metric_{metric_name}"] = metric_value
                
            # 구성 정보
            config = exp.get("config", {})
            for key, value in config.items():
                if isinstance(value, (str, int, float, bool)):
                    exp_data[f"config_{key}"] = value
            
            experiment_data.append(exp_data)
        
        return pd.DataFrame(experiment_data)
    
    def _get_parameter_values(self, param_name: str) -> List:
        """특정 파라미터의 모든 고유 값 추출"""
        col_name = f"config_{param_name}"
        if col_name not in self.experiment_df.columns:
            return []
            
        return sorted(self.experiment_df[col_name].unique())
    
    def generate_performance_comparison(self, 
                                       metric: str = "metric_avg_top_similarity",
                                       save_path: Optional[str] = None,
                                       figsize: Tuple[int, int] = (10, 5)) -> plt.Figure:
        """
        실험 간 성능 비교 차트 생성
        
        Args:
            metric: 비교할 메트릭 컬럼명
            save_path: 저장할 경로 (None이면 저장 안함)
            figsize: 그림 크기
            
        Returns:
            matplotlib Figure 객체
        """
        if self.experiment_df.empty:
            print("실험 데이터가 없습니다.")
            return plt.figure()
        
        # 메트릭 컬럼이 없는 경우
        if metric not in self.experiment_df.columns:
            print(f"메트릭 '{metric}'이 데이터에 없습니다.")
            available_metrics = [col for col in self.experiment_df.columns if col.startswith("metric_")]
            print(f"사용 가능한 메트릭: {available_metrics}")
            return plt.figure()
        
        # 실험 이름이 너무 길 경우 줄임
        self.experiment_df["short_name"] = self.experiment_df["name"].apply(
            lambda x: x[:30] + "..." if len(x) > 30 else x
        )
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 메트릭 추출 및 정렬
        display_df = self.experiment_df.sort_values(by=metric, ascending=False)
        
        # 성능 차트
        sns.barplot(x="short_name", y=metric, data=display_df, ax=ax)
        ax.set_title(safe_text(f"실험별 {metric.replace('metric_', '')} 비교"), fontsize=14)
        ax.set_xlabel(safe_text("실험"), fontsize=12)
        ax.set_ylabel(safe_text(metric.replace("metric_", "").replace("_", " ").title()), fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # 값 표시
        for i, v in enumerate(display_df[metric]):
            ax.text(i, v, f"{v:.4f}", ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"차트가 저장됨: {save_path}")
        
        return fig
    
    def generate_parameter_impact(self, 
                                 param_name: str, 
                                 metric: str = "metric_avg_top_similarity",
                                 save_path: Optional[str] = None,
                                 figsize: Tuple[int, int] = (8, 5)) -> plt.Figure:
        """
        특정 파라미터가 성능에 미치는 영향 시각화
        
        Args:
            param_name: 분석할 파라미터 이름
            metric: 분석할 메트릭
            save_path: 저장할 경로 (None이면 저장 안함)
            figsize: 그림 크기
            
        Returns:
            matplotlib Figure 객체
        """
        param_col = f"config_{param_name}"
        
        if param_col not in self.experiment_df.columns:
            print(f"파라미터 '{param_name}'이 데이터에 없습니다.")
            available_params = [col.replace("config_", "") for col in self.experiment_df.columns 
                               if col.startswith("config_")]
            print(f"사용 가능한 파라미터: {available_params}")
            return plt.figure()
            
        if metric not in self.experiment_df.columns:
            print(f"메트릭 '{metric}'이 데이터에 없습니다.")
            available_metrics = [col for col in self.experiment_df.columns if col.startswith("metric_")]
            print(f"사용 가능한 메트릭: {available_metrics}")
            return plt.figure()
        
        # 파라미터 값 기준으로 그룹화
        grouped_df = self.experiment_df.groupby(param_col)[metric].mean().reset_index()
        grouped_df = grouped_df.sort_values(by=param_col)
        
        # 시각화
        fig, ax = plt.subplots(figsize=figsize)
        
        # 수치형 파라미터인 경우 선 그래프
        if pd.api.types.is_numeric_dtype(grouped_df[param_col]):
            sns.lineplot(x=param_col, y=metric, data=grouped_df, marker='o', linewidth=2, markersize=8, ax=ax)
            
            # 최적값 표시
            best_idx = grouped_df[metric].idxmax()
            best_x = grouped_df.iloc[best_idx][param_col]
            best_y = grouped_df.iloc[best_idx][metric]
            ax.scatter([best_x], [best_y], color='red', s=100, zorder=5)
            ax.annotate(safe_text(f"최적값: {best_x}"), 
                     xy=(best_x, best_y), 
                     xytext=(0, 10),
                     textcoords='offset points',
                     ha='center', fontsize=10)
        else:
            # 범주형 파라미터인 경우 막대 그래프
            sns.barplot(x=param_col, y=metric, data=grouped_df, ax=ax)
            
            # 값 표시
            for i, v in enumerate(grouped_df[metric]):
                ax.text(i, v, f"{v:.4f}", ha='center', va='bottom', fontsize=10)
        
        ax.set_title(safe_text(f"{param_name}이 {metric.replace('metric_', '')}에 미치는 영향"), fontsize=14)
        ax.set_xlabel(safe_text(param_name), fontsize=12)
        ax.set_ylabel(safe_text(metric.replace("metric_", "").replace("_", " ").title()), fontsize=12)
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"차트가 저장됨: {save_path}")
        
        return fig
    
    def generate_correlation_heatmap(self,
                                    save_path: Optional[str] = None,
                                    figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
        """
        파라미터와 메트릭 간의 상관관계 히트맵 생성
        
        Args:
            save_path: 저장할 경로 (None이면 저장 안함)
            figsize: 그림 크기
            
        Returns:
            matplotlib Figure 객체
        """
        if self.experiment_df.empty:
            print("실험 데이터가 없습니다.")
            return plt.figure()
        
        # 수치형 파라미터와 메트릭 컬럼 선택
        numeric_cols = [col for col in self.experiment_df.columns 
                      if (col.startswith("config_") or col.startswith("metric_"))
                      and pd.api.types.is_numeric_dtype(self.experiment_df[col])]
        
        if not numeric_cols:
            print("수치형 파라미터 또는 메트릭이 없습니다.")
            return plt.figure()
        
        # 컬럼명 가독성 향상
        col_rename = {col: col.replace("config_", "").replace("metric_", "") for col in numeric_cols}
        
        # 상관관계 계산
        corr_df = self.experiment_df[numeric_cols].corr()
        corr_df = corr_df.rename(columns=col_rename, index=col_rename)
        
        # 시각화
        fig, ax = plt.subplots(figsize=figsize)
        mask = np.triu(np.ones_like(corr_df, dtype=bool))
        
        cmap = sns.diverging_palette(230, 20, as_cmap=True)
        sns.heatmap(corr_df, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
                   annot=True, fmt=".2f", square=True, linewidths=.5, ax=ax)
        
        ax.set_title(safe_text("파라미터와 메트릭 간 상관관계"), fontsize=16)
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"차트가 저장됨: {save_path}")
        
        return fig
    
    def generate_similarity_distribution(self,
                                        experiment_id: Optional[str] = None,
                                        save_path: Optional[str] = None,
                                        figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        유사도 분포 히스토그램 생성
        
        Args:
            experiment_id: 분석할 실험 ID (None이면 가장 좋은 실험 선택)
            save_path: 저장할 경로 (None이면 저장 안함)
            figsize: 그림 크기
            
        Returns:
            matplotlib Figure 객체
        """
        if not self.experiments:
            print("실험 데이터가 없습니다.")
            return plt.figure()
        
        # 실험 선택 (ID 없으면 가장 좋은 실험)
        target_exp = None
        
        if experiment_id:
            for exp in self.experiments:
                if exp.get("experiment_id") == experiment_id:
                    target_exp = exp
                    break
                    
            if not target_exp:
                print(f"실험 ID '{experiment_id}'를 찾을 수 없습니다.")
                return plt.figure()
        else:
            # 가장 높은 유사도를 가진 실험 찾기
            best_exp = None
            best_score = -1
            
            for exp in self.experiments:
                score = exp.get("metrics", {}).get("avg_top_similarity", 0)
                if score > best_score:
                    best_score = score
                    best_exp = exp
                    
            target_exp = best_exp
        
        # 유사도 추출
        all_similarities = []
        query_results = target_exp.get("query_results", [])
        
        for query_result in query_results:
            retrieval_results = query_result.get("retrieval_results", [])
            similarities = [r.get("similarity", 0) for r in retrieval_results]
            all_similarities.extend(similarities)
        
        if not all_similarities:
            print("유사도 데이터가 없습니다.")
            return plt.figure()
        
        # 시각화
        fig, ax = plt.subplots(figsize=figsize)
        
        sns.histplot(all_similarities, bins=20, kde=True, ax=ax)
        
        ax.set_title(safe_text(f"유사도 분포 - {target_exp.get('name')}"), fontsize=14)
        ax.set_xlabel(safe_text("유사도 점수"), fontsize=12)
        ax.set_ylabel(safe_text("빈도"), fontsize=12)
        
        # 통계 추가
        stats_text = (
            f"{safe_text('평균')}: {np.mean(all_similarities):.4f}\n"
            f"{safe_text('중앙값')}: {np.median(all_similarities):.4f}\n"
            f"{safe_text('최소값')}: {np.min(all_similarities):.4f}\n"
            f"{safe_text('최대값')}: {np.max(all_similarities):.4f}\n"
            f"{safe_text('표준편차')}: {np.std(all_similarities):.4f}"
        )
        
        props = dict(boxstyle='round', facecolor='white', alpha=0.7)
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
              verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"차트가 저장됨: {save_path}")
        
        return fig
    
    def generate_query_performance_breakdown(self,
                                           experiment_id: Optional[str] = None,
                                           top_n_queries: int = 10,
                                           save_path: Optional[str] = None,
                                           figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        쿼리별 성능 분석 차트 생성
        
        Args:
            experiment_id: 분석할 실험 ID (None이면 가장 좋은 실험 선택)
            top_n_queries: 표시할 상위 쿼리 수
            save_path: 저장할 경로 (None이면 저장 안함)
            figsize: 그림 크기
            
        Returns:
            matplotlib Figure 객체
        """
        if not self.experiments:
            print("실험 데이터가 없습니다.")
            return plt.figure()
        
        # 실험 선택 (ID 없으면 가장 좋은 실험)
        target_exp = None
        
        if experiment_id:
            for exp in self.experiments:
                if exp.get("experiment_id") == experiment_id:
                    target_exp = exp
                    break
                    
            if not target_exp:
                print(f"실험 ID '{experiment_id}'를 찾을 수 없습니다.")
                return plt.figure()
        else:
            # 가장 높은 유사도를 가진 실험 찾기
            best_exp = None
            best_score = -1
            
            for exp in self.experiments:
                score = exp.get("metrics", {}).get("avg_top_similarity", 0)
                if score > best_score:
                    best_score = score
                    best_exp = exp
                    
            target_exp = best_exp
        
        # 쿼리별 성능 데이터 추출
        query_data = []
        
        for query_result in target_exp.get("query_results", []):
            query = query_result.get("query", "")
            top_similarity = query_result.get("metrics", {}).get("top_chunk_similarity", 0)
            avg_similarity = query_result.get("metrics", {}).get("avg_similarity", 0)
            exec_time = query_result.get("metrics", {}).get("execution_time", 0)
            
            query_data.append({
                "query": query[:50] + "..." if len(query) > 50 else query,
                "top_similarity": top_similarity,
                "avg_similarity": avg_similarity,
                "execution_time": exec_time
            })
        
        if not query_data:
            print("쿼리 성능 데이터가 없습니다.")
            return plt.figure()
        
        # DataFrame 변환
        query_df = pd.DataFrame(query_data)
        
        # 상위 유사도 기준 정렬 및 필터링
        query_df = query_df.sort_values(by="top_similarity", ascending=False).head(top_n_queries)
        
        # 시각화
        fig, ax = plt.subplots(figsize=figsize)
        
        x = range(len(query_df))
        
        ax.bar(x, query_df["avg_similarity"], width=0.4, label=safe_text("평균 유사도"), align="edge")
        ax.bar([i+0.4 for i in x], query_df["top_similarity"], width=0.4, label=safe_text("최고 유사도"), align="edge")
        
        ax.set_xticks([i+0.2 for i in x])
        ax.set_xticklabels(query_df["query"], rotation=45, ha="right")
        
        ax.set_title(safe_text(f"쿼리별 성능 - {target_exp.get('name')}"), fontsize=14)
        ax.set_xlabel(safe_text("쿼리"), fontsize=12)
        ax.set_ylabel(safe_text("유사도 점수"), fontsize=12)
        ax.legend()
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"차트가 저장됨: {save_path}")
        
        return fig
    
    def generate_dashboard(self, output_dir: str = "./reports") -> str:
        """
        종합 시각화 대시보드 HTML 생성
        
        Args:
            output_dir: 결과물 저장 디렉토리
            
        Returns:
            생성된 HTML 파일 경로
        """
        if not self.experiments:
            print("실험 데이터가 없습니다.")
            return ""
            
        # 결과 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 시각화 생성 및 저장
        vis_dir = os.path.join(output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # 1. 성능 비교 차트
        perf_path = os.path.join(vis_dir, "performance_comparison.png")
        self.generate_performance_comparison(save_path=perf_path)
        
        # 2. 파라미터 영향 차트 (청크 크기)
        chunk_path = os.path.join(vis_dir, "chunk_size_impact.png")
        self.generate_parameter_impact("chunk_size", save_path=chunk_path)
        
        # 3. 파라미터 영향 차트 (임베딩 모델)
        embed_path = os.path.join(vis_dir, "embedding_model_impact.png")
        self.generate_parameter_impact("embedding_model", save_path=embed_path)
        
        # 4. 상관관계 히트맵
        corr_path = os.path.join(vis_dir, "correlation_heatmap.png")
        self.generate_correlation_heatmap(save_path=corr_path)
        
        # 5. 유사도 분포
        dist_path = os.path.join(vis_dir, "similarity_distribution.png")
        self.generate_similarity_distribution(save_path=dist_path)
        
        # 6. 쿼리별 성능
        query_path = os.path.join(vis_dir, "query_performance.png")
        self.generate_query_performance_breakdown(save_path=query_path)
        
        # HTML 생성
        html_path = os.path.join(output_dir, "rag_experiment_dashboard.html")
        
        # 영어 제목으로 대체 (한글 폰트 문제 방지)
        title = safe_text("RAG 실험 결과 대시보드")
        section1 = safe_text("1. 실험 성능 비교")
        section2 = safe_text("2. 파라미터 영향 분석") 
        section3 = safe_text("3. 파라미터 간 상관관계")
        section4 = safe_text("4. 유사도 분포 분석")
        section5 = safe_text("5. 쿼리별 성능 분석")
        section6 = safe_text("6. 실험 요약 테이블")
        
        column_id = safe_text("실험 ID")
        column_name = safe_text("이름")
        column_topsim = safe_text("최고 유사도")
        column_avgsim = safe_text("평균 유사도")
        column_exectime = safe_text("실행 시간")
        column_params = safe_text("주요 파라미터")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .section {{ margin-bottom: 30px; }}
                .chart {{ margin: 20px 0; text-align: center; }}
                .chart img {{ 
                    max-width: 100%; 
                    height: auto; 
                    width: auto;
                    max-height: 80vh; 
                    object-fit: contain; 
                    border: 1px solid #ddd; 
                }}
                table {{ border-collapse: collapse; width: 100%; overflow-x: auto; display: block; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                
                @media (max-width: 768px) {{
                    body {{ margin: 10px; }}
                    .chart img {{ max-height: 50vh; }}
                    h1 {{ font-size: 24px; }}
                    h2 {{ font-size: 20px; }}
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p>{safe_text('생성 시간')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="section">
                <h2>{section1}</h2>
                <div class="chart">
                    <img src="visualizations/performance_comparison.png" alt="{safe_text('성능 비교')}">
                </div>
            </div>
            
            <div class="section">
                <h2>{section2}</h2>
                <div class="chart">
                    <img src="visualizations/chunk_size_impact.png" alt="{safe_text('청크 크기 영향')}">
                </div>
                <div class="chart">
                    <img src="visualizations/embedding_model_impact.png" alt="{safe_text('임베딩 모델 영향')}">
                </div>
            </div>
            
            <div class="section">
                <h2>{section3}</h2>
                <div class="chart">
                    <img src="visualizations/correlation_heatmap.png" alt="{safe_text('상관관계 히트맵')}">
                </div>
            </div>
            
            <div class="section">
                <h2>{section4}</h2>
                <div class="chart">
                    <img src="visualizations/similarity_distribution.png" alt="{safe_text('유사도 분포')}">
                </div>
            </div>
            
            <div class="section">
                <h2>{section5}</h2>
                <div class="chart">
                    <img src="visualizations/query_performance.png" alt="{safe_text('쿼리별 성능')}">
                </div>
            </div>
            
            <div class="section">
                <h2>{section6}</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <tr>
                            <th>{column_id}</th>
                            <th>{column_name}</th>
                            <th>{column_topsim}</th>
                            <th>{column_avgsim}</th>
                            <th>{column_exectime}</th>
                            <th>{column_params}</th>
                        </tr>
        """
        
        # 실험 요약 테이블 추가
        for exp in self.experiments:
            exp_id = exp.get("experiment_id", "")
            name = exp.get("name", "")
            top_sim = exp.get("metrics", {}).get("max_top_similarity", 0)
            avg_sim = exp.get("metrics", {}).get("avg_similarity", 0)
            exec_time = exp.get("metrics", {}).get("total_execution_time", 0)
            
            config = exp.get("config", {})
            main_params = f"{safe_text('청크')}: {config.get('chunk_size', '-')}, {safe_text('모델')}: {config.get('embedding_model', '-')}"
            
            html_content += f"""
                        <tr>
                            <td>{exp_id}</td>
                            <td>{name}</td>
                            <td>{top_sim:.4f}</td>
                            <td>{avg_sim:.4f}</td>
                            <td>{exec_time:.2f}{safe_text('초')}</td>
                            <td>{main_params}</td>
                        </tr>
            """
        
        html_content += """
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"대시보드가 생성됨: {html_path}")
        return html_path


def generate_and_save_visualizations(results_dir: str, output_dir: str):
    """
    실험 결과 시각화 생성 및 저장
    
    Args:
        results_dir: 실험 결과 디렉토리
        output_dir: 출력 디렉토리
    """
    # 시각화 클래스 초기화
    visualizer = ExperimentVisualizer(results_dir)
    
    # 대시보드 생성
    dashboard_path = visualizer.generate_dashboard(output_dir)
    
    if dashboard_path:
        print(f"시각화 생성 완료. 대시보드: {dashboard_path}")
    else:
        print("시각화 생성 실패.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 실험 결과 시각화")
    parser.add_argument("--results-dir", default="./experiment_results", 
                      help="실험 결과 디렉토리")
    parser.add_argument("--output-dir", default="./reports", 
                      help="출력 디렉토리")
    
    args = parser.parse_args()
    
    generate_and_save_visualizations(args.results_dir, args.output_dir) 