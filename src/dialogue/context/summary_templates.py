"""
컨텍스트 요약 템플릿

소스에 대한 객관적인 불렛포인트 요약 생성을 위한 템플릿을 제공합니다.
"""

from typing import Dict, Any

class SummaryTemplates:
    """객관적인 요약 템플릿 모음"""
    
    # 기본 컨텍스트 요약 템플릿
    BASE_CONTEXT_SUMMARY = """
You are tasked with creating a concise, objective summary of the provided context.

CONTEXT TO SUMMARIZE:
{context}

TOPIC: {topic}

Create a summary that:
1. Identifies 3-5 key bullet points most relevant to the topic
2. Presents factual information objectively and neutrally
3. Highlights important data, evidence, and conclusions
4. Keeps each bullet point to 1-2 sentences maximum

Format your response as:
• [Key Point 1]
• [Key Point 2] 
• [Key Point 3]
• [Key Point 4]
• [Key Point 5]

Focus on factual information that provides comprehensive understanding of the topic.
"""

    # 컨텍스트 타입별 특화 템플릿들
    CONTEXT_TYPE_TEMPLATES = {
        "academic_paper": """
You are summarizing an academic paper objectively.

PAPER CONTENT:
{context}

TOPIC: {topic}

Extract key information focusing on:
- Main research findings and conclusions
- Methodological approaches used
- Statistical evidence and data points
- Expert conclusions and implications
- Areas of uncertainty or limitations mentioned

Create 3-5 bullet points in this format:
• [Research Finding/Data Point]
• [Methodological Note]
• [Expert Conclusion]
• [Implication/Application]
• [Limitation/Uncertainty]
""",
        
        "news_article": """
You are summarizing a news article objectively.

ARTICLE CONTENT:
{context}

TOPIC: {topic}

Extract key information focusing on:
- Core facts and events reported
- Different perspectives mentioned
- Statistical data or expert quotes
- Current developments or trends
- Real-world impacts or implications

Create 3-5 bullet points in this format:
• [Core Fact/Event]
• [Stakeholder Perspective]
• [Data/Expert Quote]
• [Current Development]
• [Real-world Impact]
""",
        
        "policy_document": """
You are summarizing a policy document objectively.

DOCUMENT CONTENT:
{context}

TOPIC: {topic}

Extract key information focusing on:
- Official policy positions and rationales
- Implementation details and requirements
- Expected outcomes and success metrics
- Potential challenges or concerns addressed
- Stakeholder impacts and considerations

Create 3-5 bullet points in this format:
• [Policy Position]
• [Implementation Detail]
• [Expected Outcome]
• [Challenge/Concern]
• [Stakeholder Impact]
"""
    }
    
    @classmethod
    def get_template(cls, context_type: str = None) -> str:
        """
        컨텍스트 타입에 맞는 요약 템플릿 반환
        
        Args:
            context_type: 컨텍스트 타입 (academic_paper, news_article, policy_document)
        
        Returns:
            적절한 요약 템플릿
        """
        if context_type:
            return cls.CONTEXT_TYPE_TEMPLATES.get(context_type.lower(), cls.BASE_CONTEXT_SUMMARY)
        
        return cls.BASE_CONTEXT_SUMMARY
    
    @classmethod
    def get_base_template(cls) -> str:
        """기본 컨텍스트 요약 템플릿 반환"""
        return cls.BASE_CONTEXT_SUMMARY 