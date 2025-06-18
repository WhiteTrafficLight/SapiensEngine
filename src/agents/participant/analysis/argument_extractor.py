"""
Argument extraction functionality for debate participant agent.
Handles extracting arguments from opponent responses and user input.
"""

import json
import re
import time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ArgumentExtractor:
    """Handles argument extraction from various sources."""
    
    def __init__(self, llm_manager, agent_id: str, philosopher_name: str):
        """
        Initialize the ArgumentExtractor.
        
        Args:
            llm_manager: LLM manager for generating responses
            agent_id: Agent identifier
            philosopher_name: Name of the philosopher
        """
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.philosopher_name = philosopher_name
    
    def extract_arguments_from_response(self, response: str, speaker_id: str) -> List[Dict[str, Any]]:
        """
        발언에서 핵심 논지들을 추출
        
        Args:
            response: 발언 텍스트
            speaker_id: 발언자 ID
            
        Returns:
            추출된 논지 목록
        """
        system_prompt = """
You are an expert debate analyst. Your task is to extract key arguments from a speaker's statement.
Identify the main claims, supporting evidence, and logical structure.
Return ONLY valid JSON format.
"""

        user_prompt = f"""
Analyze this debate statement and extract the key arguments:

STATEMENT: "{response}"

Extract the main arguments and return ONLY a valid JSON array:
[
  {{
    "claim": "main claim text",
    "evidence": "supporting evidence",
    "reasoning": "logical reasoning",
    "assumptions": ["assumption1", "assumption2"],
    "argument_type": "logical"
  }}
]

IMPORTANT: Return ONLY the JSON array, no other text.
"""
        
        try:
            response_text = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=1200
            )
            
            # JSON 파싱 개선
            parsed_data = self._parse_json_response(response_text)
            
            if parsed_data:
                # 데이터 검증 및 정리
                validated_arguments = []
                for arg in parsed_data:
                    if isinstance(arg, dict):
                        validated_arg = {
                            "claim": str(arg.get('claim', 'Unknown claim')),
                            "evidence": str(arg.get('evidence', 'No evidence provided')),
                            "reasoning": str(arg.get('reasoning', 'No reasoning provided')),
                            "assumptions": arg.get('assumptions', []) if isinstance(arg.get('assumptions'), list) else [],
                            "argument_type": str(arg.get('argument_type', 'logical'))
                        }
                        validated_arguments.append(validated_arg)
                
                return validated_arguments if validated_arguments else self._get_fallback_argument(response)
            else:
                return self._get_fallback_argument(response)
                
        except Exception as e:
            logger.error(f"Error extracting arguments: {str(e)}")
            return self._get_fallback_argument(response)
    
    def extract_arguments_from_user_input(self, user_response: str, speaker_id: str) -> List[Dict[str, Any]]:
        """
        유저 입력에서 LLM을 사용해 논지를 추출합니다.
        
        Args:
            user_response: 유저의 입력 텍스트
            speaker_id: 유저 ID
            
        Returns:
            List[Dict]: 추출된 논지들 (최대 3개)
        """
        try:
            logger.info(f"🔍 [{self.agent_id}] 유저 {speaker_id}의 논지 추출 시작")
            
            system_prompt = "You are an expert debate analyst. Extract key arguments from user input in Korean."
            
            user_prompt = f"""
당신은 토론 분석 전문가입니다. 다음 사용자의 발언에서 핵심 논지들을 추출해주세요.

사용자 발언:
{user_response}

요구사항:
1. 핵심 논지를 최대 3개까지 추출
2. 각 논지는 명확한 주장과 근거를 포함해야 함
3. 너무 세부적이지 않고 토론에서 공격할 수 있는 수준의 논지여야 함

다음 JSON 형식으로 반환해주세요:
{{
  "arguments": [
    {{
      "claim": "논지의 핵심 주장",
      "evidence": "제시된 근거나 증거",
      "reasoning": "논리적 추론 과정",
      "assumptions": ["기본 가정들"]
    }}
  ]
}}

논지가 3개 미만이라면 실제 개수만 반환하세요.
"""

            # llm_manager 사용하여 응답 생성
            response_text = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=1000,
                temperature=0.3
            )
            
            # JSON 파싱
            try:
                # 마크다운 코드 블록 제거
                cleaned_response = self._clean_json_response(response_text)
                parsed_data = json.loads(cleaned_response)
                extracted_arguments = parsed_data.get("arguments", [])
                
                logger.info(f"✅ [{self.agent_id}] 유저 {speaker_id}의 논지 {len(extracted_arguments)}개 추출 완료")
                
                # 기존 포맷에 맞게 변환
                formatted_arguments = []
                for i, arg in enumerate(extracted_arguments):
                    formatted_arg = {
                        'claim': arg.get('claim', ''),
                        'evidence': arg.get('evidence', ''),
                        'reasoning': arg.get('reasoning', ''),
                        'assumptions': arg.get('assumptions', []),
                        'source_text': user_response,  # 원본 텍스트 보존
                        'argument_id': f"user_arg_{i+1}"
                    }
                    formatted_arguments.append(formatted_arg)
                
                return formatted_arguments
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ [{self.agent_id}] JSON 파싱 실패: {e}")
                logger.error(f"정리된 응답: {cleaned_response if 'cleaned_response' in locals() else response_text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] 유저 논지 추출 실패: {e}")
            return []
    
    def extract_opponent_key_points(self, opponent_messages: List[Dict[str, Any]]) -> List[str]:
        """
        상대방 발언에서 핵심 논점 추출하여 반환
        다중 상대방 지원: 각 상대방별로 논점을 구분하여 저장
        
        Args:
            opponent_messages: 상대방 발언 메시지들 (여러 상대방 포함 가능)
            
        Returns:
            추출된 핵심 논점 목록
        """
        if not opponent_messages:
            logger.warning(f"[{self.agent_id}] No opponent messages to extract key points from")
            return []
        
        try:
            # 상대방별로 메시지 그룹화
            opponents_by_speaker = {}
            for msg in opponent_messages:
                speaker_id = msg.get("speaker_id", "unknown")
                text = msg.get("text", "").strip()
                if text:
                    if speaker_id not in opponents_by_speaker:
                        opponents_by_speaker[speaker_id] = []
                    opponents_by_speaker[speaker_id].append(text)
            
            if not opponents_by_speaker:
                logger.warning(f"[{self.agent_id}] No meaningful opponent text found")
                return []
            
            # 모든 상대방의 논점을 통합하여 추출
            all_opponent_text = ""
            speaker_summaries = []
            
            for speaker_id, texts in opponents_by_speaker.items():
                speaker_text = "\n".join(texts)
                all_opponent_text += f"\n\n[{speaker_id}]:\n{speaker_text}"
                speaker_summaries.append(f"- {speaker_id}: {len(texts)} statements")
            
            logger.info(f"[{self.agent_id}] Processing arguments from {len(opponents_by_speaker)} opponents: {', '.join(opponents_by_speaker.keys())}")
            
            # LLM을 사용하여 통합 핵심 논점 추출
            system_prompt = """
You are an expert debate analyst. Extract the key arguments and main points from multiple opponents' statements.
Focus on identifying:
1. Core claims and assertions from all opponents
2. Main supporting evidence or reasoning
3. Key logical structures
4. Common themes across different speakers
5. Unique arguments from individual speakers

Provide a comprehensive list that captures the essence of the opposition's position.
"""
            
            user_prompt = f"""
Analyze the following debate statements from multiple opponents and extract their key arguments:

OPPONENTS' STATEMENTS:
{all_opponent_text}

SPEAKER SUMMARY:
{chr(10).join(speaker_summaries)}

Extract 4-7 key points that represent the opponents' main arguments across all speakers. 
Include both common themes and unique individual arguments.

Format your response as a JSON list of strings:
["Key point 1", "Key point 2", "Key point 3", ...]

Each key point should be:
- A concise summary (1-2 sentences) of a major argument or claim
- Representative of the overall opposition position
- Include attribution if it's a unique argument from a specific speaker
"""
            
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                llm_model="gpt-4o",
                max_tokens=1500
            )
            
            # JSON 파싱
            json_pattern = r'\[.*?\]'
            json_match = re.search(json_pattern, response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                key_points = json.loads(json_str)
                
                if isinstance(key_points, list):
                    logger.info(f"[{self.agent_id}] Extracted {len(key_points)} opponent key points from {len(opponents_by_speaker)} speakers")
                    
                    # 디버깅용 로그
                    for i, point in enumerate(key_points, 1):
                        logger.info(f"[{self.agent_id}] Opponent point {i}: {point[:100]}...")
                    
                    return key_points
                else:
                    logger.warning(f"[{self.agent_id}] Invalid key points format: {type(key_points)}")
                    return []
            else:
                logger.warning(f"[{self.agent_id}] Failed to parse key points from response: {response[:100]}...")
                return []
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error extracting opponent key points: {str(e)}")
            return []
    
    def extract_key_concept(self, text: str) -> str:
        """
        텍스트에서 핵심 개념을 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 핵심 개념
        """
        try:
            # 간단한 키워드 추출 로직
            words = text.split()
            
            # 불용어 제거 (간단한 버전)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'cannot', 'this', 'that', 'these', 'those'}
            
            # 의미있는 단어들 필터링
            meaningful_words = [word.lower().strip('.,!?;:') for word in words 
                              if len(word) > 3 and word.lower() not in stop_words]
            
            # 가장 빈번한 단어 반환 (간단한 방법)
            if meaningful_words:
                word_freq = {}
                for word in meaningful_words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                
                # 가장 빈번한 단어 반환
                most_common = max(word_freq.items(), key=lambda x: x[1])
                return most_common[0]
            
            # 폴백: 첫 번째 의미있는 단어
            return meaningful_words[0] if meaningful_words else "concept"
            
        except Exception as e:
            logger.error(f"Error extracting key concept: {str(e)}")
            return "concept"
    
    def _parse_json_response(self, response_text: str) -> Optional[List[Dict[str, Any]]]:
        """JSON 응답을 파싱하는 헬퍼 메서드"""
        try:
            # JSON 파싱 개선
            json_patterns = [
                r'\[[\s\S]*?\]',  # 배열 형태
                r'\{[\s\S]*?\}',  # 객체 형태
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response_text, re.DOTALL)
                for match in matches:
                    try:
                        # JSON 문자열 정리
                        clean_json = match.strip()
                        # 잘못된 문자 제거
                        clean_json = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean_json)
                        
                        parsed_data = json.loads(clean_json)
                        
                        # 배열이 아니면 배열로 감싸기
                        if not isinstance(parsed_data, list):
                            parsed_data = [parsed_data]
                        
                        return parsed_data
                    except json.JSONDecodeError:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            return None
    
    def _clean_json_response(self, response_text: str) -> str:
        """JSON 응답을 정리하는 헬퍼 메서드"""
        cleaned_response = response_text.strip()
        
        # ```json과 ``` 제거
        if '```json' in cleaned_response:
            cleaned_response = cleaned_response.replace('```json', '').replace('```', '').strip()
        elif '```' in cleaned_response:
            cleaned_response = cleaned_response.replace('```', '').strip()
        
        return cleaned_response
    
    def _get_fallback_argument(self, response: str) -> List[Dict[str, Any]]:
        """JSON 파싱 실패 시 기본 논지 구조 반환"""
        return [{
            "claim": response[:200] + "..." if len(response) > 200 else response,
            "evidence": "Not extracted due to parsing error",
            "reasoning": "Not analyzed due to parsing error",
            "assumptions": [],
            "argument_type": "unknown"
        }] 