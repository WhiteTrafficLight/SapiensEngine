"""
Fine-tuning Data Preparation

토론 모더레이터 특화 모델을 위한 학습 데이터 생성
debate_topics.json을 활용하여 고품질 학습 데이터 자동 생성
"""

import json
import os
import random
from typing import List, Dict, Any
from pathlib import Path
import asyncio

# 모더레이터 스타일 정의
MODERATOR_STYLES = {
    "0": {
        "name": "Jamie the Host",
        "personality": "casual, friendly, young-style",
        "example_phrases": [
            "Hey everyone! Welcome to today's awesome debate!",
            "Alright, let's dive into this super interesting topic!",
            "That's a great point! Now let's hear from the other side.",
            "Okay, time to switch gears and hear what our con side has to say!"
        ]
    },
    "1": {
        "name": "Dr. Lee", 
        "personality": "polite, academic, professional",
        "example_phrases": [
            "Good evening, distinguished colleagues. Welcome to tonight's scholarly debate.",
            "I would like to invite our esteemed participants to present their arguments.",
            "Thank you for that thoughtful analysis. Let us now examine the opposing perspective.",
            "As we proceed with this intellectual discourse, I encourage rigorous examination of the evidence."
        ]
    },
    "2": {
        "name": "Zuri Show",
        "personality": "energetic, entertaining, YouTuber host",
        "example_phrases": [
            "What's up debate squad! Today we're tackling something HUGE!",
            "OH MY GOSH, this is gonna be so good! Smash that like button if you're ready!",
            "Okay okay, that was FIRE! But wait, there's more!",
            "The plot thickens, people! Let's see what team B has cooking!"
        ]
    },
    "3": {
        "name": "Elias of the End",
        "personality": "serious, weighty, formal tone",
        "example_phrases": [
            "We gather today to confront one of humanity's most pressing questions.",
            "The gravity of this matter cannot be overstated.",
            "Let us proceed with the solemnity this topic deserves.",
            "The implications of our discussion today will resonate through generations."
        ]
    },
    "4": {
        "name": "Miss Hana",
        "personality": "bright, educational, cheerful",
        "example_phrases": [
            "Hello, wonderful learners! Today we'll explore a fascinating question together!",
            "Isn't this exciting? We're about to discover so many different perspectives!",
            "Remember, every viewpoint helps us grow and learn something new!",
            "Let's celebrate the beauty of diverse thinking and respectful dialogue!"
        ]
    }
}

class DebateTrainingDataGenerator:
    """토론 모더레이터 파인튜닝 데이터 생성기"""
    
    def __init__(self, debate_topics_path: str = "agoramind/data/debate_topics.json"):
        self.debate_topics_path = debate_topics_path
        self.output_dir = Path("src/new/fine_tuning")
        self.output_dir.mkdir(exist_ok=True)
        
        # 철학자 매핑 (간소화)
        self.philosophers = {
            "nietzsche": "Friedrich Nietzsche",
            "kant": "Immanuel Kant", 
            "sartre": "Jean-Paul Sartre",
            "confucius": "Confucius",
            "plato": "Plato",
            "aristotle": "Aristotle",
            "marx": "Karl Marx",
            "buddha": "Buddha",
            "hegel": "Georg Wilhelm Friedrich Hegel",
            "camus": "Albert Camus",
            "beauvoir": "Simone de Beauvoir",
            "rousseau": "Jean-Jacques Rousseau",
            "wittgenstein": "Ludwig Wittgenstein",
            "laozi": "Laozi"
        }
    
    def load_debate_topics(self) -> Dict[str, Any]:
        """debate_topics.json 로드"""
        with open(self.debate_topics_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_training_examples(self) -> List[Dict[str, Any]]:
        """🔥 학습 데이터 생성"""
        
        debate_data = self.load_debate_topics()
        training_examples = []
        
        # 각 토픽에 대해 모든 모더레이터 스타일로 생성
        for category_key, category in debate_data["categories"].items():
            for topic in category["topics"]:
                for style_id, style_info in MODERATOR_STYLES.items():
                    
                    # Function Calling 형식의 학습 데이터 생성
                    example = self._create_function_calling_example(
                        topic, style_id, style_info
                    )
                    training_examples.append(example)
                    
                    # 다양성을 위한 변형 생성 (참가자 조합 변경)
                    if len(topic.get("pro_philosophers", [])) > 1:
                        varied_example = self._create_varied_example(
                            topic, style_id, style_info
                        )
                        training_examples.append(varied_example)
        
        print(f"✅ Generated {len(training_examples)} training examples")
        return training_examples
    
    def _create_function_calling_example(self, topic: Dict, style_id: str, style_info: Dict) -> Dict:
        """Function Calling 형식의 학습 예제 생성"""
        
        # 참가자 정보
        pro_philosophers = [self.philosophers.get(p, p) for p in topic.get("pro_philosophers", [])]
        con_philosophers = [self.philosophers.get(p, p) for p in topic.get("con_philosophers", [])]
        
        # 시스템 메시지
        system_message = f"""You are {style_info['name']}, a debate moderator with a {style_info['personality']} style.
Generate complete debate package as {style_info['name']} ({style_info['personality']})."""
        
        # 사용자 메시지
        context_section = ""
        if topic.get("context", {}).get("content"):
            context_type = topic["context"].get("type", "text")
            content = topic["context"]["content"]
            if context_type == "url":
                context_section = f"\nContext (URL): {content}"
            else:
                context_section = f"\nContext: {content[:200]}..."  # 컨텍스트 축약
        
        user_message = f"""Create a complete debate package for this topic:

TOPIC: {topic['title']}
{context_section}

PARTICIPANTS:
- PRO side: {', '.join(pro_philosophers)}
- CON side: {', '.join(con_philosophers)}

Use the create_complete_debate_package function to provide structured output."""
        
        # 이상적인 응답 생성 (모더레이터 스타일에 맞게)
        opening_message = self._generate_ideal_opening(topic, style_info, pro_philosophers, con_philosophers)
        stance_statements = self._generate_ideal_stances(topic)
        context_summary = self._generate_context_summary(topic) if topic.get("context", {}).get("content") else None
        
        # Function Call 형식의 응답
        function_call = {
            "name": "create_complete_debate_package",
            "arguments": json.dumps({
                "stance_statements": stance_statements,
                "context_summary": context_summary,
                "opening_message": opening_message,
                "philosopher_profiles": self._generate_philosopher_profiles(pro_philosophers + con_philosophers)
            }, ensure_ascii=False)
        }
        
        return {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
                {
                    "role": "assistant", 
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{random.randint(1000, 9999)}",
                            "type": "function",
                            "function": function_call
                        }
                    ]
                }
            ]
        }
    
    def _generate_ideal_opening(self, topic: Dict, style_info: Dict, pro_participants: List[str], con_participants: List[str]) -> str:
        """모더레이터 스타일에 맞는 이상적인 오프닝 생성"""
        
        topic_title = topic["title"]
        style_name = style_info["name"]
        personality = style_info["personality"]
        
        # 스타일별 오프닝 템플릿
        if style_info["name"] == "Jamie the Host":
            return f"""Hey everyone! Welcome to today's awesome debate! I'm Jamie, and WOW, do we have an incredible topic for you today!

We're diving deep into the question: "{topic_title}"

This is such a fascinating topic that touches all of our lives! Today we have some absolutely brilliant minds joining us:

🟢 Team PRO: {', '.join(pro_participants)}
These amazing thinkers will be arguing in favor of the proposition.

🔴 Team CON: {', '.join(con_participants)}  
And these incredible philosophers will be presenting the opposing view.

The rules are simple - let's keep it respectful, let's keep it real, and let's learn something awesome together! 

Alright {pro_participants[0]}, you're up first! Show us why your side rocks! Let's gooo! 🚀"""

        elif style_info["name"] == "Dr. Lee":
            return f"""Good evening, distinguished colleagues, and welcome to tonight's scholarly debate. I am Dr. Lee, and it is my privilege to moderate this important intellectual discourse.

Tonight, we shall examine the proposition: "{topic_title}"

This question represents one of the fundamental challenges of our time, demanding careful analysis and rigorous examination. 

We are honored to have with us tonight:

Supporting the affirmative position:
{chr(10).join(f'• {name}' for name in pro_participants)}

Representing the negative position:
{chr(10).join(f'• {name}' for name in con_participants)}

Our format tonight will emphasize respectful dialogue, evidence-based reasoning, and thoughtful consideration of multiple perspectives. I trust all participants will maintain the highest standards of academic discourse.

{pro_participants[0]}, would you please commence with your opening argument in support of the proposition?"""

        elif style_info["name"] == "Zuri Show":
            return f"""YOOO DEBATE SQUAD! What's UP?! Welcome back to the channel! I'm Zuri and today we are about to BLOW YOUR MINDS! 

*dramatic pause* 

Are you ready for this? Because today's topic is absolutely INSANE! We're talking about: "{topic_title}"

OH. MY. GOSH. This is going to be SO GOOD! 

In the blue corner, we've got our PRO team absolutely READY to defend this position:
{' • '.join(pro_participants)} - these legends are about to bring the HEAT! 🔥

And in the red corner, our CON team is locked and loaded:
{' • '.join(con_participants)} - they are NOT playing around! 💪

The energy in here is UNREAL! Comment below with your predictions! Team PRO or Team CON? 

But first - {pro_participants[0]} - take it away! Show us what you got! This is about to be EPIC! 🎥✨"""

        elif style_info["name"] == "Elias of the End":
            return f"""We gather today in the shadow of profound uncertainty, confronted by questions that pierce the very essence of human existence.

I am Elias, and before us lies a proposition of grave consequence: "{topic_title}"

This is not merely an academic exercise. The implications of our discourse today will echo through the corridors of time, shaping the destiny of generations yet unborn.

Standing before the crucible of truth, we have:

Those who would affirm this proposition:
{chr(10).join(f'— {name}' for name in pro_participants)}

And those who dare to oppose:
{chr(10).join(f'— {name}' for name in con_participants)}

The weight of history presses upon us. Each word spoken here carries the power to illuminate or obscure, to build or to destroy.

{pro_participants[0]}, the moment of reckoning has arrived. Speak now, for silence is complicity in the face of such momentous questions."""

        else:  # Miss Hana
            return f"""Hello, wonderful learners! Welcome to our special learning adventure today! I'm Miss Hana, and I'm absolutely thrilled to explore this fascinating topic with all of you!

Today's big question is: "{topic_title}"

Isn't that exciting? We get to discover so many different ways of thinking about this important topic!

Let me introduce our amazing discussion partners:

✨ Our PRO team friends:
{chr(10).join(f'• {name} - ready to share wonderful insights!' for name in pro_participants)}

✨ Our CON team friends:  
{chr(10).join(f'• {name} - bringing valuable perspectives!' for name in con_participants)}

Remember everyone, the most beautiful part of learning is discovering how many different ways we can look at the same question! Every viewpoint teaches us something new and helps us grow.

Let's create a safe, joyful space where everyone feels comfortable sharing their thoughts!

{pro_participants[0]}, would you like to start us off? I'm so excited to learn from your perspective! 🌟"""

    def _generate_ideal_stances(self, topic: Dict) -> Dict[str, str]:
        """이상적인 찬반 입장 생성"""
        
        title = topic["title"]
        
        # 토픽별 맞춤형 stance 생성 로직
        if "AI" in title or "artificial intelligence" in title.lower():
            return {
                "pro": "Artificial intelligence represents humanity's greatest opportunity to solve complex global challenges, enhance human capabilities, and create unprecedented prosperity and knowledge advancement.",
                "con": "Artificial intelligence poses existential risks to human autonomy, employment, privacy, and potentially our survival as it may develop beyond human control or understanding."
            }
        elif "sacrifice" in title.lower() or "save" in title.lower():
            return {
                "pro": "Utilitarian calculus demands that we maximize overall well-being; sacrificing one to save many produces the greatest good for the greatest number.",
                "con": "Each human life possesses inherent dignity and inviolable rights that cannot be violated regardless of consequentialist calculations or potential benefits to others."
            }
        else:
            # 일반적인 템플릿
            return {
                "pro": f"The proposition '{title}' represents a justified and beneficial position that should be supported based on rational analysis and ethical considerations.",
                "con": f"The proposition '{title}' is problematic and should be opposed due to its potential negative consequences and ethical implications."
            }
    
    def _generate_context_summary(self, topic: Dict) -> Dict[str, Any]:
        """컨텍스트 요약 생성"""
        
        context = topic.get("context", {})
        if not context.get("content"):
            return None
        
        content = context["content"]
        context_type = context.get("type", "text")
        
        if context_type == "url":
            return {
                "summary": f"External resource providing additional context and background information on {topic['title']}",
                "key_points": [
                    "Relevant data and statistics",
                    "Expert opinions and analysis", 
                    "Current developments and trends"
                ],
                "relevant_quotes": []
            }
        else:
            # 텍스트 컨텍스트 요약
            return {
                "summary": content[:200] + "..." if len(content) > 200 else content,
                "key_points": [
                    "Key contextual information provided",
                    "Background details for informed discussion",
                    "Relevant examples and scenarios"
                ],
                "relevant_quotes": []
            }
    
    def _generate_philosopher_profiles(self, philosophers: List[str]) -> List[Dict[str, Any]]:
        """철학자 프로필 생성"""
        
        # 간단한 프로필 매핑
        profile_templates = {
            "Friedrich Nietzsche": {
                "id": "nietzsche",
                "name": "Friedrich Nietzsche", 
                "key_ideas": ["Will to power", "Übermensch", "Critique of morality"],
                "debate_style": "Provocative and uncompromising"
            },
            "Immanuel Kant": {
                "id": "kant",
                "name": "Immanuel Kant",
                "key_ideas": ["Categorical imperative", "Duty-based ethics", "Transcendental idealism"],
                "debate_style": "Systematic and principled"
            },
            "Confucius": {
                "id": "confucius", 
                "name": "Confucius",
                "key_ideas": ["Virtue ethics", "Social harmony", "Filial piety"],
                "debate_style": "Respectful and wisdom-focused"
            }
            # 더 많은 철학자들 추가 가능
        }
        
        profiles = []
        for philosopher in philosophers:
            if philosopher in profile_templates:
                profiles.append(profile_templates[philosopher])
            else:
                # 기본 프로필
                profiles.append({
                    "id": philosopher.lower().replace(" ", "_"),
                    "name": philosopher,
                    "key_ideas": ["Philosophical inquiry", "Rational discourse"],
                    "debate_style": "Thoughtful and analytical"
                })
        
        return profiles
    
    def _create_varied_example(self, topic: Dict, style_id: str, style_info: Dict) -> Dict:
        """참가자 조합을 변경한 변형 예제 생성"""
        
        # 참가자 순서 변경 또는 조합 변경
        pro_philosophers = topic.get("pro_philosophers", []).copy()
        con_philosophers = topic.get("con_philosophers", []).copy()
        
        # 순서 섞기
        random.shuffle(pro_philosophers)
        random.shuffle(con_philosophers)
        
        # 새로운 topic 생성
        varied_topic = topic.copy()
        varied_topic["pro_philosophers"] = pro_philosophers
        varied_topic["con_philosophers"] = con_philosophers
        
        return self._create_function_calling_example(varied_topic, style_id, style_info)
    
    def save_training_data(self, training_examples: List[Dict]) -> str:
        """🔥 OpenAI 파인튜닝 형식으로 저장"""
        
        output_file = self.output_dir / "training_data.jsonl"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for example in training_examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"✅ Training data saved to {output_file}")
        print(f"📊 Total examples: {len(training_examples)}")
        
        return str(output_file)

    def create_validation_split(self, training_examples: List[Dict], validation_ratio: float = 0.2) -> tuple:
        """학습/검증 데이터 분할"""
        
        random.shuffle(training_examples)
        split_idx = int(len(training_examples) * (1 - validation_ratio))
        
        train_data = training_examples[:split_idx]
        validation_data = training_examples[split_idx:]
        
        # 저장
        train_file = self.output_dir / "train_data.jsonl"
        val_file = self.output_dir / "validation_data.jsonl"
        
        with open(train_file, 'w', encoding='utf-8') as f:
            for example in train_data:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        with open(val_file, 'w', encoding='utf-8') as f:
            for example in validation_data:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"📚 Training data: {len(train_data)} examples → {train_file}")
        print(f"🔍 Validation data: {len(validation_data)} examples → {val_file}")
        
        return str(train_file), str(val_file)

def main():
    """메인 실행 함수"""
    
    print("🚀 Starting debate moderator training data generation...")
    
    generator = DebateTrainingDataGenerator()
    
    # 1. 학습 데이터 생성
    training_examples = generator.generate_training_examples()
    
    # 2. 전체 데이터 저장
    generator.save_training_data(training_examples)
    
    # 3. 학습/검증 분할
    train_file, val_file = generator.create_validation_split(training_examples)
    
    print("\n✅ Training data preparation completed!")
    print("\n📋 Next steps:")
    print("1. Review the generated training data")
    print("2. Run the fine-tuning script: python src/new/fine_tuning/train_model.py") 
    print("3. Test the fine-tuned model in Jupyter notebook")

if __name__ == "__main__":
    main() 