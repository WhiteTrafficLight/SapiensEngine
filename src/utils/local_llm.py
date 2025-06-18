"""
Local LLM module for Sapiens Engine.

This module provides utilities for loading and running local LLMs
using either llama.cpp or HuggingFace Transformers.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Union, Any
import time

# Conditionally import libraries for model loading
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

try:
    import torch
    from transformers import (
        AutoModelForCausalLM, 
        AutoTokenizer, 
        pipeline, 
        TextIteratorStreamer,
        BitsAndBytesConfig
    )
    from threading import Thread
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

logger = logging.getLogger(__name__)

class LocalLLM:
    """
    A class for loading and running local language models.
    
    Supports both llama.cpp and HuggingFace Transformers models.
    """
    
    def __init__(self, 
                 model_path: str, 
                 model_type: str = "auto",
                 model_config: Optional[Dict[str, Any]] = None,
                 device: str = "auto",
                 quantize: bool = True):
        """
        Initialize the LocalLLM.
        
        Args:
            model_path: Path to the model file or directory.
            model_type: Type of model ("llama.cpp", "transformers", or "auto").
            model_config: Additional configuration options for the model.
            device: Device to run on ("cpu", "cuda", "mps", or "auto").
            quantize: Whether to quantize the model to reduce memory usage.
        """
        self.model_path = model_path
        self.model_type = model_type
        self.model_config = model_config or {}
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # Determine the device
        if device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device
            
        # Determine the model type if auto
        if model_type == "auto":
            if model_path.endswith((".bin", ".gguf")):
                self.model_type = "llama.cpp"
            else:
                self.model_type = "transformers"
        
        # Set up quantization
        self.quantize = quantize
        
        # Load the model
        self._load_model()
        
    def _load_model(self):
        """Load the model based on the specified type."""
        if self.model_type == "llama.cpp":
            self._load_llama_cpp_model()
        elif self.model_type == "transformers":
            self._load_transformers_model()
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
            
    def _load_llama_cpp_model(self):
        """Load a model using llama.cpp."""
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama_cpp not installed. Install with 'pip install llama-cpp-python'")
            
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
        # Extract parameters from model_config
        n_ctx = self.model_config.get("context_length", 2048)
        n_gpu_layers = self.model_config.get("n_gpu_layers", -1)
        
        # Use verbose=True during development to see loading progress
        logger.info(f"Loading llama.cpp model from {self.model_path}...")
        self.model = Llama(
            model_path=self.model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        logger.info(f"Loaded llama.cpp model, context length: {n_ctx}")
            
    def _load_transformers_model(self):
        """Load a model using HuggingFace Transformers."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not installed. Install with 'pip install transformers accelerate'")
            
        # Extract parameters from model_config
        load_in_8bit = self.quantize and self.model_config.get("load_in_8bit", False)
        load_in_4bit = self.quantize and self.model_config.get("load_in_4bit", True)
        
        logger.info(f"Loading Transformers model from {self.model_path}...")
        
        # Set up quantization config
        if self.quantize and self.device != "cpu":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=load_in_4bit,
                load_in_8bit=load_in_8bit,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        else:
            quantization_config = None
        
        # Load the model
        try:
            start_time = time.time()
            
            # First load the tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, 
                use_fast=True
            )
            
            # Then load the model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map=self.device if self.device != "mps" else "cpu",  # MPS uses special handling
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                quantization_config=quantization_config,
                **self.model_config.get("model_kwargs", {})
            )
            
            # For MPS we manually move the model
            if self.device == "mps":
                self.model = self.model.to("mps")
            
            # Create text generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else self.device,
                **self.model_config.get("pipeline_kwargs", {})
            )
            
            load_time = time.time() - start_time
            logger.info(f"Loaded Transformers model in {load_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error loading Transformers model: {str(e)}")
            raise
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 512,
                     temperature: float = 0.7,
                     top_p: float = 0.9,
                     top_k: int = 40,
                     stop_sequences: List[str] = None,
                     stream: bool = False) -> Union[str, List[str]]:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The input prompt.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            top_k: Top-k sampling parameter.
            stop_sequences: List of strings to stop generation when encountered.
            stream: Whether to stream the output.
            
        Returns:
            Generated text or a list of tokens if streaming.
        """
        stop_sequences = stop_sequences or []
        
        if self.model_type == "llama.cpp":
            return self._generate_llama_cpp(
                prompt, max_tokens, temperature, top_p, top_k, stop_sequences, stream
            )
        else:
            return self._generate_transformers(
                prompt, max_tokens, temperature, top_p, top_k, stop_sequences, stream
            )
    
    def _generate_llama_cpp(self, 
                           prompt: str, 
                           max_tokens: int,
                           temperature: float,
                           top_p: float,
                           top_k: int,
                           stop_sequences: List[str],
                           stream: bool) -> Union[str, List[str]]:
        """Generate text using llama.cpp."""
        if not self.model:
            raise ValueError("Model not loaded")
            
        # Handle streaming
        if stream:
            # Basic implementation, for advanced needs, override this method
            return self.model.create_completion(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                stop=stop_sequences,
                stream=True
            )
        
        # Regular completion
        completion = self.model.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop_sequences,
            stream=False
        )
        
        # Extract the generated text
        if "choices" in completion and len(completion["choices"]) > 0:
            return completion["choices"][0]["text"]
        return ""
    
    def _generate_transformers(self, 
                              prompt: str, 
                              max_tokens: int,
                              temperature: float,
                              top_p: float,
                              top_k: int,
                              stop_sequences: List[str],
                              stream: bool) -> Union[str, List[str]]:
        """Generate text using HuggingFace Transformers."""
        if not self.pipeline:
            raise ValueError("Model pipeline not created")
            
        # Handle streaming
        if stream:
            # Create a streamer
            streamer = TextIteratorStreamer(self.tokenizer)
            
            # Define generation parameters
            gen_kwargs = {
                "input_ids": self.tokenizer.encode(prompt, return_tensors="pt").to(self.device),
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "streamer": streamer,
                "do_sample": temperature > 0,
            }
            
            # Start generation in a separate thread
            thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
            thread.start()
            
            # Return the streamer
            return streamer
        
        # Regular generation
        try:
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=temperature > 0,
                return_full_text=False,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            
            # Check if we need to apply stop sequences
            result = outputs[0]["generated_text"]
            
            # Apply stop sequences manually
            if stop_sequences:
                for stop_seq in stop_sequences:
                    stop_idx = result.find(stop_seq)
                    if stop_idx >= 0:
                        result = result[:stop_idx]
                        
            return result
            
        except Exception as e:
            logger.error(f"Error generating text with Transformers: {str(e)}")
            return ""
            
    def check_availability(self) -> Dict[str, Any]:
        """
        Check the availability and capabilities of the model.
        
        Returns:
            Dict with model information.
        """
        info = {
            "model_type": self.model_type,
            "model_path": self.model_path,
            "device": self.device,
            "loaded": self.model is not None,
            "quantized": self.quantize,
            "error": None,
        }
        
        try:
            # Try a simple generation to verify the model works
            if self.model:
                _ = self.generate_text("Hello, world!", max_tokens=5)
                info["functional"] = True
        except Exception as e:
            info["functional"] = False
            info["error"] = str(e)
            
        return info
        
    def get_context_length(self) -> int:
        """
        Get the maximum context length of the model.
        
        Returns:
            Maximum context length in tokens.
        """
        if self.model_type == "llama.cpp":
            return self.model.n_ctx()
        elif self.model_type == "transformers" and self.model:
            config = self.model.config
            # Check various attributes commonly used for context length
            for attr in ["max_position_embeddings", "n_positions", "max_seq_len", "n_ctx"]:
                if hasattr(config, attr):
                    return getattr(config, attr)
            # Default fallback
            return 2048
        return 0 
 