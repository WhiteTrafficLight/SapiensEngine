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

# 조건부 임포트 - llama.cpp
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama.cpp not available. llama.cpp models disabled.")

# 조건부 임포트 - transformers & torch
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
    logging.warning("transformers/torch not available. HuggingFace models disabled.")

logger = logging.getLogger(__name__)

class LocalLLM:
    """
    A class for loading and running local language models.
    
    Supports both llama.cpp and HuggingFace Transformers models.
    """
    
    def __init__(
        self,
        model_path: str,
        model_type: str = "auto",  # "llama_cpp", "transformers", "auto"
        device: str = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Initialize the LocalLLM with the specified model.
        
        Args:
            model_path: Path to the model file or HuggingFace model name
            model_type: Type of model to load ("llama_cpp", "transformers", "auto")
            device: Device to run the model on ("cpu", "cuda", "auto")
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional arguments for model loading
        """
        self.model_path = model_path
        self.model_type = model_type
        self.device = device
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.kwargs = kwargs
        
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # Determine model type if auto
        if model_type == "auto":
            self.model_type = self._detect_model_type(model_path)
        
        # Load the model
        self._load_model()
    
    def _detect_model_type(self, model_path: str) -> str:
        """Auto-detect model type based on path and availability."""
        if model_path.endswith(('.gguf', '.ggml', '.bin')) and LLAMA_CPP_AVAILABLE:
            return "llama_cpp"
        elif TRANSFORMERS_AVAILABLE:
            return "transformers"
        elif LLAMA_CPP_AVAILABLE:
            return "llama_cpp"
        else:
            logger.error("No suitable model backend available")
            return "none"
    
    def _load_model(self):
        """Load the model based on the specified type."""
        if self.model_type == "llama_cpp" and LLAMA_CPP_AVAILABLE:
            self._load_llama_cpp()
        elif self.model_type == "transformers" and TRANSFORMERS_AVAILABLE:
            self._load_transformers()
        else:
            logger.error(f"Cannot load model: {self.model_type} backend not available")
            return
    
    def _load_llama_cpp(self):
        """Load model using llama.cpp."""
        if not LLAMA_CPP_AVAILABLE:
            logger.error("llama.cpp not available")
            return
            
        try:
            logger.info(f"Loading llama.cpp model from {self.model_path}")
            
            # Set device-specific parameters
            gpu_layers = 0
            if self.device == "cuda" or (self.device == "auto" and torch.cuda.is_available() if TRANSFORMERS_AVAILABLE else False):
                gpu_layers = -1  # Use all GPU layers
            
            self.model = Llama(
                model_path=self.model_path,
                n_gpu_layers=gpu_layers,
                n_ctx=self.kwargs.get('n_ctx', 4096),
                n_batch=self.kwargs.get('n_batch', 512),
                verbose=self.kwargs.get('verbose', False),
                **{k: v for k, v in self.kwargs.items() if k in ['n_ctx', 'n_batch', 'verbose']}
            )
            
            logger.info("llama.cpp model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load llama.cpp model: {str(e)}")
            self.model = None
    
    def _load_transformers(self):
        """Load model using HuggingFace Transformers."""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers not available")
            return
            
        try:
            logger.info(f"Loading transformers model: {self.model_path}")
            
            # Determine device
            if self.device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self.device
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=self.kwargs.get('trust_remote_code', False)
            )
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Configure model loading
            model_kwargs = {
                'torch_dtype': self.kwargs.get('torch_dtype', torch.float16),
                'device_map': self.kwargs.get('device_map', device),
                'trust_remote_code': self.kwargs.get('trust_remote_code', False)
            }
            
            # Add quantization if specified
            if self.kwargs.get('load_in_8bit', False) or self.kwargs.get('load_in_4bit', False):
                model_kwargs['quantization_config'] = BitsAndBytesConfig(
                    load_in_8bit=self.kwargs.get('load_in_8bit', False),
                    load_in_4bit=self.kwargs.get('load_in_4bit', False)
                )
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                **model_kwargs
            )
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1
            )
            
            logger.info("Transformers model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load transformers model: {str(e)}")
            self.model = None
            self.tokenizer = None
            self.pipeline = None

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Generate text based on the input prompt.
        
        Args:
            prompt: Input text prompt
            max_tokens: Maximum tokens to generate (overrides instance default)
            temperature: Sampling temperature (overrides instance default)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        if self.model is None:
            logger.error("No model loaded")
            return "Error: No model available"
        
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        if self.model_type == "llama_cpp":
            return self._generate_llama_cpp(prompt, max_tokens, temperature, **kwargs)
        elif self.model_type == "transformers":
            return self._generate_transformers(prompt, max_tokens, temperature, **kwargs)
        else:
            logger.error(f"Unknown model type: {self.model_type}")
            return "Error: Unknown model type"
    
    def _generate_llama_cpp(self, prompt: str, max_tokens: int, temperature: float, **kwargs) -> str:
        """Generate using llama.cpp."""
        try:
            output = self.model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=kwargs.get('stop', []),
                echo=kwargs.get('echo', False)
            )
            
            return output['choices'][0]['text']
            
        except Exception as e:
            logger.error(f"Generation error (llama.cpp): {str(e)}")
            return f"Error: {str(e)}"
    
    def _generate_transformers(self, prompt: str, max_tokens: int, temperature: float, **kwargs) -> str:
        """Generate using transformers."""
        try:
            if self.pipeline is None:
                logger.error("Pipeline not initialized")
                return "Error: Pipeline not available"
            
            # Generate
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
                **{k: v for k, v in kwargs.items() if k in ['top_p', 'top_k', 'repetition_penalty']}
            )
            
            # Extract generated text (remove input prompt)
            generated_text = outputs[0]['generated_text']
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):]
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"Generation error (transformers): {str(e)}")
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Check if the model is loaded and available."""
        return self.model is not None

    def get_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "model_path": self.model_path,
            "model_type": self.model_type,
            "device": self.device,
            "is_available": self.is_available(),
            "backends_available": {
                "llama_cpp": LLAMA_CPP_AVAILABLE,
                "transformers": TRANSFORMERS_AVAILABLE
            }
        }
        
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
 