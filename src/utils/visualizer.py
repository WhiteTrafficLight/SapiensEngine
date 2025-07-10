"""
Visualization utilities for the Sapiens Engine.
"""

# 조건부 임포트 - numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    import logging
    logging.warning("numpy not available. Advanced numerical operations disabled.")

# 조건부 임포트 - pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    import logging
    logging.warning("pandas not available. Data analysis features disabled.")

import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

class Visualizer:
    """
    Visualization class for Sapiens Engine data and results.
    """
    
    def __init__(self):
        """Initialize the visualizer."""
        self.setup_matplotlib()
    
    def setup_matplotlib(self):
        """Setup matplotlib with appropriate settings."""
        try:
            plt.style.use('seaborn-v0_8')
        except OSError:
            try:
                plt.style.use('seaborn')
            except OSError:
                # Fallback to default style
                pass
    
    def plot_data(self, data, title="Data Visualization", **kwargs):
        """
        Plot data with fallback options.
        
        Args:
            data: Data to plot (supports various formats)
            title: Plot title
            **kwargs: Additional plotting arguments
        """
        if not PANDAS_AVAILABLE and not NUMPY_AVAILABLE:
            logger.warning("Neither pandas nor numpy available. Cannot plot data.")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=kwargs.get('figsize', (10, 6)))
            
            # Handle different data types
            if PANDAS_AVAILABLE and isinstance(data, pd.DataFrame):
                data.plot(ax=ax, **kwargs)
            elif PANDAS_AVAILABLE and isinstance(data, pd.Series):
                data.plot(ax=ax, **kwargs)
            elif NUMPY_AVAILABLE and isinstance(data, np.ndarray):
                ax.plot(data, **kwargs)
            elif isinstance(data, (list, tuple)):
                ax.plot(data, **kwargs)
            else:
                logger.warning(f"Unsupported data type: {type(data)}")
                return None
            
            ax.set_title(title)
            ax.grid(True)
            plt.tight_layout()
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating plot: {str(e)}")
            return None

    def create_dataframe_fallback(self, data):
        """Create a DataFrame-like structure when pandas is not available."""
        if PANDAS_AVAILABLE:
            return pd.DataFrame(data)
        else:
            logger.warning("pandas not available. Returning raw data.")
            return data

import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

class PhilosophicalVisualizer:
    """
    Visualization utilities for philosophical simulation results
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the visualizer
        
        Args:
            output_dir: Directory where visualization outputs will be saved
        """
        self.output_dir = output_dir
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
    def visualize_philosophical_trends(self, trends_data: List[Dict[str, Any]], 
                                       save_path: Optional[str] = None):
        """
        Visualize how philosophical trends change over time
        
        Args:
            trends_data: List of trend data points, each containing 'turn' and 'trends'
            save_path: Optional path to save the visualization
        """
        if not trends_data:
            print("No trend data to visualize")
            return
            
        # Extract data for plotting
        turns = [data["turn"] for data in trends_data]
        trend_names = list(trends_data[0]["trends"].keys())
        
        # Create a DataFrame for easier plotting
        df = pd.DataFrame(index=turns)
        
        for trend in trend_names:
            df[trend] = [data["trends"][trend] for data in trends_data]
            
        # Create the plot
        plt.figure(figsize=(12, 6))
        for trend in trend_names:
            plt.plot(df.index, df[trend], marker='o', linewidth=2, label=trend)
            
        plt.title("Evolution of Philosophical Trends", fontsize=14)
        plt.xlabel("Simulation Turn", fontsize=12)
        plt.ylabel("Trend Strength", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=10)
        plt.ylim(0, 1)
        plt.xticks(turns)
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Trends visualization saved to {save_path}")
        else:
            plt.show()
            
        plt.close()
        
    def visualize_npc_dialogue_stats(self, npc_states: Dict[str, Dict[str, Any]],
                                    save_path: Optional[str] = None):
        """
        Visualize NPC dialogue statistics
        
        Args:
            npc_states: Dictionary mapping NPC IDs to their state
            save_path: Optional path to save the visualization
        """
        if not npc_states:
            print("No NPC data to visualize")
            return
            
        # Extract data for plotting
        npc_names = []
        trait_data = {}
        
        for npc_id, npc_state in npc_states.items():
            npc_names.append(npc_state.get("name", npc_id))
            
            for trait, value in npc_state.get("personality_traits", {}).items():
                if trait not in trait_data:
                    trait_data[trait] = []
                trait_data[trait].append(value)
                
        # Select a subset of traits to visualize (to avoid overcrowding)
        selected_traits = [
            "conformity", "critical_thinking", "creativity", 
            "dogmatism", "openness", "rationality"
        ]
        
        # Filter to only include selected traits that exist in the data
        selected_traits = [t for t in selected_traits if t in trait_data]
        
        # Create a radar chart
        num_npcs = len(npc_names)
        num_traits = len(selected_traits)
        
        # Set up the angles for each trait
        angles = np.linspace(0, 2*np.pi, num_traits, endpoint=False).tolist()
        angles += angles[:1]  # close the loop
        
        # Set up the figure
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        
        # Add trait labels
        plt.xticks(angles[:-1], selected_traits, fontsize=12)
        
        # Draw the chart for each NPC
        for i, npc_name in enumerate(npc_names):
            values = [trait_data[trait][i] for trait in selected_traits]
            values += values[:1]  # close the loop
            
            ax.plot(angles, values, linewidth=2, label=npc_name)
            ax.fill(angles, values, alpha=0.1)
            
        plt.title("NPC Philosophical Traits Comparison", fontsize=15)
        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"NPC traits visualization saved to {save_path}")
        else:
            plt.show()
            
        plt.close()
        
    def create_dialogue_summary(self, dialogue_history: List[Dict[str, Any]], 
                               save_path: Optional[str] = None):
        """
        Create a text-based summary of dialogues
        
        Args:
            dialogue_history: List of dialogue exchanges
            save_path: Optional path to save the summary
        """
        if not dialogue_history:
            print("No dialogue history to summarize")
            return
            
        summary = []
        summary.append("# PHILOSOPHICAL DIALOGUE SUMMARY\n")
        
        for turn_data in dialogue_history:
            topic = turn_data.get("topic", "Unknown topic")
            turn = turn_data.get("turn", "?")
            npcs = turn_data.get("participating_npcs", [])
            
            summary.append(f"\n## Turn {turn}: {topic}")
            summary.append(f"Participants: {', '.join(npcs)}\n")
            
            for exchange in turn_data.get("exchanges", []):
                speaker = exchange.get("speaker", "Unknown")
                content = exchange.get("content", "")
                summary.append(f"**{speaker}**: {content}\n")
                
        # Join all parts
        summary_text = "\n".join(summary)
        
        # Save or return the summary
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            print(f"Dialogue summary saved to {save_path}")
            return save_path
        else:
            return summary_text
            
    def visualize_simulation_results(self, results: Dict[str, Any], 
                                    output_dir: Optional[str] = None):
        """
        Create a comprehensive visualization of simulation results
        
        Args:
            results: Simulation results
            output_dir: Directory to save visualizations
        """
        # Use provided output directory or default
        output_dir = output_dir or self.output_dir
        if not output_dir:
            print("No output directory specified")
            return
            
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract data from results
        trends_data = results.get("philosophical_trends", [])
        npc_states = results.get("npc_states", {})
        dialogue_history = results.get("dialogue_history", [])
        
        # Generate visualizations
        if trends_data:
            trends_path = os.path.join(output_dir, "philosophical_trends.png")
            self.visualize_philosophical_trends(trends_data, trends_path)
            
        if npc_states:
            npc_path = os.path.join(output_dir, "npc_traits.png")
            self.visualize_npc_dialogue_stats(npc_states, npc_path)
            
        if dialogue_history:
            summary_path = os.path.join(output_dir, "dialogue_summary.md")
            self.create_dialogue_summary(dialogue_history, summary_path)
            
        # Create a simple HTML report that links to all visualizations
        self._create_html_report(results, output_dir)
        
    def _create_html_report(self, results: Dict[str, Any], output_dir: str):
        """
        Create an HTML report summarizing the simulation results
        
        Args:
            results: Simulation results dictionary
            output_dir: Directory to save the report
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_turns = results.get("total_turns", 0)
        zeitgeist = results.get("final_zeitgeist", {})
        npc_states = results.get("npc_states", {})
        
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sapiens Engine - Simulation Results</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                h1, h2, h3 {{
                    color: #2c3e50;
                }}
                .container {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                }}
                .section {{
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .full-width {{
                    width: 100%;
                }}
                .half-width {{
                    width: 48%;
                }}
                .visualization {{
                    text-align: center;
                    margin: 20px 0;
                }}
                .visualization img {{
                    max-width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                .footer {{
                    margin-top: 30px;
                    text-align: center;
                    font-size: 0.8em;
                    color: #777;
                }}
            </style>
        </head>
        <body>
            <h1>Sapiens Engine - Philosophical Simulation Results</h1>
            <p>Report generated on {timestamp}</p>
            
            <div class="section full-width">
                <h2>Simulation Overview</h2>
                <table>
                    <tr>
                        <th>Total Turns</th>
                        <td>{total_turns}</td>
                    </tr>
                    <tr>
                        <th>Environment</th>
                        <td>{zeitgeist.get("name", "Unknown")}</td>
                    </tr>
                    <tr>
                        <th>Era</th>
                        <td>{zeitgeist.get("era", "Unknown")}</td>
                    </tr>
                    <tr>
                        <th>Historical Context</th>
                        <td>{zeitgeist.get("historical_context", "Unknown")}</td>
                    </tr>
                </table>
            </div>
            
            <div class="container">
                <div class="section half-width">
                    <h2>Participating NPCs</h2>
                    <table>
                        <tr>
                            <th>Name</th>
                            <th>Role</th>
                        </tr>
        """
        
        # Add NPC data
        for npc_id, npc in npc_states.items():
            html_content += f"""
                <tr>
                    <td>{npc.get("name", npc_id)}</td>
                    <td>{npc.get("role", "Unknown")}</td>
                </tr>
            """
            
        html_content += """
                    </table>
                </div>
                
                <div class="section half-width">
                    <h2>Dominant Ideologies</h2>
                    <ul>
        """
        
        # Add ideologies
        for ideology in zeitgeist.get("dominant_ideologies", []):
            html_content += f"<li>{ideology}</li>\n"
            
        html_content += """
                    </ul>
                    
                    <h3>Current Crises</h3>
                    <ul>
        """
        
        # Add crises
        for crisis in zeitgeist.get("current_crises", []):
            html_content += f"<li>{crisis}</li>\n"
            
        html_content += """
                    </ul>
                </div>
            </div>
            
            <div class="section full-width">
                <h2>Visualizations</h2>
                
                <div class="visualization">
                    <h3>Philosophical Trends</h3>
                    <img src="philosophical_trends.png" alt="Philosophical Trends Graph">
                </div>
                
                <div class="visualization">
                    <h3>NPC Traits Comparison</h3>
                    <img src="npc_traits.png" alt="NPC Traits Radar Chart">
                </div>
                
                <p>
                    <a href="dialogue_summary.md">View Detailed Dialogue Summary</a>
                </p>
            </div>
            
            <div class="footer">
                <p>Generated by Sapiens Engine - Philosophical Simulation</p>
            </div>
        </body>
        </html>
        """
        
        # Write HTML file
        html_path = os.path.join(output_dir, "report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"HTML report generated at {html_path}")
        
        return html_path 
 