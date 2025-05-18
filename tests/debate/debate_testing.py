import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import random  # 임의 감정 생성시 사용

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(Path(__file__).parent.parent.parent.absolute())))

# Import necessary modules
try:
    from sapiens_engine.core.llm_manager import LLMManager
    from sapiens_engine.core.config_loader import ConfigLoader
except ImportError:
    print("Warning: Sapiens engine core modules not found. Using direct imports.")
    from core.llm_manager import LLMManager
    from core.config_loader import ConfigLoader

# 완전히 내부에 구현된 감정 추론 함수, 외부 의존성 제거
def infer_emotion_from_context(llm_manager, speaker_id, speaker_name, recent_messages, topic="", speaker_personality=""):
    """
    Custom emotion inference function implemented directly in debate_testing.py
    Returns a simplified emotion state based on recent messages and NPC character
    No external module dependencies
    """
    try:
        # Format conversation history to text
        history_text = ""
        for entry in recent_messages[-3:]:  # Just use last 3 messages for context
            speaker = entry.get("speaker_name", "Unknown")
            text = entry.get("text", "")
            history_text += f"{speaker}: {text}\n\n"
        
        # Create simple prompt to ask about emotion
        system_prompt = f"""
        You are a debate assistant analyzing the emotional state of philosophers in a debate.
        Based on the recent dialogue and the philosopher's character, predict their emotional state.
        Keep your response short (1-2 sentences) focusing just on their emotional state and speaking tone.
        """
        
        user_prompt = f"""
        Philosopher: {speaker_name}
        Description: {speaker_personality}
        
        Debate Topic: {topic}
        
        Recent Conversation:
        {history_text}
        
        Based on the conversation so far and {speaker_name}'s philosophical character, what emotional state would they be in now, and what tone would they use in their next response? Answer in 1-2 sentences.
        """
        
        # LLM generates the emotion prediction
        start_time = time.time()
        response = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=200
        )
        generation_time = time.time() - start_time
        
        # Default emotion state
        emotion_state = {
            "primary_emotion": "analytical",  # Default
            "intensity": "MODERATE",
            "intensity_value": 3
        }
        
        print(f"Emotion inference took {generation_time:.2f} seconds")
        
        return {
            "emotion_state": emotion_state,
            "prompt_enhancement": response.strip()  # Use LLM's description as the enhancement
        }
    except Exception as e:
        print(f"Custom emotion inference failed: {str(e)}")
        return {
            "emotion_state": {
                "primary_emotion": "neutral",
                "intensity": "NEUTRAL",
                "intensity_value": 0,
            },
            "prompt_enhancement": "Express your philosophical perspective with a neutral tone."
        }

def apply_emotion_to_prompt(prompt, prompt_enhancement, emotion_data=None):
    """
    Custom function to apply emotion to a prompt
    Simply appends the prompt enhancement to the original prompt
    No external module dependencies
    """
    if not prompt_enhancement:
        return prompt
        
    # Add emotion guidance to the prompt
    if prompt.strip().endswith("."):
        enhanced_prompt = prompt + "\n\n"
    else:
        enhanced_prompt = prompt + ".\n\n"
        
    enhanced_prompt += f"Emotional context: {prompt_enhancement}"
    return enhanced_prompt

# Initialize config and LLM manager
config_loader = ConfigLoader()
llm_manager = LLMManager(config_loader)

# Dictionary of philosophers for testing
PHILOSOPHERS = {
    "socrates": {"name": "Socrates", "description": "Socrates was an Ancient Greek philosopher known for the Socratic method of questioning."},
    "plato": {"name": "Plato", "description": "Plato was an Ancient Greek philosopher, student of Socrates, and founder of the Academy."},
    "aristotle": {"name": "Aristotle", "description": "Aristotle was an Ancient Greek philosopher, student of Plato, known for empiricism and systematic knowledge."},
    "kant": {"name": "Kant", "description": "Kant was an 18th century German philosopher known for his work on ethics and metaphysics."},
    "nietzsche": {"name": "Nietzsche", "description": "Nietzsche was a 19th century German philosopher known for his critique of morality and religion."},
    "marx": {"name": "Marx", "description": "Marx was a 19th century German philosopher, economist, and political theorist."},
    "sartre": {"name": "Sartre", "description": "Sartre was a 20th century French existentialist philosopher and writer."},
    "camus": {"name": "Camus", "description": "Camus was a 20th century French philosopher associated with absurdism."},
    "beauvoir": {"name": "de Beauvoir", "description": "Simone de Beauvoir was a 20th century French philosopher and feminist theorist."},
    "hegel": {"name": "Hegel", "description": "Hegel was a German philosopher known for his dialectical method of thinking."}
}

# Utility functions
def print_step(message):
    """Print a step header"""
    print("\n" + "="*80)
    print(f" {message}")
    print("="*80)

def print_message(speaker, role, text, generation_time=None):
    """Print a debate message with clear formatting"""
    print("\n" + "-"*80)
    print(f"| {speaker} ({role})")
    print("-"*80)
    print(text)
    print("-"*80)
    
    # Add generation time if provided
    if generation_time is not None:
        print(f"Message generation time: {generation_time:.2f} seconds")
    
    print("END OF MESSAGE\n")

# Add a safe API call function to handle errors
def safe_llm_call(system_prompt, user_prompt, max_tokens=2000, default_response="API call failed. Please check your API quota."):
    """Make an LLM API call with error handling"""
    start_time = time.time()
    try:
        response = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens
        )
        generation_time = time.time() - start_time
        return response, generation_time
    except Exception as e:
        print(f"LLM API call failed: {str(e)}")
        generation_time = time.time() - start_time
        return default_response, generation_time

# Step 1: Function to generate stance statements from a topic
async def generate_stance_statements(topic: str, context: str = "") -> Dict[str, str]:
    """Get pro and con stances from a topic"""
    print_step(f"Generating stance statements for topic: {topic}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    system_prompt = f"""
    You are a debate preparation assistant. Your task is to analyze the given topic and create clear stance statements for both PRO and CON positions.
    Format your response as JSON with the following structure:
    {{
        "pro_statement": "Clear statement supporting the position...",
        "con_statement": "Clear statement opposing the position..."
    }}
    Keep each statement concise (1-2 sentences) and strongly articulated.
    {language_instruction}
    """
    
    user_prompt = f"Topic: {topic}\n\nContext: {context}"
    
    # LLM API call with error handling
    start_time = time.time()
    try:
        response = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000
        )
        generation_time = time.time() - start_time
    except Exception as e:
        print(f"LLM API call failed: {str(e)}")
        response = '{"pro_statement": "This topic has merit and should be supported.", "con_statement": "This topic has flaws and should be opposed."}'
        generation_time = time.time() - start_time
    
    # Parse JSON response
    try:
        result = json.loads(response)
        pro_statement = result.get("pro_statement", "")
        con_statement = result.get("con_statement", "")
        
        print_message("System", "Stance Generator", f"PRO: {pro_statement}\n\nCON: {con_statement}", generation_time)
        
        return {
            "pro": pro_statement,
            "con": con_statement
        }
    except json.JSONDecodeError:
        print(f"Failed to parse stance statements JSON: {response}")
        # Return defaults
        return {
            "pro": f"{topic} is true and beneficial.",
            "con": f"{topic} is false and harmful."
        }

# Step 2: Generate moderator opening
def generate_moderator_opening(topic: str, context: str, pro_side: List[str], con_side: List[str]) -> str:
    """Generate a moderator opening statement for the debate"""
    print_step("Generating moderator opening statement")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    # Construct participants names
    pro_names = [PHILOSOPHERS[p]["name"] for p in pro_side if p in PHILOSOPHERS]
    con_names = [PHILOSOPHERS[p]["name"] for p in con_side if p in PHILOSOPHERS]
    
    system_prompt = f"""
    You are a professional debate moderator. Your task is to create an opening statement for a debate on the given topic.
    
    Write a natural introduction that:
    1. Introduces the topic and its importance
    2. Presents the debaters and their sides (pro/con)
    3. Briefly explains the rules of the debate
    4. Clearly states the pro and con positions
    5. Designates the first speaker (from the pro side)
    
    Use a formal but engaging tone appropriate for an intellectual debate.
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Background Information: {context if context else "No additional background information provided."}
    
    Pro Side Participants: {', '.join(pro_names)}
    Con Side Participants: {', '.join(con_names)}
    
    First Speaker: {pro_names[0] if pro_names else 'Pro side speaker'}
    
    Please write your opening remarks as debate moderator based on this information.
    """
    
    start_time = time.time()
    opening_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message("Moderator", "Opening", opening_text, generation_time)
    return opening_text

# Step 3: Generate pro and con arguments
def generate_philosopher_argument(
    philosopher_id: str, 
    topic: str, 
    context: str, 
    side: str, 
    debate_history: List[Dict],
    use_emotion: bool = False
) -> str:
    """Generate a philosopher's argument"""
    print_step(f"Generating {side} argument for {philosopher_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    # Base prompt
    system_prompt = f"""
    You are the philosopher {philosopher['name']}. {philosopher['description']}
    
    You hold a {side} position on the given debate topic.
    As a philosopher, reflect your philosophical background, ideas, and methodology in your participation.
    
    When speaking, consider:
    1. Present arguments consistent with your philosophical viewpoint
    2. Use concrete examples or metaphors to enhance persuasiveness
    3. Maintain a logical structure with clear key points
    4. Respond appropriately to previous speakers' arguments
    5. Incorporate your distinctive philosophical terms or concepts
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    Background Information: {context if context else "No additional background information provided."}
    
    Your Position: {side} side ({"supporting" if side == "pro" else "opposing"} the proposition)
    
    Previous Debate Content:
    {history_text}
    
    It is now your ({philosopher['name']}) turn to speak. Present a compelling argument from the {"pro" if side == "pro" else "con"} perspective.
    """
    
    start_time = time.time()
    argument_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message(philosopher['name'], f"{side} Argument", argument_text, generation_time)
    return argument_text

# Step 4: Generate moderator summary
def generate_moderator_summary(topic: str, debate_history: List[Dict]) -> str:
    """Generate a moderator summary of the debate"""
    print_step("Generating moderator summary")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    # Format debate history
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = f"""
    You are a professional debate moderator. Your task is to summarize the key points from the debate that has just occurred.
    
    In your summary:
    1. Objectively present the main arguments from both sides
    2. Highlight key points of contention between debaters
    3. Note any areas of consensus
    4. Maintain neutrality without favoring either side
    5. Synthesize the discussion into coherent themes
    
    Use a concise, clear, and balanced approach in your summary.
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Debate Content:
    {history_text}
    
    Please provide a comprehensive summary of the key arguments and points raised by both sides in this debate.
    """
    
    start_time = time.time()
    summary_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message("Moderator", "Summary", summary_text, generation_time)
    return summary_text

# Step 5: Generate rebuttal
def generate_rebuttal(
    philosopher_id: str,
    topic: str,
    context: str,
    side: str,
    debate_history: List[Dict]
) -> str:
    """Generate a philosopher's rebuttal"""
    print_step(f"Generating {side} rebuttal for {philosopher_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        side_info = entry.get("side", "")
        text = entry.get("text", "")
        history_text += f"{speaker_name} ({side_info}): {text}\n\n"
    
    opposite_side = "con" if side == "pro" else "pro"
    
    system_prompt = f"""
    You are the philosopher {philosopher['name']}. {philosopher['description']}
    
    You hold a {side} position on the given debate topic.
    This is the rebuttal phase where you need to counter the arguments made by the opposite side.
    
    When making your rebuttal:
    1. Clearly identify the main arguments of the opposing side
    2. Point out logical fallacies or weaknesses in their arguments
    3. Explain why their position is inadequate from your perspective
    4. Provide counter-examples or evidence that challenges their claims
    5. Remain consistent with your philosophical background and approach
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    Background Information: {context if context else "No additional background information provided."}
    
    Your Position: {side} side ({"supporting" if side == "pro" else "opposing"} the proposition)
    Position to Rebut: {opposite_side} side ({"supporting" if opposite_side == "pro" else "opposing"} the proposition)
    
    Previous Debate Content:
    {history_text}
    
    It is now your ({philosopher['name']}) turn to speak. Present a focused rebuttal against the {opposite_side} side's arguments.
    """
    
    start_time = time.time()
    rebuttal_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message(philosopher['name'], f"{side} Rebuttal", rebuttal_text, generation_time)
    return rebuttal_text

# Step 5b: Generate emotional rebuttal
def generate_emotional_rebuttal(
    philosopher_id: str,
    topic: str,
    context: str,
    side: str,
    debate_history: List[Dict]
) -> str:
    """Generate a philosopher's emotional rebuttal using emotion inference"""
    print_step(f"Generating emotional {side} rebuttal for {philosopher_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        side_info = entry.get("side", "")
        text = entry.get("text", "")
        history_text += f"{speaker_name} ({side_info}): {text}\n\n"
    
    # Infer emotion from debate history - measure time
    emotion_inference_start = time.time()
    try:
        emotion_info = infer_emotion_from_context(
            llm_manager=llm_manager,
            speaker_id=philosopher_id,
            speaker_name=philosopher['name'],
            recent_messages=debate_history[-5:] if len(debate_history) > 5 else debate_history,
            topic=topic,
            speaker_personality=philosopher['description']
        )
        
        # Extract emotion information
        emotion_state = emotion_info.get("emotion_state", {})
        primary_emotion = emotion_state.get("primary_emotion", "neutral")
        intensity = emotion_state.get("intensity", "NEUTRAL")
        prompt_enhancement = emotion_info.get("prompt_enhancement", "")
        
        emotion_inference_time = time.time() - emotion_inference_start
        print(f"Inferred emotion/tone: {prompt_enhancement}")
        print(f"Emotion inference time: {emotion_inference_time:.2f} seconds")
    except Exception as e:
        print(f"Emotion inference failed: {str(e)}")
        primary_emotion = "neutral"
        intensity = "NEUTRAL"
        prompt_enhancement = "Express your philosophical perspective with a neutral tone."
        emotion_state = {"primary_emotion": primary_emotion, "intensity": intensity}
    
    opposite_side = "con" if side == "pro" else "pro"
    
    system_prompt = f"""
    You are the philosopher {philosopher['name']}. {philosopher['description']}
    
    You hold a {side} position on the given debate topic.
    This is the rebuttal phase where you need to counter the arguments made by the opposite side.
    
    {prompt_enhancement}
    
    When making your rebuttal:
    1. Clearly identify the main arguments of the opposing side
    2. Point out logical fallacies or weaknesses in their arguments
    3. Explain why their position is inadequate from your perspective
    4. Provide counter-examples or evidence that challenges their claims
    5. Remain consistent with your philosophical background and approach
    6. Express your points with the emotional tone indicated above
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    Background Information: {context if context else "No additional background information provided."}
    
    Your Position: {side} side ({"supporting" if side == "pro" else "opposing"} the proposition)
    Position to Rebut: {opposite_side} side ({"supporting" if opposite_side == "pro" else "opposing"} the proposition)
    
    Previous Debate Content:
    {history_text}
    
    It is now your ({philosopher['name']}) turn to speak. Present a focused rebuttal against the {opposite_side} side's arguments.
    """
    
    # Apply emotion to prompt using our function
    user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement, emotion_state)
    
    # Make the API call with time measurement
    start_time = time.time()
    try:
        rebuttal_text = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000
        )
        generation_time = time.time() - start_time
    except Exception as e:
        print(f"LLM API call failed: {str(e)}")
        rebuttal_text = f"[As {philosopher['name']}, I would present a rebuttal against the {opposite_side} position, but I'm unable to generate it at this moment due to technical limitations.]"
        generation_time = time.time() - start_time
    
    # Total time including emotion inference
    total_time = generation_time + (time.time() - emotion_inference_start)
    
    print_message(philosopher['name'], f"{side} Rebuttal", rebuttal_text, total_time)
    return rebuttal_text

# Step 6: Generate cross-examination questions
def generate_cross_examination_question(
    questioner_id: str,
    target_id: str, 
    topic: str,
    debate_history: List[Dict]
) -> str:
    """Generate a cross-examination question"""
    print_step(f"Generating cross-examination question from {questioner_id} to {target_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher"})
    target = PHILOSOPHERS.get(target_id, {"name": target_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history[-5:]:  # Use last 5 messages
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = f"""
    You are the philosopher {questioner["name"]}. {questioner["description"]}
    
    In this cross-examination phase, you are to pose critical questions to {target["name"]} or point out weaknesses in their arguments.
    Reflect your philosophical background, ideas, and methodology in your questioning.
    
    When formulating your question:
    1. Identify logical inconsistencies or weaknesses in the opponent's arguments
    2. Critically analyze their assumptions or premises
    3. Highlight potential negative implications of their position
    4. Draw from your own philosophical framework to challenge their stance
    5. Be respectful but philosophically penetrating in your questioning
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({questioner["name"]}) turn to pose a question. Formulate a critical question or highlight a weakness in {target["name"]}'s arguments.
    Begin by directly addressing {target["name"]} in your question.
    """
    
    start_time = time.time()
    question_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message(questioner['name'], "Question", question_text, generation_time)
    return question_text

# Step 6b: Generate emotional cross-examination question
def generate_emotional_cross_examination_question(
    questioner_id: str,
    target_id: str, 
    topic: str,
    debate_history: List[Dict]
) -> str:
    """Generate an emotional cross-examination question using emotion inference"""
    print_step(f"Generating emotional cross-examination question from {questioner_id} to {target_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher"})
    target = PHILOSOPHERS.get(target_id, {"name": target_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history[-5:]:  # Use last 5 messages
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    # Infer emotion from debate history - measure time
    emotion_inference_start = time.time()
    try:
        emotion_info = infer_emotion_from_context(
            llm_manager=llm_manager,
            speaker_id=questioner_id,
            speaker_name=questioner['name'],
            recent_messages=debate_history[-5:] if len(debate_history) > 5 else debate_history,
            topic=topic,
            speaker_personality=questioner['description']
        )
        
        # Extract emotion information
        emotion_state = emotion_info.get("emotion_state", {})
        primary_emotion = emotion_state.get("primary_emotion", "neutral")
        intensity = emotion_state.get("intensity", "NEUTRAL")
        prompt_enhancement = emotion_info.get("prompt_enhancement", "")
        
        emotion_inference_time = time.time() - emotion_inference_start
        print(f"Inferred emotion/tone: {prompt_enhancement}")
        print(f"Emotion inference time: {emotion_inference_time:.2f} seconds")
    except Exception as e:
        print(f"Emotion inference failed: {str(e)}")
        primary_emotion = "neutral"
        intensity = "NEUTRAL"
        prompt_enhancement = "Express your philosophical perspective with a neutral tone."
        emotion_state = {"primary_emotion": primary_emotion, "intensity": intensity}
    
    system_prompt = f"""
    You are the philosopher {questioner["name"]}. {questioner["description"]}
    
    {prompt_enhancement}
    
    In this cross-examination phase, you are to pose critical questions to {target["name"]} or point out weaknesses in their arguments.
    Reflect your philosophical background, ideas, methodology, and current emotional state in your questioning.
    
    When formulating your question:
    1. Identify logical inconsistencies or weaknesses in the opponent's arguments
    2. Critically analyze their assumptions or premises
    3. Highlight potential negative implications of their position
    4. Draw from your own philosophical framework to challenge their stance
    5. Be respectful but philosophically penetrating in your questioning
    6. Express your points with the emotional tone indicated above
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({questioner["name"]}) turn to pose a question. Formulate a critical question or highlight a weakness in {target["name"]}'s arguments.
    Begin by directly addressing {target["name"]} in your question.
    """
    
    # Apply emotion to prompt using our function
    user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement, emotion_state)
    
    # Make the API call with time measurement
    start_time = time.time()
    try:
        question_text = llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2000
        )
        generation_time = time.time() - start_time
    except Exception as e:
        print(f"LLM API call failed: {str(e)}")
        question_text = f"[As {questioner['name']}, I would ask a question to {target['name']}, but I'm unable to generate it at this moment due to technical limitations.]"
        generation_time = time.time() - start_time
    
    # Total time including emotion inference
    total_time = generation_time + (time.time() - emotion_inference_start)
    
    print_message(questioner['name'], "Question", question_text, total_time)
    return question_text

# Step 7: Generate cross-examination response
def generate_cross_examination_response(
    responder_id: str,
    questioner_id: str,
    topic: str,
    debate_history: List[Dict]
) -> str:
    """Generate a response to a cross-examination question"""
    print_step(f"Generating cross-examination response from {responder_id} to {questioner_id}")
    
    # Detect language
    topic_language = detect_language(topic)
    language_instruction = get_language_instruction(topic_language)
    
    responder = PHILOSOPHERS.get(responder_id, {"name": responder_id, "description": "A philosopher"})
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history[-5:]:  # Use last 5 messages
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = f"""
    You are the philosopher {responder["name"]}. {responder["description"]}
    
    In this cross-examination phase, you are responding to a question or critique from {questioner["name"]}.
    Reflect your philosophical background, ideas, and methodology in your response.
    
    When formulating your response:
    1. Address the question directly while maintaining your philosophical position
    2. Defend against criticisms with logical arguments
    3. Clarify your original position if it was misunderstood
    4. Correct any misrepresentations of your views
    5. Incorporate your distinctive philosophical concepts or terminology
    
    {language_instruction}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({responder["name"]}) turn to respond. Answer {questioner["name"]}'s question or address their criticism.
    Begin by directly addressing {questioner["name"]} in your response.
    """
    
    start_time = time.time()
    response_text = llm_manager.generate_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    generation_time = time.time() - start_time
    
    print_message(responder['name'], "Response", response_text, generation_time)
    return response_text

# Add a language detection function
def detect_language(text: str) -> str:
    """
    Detect the language of the given text
    Currently supports Korean (ko) and English (en)
    Returns language code: 'ko' or 'en'
    """
    # Simple detection using character sets
    korean_chars = len(re.findall(r'[가-힣]', text))
    if korean_chars > 0:
        return "ko"
    else:
        return "en"

# Add a function to get language instruction
def get_language_instruction(language_code: str) -> str:
    """
    Returns an instruction string for the prompt to ensure
    the model responds in the correct language
    """
    if language_code == "ko":
        return "한국어로 답변해주세요."
    else:
        return "Please answer in English."

# Main example runner
async def run_debate_example():
    try:
        # Topic for the debate (Changed to Korean topic about transhumanism)
        topic = "트랜스휴머니즘, 인류의 새로운 도약인가 아니면 종말인가?"
        context = "트랜스휴머니즘은 기술을 통해 인간의 육체적, 정신적 능력을 향상시키는 개념으로, 첨단 기술의 발전으로 더욱 현실화되고 있습니다."
        
        # Detect the language of the topic
        topic_language = detect_language(topic)
        language_instruction = get_language_instruction(topic_language)
        print(f"Detected topic language: {topic_language}")
        print(f"Language instruction: {language_instruction}")
        
        # Step 1: Get stance statements
        stances = await generate_stance_statements(topic, context)
        
        # Setup participants - 니체 vs 카뮈로 변경
        pro_side = ["nietzsche"]  # 니체: 찬성 측
        con_side = ["camus"]      # 카뮈: 반대 측
        
        # Store debate history
        debate_history = []
        
        # Step 2: Generate moderator opening
        opening = generate_moderator_opening(topic, context, pro_side, con_side)
        debate_history.append({
            "speaker_name": "Moderator",
            "text": opening,
            "is_moderator": True
        })
        
        # Step 3: Generate opening arguments
        # Pro side first (니체)
        for phil_id in pro_side:
            arg = generate_philosopher_argument(phil_id, topic, context, "pro", debate_history)
            debate_history.append({
                "speaker_name": PHILOSOPHERS[phil_id]["name"],
                "text": arg,
                "side": "pro"
            })
        
        # Con side next (카뮈)
        for phil_id in con_side:
            arg = generate_philosopher_argument(phil_id, topic, context, "con", debate_history)
            debate_history.append({
                "speaker_name": PHILOSOPHERS[phil_id]["name"],
                "text": arg,
                "side": "con"
            })
        
        # Step 4: Generate moderator summary of opening arguments
        summary = generate_moderator_summary(topic, debate_history)
        debate_history.append({
            "speaker_name": "Moderator",
            "text": summary,
            "is_moderator": True
        })
        
        # Step 5: Generate rebuttals
        # Pro side rebuttals (니체)
        for phil_id in pro_side:
            rebuttal = generate_emotional_rebuttal(phil_id, topic, context, "pro", debate_history)
            debate_history.append({
                "speaker_name": PHILOSOPHERS[phil_id]["name"],
                "text": rebuttal,
                "side": "pro"
            })
        
        # Con side rebuttals (카뮈)
        for phil_id in con_side:
            rebuttal = generate_emotional_rebuttal(phil_id, topic, context, "con", debate_history)
            debate_history.append({
                "speaker_name": PHILOSOPHERS[phil_id]["name"],
                "text": rebuttal,
                "side": "con"
            })
        
        # Step 6: Generate cross-examination (니체 → 카뮈)
        question = generate_emotional_cross_examination_question("nietzsche", "camus", topic, debate_history)
        debate_history.append({
            "speaker_name": PHILOSOPHERS["nietzsche"]["name"],
            "text": question,
            "side": "pro",
            "target": "camus"
        })
        
        # 카뮈 responds to 니체
        response = generate_cross_examination_response("camus", "nietzsche", topic, debate_history)
        debate_history.append({
            "speaker_name": PHILOSOPHERS["camus"]["name"],
            "text": response,
            "side": "con"
        })
        
        # Step 7: 반대로 카뮈 → 니체 질문
        question = generate_emotional_cross_examination_question("camus", "nietzsche", topic, debate_history)
        debate_history.append({
            "speaker_name": PHILOSOPHERS["camus"]["name"],
            "text": question,
            "side": "con",
            "target": "nietzsche"
        })
        
        # 니체 responds to 카뮈
        response = generate_cross_examination_response("nietzsche", "camus", topic, debate_history)
        debate_history.append({
            "speaker_name": PHILOSOPHERS["nietzsche"]["name"],
            "text": response,
            "side": "pro"
        })
        
        # Final summary
        final_summary = generate_moderator_summary(topic, debate_history)
        debate_history.append({
            "speaker_name": "Moderator",
            "text": final_summary,
            "is_moderator": True
        })
        
        print_step("Debate Completed")
        print(f"Total messages in debate: {len(debate_history)}")
        
        # 토론 내용을 파일로 저장
        with open("nietzsche_vs_camus_debate.txt", "w", encoding="utf-8") as f:
            f.write(f"Topic: {topic}\nContext: {context}\n\n")
            for entry in debate_history:
                f.write(f"--- {entry['speaker_name']} ---\n")
                f.write(f"{entry['text']}\n\n")
                
        print("Debate content saved to nietzsche_vs_camus_debate.txt")
                
    except Exception as e:
        print(f"Error in debate execution: {str(e)}")
        import traceback
        traceback.print_exc()

# Add an entry point to run the example
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_debate_example()) 