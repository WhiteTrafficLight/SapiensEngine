#!/usr/bin/env python
import os
import sys
import time
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import io
import requests
from typing import Dict, List, Any, Optional
import random
import re

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.core import SourceLoader  # Changed import to use the __init__ module
from sapiens_engine.core.simulation import PhilosophicalSimulation
from sapiens_engine.utils.visualizer import PhilosophicalVisualizer
from sapiens_engine.utils.audio_generator import AudioGenerator
from sapiens_engine.models.npc import PhilosophicalNPC

# Import LLM managers
from sapiens_engine.core.llm_manager import LLMManager
from sapiens_engine.core.local_llm_manager import LocalLLMManager

# SAPIENS ENGINE: Philosophical Dialogue Simulation Platform
#
# Future Development Notes for Multi-User Environment:
# -------------------------------------------------
# For converting this application into a multi-user platform with dialogue rooms:
#
# 1. Database Integration:
#    - Implement a database (MongoDB, PostgreSQL, etc.) to store:
#      - User accounts and profiles
#      - Dialogue rooms data
#      - Shared contexts
#      - Generated papers
#
# 2. Authentication:
#    - Add user authentication and authorization
#    - Support user roles (admin, moderator, regular user)
#
# 3. Real-time Updates:
#    - Implement WebSocket for real-time dialogue updates using Socket.IO
#    - Consider migrating from Streamlit to a framework like Flask or FastAPI with React/Vue frontend
#    - Alternatively, explore Streamlit sharing capabilities
#
# 4. Dialogue Room Management:
#    - Create, join, and manage dialogue rooms
#    - Set up public vs. private rooms
#    - Room discovery and invitation system
#    - Room state persistence
#
# 5. Context Sharing:
#    - Allow users to share contexts across dialogue rooms
#    - Create a context library/repository
#    - Version control for contexts
#
# 6. Paper Generation & Sharing:
#    - Collaborative paper editing
#    - Citation management
#    - Paper version control
#    - PDF export and formatting
#
# 7. Deployment Options:
#    - Docker containerization for consistent deployment
#    - Kubernetes for scaling
#    - Cloud hosting (AWS, GCP, Azure)
#
# The current Streamlit implementation serves as a prototype for these features.
# For a full multi-user system, consider migrating to a more scalable web framework.

# Set page configuration
st.set_page_config(
    page_title="Sapiens Engine - Philosophical Simulation",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False
    
if "simulation_results" not in st.session_state:
    st.session_state.simulation_results = None
    
if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0
    
if "dialogue_history" not in st.session_state:
    st.session_state.dialogue_history = []

if "config_loader" not in st.session_state:
    st.session_state.config_loader = ConfigLoader()

if "llm_type" not in st.session_state:
    st.session_state.llm_type = "openai"  # Default to OpenAI
    
if "local_model_path" not in st.session_state:
    # Default local model path - update this based on where models will be stored
    st.session_state.local_model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    
if "local_model_type" not in st.session_state:
    st.session_state.local_model_type = "auto"
    
if "device" not in st.session_state:
    st.session_state.device = "auto"
    
if "simulation" not in st.session_state:
    # Initialize with the default LLM manager (OpenAI)
    st.session_state.simulation = PhilosophicalSimulation(st.session_state.config_loader)
    
if "user_contexts" not in st.session_state:
    st.session_state.user_contexts = []
    
if "custom_npcs" not in st.session_state:
    st.session_state.custom_npcs = []
    
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Home"

def load_configurations():
    """Load configurations for the simulation"""
    config_loader = st.session_state.config_loader
    main_config = config_loader.get_main_config()
    npcs = config_loader.get_all_npcs()
    return main_config, npcs

def initialize_simulation_with_model():
    """Initialize or reinitialize the simulation with the selected model type"""
    config_loader = st.session_state.config_loader
    
    # Create a new simulation with the appropriate LLM manager
    if st.session_state.llm_type == "local":
        # Check if model path exists
        model_path = st.session_state.local_model_path
        if not os.path.exists(model_path):
            st.error(f"Model path not found: {model_path}")
            return False
            
        # Create LocalLLMManager
        try:
            local_llm_manager = LocalLLMManager(
                model_path=model_path,
                model_type=st.session_state.local_model_type,
                device=st.session_state.device,
                quantize=True
            )
            
            # Create a new simulation with the local LLM manager
            simulation = PhilosophicalSimulation(config_loader)
            # Replace the default LLM manager with our local one
            simulation.set_llm_manager(local_llm_manager)
            
            # Update the session state
            st.session_state.simulation = simulation
            st.success(f"Initialized simulation with local model: {model_path}")
            return True
            
        except Exception as e:
            st.error(f"Error initializing local model: {str(e)}")
            return False
    else:
        # Use the default OpenAI LLM manager
        simulation = PhilosophicalSimulation(config_loader)
        st.session_state.simulation = simulation
        st.success("Initialized simulation with OpenAI model")
        return True

def start_simulation(num_turns, topics, visualize, single_topic=False, selected_npcs=None, selected_sources=None):
    """Start the simulation with the given parameters"""
    # First make sure we have a valid simulation with the correct LLM manager
    if not initialize_simulation_with_model():
        st.error("Failed to initialize simulation with the selected model.")
        return None
        
    st.session_state.simulation_running = True
    st.session_state.current_turn = 0
    st.session_state.dialogue_history = []
    
    # Create a placeholder for simulation updates
    progress_ph = st.empty()
    progress_bar = progress_ph.progress(0)
    
    status_ph = st.empty()
    status_ph.info("Initializing simulation...")
    
    # Get the simulation instance
    simulation = st.session_state.simulation
    
    # Handle single topic mode
    if single_topic:
        # Use the first topic for all turns
        topic_list = [topics.strip()] * num_turns
    else:
        # Set up topic list if provided
        topic_list = topics.split("\n") if topics else None
    
    # Run the simulation manually, turn by turn
    total_turns = num_turns
    st.session_state.current_turn = 0
    
    # Create a expander for displaying dialogue updates
    dialogue_expander = st.expander("Dialogue Updates", expanded=True)
    
    # Show which LLM is being used
    llm_type = "Local" if st.session_state.llm_type == "local" else "OpenAI"
    if st.session_state.llm_type == "local":
        model_info = f"Model: {st.session_state.local_model_path}, Device: {st.session_state.device}"
    else:
        model_info = f"Model: {simulation.llm_manager.llm_config.get('model', 'gpt-4')}"
    
    st.info(f"Using {llm_type} LLM for dialogue generation. {model_info}")
    
    for turn in range(total_turns):
        st.session_state.current_turn = turn + 1
        progress = (turn + 1) / total_turns
        progress_bar.progress(progress)
        
        # Get the topic for this turn
        if topic_list and turn < len(topic_list):
            topic = topic_list[turn]
        else:
            # Use a default topic if none provided
            topic = "The nature of consciousness and free will"
            
        status_ph.info(f"Running turn {turn + 1}/{total_turns}: Topic '{topic}'")
        
        # Run a single turn of the simulation with selected participants if provided
        if selected_npcs:
            turn_results = simulation._run_simulation_turn(topic, selected_npcs, selected_sources)
        else:
            turn_results = simulation._run_simulation_turn(topic)
        
        # Ensure no duplicate source materials
        if "source_materials" in turn_results:
            # Create a temporary list with unique sources
            unique_sources = []
            seen_source_ids = set()
            
            for source in turn_results["source_materials"]:
                source_id = source.get("id")
                if source_id and source_id not in seen_source_ids:
                    unique_sources.append(source)
                    seen_source_ids.add(source_id)
            
            # Replace the original list with the de-duplicated one
            turn_results["source_materials"] = unique_sources
        
        # Update the simulation state
        simulation._update_zeitgeist(turn_results)
        simulation.dialogue_history.append(turn_results)
        st.session_state.dialogue_history.append(turn_results)
        
        # Display the dialogue
        with dialogue_expander:
            st.subheader(f"Turn {turn + 1}: {topic}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Participants")
                for npc_id in turn_results["participating_npcs"]:
                    npc = simulation.npcs[npc_id]
                    st.write(f"- **{npc.name}** ({npc.role})")
                    
            with col2:
                if turn_results.get("source_materials"):
                    st.write("#### Source Materials")
                    # Use a set to track already displayed sources by ID
                    displayed_sources = set()
                    for source in turn_results.get("source_materials", []):
                        source_id = source.get("id", "")
                        source_name = source.get("source", "Unknown")
                        author = source.get("author", "Unknown")
                        display_key = f"{source_name}-{author}"
                        
                        if display_key not in displayed_sources:
                            st.write(f"- {source_name} by {author}")
                            displayed_sources.add(display_key)
                
                if turn_results.get("user_contexts"):
                    st.write("#### User Contexts")
                    # Use a set to avoid duplicate contexts
                    displayed_contexts = set()
                    for context in turn_results.get("user_contexts", []):
                        if context not in displayed_contexts:
                            st.write(f"- {context}")
                            displayed_contexts.add(context)
                    
            st.write("#### Dialogue")
            for exchange in turn_results["exchanges"]:
                speaker = exchange["speaker"]
                content = exchange["content"]
                summary = exchange.get("summary", "")
                
                st.markdown(f"**{speaker}**: {content}")
                if summary and summary not in content:
                    st.markdown(f"*Summary: {summary}*")
            
            st.write("---")
        
        # Short pause for UI updates
        time.sleep(0.5)
    
    # Complete the simulation
    results = simulation._compile_simulation_results()
    st.session_state.simulation_results = results
    
    # Update UI when complete
    progress_bar.progress(1.0)
    status_ph.success(f"Simulation completed successfully! Ran {total_turns} turns of philosophical dialogue.")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'results')
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, f"simulation_results_{timestamp}.json")
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=lambda o: str(o))
    
    st.session_state.simulation_running = False
    
    return results

def add_user_context():
    """Add a user-provided context to the simulation"""
    simulation = st.session_state.simulation
    
    st.subheader("Add Context for Dialogue")
    
    # Create tabs for different input methods
    context_tabs = st.tabs(["Text Input", "File Upload", "URL"])
    
    with context_tabs[0]:
        st.write("Enter text that should be used as context for the philosophical dialogue:")
        text_title = st.text_input("Title/Label for this context", "My Text Input")
        text_content = st.text_area("Text content (philosophical material, article, etc.)", height=250)
        
        if st.button("Add Text Context"):
            if text_content:
                context_id = simulation.add_context_from_text(text_content, text_title)
                st.success(f"Added context: {text_title} (ID: {context_id})")
                # Refresh the context list
                st.session_state.user_contexts = simulation.get_all_contexts()
                st.rerun()
            else:
                st.warning("Please enter some text content")
    
    with context_tabs[1]:
        st.write("Upload a text file to use as context:")
        uploaded_file = st.file_uploader("Choose a text file", type=["txt", "md", "csv", "json"])
        
        if uploaded_file and st.button("Add File Context"):
            # Save the uploaded file temporarily
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            context_id = simulation.add_context_from_file(file_path)
            st.success(f"Added file context: {uploaded_file.name} (ID: {context_id})")
            
            # Refresh the context list
            st.session_state.user_contexts = simulation.get_all_contexts()
            st.rerun()
    
    with context_tabs[2]:
        st.write("Enter a URL to extract content from:")
        url = st.text_input("URL to fetch content from (article, blog, philosophical text, etc.)")
        
        if st.button("Add URL Context"):
            if url:
                try:
                    context_id = simulation.add_context_from_url(url)
                    st.success(f"Added URL context: {url} (ID: {context_id})")
                    # Refresh the context list
                    st.session_state.user_contexts = simulation.get_all_contexts()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error fetching URL: {str(e)}")
            else:
                st.warning("Please enter a URL")
    
    # Display current contexts
    st.subheader("Current Contexts")
    contexts = simulation.get_all_contexts()
    
    if not contexts:
        st.info("No contexts added yet. Add some context from above to provide materials for the dialogue.")
    else:
        st.write(f"Total contexts: {len(contexts)}")
        
        # Create a multiselect to choose active contexts
        active_context_ids = [ctx["id"] for ctx in contexts if ctx.get("active", False)]
        all_context_ids = [ctx["id"] for ctx in contexts]
        all_context_labels = [f"{ctx['title']} ({ctx['type']})" for ctx in contexts]
        
        selected_contexts = st.multiselect(
            "Select contexts to use in simulation",
            options=all_context_ids,
            default=active_context_ids,
            format_func=lambda x: all_context_labels[all_context_ids.index(x)],
            key="user_contexts_tab_select"
        )
        
        if st.button("Update Active Contexts"):
            simulation.set_active_contexts(selected_contexts)
            st.success(f"Updated active contexts: {len(selected_contexts)} selected")
            # Refresh the context list
            st.session_state.user_contexts = simulation.get_all_contexts()
            st.rerun()
        
        # Display context previews
        with st.expander("Context Previews", expanded=True):
            for ctx in contexts:
                st.markdown(f"**{ctx['title']}** ({ctx['type']}) - {'Active' if ctx.get('active', False) else 'Inactive'}")
                st.write(f"Source: {ctx['source']}")
                st.text_area(f"Excerpt from {ctx['title']}", value=ctx['content'][:200] + "...", height=100, key=f"ctx_{ctx['id']}")
                
                # Add a button to remove this context
                if st.button(f"Remove {ctx['title']}", key=f"remove_{ctx['id']}"):
                    simulation.context_manager.remove_context(ctx['id'])
                    st.success(f"Removed context: {ctx['title']}")
                    # Refresh the context list
                    st.session_state.user_contexts = simulation.get_all_contexts()
                    st.rerun()
                    
                st.write("---")

def add_custom_npc():
    """Add a custom NPC to the simulation"""
    simulation = st.session_state.simulation
    
    st.subheader("Create Custom Philosophical NPC")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("NPC Name", "Custom Philosopher")
        role = st.text_input("Role/Position", "Contemporary Thinker")
        
        voice_style = st.text_area("Voice Style", 
                                 "Clear, straightforward, using concrete examples and evidence-based reasoning")
                                 
        communication_style = st.selectbox(
            "Communication Style",
            ["balanced", "assertive", "collaborative", "analytical"],
            index=0,
            help="How this NPC communicates with others"
        )
        
        debate_approach = st.selectbox(
            "Debate Approach",
            ["dialectical", "analytical", "pragmatic", "critical"],
            index=0,
            help="The NPC's approach to philosophical debate"
        )
    
    with col2:
        # List of philosophers to choose from
        all_philosophers = [
            "Socrates", "Plato", "Aristotle",
            "Kant", "Hegel", "Schopenhauer", 
            "Nietzsche", "Sartre", "Camus", "Heidegger",
            "Marx", "Engels", "Adorno", "Horkheimer",
            "Confucius", "Lao Tzu", "Buddha",
            "Wittgenstein", "Russell", "Frege",
            "Foucault", "Derrida", "Deleuze",
            "Singer", "Rawls", "Nozick",
            "Harari", "Diamond", "Husserl"
        ]
        
        selected_philosophers = st.multiselect(
            "Reference Philosophers",
            options=all_philosophers,
            default=[],
            help="Philosophers that influence this NPC's thinking",
            key="custom_npcs_philosophers_select"
        )
        
        # Display sliders for weighting philosophers
        st.write("Philosopher Weights (importance of each philosopher's ideas)")
        philosopher_weights = {}
        
        for philosopher in selected_philosophers:
            weight = st.slider(f"Weight for {philosopher}", 0.1, 2.0, 1.0, 0.1, key=f"weight_{philosopher}")
            philosopher_weights[philosopher] = weight
        
        # Optional personality traits
        st.write("Personality Traits (optional)")
        
        custom_traits = {}
        traits_col1, traits_col2 = st.columns(2)
        
        with traits_col1:
            custom_traits["conformity"] = st.slider("Conformity", 0.0, 1.0, 0.5, 0.1)
            custom_traits["critical_thinking"] = st.slider("Critical Thinking", 0.0, 1.0, 0.7, 0.1)
            custom_traits["creativity"] = st.slider("Creativity", 0.0, 1.0, 0.6, 0.1)
            custom_traits["dogmatism"] = st.slider("Dogmatism", 0.0, 1.0, 0.4, 0.1)
        
        with traits_col2:
            custom_traits["openness"] = st.slider("Openness", 0.0, 1.0, 0.7, 0.1)
            custom_traits["rationality"] = st.slider("Rationality", 0.0, 1.0, 0.8, 0.1)
            custom_traits["emotionality"] = st.slider("Emotionality", 0.0, 1.0, 0.5, 0.1)
            custom_traits["collectivism"] = st.slider("Collectivism", 0.0, 1.0, 0.5, 0.1)
    
    # Create NPC button
    if st.button("Create NPC"):
        if not name or not role or not selected_philosophers:
            st.warning("Please provide a name, role, and select at least one reference philosopher")
        else:
            try:
                npc_id = simulation.add_custom_npc(
                    name=name,
                    role=role,
                    voice_style=voice_style,
                    reference_philosophers=selected_philosophers,
                    philosopher_weights=philosopher_weights,
                    communication_style=communication_style,
                    debate_approach=debate_approach,
                    personality_traits=custom_traits
                )
                
                st.success(f"Created custom NPC: {name} (ID: {npc_id})")
                
                # Update session state
                custom_npcs = []
                for npc_id, npc in simulation.custom_npcs.items():
                    custom_npcs.append(npc.to_dict())
                    
                st.session_state.custom_npcs = custom_npcs
                st.rerun()
                
            except Exception as e:
                st.error(f"Error creating NPC: {str(e)}")
    
    # Display current custom NPCs
    st.subheader("Custom NPCs")
    
    if not simulation.custom_npcs:
        st.info("No custom NPCs created yet.")
    else:
        for npc_id, npc in simulation.custom_npcs.items():
            with st.expander(f"{npc.name} - {npc.role}", expanded=False):
                st.write(f"**Voice Style:** {npc.voice_style}")
                st.write(f"**Communication Style:** {npc.communication_style}")
                st.write(f"**Debate Approach:** {npc.debate_approach}")
                
                st.write("**Reference Philosophers:**")
                for philosopher, weight in npc.philosopher_weights.items():
                    st.write(f"- {philosopher} (weight: {weight:.1f})")
                    
                st.write("**Personality Traits:**")
                for trait, value in npc.personality_traits.items():
                    st.write(f"- {trait}: {value:.1f}")
                    
                # Button to remove this NPC
                if st.button(f"Remove {npc.name}", key=f"remove_npc_{npc_id}"):
                    del simulation.npcs[npc_id]
                    del simulation.custom_npcs[npc_id]
                    st.success(f"Removed NPC: {npc.name}")
                    
                    # Update session state
                    custom_npcs = []
                    for npc_id, npc in simulation.custom_npcs.items():
                        custom_npcs.append(npc.to_dict())
                        
                    st.session_state.custom_npcs = custom_npcs
                    st.rerun()

def display_results(results):
    """Display the simulation results"""
    if not results:
        st.warning("No simulation results to display")
        return
        
    st.subheader("Simulation Results")
    
    # Set up tabs for different views
    tab1, tab2, tab3 = st.tabs(["Dialogues", "Philosophical Trends", "NPC States"])
    
    # Tab 1: Dialogues
    with tab1:
        dialogue_history = results.get("dialogue_history", [])
        
        for turn_data in dialogue_history:
            turn = turn_data.get("turn", 0)
            topic = turn_data.get("topic", "Unknown")
            
            with st.expander(f"Turn {turn}: {topic}", expanded=(turn == 1)):
                # Display context sources if available
                col1, col2 = st.columns(2)
                
                with col1:
                    if turn_data.get("source_materials"):
                        st.write("**Source Materials:**")
                        # Use a set to track displayed sources to avoid duplicates
                        displayed_sources = set()
                        for source in turn_data.get("source_materials", []):
                            # Create a unique identifier for each source
                            source_key = f"{source.get('source', 'Unknown')}-{source.get('author', 'Unknown')}"
                            if source_key not in displayed_sources:
                                st.write(f"- {source.get('source', 'Unknown')} by {source.get('author', 'Unknown')}")
                                displayed_sources.add(source_key)
                
                with col2:
                    if turn_data.get("user_contexts"):
                        st.write("**User Contexts:**")
                        # Use a set to track displayed contexts to avoid duplicates
                        displayed_contexts = set()
                        for ctx in turn_data.get("user_contexts", []):
                            # Create a unique identifier for each context
                            ctx_key = f"{ctx}"
                            if ctx_key not in displayed_contexts:
                                st.write(f"- {ctx}")
                                displayed_contexts.add(ctx_key)
                
                # Display exchanges
                st.write("**Dialogue:**")
                exchanges = turn_data.get("exchanges", [])
                
                for exchange in exchanges:
                    speaker = exchange.get("speaker", "Unknown")
                    content = exchange.get("content", "")
                    summary = exchange.get("summary", "")
                    
                    st.markdown(f"**{speaker}**: {content}")
                    if summary and summary not in content:
                        st.markdown(f"*Summary: {summary}*")
    
    # Tab 2: Philosophical Trends
    with tab2:
        trends_data = results.get("philosophical_trends", [])
        
        if trends_data:
            # Convert data for chart
            turns = [data["turn"] for data in trends_data]
            trend_names = list(trends_data[0]["trends"].keys())
            
            # Create a DataFrame
            df = pd.DataFrame(index=turns)
            for trend in trend_names:
                df[trend] = [data["trends"].get(trend, 0) for data in trends_data]
                
            # Plot the trends
            st.subheader("Evolution of Philosophical Trends")
            fig, ax = plt.subplots(figsize=(10, 6))
            
            for trend in trend_names:
                ax.plot(df.index, df[trend], marker='o', linewidth=2, label=trend)
                
            ax.set_title("Evolution of Philosophical Trends")
            ax.set_xlabel("Simulation Turn")
            ax.set_ylabel("Trend Strength")
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            ax.set_ylim(0, 1)
            
            st.pyplot(fig)
            
            # Also display as a table
            st.subheader("Trend Values")
            st.dataframe(df)
        else:
            st.warning("No trend data available")
    
    # Tab 3: NPC States
    with tab3:
        npc_states = results.get("npc_states", {})
        
        if npc_states:
            st.subheader("NPC Final States")
            
            for npc_id, npc_state in npc_states.items():
                with st.expander(f"{npc_state.get('name', npc_id)}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Role:** {npc_state.get('role', 'Unknown')}")
                        st.write(f"**Current Position:** {npc_state.get('current_position', 'Unknown')}")
                        
                        st.write("**Philosophical Background:**")
                        for bg in npc_state.get("philosophical_background", []):
                            st.write(f"- {bg}")
                            
                        # Display reference philosophers if available
                        if npc_state.get("reference_philosophers"):
                            st.write("**Reference Philosophers:**")
                            for philosopher in npc_state.get("reference_philosophers", []):
                                weight = npc_state.get("philosopher_weights", {}).get(philosopher, 1.0)
                                st.write(f"- {philosopher} (weight: {weight:.1f})")
                            
                    with col2:
                        st.write("**Personality Traits:**")
                        traits = npc_state.get("personality_traits", {})
                        
                        # Create a bar chart for traits
                        trait_names = list(traits.keys())
                        trait_values = list(traits.values())
                        
                        fig, ax = plt.subplots(figsize=(10, 4))
                        ax.barh(trait_names, trait_values, color='skyblue')
                        ax.set_xlim(0, 1)
                        ax.set_title("Personality Traits")
                        
                        st.pyplot(fig)
        else:
            st.warning("No NPC state data available")

# Helper function to get source materials based on topic and selected sources
def _get_source_materials(source_loader, topic, selected_sources):
    if selected_sources:
        # Use specifically selected sources
        source_materials = []
        all_sources = source_loader.get_all_sources()
        
        for source_id in selected_sources:
            # Find the source by ID and add it only if not already in the list
            for source in all_sources:
                if source.get("id") == source_id:
                    # Check if this source is already in source_materials
                    if not any(s.get("id") == source_id for s in source_materials):
                        source_materials.append(source)
                    break
                    
        return source_materials
    else:
        # Get relevant sources based on topic, ensuring no duplicates
        sources = source_loader.get_relevant_excerpts(query=topic, max_excerpts=3)
        # Remove duplicates by ID
        unique_sources = []
        added_ids = set()
        for source in sources:
            source_id = source.get("id")
            if source_id not in added_ids:
                unique_sources.append(source)
                added_ids.add(source_id)
        return unique_sources

def ensure_model_directory_exists():
    """Ensure that the model directory exists and create it if it doesn't.
    Also creates a README.md file in the directory if it doesn't exist.
    Returns the path to the model directory."""
    
    # Get the model directory path
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    
    # Create the directory if it doesn't exist
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
        
        # Create a README.md file with instructions
        readme_path = os.path.join(model_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write("""# Local Language Models

This directory is for storing local language model files for use with Sapiens Engine.

## Adding Models

To use a local model:
1. Place your model files or folders in this directory
2. In the app, go to Settings > Model Selection
3. Select "Local Model" and set the path to your model
4. Choose the appropriate model type and device options
5. Click "Test Local Model" to verify it works correctly

## Supported Model Formats

- LLaMa GGUF files (.gguf)
- Hugging Face model directories
- Other compatible model formats

Note: Using local models requires more system resources than the OpenAI API.
""")
        
    return model_dir

def main():
    """Main application function"""
    # Title and description
    st.title("Sapiens Engine: Philosophical Dialogue Simulation")
    
    # Custom CSS for better tabs at the top
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f5f5f5;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f7ff;
        border-bottom: 2px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main tabs - now at the top of the page instead of sidebar
    tabs = ["Home", "Results", "Settings", "Interactive", "User Contexts", "Custom NPCs"]
    
    # Determine the index of the active tab
    if "active_tab" not in st.session_state or st.session_state.active_tab not in tabs:
        active_tab_index = 0  # Default to first tab
    else:
        active_tab_index = tabs.index(st.session_state.active_tab)
    
    # Create the tabs
    tab_home, tab_results, tab_settings, tab_interactive, tab_user_contexts, tab_custom_npcs = st.tabs(tabs)
    
    # Load configuration and NPCs
    main_config, npcs = load_configurations()
    
    # Home tab (formerly Simulation)
    with tab_home:
        if active_tab_index == 0:  # Only update if this tab is active
            st.session_state.active_tab = "Home"
        
        # App Description
        st.markdown("""
        ## Welcome to Sapiens Engine
        
        Sapiens Engine is a philosophical dialogue simulation platform that enables you to:
        
        * Generate deep philosophical discussions between AI NPCs with distinct philosophical backgrounds
        * Create your own philosophical personas based on famous thinkers
        * Add your own context materials to influence the dialogue
        * Participate in real-time interactive discussions
        
        The engine uses advanced language models to simulate authentic philosophical exchanges,
        helping you explore complex ideas through the lens of various philosophical traditions.
        """)
        
        # Horizontal line to separate description from simulation controls
        st.markdown("---")
        
        # Simulation configuration
        st.header("Create a Philosophical Dialogue")
        
        # Create two columns for the configuration
        col1, col2 = st.columns(2)
        
        with col1:
            # Number of turns
            num_turns = st.slider("Number of Turns", 1, 10, 3, help="Number of dialogue exchanges to simulate")
            
            # Topic selection mode
            topic_mode = st.radio(
                "Topic Selection",
                ["Single Topic", "Multiple Topics"],
                help="Choose a single topic for all turns or different topics for each turn",
                key="home_topic_mode_radio"
            )
            
            # Visualization option
            visualize = st.checkbox("Generate Visualizations", True, 
                                   help="Create visual representations of the dialogue",
                                   key="home_visualize_checkbox")
            
        with col2:
            # Topic input
            if topic_mode == "Single Topic":
                topic_help = "Enter a philosophical topic for the dialogue"
                topics = st.text_input("Philosophical Topic", 
                                     "The impact of technology on human consciousness", 
                                     help=topic_help,
                                     key="home_single_topic_input")
                single_topic = True
            else:
                topic_help = "Enter one topic per line (one for each turn)"
                topics = st.text_area("Philosophical Topics", 
                                    "The impact of technology on human consciousness\nThe nature of freedom in modern society\nThe relationship between ethics and politics", 
                                    help=topic_help,
                                    key="home_multiple_topics_input")
                single_topic = False
        
        # Participants selection area (always visible)
        st.subheader("Select Participants")
        
        # Get all available NPCs
        all_npcs = npcs + st.session_state.custom_npcs
        
        npc_options = []
        for npc in all_npcs:
            npc_id = npc.get("id")
            npc_name = npc.get("name")
            npc_role = npc.get("role")
            npc_options.append((npc_id, f"{npc_name} ({npc_role})"))
        
        # Display multiselect for NPCs (max 4)
        selected_npc_ids = st.multiselect(
            "Select Participants (max 4)",
            options=[npc_id for npc_id, _ in npc_options],
            format_func=lambda npc_id: next((name for id, name in npc_options if id == npc_id), npc_id),
            default=[npc_options[0][0], npc_options[1][0]] if len(npc_options) >= 2 else [],
            max_selections=4,
            key="home_participants_select"
        )
        
        # Source materials selection area (always visible)
        st.subheader("Select Source Materials")
        
        # Get all available sources
        all_sources = st.session_state.simulation.source_loader.get_all_sources()
        
        source_options = []
        for source in all_sources:
            source_id = source.get("id")
            source_title = source.get("source")
            source_author = source.get("author", "Unknown")
            source_options.append((source_id, f"{source_title} ({source_author})"))
        
        # Display multiselect for sources
        selected_source_ids = st.multiselect(
            "Select Source Materials",
            options=[source_id for source_id, _ in source_options],
            format_func=lambda source_id: next((name for id, name in source_options if id == source_id), source_id),
            default=[],
            max_selections=5,
            key="home_sources_select"
        )
        
        # User context selection area
        if st.session_state.user_contexts:
            st.subheader("Select User Contexts")
            
            # Get user contexts
            contexts = st.session_state.simulation.get_all_contexts()
            
            context_options = []
            for ctx in contexts:
                context_id = ctx.get("id")
                context_title = ctx.get("title")
                context_type = ctx.get("type")
                context_options.append((context_id, f"{context_title} ({context_type})"))
            
            # Display multiselect for user contexts
            selected_context_ids = st.multiselect(
                "Select User Contexts",
                options=[ctx_id for ctx_id, _ in context_options],
                format_func=lambda ctx_id: next((name for id, name in context_options if id == ctx_id), ctx_id),
                default=[],
                max_selections=5,
                key="home_contexts_select"
            )
            
            # Update active contexts in the simulation
            if selected_context_ids:
                st.session_state.simulation.set_active_contexts(selected_context_ids)
            
        # Start simulation button
        if st.button("Start Simulation", key="start_simulation"):
            # Run the simulation with the selected parameters
            results = start_simulation(
                num_turns=num_turns,
                topics=topics,
                visualize=visualize,
                single_topic=single_topic,
                selected_npcs=selected_npc_ids,
                selected_sources=selected_source_ids
            )
            
            if results:
                st.session_state.simulation_results = results
                
                # Switch to results tab
                st.session_state.active_tab = "Results"
                st.rerun()
    
    # Results tab
    with tab_results:
        if active_tab_index == 1:  # Only update if this tab is active
            st.session_state.active_tab = "Results"
        # Display results if available
        if st.session_state.simulation_results:
            display_results(st.session_state.simulation_results)
        else:
            st.info("Run a simulation to see results here!")
    
    # Settings tab
    with tab_settings:
        if active_tab_index == 2:  # Only update if this tab is active
            st.session_state.active_tab = "Settings"
        st.header("Settings")
        
        # Only show Model Selection in Settings tab
        st.subheader("LLM Model Selection")
        
        # Model type selection
        model_type = st.radio(
            "Select LLM Provider",
            ["OpenAI API", "Local Model"],
            index=0 if st.session_state.llm_type == "openai" else 1,
            help="Choose between using OpenAI's API or a locally hosted model",
            key="settings_model_type_radio"
        )
        
        # Update session state based on selection
        st.session_state.llm_type = "openai" if model_type == "OpenAI API" else "local"
        
        # OpenAI settings
        if model_type == "OpenAI API":
            st.info("Using OpenAI's API for dialogue generation.")
            
            # Get API key from .env
            from dotenv import dotenv_values
            env_values = dotenv_values()
            api_key = env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            
            # Show masked API key if available
            if api_key:
                masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
                st.success(f"OpenAI API Key is configured: {masked_key}")
            else:
                st.error("OpenAI API Key is not configured. Add OPENAI_API_KEY to .env file.")
            
            # Model selection
            model_options = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
            selected_model = st.selectbox("Select OpenAI Model", 
                                         model_options, 
                                         key="settings_openai_model_select")
            
            # Save model selection to config (this would need a method to update the config)
            st.info(f"Selected model: {selected_model}")
            
        # Local model settings
        else:
            st.info("Using a locally hosted model for dialogue generation.")
            
            # Model path
            model_path = st.text_input(
                "Model Path", 
                value=st.session_state.local_model_path,
                help="Path to the model file or directory",
                key="settings_model_path_input"
            )
            st.session_state.local_model_path = model_path
            
            # Model type selection
            model_type_options = ["auto", "llama.cpp", "transformers"]
            selected_model_type = st.selectbox(
                "Model Type",
                model_type_options,
                index=model_type_options.index(st.session_state.local_model_type),
                help="The model loading method to use",
                key="settings_model_type_select"
            )
            st.session_state.local_model_type = selected_model_type
            
            # Device selection
            import torch
            device_options = ["auto"]
            if torch.cuda.is_available():
                device_options.append("cuda")
                cuda_devices = [f"cuda:{i}" for i in range(torch.cuda.device_count())]
                device_options.extend(cuda_devices)
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device_options.append("mps")
            device_options.append("cpu")
            
            selected_device = st.selectbox(
                "Computation Device",
                device_options,
                index=device_options.index(st.session_state.device) if st.session_state.device in device_options else 0,
                help="The device to run the model on",
                key="settings_device_select"
            )
            st.session_state.device = selected_device
            
            # Test local model button
            if st.button("Test Local Model"):
                with st.spinner("Testing local model..."):
                    try:
                        # Try to initialize the LocalLLM and generate a test response
                        from sapiens_engine.utils.local_llm import LocalLLM
                        llm = LocalLLM(
                            model_path=model_path,
                            model_type=selected_model_type,
                            device=selected_device,
                            quantize=True
                        )
                        
                        test_prompt = "What is the meaning of life?"
                        max_tokens = 50
                        
                        # Generate a short test response
                        start_time = time.time()
                        test_response = llm.generate_text(
                            prompt=test_prompt,
                            max_tokens=max_tokens,
                            temperature=0.7
                        )
                        end_time = time.time()
                        
                        # Show the results
                        st.success(f"Model loaded successfully! Generation time: {end_time - start_time:.2f} seconds")
                        st.markdown("**Test prompt:** " + test_prompt)
                        st.markdown("**Response:** " + test_response)
                        
                    except Exception as e:
                        st.error(f"Error testing local model: {str(e)}")
        
        # Save model settings button
        if st.button("Apply Model Settings"):
            # Initialize simulation with the selected model
            result = initialize_simulation_with_model()
            if result:
                st.success("Model settings applied successfully!")
            else:
                st.error("Failed to apply model settings. Check the errors above.")
    
    # Interactive tab
    with tab_interactive:
        if active_tab_index == 3:  # Only update if this tab is active
            st.session_state.active_tab = "Interactive"
        
        # Now add the actual interactive UI code
        st.title("Interactive Philosophical Dialogue")
        
        # Initialize interactive dialogue session state variables if needed
        if "interactive_dialogue" not in st.session_state:
            st.session_state.interactive_dialogue = []
        
        if "paused" not in st.session_state:
            st.session_state.paused = False
        
        if "active_npcs" not in st.session_state:
            # Select 2 default NPCs to participate in the dialogue
            all_npcs = npcs + st.session_state.custom_npcs
            if len(all_npcs) >= 2:
                st.session_state.active_npcs = [all_npcs[0].get("id"), all_npcs[1].get("id")]
            else:
                st.session_state.active_npcs = [npc.get("id") for npc in all_npcs]
        
        if "current_topic" not in st.session_state:
            st.session_state.current_topic = "The impact of technology on human consciousness"
        
        if "responding_npcs" not in st.session_state:
            st.session_state.responding_npcs = []
        
        # Set up UI for interactive dialogue
        st.subheader("Real-time Philosophical Dialogue")
        
        # Configuration area
        with st.expander("Dialogue Configuration", expanded=len(st.session_state.interactive_dialogue) == 0):
            # Topic selection
            st.session_state.current_topic = st.text_input(
                "Dialogue Topic",
                value=st.session_state.current_topic,
                help="The philosophical topic for discussion",
                key="interactive_topic_input"
            )
            
            # NPC selection
            all_npcs = npcs + st.session_state.custom_npcs
            
            npc_options = []
            for npc in all_npcs:
                npc_id = npc.get("id")
                npc_name = npc.get("name")
                npc_role = npc.get("role")
                npc_options.append((npc_id, f"{npc_name} ({npc_role})"))
            
            # Display multiselect for NPCs (max 4) in Interactive tab
            st.session_state.active_npcs = st.multiselect(
                "Select Participants (max 4)",
                options=[npc_id for npc_id, _ in npc_options],
                format_func=lambda npc_id: next((name for id, name in npc_options if id == npc_id), npc_id),
                default=st.session_state.active_npcs,
                max_selections=4,
                key="interactive_participants_select"
            )
            
            # Add context selection section
            st.subheader("Add Context for Dialogue")
            
            # Get user contexts from simulation
            contexts = st.session_state.simulation.get_all_contexts()
            
            if contexts:
                # Create options for existing contexts
                context_options = []
                for ctx in contexts:
                    context_id = ctx.get("id")
                    context_title = ctx.get("title")
                    context_type = ctx.get("type")
                    context_options.append((context_id, f"{context_title} ({context_type})"))
                
                # Display multiselect for contexts
                selected_context_ids = st.multiselect(
                    "Select Existing Contexts",
                    options=[ctx_id for ctx_id, _ in context_options],
                    format_func=lambda ctx_id: next((name for id, name in context_options if id == ctx_id), ctx_id),
                    default=[],
                    key="interactive_contexts_select"
                )
                
                # Apply selected contexts to the simulation
                if selected_context_ids:
                    st.session_state.simulation.set_active_contexts(selected_context_ids)
            else:
                st.info("No contexts available. Add some context below or in the User Contexts tab.")
            
            # Add quick context input
            st.subheader("Quick Add Context")
            
            quick_context_title = st.text_input("Context Title", "Quick Context", key="interactive_quick_context_title")
            quick_context_content = st.text_area("Context Content", "", key="interactive_quick_context_content")
            
            if st.button("Add This Context", key="interactive_add_context_btn"):
                if quick_context_content:
                    # Add context to simulation
                    context_id = st.session_state.simulation.add_context_from_text(
                        quick_context_content, 
                        quick_context_title
                    )
                    
                    # Set this context as active
                    st.session_state.simulation.set_active_contexts([context_id])
                    
                    # Update session state and clear fields
                    st.session_state.user_contexts = st.session_state.simulation.get_all_contexts()
                    st.success(f"Added context: {quick_context_title}")
                    
                    # Clear the input fields
                    st.session_state["interactive_quick_context_title"] = "Quick Context"
                    st.session_state["interactive_quick_context_content"] = ""
                    
                    st.rerun()
                else:
                    st.warning("Please enter content for the context")
            
            # Button to start/reset dialogue
            if st.button("Start New Dialogue"):
                st.session_state.interactive_dialogue = []
                st.session_state.paused = False
                st.session_state.responding_npcs = []
                
                # Initialize the dialogue with the first NPC response
                if st.session_state.active_npcs:
                    # Get a random NPC to start
                    first_npc_id = random.choice(st.session_state.active_npcs)
                    
                    # Find the NPC in the list
                    first_npc = None
                    for npc in all_npcs:
                        if npc.get("id") == first_npc_id:
                            first_npc = npc
                            break
                    
                    if first_npc:
                        # Add the first exchange
                        simulation = st.session_state.simulation
                        
                        # Generate response for the first NPC
                        npc_obj = simulation.npcs.get(first_npc_id)
                        if npc_obj:
                            first_response = simulation.llm_manager.generate_single_response(
                                npc=npc_obj,
                                topic=st.session_state.current_topic,
                                dialogue_history=[],
                                is_first=True
                            )
                            
                            st.session_state.interactive_dialogue.append({
                                "speaker": npc_obj.name,
                                "content": first_response,
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            })
                            
                            # Remove this NPC from the responding list to avoid duplication
                            if first_npc_id in st.session_state.responding_npcs:
                                st.session_state.responding_npcs.remove(first_npc_id)
                            
                            # Mark all other NPCs as needing to respond
                            for npc_id in st.session_state.active_npcs:
                                if npc_id != first_npc_id and npc_id not in st.session_state.responding_npcs:
                                    st.session_state.responding_npcs.append(npc_id)
                
                st.rerun()
        
        # Create a 2-column layout with fixed heights
        # Left column for dialogue history, right column stays empty for better aesthetics
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # Display the dialogue - create a container with fixed height for scrollable content
            st.subheader(f"Topic: {st.session_state.current_topic}")
            
            # Display the dialogue history with speech bubble style
            if not st.session_state.interactive_dialogue:
                st.info("Start a dialogue by configuring settings above and clicking 'Start New Dialogue', or enter your own message to begin.")
            else:
                # Custom CSS for speech bubbles and fixed container
                st.markdown("""
                <style>
                .user-bubble {
                    background-color: #e6f7ff;
                    border-radius: 18px;
                    padding: 10px 15px;
                    margin: 10px 0;
                    max-width: 80%;
                    margin-left: auto;
                    position: relative;
                }
                .npc-bubble {
                    background-color: #f1f1f1;
                    border-radius: 18px;
                    padding: 10px 15px;
                    margin: 10px 0;
                    max-width: 80%;
                    margin-right: auto;
                    position: relative;
                }
                .bubble-container {
                    display: flex;
                    flex-direction: column;
                    height: 500px;
                    overflow-y: auto;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    background-color: white;
                }
                .bubble-header {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .timestamp {
                    font-size: 0.8em;
                    color: #666;
                    margin-left: 5px;
                }
                .input-container {
                    position: sticky;
                    bottom: 0;
                    background-color: white;
                    padding: 10px 0;
                    border-top: 1px solid #ddd;
                    margin-top: 15px;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Create a container for dialogue with fixed height and scrolling
                st.markdown('<div class="bubble-container">', unsafe_allow_html=True)
                
                for exchange in st.session_state.interactive_dialogue:
                    speaker = exchange["speaker"]
                    content = exchange["content"]
                    timestamp = exchange.get("timestamp", "")
                    
                    if speaker == "User":
                        st.markdown(f"""
                        <div class="user-bubble">
                            <div class="bubble-header">You <span class="timestamp">{timestamp}</span></div>
                            {content}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="npc-bubble">
                            <div class="bubble-header">{speaker} <span class="timestamp">{timestamp}</span></div>
                            {content}
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Create a fixed container at the bottom for user input
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        # User input and pause/resume button side by side
        input_cols = st.columns([3, 1])
        
        with input_cols[0]:
            user_input = st.text_area("Your response:", height=80, key="user_input_area")
            
        with input_cols[1]:
            pause_label = "Pause" if not st.session_state.paused else "Resume"
            pause_button = st.button(pause_label, key="pause_button")
            send_button = st.button("Send", key="send_button", disabled=not user_input)
        
        st.markdown('</div>', unsafe_allow_html=True)
            
        # Handle pause/resume button
        if pause_button:
            st.session_state.paused = not st.session_state.paused
            st.rerun()
            
        # Handle send button
        if send_button and user_input:
            # Add user message to dialogue
            st.session_state.interactive_dialogue.append({
                "speaker": "User",
                "content": user_input,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # Unpause the dialogue if it was paused
            st.session_state.paused = False
            
            # Reset the list of responding NPCs so all NPCs respond to the user's input
            st.session_state.responding_npcs = list(st.session_state.active_npcs)
            
            # Rerun to update UI
            st.rerun()
        
        # Auto-generate NPC responses if not paused (keep outside of the visual layout)
        if not st.session_state.paused and st.session_state.interactive_dialogue:
            simulation = st.session_state.simulation
            
            # Format previous dialogue for context (for the NPC)
            dialogue_context = []
            for exchange in st.session_state.interactive_dialogue[-10:]:  # Get recent context
                dialogue_context.append({
                    "speaker": exchange["speaker"], 
                    "content": exchange["content"]
                })
            
            # Generate responses from NPCs if any need to respond
            if st.session_state.responding_npcs:
                # Get the next NPC to respond
                next_npc_id = st.session_state.responding_npcs[0]
                
                # Generate response
                npc_obj = simulation.npcs.get(next_npc_id)
                if npc_obj:
                    # Generate response based on dialogue history
                    npc_response = simulation.llm_manager.generate_single_response(
                        npc=npc_obj,
                        topic=st.session_state.current_topic,
                        dialogue_history=dialogue_context,
                        is_first=False
                    )
                    
                    # Add response to dialogue
                    st.session_state.interactive_dialogue.append({
                        "speaker": npc_obj.name,
                        "content": npc_response,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    # Remove this NPC from the responding list
                    st.session_state.responding_npcs.remove(next_npc_id)
                    
                    # Wait a short time before adding the next response
                    time.sleep(0.5)
                    
                    # Rerun to update UI
                    st.rerun()
            
            # If no NPCs are currently responding, check if we need to start a new round
            # This ensures continuous dialogue between NPCs
            elif len(st.session_state.active_npcs) > 1:  # Only do this if we have multiple NPCs
                # Get the last speaker
                last_speaker = st.session_state.interactive_dialogue[-1]["speaker"]
                last_speaker_is_npc = last_speaker != "User"
                
                # If the last message was from an NPC (not the user) and we have more than one NPC,
                # then randomly select another NPC to continue the conversation
                if last_speaker_is_npc and len(st.session_state.active_npcs) > 1:
                    # Find which NPC ID corresponds to the last speaker
                    last_npc_id = None
                    for npc_id, npc in simulation.npcs.items():
                        if npc.name == last_speaker:
                            last_npc_id = npc_id
                            break
                    
                    # If found, select a different NPC to respond
                    if last_npc_id is not None:
                        # Filter active NPCs to exclude the last speaker
                        available_npcs = [npc_id for npc_id in st.session_state.active_npcs if npc_id != last_npc_id]
                        
                        if available_npcs:
                            # Randomly select one NPC to respond
                            next_npc_id = random.choice(available_npcs)
                            st.session_state.responding_npcs.append(next_npc_id)
                            
                            # Rerun to trigger the response generation
                            st.rerun()
    
    # User Contexts tab (new)
    with tab_user_contexts:
        if active_tab_index == 4:  # Only update if this tab is active
            st.session_state.active_tab = "User Contexts"
        add_user_context()
    
    # Custom NPCs tab (new)
    with tab_custom_npcs:
        if active_tab_index == 5:  # Only update if this tab is active
            st.session_state.active_tab = "Custom NPCs"
        add_custom_npc()

    # Add dialogue export function
    if st.session_state.interactive_dialogue:
        # Create a button to export the dialogue as a paper/essay
        st.markdown("---")
        st.subheader("Generate Paper from Dialogue")
        
        paper_format = st.selectbox(
            "Paper Format",
            ["Academic Essay", "Research Paper", "Philosophical Analysis", "Summary Report"],
            key="paper_format_select"
        )
        
        paper_length = st.select_slider(
            "Paper Length",
            options=["Short", "Medium", "Comprehensive"],
            value="Medium",
            key="paper_length_select"
        )
        
        if st.button("Generate Paper", key="generate_paper_btn"):
            with st.spinner("Generating philosophical paper from dialogue..."):
                # Get the dialogue content
                simulation = st.session_state.simulation
                dialogue_text = "\n\n".join([f"{exchange['speaker']}: {exchange['content']}" for exchange in st.session_state.interactive_dialogue])
                
                # Create prompt for generating a philosophical paper
                paper_prompt = f"""
                Generate a philosophical {paper_format} based on the following dialogue on the topic of "{st.session_state.current_topic}".
                The paper should provide a {paper_length.lower()}-length analysis of the key philosophical arguments, points of agreement and disagreement, and overall conclusions.
                
                DIALOGUE:
                {dialogue_text}
                
                The paper should:
                1. Have a clear introduction setting out the philosophical problem
                2. Analyze the main arguments presented in the dialogue
                3. Identify any consensus or synthesis that emerged
                4. Include proper citations to relevant philosophers mentioned
                5. End with a conclusion that summarizes the philosophical significance
                
                Please format as a proper {paper_format} with sections and paragraphs.
                """
                
                # Generate the paper using the LLM
                try:
                    # Use the simulation's LLM manager to generate the paper
                    system_prompt = """You are a renowned philosophy professor tasked with converting philosophical dialogues into formal papers.
                    Your job is to analyze the dialogue, extract key arguments, and format them into a cohesive academic paper.
                    Structure should include introduction, main sections with analysis, and conclusion.
                    Cite relevant philosophers mentioned in or related to the dialogue content.
                    Use academic language but maintain readability."""
                    
                    paper_result = simulation.llm_manager.generate_response(system_prompt, paper_prompt)
                    
                    # Create a file name based on the topic and timestamp
                    sanitized_topic = re.sub(r'[^\w\s-]', '', st.session_state.current_topic).strip().replace(' ', '_')
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_name = f"{sanitized_topic}_{timestamp}"
                    
                    # Store the paper to a file for download
                    paper_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'papers')
                    os.makedirs(paper_dir, exist_ok=True)
                    paper_path = os.path.join(paper_dir, f"{file_name}.md")
                    
                    with open(paper_path, 'w', encoding='utf-8') as f:
                        f.write(f"# {st.session_state.current_topic}\n\n")
                        f.write(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                        f.write(paper_result)
                        
                        # Add the dialogue at the end as an appendix
                        f.write("\n\n## Appendix: Original Dialogue\n\n")
                        for exchange in st.session_state.interactive_dialogue:
                            f.write(f"**{exchange['speaker']}**: {exchange['content']}\n\n")
                    
                    # Display the result
                    st.subheader(f"Generated {paper_format}")
                    st.markdown(paper_result)
                    
                    # Add download button
                    with open(paper_path, 'r', encoding='utf-8') as f:
                        paper_content = f.read()
                        
                    st.download_button(
                        label="Download Paper as Markdown",
                        data=paper_content,
                        file_name=f"{file_name}.md",
                        mime="text/markdown",
                        key="download_paper_btn"
                    )
                    
                    # Generate PDF version option (placeholder)
                    st.info("PDF generation functionality could be added in the future.")
                    
                except Exception as e:
                    st.error(f"Error generating paper: {str(e)}")

# Entry point for the app
if __name__ == "__main__":
    # Ensure model directory exists
    model_dir = ensure_model_directory_exists()
    
    # Set default local model path if not already set
    if "local_model_path" not in st.session_state:
        st.session_state.local_model_path = model_dir
    
    # Run the main Streamlit app
    main() 