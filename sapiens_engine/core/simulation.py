import os
import sys
import time
import json
import random
import logging
import re
from typing import Dict, List, Any, Optional, Union

# Add imports for new features
from sapiens_engine.utils.context_manager import UserContextManager

from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.core.source_loader import SourceLoader
from sapiens_engine.core.llm_manager import LLMManager
# Add import for local LLM manager
from sapiens_engine.core.local_llm_manager import LocalLLMManager
from sapiens_engine.models.npc import PhilosophicalNPC
from sapiens_engine.utils.logger import SimulationLogger

logger = logging.getLogger(__name__)

class PhilosophicalSimulation:
    """
    Core simulation engine that orchestrates philosophical dialogues between NPCs.
    """
    
    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the simulation.
        
        Args:
            config_loader: Configuration loader
        """
        self.config_loader = config_loader
        self.main_config = config_loader.get_main_config()
        self.simulation_config = self.main_config.get("simulation", {})
        self.environment_config = self.main_config.get("environment", {})
        
        # Initialize NPCs
        npc_configs = config_loader.get_all_npcs()
        self.npcs = {npc_config["id"]: PhilosophicalNPC(npc_config) for npc_config in npc_configs}
        
        # Initialize source loader for philosophical texts
        sources_config = self.main_config.get("sources", {})
        sources_dir = sources_config.get("directory", "data/sources")
        self.source_loader = SourceLoader(sources_dir)
        
        # Initialize LLM manager
        llm_config = self.main_config.get("llm", {})
        self.llm_manager = LLMManager(llm_config)
        
        # Initialize context manager
        self.context_manager = self.llm_manager.context_manager
        
        # Initialize simulation state
        self.current_turn = 0
        self.dialogue_history = []
        self.zeitgeist = self._initialize_zeitgeist()
        self.custom_npcs = {}  # Store user-created NPCs
        
        # Set up logging
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        self.logger = SimulationLogger(log_dir, self.simulation_config.get("log_level", "info"))
        
    def _initialize_zeitgeist(self) -> Dict[str, Any]:
        """
        Initialize the philosophical zeitgeist (dominant ideas).
        
        Returns:
            Dictionary representing the zeitgeist
        """
        # Use the dominant ideologies from the environment config as a starting point
        ideologies = self.environment_config.get("dominant_ideologies", [])
        
        # Simple initial zeitgeist with placeholder values
        zeitgeist = {
            "dominant_ideas": ideologies,
            "idea_strengths": {idea: random.uniform(0.6, 0.8) for idea in ideologies},
            "philosophical_trends": {}
        }
        
        return zeitgeist
        
    def set_llm_manager(self, llm_manager: Union[LLMManager, LocalLLMManager]):
        """
        Set or replace the LLM manager used by the simulation.
        
        This allows for switching between OpenAI and local LLM without reinitializing the simulation.
        
        Args:
            llm_manager: The LLM manager instance to use
        """
        self.llm_manager = llm_manager
        # Update the context manager reference to use the one from the new LLM manager
        if hasattr(llm_manager, 'context_manager'):
            self.context_manager = llm_manager.context_manager
        logger.info(f"Set simulation to use {type(llm_manager).__name__}")
        
    def run_simulation(self, num_turns: int, topics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run the complete simulation for the specified number of turns.
        
        Args:
            num_turns: Number of turns to run
            topics: List of topics for each turn (optional)
            
        Returns:
            Dictionary with simulation results
        """
        self.current_turn = 0
        self.dialogue_history = []
        
        # Run the simulation for the specified number of turns
        for turn in range(num_turns):
            self.current_turn = turn + 1
            
            # Determine the topic for this turn
            if topics and turn < len(topics):
                topic = topics[turn]
            else:
                # Use a default topic or generate one
                default_topics = self.simulation_config.get("default_topics", ["The nature of consciousness"])
                topic = random.choice(default_topics)
                
            logger.info(f"Running turn {turn + 1}/{num_turns} with topic: {topic}")
            
            # Run a single turn
            turn_results = self._run_simulation_turn(topic)
            
            # Update the zeitgeist based on this turn's dialogue
            self._update_zeitgeist(turn_results)
            
            # Store the results in the dialogue history
            self.dialogue_history.append(turn_results)
            
        # Compile and return the simulation results
        return self._compile_simulation_results()
        
    def add_custom_npc(self, 
                      name: str, 
                      role: str, 
                      voice_style: str,
                      reference_philosophers: List[str],
                      philosopher_weights: Optional[Dict[str, float]] = None,
                      communication_style: str = "balanced",
                      debate_approach: str = "dialectical",
                      personality_traits: Optional[Dict[str, float]] = None) -> str:
        """
        Add a custom NPC to the simulation.
        
        Args:
            name: NPC name
            role: NPC role description
            voice_style: Description of speaking style
            reference_philosophers: List of philosophers to reference
            philosopher_weights: Optional weights for each philosopher
            communication_style: Style of communication
            debate_approach: Approach to debate
            personality_traits: Optional custom personality traits
            
        Returns:
            ID of the created NPC
        """
        # Create the custom NPC
        npc = PhilosophicalNPC.create_custom_npc(
            name=name,
            role=role,
            voice_style=voice_style,
            reference_philosophers=reference_philosophers,
            philosopher_weights=philosopher_weights,
            communication_style=communication_style,
            debate_approach=debate_approach,
            personality_traits=personality_traits
        )
        
        # Add to our NPCs collection
        self.npcs[npc.id] = npc
        self.custom_npcs[npc.id] = npc
        
        logger.info(f"Added custom NPC: {name} (ID: {npc.id})")
        
        return npc.id
        
    def add_context_from_text(self, text: str, title: str = "User Input") -> str:
        """
        Add user-provided text as context for the dialogue.
        
        Args:
            text: The text content
            title: A title for this context
            
        Returns:
            The ID of the added context
        """
        context_id = self.context_manager.add_text_context(text, title)
        logger.info(f"Added user context: {title} (ID: {context_id})")
        return context_id
        
    def add_context_from_file(self, file_path: str) -> str:
        """
        Add context from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            The ID of the added context
        """
        context_id = self.context_manager.add_file_context(file_path)
        logger.info(f"Added file context: {file_path} (ID: {context_id})")
        return context_id
        
    def add_context_from_url(self, url: str) -> str:
        """
        Add context from a URL.
        
        Args:
            url: The URL to fetch content from
            
        Returns:
            The ID of the added context
        """
        context_id = self.context_manager.add_url_context(url)
        logger.info(f"Added URL context: {url} (ID: {context_id})")
        return context_id
        
    def set_active_contexts(self, context_ids: List[str]):
        """
        Set which contexts should be active for the dialogue.
        
        Args:
            context_ids: List of context IDs to activate
        """
        self.context_manager.set_active_contexts(context_ids)
        logger.info(f"Set active contexts: {context_ids}")
        
    def get_all_contexts(self) -> List[Dict[str, Any]]:
        """
        Get all available contexts.
        
        Returns:
            List of all context dictionaries
        """
        return self.context_manager.get_all_contexts()
        
    def _run_simulation_turn(self, topic: str, selected_npc_ids=None, selected_sources=None) -> Dict[str, Any]:
        """
        Run a single turn of the simulation.
        
        Args:
            topic: The philosophical topic for this turn
            selected_npc_ids: Optional list of specific NPCs to include in the dialogue
            selected_sources: Optional list of specific source names to include
            
        Returns:
            Dictionary containing the turn results
        """
        # Get philosophical sources
        if selected_sources:
            # Use specifically selected sources
            source_materials = []
            all_sources = self.source_loader.get_all_sources()
            
            for source in all_sources:
                if source["name"] in selected_sources:
                    # Extract relevant excerpts from this specific source
                    content = source["content"].lower()
                    keywords = set(re.findall(r'\w+', topic.lower()))
                    
                    # Find paragraphs with keyword matches
                    paragraphs = re.split(r'\n\s*\n', content)
                    scored_paragraphs = []
                    
                    for para in paragraphs:
                        if len(para.strip()) < 50:  # Skip very short paragraphs
                            continue
                            
                        # Count keyword matches
                        score = sum(1 for keyword in keywords if keyword in para)
                        if score > 0:
                            scored_paragraphs.append((score, para))
                    
                    # Sort by score and take top match
                    scored_paragraphs.sort(reverse=True)
                    
                    if scored_paragraphs:
                        score, para = scored_paragraphs[0]
                        # Trim to approximate length
                        excerpt_length = 200
                        if len(para) > excerpt_length:
                            # Try to find a good breaking point
                            end_pos = para.rfind('. ', 0, excerpt_length) + 1
                            if end_pos <= 0:
                                end_pos = excerpt_length
                            para = para[:end_pos] + '...'
                            
                        source_materials.append({
                            "text": para,
                            "source": source["name"],
                            "author": source["author"],
                            "relevance": score
                        })
        else:
            # Get relevant philosophical sources based on topic
            source_materials = self.source_loader.get_relevant_excerpts(
                query=topic,
                max_excerpts=3,
                excerpt_length=200
            )
        
        # Get relevant user contexts
        user_contexts = self.context_manager.get_relevant_contexts(
            topic=topic,
            max_contexts=3
        )
        
        # Log what we're using
        logger.info(f"Topic: {topic}")
        logger.info(f"Found {len(source_materials)} relevant source materials")
        logger.info(f"Found {len(user_contexts)} relevant user contexts")
        
        # Handle NPC selection
        if selected_npc_ids:
            # Use specifically selected NPCs
            selected_npc_ids = [npc_id for npc_id in selected_npc_ids if npc_id in self.npcs]
            if len(selected_npc_ids) < 2:
                logger.warning("Not enough valid NPCs selected. Using default NPCs.")
                selected_npc_ids = list(self.npcs.keys())[:2]
        else:
            # Select NPCs for this dialogue
            # Use 2 NPCs by default, or more based on configuration
            num_participants = self.simulation_config.get("participants_per_turn", 2)
            num_participants = min(num_participants, len(self.npcs))
            
            if num_participants < 2:
                logger.warning("Not enough NPCs for dialogue. Using default NPCs.")
                selected_npc_ids = list(self.npcs.keys())[:2]
            else:
                selected_npc_ids = random.sample(list(self.npcs.keys()), num_participants)
        
        selected_npcs = [self.npcs[npc_id] for npc_id in selected_npc_ids]
        logger.info(f"Selected NPCs: {[npc.name for npc in selected_npcs]}")
        
        # Track dialogue through multiple rounds if configured
        dialogue_rounds = self.simulation_config.get("dialogue_rounds_per_turn", 3)
        previous_dialogue = ""
        
        # Store exchanges for all rounds
        all_exchanges = []
        
        # Run the dialogue for the specified number of rounds
        for round_num in range(dialogue_rounds):
            logger.info(f"Round {round_num + 1}/{dialogue_rounds}")
            
            # Handle multiple participants
            if len(selected_npcs) > 2:
                # For multi-participant dialogues, cycle through participants
                # Each round, two participants will exchange ideas
                idx1 = round_num % len(selected_npcs)
                idx2 = (round_num + 1) % len(selected_npcs)
                npc1 = selected_npcs[idx1]
                npc2 = selected_npcs[idx2]
            else:
                # Use the same two NPCs for each round
                npc1 = selected_npcs[0]
                npc2 = selected_npcs[1]
            
            # Generate dialogue exchange
            dialogue_result = self.llm_manager.generate_dialogue_exchange(
                npc1_description=npc1.to_prompt_format(),
                npc2_description=npc2.to_prompt_format(),
                topic=topic,
                previous_dialogue=previous_dialogue,
                source_materials=source_materials,
                user_contexts=user_contexts,
                references=None
            )
            
            # Update the previous dialogue for the next round
            previous_dialogue = previous_dialogue + "\n\n" + dialogue_result["raw_text"]
            
            # Extract philosophical positions when possible
            for exchange in dialogue_result["exchanges"]:
                speaker_name = exchange["speaker"]
                content = exchange["content"]
                
                # Log the content
                logger.info(f"{speaker_name}: {content}")
                
                # Extract potential summary sentences or key points
                summary = self._extract_summary_sentence(content)
                if summary:
                    logger.info(f"  Summary: {summary}")
                
                # Add exchange to the results
                exchange_info = {
                    "speaker": speaker_name,
                    "content": content,
                    "summary": summary
                }
                all_exchanges.append(exchange_info)
                
                # Try to determine which NPC this is to update their dialogue history
                for npc in selected_npcs:
                    if npc.name in speaker_name:
                        npc.add_dialogue({
                            "turn": self.current_turn,
                            "round": round_num + 1,
                            "topic": topic,
                            "content": content,
                            "summary": summary
                        })
                        
                        # Try to extract a philosophical position
                        position = self._extract_philosophical_position(content)
                        if position:
                            logger.info(f"Extracted position for {npc.name}: {position}")
                            npc.update_position(position)
                
        # Assemble results for this turn
        turn_results = {
            "turn": self.current_turn,
            "topic": topic,
            "participating_npcs": selected_npc_ids,
            "source_materials": [source["source"] for source in source_materials],
            "user_contexts": [ctx["title"] for ctx in user_contexts],
            "exchanges": all_exchanges,
            "raw_dialogue": previous_dialogue
        }
        
        return turn_results
        
    def _extract_summary_sentence(self, text: str) -> Optional[str]:
        """
        Extract a likely summary sentence from the text.
        
        Args:
            text: The text to analyze
            
        Returns:
            A summary sentence if found, otherwise None
        """
        # A very simple approach: assume the last sentence might be a summary
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            return sentences[-1]
        return None
        
    def _extract_philosophical_position(self, text: str) -> Optional[str]:
        """
        Extract a philosophical position from the text.
        This is a simplified implementation.
        
        Args:
            text: The text to analyze
            
        Returns:
            A philosophical position if found, otherwise None
        """
        # Look for statements that might indicate a position
        position_markers = [
            r"I believe that (.*?)[.!?]",
            r"My position is that (.*?)[.!?]",
            r"In my view, (.*?)[.!?]",
            r"I maintain that (.*?)[.!?]",
            r"The core insight is that (.*?)[.!?]"
        ]
        
        for marker in position_markers:
            match = re.search(marker, text)
            if match:
                return match.group(1)
                
        # If no clear position found, use the summary sentence
        return self._extract_summary_sentence(text)
        
    def _update_zeitgeist(self, turn_results: Dict[str, Any]):
        """
        Update the zeitgeist based on dialogue from a turn.
        
        Args:
            turn_results: Results from a simulation turn
        """
        # Extract key concepts and their strength from the dialogue
        concepts = {}
        
        # Analyze exchanges for repeated terms/concepts
        for exchange in turn_results["exchanges"]:
            content = exchange.get("content", "")
            summary = exchange.get("summary", "")
            
            # Very simple concept extraction - look for capitalized terms
            # A real implementation would use NLP techniques
            capitalized_terms = re.findall(r'\b[A-Z][a-z]{3,}\b', content)
            for term in capitalized_terms:
                concepts[term] = concepts.get(term, 0) + 1
                
            # Give higher weight to terms in summaries
            if summary:
                capitalized_in_summary = re.findall(r'\b[A-Z][a-z]{3,}\b', summary)
                for term in capitalized_in_summary:
                    concepts[term] = concepts.get(term, 0) + 2
        
        # Update the zeitgeist with new concept strengths
        total_mentions = sum(concepts.values()) or 1  # Avoid division by zero
        
        for concept, mentions in concepts.items():
            strength = mentions / total_mentions
            
            if concept in self.zeitgeist["philosophical_trends"]:
                # Update existing concept - weighted average
                current = self.zeitgeist["philosophical_trends"][concept]
                self.zeitgeist["philosophical_trends"][concept] = (current * 0.7) + (strength * 0.3)
            else:
                # Add new concept
                self.zeitgeist["philosophical_trends"][concept] = strength
        
        # Record the zeitgeist state for this turn
        zeitgeist_snapshot = {
            "turn": self.current_turn,
            "trends": self.zeitgeist["philosophical_trends"].copy()
        }
        
        # Store the snapshot if not already in results
        if not hasattr(self, "zeitgeist_history"):
            self.zeitgeist_history = []
            
        self.zeitgeist_history.append(zeitgeist_snapshot)
        
    def _compile_simulation_results(self) -> Dict[str, Any]:
        """
        Compile the final results of the simulation.
        
        Returns:
            Dictionary with comprehensive simulation results
        """
        # Get final states of all NPCs
        npc_states = {}
        for npc_id, npc in self.npcs.items():
            npc_states[npc_id] = npc.to_dict()
            
        # Compile results
        results = {
            "simulation_config": self.simulation_config,
            "environment": self.environment_config,
            "dialogue_history": self.dialogue_history,
            "philosophical_trends": getattr(self, "zeitgeist_history", []),
            "npc_states": npc_states,
            "custom_npcs": {npc_id: npc.to_dict() for npc_id, npc in self.custom_npcs.items()},
            "user_contexts": self.context_manager.get_all_contexts()
        }
        
        return results
        
    def save_simulation_results(self, results: Dict[str, Any], filename: str = None):
        """
        Save simulation results to a file
        
        Args:
            results: Simulation results to save
            filename: Optional filename to use
        """
        if filename is None:
            timestamp = datetime.fromtimestamp(results["timestamp"])
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_results_{timestamp_str}.json"
            
        results_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            'logs', 
            'results'
        )
        os.makedirs(results_dir, exist_ok=True)
        
        results_path = os.path.join(results_dir, filename)
        
        with open(results_path, 'w', encoding='utf-8') as f:
            # Use a custom serializer to handle non-serializable objects
            json.dump(results, f, indent=2, default=lambda o: str(o))
            
        self.logger.info(f"Simulation results saved to {results_path}")
        return results_path 
 