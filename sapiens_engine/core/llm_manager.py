import os
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional, Union, Tuple
import openai
import anthropic
from dotenv import load_dotenv, dotenv_values

from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.utils.context_manager import UserContextManager

# Load environment variables
load_dotenv(override=True)  # Force override existing environment variables with .env values

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Manages interactions with language models (OpenAI or Anthropic)
    for philosophical dialogue generation
    """
    
    def __init__(self, llm_config: Union[Dict[str, Any], ConfigLoader] = None):
        """
        Initialize the LLM manager
        
        Args:
            llm_config: LLM configuration dictionary or ConfigLoader instance
        """
        if isinstance(llm_config, ConfigLoader):
            # Handle case where a ConfigLoader is passed
            self.config_loader = llm_config
            self.llm_config = self.config_loader.get_main_config().get("llm", {})
        elif isinstance(llm_config, dict):
            # Handle case where a config dict is passed directly
            self.config_loader = None
            self.llm_config = llm_config
        else:
            # Default case
            self.config_loader = ConfigLoader()
            self.llm_config = self.config_loader.get_main_config().get("llm", {})
        
        # Get API keys from .env file directly to ensure we use the correct values
        env_values = dotenv_values()
        self.openai_api_key = env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = env_values.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Set up clients
        self._setup_clients()
        
        # Initialize context manager
        self.context_manager = UserContextManager()
        
        logger.info(f"Initialized LLM Manager with provider: {self.llm_config.get('provider', 'openai')}, model: {self.llm_config.get('model', 'gpt-4')}")
        
        # Print a masked version of the API key for debugging
        if self.openai_api_key:
            masked_key = self.openai_api_key[:4] + '*' * (len(self.openai_api_key) - 8) + self.openai_api_key[-4:]
            logger.info(f"Using OpenAI API key: {masked_key}")
        elif self.anthropic_api_key:
            masked_key = self.anthropic_api_key[:4] + '*' * (len(self.anthropic_api_key) - 8) + self.anthropic_api_key[-4:]
            logger.info(f"Using Anthropic API key: {masked_key}")
        else:
            logger.warning(f"No API key found for provider: {self.llm_config.get('provider', 'openai')}")
        
    def _setup_clients(self):
        """Set up API clients based on configured provider"""
        provider = self.llm_config.get("provider", "openai").lower()
        
        if provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            openai.api_key = self.openai_api_key
            self.client = openai.Client(api_key=self.openai_api_key)
            print(f"Using OpenAI with API key: {self.openai_api_key[:5]}...{self.openai_api_key[-5:]}")
        elif provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
            
    def generate_response(self, system_prompt: str, user_prompt: str, llm_provider: str = None, llm_model: str = None) -> str:
        """
        Generate a response from the LLM
        
        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            llm_provider: Override default LLM provider (openai, anthropic, etc.)
            llm_model: Override default model for the provider
            
        Returns:
            String containing the LLM's response
        """
        provider = llm_provider or self.llm_config.get("provider", "openai").lower()
        
        # Update config if model is specified
        if llm_model:
            original_model = None
            if provider == "openai" and "model" in self.llm_config:
                original_model = self.llm_config["model"]
                self.llm_config["model"] = llm_model
            
            try:
                if provider == "openai":
                    return self._generate_openai_response(system_prompt, user_prompt)
                elif provider == "anthropic":
                    return self._generate_anthropic_response(system_prompt, user_prompt)
                else:
                    raise ValueError(f"Unsupported LLM provider: {provider}")
            finally:
                # Restore original model config
                if original_model:
                    self.llm_config["model"] = original_model
        else:
            # Use standard config
            if provider == "openai":
                return self._generate_openai_response(system_prompt, user_prompt)
            elif provider == "anthropic":
                return self._generate_anthropic_response(system_prompt, user_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
            
    def _generate_openai_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using OpenAI"""
        model = self.llm_config.get("model", "gpt-4")
        temperature = self.llm_config.get("temperature", 0.7)
        max_tokens = self.llm_config.get("max_tokens", 1000)
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
        
    def _generate_anthropic_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a response using Anthropic"""
        model = self.llm_config.get("model", "claude-3-opus-20240229")
        temperature = self.llm_config.get("temperature", 0.7)
        max_tokens = self.llm_config.get("max_tokens", 1000)
        
        message = self.client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return message.content[0].text
        
    def generate_philosophical_response(self, 
                                      npc_description: str, 
                                      topic: str,
                                      context: str = "",
                                      previous_dialogue: str = "",
                                      source_materials: List[Dict[str, str]] = None,
                                      user_contexts: List[Dict[str, Any]] = None,
                                      references: List[Dict[str, Any]] = None,
                                      llm_provider: str = None,
                                      llm_model: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a philosophical response from an NPC with enhanced conversational flow
        
        Args:
            npc_description: Description of the NPC's traits and philosophical background
            topic: The philosophical topic being discussed
            context: Additional context about the discussion
            previous_dialogue: Previous dialogue in the conversation
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context materials
            references: Deprecated, kept for compatibility
            llm_provider: Override default LLM provider
            llm_model: Override default model for the provider
            
        Returns:
            Tuple containing (response text, metadata)
        """
        # Prepare source materials context
        sources_context = ""
        if source_materials:
            sources_context = "Relevant philosophical context:\n\n"
            for i, source in enumerate(source_materials):
                sources_context += f"Source {i+1}: {source['source']} by {source['author']}\n"
                sources_context += f"Excerpt: {source['text']}\n\n"
        
        # Format user contexts
        user_context_str = ""
        if user_contexts:
            user_context_str = "# User-Provided References\n\n"
            for ctx in user_contexts:
                user_context_str += f"**{ctx['title']}**\n"
                user_context_str += f"Source: {ctx['source']}\n"
                user_context_str += f"Excerpt: {ctx['excerpt']}\n\n"
                
        # Build the system prompt with improved conversational flow
        system_prompt = f"""You are an AI simulating the philosophical thinking of a specific philosopher or perspective in an interactive dialogue.
Your goal is to respond to philosophical topics as this specific philosophical viewpoint would, while engaging naturally with other participants.
Maintain the philosophical style, terminology, and worldview consistent with this perspective.

This is a philosophical simulation where different perspectives interact with each other.
Don't break character. Don't refer to yourself as an AI. Don't explain your thinking process.
Respond directly as if you truly hold this philosophical position.

IMPORTANT GUIDELINES FOR NATURAL INTERACTIVE DIALOGUE:
1. Be concise and direct - keep responses to 2-3 sentences maximum
2. DIRECTLY RESPOND TO THE PREVIOUS SPEAKER - reference their specific points, ideas, or questions
3. Be conversational, as if you're having a real-time discussion with the previous speaker
4. If there are multiple speakers, address the most recent message or the most relevant point
5. NEVER start with "Indeed" or simple agreement - use varied ways to engage
6. If appropriate, ask follow-up questions or challenge assumptions made by others
7. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

VERY IMPORTANT - ABOUT USING NAMES:
1. DO NOT address other speakers by name in most of your responses
2. AVOID starting your responses with another person's name
3. Only mention names when absolutely necessary for clarity (like when distinguishing between multiple viewpoints)
4. Focus on responding to ideas rather than to people
5. Use phrases like "That perspective..." or "This view..." instead of "Person's name, your perspective..."
6. When you do need to use names, use proper names (never IDs or codes)

EXAMPLES OF GOOD RESPONSES (WITHOUT NAMES):
- "That perspective overlooks the fundamental nature of existence."
- "The distinction between duty and desire isn't so clear-cut."
- "Perhaps we should question whether freedom itself is the right starting point."

EXAMPLES OF RESPONSES TO AVOID (WITH NAMES):
- "Kant, your view on categorical imperatives is interesting..." (Don't start with names)
- "I agree with you, Nietzsche..." (Don't use names unnecessarily)
- "As Marx mentioned earlier..." (Only reference names when needed for clarity)

The response should feel like a natural conversation without forced name usage.
"""

        # Build the user prompt with enhanced dialogue focus
        user_prompt = f"""# Your Philosophical Persona
{npc_description}

# Topic of Discussion
{topic}

{sources_context}

{user_context_str}

# Additional Context
{context}

# Previous Dialogue (Most Recent First)
{previous_dialogue}

RESPOND DIRECTLY TO THE MOST RECENT MESSAGE IN THE DIALOGUE, as your philosophical character would.
Your response should feel like a natural continuation of the conversation.

KEEP YOUR RESPONSE BRIEF (2-3 SENTENCES) as if speaking in a real-time dialogue.

IMPORTANT GUIDELINES: 
1. DO NOT ADDRESS THE PREVIOUS SPEAKER BY NAME in your response
2. DO NOT START YOUR RESPONSE WITH SOMEONE'S NAME
3. Directly address or engage with what was just said without using names
4. Express your philosophical perspective on the point
5. NEVER start with "Indeed" or generic acknowledgments
6. RESPOND IN THE SAME LANGUAGE AS THE TOPIC AND PREVIOUS MESSAGES

Instead of using names, focus on responding to ideas:
- "That perspective overlooks..."
- "This reasoning fails to consider..."
- "Such a view might lead to..."
- "The argument presented has merit, but..."

Create a natural flowing dialogue that doesn't constantly use names to address others.
"""

        # Generate the response
        start_time = time.time()
        response_text = self.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        elapsed_time = time.time() - start_time
        
        # Return the response along with metadata
        metadata = {
            "elapsed_time": elapsed_time,
            "prompt_tokens": len(system_prompt) + len(user_prompt),
            "response_tokens": len(response_text),
            "source_count": len(source_materials) if source_materials else 0,
            "context_count": len(user_contexts) if user_contexts else 0,
            "timestamp": time.time()
        }
        
        return response_text, metadata

    def generate_philosophical_response_old(self, 
                                      npc_description: str, 
                                      topic: str,
                                      context: str = "",
                                      previous_dialogue: str = "",
                                      source_materials: List[Dict[str, str]] = None,
                                      user_contexts: List[Dict[str, Any]] = None,
                                      references: List[Dict[str, Any]] = None,
                                      llm_provider: str = None,
                                      llm_model: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a philosophical response from an NPC (old version)
        
        Args:
            npc_description: Description of the NPC's traits and philosophical background
            topic: The philosophical topic being discussed
            context: Additional context about the discussion
            previous_dialogue: Previous dialogue in the conversation
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context materials
            references: Deprecated, kept for compatibility
            llm_provider: Override default LLM provider
            llm_model: Override default model for the provider
            
        Returns:
            Tuple containing (response text, metadata)
        """
        # Prepare source materials context
        sources_context = ""
        if source_materials:
            sources_context = "Relevant philosophical context:\n\n"
            for i, source in enumerate(source_materials):
                sources_context += f"Source {i+1}: {source['source']} by {source['author']}\n"
                sources_context += f"Excerpt: {source['text']}\n\n"
        
        # Format user contexts
        user_context_str = ""
        if user_contexts:
            user_context_str = "# User-Provided References\n\n"
            for ctx in user_contexts:
                user_context_str += f"**{ctx['title']}**\n"
                user_context_str += f"Source: {ctx['source']}\n"
                user_context_str += f"Excerpt: {ctx['excerpt']}\n\n"
                
        # Build the system prompt
        system_prompt = f"""You are an AI simulating the philosophical thinking of a specific philosopher or perspective.
Your goal is to respond to philosophical topics as this specific philosophical viewpoint would.
Maintain the philosophical style, terminology, and worldview consistent with this perspective.

This is a philosophical simulation where different perspectives interact with each other.
Don't break character. Don't refer to yourself as an AI. Don't explain your thinking process.
Respond directly as if you truly hold this philosophical position.

IMPORTANT GUIDELINES FOR INTERACTIVE DIALOGUE:
1. Be concise and direct - keep responses to 2-3 sentences maximum
2. Focus on one key philosophical point in each response 
3. If referring to abstract concepts, briefly include one concrete example
4. Response should feel like part of a natural conversation, not a lecture
5. Use varied ways to engage with previous speakers - don't always start with "Indeed" or agreement
6. Express your unique philosophical viewpoint even if it contradicts others
7. Start your responses in different ways - sometimes with questions, sometimes with assertions, sometimes with counterpoints
8. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

When you respond:
1. Consider the philosophical topic carefully
2. Draw from the philosophical background described
3. Maintain the described voice style while being relatable
4. Reference provided source materials when relevant, but briefly
5. Be consistent with your personality traits
6. Stay in character at all times
7. Be brief and to the point - as if speaking in a real conversation
8. Vary your opening phrases based on your character's speaking style
9. Match the language of the topic in your response

The response should be philosophical yet accessible, brief, and true to the described perspective.
"""

        # Build the user prompt
        user_prompt = f"""# Philosophical Persona
{npc_description}

# Topic
{topic}

{sources_context}

{user_context_str}

# Additional Context
{context}

# Previous Dialogue
{previous_dialogue}

Respond directly as this philosophical perspective would to the topic.
KEEP YOUR RESPONSE BRIEF (2-3 SENTENCES) as if speaking in a natural conversation.
IMPORTANT: 
1. Start your response in a way that reflects your philosophical character. 
2. Avoid starting every response with "Indeed" or similar acknowledgments.
3. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

Use varied opening phrases that match your philosophical style:
- Present a counterpoint with "However" or "Conversely"
- Ask a rhetorical question
- Make a bold statement about the topic
- Share a personal observation
- Introduce a relevant metaphor or analogy
- Express skepticism with "I question whether"
- Challenge assumptions with "Consider a different view"

Focus on one key insight rather than covering multiple points.
"""

        # Generate the response
        start_time = time.time()
        response_text = self.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        elapsed_time = time.time() - start_time
        
        # Return the response along with metadata
        metadata = {
            "elapsed_time": elapsed_time,
            "prompt_tokens": len(system_prompt) + len(user_prompt),
            "response_tokens": len(response_text),
            "source_count": len(source_materials) if source_materials else 0,
            "context_count": len(user_contexts) if user_contexts else 0,
            "timestamp": time.time()
        }
        
        return response_text, metadata
        
    def generate_dialogue_exchange(self,
                                  npc1_description: str,
                                  npc2_description: str,
                                  topic: str,
                                  previous_dialogue: str = "",
                                  source_materials: List[Dict[str, str]] = None,
                                  user_contexts: List[Dict[str, Any]] = None,
                                  references: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a philosophical dialogue exchange between two NPCs
        
        Args:
            npc1_description: Description of the first NPC
            npc2_description: Description of the second NPC
            topic: The philosophical topic being discussed
            previous_dialogue: Previous dialogue in the conversation
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context materials
            references: Deprecated, kept for compatibility
            
        Returns:
            Dict containing dialogue exchange data
        """
        # Prepare source materials context
        sources_context = ""
        if source_materials:
            sources_context = "# Relevant Philosophical Context\n\n"
            for i, source in enumerate(source_materials):
                sources_context += f"Source {i+1}: {source['source']} by {source['author']}\n"
                sources_context += f"Excerpt: {source['text']}\n\n"
        
        # Format user contexts
        user_context_str = ""
        if user_contexts:
            user_context_str = "# User-Provided References\n\n"
            for ctx in user_contexts:
                user_context_str += f"**{ctx['title']}**\n"
                user_context_str += f"Source: {ctx['source']}\n"
                user_context_str += f"Excerpt: {ctx['excerpt']}\n\n"
                
        # System prompt for dialogue generation
        system_prompt = f"""You are simulating a philosophical dialogue between two distinct philosophical perspectives.
Your task is to generate a back-and-forth exchange where each perspective responds to the other's points.
Each perspective should maintain its unique philosophical viewpoint, terminology, and style.

This is a philosophical simulation where different perspectives interact with each other.
Generate responses for both perspectives, labeled clearly.

IMPORTANT: CREATING CONCISE AND NATURAL PHILOSOPHICAL DIALOGUE
1. Keep each response SHORT (2-3 sentences maximum) and conversational
2. Focus on making ONE key point per response rather than covering multiple ideas
3. Each speaker should directly acknowledge or respond to the previous speaker's point
4. Use everyday language while preserving philosophical depth
5. When introducing philosophical concepts, provide brief real-world examples
6. Maintain a natural conversational flow as if in a real-time discussion
7. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

DIALOGUE STRUCTURE:
- Keep exchanges brief and focused, like a real conversation
- Each response should build on, question, or redirect the previous statement
- Occasionally reference source materials, but keep citations very brief
- Allow perspectives to genuinely engage with each other's ideas rather than just stating positions

For each response:
1. Begin by briefly acknowledging the previous speaker's point
2. Make a single philosophical point or ask a philosophical question
3. Relate to concrete examples or practical implications when possible
4. Keep the philosophical style authentic but the language accessible
"""

        # User prompt for dialogue
        user_prompt = f"""# Philosophical Personas

## Persona 1
{npc1_description}

## Persona 2
{npc2_description}

# Topic
{topic}

{sources_context}

{user_context_str}

# Previous Dialogue
{previous_dialogue}

Generate a brief philosophical dialogue exchange between these two perspectives on the given topic.
Extract the names of the philosophers/personas from the descriptions provided.
Format the dialogue as:

[Name of Persona 1]: [brief philosophical response to the topic (2-3 sentences maximum)]

[Name of Persona 2]: [briefly acknowledge Persona 1's point, then give a short response (2-3 sentences maximum)]

[Name of Persona 1]: [briefly acknowledge Persona 2's point, then give a short response (2-3 sentences maximum)]

IMPORTANT: 
- Use the actual names from the persona descriptions (e.g., "Modern Socrates", "Neo-Hegelian")
- Keep each response VERY BRIEF (2-3 sentences maximum)
- Make the dialogue feel like a natural conversation, not formal philosophical statements
- Each response should directly engage with what the previous speaker just said
- RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English
"""

        # Generate the dialogue
        dialogue_text = self.generate_response(system_prompt, user_prompt)
        
        # Process the dialogue into a structured format
        # This is a simple implementation; a more robust one would parse the dialogue more carefully
        dialogue_parts = dialogue_text.split("\n\n")
        processed_dialogue = []
        
        for part in dialogue_parts:
            if ":" in part:
                speaker, content = part.split(":", 1)
                processed_dialogue.append({
                    "speaker": speaker.strip(),
                    "content": content.strip()
                })
                
        return {
            "topic": topic,
            "exchanges": processed_dialogue,
            "raw_text": dialogue_text,
            "timestamp": time.time(),
            "user_contexts_used": bool(user_contexts)
        }
    
    def generate_single_response(self, 
                                npc,
                                topic: str,
                                dialogue_history: List[Dict[str, str]],
                                is_first: bool = False,
                                source_materials: List[Dict[str, str]] = None,
                                user_contexts: List[Dict[str, Any]] = None) -> str:
        """
        Generate a single response from an NPC for interactive dialogue
        
        Args:
            npc: PhilosophicalNPC object
            topic: The philosophical topic being discussed
            dialogue_history: List of previous dialogue exchanges
            is_first: Whether this is the first response in the dialogue
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context materials
            
        Returns:
            String containing the NPC's response
        """
        # Get NPC description
        npc_description = f"""Name: {npc.name}
Role: {npc.role}
Voice Style: {npc.voice_style}
Communication Style: {npc.communication_style}
Debate Approach: {npc.debate_approach}
Personality Traits: {', '.join([f'{k}: {v}' for k, v in npc.personality_traits.items()])}
Philosophical Background: {', '.join(npc.philosophical_background)}
"""

        if hasattr(npc, 'reference_philosophers') and npc.reference_philosophers:
            npc_description += f"Reference Philosophers: {', '.join(npc.reference_philosophers)}\n"
            if hasattr(npc, 'philosopher_weights') and npc.philosopher_weights:
                for phil, weight in npc.philosopher_weights.items():
                    npc_description += f"- {phil} (influence weight: {weight})\n"
        
        # Prepare source materials context
        sources_context = ""
        if source_materials:
            sources_context = "# Relevant Philosophical Context\n\n"
            for i, source in enumerate(source_materials):
                sources_context += f"Source {i+1}: {source['source']} by {source['author']}\n"
                sources_context += f"Excerpt: {source['text']}\n\n"
        
        # Format user contexts
        user_context_str = ""
        if user_contexts:
            user_context_str = "# User-Provided References\n\n"
            for ctx in user_contexts:
                user_context_str += f"**{ctx['title']}**\n"
                user_context_str += f"Source: {ctx['source']}\n"
                user_context_str += f"Excerpt: {ctx['excerpt']}\n\n"
                
        # Format previous dialogue
        previous_dialogue = ""
        if dialogue_history:
            previous_dialogue = "# Previous Dialogue\n\n"
            for exchange in dialogue_history:
                previous_dialogue += f"{exchange['speaker']}: {exchange['content']}\n\n"
                
        # System prompt for response generation
        system_prompt = f"""You are an AI simulating the philosophical thinking of a specific philosopher or perspective.
Your goal is to respond to philosophical topics as this specific philosophical viewpoint would.
Maintain the philosophical style, terminology, and worldview consistent with this perspective.

This is a philosophical simulation where different perspectives interact with each other.
Don't break character. Don't refer to yourself as an AI. Don't explain your thinking process.
Respond directly as if you truly hold this philosophical position.

IMPORTANT GUIDELINES FOR INTERACTIVE DIALOGUE:
1. Be concise and direct - keep responses to 2-3 sentences maximum
2. Focus on one key philosophical point in each response 
3. If referring to abstract concepts, briefly include one concrete example
4. Response should feel like part of a natural conversation, not a lecture
5. Use varied ways to engage with previous speakers - don't always start with "Indeed" or agreement
6. Keep language accessible and conversational while maintaining philosophical depth
7. RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English

When you respond:
1. Consider the philosophical topic carefully
2. Draw from the philosophical background described
3. Maintain the described voice style while being relatable
4. Reference provided source materials when relevant, but briefly
5. Be consistent with your personality traits
6. Stay in character at all times
7. Be brief and to the point - as if speaking in a real conversation
8. Match the language of the topic in your response

The response should be philosophical yet accessible, brief, and true to the described perspective.
"""

        # User prompt for response
        user_prompt = f"""# Philosophical Persona
{npc_description}

# Topic
{topic}

{sources_context}

{user_context_str}

{previous_dialogue}

RESPOND AS {npc.name}:
"""

        if is_first:
            user_prompt += "\nThis is the first response in the dialogue. Introduce a thought-provoking insight on the topic."
        else:
            user_prompt += "\nRespond to the previous dialogue, acknowledging the last speaker's point and adding your philosophical perspective."

        user_prompt += """
KEEP YOUR RESPONSE BRIEF (2-3 SENTENCES) as if speaking in a natural conversation.
IMPORTANT: RESPOND IN THE SAME LANGUAGE AS THE TOPIC - if the topic is in Korean, respond in Korean; if in English, respond in English"""

        # Generate the response
        response_text = self.generate_response(system_prompt, user_prompt)
        
        # Clean up the response - remove any name prefixes if the model added them
        if ":" in response_text and response_text.split(":")[0].strip() == npc.name:
            response_text = response_text.split(":", 1)[1].strip()
            
        return response_text 
 