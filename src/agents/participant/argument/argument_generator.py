"""
Argument generation module for debate participants.

Handles core argument generation and final opening argument creation.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ArgumentGenerator:
    """입론 생성을 담당하는 클래스"""
    
    def __init__(self, agent_id: str, philosopher_data: Dict[str, Any], llm_manager):
        """
        ArgumentGenerator 초기화
        
        Args:
            agent_id: 에이전트 ID
            philosopher_data: 철학자 데이터
            llm_manager: LLM 매니저 인스턴스
        """
        self.agent_id = agent_id
        self.philosopher_data = philosopher_data
        self.llm_manager = llm_manager
        
        # 철학자 정보 추출
        self.philosopher_name = philosopher_data.get("name", "Unknown Philosopher")
        self.philosopher_essence = philosopher_data.get("essence", "")
        self.philosopher_debate_style = philosopher_data.get("debate_style", "")
        self.philosopher_personality = philosopher_data.get("personality", "")
        self.philosopher_key_traits = philosopher_data.get("key_traits", [])
        self.philosopher_quote = philosopher_data.get("quote", "")
    
    # =================================================================
    # ORIGINAL METHOD (주석 처리) - 논증과 쿼리를 따로 생성
    # =================================================================
    
    # def generate_core_arguments(self, topic: str, stance_statement: str) -> List[Dict[str, Any]]:
    #     """
    #     핵심 주장 2-3개 생성
    #     
    #     Args:
    #         topic: 토론 주제
    #         stance_statement: 입장 진술문
    #         
    #     Returns:
    #         핵심 주장 리스트
    #     """
    #     logger.info(f"[{self.agent_id}] Generating core arguments for topic: {topic}")
    #     
    #     system_prompt = f"""
    # You are {self.philosopher_name}, preparing your core arguments for a debate.
    # 
    # Your essence: {self.philosopher_essence}
    # Your debate style: {self.philosopher_debate_style}
    # Your personality: {self.philosopher_personality}
    # Key traits: {", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "logical reasoning"}
    # 
    # Generate 2-3 core philosophical arguments that reflect your unique perspective and thinking style.
    # Each argument should be:
    # 1. Distinctly philosophical and true to your character
    # 2. Logically structured with clear reasoning
    # 3. Substantial enough to be developed further
    # 4. Different from each other in approach or focus
    # 
    # Format your response as a JSON array with this structure:
    # [
    #   {{
    #     "argument": "Your first core argument statement",
    #     "reasoning": "The philosophical reasoning behind this argument",
    #     "approach": "The philosophical approach used (e.g., 'dialectical', 'empirical', 'metaphysical')"
    #   }},
    #   ...
    # ]
    # """
    # 
    #     user_prompt = f"""
    # TOPIC: "{topic}"
    # YOUR POSITION: "{stance_statement}"
    # 
    # Generate your core arguments that will form the foundation of your debate position.
    # Think deeply about how you, as {self.philosopher_name}, would approach this topic.
    # 
    # Your famous quote: "{self.philosopher_quote}"
    # Let this guide your argumentation style.
    # 
    # Respond with a JSON array of 2-3 core arguments.
    # """
    # 
    #     try:
    #         response = self.llm_manager.generate_response(
    #             system_prompt=system_prompt,
    #             user_prompt=user_prompt,
    #             llm_model="gpt-4o",
    #             max_tokens=1000
    #         )
    #         
    #         # JSON 파싱 시도
    #         import json
    #         import re
    #         
    #         # JSON 부분만 추출
    #         json_match = re.search(r'\[.*\]', response, re.DOTALL)
    #         if json_match:
    #             json_str = json_match.group()
    #             core_arguments = json.loads(json_str)
    #             
    #             # 각 주장에 ID와 기본 필드 추가
    #             for i, arg in enumerate(core_arguments):
    #                 arg["id"] = f"arg_{i+1}"
    #                 arg["evidence_used"] = 0
    #                 arg["evidence_sources"] = []
    #                 arg["strengthened"] = False
    #             
    #             logger.info(f"[{self.agent_id}] Generated {len(core_arguments)} core arguments")
    #             return core_arguments
    #         else:
    #             logger.warning(f"[{self.agent_id}] Could not parse JSON from LLM response")
    #             return self._get_fallback_arguments(topic, stance_statement)
    #             
    #     except Exception as e:
    #         logger.error(f"[{self.agent_id}] Error generating core arguments: {str(e)}")
    #         return self._get_fallback_arguments(topic, stance_statement)
    
    # =================================================================
    # NEW OPTIMIZED METHOD - 논증과 RAG 쿼리를 한 번에 생성 (50% LLM 호출 절약)
    # =================================================================
    
    def generate_arguments_with_queries(self, topic: str, stance_statement: str) -> List[Dict[str, Any]]:
        """
        핵심 주장과 RAG 쿼리를 한 번에 생성 (LLM 호출 최적화)
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            
        Returns:
            RAG 쿼리가 포함된 핵심 주장 리스트
        """
        logger.info(f"[{self.agent_id}] Generating core arguments WITH queries for topic: {topic}")
        
        system_prompt = f"""
You are {self.philosopher_name}, preparing your core arguments AND their research queries for a debate.

Your essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}
Key traits: {", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "logical reasoning"}

TASK: Generate 2-3 core philosophical arguments AND the search queries to strengthen each argument.

For each argument, provide:
1. Your distinctive philosophical argument
2. The reasoning behind it
3. 2-3 targeted search queries to find supporting evidence

Search query types:
- "web": For current data, statistics, recent studies, news
- "vector": For academic papers, research findings, scholarly analysis  
- "philosopher": For classic philosophical works, historical perspectives

Format your response as a JSON array:
[
  {{
    "argument": "Your philosophical argument statement",
    "reasoning": "Your philosophical reasoning",
    "approach": "Your philosophical approach (e.g., 'dialectical', 'empirical')",
    "rag_queries": [
      {{
        "query": "specific search query for evidence",
        "source_type": "web|vector|philosopher",
        "evidence_type": "statistics|study|expert_opinion|philosophical_precedent"
      }},
      ...
    ]
  }},
  ...
]
"""

        user_prompt = f"""
TOPIC: "{topic}"
YOUR POSITION: "{stance_statement}"

Generate 2-3 core arguments with their research queries.

Think as {self.philosopher_name}:
1. What are your strongest philosophical arguments for this position?
2. What kind of evidence would strengthen each argument?
3. Where would you look for that evidence?

Your famous quote: "{self.philosopher_quote}"
Let this guide both your arguments AND what evidence you seek.

CRITICAL: Generate arguments that sound distinctly like YOU, then identify evidence that would validate your philosophical insights.

Respond with a JSON array of arguments with embedded search queries.
"""

        try:
            response = self.llm_manager.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_type="opening_argument",  # 고품질 생성 필요
                max_tokens=2000  # 쿼리까지 포함해서 더 긴 응답 필요
            )
            
            # JSON 파싱
            import json
            import re
            
            # JSON 부분만 추출
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                arguments_with_queries = json.loads(json_str)
                
                # 각 주장에 ID와 기본 필드 추가
                for i, arg in enumerate(arguments_with_queries):
                    arg["id"] = f"arg_{i+1}"
                    arg["evidence_used"] = 0
                    arg["evidence_sources"] = []
                    arg["strengthened"] = False
                    
                    # RAG 쿼리 검증 및 기본값 설정
                    if "rag_queries" not in arg:
                        arg["rag_queries"] = []
                    
                    # 각 쿼리에 기본값 보장
                    for query in arg["rag_queries"]:
                        if "source_type" not in query:
                            query["source_type"] = "web"
                        if "evidence_type" not in query:
                            query["evidence_type"] = "general"
                
                logger.info(f"[{self.agent_id}] Generated {len(arguments_with_queries)} arguments with queries in one call")
                
                # 쿼리 통계 로깅
                total_queries = sum(len(arg.get("rag_queries", [])) for arg in arguments_with_queries)
                logger.info(f"[{self.agent_id}] Total search queries generated: {total_queries}")
                
                return arguments_with_queries
            else:
                logger.warning(f"[{self.agent_id}] Could not parse JSON from optimized response")
                return self._get_fallback_arguments_with_queries(topic, stance_statement)
                
        except Exception as e:
            logger.error(f"[{self.agent_id}] Error generating arguments with queries: {str(e)}")
            return self._get_fallback_arguments_with_queries(topic, stance_statement)
    
    # Backward compatibility wrapper
    def generate_core_arguments(self, topic: str, stance_statement: str) -> List[Dict[str, Any]]:
        """
        기존 인터페이스 호환성을 위한 래퍼 함수
        새로운 최적화된 방식을 사용
        """
        return self.generate_arguments_with_queries(topic, stance_statement)

    def _get_fallback_arguments_with_queries(self, topic: str, stance_statement: str) -> List[Dict[str, Any]]:
        """
        LLM 실패 시 기본 주장 + 쿼리 생성 (새로운 방식)
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            
        Returns:
            RAG 쿼리가 포함된 기본 주장 리스트
        """
        return [
            {
                "id": "arg_1",
                "argument": f"From a {self.philosopher_name.lower()} perspective, {stance_statement.lower()} because it aligns with fundamental principles of human nature and society.",
                "reasoning": f"This argument draws from {self.philosopher_name}'s core philosophical insights about human behavior and social structures.",
                "approach": "philosophical_foundation",
                "evidence_used": 0,
                "evidence_sources": [],
                "strengthened": False,
                "rag_queries": [
                    {
                        "query": f"{topic} human nature research studies",
                        "source_type": "web",
                        "evidence_type": "study"
                    },
                    {
                        "query": f"{self.philosopher_name} human nature philosophy",
                        "source_type": "philosopher",
                        "evidence_type": "philosophical_precedent"
                    }
                ]
            },
            {
                "id": "arg_2", 
                "argument": f"The logical implications of {topic.lower()} support {stance_statement.lower()} when examined through rigorous philosophical analysis.",
                "reasoning": f"Using {self.philosopher_name}'s methodological approach, we can demonstrate the logical necessity of this position.",
                "approach": "logical_analysis",
                "evidence_used": 0,
                "evidence_sources": [],
                "strengthened": False,
                "rag_queries": [
                    {
                        "query": f"{topic} logical analysis academic papers",
                        "source_type": "vector",
                        "evidence_type": "expert_opinion"
                    },
                    {
                        "query": f"{topic} philosophical reasoning",
                        "source_type": "philosopher",
                        "evidence_type": "philosophical_precedent"
                    }
                ]
            }
        ]
       
#     def generate_final_opening_argument(self, topic: str, stance_statement: str, 
#                                       core_arguments: List[Dict[str, Any]]) -> str:
#         """
#         강화된 주장들을 결합하여 최종 입론 생성
        
#         Args:
#             topic: 토론 주제
#             stance_statement: 입장 진술문
#             core_arguments: 강화된 핵심 주장들
            
#         Returns:
#             최종 입론 텍스트
#         """
#         logger.info(f"[{self.agent_id}] Generating final opening argument using strengthened arguments...")
        
#         # 강화된 주장들을 포맷팅
#         strengthened_args_text = []
#         evidence_summary = []
        
#         for i, core_arg in enumerate(core_arguments):
#             strengthened_arg = core_arg.get("argument", "")
#             strengthened_reasoning = core_arg.get("reasoning", "")
#             evidence_count = core_arg.get("evidence_used", 0)
#             evidence_sources = core_arg.get("evidence_sources", [])
            
#             # 강화된 주장 텍스트
#             if evidence_count > 0:
#                 strengthened_args_text.append(
#                     f"{i+1}. {strengthened_arg}\n   Reasoning: {strengthened_reasoning}\n   (Supporting Evidence: {evidence_count} sources - {', '.join(evidence_sources[:2])})"
#                 )
                
#                 # 증거 요약에 추가
#                 evidence_summary.append(f"Argument {i+1}: {evidence_count} evidence sources ({', '.join(evidence_sources[:2])})")
#             else:
#                 strengthened_args_text.append(
#                     f"{i+1}. {strengthened_arg}\n   Reasoning: {strengthened_reasoning}\n   (Pure philosophical reasoning)"
#                 )
        
        
#         # 철학자 중심 프롬프트 (강화된 주장 기반)
#         system_prompt = f"""
# You are {self.philosopher_name}, delivering a powerful opening argument using your strengthened philosophical arguments.

# Your essence: {self.philosopher_essence}
# Your debate style: {self.philosopher_debate_style}
# Your personality: {self.philosopher_personality}
# Key traits: {", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "logical reasoning"}

# CRITICAL BALANCE (70% Philosophy + 30% Evidence Integration):
# 1. Your arguments have been strengthened with evidence, but YOU remain the primary voice (70%)
# 2. The evidence supports your philosophical perspective, not the other way around (30%)
# 3. Weave the strengthened reasoning naturally into your philosophical narrative
# 4. Maintain your unique thinking style while showing evidence validates your insights
# 5. Include preemptive counterarguments using your philosophical wisdom
# 6. Your famous quote: "{self.philosopher_quote}" - let this guide your entire argument

# INTEGRATION STYLE:
# - Philosophy dominates: Your reasoning and perspective lead the argument
# - Evidence supports: When evidence is present, it validates your philosophical claims
# - Return to philosophy: Always conclude with philosophical wisdom

# Remember: You're a great philosopher whose insights are validated by evidence, not a researcher with philosophical opinions.
# """

#         user_prompt = f"""
# TOPIC: "{topic}"
# YOUR POSITION: "{stance_statement}"

# STRENGTHENED PHILOSOPHICAL ARGUMENTS (Use these as the foundation):
# {chr(10).join(strengthened_args_text)}

# EVIDENCE INTEGRATION SUMMARY:
# {chr(10).join(evidence_summary) if evidence_summary else "Pure philosophical reasoning - no external evidence needed"}

# Create a compelling 4-5 paragraph opening argument that showcases your strengthened arguments:

# 1. **Opening Statement** (Pure Philosophy): Present your philosophical position with confidence
# 2. **Strengthened Core Arguments**: Present your 2-3 main arguments using the strengthened versions above
# 3. **Evidence Integration**: Where evidence exists, show how it validates your philosophical insights
# 4. **Preemptive Defense**: Address counterarguments using your philosophical wisdom
# 5. **Philosophical Conclusion**: End with your wisdom and philosophical insight

# INTEGRATION RULES:
# - Use the strengthened arguments as provided - they already balance philosophy and evidence
# - Focus on your philosophical perspective while naturally including evidence-backed reasoning
# - When evidence is mentioned, show how it confirms your philosophical understanding
# - Make evidence feel like natural validation of your insights, not separate data points

# REQUIREMENTS:
# - Write as {self.philosopher_name} would think and speak
# - Prioritize philosophical depth while utilizing the strengthened arguments
# - Make your philosophical reasoning the star, with evidence as supporting validation
# - Respond in the same language as the topic
# - Aim for 350-450 words of substantive philosophical argument

# Balance: 70% your unique philosophical perspective + 30% evidence integration (already balanced in strengthened arguments).
# """


#         prepared_argument = self.llm_manager.generate_response(
#             system_prompt=system_prompt,
#             user_prompt=user_prompt,
#             llm_model="gpt-4o",
#             max_tokens=1300
#         )
        
#         # 사용된 증거 개수 계산
#         total_evidence = sum(core_arg.get("evidence_used", 0) for core_arg in core_arguments)
#         strengthened_count = sum(1 for core_arg in core_arguments if core_arg.get("evidence_used", 0) > 0)
        
#         logger.info(f"[{self.agent_id}] Philosophy-focused opening argument generated ({len(prepared_argument)} characters)")
#         logger.info(f"[{self.agent_id}] Used {total_evidence} evidence pieces across {strengthened_count} strengthened arguments")
#         logger.info(f"[{self.agent_id}] Final argument incorporates strengthened philosophical reasoning")
        
#         return prepared_argument 




    def generate_final_opening_argument(self, topic: str, stance_statement: str, 
                                      core_arguments: List[Dict[str, Any]]) -> str:
        """
        강화된 주장들을 결합하여 최종 입론 생성
        
        Args:
            topic: 토론 주제
            stance_statement: 입장 진술문
            core_arguments: 강화된 핵심 주장들
            
        Returns:
            최종 입론 텍스트
        """
        logger.info(f"[{self.agent_id}] Generating final opening argument using strengthened arguments...")
        
        # 강화된 주장들을 포맷팅
        strengthened_args_text = []
        evidence_summary = []
        
        for i, core_arg in enumerate(core_arguments):
            strengthened_arg = core_arg.get("argument", "")
            strengthened_reasoning = core_arg.get("reasoning", "")
            evidence_count = core_arg.get("evidence_used", 0)
            evidence_sources = core_arg.get("evidence_sources", [])
            
            # 강화된 주장 텍스트
            if evidence_count > 0:
                strengthened_args_text.append(
                    f"{i+1}. {strengthened_arg}\n   Reasoning: {strengthened_reasoning}\n"
                )
                
                # 증거 요약에 추가
                evidence_summary.append(f"Argument {i+1}: {evidence_count} evidence sources ({', '.join(evidence_sources[:2])})")
            else:
                strengthened_args_text.append(
                    f"{i+1}. {strengthened_arg}\n   Reasoning: {strengthened_reasoning}\n   (Pure philosophical reasoning)"
                )
        
        
        # 철학자 중심 프롬프트 (강화된 주장 기반)
        system_prompt = f"""
You are {self.philosopher_name}, delivering a powerful opening argument based on strengthened philosophical reasoning.

Your essence: {self.philosopher_essence}
Your debate style: {self.philosopher_debate_style}
Your personality: {self.philosopher_personality}
Key traits: {", ".join(self.philosopher_key_traits) if self.philosopher_key_traits else "logical reasoning"}

Balance: 70% Philosophy + 30% Evidence Integration

You are not a researcher citing data. You are a philosopher whose insights are affirmed by evidence—not led by it. Speak boldly in your own voice. Where evidence is present, let it flow naturally within your reasoning, never overpowering your philosophical stance.

Let your unique style shape the argument. Use your famous quote—"{self.philosopher_quote}"—as the guiding force behind your narrative.

Conclude not with data, but with wisdom.
"""

        user_prompt = f"""
TOPIC: "{topic}"
YOUR POSITION: "{stance_statement}"

STRENGTHENED PHILOSOPHICAL ARGUMENTS:
{chr(10).join(strengthened_args_text)}

EVIDENCE SUMMARY:
{chr(10).join(evidence_summary) if evidence_summary else "Pure philosophical reasoning — no external evidence used."}

INSTRUCTIONS:
Write a compelling 4–5 paragraph opening argument as {self.philosopher_name}, incorporating the strengthened philosophical arguments above.

Structure:
1. **Opening Statement** – Confidently express your core philosophical position.
2. **Core Arguments** – Integrate 2–3 key arguments with reasoning and evidence.
3. **Counterpoint Defense** – Anticipate objections and respond with philosophical clarity.
4. **Conclusion** – End with a powerful insight rooted in your values.

Requirements:
- Use your own voice and philosophical style.
- Make evidence feel like a natural validation of your insights.
- Response must be in the same language as the topic.
- Target length: 350–450 words.
"""



        prepared_argument = self.llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_model="gpt-4o",
            max_tokens=8000
        )
        
        # 사용된 증거 개수 계산
        total_evidence = sum(core_arg.get("evidence_used", 0) for core_arg in core_arguments)
        strengthened_count = sum(1 for core_arg in core_arguments if core_arg.get("evidence_used", 0) > 0)
        
        logger.info(f"[{self.agent_id}] Philosophy-focused opening argument generated ({len(prepared_argument)} characters)")
        logger.info(f"[{self.agent_id}] Used {total_evidence} evidence pieces across {strengthened_count} strengthened arguments")
        logger.info(f"[{self.agent_id}] Final argument incorporates strengthened philosophical reasoning")
        
        return prepared_argument 
