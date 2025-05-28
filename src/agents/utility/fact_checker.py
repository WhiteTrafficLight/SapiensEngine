"""
팩트 체커(Fact Checker) 유틸리티 에이전트 모듈

대화 중 제시된 정보의 정확성을 검증하는 유틸리티 에이전트
"""

from typing import Dict, Any, List, Optional, Tuple
from src.agents.base.agent import Agent
from src.rag.retrieval.web_retriever import WebSearchRetriever
from src.models.llm.llm_manager import LLMManager


class FactCheckerAgent(Agent):
    """
    팩트 체커 에이전트
    
    대화 중 제시된 정보를 검증하고 피드백을 제공
    """
    
    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        """
        팩트 체커 에이전트 초기화
        
        Args:
            agent_id: 고유 식별자
            name: 에이전트 이름
            config: 설정 매개변수
        """
        super().__init__(agent_id, name, config)
        
        # 검증 설정
        self.check_frequency = config.get("parameters", {}).get("check_frequency", 0.5)
        self.web_search_enabled = config.get("parameters", {}).get("web_search_enabled", True)
        self.rag_enabled = config.get("parameters", {}).get("rag_enabled", True)
        
        # 외부 컴포넌트 (실제 구현에서는 의존성 주입 방식으로 설정)
        self.web_retriever = None
        self.llm_manager = None
        
        # 상태 초기화
        self.state.update({
            "verified_facts": [],
            "corrections": [],
            "pending_claims": [],
            "verification_history": []
        })
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        입력 처리 및 팩트 체크 수행
        
        Args:
            input_data: 처리할 입력 데이터 (대화 상태, 검증할 메시지 등)
            
        Returns:
            검증 결과
        """
        message = input_data.get("message")
        force_check = input_data.get("force_check", False)
        
        if not message:
            return {"result": "skipped", "reason": "no_message"}
        
        # 검증 빈도에 따라 수행 여부 결정 (force_check이 True면 무조건 수행)
        import random
        if not force_check and random.random() > self.check_frequency:
            return {"result": "skipped", "reason": "frequency"}
        
        # 주장 추출
        claims = self._extract_claims(message.content)
        
        if not claims:
            return {"result": "skipped", "reason": "no_claims"}
        
        # 주장 검증
        verification_results = []
        for claim in claims:
            result = self._verify_claim(claim)
            verification_results.append(result)
            self._update_verification_history(claim, result)
        
        # 피드백 생성
        feedback = self._generate_feedback(verification_results)
        
        return {
            "result": "completed",
            "claims": claims,
            "verification_results": verification_results,
            "feedback": feedback
        }
    
    def update_state(self, state_update: Dict[str, Any]) -> None:
        """
        에이전트 상태 업데이트
        
        Args:
            state_update: 상태 업데이트 데이터
        """
        self.state.update(state_update)
    
    def set_web_retriever(self, web_retriever: WebSearchRetriever) -> None:
        """
        웹 검색 리트리버 설정
        
        Args:
            web_retriever: 웹 검색 리트리버 인스턴스
        """
        self.web_retriever = web_retriever
    
    def set_llm_manager(self, llm_manager: LLMManager) -> None:
        """
        LLM 관리자 설정
        
        Args:
            llm_manager: LLM 관리자 인스턴스
        """
        self.llm_manager = llm_manager
    
    def _extract_claims(self, message_content: str) -> List[str]:
        """
        메시지에서 팩트 체크할 주장을 추출
        
        Args:
            message_content: 메시지 내용
            
        Returns:
            추출된 주장 목록
        """
        if not self.llm_manager:
            # 간단한 구현: 문장 단위로 분리
            import re
            sentences = re.split(r'(?<=[.!?])\s+', message_content)
            return [s for s in sentences if len(s.split()) > 5]  # 5단어 이상인 문장만 주장으로 간주
        
        # LLM을 사용한 주장 추출
        prompt = f"""
        다음 대화 메시지에서 사실 검증이 필요한 주장들을 추출해주세요.
        숫자, 통계, 역사적 사실, 인용 등 객관적으로 검증할 수 있는 주장만 추출해주세요.
        의견이나 가치 판단은 포함하지 마세요.
        
        메시지:
        {message_content}
        
        추출된 주장들:
        """
        
        response = self.llm_manager.generate_text(prompt)
        
        # 응답에서 주장 목록 파싱
        claims = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-'):
                claims.append(line)
        
        return claims
    
    def _verify_claim(self, claim: str) -> Dict[str, Any]:
        """
        주장의 사실 여부를 검증
        
        Args:
            claim: 검증할 주장
            
        Returns:
            검증 결과
        """
        evidence = self._gather_evidence(claim)
        
        if not evidence:
            return {
                "claim": claim,
                "verified": False,
                "confidence": 0.0,
                "result": "insufficient_evidence",
                "evidence": [],
                "correction": None
            }
        
        # 검증 수행 (실제 구현에서는 LLM 사용)
        if self.llm_manager:
            verification_result = self._verify_with_llm(claim, evidence)
        else:
            # 기본 구현: 단순 키워드 매칭
            verification_result = self._simple_verification(claim, evidence)
        
        return verification_result
    
    def _gather_evidence(self, claim: str) -> List[Dict[str, Any]]:
        """
        주장 검증을 위한 증거 수집
        
        Args:
            claim: 검증할 주장
            
        Returns:
            수집된 증거 목록
        """
        evidence = []
        
        # 웹 검색으로 증거 수집
        if self.web_search_enabled and self.web_retriever:
            try:
                search_query = f"fact check: {claim}"
                web_results = self.web_retriever.retrieve_and_extract(
                    query=search_query,
                    max_pages=3,
                    rerank=True
                )
                
                for result in web_results[:5]:  # 상위 5개 결과만 사용
                    evidence.append({
                        "source": "web",
                        "text": result.get("text", ""),
                        "url": result.get("metadata", {}).get("url", ""),
                        "title": result.get("metadata", {}).get("title", ""),
                        "score": result.get("score", 0)
                    })
            except Exception as e:
                print(f"웹 검색 오류: {str(e)}")
        
        # 로컬 문서에서 증거 수집 (RAG)
        if self.rag_enabled:
            # 실제 구현에서는 RAG 시스템 활용
            pass
        
        return evidence
    
    def _verify_with_llm(self, claim: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLM을
        
        _verify_with_llm을 사용하여 주장 검증
        
        Args:
            claim: 검증할 주장
            evidence: 수집된 증거
            
        Returns:
            검증 결과
        """
        # 증거 텍스트 결합
        evidence_text = "\n\n".join([
            f"출처: {e.get('title', 'Unknown')} ({e.get('url', 'No URL')})\n{e.get('text', '')}"
            for e in evidence
        ])
        
        prompt = f"""
        다음 주장의 사실 여부를 검증해주세요.
        
        주장: "{claim}"
        
        다음은 이 주장을 검증하기 위해 수집한 증거입니다:
        
        {evidence_text}
        
        위 증거를 바탕으로 주장의 사실 여부를 판단하고, 다음 형식으로 응답해주세요:
        
        검증결과: [TRUE/FALSE/PARTLY_TRUE/INCONCLUSIVE]
        신뢰도: [0-1 사이의 숫자]
        설명: [검증 설명 및 이유]
        수정사항: [주장이 잘못된 경우, 올바른 정보 제시]
        """
        
        response = self.llm_manager.generate_text(prompt)
        
        # 응답 파싱
        import re
        verification = {}
        
        verification["claim"] = claim
        verification["evidence"] = evidence
        
        # 검증 결과 추출
        result_match = re.search(r'검증결과:\s*(TRUE|FALSE|PARTLY_TRUE|INCONCLUSIVE)', response)
        if result_match:
            result = result_match.group(1)
            if result == "TRUE":
                verification["verified"] = True
                verification["result"] = "true"
            elif result == "FALSE":
                verification["verified"] = False
                verification["result"] = "false"
            elif result == "PARTLY_TRUE":
                verification["verified"] = True
                verification["result"] = "partly_true"
            else:
                verification["verified"] = False
                verification["result"] = "inconclusive"
        else:
            verification["verified"] = False
            verification["result"] = "inconclusive"
        
        # 신뢰도 추출
        confidence_match = re.search(r'신뢰도:\s*(0\.\d+|1\.0|1|0)', response)
        verification["confidence"] = float(confidence_match.group(1)) if confidence_match else 0.0
        
        # 설명 추출
        explanation_match = re.search(r'설명:\s*(.*?)(?=\n수정사항:|$)', response, re.DOTALL)
        verification["explanation"] = explanation_match.group(1).strip() if explanation_match else ""
        
        # 수정사항 추출
        correction_match = re.search(r'수정사항:\s*(.*?)(?=$)', response, re.DOTALL)
        verification["correction"] = correction_match.group(1).strip() if correction_match else None
        
        return verification
    
    def _simple_verification(self, claim: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        단순 검증 로직 (기본 구현)
        
        Args:
            claim: 검증할 주장
            evidence: 수집된 증거
            
        Returns:
            검증 결과
        """
        # 간단한 구현: 키워드 일치도로 검증
        claim_words = set(claim.lower().split())
        
        match_scores = []
        for e in evidence:
            evidence_text = e.get("text", "").lower()
            evidence_words = set(evidence_text.split())
            
            # 단어 일치 점수
            if claim_words:
                match_ratio = len(claim_words.intersection(evidence_words)) / len(claim_words)
                match_scores.append(match_ratio)
        
        avg_score = sum(match_scores) / len(match_scores) if match_scores else 0
        
        return {
            "claim": claim,
            "verified": avg_score > 0.3,  # 간단한 임계값
            "confidence": avg_score,
            "result": "likely_true" if avg_score > 0.3 else "inconclusive",
            "evidence": evidence,
            "correction": None
        }
    
    def _generate_feedback(self, verification_results: List[Dict[str, Any]]) -> str:
        """
        검증 결과를 바탕으로 피드백 생성
        
        Args:
            verification_results: 주장 검증 결과 목록
            
        Returns:
            피드백 메시지
        """
        if not verification_results:
            return "검증할 주장이 없습니다."
        
        # 결과 분류
        true_claims = []
        false_claims = []
        inconclusive_claims = []
        
        for result in verification_results:
            if result["result"] in ["true", "likely_true"]:
                true_claims.append(result)
            elif result["result"] in ["false", "mostly_false"]:
                false_claims.append(result)
            else:
                inconclusive_claims.append(result)
        
        # 피드백 생성
        feedback = "팩트 체크 결과:\n\n"
        
        if false_claims:
            feedback += "⚠️ 정확하지 않은 정보:\n"
            for claim in false_claims:
                feedback += f"- \"{claim['claim']}\"\n"
                if claim.get("correction"):
                    feedback += f"  → 정확한 정보: {claim['correction']}\n"
            feedback += "\n"
        
        if true_claims:
            feedback += "✓ 정확한 정보:\n"
            for claim in true_claims[:2]:  # 2개만 표시
                feedback += f"- \"{claim['claim']}\"\n"
            feedback += "\n"
        
        if inconclusive_claims:
            feedback += "❓ 확인할 수 없는 정보:\n"
            for claim in inconclusive_claims[:1]:  # 1개만 표시
                feedback += f"- \"{claim['claim']}\"\n"
        
        return feedback
    
    def _update_verification_history(self, claim: str, result: Dict[str, Any]) -> None:
        """
        검증 기록 업데이트
        
        Args:
            claim: 검증된 주장
            result: 검증 결과
        """
        verification_record = {
            "timestamp": import_time().time(),
            "claim": claim,
            "result": result
        }
        
        history = self.state.get("verification_history", [])
        history.append(verification_record)
        
        # 최대 기록 수 제한
        if len(history) > 100:
            history = history[-100:]
            
        self.state["verification_history"] = history
        
        # 결과에 따라 분류하여 저장
        if result["verified"]:
            verified_facts = self.state.get("verified_facts", [])
            verified_facts.append(claim)
            self.state["verified_facts"] = verified_facts[-50:]  # 최대 50개 유지
        elif result.get("correction"):
            corrections = self.state.get("corrections", [])
            corrections.append((claim, result["correction"]))
            self.state["corrections"] = corrections[-30:]  # 최대 30개 유지 