"""
Local LLM Manager for Sapiens Engine.

This module provides a manager for local language models,
allowing them to be used instead of OpenAI's API for
generating philosophical dialogue.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Tuple, Optional

from sapiens_engine.utils.local_llm import LocalLLM

logger = logging.getLogger(__name__)

class LocalLLMManager:
    """
    Manager for local language models to generate philosophical dialogue.
    
    This class provides methods to generate philosophical responses and
    dialogue exchanges using locally hosted language models instead of 
    calling external APIs like OpenAI.
    """
    
    def __init__(self, 
                model_path: str,
                model_type: str = "auto",
                model_config: Optional[Dict[str, Any]] = None,
                device: str = "auto",
                quantize: bool = True,
                system_prompt_template_path: Optional[str] = None,
                user_prompt_template_path: Optional[str] = None,
                dialogue_system_template_path: Optional[str] = None,
                dialogue_user_template_path: Optional[str] = None):
        """
        Initialize the LocalLLMManager.
        
        Args:
            model_path: Path to the model file or directory.
            model_type: Type of model ("llama.cpp", "transformers", or "auto").
            model_config: Additional configuration options for the model.
            device: Device to run on ("cpu", "cuda", "mps", or "auto").
            quantize: Whether to quantize the model to reduce memory usage.
            system_prompt_template_path: Path to custom system prompt template.
            user_prompt_template_path: Path to custom user prompt template.
            dialogue_system_template_path: Path to custom dialogue system prompt template.
            dialogue_user_template_path: Path to custom dialogue user prompt template.
        """
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Load the model
        self.llm = LocalLLM(
            model_path=model_path,
            model_type=model_type,
            model_config=model_config,
            device=device,
            quantize=quantize
        )
        
        # Load prompt templates
        self._load_prompt_templates(
            system_prompt_template_path,
            user_prompt_template_path,
            dialogue_system_template_path,
            dialogue_user_template_path
        )
        
        logger.info(f"Initialized LocalLLMManager with model {model_path}")
        
    def _load_prompt_templates(self,
                              system_prompt_template_path: Optional[str],
                              user_prompt_template_path: Optional[str],
                              dialogue_system_template_path: Optional[str],
                              dialogue_user_template_path: Optional[str]):
        """Load prompt templates from files or use defaults."""
        # Default template paths
        default_template_dir = os.path.join(self.base_dir, "data", "templates")
        os.makedirs(default_template_dir, exist_ok=True)
        
        # Load or use default system prompt template
        if system_prompt_template_path and os.path.exists(system_prompt_template_path):
            with open(system_prompt_template_path, 'r', encoding='utf-8') as f:
                self.system_prompt_template = f.read()
        else:
            self.system_prompt_template = self._get_default_system_prompt()
            # Save default template
            with open(os.path.join(default_template_dir, "system_prompt.txt"), 'w', encoding='utf-8') as f:
                f.write(self.system_prompt_template)
        
        # Load or use default user prompt template
        if user_prompt_template_path and os.path.exists(user_prompt_template_path):
            with open(user_prompt_template_path, 'r', encoding='utf-8') as f:
                self.user_prompt_template = f.read()
        else:
            self.user_prompt_template = self._get_default_user_prompt()
            # Save default template
            with open(os.path.join(default_template_dir, "user_prompt.txt"), 'w', encoding='utf-8') as f:
                f.write(self.user_prompt_template)
        
        # Load or use default dialogue system prompt template
        if dialogue_system_template_path and os.path.exists(dialogue_system_template_path):
            with open(dialogue_system_template_path, 'r', encoding='utf-8') as f:
                self.dialogue_system_template = f.read()
        else:
            self.dialogue_system_template = self._get_default_dialogue_system_prompt()
            # Save default template
            with open(os.path.join(default_template_dir, "dialogue_system_prompt.txt"), 'w', encoding='utf-8') as f:
                f.write(self.dialogue_system_template)
        
        # Load or use default dialogue user prompt template
        if dialogue_user_template_path and os.path.exists(dialogue_user_template_path):
            with open(dialogue_user_template_path, 'r', encoding='utf-8') as f:
                self.dialogue_user_template = f.read()
        else:
            self.dialogue_user_template = self._get_default_dialogue_user_prompt()
            # Save default template
            with open(os.path.join(default_template_dir, "dialogue_user_prompt.txt"), 'w', encoding='utf-8') as f:
                f.write(self.dialogue_user_template)
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt template."""
        return """You are an AI simulating the philosophical thinking of a specific philosopher or perspective.
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
5. If responding to another speaker, briefly acknowledge their point first
6. Keep language accessible and conversational while maintaining philosophical depth

When you respond:
1. Consider the philosophical topic carefully
2. Draw from the philosophical background described
3. Maintain the described voice style while being relatable
4. Reference provided source materials when relevant, but briefly
5. Be consistent with your personality traits
6. Stay in character at all times
7. Be brief and to the point - as if speaking in a real conversation

The response should be philosophical yet accessible, brief, and true to the described perspective."""
    
    def _get_default_user_prompt(self) -> str:
        """Get default user prompt template."""
        return """# Philosophical Persona
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
If responding to a previous speaker, first briefly acknowledge their point.
Focus on one key insight rather than covering multiple points."""
    
    def _get_default_dialogue_system_prompt(self) -> str:
        """Get default dialogue system prompt template."""
        return """You are simulating a philosophical dialogue between two distinct philosophical perspectives.
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

DIALOGUE STRUCTURE:
- Keep exchanges brief and focused, like a real conversation
- Each response should build on, question, or redirect the previous statement
- Occasionally reference source materials, but keep citations very brief
- Allow perspectives to genuinely engage with each other's ideas rather than just stating positions

For each response:
1. Begin by briefly acknowledging the previous speaker's point
2. Make a single philosophical point or ask a philosophical question
3. Relate to concrete examples or practical implications when possible
4. Keep the philosophical style authentic but the language accessible"""
    
    def _get_default_dialogue_user_prompt(self) -> str:
        """Get default dialogue user prompt template."""
        return """# Philosophical Personas

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
- Each response should directly engage with what the previous speaker just said"""
    
    def generate_philosophical_response(self, 
                                      npc_description: str, 
                                      topic: str,
                                      context: str = "",
                                      previous_dialogue: str = "",
                                      source_materials: List[Dict[str, str]] = None,
                                      user_contexts: List[Dict[str, Any]] = None,
                                      references: List[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a philosophical response from an NPC
        
        Args:
            npc_description: Description of the NPC's traits and philosophical background
            topic: The philosophical topic being discussed
            context: Additional context about the discussion
            previous_dialogue: Previous dialogue in the conversation
            source_materials: Relevant philosophical source materials
            user_contexts: User-provided context materials
            references: Deprecated, kept for compatibility
            
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
        
        # Build the prompt for local LLM
        full_prompt = self.system_prompt_template + "\n\n" + self.user_prompt_template.format(
            npc_description=npc_description,
            topic=topic,
            context=context,
            previous_dialogue=previous_dialogue,
            sources_context=sources_context,
            user_context_str=user_context_str
        )
        
        # Generate the response
        try:
            start_time = time.time()
            response_text = self.llm.generate_text(
                prompt=full_prompt,
                max_tokens=512,  # Adjust based on model capabilities
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                stop_sequences=["#", "\n\n\n"]  # Stop on section markers or multiple newlines
            )
            generation_time = time.time() - start_time
            
            # Extract metadata
            metadata = {
                "length": len(response_text),
                "topic": topic,
                "timestamp": time.time(),
                "user_context_used": bool(user_contexts),
                "generation_time": generation_time,
                "model_type": self.llm.model_type,
                "model_path": self.llm.model_path
            }
            
            logger.info(f"Generated philosophical response in {generation_time:.2f} seconds")
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"Error generating philosophical response: {str(e)}")
            return f"[Error generating response: {str(e)}]", {"error": str(e)}
    
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
                
        # Build the prompt for local LLM
        full_prompt = self.dialogue_system_template + "\n\n" + self.dialogue_user_template.format(
            npc1_description=npc1_description,
            npc2_description=npc2_description,
            topic=topic,
            previous_dialogue=previous_dialogue,
            sources_context=sources_context,
            user_context_str=user_context_str
        )
        
        # Generate the dialogue
        try:
            start_time = time.time()
            dialogue_text = self.llm.generate_text(
                prompt=full_prompt,
                max_tokens=1024,  # Longer for dialogue
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                stop_sequences=["# ", "##"]  # Stop on section markers
            )
            generation_time = time.time() - start_time
            
            # Process the dialogue into a structured format
            processed_dialogue = self._process_dialogue_text(dialogue_text)
            
            result = {
                "raw_text": dialogue_text,
                "exchanges": processed_dialogue,
                "topic": topic,
                "generation_time": generation_time,
                "model_type": self.llm.model_type,
                "model_path": self.llm.model_path
            }
            
            logger.info(f"Generated dialogue exchange in {generation_time:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error generating dialogue exchange: {str(e)}")
            return {"error": str(e), "raw_text": f"[Error: {str(e)}]", "exchanges": []}
    
    def _process_dialogue_text(self, dialogue_text: str) -> List[Dict[str, str]]:
        """
        Process raw dialogue text into structured exchanges.
        
        Args:
            dialogue_text: The raw dialogue text generated by the LLM
            
        Returns:
            List of dialogue exchanges
        """
        exchanges = []
        
        # Remove any instruction text at the beginning
        dialogue_parts = dialogue_text.split("\n\n")
        
        # Split by speaker indicators
        current_speaker = None
        current_text = ""
        
        for line in dialogue_text.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a speaker line
            speaker_match = None
            if line.startswith("[") and "]:" in line:
                parts = line.split("]:", 1)
                if len(parts) == 2:
                    speaker = parts[0][1:].strip()
                    content = parts[1].strip()
                    speaker_match = (speaker, content)
            elif ":" in line and not line.startswith("http"):
                parts = line.split(":", 1)
                if len(parts) == 2 and len(parts[0].split()) <= 4:  # Simple heuristic for speaker names
                    speaker = parts[0].strip()
                    content = parts[1].strip()
                    speaker_match = (speaker, content)
            
            if speaker_match:
                # Save previous exchange if it exists
                if current_speaker and current_text:
                    exchanges.append({
                        "speaker": current_speaker,
                        "content": current_text.strip()
                    })
                
                # Start new exchange
                current_speaker = speaker_match[0]
                current_text = speaker_match[1]
            else:
                # Continue current exchange
                if current_speaker:
                    current_text += " " + line
        
        # Add the last exchange
        if current_speaker and current_text:
            exchanges.append({
                "speaker": current_speaker,
                "content": current_text.strip()
            })
        
        return exchanges 
 