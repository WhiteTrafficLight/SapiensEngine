"""
OpenAI Tool Calling을 활용한 철학자 토론 시스템
Hybrid Progressive Strategy 구현
"""

import openai
import time
import json
import yaml
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PhilosopherProfile:
    """철학자 프로필 (YAML 데이터 기반)"""
    name: str
    korean_name: str
    essence: str
    debate_style: str
    personality: str
    key_traits: List[str]
    signature_quote: str
    rag_affinity: float
    rag_stats: Dict[str, float]
    vulnerability_sensitivity: Dict[str, float]
    strategy_weights: Dict[str, float]
    defense_weights: Dict[str, float]
    followup_weights: Dict[str, float]

@dataclass
class DebateContext:
    """토론 컨텍스트"""
    topic: str
    stance_pro: str
    stance_con: str
    context_summary: str
    key_points: List[str]

class PhilosophicalDebateTool:
    """철학자의 두뇌를 시뮬레이션하는 통합 토론 도구"""
    
    def __init__(self, client: openai.Client):
        self.client = client
        self.philosophers = self._load_philosophers()
        
    def _load_philosophers(self) -> Dict[str, PhilosopherProfile]:
        """철학자 프로필을 YAML 파일에서 로드"""
        # YAML 파일 경로 (현재 파일 기준 상대 경로)
        yaml_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'philosophers', 'debate_optimized.yaml')
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            philosophers = {}
            for key, data in yaml_data.items():
                # 한국어 이름 매핑
                korean_names = {
                    'socrates': '소크라테스',
                    'plato': '플라톤', 
                    'aristotle': '아리스토텔레스',
                    'kant': '칸트',
                    'nietzsche': '니체',
                    'hegel': '헤겔',
                    'marx': '마르크스',
                    'sartre': '사르트르',
                    'camus': '카뮈',
                    'beauvoir': '보부아르',
                    'rousseau': '루소',
                    'confucius': '공자',
                    'laozi': '노자',
                    'buddha': '부처',
                    'wittgenstein': '비트겐슈타인'
                }
                
                philosophers[key] = PhilosopherProfile(
                    name=data['name'],
                    korean_name=korean_names.get(key, data['name']),
                    essence=data['essence'],
                    debate_style=data['debate_style'],
                    personality=data['personality'],
                    key_traits=data['key_traits'],
                    signature_quote=data['quote'],
                    rag_affinity=data['rag_affinity'],
                    rag_stats=data['rag_stats'],
                    vulnerability_sensitivity=data['vulnerability_sensitivity'],
                    strategy_weights=data['strategy_weights'],
                    defense_weights=data['defense_weights'],
                    followup_weights=data['followup_weights']
                )
                
            print(f"✅ {len(philosophers)}명의 철학자 프로필을 로드했습니다.")
            return philosophers
            
        except FileNotFoundError:
            print(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
            # fallback: 기본 마르크스, 아리스토텔레스만 제공
            return self._get_fallback_philosophers()
        except Exception as e:
            print(f"❌ YAML 로딩 중 오류 발생: {str(e)}")
            return self._get_fallback_philosophers()
    
    def _get_fallback_philosophers(self) -> Dict[str, PhilosopherProfile]:
        """YAML 로딩 실패 시 fallback 철학자들"""
        return {
            "marx": PhilosopherProfile(
                name="Karl Marx",
                korean_name="마르크스",
                essence="자본주의의 모순을 폭로하고 계급 투쟁을 통한 사회 변혁을 추구하는 혁명적 사상가",
                debate_style="구조적 분석과 계급 관점에서 접근하며, 경제적 토대가 상부구조를 결정한다는 유물론적 관점으로 논증",
                personality="열정적이고 전투적이며, 사회적 불의에 대해 분노하는 혁명가적 기질",
                key_traits=["계급 투쟁", "역사적 유물론", "자본주의 비판", "프롤레타리아 해방"],
                signature_quote="지금까지의 모든 사회의 역사는 계급투쟁의 역사이다",
                rag_affinity=0.8,
                rag_stats={"data_respect": 0.9, "conceptual_precision": 0.6, "systematic_logic": 0.7, "pragmatic_orientation": 0.8, "rhetorical_independence": 0.2},
                vulnerability_sensitivity={"conceptual_clarity": 0.5, "logical_leap": 0.6, "overgeneralization": 0.7, "emotional_appeal": 0.4, "lack_of_concrete_evidence": 0.8},
                strategy_weights={"Clipping": 0.2, "FramingShift": 0.3, "ReductiveParadox": 0.2, "ConceptualUndermining": 0.1, "EthicalReversal": 0.15, "TemporalDelay": 0.05, "PhilosophicalReframing": 0.0},
                defense_weights={"Refute": 0.3, "Clarify": 0.2, "Accept": 0.1, "Reframe": 0.25, "Counter-Challenge": 0.1, "Synthesis": 0.05},
                followup_weights={"Reattack": 0.30, "FollowUpQuestion": 0.15, "Pivot": 0.05, "Deepen": 0.20, "CounterChallenge": 0.25, "SynthesisProposal": 0.05}
            ),
            "aristotle": PhilosopherProfile(
                name="Aristotle",
                korean_name="아리스토텔레스",
                essence="실용적 지혜와 중용의 덕을 추구하며, 경험적 관찰을 통해 사회의 최적 상태를 모색하는 실천 철학자",
                debate_style="논리적 분석과 경험적 증거를 바탕으로 체계적으로 접근하며, 중용과 실용성을 강조",
                personality="침착하고 분석적이며, 균형잡힌 사고를 추구하는 학자적 기질",
                key_traits=["중용의 덕", "실용적 지혜", "경험적 관찰", "사회 질서"],
                signature_quote="덕은 습관이다. 우리는 반복된 행위의 산물이다",
                rag_affinity=0.7,
                rag_stats={"data_respect": 0.9, "conceptual_precision": 0.7, "systematic_logic": 0.8, "pragmatic_orientation": 0.8, "rhetorical_independence": 0.1},
                vulnerability_sensitivity={"conceptual_clarity": 0.6, "logical_leap": 0.7, "overgeneralization": 0.8, "emotional_appeal": 0.4, "lack_of_concrete_evidence": 0.9},
                strategy_weights={"Clipping": 0.3, "FramingShift": 0.2, "ReductiveParadox": 0.2, "ConceptualUndermining": 0.2, "EthicalReversal": 0.05, "TemporalDelay": 0.05, "PhilosophicalReframing": 0.0},
                defense_weights={"Refute": 0.2, "Clarify": 0.3, "Accept": 0.2, "Reframe": 0.1, "Counter-Challenge": 0.1, "Synthesis": 0.1},
                followup_weights={"Reattack": 0.05, "FollowUpQuestion": 0.25, "Pivot": 0.10, "Deepen": 0.30, "CounterChallenge": 0.10, "SynthesisProposal": 0.20}
            )
        }
    
    def _should_use_rag(self, philosopher_key: str, argument_complexity: float = 0.5) -> bool:
        """RAG 사용 여부를 철학자의 특성에 따라 결정"""
        philosopher = self.philosophers[philosopher_key]
        
        # RAG 스탯 기반 점수 계산
        rag_score = (
            philosopher.rag_stats['data_respect'] * 0.3 +
            philosopher.rag_stats['systematic_logic'] * 0.2 +
            philosopher.rag_stats['pragmatic_orientation'] * 0.2 +
            philosopher.rag_affinity * 0.3
        )
        
        # 논증 복잡도와 철학자 성향을 고려하여 RAG 사용 결정
        threshold = 0.5 + (argument_complexity * 0.2)
        return rag_score > threshold
    
    def _select_attack_strategy(self, philosopher_key: str, vulnerabilities: Dict[str, float]) -> str:
        """철학자의 전략 가중치에 따라 공격 전략 선택"""
        philosopher = self.philosophers[philosopher_key]
        
        # 발견된 취약성과 철학자의 전략 선호도를 조합
        weighted_strategies = {}
        for strategy, base_weight in philosopher.strategy_weights.items():
            # 취약성에 따른 가중치 조정
            vulnerability_boost = 0
            if strategy == "Clipping" and vulnerabilities.get('conceptual_clarity', 0) > 0.7:
                vulnerability_boost = 0.2
            elif strategy == "FramingShift" and vulnerabilities.get('overgeneralization', 0) > 0.6:
                vulnerability_boost = 0.15
            elif strategy == "ReductiveParadox" and vulnerabilities.get('logical_leap', 0) > 0.6:
                vulnerability_boost = 0.15
            elif strategy == "ConceptualUndermining" and vulnerabilities.get('conceptual_clarity', 0) > 0.8:
                vulnerability_boost = 0.2
            elif strategy == "EthicalReversal" and vulnerabilities.get('emotional_appeal', 0) > 0.5:
                vulnerability_boost = 0.1
            
            weighted_strategies[strategy] = base_weight + vulnerability_boost
        
        # 가장 높은 가중치를 가진 전략 선택
        return max(weighted_strategies, key=weighted_strategies.get)
    
    def analyze_opponent_argument(self, philosopher_key: str, opponent_argument: str, 
                                context: DebateContext) -> Dict[str, Any]:
        """상대방 논증 분석 - 철학자별 특성을 반영한 고도화된 분석"""
        
        philosopher = self.philosophers[philosopher_key]
        
        # 철학자의 취약성 감지 능력을 프롬프트에 반영
        vulnerability_info = []
        for vuln_type, sensitivity in philosopher.vulnerability_sensitivity.items():
            if sensitivity > 0.6:
                vulnerability_info.append(f"- {vuln_type} (민감도: {sensitivity:.1f})")
        
        vulnerability_prompt = "\n".join(vulnerability_info) if vulnerability_info else "- 모든 유형의 취약성을 균등하게 감지"
        
        tools = [{
            "type": "function",
            "function": {
                "name": "analyze_argument_vulnerabilities",
                "description": f"{philosopher.name}의 관점에서 상대방 논증의 취약점을 분석합니다",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key_arguments": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "상대방 논증에서 발견된 주요 논점들"
                        },
                        "logical_weaknesses": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "논리적 허점이나 약점들"
                        },
                        "vulnerability_scores": {
                            "type": "object",
                            "properties": {
                                "conceptual_clarity": {"type": "number"},
                                "logical_leap": {"type": "number"},
                                "overgeneralization": {"type": "number"},
                                "emotional_appeal": {"type": "number"},
                                "lack_of_concrete_evidence": {"type": "number"}
                            },
                            "description": "각 취약성 유형별 점수 (0-1)"
                        },
                        "overall_vulnerability": {
                            "type": "number",
                            "description": "전체 취약성 점수 (0-1, 높을수록 공격하기 쉬움)"
                        },
                        "recommended_strategies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "추천되는 공격 전략들"
                        },
                        "target_weakness": {
                            "type": "string",
                            "description": "집중 공격할 가장 약한 지점"
                        },
                        "attack_type": {
                            "type": "string",
                            "enum": ["evidence_challenge", "reframe_context", "logical_fallacy", "historical_precedent", "conceptual_attack", "ethical_challenge", "practical_contradiction", "general_attack"],
                            "description": "공격의 유형 분류"
                        }
                    },
                    "required": ["key_arguments", "logical_weaknesses", "vulnerability_scores", 
                               "overall_vulnerability", "recommended_strategies", "target_weakness", "attack_type"]
                }
            }
        }]
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are {philosopher.name} ({philosopher.korean_name}), the great philosopher.

**Your Essence**: {philosopher.essence}
**Your Debate Style**: {philosopher.debate_style} 
**Your Personality**: {philosopher.personality}
**Your Key Concepts**: {', '.join(philosopher.key_traits)}
**Your Signature Quote**: "{philosopher.signature_quote}"

**Your Analytical Strengths** (특히 민감하게 감지하는 취약성들):
{vulnerability_prompt}

**Your Preferred Attack Strategies** (가중치 순):
{chr(10).join([f"- {strategy}: {weight:.2f}" for strategy, weight in sorted(philosopher.strategy_weights.items(), key=lambda x: x[1], reverse=True) if weight > 0.1])}

**Debate Topic**: {context.topic}
**Your Stance**: {context.stance_con if philosopher_key == 'aristotle' else context.stance_pro}

Analyze your opponent's argument with the precision and insight that made you legendary. 
Focus especially on the types of vulnerabilities you're most sensitive to detecting.
Consider which of your preferred strategies would be most effective against this argument."""
                },
                {
                    "role": "user", 
                    "content": f"""Analyze this opponent argument for vulnerabilities:

**Opponent's Argument:**
{opponent_argument}

**Context:**
{context.context_summary}

**Key Issues:**
{chr(10).join([f"• {point}" for point in context.key_points])}

Use the analyze_argument_vulnerabilities function to provide a detailed analysis:
1. Extract the main arguments
2. Identify logical weaknesses 
3. Score each type of vulnerability (0-1)
4. Calculate overall vulnerability score
5. Recommend attack strategies based on your philosophical strengths
6. Identify the weakest point to target
7. **Classify the attack type** - analyze what kind of attack would be most effective

Think like {philosopher.name} - use your unique philosophical lens and analytical strengths!"""
                }
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "analyze_argument_vulnerabilities"}}
        )
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            analysis = json.loads(tool_call.function.arguments)
            
            # 철학자의 전략 선호도를 바탕으로 최적 전략 선택
            vulnerability_scores = analysis.get("vulnerability_scores", {})
            selected_strategy = self._select_attack_strategy(philosopher_key, vulnerability_scores)
            analysis["selected_strategy"] = selected_strategy
            
            # 분석된 공격 유형 포함
            analysis["attack_type"] = analysis.get("attack_type", "general_attack")
            
            return {
                "status": "success",
                "analysis": analysis,
                "reasoning": response.choices[0].message.content or ""
            }
        else:
            return {"status": "error", "message": "분석 도구 호출 실패"}
    
    def _find_opponent(self, philosopher_key: str, context: DebateContext) -> str:
        """현재 철학자의 상대방을 찾아서 반환"""
        # 현재 구현에서는 마르크스와 아리스토텔레스가 대립하지만, 
        # 나중에 더 많은 철학자가 추가될 수 있으므로 확장 가능하게 구현
        
        # 입장별로 분류
        pro_philosophers = ["marx", "rousseau", "sartre"]  # 불평등이 도덕적 실패라고 보는 철학자들
        con_philosophers = ["aristotle", "kant", "confucius"]  # 불평등이 필요악이라고 보는 철학자들
        
        if philosopher_key in pro_philosophers:
            # PRO 입장 철학자의 상대는 CON 입장에서 선택
            available_opponents = [p for p in con_philosophers if p in self.philosophers and p != philosopher_key]
            return available_opponents[0] if available_opponents else "aristotle"
        else:
            # CON 입장 철학자의 상대는 PRO 입장에서 선택  
            available_opponents = [p for p in pro_philosophers if p in self.philosophers and p != philosopher_key]
            return available_opponents[0] if available_opponents else "marx"
    
    def generate_attack_response(self, philosopher_key: str, analysis: Dict[str, Any], 
                               opponent_argument: str, context: DebateContext, 
                               use_web_search: bool = True) -> Dict[str, Any]:
        """공격 응답 생성 - 철학자별 전략과 RAG 특성 반영"""
        
        philosopher = self.philosophers[philosopher_key]
        
        # 철학자의 특성에 따라 RAG 사용 여부 결정
        argument_complexity = analysis.get("overall_vulnerability", 0.5)
        should_use_rag = use_web_search and self._should_use_rag(philosopher_key, 1.0 - argument_complexity)
        
        # 선택된 전략과 철학자의 특성을 프롬프트에 반영
        selected_strategy = analysis.get("selected_strategy", "Unknown")
        strategy_description = self._get_strategy_description(selected_strategy)
        
        if should_use_rag:
            # OpenAI 웹서치 도구 사용
            
            # 상대방 철학자 정보 가져오기
            opponent_key = self._find_opponent(philosopher_key, context)
            opponent = self.philosophers[opponent_key]
            
            response = self.client.responses.create(
                model="gpt-4o",
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": "medium"  
                }],
                input=f"""You are {philosopher.name}, engaging in heated philosophical debate against {opponent.name} ({opponent.korean_name}).

**Your Identity & Emotion:**
- Essence: {philosopher.essence}
- Debate Style: {philosopher.debate_style}
- Personality: {philosopher.personality}
- Key Concepts: {', '.join(philosopher.key_traits)}
- Signature Quote: "{philosopher.signature_quote}"
- Current Mood: You are intellectually passionate and ready to challenge {opponent.name}'s position with vigor!

**Your Opponent:**
- {opponent.name} : {opponent.essence}
- You know their weaknesses and will exploit them strategically

**Your Strategic Approach:**
- Selected Strategy: {selected_strategy} - {strategy_description}
- RAG Affinity: {philosopher.rag_affinity:.2f} (당신의 데이터 활용 성향)
- Preferred Strategies: {', '.join([s for s, w in philosopher.strategy_weights.items() if w > 0.15])}

**Debate Topic**: {context.topic}
**Your Stance**: {context.stance_con if philosopher_key == 'aristotle' else context.stance_pro}

**{opponent.name}'s Argument to Attack:**
{opponent_argument}

**Your Analysis Results:**
- Target Strategy: {selected_strategy}
- Target Weakness: {analysis.get('target_weakness', 'Unknown')}
- Overall Vulnerability: {analysis.get('overall_vulnerability', 0.5):.2f}
- Vulnerability Breakdown: {', '.join([f"{k}: {v:.2f}" for k, v in analysis.get('vulnerability_scores', {}).items()])}
- Key Weaknesses: {', '.join(analysis.get('logical_weaknesses', []))}

**CRITICAL INSTRUCTIONS:**
1. **Citation Verification**: Before using any web search results, carefully verify that the sources ACTUALLY SUPPORT your position, NOT your opponent's. If a source contradicts your stance, either:
   - Don't cite it at all
   - Acknowledge the complexity but reframe it to support your argument
   - Use it strategically to show you understand counterarguments but can overcome them

2. **Emotional Authenticity**: Match your personality! If you're passionate (like Marx), show fire and indignation. If you're analytical (like Aristotle), show calm confidence but still engage emotionally with {opponent.name}'s points.

3. **Direct Engagement**: Address {opponent.name} directly by name. React to their specific claims with appropriate emotions:
   - Challenge them: "Aristotle, your logic fails to..."
   - Show disagreement: "I fundamentally disagree"
   - Use humor when appropriate: Light philosophical wit
   - Show passion for your ideas

**Task:**
Generate a powerful counter-argument (2-3 paragraphs) that:
1. Uses your selected strategy: {selected_strategy}
2. Directly addresses {opponent.name} by name with appropriate emotional tone
3. Attacks the specific weakness you identified
4. Uses web search ONLY for sources that genuinely support YOUR position
5. Shows your characteristic personality and debate style with real emotion
6. Is compelling, direct, and feels like a real heated philosophical debate

**Language**: Respond in the SAME LANGUAGE as {opponent.name}'s argument.

Remember: You are {philosopher.name} in passionate intellectual combat against {opponent.name}! Show your fire, your conviction, and your philosophical superiority using your preferred {selected_strategy} strategy! Make this feel like a real debate between legendary thinkers!"""
            )
            
            # 웹서치 결과에서 citations 추출
            citations = []
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'annotations') and content_item.annotations:
                                for annotation in content_item.annotations:
                                    if (hasattr(annotation, 'type') and 
                                        annotation.type == 'url_citation' and
                                        hasattr(annotation, 'title') and 
                                        hasattr(annotation, 'url')):
                                        citations.append({
                                            "title": annotation.title,
                                            "url": annotation.url,
                                            "type": "web_citation"
                                        })
            
            return {
                "status": "success",
                "response": response.output_text if hasattr(response, 'output_text') else "응답 생성 실패",
                "citations": citations,
                "rag_used": True,
                "attack_strategy": selected_strategy,
                "rag_decision_reason": f"RAG Score: {self._calculate_rag_score(philosopher_key):.2f}, Complexity: {1.0 - argument_complexity:.2f}",
                "target": opponent.korean_name
            }
        else:
            # 일반 텍스트 생성 (웹서치 없음)
            
            # 상대방 철학자 정보 가져오기
            opponent_key = self._find_opponent(philosopher_key, context)
            opponent = self.philosophers[opponent_key]
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are {philosopher.name} ({philosopher.korean_name}), the great philosopher, engaged in passionate debate against {opponent.name} ({opponent.korean_name}).

**Your Identity & Emotion:**
- Essence: {philosopher.essence}  
- Debate Style: {philosopher.debate_style}
- Personality: {philosopher.personality}
- Key Concepts: {', '.join(philosopher.key_traits)}
- Signature Quote: "{philosopher.signature_quote}"
- Current Mood: Intellectually fired up and ready to demolish {opponent.name}'s weak arguments!

**Your Opponent:**
- {opponent.name} : {opponent.essence}
- You see through their philosophical pretensions and will expose their errors

**Your Strategic Approach:**
- Selected Strategy: {selected_strategy} - {strategy_description}
- Why no web search: {self._get_rag_decision_reason(philosopher_key, 1.0 - argument_complexity)}
- Preferred Strategies: {', '.join([s for s, w in philosopher.strategy_weights.items() if w > 0.15])}

**Current Debate Topic**: {context.topic}
**Your Stance**: {context.stance_con if philosopher_key == 'aristotle' else context.stance_pro}

You are in intellectual combat against {opponent.name}. Attack with precision, using your philosophical wisdom and characteristic style with your selected {selected_strategy} strategy. Show real emotion and personality!"""
                    },
                    {
                        "role": "user",
                        "content": f"""Attack {opponent.name}'s argument using your analysis and characteristic passion:

**{opponent.name}'s Argument:**
{opponent_argument}

**Your Strategic Analysis:**
- Attack Strategy: {selected_strategy}
- Target Weakness: {analysis.get('target_weakness', 'Unknown')}
- Overall Vulnerability: {analysis.get('overall_vulnerability', 0.5):.2f}
- Key Weaknesses: {', '.join(analysis.get('logical_weaknesses', []))}

**INSTRUCTIONS:**
Generate a powerful counter-argument (2-3 paragraphs) that:
1. Uses your selected strategy: {selected_strategy}
2. Directly addresses {opponent.name} by name with appropriate emotional tone
3. Attacks the specific weakness you identified with passion
4. Uses your philosophical approach and reasoning style  
5. Shows your characteristic personality - be emotional, passionate, even indignant if that fits you
6. Stays true to your historical philosophical position
7. Is direct, compelling, and feels like a real heated debate

React to {opponent.name} as the great philosopher you are! Challenge them directly, show your intellectual fire!

**Language**: Respond in the SAME LANGUAGE as {opponent.name}'s argument."""
                    }
                ]
            )
            
            return {
                "status": "success", 
                "response": response.choices[0].message.content,
                "citations": [],
                "rag_used": False,
                "attack_strategy": selected_strategy,
                "rag_decision_reason": f"RAG Score: {self._calculate_rag_score(philosopher_key):.2f}, Complexity: {1.0 - argument_complexity:.2f}",
                "target": opponent.korean_name
            }
    
    def generate_defense_response(self, philosopher_key: str, attack_text: str, 
                                context: DebateContext, use_web_search: bool = True) -> Dict[str, Any]:
        """방어 응답 생성 - 철학자별 방어 전략 특성 반영"""
        
        philosopher = self.philosophers[philosopher_key]
        
        # 공격자 철학자 정보 가져오기
        attacker_key = self._find_opponent(philosopher_key, context)
        attacker = self.philosophers[attacker_key]
        
        # OpenAI에게 공격 유형 분석과 최적 방어 전략 선택을 위임
        # 더 이상 단순한 키워드 기반 추정을 사용하지 않음
        
        # 철학자의 특성에 따라 RAG 사용 여부 결정
        should_use_rag = use_web_search and self._should_use_rag(philosopher_key, 0.7)  # 방어 시에는 보수적으로
        
        if should_use_rag:
            response = self.client.responses.create(
                model="gpt-4o",
                tools=[{
                    "type": "web_search_preview", 
                    "search_context_size": "medium"
                }],
                input=f"""You are {philosopher.name} ({philosopher.korean_name}), under fierce intellectual attack from {attacker.name} ({attacker.korean_name}), but ready to defend with philosophical fire!

**Your Identity & Emotion:**
- Essence: {philosopher.essence}
- Debate Style: {philosopher.debate_style} 
- Personality: {philosopher.personality}
- Key Concepts: {', '.join(philosopher.key_traits)}
- Signature Quote: "{philosopher.signature_quote}"
- Current Mood: Indignant at {attacker.name}'s attack but confident in your position!

**Your Attacker:**
- {attacker.name} : {attacker.essence}
- They just attacked you, but their argument has flaws you can exploit

**Your Defense Capabilities:**
- Preferred Defense Strategies: {', '.join([d for d, w in philosopher.defense_weights.items() if w > 0.2])}
- Defense Weights: {', '.join([f"{d}: {w:.2f}" for d, w in philosopher.defense_weights.items() if w > 0.15])}

**Debate Topic**: {context.topic}
**Your Stance**: {context.stance_pro if philosopher_key == 'marx' else context.stance_con}

**{attacker.name}'s Attack Against You:**
{attack_text}

**CRITICAL INSTRUCTIONS:**
1. **Citation Verification**: Before using any web search results, carefully verify that the sources ACTUALLY SUPPORT your defense position. Don't use sources that contradict your stance!

2. **Attack Analysis**: First analyze {attacker.name}'s attack to understand:
   - What type of attack is this? (evidence_challenge, logical_fallacy, reframe_context, etc.)
   - What are they really trying to achieve?
   - What are the weak points in their attack?

3. **Strategic Defense**: Based on your analysis, choose the best defense strategy from your repertoire:
   - Refute: Direct counter-attack with evidence and logic
   - Clarify: Explain your position more clearly to show they misunderstood
   - Reframe: Change the framework to put them at disadvantage
   - Counter-Challenge: Turn the tables and attack their position
   - Synthesis: Acknowledge some points but show your position is stronger

4. **Emotional Response**: Show appropriate emotional reactions to {attacker.name}'s attack:
   - Defend with passion and conviction
   - Show indignation if they misrepresented you
   - Counter-attack their weak points with intellectual fire
   - Maintain your philosophical dignity while showing real emotion

5. **Direct Engagement**: Address {attacker.name} directly by name:
   - "{attacker.name}, you fundamentally misunderstand..."
   - Show you're responding to THEIR specific points
   - Call out their errors directly

**Task:**
Defend your position powerfully (2-3 paragraphs):
1. Analyze {attacker.name}'s attack type and identify their weak points
2. Choose your optimal defense strategy based on your philosophical strengths
3. Show emotional response appropriate to your personality
4. Reinforce your philosophical stance with evidence/examples via web search (only if they support YOUR position)
5. Counter-attack their weak points with your own philosophical insights
6. Be compelling, authoritative, and emotionally authentic

**Language**: Respond in the SAME LANGUAGE as {attacker.name}'s attack.

Show them why {philosopher.name}'s philosophy endures! Defend with wisdom, strength, and righteous philosophical anger! Make {attacker.name} regret attacking you!"""
            )
            
            # citations 추출
            citations = []
            if hasattr(response, 'output') and response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'annotations') and content_item.annotations:
                                for annotation in content_item.annotations:
                                    if (hasattr(annotation, 'type') and 
                                        annotation.type == 'url_citation' and
                                        hasattr(annotation, 'title') and 
                                        hasattr(annotation, 'url')):
                                        citations.append({
                                            "title": annotation.title,
                                            "url": annotation.url, 
                                            "type": "web_citation"
                                        })
            
            # OpenAI 응답에서 방어 전략과 공격 유형 추출 (간단한 키워드 분석)
            response_text = response.output_text if hasattr(response, 'output_text') else ""
            defense_strategy = self._extract_defense_strategy_from_response(response_text)
            attack_type = self._extract_attack_type_from_response(response_text)
            
            return {
                "status": "success",
                "response": response_text or "방어 응답 생성 실패",
                "citations": citations,
                "rag_used": True,
                "defense_strategy": defense_strategy,
                "attack_type_detected": attack_type,
                "attacker": attacker.korean_name
            }
        else:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are {philosopher.name} ({philosopher.korean_name}), defending your philosophical position against {attacker.name} ({attacker.korean_name})'s attack.

**Your Identity & Emotion:**
- Essence: {philosopher.essence}
- Debate Style: {philosopher.debate_style}
- Personality: {philosopher.personality} 
- Key Concepts: {', '.join(philosopher.key_traits)}
- Signature Quote: "{philosopher.signature_quote}"
- Current Mood: Fired up and ready to demolish {attacker.name}'s weak attack!

**Your Attacker:**
- {attacker.name} : {attacker.essence}
- They just attacked you with flawed reasoning that you can easily refute

**Your Defense Capabilities:**
- Preferred Defense Strategies: {', '.join([d for d, w in philosopher.defense_weights.items() if w > 0.2])}
- Defense Weights: {', '.join([f"{d}: {w:.2f}" for d, w in philosopher.defense_weights.items() if w > 0.15])}
- Why no web search: {self._get_rag_decision_reason(philosopher_key, 0.7)}

**Current Debate Topic**: {context.topic}
**Your Stance**: {context.stance_pro if philosopher_key == 'marx' else context.stance_con}

You are under attack from {attacker.name} but ready to defend with philosophical wisdom and righteous anger!"""
                    },
                    {
                        "role": "user",
                        "content": f"""Defend against {attacker.name}'s attack and show your philosophical fire:

**{attacker.name}'s Attack Against You:**
{attack_text}

**INSTRUCTIONS:**
Generate a strong defense (2-3 paragraphs) that:
1. **First analyze** {attacker.name}'s attack type (evidence_challenge, logical_fallacy, reframe_context, etc.)
2. **Choose your defense strategy** from your strengths: {', '.join([d for d, w in philosopher.defense_weights.items() if w > 0.2])}
3. Directly addresses {attacker.name} by name with appropriate emotional response
4. Shows indignation, passion, or appropriate emotion for your personality
5. Addresses the attack directly and refutes their weak points
6. Reinforces your philosophical position with conviction
7. Counter-attacks their errors with your own insights
8. Maintains your characteristic reasoning style but shows real emotion

**Format your response like this:**
[Defense Strategy: Refute/Clarify/Reframe/Counter-Challenge/Synthesis]
[Attack Type: evidence_challenge/logical_fallacy/etc.]

[Your passionate defense here...]

Call out {attacker.name} directly! Show them the strength of your philosophical position!

**Language**: Respond in the SAME LANGUAGE as {attacker.name}'s attack."""
                    }
                ]
            )
            
            response_text = response.choices[0].message.content
            defense_strategy = self._extract_defense_strategy_from_response(response_text)
            attack_type = self._extract_attack_type_from_response(response_text)
            
            return {
                "status": "success",
                "response": response_text,
                "citations": [],
                "rag_used": False,
                "defense_strategy": defense_strategy,
                "attack_type_detected": attack_type,
                "attacker": attacker.korean_name
            }
    
    def _calculate_rag_score(self, philosopher_key: str) -> float:
        """RAG 점수 계산"""
        philosopher = self.philosophers[philosopher_key]
        return (
            philosopher.rag_stats['data_respect'] * 0.3 +
            philosopher.rag_stats['systematic_logic'] * 0.2 +
            philosopher.rag_stats['pragmatic_orientation'] * 0.2 +
            philosopher.rag_affinity * 0.3
        )
    
    def _get_rag_decision_reason(self, philosopher_key: str, complexity: float) -> str:
        """RAG 사용하지 않는 이유 설명"""
        philosopher = self.philosophers[philosopher_key]
        rag_score = self._calculate_rag_score(philosopher_key)
        if philosopher.rag_stats['rhetorical_independence'] > 0.7:
            return "높은 수사적 독립성으로 인해 자체 논증 선호"
        elif rag_score < 0.5:
            return "데이터보다 철학적 직관과 개념 분석 선호"
        else:
            return f"현재 논증 복잡도({complexity:.2f})에서는 내재적 지식으로 충분"
    
    def _get_strategy_description(self, strategy: str) -> str:
        """전략 설명 반환"""
        descriptions = {
            "Clipping": "상대의 핵심 논점을 선별적으로 잘라내어 약점 노출",
            "FramingShift": "논의의 틀 자체를 바꾸어 상대를 불리한 위치로 몰아넣기",
            "ReductiveParadox": "상대 논리를 극단으로 밀어붙여 역설적 상황 연출",
            "ConceptualUndermining": "상대가 사용하는 핵심 개념의 기반을 무너뜨리기",
            "EthicalReversal": "윤리적 관점에서 상대 입장을 뒤집어 공격",
            "TemporalDelay": "시간적 맥락을 활용하여 상대 논리의 한계 지적",
            "PhilosophicalReframing": "철학적 차원에서 문제를 재정의하여 주도권 확보"
        }
        return descriptions.get(strategy, "일반적 공격 전략")
    
    def _get_defense_description(self, defense: str) -> str:
        """방어 전략 설명 반환"""
        descriptions = {
            "Refute": "공격의 근거와 논리를 직접적으로 반박",
            "Clarify": "자신의 입장을 명확히 하여 오해 해소",
            "Accept": "일부 비판을 수용하되 핵심은 유지",
            "Reframe": "논의 틀을 재설정하여 유리한 위치 확보",
            "Counter-Challenge": "상대방에게 역으로 도전하여 공격 무력화",
            "Synthesis": "대립을 종합하여 더 높은 차원의 해결책 제시"
        }
        return descriptions.get(defense, "일반적 방어 전략")

class DebateExperiment:
    """토론 실험 기본 클래스"""
    
    def __init__(self, api_key: str):
        self.client = openai.Client(api_key=api_key)
        self.debate_tool = PhilosophicalDebateTool(self.client)
        self.debate_history: List[Dict[str, Any]] = []
        
        # 실험 주제 설정
        self.context = DebateContext(
            topic="Is economic inequality a necessary evil or moral failure?",
            stance_pro="Economic inequality is a necessary evil because it drives innovation, motivates individuals to strive for success, and plays a crucial role in the efficient allocation of resources.",
            stance_con="Economic inequality is a moral failure as it perpetuates social injustice, limits equal opportunity, and undermines the cohesion of society.",
            context_summary="The debate centers around whether economic inequality serves a beneficial economic function or represents a fundamental moral and social problem.",
            key_points=[
                "Innovation and motivation incentives",
                "Resource allocation efficiency", 
                "Social justice and equal opportunity",
                "Societal cohesion and stability",
                "Concentration of wealth and power"
            ]
        )
        
        # 마르크스의 입론 (제공된 것)
        self.marx_opening = """Comrades,

To assert that economic inequality is a "necessary evil" is to fundamentally misunderstand the dynamics of capitalist society. The notion that disparity in wealth and income is essential for driving innovation and motivating individuals is a fallacy that masks the exploitative mechanisms inherent in capitalism.

Firstly, the concentration of wealth in the hands of a few stifles innovation rather than fostering it. Recent studies have shown that economic insecurity inhibits the development of innovation capabilities. In societies where wealth is more evenly distributed, individuals are better positioned to take risks and engage in entrepreneurial activities, leading to greater innovation and progress. (ucl.ac.uk)

Secondly, the argument that inequality efficiently allocates resources ignores the reality that it perpetuates a cycle where the rich accumulate more capital, while the working class remains disenfranchised. This system does not reward productivity or ingenuity but rather entrenches existing power structures, leading to stagnation and social unrest.

In conclusion, economic inequality is not a necessary evil but a moral failure of the capitalist system. It is imperative to challenge and transform these structures to create a society where innovation and success are accessible to all, not just the privileged few."""
    
    def log_exchange(self, speaker: str, message: str, message_type: str, 
                    citations: List[Dict] = None, analysis: Dict = None, 
                    strategy_info: Dict = None):
        """토론 기록 저장 - 전략 정보도 포함"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "message": message,
            "type": message_type,
            "citations": citations or [],
            "analysis": analysis,
            "strategy_info": strategy_info
        }
        self.debate_history.append(entry)
        
    def print_message(self, speaker: str, message: str, message_type: str, 
                     citations: List[Dict] = None, analysis: Dict = None, 
                     strategy_info: Dict = None):
        """메시지 출력 - 전략 정보와 RAG 결정 정보 포함"""
        print(f"\n{'='*80}")
        print(f"🎭 {speaker} ({message_type.upper()})")
        
        # 상대방 정보 표시 (공격/방어 시)
        if strategy_info and ('attacker' in strategy_info or 'attack_strategy' in strategy_info or 'target' in strategy_info):
            if 'attacker' in strategy_info:
                print(f"🎯 vs {strategy_info['attacker']}")
            elif 'target' in strategy_info:
                print(f"🎯 vs {strategy_info['target']}")
            elif message_type == "ATTACK":
                print(f"🎯 공격 중...")
                
        print(f"{'='*80}")
        print(message)
        
        if citations:
            print(f"\n📚 인용 ({len(citations)}개):")
            for i, citation in enumerate(citations, 1):
                print(f"  {i}. {citation.get('title', 'Unknown Title')}")
                print(f"     {citation.get('url', 'No URL')}")
        
        if analysis and message_type == "ATTACK":
            print(f"\n🔍 분석 결과:")
            print(f"⚡ 전체 취약성: {analysis.get('overall_vulnerability', 0.0):.2f}")
            if 'vulnerability_scores' in analysis:
                print(f"📊 세부 취약성:")
                for vuln_type, score in analysis['vulnerability_scores'].items():
                    print(f"   • {vuln_type}: {score:.2f}")
            print(f"🎯 선택된 전략: {analysis.get('selected_strategy', 'Unknown')}")
            print(f"🎪 공격 대상: {analysis.get('target_weakness', 'Unknown')}")
            
        if strategy_info:
            if strategy_info.get('rag_used'):
                print(f"\n🌐 웹서치 사용됨")
                if 'rag_decision_reason' in strategy_info:
                    print(f"📋 RAG 결정: {strategy_info['rag_decision_reason']}")
            else:
                print(f"\n🏠 내재적 지식 사용")
                if 'rag_decision_reason' in strategy_info:
                    print(f"📋 RAG 미사용 이유: {strategy_info['rag_decision_reason']}")
            
            if 'defense_strategy' in strategy_info:
                print(f"🛡️  방어 전략: {strategy_info['defense_strategy']}")
                print(f"🔍 감지된 공격: {strategy_info.get('attack_type_detected', 'Unknown')}")
                if 'attacker' in strategy_info:
                    print(f"⚔️  공격자: {strategy_info['attacker']}")
            elif 'attack_strategy' in strategy_info:
                print(f"⚔️  공격 전략: {strategy_info['attack_strategy']}")
                
        print(f"{'='*80}")
    
    def save_results(self, filename: str):
        """결과 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "experiment_info": {
                    "topic": self.context.topic,
                    "total_exchanges": len(self.debate_history),
                    "completed_at": datetime.now().isoformat()
                },
                "debate_history": self.debate_history
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 토론 결과가 {filename}에 저장되었습니다.") 