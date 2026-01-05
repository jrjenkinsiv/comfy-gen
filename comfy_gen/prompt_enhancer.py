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

# Alternative models that can be used (for future flexibility)
# Usage: enhance_prompt(prompt, model="microsoft/phi-2")
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
                print(f"[WARN] Enhancement will proceed without catalog context", file=sys.stderr)
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
            
            # Load model - don't use device_map with pipeline to avoid accelerate conflict
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                cache_dir=CACHE_DIR,
                torch_dtype=torch.float32,  # Use float32 for CPU
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            # Move to device if not using accelerate
            if self.device == "cpu":
                self.model = self.model.cpu()
            elif self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()
            
            # Create text generation pipeline without device arg (model already on correct device)
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
            
            print(f"[OK] Model loaded successfully")
            
        except Exception as e:
            print(f"[ERROR] Failed to load model {self.model_name}: {e}", file=sys.stderr)
            raise
    
    def _get_style_guidelines(self, style: Optional[str] = None) -> str:
        """Get style-specific guidelines from the catalog."""
        if not style:
            return ""
        
        # Check model-specific guidelines
        model_guidance = ""
        if self.catalog and "model_specific" in self.catalog:
            model_spec = self.catalog["model_specific"]
            if style in ["photorealistic", "portrait", "landscape"]:
                if "flux" in model_spec:
                    flux = model_spec["flux"]
                    model_guidance = f"\nModel guidance: {flux.get('notes', '')}. Prompt style: {flux.get('prompt_style', 'natural-language')}."
            elif style in ["pixel", "cartoon", "vector", "game-asset"]:
                if "sd15" in model_spec:
                    sd = model_spec["sd15"]
                    model_guidance = f"\nModel guidance: {sd.get('notes', '')}. Prompt style: {sd.get('prompt_style', 'keyword-heavy')}."
        
        # Get style modifiers from catalog
        style_mods = []
        if self.catalog and "style_modifiers" in self.catalog:
            mods = self.catalog["style_modifiers"]
            if style == "photorealistic" and "photography_styles" in mods:
                style_mods = mods["photography_styles"][:3]
            elif style == "artistic" and "artistic_styles" in mods:
                style_mods = mods["artistic_styles"][:3]
            elif style in ["game-asset", "pixel", "vector"]:
                style_mods = ["top-down view", "clean edges", "centered composition", "isolated subject"]
        
        style_examples = f"\nRelevant style keywords: {', '.join(style_mods)}" if style_mods else ""
        
        return f"{model_guidance}{style_examples}"
    
    def _get_quality_boosters_text(self) -> str:
        """Extract quality boosters from catalog as formatted text."""
        if not self.catalog or "quality_boosters" not in self.catalog:
            return "8K resolution, sharp focus, professional photography, cinematic lighting"
        
        boosters = self.catalog["quality_boosters"]
        examples = []
        
        for category in ["resolution", "lighting", "sharpness", "composition"]:
            if category in boosters:
                items = boosters[category]
                if items and len(items) > 0:
                    # Get keyword from first item with "high" effectiveness
                    high_eff = [b["keyword"] for b in items if b.get("effectiveness") == "high"]
                    if high_eff:
                        examples.append(high_eff[0])
        
        return ", ".join(examples) if examples else "8K resolution, sharp focus, cinematic lighting"
    
    def _get_negative_hints(self, style: Optional[str] = None) -> str:
        """Get negative prompt hints from catalog."""
        if not self.catalog or "negative_presets" not in self.catalog:
            return ""
        
        presets = self.catalog["negative_presets"]
        preset_key = "universal"
        
        if style:
            if style == "photorealistic":
                preset_key = "photorealistic"
            elif style in ["portrait", "nsfw"]:
                preset_key = "single_portrait"
            elif style in ["game-asset", "pixel", "vector"]:
                preset_key = "game_assets"
            elif style == "landscape":
                preset_key = "landscape"
        
        if preset_key in presets:
            return f"\nRecommended negative elements to avoid: {presets[preset_key].get('prompt', '')}"
        
        return ""
    
    def _build_system_prompt(self, style: Optional[str] = None) -> str:
        """Build comprehensive system prompt with catalog knowledge.
        
        Args:
            style: Optional style hint (photorealistic, artistic, game-asset, etc.)
        """
        quality_boosters = self._get_quality_boosters_text()
        style_guidelines = self._get_style_guidelines(style)
        negative_hints = self._get_negative_hints(style)
        
        # Include single-subject pattern if relevant (portraits, characters)
        single_subject_guidance = ""
        if style in ["portrait", "nsfw", "character"]:
            if self.catalog and "single_subject_patterns" in self.catalog:
                patterns = self.catalog["single_subject_patterns"]
                if "positive_prefix" in patterns:
                    prefix = patterns["positive_prefix"].get("strong", "")
                    single_subject_guidance = f"\n\nCRITICAL for single-person images: Start with emphasis like '{prefix}' to prevent duplicate subjects."
        
        system_prompt = f"""You are an expert prompt engineer for Stable Diffusion and Flux AI image generation models. Your task is to transform short, simple prompts into detailed, production-quality prompts that generate excellent images.

YOUR ROLE:
- You receive a basic prompt idea from the user
- You output a single enhanced prompt (no explanation, no meta-commentary)
- The enhanced prompt should be 100-200 words of vivid, specific description

ENHANCEMENT STRATEGY:
1. SUBJECT CLARITY: Keep the original subject but add specific details (age, appearance, pose, expression)
2. SCENE CONTEXT: Add environment, setting, time of day, weather/atmosphere
3. TECHNICAL QUALITY: Include quality boosters like: {quality_boosters}
4. CAMERA/COMPOSITION: Specify lens type, focal length, aperture, perspective, framing
5. LIGHTING: Describe light sources, direction, quality (soft/hard), color temperature
6. STYLE CONSISTENCY: Match the visual style throughout the prompt{style_guidelines}{single_subject_guidance}{negative_hints}

RULES:
- Output ONLY the enhanced prompt text, nothing else
- Do NOT include "Enhanced prompt:" or similar labels
- Do NOT add negative prompt suggestions (those are separate)
- Do NOT use bullet points or formatting - write as flowing natural text
- Maintain the user's original intent and subject

EXAMPLE:
User: "a cat"
Output: A majestic orange tabby cat with vibrant amber eyes perched gracefully on a weathered wooden fence post, bathed in warm golden hour sunlight that creates a soft rim light around its fluffy fur. The background features a blurred meadow with wildflowers in soft bokeh. Professional pet photography captured with an 85mm f/1.4 lens, shallow depth of field isolating the subject, ultra-detailed fur texture visible in 8K resolution, National Geographic style wildlife portrait."""
        
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
            # Use dedicated pad_token_id if available, fallback to eos_token_id
            pad_token = (
                self.tokenizer.pad_token_id 
                if self.tokenizer.pad_token_id is not None 
                else self.tokenizer.eos_token_id
            )
            result = self.pipeline(
                formatted_prompt,
                max_new_tokens=256,
                num_return_sequences=1,
                pad_token_id=pad_token,
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


def reset_enhancer() -> None:
    """Reset the global enhancer instance.
    
    This is primarily useful for testing to ensure a clean state
    between test cases.
    """
    global _enhancer_instance
    _enhancer_instance = None
