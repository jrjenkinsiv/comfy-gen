#!/usr/bin/env python3
"""Intelligent model and LoRA selection based on prompt analysis.

This script analyzes a text prompt and suggests appropriate models and LoRAs
based on semantic keywords and intent detection.

Usage:
    python3 select_model.py "a car driving fast with motion blur"
    python3 select_model.py --prompt "realistic portrait" --query-api
"""

import argparse
import json
import re
import sys
import requests
from typing import Dict, List, Tuple, Optional

COMFYUI_HOST = "http://192.168.1.215:8188"

# Model catalog with semantic tags
MODELS = {
    "v1-5-pruned-emaonly-fp16.safetensors": {
        "type": "checkpoint",
        "tags": ["image", "photo", "art", "general", "fast", "portrait", "landscape", "object"],
        "description": "SD 1.5 - Fast general-purpose image generation"
    },
    "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors": {
        "type": "diffusion",
        "tags": ["video", "motion", "animation", "movement", "action", "high-noise", "text-to-video"],
        "description": "Wan 2.2 T2V High Noise - Text-to-video with high noise tolerance"
    },
    "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors": {
        "type": "diffusion",
        "tags": ["video", "motion", "animation", "movement", "action", "low-noise", "text-to-video"],
        "description": "Wan 2.2 T2V Low Noise - Text-to-video with low noise for cleaner output"
    }
}

# LoRA catalog with semantic tags (from LORA_CATALOG.md)
LORAS = {
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "text-to-video"],
        "compatible_with": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"],
        "strength": (1.0, 1.0),
        "description": "4-step acceleration for Wan 2.2 T2V high noise"
    },
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "text-to-video"],
        "compatible_with": ["wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": (1.0, 1.0),
        "description": "4-step acceleration for Wan 2.2 T2V low noise"
    },
    "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "image-to-video"],
        "compatible_with": ["wan2.2_i2v_high_noise"],
        "strength": (1.0, 1.0),
        "description": "4-step acceleration for Wan 2.2 I2V high noise"
    },
    "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "image-to-video"],
        "compatible_with": ["wan2.2_i2v_low_noise"],
        "strength": (1.0, 1.0),
        "description": "4-step acceleration for Wan 2.2 I2V low noise"
    },
    "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "seko", "image-to-video"],
        "compatible_with": ["wan2.2_i2v_high_noise"],
        "strength": (1.0, 1.0),
        "description": "Alternative 4-step acceleration for Wan 2.2 I2V (Seko)"
    },
    "BoobPhysics_WAN_v6.safetensors": {
        "tags": ["physics", "motion", "body", "realistic", "dynamics", "bounce"],
        "compatible_with": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", 
                          "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": (0.7, 0.7),
        "description": "Realistic body physics for video"
    },
    "BounceHighWan2_2.safetensors": {
        "tags": ["motion", "bounce", "dynamics", "movement", "high-energy"],
        "compatible_with": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"],
        "strength": (0.7, 0.7),
        "description": "Enhanced bounce and motion for high noise variant"
    },
    "BounceLowWan2_2.safetensors": {
        "tags": ["motion", "bounce", "dynamics", "movement", "subtle"],
        "compatible_with": ["wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": (0.7, 0.7),
        "description": "Enhanced bounce and motion for low noise variant"
    },
    "wan-thiccum-v3.safetensors": {
        "tags": ["body", "enhancement", "curves", "proportions"],
        "compatible_with": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                          "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": (0.6, 0.6),
        "description": "Body proportion enhancement"
    }
}

# Default selections
DEFAULT_MODEL = "v1-5-pruned-emaonly-fp16.safetensors"
DEFAULT_VIDEO_MODEL = "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"


def query_available_models() -> Tuple[List[str], List[str]]:
    """Query ComfyUI API for available models and LoRAs.
    
    Returns:
        Tuple of (available_models, available_loras)
    """
    try:
        response = requests.get(f"{COMFYUI_HOST}/object_info", timeout=5)
        if response.status_code != 200:
            print(f"[WARN] Failed to query API: {response.status_code}")
            return [], []
        
        data = response.json()
        
        # Extract checkpoints
        checkpoints = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        
        # Extract LoRAs
        loras = data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
        
        return checkpoints, loras
        
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Could not connect to ComfyUI API: {e}")
        return [], []
    except Exception as e:
        print(f"[WARN] Error parsing API response: {e}")
        return [], []


def analyze_prompt(prompt: str) -> Dict[str, any]:
    """Analyze prompt to extract intent and keywords.
    
    Args:
        prompt: User's text prompt
        
    Returns:
        Dictionary with analysis results
    """
    prompt_lower = prompt.lower()
    
    analysis = {
        "is_video": False,
        "needs_speed": False,
        "needs_motion": False,
        "needs_physics": False,
        "keywords": []
    }
    
    # Video detection
    video_keywords = ["video", "animation", "motion", "movement", "driving", "walking", 
                     "running", "dancing", "flying", "moving", "action"]
    analysis["is_video"] = any(kw in prompt_lower for kw in video_keywords)
    
    # Speed/fast generation detection
    speed_keywords = ["fast", "quick", "speed", "rapid", "4-step", "4 step"]
    analysis["needs_speed"] = any(kw in prompt_lower for kw in speed_keywords)
    
    # Motion/dynamics detection
    motion_keywords = ["motion", "dynamic", "bounce", "physics", "realistic movement"]
    analysis["needs_motion"] = any(kw in prompt_lower for kw in motion_keywords)
    
    # Physics detection
    physics_keywords = ["physics", "realistic", "natural movement", "body"]
    analysis["needs_physics"] = any(kw in prompt_lower for kw in physics_keywords)
    
    # Extract all words as potential keywords
    words = re.findall(r'\b\w+\b', prompt_lower)
    analysis["keywords"] = words
    
    return analysis


def select_model(analysis: Dict[str, any], available_models: Optional[List[str]] = None) -> str:
    """Select best model based on prompt analysis.
    
    Args:
        analysis: Prompt analysis results
        available_models: List of available models from API (optional)
        
    Returns:
        Selected model filename
    """
    if analysis["is_video"]:
        # Prefer low noise for general use unless high energy motion
        if analysis["needs_motion"] or analysis["needs_physics"]:
            model = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"
        else:
            model = DEFAULT_VIDEO_MODEL
    else:
        model = DEFAULT_MODEL
    
    # Verify model is available if we have API data
    if available_models and model not in available_models:
        print(f"[WARN] Preferred model {model} not available, using default")
        if analysis["is_video"]:
            # Try to find any wan model
            wan_models = [m for m in available_models if "wan" in m.lower()]
            model = wan_models[0] if wan_models else DEFAULT_MODEL
        else:
            model = DEFAULT_MODEL
    
    return model


def select_loras(analysis: Dict[str, any], model: str, 
                available_loras: Optional[List[str]] = None) -> List[Dict[str, any]]:
    """Select compatible LoRAs based on prompt analysis and model.
    
    Args:
        analysis: Prompt analysis results
        model: Selected model filename
        available_loras: List of available LoRAs from API (optional)
        
    Returns:
        List of selected LoRAs with metadata
    """
    selected = []
    
    for lora_name, lora_info in LORAS.items():
        # Skip if not compatible with selected model
        if model not in lora_info["compatible_with"]:
            continue
        
        # Skip if not available (if we have API data)
        if available_loras and lora_name not in available_loras:
            continue
        
        score = 0
        reasons = []
        
        # Score based on matching tags with analysis
        if analysis["needs_speed"] and any(tag in lora_info["tags"] for tag in ["acceleration", "speed", "fast"]):
            score += 10
            reasons.append("speed optimization requested")
        
        if analysis["needs_motion"] and any(tag in lora_info["tags"] for tag in ["motion", "bounce", "dynamics"]):
            score += 8
            reasons.append("motion enhancement needed")
        
        if analysis["needs_physics"] and any(tag in lora_info["tags"] for tag in ["physics", "realistic"]):
            score += 8
            reasons.append("physics simulation needed")
        
        # Match keywords
        keyword_matches = sum(1 for kw in analysis["keywords"] if kw in lora_info["tags"])
        score += keyword_matches * 2
        if keyword_matches > 0:
            reasons.append(f"{keyword_matches} keyword matches")
        
        if score > 0:
            strength_model, strength_clip = lora_info["strength"]
            selected.append({
                "filename": lora_name,
                "score": score,
                "strength_model": strength_model,
                "strength_clip": strength_clip,
                "description": lora_info["description"],
                "reasons": reasons
            })
    
    # Sort by score descending
    selected.sort(key=lambda x: x["score"], reverse=True)
    
    return selected


def main():
    parser = argparse.ArgumentParser(
        description="Suggest models and LoRAs based on prompt analysis"
    )
    parser.add_argument(
        "prompt", 
        nargs="?",
        help="Text prompt to analyze"
    )
    parser.add_argument(
        "--prompt",
        dest="prompt_arg",
        help="Text prompt to analyze (alternative syntax)"
    )
    parser.add_argument(
        "--query-api",
        action="store_true",
        help="Query ComfyUI API for available models/LoRAs"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    # Get prompt from either positional or named argument
    prompt = args.prompt or args.prompt_arg
    if not prompt:
        parser.error("Prompt is required")
    
    # Query API if requested
    available_models = []
    available_loras = []
    if args.query_api:
        print("[INFO] Querying ComfyUI API for available models...")
        available_models, available_loras = query_available_models()
        if available_models:
            print(f"[OK] Found {len(available_models)} models and {len(available_loras)} LoRAs")
    
    # Analyze prompt
    analysis = analyze_prompt(prompt)
    
    # Select model and LoRAs
    model = select_model(analysis, available_models if args.query_api else None)
    loras = select_loras(analysis, model, available_loras if args.query_api else None)
    
    # Prepare results
    results = {
        "prompt": prompt,
        "analysis": analysis,
        "model": model,
        "model_description": MODELS.get(model, {}).get("description", "Unknown model"),
        "loras": loras[:3]  # Top 3 LoRAs
    }
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"\n[OK] Analysis complete for prompt: \"{prompt}\"\n")
        print(f"Suggested Model: {model}")
        print(f"  Description: {results['model_description']}")
        print(f"  Reason: {'Video generation' if analysis['is_video'] else 'Image generation'}")
        
        if loras:
            print(f"\nSuggested LoRAs ({len(loras)} found):")
            for i, lora in enumerate(loras, 1):
                print(f"\n  {i}. {lora['filename']}")
                print(f"     Description: {lora['description']}")
                print(f"     Strength: model={lora['strength_model']}, clip={lora['strength_clip']}")
                print(f"     Reasons: {', '.join(lora['reasons'])}")
                print(f"     Score: {lora['score']}")
        else:
            print("\nNo LoRAs suggested (use base model only)")
        
        print(f"\nIntent Detection:")
        print(f"  Video: {analysis['is_video']}")
        print(f"  Speed: {analysis['needs_speed']}")
        print(f"  Motion: {analysis['needs_motion']}")
        print(f"  Physics: {analysis['needs_physics']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
