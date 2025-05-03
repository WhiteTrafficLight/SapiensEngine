from typing import Dict, Any, List, Optional
import random
import json

class PhilosophicalNPC:
    """
    Represents a philosophical NPC in the simulation with distinct traits,
    philosophical positions, and the ability to engage in dialogue.
    """
    
    def __init__(self, npc_config: Dict[str, Any]):
        """
        Initialize an NPC from configuration
        
        Args:
            npc_config: Dictionary containing NPC configuration
        """
        self.id = npc_config["id"]
        self.name = npc_config["name"]
        self.role = npc_config["role"]
        self.personality_traits = npc_config["personality_traits"]
        self.philosophical_background = npc_config["philosophical_background"]
        self.initial_position = npc_config["initial_position"]
        self.voice_style = npc_config["voice_style"]
        
        # New attributes for customizable NPCs
        self.reference_philosophers = npc_config.get("reference_philosophers", [])
        self.philosopher_weights = npc_config.get("philosopher_weights", {})
        self.communication_style = npc_config.get("communication_style", "balanced")
        self.debate_approach = npc_config.get("debate_approach", "dialectical")
        
        # Track NPC state through the simulation
        self.current_position = self.initial_position
        self.position_history = []
        self.dialogues = []
        
    @property
    def conformity(self) -> float:
        """Tendency to conform to dominant ideas"""
        return self.personality_traits.get("conformity", 0.5)
        
    @property
    def critical_thinking(self) -> float:
        """Ability to critically analyze ideas"""
        return self.personality_traits.get("critical_thinking", 0.5)
        
    @property
    def creativity(self) -> float:
        """Ability to generate new ideas"""
        return self.personality_traits.get("creativity", 0.5)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert NPC to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "personality_traits": self.personality_traits,
            "philosophical_background": self.philosophical_background,
            "current_position": self.current_position,
            "voice_style": self.voice_style,
            "reference_philosophers": self.reference_philosophers,
            "philosopher_weights": self.philosopher_weights,
            "communication_style": self.communication_style,
            "debate_approach": self.debate_approach
        }
        
    def to_prompt_format(self) -> str:
        """Format NPC information for inclusion in LLM prompts"""
        traits_str = ", ".join([f"{k}: {v}" for k, v in self.personality_traits.items()])
        background_str = ", ".join(self.philosophical_background)
        
        # Include reference philosophers if available
        ref_philosophers = ""
        if self.reference_philosophers:
            philosophers_with_weights = []
            for philosopher in self.reference_philosophers:
                weight = self.philosopher_weights.get(philosopher, 1.0)
                philosophers_with_weights.append(f"{philosopher} (weight: {weight:.1f})")
            ref_philosophers = f"Reference Philosophers: {', '.join(philosophers_with_weights)}\n"
        
        # Include communication style if specified
        style_info = ""
        if self.communication_style != "balanced":
            style_info = f"Communication Style: {self.communication_style}\n"
            
        # Include debate approach if specified
        approach_info = ""
        if self.debate_approach != "dialectical":
            approach_info = f"Debate Approach: {self.debate_approach}\n"
        
        return (
            f"Name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Personality Traits: {traits_str}\n"
            f"Philosophical Background: {background_str}\n"
            f"Current Position: {self.current_position}\n"
            f"Voice Style: {self.voice_style}\n"
            f"{ref_philosophers}"
            f"{style_info}"
            f"{approach_info}"
        )
        
    def update_position(self, new_position: str):
        """
        Update the NPC's philosophical position
        
        Args:
            new_position: The new philosophical position
        """
        self.position_history.append(self.current_position)
        self.current_position = new_position
        
    def add_dialogue(self, dialogue_entry: Dict[str, Any]):
        """
        Add a dialogue entry to the NPC's dialogue history
        
        Args:
            dialogue_entry: Dictionary containing dialogue information
        """
        self.dialogues.append(dialogue_entry)
        
    def calculate_response_tendency(self, zeitgeist: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate how this NPC is likely to respond to the current zeitgeist
        
        Args:
            zeitgeist: Dictionary representing current dominant ideas
            
        Returns:
            Dictionary with response tendencies (accept, reject, transform)
        """
        # Basic calculation based on personality traits
        accept_tendency = self.conformity * 0.7 + (1 - self.critical_thinking) * 0.3
        reject_tendency = self.critical_thinking * 0.6 + (1 - self.conformity) * 0.4
        transform_tendency = self.creativity * 0.8 + self.critical_thinking * 0.2
        
        # Adjust based on communication style
        if self.communication_style == "assertive":
            reject_tendency *= 1.2
            accept_tendency *= 0.8
        elif self.communication_style == "collaborative":
            transform_tendency *= 1.2
            reject_tendency *= 0.8
        elif self.communication_style == "analytical":
            critical_thinking_factor = 1.0 + (self.critical_thinking * 0.5)
            reject_tendency *= critical_thinking_factor
            transform_tendency *= critical_thinking_factor
            accept_tendency /= critical_thinking_factor
        
        # Normalize so they sum to 1.0
        total = accept_tendency + reject_tendency + transform_tendency
        
        return {
            "accept": accept_tendency / total,
            "reject": reject_tendency / total,
            "transform": transform_tendency / total
        }
        
    def get_dialogue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about this NPC's dialogue participation
        
        Returns:
            Dictionary containing dialogue statistics
        """
        if not self.dialogues:
            return {"total_dialogues": 0}
            
        return {
            "total_dialogues": len(self.dialogues),
            "average_length": sum(len(d.get("content", "")) for d in self.dialogues) / len(self.dialogues),
            "common_themes": self._extract_common_themes()
        }
        
    def _extract_common_themes(self) -> List[str]:
        """Extract common themes from dialogue history"""
        # This would be more sophisticated in a real implementation
        # Here we'll just return a placeholder
        return ["theme1", "theme2"]
        
    @classmethod
    def create_custom_npc(cls, 
                         name: str, 
                         role: str, 
                         voice_style: str,
                         reference_philosophers: List[str],
                         philosopher_weights: Optional[Dict[str, float]] = None,
                         communication_style: str = "balanced",
                         debate_approach: str = "dialectical",
                         personality_traits: Optional[Dict[str, float]] = None) -> 'PhilosophicalNPC':
        """
        Create a custom NPC with user-defined attributes
        
        Args:
            name: NPC name
            role: NPC role description
            voice_style: Description of speaking style
            reference_philosophers: List of philosophers to reference
            philosopher_weights: Optional weights for each philosopher (0.0-2.0 scale)
            communication_style: Style of communication (balanced, assertive, collaborative, analytical)
            debate_approach: Approach to debate (dialectical, analytical, pragmatic, critical)
            personality_traits: Optional custom personality traits
            
        Returns:
            A new PhilosophicalNPC instance
        """
        # Generate a unique ID
        npc_id = f"custom_{name.lower().replace(' ', '_')}_{random.randint(1000, 9999)}"
        
        # Generate default personality traits if not provided
        if not personality_traits:
            personality_traits = {
                "conformity": random.uniform(0.3, 0.7),
                "critical_thinking": random.uniform(0.4, 0.9),
                "creativity": random.uniform(0.4, 0.8),
                "dogmatism": random.uniform(0.2, 0.6),
                "openness": random.uniform(0.4, 0.9),
                "rationality": random.uniform(0.5, 0.9),
                "emotionality": random.uniform(0.3, 0.8),
                "collectivism": random.uniform(0.3, 0.8),
                "individualism": random.uniform(0.3, 0.8)
            }
            
        # Process philosopher weights
        if not philosopher_weights and reference_philosophers:
            philosopher_weights = {philosopher: 1.0 for philosopher in reference_philosophers}
            
        # Derive philosophical background from reference philosophers
        philosophical_background = []
        for philosopher in reference_philosophers:
            if philosopher in ["Socrates", "Plato", "Aristotle"]:
                philosophical_background.append("Classical Greek Philosophy")
            elif philosopher in ["Kant", "Hegel", "Schopenhauer"]:
                philosophical_background.append("German Idealism")
            elif philosopher in ["Nietzsche", "Sartre", "Camus", "Heidegger"]:
                philosophical_background.append("Existentialism")
            elif philosopher in ["Marx", "Engels", "Adorno", "Horkheimer"]:
                philosophical_background.append("Critical Theory")
            elif philosopher in ["Confucius", "Lao Tzu", "Buddha"]:
                philosophical_background.append("Eastern Philosophy")
            elif philosopher in ["Wittgenstein", "Russell", "Frege"]:
                philosophical_background.append("Analytic Philosophy")
            elif philosopher in ["Foucault", "Derrida", "Deleuze"]:
                philosophical_background.append("Post-structuralism")
            elif philosopher in ["Singer", "Rawls", "Nozick"]:
                philosophical_background.append("Contemporary Ethics")
            else:
                philosophical_background.append("Contemporary Philosophy")
        
        # Remove duplicates
        philosophical_background = list(set(philosophical_background))
        
        # Generate an initial position based on the philosophers
        initial_position = f"Synthesizes perspectives from {', '.join(reference_philosophers)}, approaching philosophical questions with a {debate_approach} methodology"
        
        # Create the NPC configuration
        npc_config = {
            "id": npc_id,
            "name": name,
            "role": role,
            "personality_traits": personality_traits,
            "philosophical_background": philosophical_background,
            "initial_position": initial_position,
            "voice_style": voice_style,
            "reference_philosophers": reference_philosophers,
            "philosopher_weights": philosopher_weights,
            "communication_style": communication_style,
            "debate_approach": debate_approach
        }
        
        return cls(npc_config) 
 