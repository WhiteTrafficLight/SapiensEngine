"""
Opponent analysis functionality for debate participant agent.
Handles analyzing opponent arguments and managing opponent data.
"""

import time
from typing import Dict, List, Any, Optional
import logging

from .argument_extractor import ArgumentExtractor
from .vulnerability_scorer import VulnerabilityScorer

logger = logging.getLogger(__name__)


class OpponentAnalyzer:
    """Handles opponent analysis and argument scoring."""
    
    def __init__(self, llm_manager, agent_id: str, philosopher_name: str, philosopher_data: Dict[str, Any]):
        """
        Initialize the OpponentAnalyzer.
        
        Args:
            llm_manager: LLM manager for generating responses
            agent_id: Agent identifier
            philosopher_name: Name of the philosopher
            philosopher_data: Philosopher-specific data
        """
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.philosopher_name = philosopher_name
        self.philosopher_data = philosopher_data
        
        # Initialize sub-components
        self.argument_extractor = ArgumentExtractor(llm_manager, agent_id, philosopher_name)
        self.vulnerability_scorer = VulnerabilityScorer(llm_manager, agent_id, philosopher_name, philosopher_data)
        
        # Data storage
        self.opponent_arguments = {}
        self.opponent_key_points = []
        self.opponent_details = {}
    
    def analyze_and_score_arguments(self, opponent_response: str, speaker_id: str) -> Dict[str, Any]:
        """
        상대방 발언에서 논지를 추출하고 스코어링
        
        Args:
            opponent_response: 상대방 발언 텍스트
            speaker_id: 발언자 ID
            
        Returns:
            분석 결과 (논지 목록, 스코어, 취약점 등)
        """
        try:
            # 1. 논지 추출
            arguments = self.argument_extractor.extract_arguments_from_response(opponent_response, speaker_id)
            
            # 2. 각 논지별 스코어링
            scored_arguments = []
            for arg in arguments:
                score_data = self.vulnerability_scorer.score_single_argument(arg, opponent_response)
                scored_arguments.append({
                    "argument": arg,
                    "scores": score_data,
                    "vulnerability_rank": score_data.get("final_vulnerability", 0.0)  # 개선된 취약성 사용
                })
            
            # 3. 취약점 순으로 정렬
            scored_arguments.sort(key=lambda x: x["vulnerability_rank"], reverse=True)
            
            # 4. 상대방 논지 저장
            if speaker_id not in self.opponent_arguments:
                self.opponent_arguments[speaker_id] = []
            self.opponent_arguments[speaker_id].extend(scored_arguments)
            
            return {
                "status": "success",
                "speaker_id": speaker_id,
                "arguments_count": len(arguments),
                "scored_arguments": scored_arguments[:3],  # 상위 3개만 반환
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing opponent arguments: {str(e)}")
            return {"error": str(e)}
    
    def analyze_user_arguments(self, user_response: str, speaker_id: str) -> Dict[str, Any]:
        """
        유저 입력을 분석하여 논지를 추출하고 취약성을 평가합니다.
        
        Args:
            user_response: 유저의 입력 텍스트  
            speaker_id: 유저 ID
            
        Returns:
            Dict: 분석 결과 (기존 analyze_and_score_arguments와 동일한 포맷)
        """
        try:
            logger.info(f"🎯 [{self.agent_id}] 유저 {speaker_id} 논지 분석 시작")
            
            # 1단계: 유저 입력에서 논지 추출
            extracted_arguments = self.argument_extractor.extract_arguments_from_user_input(user_response, speaker_id)
            
            if not extracted_arguments:
                logger.warning(f"⚠️ [{self.agent_id}] 유저 {speaker_id}에서 논지를 추출하지 못함")
                return {
                    'opponent_arguments': {speaker_id: []},
                    'total_arguments': 0,
                    'analysis_summary': f"유저 {speaker_id}의 논지 추출 실패"
                }
            
            # 2단계: 각 추출된 논지에 대해 취약성 점수 계산
            analyzed_arguments = []
            total_vulnerability_score = 0.0
            
            for argument in extracted_arguments:
                try:
                    # 기존 score_single_argument 메서드 활용
                    vulnerability_data = self.vulnerability_scorer.score_single_argument(argument, user_response)
                    
                    # 분석 결과 구성
                    analyzed_arg = {
                        'claim': argument['claim'],
                        'evidence': argument['evidence'], 
                        'reasoning': argument['reasoning'],
                        'assumptions': argument['assumptions'],
                        'vulnerability_score': vulnerability_data.get('final_vulnerability', 0.0),
                        'scores': vulnerability_data,
                        'source_text': argument.get('source_text', ''),
                        'argument_id': argument.get('argument_id', f"user_arg_{len(analyzed_arguments)}")
                    }
                    
                    analyzed_arguments.append(analyzed_arg)
                    total_vulnerability_score += vulnerability_data.get('final_vulnerability', 0.0)
                    
                    logger.info(f"📊 [{self.agent_id}] 유저 논지 '{argument['claim'][:50]}...' 취약성: {vulnerability_data.get('final_vulnerability', 0.0):.2f}")
                    
                except Exception as e:
                    logger.error(f"❌ [{self.agent_id}] 논지 분석 실패: {e}")
                    continue
            
            # 3단계: 결과 포맷팅 (기존 analyze_and_score_arguments와 동일한 구조)
            average_vulnerability = total_vulnerability_score / len(analyzed_arguments) if analyzed_arguments else 0.0
            
            analysis_result = {
                'opponent_arguments': {speaker_id: analyzed_arguments},
                'total_arguments': len(analyzed_arguments),
                'average_vulnerability': average_vulnerability,
                'analysis_summary': f"유저 {speaker_id}의 논지 {len(analyzed_arguments)}개 분석 완료 (평균 취약성: {average_vulnerability:.2f})"
            }
            
            # 4단계: 분석 결과 저장
            self.opponent_arguments[speaker_id] = analyzed_arguments
            
            logger.info(f"✅ [{self.agent_id}] 유저 {speaker_id} 논지 분석 완료: {len(analyzed_arguments)}개 논지, 평균 취약성 {average_vulnerability:.2f}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] 유저 논지 분석 실패: {e}")
            return {
                'opponent_arguments': {speaker_id: []},
                'total_arguments': 0,
                'analysis_summary': f"유저 {speaker_id} 분석 중 오류 발생: {str(e)}"
            }
    
    def extract_opponent_key_points(self, opponent_messages: List[Dict[str, Any]]) -> None:
        """
        상대방 발언에서 핵심 논점 추출하여 저장
        
        Args:
            opponent_messages: 상대방 발언 메시지들
        """
        key_points = self.argument_extractor.extract_opponent_key_points(opponent_messages)
        if key_points:
            self.opponent_key_points = key_points
            
            # 상대방별 상세 정보도 저장
            opponents_by_speaker = {}
            for msg in opponent_messages:
                speaker_id = msg.get("speaker_id", "unknown")
                text = msg.get("text", "").strip()
                if text:
                    if speaker_id not in opponents_by_speaker:
                        opponents_by_speaker[speaker_id] = []
                    opponents_by_speaker[speaker_id].append(text)
            
            self.opponent_details = {
                'speakers': list(opponents_by_speaker.keys()),
                'message_counts': {k: len(v) for k, v in opponents_by_speaker.items()}
            }
    
    def clear_opponent_data(self, speaker_id: str = None):
        """
        상대방 데이터 정리
        
        Args:
            speaker_id: 특정 발언자 ID (None이면 전체 정리)
        """
        if speaker_id:
            # 특정 상대방 데이터만 정리
            if speaker_id in self.opponent_arguments:
                del self.opponent_arguments[speaker_id]
            logger.info(f"[{self.agent_id}] Cleared opponent data for {speaker_id}")
        else:
            # 전체 상대방 데이터 정리
            self.opponent_arguments.clear()
            self.opponent_key_points.clear()
            self.opponent_details.clear()
            logger.info(f"[{self.agent_id}] Cleared all opponent data")
    
    def get_opponent_arguments(self, speaker_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        상대방 논지 데이터 반환
        
        Args:
            speaker_id: 특정 발언자 ID (None이면 전체 반환)
            
        Returns:
            상대방 논지 데이터
        """
        if speaker_id:
            return {speaker_id: self.opponent_arguments.get(speaker_id, [])}
        return self.opponent_arguments.copy()
    
    def get_opponent_key_points(self) -> List[str]:
        """상대방 핵심 논점 반환"""
        return self.opponent_key_points.copy()
    
    def get_opponent_details(self) -> Dict[str, Any]:
        """상대방 상세 정보 반환"""
        return self.opponent_details.copy()
    
    def update_my_key_points_from_core_arguments(self, core_arguments: List[Any]) -> List[str]:
        """
        자신의 core_arguments에서 my_key_points 업데이트
        
        Args:
            core_arguments: 핵심 논지 목록
            
        Returns:
            업데이트된 핵심 논점 목록
        """
        try:
            if core_arguments:
                # core_arguments가 딕셔너리 형태인 경우
                if isinstance(core_arguments[0], dict):
                    my_key_points = [
                        arg.get("argument", "") for arg in core_arguments
                        if arg.get("argument", "").strip()
                    ]
                # core_arguments가 문자열 리스트인 경우
                else:
                    my_key_points = [
                        str(arg) for arg in core_arguments
                        if str(arg).strip()
                    ]
                
                logger.info(f"[{self.agent_id}] Updated my_key_points from {len(core_arguments)} core arguments")
                return my_key_points
            else:
                logger.warning(f"[{self.agent_id}] No core_arguments available to update my_key_points")
                return []
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error updating my_key_points: {str(e)}")
            return [] 