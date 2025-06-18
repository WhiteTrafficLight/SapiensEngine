#!/usr/bin/env python
import os
import sys
import argparse
import time
from typing import Dict, Any, List, Optional

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sapiens_engine.core.config_loader import ConfigLoader
from sapiens_engine.core.source_loader import SourceLoader
from sapiens_engine.core.simulation import PhilosophicalSimulation
from sapiens_engine.utils.visualizer import PhilosophicalVisualizer
from sapiens_engine.utils.logger import SimulationLogger

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Sapiens Engine - Philosophical Simulation")
    
    parser.add_argument("--turns", type=int, default=None,
                       help="Number of simulation turns (default: from config)")
    parser.add_argument("--topic", type=str, action="append", dest="topics",
                       help="Philosophical topic for discussion (can specify multiple)")
    parser.add_argument("--output-dir", type=str, default="output",
                       help="Directory for saving results (default: 'output')")
    parser.add_argument("--config-dir", type=str, default=None,
                       help="Directory containing configuration files (default: from package)")
    parser.add_argument("--visualize", action="store_true",
                       help="Generate visualizations of results")
    parser.add_argument("--log-level", type=str, default="info",
                       choices=["debug", "info", "warning", "error", "critical"],
                       help="Logging level (default: info)")
    
    return parser.parse_args()

def main():
    """Main entry point for the Sapiens Engine"""
    args = parse_arguments()
    
    # Set up output directory
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up config loader
    config_loader = ConfigLoader(args.config_dir)
    
    # Initialize simulation components
    logger = SimulationLogger(output_dir, args.log_level)
    
    logger.info("Initializing Sapiens Engine - Philosophical Simulation")
    
    # Display loaded configuration
    try:
        config = config_loader.get_main_config()
        npcs = config_loader.get_all_npcs()
        logger.info(f"Loaded configuration with {len(npcs)} NPCs")
        logger.info(f"Simulation environment: {config.get('environment', {}).get('name', 'Default')}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return 1
    
    # Initialize and run the simulation
    try:
        simulation = PhilosophicalSimulation(config_loader)
        
        # Get topics from arguments or use None to let the simulation use defaults
        topics = args.topics if args.topics else None
        
        # Run the simulation
        logger.info("Starting philosophical simulation")
        start_time = time.time()
        
        results = simulation.run_simulation(args.turns, topics)
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Simulation completed in {duration:.2f} seconds")
        
        # Save results
        results_file = f"simulation_results.json"
        results_path = simulation.save_simulation_results(results, results_file)
        logger.info(f"Results saved to {results_path}")
        
        # Generate visualizations if requested
        if args.visualize:
            logger.info("Generating visualizations")
            visualizer = PhilosophicalVisualizer(os.path.join(output_dir, "visualizations"))
            visualizer.visualize_simulation_results(results)
            
        logger.info("Sapiens Engine execution completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error during simulation: {e}")
        logger.exception(e)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
 