#!/usr/bin/env python
import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path

# Ensure sapiens_engine is in the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(Path(__file__).parent.parent.parent.absolute())))

# Import necessary modules
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.config_loader import ConfigLoader

# Try to import yaml
try:
    import yaml
except ImportError:
    print("Warning: PyYAML not installed. Using default philosopher data.")
    yaml = None

# Import emotion inference
try:
    from sapiens_engine.dialogue.emotion_inference import infer_emotion_from_context, apply_emotion_to_prompt
except ImportError:
    # Create dummy emotion inference function if the real one is not available
    def infer_emotion_from_context(llm_manager, speaker_id, speaker_name, recent_messages, topic="", speaker_personality=""):
        return {
            "emotion_state": {
                "primary_emotion": "neutral",
                "intensity": "NEUTRAL",
                "intensity_value": 0,
            },
            "prompt_enhancement": ""
        }
    
    def apply_emotion_to_prompt(prompt, emotion_enhancement, emotion_data=None):
        return prompt

# Initialize config and LLM manager
config_loader = ConfigLoader()
llm_manager = LLMManager(config_loader)

# Load philosopher data from config
def load_philosophers() -> Dict[str, Dict[str, Any]]:
    """Load philosopher data from config files"""
    philosophers = {}
    
    # If yaml not installed, use default philosophers
    if yaml is None:
        return get_default_philosophers()
    
    # Try to load from standard locations
    npc_paths = [
        Path('sapiens_engine/config/npcs.yaml'),
        Path('config/npcs.yaml'),
        Path('agoramind/src/config/npcs.yaml'),
    ]
    
    for path in npc_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'npcs' in data:
                        for npc in data['npcs']:
                            npc_id = npc.get('id', '').lower()
                            if npc_id:
                                philosophers[npc_id] = {
                                    'name': npc.get('name', ''),
                                    'description': f"{npc.get('role', '')}. {npc.get('initial_position', '')}",
                                    'voice_style': npc.get('voice_style', ''),
                                    'philosophical_background': npc.get('philosophical_background', []),
                                    'personality_traits': npc.get('personality_traits', {})
                                }
            except Exception as e:
                print(f"Error loading NPC config from {path}: {e}")
    
    # If no philosophers found, use default ones
    if not philosophers:
        philosophers = get_default_philosophers()
    
    return philosophers

def get_default_philosophers() -> Dict[str, Dict[str, Any]]:
    """Get default philosopher data"""
    return {
        "socrates": {"name": "Socrates", "description": "Critical Questioner. Questions established norms and seeks deeper understanding through dialogue.", "voice_style": "Inquisitive, ironic, feigning ignorance to expose contradictions."},
        "plato": {"name": "Plato", "description": "Idealist. Believes in universal Forms and that material reality is a shadow of ideal Forms.", "voice_style": "Uses dialogues and allegories to explain complex philosophical concepts."},
        "aristotle": {"name": "Aristotle", "description": "Empiricist. Emphasizes observation, categorization and finding the golden mean.", "voice_style": "Systematic, logical, observational, focused on categorization and definitions."},
        "kant": {"name": "Kant", "description": "Transcendental Idealist. Believes that human experience is structured by the mind's categories.", "voice_style": "Rigorous, structured, technical, making careful distinctions."},
        "nietzsche": {"name": "Nietzsche", "description": "Value Critic. Questions traditional values and morality as social constructs masking power dynamics.", "voice_style": "Provocative, aphoristic, passionate, questioning assumed moral frameworks."},
        "marx": {"name": "Marx", "description": "Historical Materialist. Analyzes society through economic relations and class struggle.", "voice_style": "Analytical and critical, focusing on material conditions, historical processes, and class relations."},
        "sartre": {"name": "Sartre", "description": "Existentialist. Believes in radical freedom and that existence precedes essence.", "voice_style": "Focuses on concrete human experience, freedom, and responsibility."},
        "camus": {"name": "Camus", "description": "Absurdist. Explores how humans find meaning in an inherently meaningless universe.", "voice_style": "Clear, direct, often using metaphors and emphasizing the human condition."},
        "beauvoir": {"name": "de Beauvoir", "description": "Feminist Existentialist. Examines how gender is socially constructed and limits freedom.", "voice_style": "Analytical, draws on personal experience, challenges gender norms."},
        "hegel": {"name": "Hegel", "description": "Dialectical Synthesizer. History progresses through thesis-antithesis-synthesis, leading to greater consciousness.", "voice_style": "Complex, systematic, historically-minded, focused on contradictions and their resolution."}
    }

# Load philosophers
PHILOSOPHERS = load_philosophers()

# Utility functions for printing
def print_header(text):
    print("\n" + "="*80)
    print(f" {text}")
    print("="*80)

def print_message(text):
    print("\n" + "-"*80)
    print(text)
    print("-"*80)
    print("END OF MESSAGE\n")

# Add a safe API call function to handle errors
def safe_llm_call(system_prompt, user_prompt, max_tokens=2000, default_response="API call failed. Please check your API quota."):
    """Make an LLM API call with error handling"""
    try:
        return llm_manager.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens
        )
    except Exception as e:
        print(f"LLM API call failed: {str(e)}")
        return default_response

# Function to test stance generation
async def test_stance_generation(topic, context=""):
    print_header(f"TESTING STANCE GENERATION FOR: {topic}")
    
    system_prompt = """
    You are a debate preparation assistant. Your task is to analyze the given topic and create clear stance statements for both PRO and CON positions.
    Format your response as JSON with the following structure:
    {
        "pro_statement": "Clear statement supporting the position...",
        "con_statement": "Clear statement opposing the position..."
    }
    Keep each statement concise (1-2 sentences) and strongly articulated.
    """
    
    user_prompt = f"Topic: {topic}\n\nContext: {context}"
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    response = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        default_response='{"pro_statement": "This topic has merit and should be supported.", "con_statement": "This topic has flaws and should be opposed."}'
    )
    
    print_message(response)
    
    try:
        result = json.loads(response)
        pro_statement = result.get("pro_statement", "")
        con_statement = result.get("con_statement", "")
        
        print(f"PRO: {pro_statement}")
        print(f"CON: {con_statement}")
        
        return {
            "pro": pro_statement,
            "con": con_statement
        }
    except json.JSONDecodeError:
        print(f"Failed to parse JSON: {response}")
        return {"pro": "This position is supportable.", "con": "This position is objectionable."}

# Function to test moderator opening
def test_moderator_opening(topic, context="", pro_side=None, con_side=None):
    if pro_side is None:
        pro_side = ["sartre", "nietzsche"]
    if con_side is None:
        con_side = ["kant", "camus"]
    
    print_header(f"TESTING MODERATOR OPENING FOR: {topic}")
    
    # Construct participants names
    pro_names = [PHILOSOPHERS[p]["name"] for p in pro_side if p in PHILOSOPHERS]
    con_names = [PHILOSOPHERS[p]["name"] for p in con_side if p in PHILOSOPHERS]
    
    system_prompt = """
    You are a professional debate moderator. Your task is to create an opening statement for a debate on the given topic.
    
    Write a natural introduction that:
    1. Introduces the topic and its importance
    2. Presents the debaters and their sides (pro/con)
    3. Briefly explains the rules of the debate
    4. Clearly states the pro and con positions
    5. Designates the first speaker (from the pro side)
    
    Use a formal but engaging tone appropriate for an intellectual debate.
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Background Information: {context if context else "No additional background information provided."}
    
    Pro Side Participants: {', '.join(pro_names)}
    Con Side Participants: {', '.join(con_names)}
    
    First Speaker: {pro_names[0] if pro_names else 'Pro side speaker'}
    
    Please write your opening remarks as debate moderator based on this information.
    """
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    opening_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        default_response=f"[As the debate moderator, I welcome you to our discussion on {topic}. Our pro side features {', '.join(pro_names)} and our con side includes {', '.join(con_names)}. Let's begin with {pro_names[0] if pro_names else 'our first speaker'} presenting the pro position.]"
    )
    
    print_message(opening_text)
    return opening_text

# Function to test philosopher argument
def test_philosopher_argument(philosopher_id, topic, context="", side="pro", debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING {side.upper()} ARGUMENT BY {philosopher_id.upper()}")
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher", "voice_style": "Academic"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
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
    
    Voice style: {philosopher.get('voice_style', 'Academic')}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    Background Information: {context if context else "No additional background information provided."}
    
    Your Position: {side} side ({"supporting" if side == "pro" else "opposing"} the proposition)
    
    Previous Debate Content:
    {history_text}
    
    It is now your ({philosopher['name']}) turn to speak. Present a compelling argument from the {"pro" if side == "pro" else "con"} perspective.
    """
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    argument_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    
    print_message(argument_text)
    return argument_text

# Function to test moderator summary
def test_moderator_summary(topic, debate_history=None):
    if debate_history is None:
        debate_history = []
        
    print_header(f"TESTING MODERATOR SUMMARY FOR: {topic}")
    
    # Format debate history
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    system_prompt = """
    You are a professional debate moderator. Your task is to summarize the key points from the debate that has just occurred.
    
    In your summary:
    1. Objectively present the main arguments from both sides
    2. Highlight key points of contention between debaters
    3. Note any areas of consensus
    4. Maintain neutrality without favoring either side
    5. Synthesize the discussion into coherent themes
    
    Use a concise, clear, and balanced approach in your summary.
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Debate Content:
    {history_text}
    
    Please provide a comprehensive summary of the key arguments and points raised by both sides in this debate.
    """
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    summary_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    
    print_message(summary_text)
    return summary_text

# Function to test rebuttal
def test_rebuttal(philosopher_id, topic, context="", side="pro", debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING {side.upper()} REBUTTAL BY {philosopher_id.upper()}")
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher", "voice_style": "Academic"})
    
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
    
    Voice style: {philosopher.get('voice_style', 'Academic')}
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
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    rebuttal_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    
    print_message(rebuttal_text)
    return rebuttal_text

# Function to test cross-examination question
def test_cross_examination_question(questioner_id, target_id, topic, debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING CROSS-EXAMINATION QUESTION FROM {questioner_id.upper()} TO {target_id.upper()}")
    
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher", "voice_style": "Academic"})
    target = PHILOSOPHERS.get(target_id, {"name": target_id, "description": "A philosopher", "voice_style": "Academic"})
    
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
    
    Voice style: {questioner.get("voice_style", "Academic")}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({questioner["name"]}) turn to pose a question. Formulate a critical question or highlight a weakness in {target["name"]}'s arguments.
    Begin by directly addressing {target["name"]} in your question.
    """
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    question_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    
    print_message(question_text)
    return question_text

# Function to test cross-examination response
def test_cross_examination_response(responder_id, questioner_id, topic, debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING CROSS-EXAMINATION RESPONSE FROM {responder_id.upper()} TO {questioner_id.upper()}")
    
    responder = PHILOSOPHERS.get(responder_id, {"name": responder_id, "description": "A philosopher", "voice_style": "Academic"})
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher", "voice_style": "Academic"})
    
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
    
    Voice style: {responder.get("voice_style", "Academic")}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({responder["name"]}) turn to respond. Answer {questioner["name"]}'s question or address their criticism.
    Begin by directly addressing {questioner["name"]} in your response.
    """
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    response_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=2000
    )
    
    print_message(response_text)
    return response_text

# Function to test emotional rebuttal
def test_emotional_rebuttal(philosopher_id, topic, context="", side="pro", debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING EMOTIONAL {side.upper()} REBUTTAL BY {philosopher_id.upper()}")
    
    philosopher = PHILOSOPHERS.get(philosopher_id, {"name": philosopher_id, "description": "A philosopher", "voice_style": "Academic"})
    
    # Convert debate history to text format for display
    history_text = ""
    for entry in debate_history:
        speaker_name = entry.get("speaker_name", "Unknown")
        side_info = entry.get("side", "")
        text = entry.get("text", "")
        history_text += f"{speaker_name} ({side_info}): {text}\n\n"
    
    # Infer emotion from debate history
    try:
        emotion_info = infer_emotion_from_context(
            llm_manager=llm_manager,
            speaker_id=philosopher_id,
            speaker_name=philosopher.get("name", ""),
            recent_messages=debate_history[-5:] if len(debate_history) > 5 else debate_history,
            topic=topic,
            speaker_personality=philosopher.get("description", "")
        )
        
        # Extract emotion information
        emotion_state = emotion_info.get("emotion_state", {})
        primary_emotion = emotion_state.get("primary_emotion", "neutral")
        intensity = emotion_state.get("intensity", "NEUTRAL")
        prompt_enhancement = emotion_info.get("prompt_enhancement", "")
        
        print(f"Inferred emotion: {primary_emotion} ({intensity})")
        print(f"Prompt enhancement: {prompt_enhancement}")
    except Exception as e:
        print(f"Emotion inference failed: {str(e)}")
        primary_emotion = "neutral"
        intensity = "NEUTRAL"
        prompt_enhancement = ""
        emotion_state = {"primary_emotion": primary_emotion, "intensity": intensity}
    
    opposite_side = "con" if side == "pro" else "pro"
    
    system_prompt = f"""
    You are the philosopher {philosopher['name']}. {philosopher['description']}
    
    You hold a {side} position on the given debate topic.
    This is the rebuttal phase where you need to counter the arguments made by the opposite side.
    
    Current emotional state: {primary_emotion.capitalize()} ({intensity})
    {prompt_enhancement}
    
    When making your rebuttal:
    1. Clearly identify the main arguments of the opposing side
    2. Point out logical fallacies or weaknesses in their arguments
    3. Explain why their position is inadequate from your perspective
    4. Provide counter-examples or evidence that challenges their claims
    5. Remain consistent with your philosophical background and approach
    6. Express your points with the emotional tone indicated above
    
    Voice style: {philosopher.get('voice_style', 'Academic')}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    Background Information: {context if context else "No additional background information provided."}
    
    Your Position: {side} side ({"supporting" if side == "pro" else "opposing"} the proposition)
    Position to Rebut: {opposite_side} side ({"supporting" if opposite_side == "pro" else "opposing"} the proposition)
    
    Previous Debate Content:
    {history_text}
    
    It is now your ({philosopher['name']}) turn to speak. Present a focused rebuttal against the {opposite_side} side's arguments, expressing your {primary_emotion} state in your delivery.
    """
    
    # Apply emotion to prompt if the function is available
    try:
        user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement, emotion_state)
    except TypeError:
        # Try with two arguments if the function signature doesn't match
        try:
            user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement)
        except Exception as e:
            print(f"Failed to apply emotion to prompt: {str(e)}")
    except Exception as e:
        print(f"Failed to apply emotion to prompt: {str(e)}")
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    # Use safe API call
    rebuttal_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        default_response=f"[As {philosopher['name']}, I would present a {primary_emotion} rebuttal against the {opposite_side} position, but I'm unable to generate it at this moment due to technical limitations.]"
    )
    
    print_message(rebuttal_text)
    return rebuttal_text

# Function to test emotional cross-examination
def test_emotional_cross_examination(questioner_id, target_id, topic, debate_history=None):
    if debate_history is None:
        debate_history = []
    
    print_header(f"TESTING EMOTIONAL CROSS-EXAMINATION FROM {questioner_id.upper()} TO {target_id.upper()}")
    
    questioner = PHILOSOPHERS.get(questioner_id, {"name": questioner_id, "description": "A philosopher", "voice_style": "Academic"})
    target = PHILOSOPHERS.get(target_id, {"name": target_id, "description": "A philosopher", "voice_style": "Academic"})
    
    # Convert debate history to text
    history_text = ""
    for entry in debate_history[-5:]:  # Use last 5 messages
        speaker_name = entry.get("speaker_name", "Unknown")
        text = entry.get("text", "")
        history_text += f"{speaker_name}: {text}\n\n"
    
    # Infer emotion from debate history
    try:
        emotion_info = infer_emotion_from_context(
            llm_manager=llm_manager,
            speaker_id=questioner_id,
            speaker_name=questioner.get("name", ""),
            recent_messages=debate_history[-5:] if len(debate_history) > 5 else debate_history,
            topic=topic,
            speaker_personality=questioner.get("description", "")
        )
        
        # Extract emotion information
        emotion_state = emotion_info.get("emotion_state", {})
        primary_emotion = emotion_state.get("primary_emotion", "neutral")
        intensity = emotion_state.get("intensity", "NEUTRAL")
        prompt_enhancement = emotion_info.get("prompt_enhancement", "")
        
        print(f"Inferred emotion: {primary_emotion} ({intensity})")
        print(f"Prompt enhancement: {prompt_enhancement}")
    except Exception as e:
        print(f"Emotion inference failed: {str(e)}")
        primary_emotion = "neutral"
        intensity = "NEUTRAL"
        prompt_enhancement = ""
        emotion_state = {"primary_emotion": primary_emotion, "intensity": intensity}
    
    system_prompt = f"""
    You are the philosopher {questioner["name"]}. {questioner["description"]}
    
    Current emotional state: {primary_emotion.capitalize()} ({intensity})
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
    
    Voice style: {questioner.get("voice_style", "Academic")}
    """
    
    user_prompt = f"""
    Debate Topic: {topic}
    
    Recent Debate Content:
    {history_text}
    
    It is now your ({questioner["name"]}) turn to pose a question. Formulate a critical question or highlight a weakness in {target["name"]}'s arguments.
    Begin by directly addressing {target["name"]} in your question, and express your {primary_emotion} state in your delivery.
    """
    
    # Apply emotion to prompt if the function is available
    try:
        user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement, emotion_state)
    except TypeError:
        # Try with two arguments if the function signature doesn't match
        try:
            user_prompt = apply_emotion_to_prompt(user_prompt, prompt_enhancement)
        except Exception as e:
            print(f"Failed to apply emotion to prompt: {str(e)}")
    except Exception as e:
        print(f"Failed to apply emotion to prompt: {str(e)}")
    
    print(f"System prompt:\n{system_prompt}")
    print(f"User prompt:\n{user_prompt}")
    
    # Use safe API call
    question_text = safe_llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        default_response=f"[As {questioner['name']}, I would ask a {primary_emotion} question to {target['name']}, but I'm unable to generate it at this moment due to technical limitations.]"
    )
    
    print_message(question_text)
    return question_text

# Main interactive testing function
async def run_interactive_test():
    print_header("DEBATE DIALOGUE SYSTEM PROMPT TESTING")
    print("Test prompts for each stage of the debate individually.")
    
    # Default values
    topic = "Can artificial intelligence replace human creativity?"
    context = "Recent advances in AI have shown impressive results in creative domains like art, music, and literature."
    
    try:
        while True:
            print("\n" + "-"*40)
            print("Test Menu:")
            print("1. Set Topic")
            print("2. Test Stance Generation")
            print("3. Test Moderator Opening")
            print("4. Test Philosopher Argument")
            print("5. Test Moderator Summary")
            print("6. Test Rebuttal")
            print("7. Test Emotional Rebuttal (with emotion inference)")
            print("8. Test Cross-Examination Question")
            print("9. Test Emotional Cross-Examination (with emotion inference)")
            print("10. Run Sequential Test of All Stages")
            print("0. Exit")
            
            choice = input("\nSelection: ")
            
            if choice == "0":
                break
                
            elif choice == "1":
                topic = input("Debate Topic: ")
                context = input("Background Information (optional): ")
                print(f"Topic set to '{topic}'")
            
            elif choice == "2":
                stances = await test_stance_generation(topic, context)
            
            elif choice == "3":
                opening = test_moderator_opening(topic, context)
            
            elif choice == "4":
                philosophers = list(PHILOSOPHERS.keys())
                print("\nAvailable Philosophers:")
                for i, phil in enumerate(philosophers):
                    print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                
                phil_idx = int(input("\nSelect Philosopher Number: ")) - 1
                if 0 <= phil_idx < len(philosophers):
                    phil_id = philosophers[phil_idx]
                    
                    side = input("Select Position (pro/con): ").lower()
                    if side not in ["pro", "con"]:
                        side = "pro"
                    
                    argument = test_philosopher_argument(phil_id, topic, context, side)
                else:
                    print("Invalid selection.")
                
            elif choice == "5":
                # Create basic debate history for testing
                debate_history = [
                    {"speaker_name": "Moderator", "text": "Welcome to the debate on whether AI can replace human creativity.", "is_moderator": True},
                    {"speaker_name": "Sartre", "text": "Creativity requires authentic human experience and freedom of choice that AI lacks.", "side": "con"},
                    {"speaker_name": "Turing", "text": "AI can learn patterns of human creativity and reproduce them in novel ways.", "side": "pro"}
                ]
                summary = test_moderator_summary(topic, debate_history)
            
            elif choice == "6":
                philosophers = list(PHILOSOPHERS.keys())
                print("\nAvailable Philosophers:")
                for i, phil in enumerate(philosophers):
                    print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                
                phil_idx = int(input("\nSelect Philosopher Number: ")) - 1
                if 0 <= phil_idx < len(philosophers):
                    phil_id = philosophers[phil_idx]
                    
                    side = input("Select Position (pro/con): ").lower()
                    if side not in ["pro", "con"]:
                        side = "pro"
                    
                    # Create basic debate history for testing
                    opposite_side = "pro" if side == "con" else "con"
                    debate_history = [
                        {"speaker_name": "Moderator", "text": "Welcome to the debate on whether AI can replace human creativity.", "is_moderator": True},
                        {"speaker_name": "Sartre", "text": "Creativity requires authentic human experience and freedom of choice that AI lacks.", "side": opposite_side},
                        {"speaker_name": "Turing", "text": "AI can learn patterns of human creativity and reproduce them in novel ways.", "side": side}
                    ]
                    
                    rebuttal = test_rebuttal(phil_id, topic, context, side, debate_history)
                else:
                    print("Invalid selection.")
                
            elif choice == "7":
                philosophers = list(PHILOSOPHERS.keys())
                print("\nAvailable Philosophers:")
                for i, phil in enumerate(philosophers):
                    print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                
                phil_idx = int(input("\nSelect Philosopher Number: ")) - 1
                if 0 <= phil_idx < len(philosophers):
                    phil_id = philosophers[phil_idx]
                    
                    side = input("Select Position (pro/con): ").lower()
                    if side not in ["pro", "con"]:
                        side = "pro"
                    
                    # Create basic debate history for testing
                    opposite_side = "pro" if side == "con" else "con"
                    debate_history = [
                        {"speaker_name": "Moderator", "text": "Welcome to the debate on whether AI can replace human creativity.", "is_moderator": True},
                        {"speaker_name": "Sartre", "text": "Creativity requires authentic human experience and freedom of choice that AI lacks.", "side": opposite_side},
                        {"speaker_name": "Turing", "text": "AI can learn patterns of human creativity and reproduce them in novel ways.", "side": side}
                    ]
                    
                    # Add an emotionally charged message to influence the emotion detection
                    debate_history.append({
                        "speaker_name": PHILOSOPHERS[opposite_side]["name"] if opposite_side in PHILOSOPHERS else "Opponent",
                        "text": "Your argument completely ignores the empirical evidence. It's disappointing to see such logical fallacies from a respected philosopher.",
                        "side": opposite_side
                    })
                    
                    emotional_rebuttal = test_emotional_rebuttal(phil_id, topic, context, side, debate_history)
                else:
                    print("Invalid selection.")
                
            elif choice == "8":
                philosophers = list(PHILOSOPHERS.keys())
                print("\nAvailable Questioners:")
                for i, phil in enumerate(philosophers):
                    print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                
                questioner_idx = int(input("\nSelect Questioner Number: ")) - 1
                if 0 <= questioner_idx < len(philosophers):
                    questioner_id = philosophers[questioner_idx]
                    
                    print("\nAvailable Targets:")
                    for i, phil in enumerate(philosophers):
                        if phil != questioner_id:
                            print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                    
                    target_idx = int(input("\nSelect Target Number: ")) - 1
                    if 0 <= target_idx < len(philosophers):
                        target_id = philosophers[target_idx]
                        
                        # Create basic debate history for testing
                        debate_history = [
                            {"speaker_name": "Moderator", "text": "Welcome to the debate on whether AI can replace human creativity.", "is_moderator": True},
                            {"speaker_name": PHILOSOPHERS[questioner_id]["name"], "text": "Creativity requires authentic human experience and freedom of choice that AI lacks.", "side": "con"},
                            {"speaker_name": PHILOSOPHERS[target_id]["name"], "text": "AI can learn patterns of human creativity and reproduce them in novel ways.", "side": "pro"}
                        ]
                        
                        question = test_cross_examination_question(questioner_id, target_id, topic, debate_history)
                    else:
                        print("Invalid selection.")
                else:
                    print("Invalid selection.")
                
            elif choice == "9":
                philosophers = list(PHILOSOPHERS.keys())
                print("\nAvailable Questioners:")
                for i, phil in enumerate(philosophers):
                    print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                
                questioner_idx = int(input("\nSelect Questioner Number: ")) - 1
                if 0 <= questioner_idx < len(philosophers):
                    questioner_id = philosophers[questioner_idx]
                    
                    print("\nAvailable Targets:")
                    for i, phil in enumerate(philosophers):
                        if phil != questioner_id:
                            print(f"{i+1}. {PHILOSOPHERS[phil]['name']} ({phil})")
                    
                    target_idx = int(input("\nSelect Target Number: ")) - 1
                    if 0 <= target_idx < len(philosophers):
                        target_id = philosophers[target_idx]
                        
                        # Create basic debate history for testing with provocative statements
                        debate_history = [
                            {"speaker_name": "Moderator", "text": "Welcome to the debate on whether AI can replace human creativity.", "is_moderator": True},
                            {"speaker_name": PHILOSOPHERS[questioner_id]["name"], "text": "Creativity requires authentic human experience and freedom of choice that AI lacks.", "side": "con"},
                            {"speaker_name": PHILOSOPHERS[target_id]["name"], "text": "Your argument is fundamentally flawed. AI has already demonstrated creative capabilities that rival human artists.", "side": "pro"}
                        ]
                        
                        # Add provocative statement to trigger emotional reaction
                        debate_history.append({
                            "speaker_name": PHILOSOPHERS[target_id]["name"],
                            "text": "It's naive and outdated to believe that consciousness or subjective experience is required for creativity. This is simply a romantic notion with no empirical support.",
                            "side": "pro"
                        })
                        
                        emotional_question = test_emotional_cross_examination(questioner_id, target_id, topic, debate_history)
                    else:
                        print("Invalid selection.")
                else:
                    print("Invalid selection.")
                
            elif choice == "10":
                # Sequential test of all stages
                print("Starting sequential test of all debate stages...")
                
                # Step 1: Stance generation
                stances = await test_stance_generation(topic, context)
                input("Press Enter to continue...")
                
                # Step 2: Moderator opening
                opening = test_moderator_opening(topic, context)
                debate_history = [{"speaker_name": "Moderator", "text": opening, "is_moderator": True}]
                input("Press Enter to continue...")
                
                # Step 3: Pro argument
                pro_phil = "sartre"
                pro_arg = test_philosopher_argument(pro_phil, topic, context, "pro", debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[pro_phil]["name"], "text": pro_arg, "side": "pro"})
                input("Press Enter to continue...")
                
                # Step 4: Con argument
                con_phil = "kant"
                con_arg = test_philosopher_argument(con_phil, topic, context, "con", debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[con_phil]["name"], "text": con_arg, "side": "con"})
                input("Press Enter to continue...")
                
                # Step 5: Moderator summary
                summary = test_moderator_summary(topic, debate_history)
                debate_history.append({"speaker_name": "Moderator", "text": summary, "is_moderator": True})
                input("Press Enter to continue...")
                
                # Step 6: Pro rebuttal
                pro_rebuttal = test_rebuttal(pro_phil, topic, context, "pro", debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[pro_phil]["name"], "text": pro_rebuttal, "side": "pro"})
                input("Press Enter to continue...")
                
                # Step 7: Con rebuttal with emotion
                con_emotional_rebuttal = test_emotional_rebuttal(con_phil, topic, context, "con", debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[con_phil]["name"], "text": con_emotional_rebuttal, "side": "con"})
                input("Press Enter to continue...")
                
                # Step 8: Cross-examination question with emotion
                emotional_question = test_emotional_cross_examination(pro_phil, con_phil, topic, debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[pro_phil]["name"], "text": emotional_question, "side": "pro", "target": con_phil})
                input("Press Enter to continue...")
                
                # Step 9: Cross-examination response
                response = test_cross_examination_response(con_phil, pro_phil, topic, debate_history)
                debate_history.append({"speaker_name": PHILOSOPHERS[con_phil]["name"], "text": response, "side": "con"})
                
                print("Sequential test completed!")
            
            else:
                print("Invalid selection.")
    except Exception as e:
        print(f"Error in test execution: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_interactive_test()) 