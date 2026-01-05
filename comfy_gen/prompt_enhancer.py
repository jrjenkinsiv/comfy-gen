"""Prompt enhancement using small language models.

This module provides automatic prompt enhancement for better image generation:
- Adds quality boosters (resolution, lighting, composition)
- Suggests style modifiers based on subject
- Applies model-specific optimizations
- Prevents common prompt mistakes

The enhancer uses small LLMs that can run on CPU for portability.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

# Lazy imports for transformers (only loaded when needed)
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


# Default model to use (Qwen2.5-0.5B is small, fast, and good at following instructions)
DEFAULT_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ALTERNATIVE_MODELS = [
    "microsoft/phi-2",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
]

# Model cache directory
CACHE_DIR = Path.home() / ".cache" / "comfy-gen" / "prompt-enhancer"


class PromptEnhancer:
    """Enhance prompts using a small language model."""
    
    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "cpu"):
        """Initialize the prompt enhancer.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run on ("cpu" or "cuda")
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "Transformers library not available. "
                "Install with: pip install transformers torch"
            )
        
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # Load prompt catalog for context
        self.catalog = self._load_prompt_catalog()
    
    def _load_prompt_catalog(self) -> Dict[str, Any]:
        """Load prompt catalog for quality boosters and style modifiers."""
        catalog_path = Path(__file__).parent.parent / "prompt_catalog.yaml"
        if catalog_path.exists():
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[WARN] Failed to load prompt_catalog.yaml: {e}", file=sys.stderr)
        return {}
    
    def _ensure_model_loaded(self):
        """Lazy-load the model on first use."""
        if self.pipeline is not None:
            return
        
        print(f"[INFO] Loading prompt enhancer model: {self.model_name}")
        print(f"[INFO] This may take a moment on first run (model will be cached)")
        
        try:
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=CACHE_DIR,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                cache_dir=CACHE_DIR,
                torch_dtype=torch.float32,  # Use float32 for CPU
                device_map=self.device,
                trust_remote_code=True
            )
            
            # Create text generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
            
            print(f"[OK] Model loaded successfully")
            
        except Exception as e:
            print(f"[ERROR] Failed to load model {self.model_name}: {e}", file=sys.stderr)
            raise
    
    def _build_system_prompt(self, style: Optional[str] = None) -> str:
        """Build system prompt with guidelines for enhancement.
        
        Args:
            style: Optional style hint (photorealistic, artistic, game-asset, etc.)
        """
        # Extract quality boosters from catalog
        quality_hints = []
        if self.catalog and "quality_boosters" in self.catalog:
            boosters = self.catalog["quality_boosters"]
            if "resolution" in boosters:
                quality_hints.append("resolution keywords (8K, 4K, ultra detailed)")
            if "lighting" in boosters:
                quality_hints.append("lighting (cinematic, volumetric, golden hour)")
            if "sharpness" in boosters:
                quality_hints.append("sharpness (sharp focus, crystal clear)")
            if "composition" in boosters:
                quality_hints.append("composition (professional photography)")
        
        style_context = ""
        if style:
            style_context = f"\n- Target style: {style}"
        
        system_prompt = f"""You are an expert prompt engineer for AI image generation. Your task is to enhance user prompts to produce higher quality images.

Guidelines:
- Add descriptive details about lighting, composition, and camera settings
- Include quality boosters: {', '.join(quality_hints) if quality_hints else 'detailed, high resolution, sharp focus'}
- Maintain the original subject and intent
- Keep prompts natural and readable
- Target length: 100-200 tokens
- DO NOT add explanations or meta-commentary{style_context}

Output ONLY the enhanced prompt, nothing else."""
        
        return system_prompt
    
    def enhance(self, prompt: str, style: Optional[str] = None) -> str:
        """Enhance a prompt using the LLM.
        
        Args:
            prompt: Original user prompt
            style: Optional style hint (photorealistic, artistic, game-asset, etc.)
        
        Returns:
            Enhanced prompt string
        """
        self._ensure_model_loaded()
        
        system_prompt = self._build_system_prompt(style)
        
        # Build the full prompt for the model
        # Format depends on the model - Qwen2.5 uses chat format
        if "Qwen" in self.model_name:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Enhance this image generation prompt: {prompt}"}
            ]
            
            # Apply chat template
            formatted_prompt = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # Generic format for other models
            formatted_prompt = f"{system_prompt}\n\nUser prompt: {prompt}\n\nEnhanced prompt:"
        
        try:
            # Generate enhanced prompt
            result = self.pipeline(
                formatted_prompt,
                max_new_tokens=256,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
            # Extract the generated text
            generated = result[0]["generated_text"]
            
            # Clean up the output
            if "Qwen" in self.model_name:
                # For chat models, extract only the assistant's response
                if "<|im_start|>assistant" in generated:
                    enhanced = generated.split("<|im_start|>assistant")[-1]
                    enhanced = enhanced.replace("<|im_end|>", "").strip()
                else:
                    # Fallback: take everything after the prompt
                    enhanced = generated[len(formatted_prompt):].strip()
            else:
                # For non-chat models, take everything after the prompt
                enhanced = generated[len(formatted_prompt):].strip()
            
            # Remove any remaining template markers
            enhanced = enhanced.replace("<|im_start|>", "").replace("<|im_end|>", "")
            
            # If the model added quotes, remove them
            enhanced = enhanced.strip('"\'')
            
            return enhanced
            
        except Exception as e:
            print(f"[ERROR] Enhancement failed: {e}", file=sys.stderr)
            # Fallback: return original prompt
            return prompt


# Global enhancer instance (lazy-loaded)
_enhancer_instance: Optional[PromptEnhancer] = None


def enhance_prompt(prompt: str, style: Optional[str] = None, model: Optional[str] = None) -> str:
    """Enhance a prompt using a small language model.
    
    This is the main public API for prompt enhancement.
    
    Args:
        prompt: Original user prompt
        style: Optional style hint (photorealistic, artistic, game-asset, etc.)
        model: Optional model name override (default: Qwen/Qwen2.5-0.5B-Instruct)
    
    Returns:
        Enhanced prompt string, or original prompt if enhancement fails
    
    Example:
        >>> enhanced = enhance_prompt("a cat", style="photorealistic")
        >>> print(enhanced)
        A highly detailed photograph of a cat, professional pet photography,
        soft natural lighting, shallow depth of field, 8K resolution, sharp focus
    """
    global _enhancer_instance
    
    if not TRANSFORMERS_AVAILABLE:
        print("[WARN] Transformers not available, returning original prompt", file=sys.stderr)
        return prompt
    
    try:
        # Lazy-load the enhancer
        if _enhancer_instance is None or (model and _enhancer_instance.model_name != model):
            model_name = model or DEFAULT_MODEL
            _enhancer_instance = PromptEnhancer(model_name=model_name)
        
        return _enhancer_instance.enhance(prompt, style=style)
        
    except Exception as e:
        print(f"[ERROR] Prompt enhancement failed: {e}", file=sys.stderr)
        print(f"[INFO] Returning original prompt", file=sys.stderr)
        return prompt


def is_available() -> bool:
    """Check if prompt enhancement is available.
    
    Returns:
        True if transformers library is installed, False otherwise
    """
    return TRANSFORMERS_AVAILABLE
