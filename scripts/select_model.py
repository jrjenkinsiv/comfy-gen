#!/usr/bin/env python3
"""Intelligent model and LoRA selection based on prompt analysis.

This script analyzes text prompts and suggests appropriate models and LoRAs
from the available inventory on the ComfyUI server.

Usage:
    python scripts/select_model.py "your prompt here"
    python scripts/select_model.py "your prompt" --output-format json
    python scripts/select_model.py "your prompt" --prefer-speed
    python scripts/select_model.py "your prompt" --prefer-quality
"""

import argparse
import json
import sys
import re
from typing import Dict, List, Tuple, Optional

try:
    import requests
except ImportError:
    print("[ERROR] requests package not installed. Run: pip install requests")
    sys.exit(1)

COMFYUI_HOST = "http://192.168.1.215:8188"

# Default models for different use cases
DEFAULT_IMAGE_MODEL = "v1-5-pruned-emaonly-fp16.safetensors"
DEFAULT_VIDEO_MODEL = "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"

# LoRA catalog with semantic information
LORA_CATALOG = {
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "text-to-video"],
        "compatible_with": ["wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors"],
        "strength": {"model": 1.0, "clip": 1.0},
        "description": "4-step acceleration for Wan 2.2 T2V high noise",
        "priority": "speed"
    },
    "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "text-to-video"],
        "compatible_with": ["wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": {"model": 1.0, "clip": 1.0},
        "description": "4-step acceleration for Wan 2.2 T2V low noise",
        "priority": "speed"
    },
    "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "image-to-video", "animation"],
        "compatible_with": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"],
        "strength": {"model": 1.0, "clip": 1.0},
        "description": "4-step acceleration for Wan 2.2 I2V high noise",
        "priority": "speed"
    },
    "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "image-to-video", "animation"],
        "compatible_with": ["wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"],
        "strength": {"model": 1.0, "clip": 1.0},
        "description": "4-step acceleration for Wan 2.2 I2V low noise",
        "priority": "speed"
    },
    "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors": {
        "tags": ["acceleration", "speed", "4-step", "fast", "quick", "image-to-video", "seko"],
        "compatible_with": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"],
        "strength": {"model": 1.0, "clip": 1.0},
        "description": "Alternative 4-step acceleration (Seko) for Wan 2.2 I2V",
        "priority": "speed"
    },
    "BoobPhysics_WAN_v6.safetensors": {
        "tags": ["physics", "motion", "body", "realistic", "bounce", "movement", "anatomy"],
        "compatible_with": [
            "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
        ],
        "strength": {"model": 0.7, "clip": 0.7},
        "description": "Enhances realistic body physics in video",
        "priority": "quality"
    },
    "BounceHighWan2_2.safetensors": {
        "tags": ["bounce", "motion", "physics", "movement", "dynamic", "high-noise"],
        "compatible_with": [
            "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
        ],
        "strength": {"model": 0.7, "clip": 0.7},
        "description": "Enhances bouncing and dynamic motion (high noise)",
        "priority": "quality"
    },
    "BounceLowWan2_2.safetensors": {
        "tags": ["bounce", "motion", "physics", "movement", "dynamic", "low-noise"],
        "compatible_with": [
            "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors",
            "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
        ],
        "strength": {"model": 0.7, "clip": 0.7},
        "description": "Enhances bouncing and dynamic motion (low noise)",
        "priority": "quality"
    },
    "wan-thiccum-v3.safetensors": {
        "tags": ["body", "enhancement", "figure", "shape", "anatomy"],
        "compatible_with": [
            "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
            "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"
        ],
        "strength": {"model": 0.7, "clip": 0.7},
        "description": "Body enhancement for Wan 2.2",
        "priority": "quality"
    }
}


def query_available_models() -> Dict[str, List[str]]:
    """Query ComfyUI API for available models.
    
    Returns:
        Dictionary with model types as keys and lists of filenames as values
    """
    try:
        response = requests.get(f"{COMFYUI_HOST}/object_info", timeout=5)
        if response.status_code != 200:
            print(f"[WARN] Could not query models from ComfyUI API (status {response.status_code})")
            return {}
        
        data = response.json()
        
        available = {
            "checkpoints": [],
            "diffusion_models": [],
            "loras": []
        }
        
        # Extract checkpoint models
        if "CheckpointLoaderSimple" in data:
            ckpt_data = data["CheckpointLoaderSimple"].get("input", {}).get("required", {})
            if "ckpt_name" in ckpt_data:
                available["checkpoints"] = ckpt_data["ckpt_name"][0]
        
        # Extract LoRA models
        if "LoraLoader" in data:
            lora_data = data["LoraLoader"].get("input", {}).get("required", {})
            if "lora_name" in lora_data:
                available["loras"] = lora_data["lora_name"][0]
        
        return available
        
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Could not connect to ComfyUI server: {e}")
        return {}


def analyze_prompt(prompt: str) -> Dict[str, any]:
    """Analyze prompt to determine generation requirements.
    
    Args:
        prompt: Text prompt to analyze
        
    Returns:
        Dictionary with analysis results
    """
    prompt_lower = prompt.lower()
    
    analysis = {
        "is_video": False,
        "has_motion": False,
        "motion_keywords": [],
        "style_keywords": [],
        "requires_physics": False
    }
    
    # Video indicators
    video_keywords = [
        "video", "animation", "animate", "movement", "motion", "moving",
        "walk", "walking", "run", "running", "drive", "driving",
        "fly", "flying", "dance", "dancing", "jump", "jumping",
        "bounce", "bouncing", "swing", "swinging"
    ]
    
    for keyword in video_keywords:
        if keyword in prompt_lower:
            analysis["is_video"] = True
            analysis["has_motion"] = True
            analysis["motion_keywords"].append(keyword)
    
    # Physics indicators
    physics_keywords = [
        "bounce", "bouncing", "physics", "realistic motion",
        "body movement", "natural movement"
    ]
    
    for keyword in physics_keywords:
        if keyword in prompt_lower:
            analysis["requires_physics"] = True
    
    # Style indicators
    style_keywords = {
        "photorealistic": ["photo", "photorealistic", "realistic", "photography"],
        "cinematic": ["cinematic", "film", "movie"],
        "artistic": ["artistic", "painting", "drawn", "illustration"],
        "anime": ["anime", "manga", "cartoon"]
    }
    
    for style, keywords in style_keywords.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                analysis["style_keywords"].append(style)
                break
    
    return analysis


def select_base_model(analysis: Dict, available_models: Dict) -> Tuple[str, str]:
    """Select appropriate base model based on analysis.
    
    Args:
        analysis: Prompt analysis results
        available_models: Available models from API
        
    Returns:
        Tuple of (model_filename, reason)
    """
    checkpoints = available_models.get("checkpoints", [])
    
    if analysis["is_video"]:
        # Prefer high noise for video by default
        preferred = DEFAULT_VIDEO_MODEL
        reason = "Video generation requested"
        
        # Check if available
        if checkpoints and preferred not in checkpoints:
            # Try to find any Wan model
            for ckpt in checkpoints:
                if "wan" in ckpt.lower() and "t2v" in ckpt.lower():
                    return ckpt, f"Video model (fallback to {ckpt})"
            
            # Last resort: use default image model
            if DEFAULT_IMAGE_MODEL in checkpoints:
                return DEFAULT_IMAGE_MODEL, "Fallback to image model (no video models available)"
        
        return preferred, reason
    else:
        # Image generation
        preferred = DEFAULT_IMAGE_MODEL
        reason = "Image generation (default SD 1.5)"
        
        if checkpoints and preferred not in checkpoints:
            # Use first available checkpoint
            if checkpoints:
                return checkpoints[0], f"Fallback to {checkpoints[0]}"
        
        return preferred, reason


def select_loras(
    base_model: str,
    analysis: Dict,
    available_loras: List[str],
    prefer_speed: bool = True
) -> List[Tuple[str, Dict, str]]:
    """Select appropriate LoRAs based on base model and analysis.
    
    Args:
        base_model: Selected base model filename
        analysis: Prompt analysis results
        available_loras: List of available LoRA filenames
        prefer_speed: Whether to prioritize speed over quality
        
    Returns:
        List of tuples (lora_filename, config_dict, reason)
    """
    selected = []
    
    # Filter catalog to only available LoRAs
    available_catalog = {
        name: config for name, config in LORA_CATALOG.items()
        if name in available_loras
    }
    
    # Check compatibility with base model
    compatible_loras = {
        name: config for name, config in available_catalog.items()
        if base_model in config["compatible_with"]
    }
    
    if not compatible_loras:
        return []
    
    # Always add acceleration LoRA if available and prefer_speed is True
    if prefer_speed:
        for name, config in compatible_loras.items():
            if "acceleration" in config["tags"]:
                selected.append((
                    name,
                    config["strength"],
                    "Speed optimization (4-step acceleration)"
                ))
                break  # Only one acceleration LoRA
    
    # Add physics/motion LoRAs if needed
    if analysis["has_motion"] or analysis["requires_physics"]:
        for name, config in compatible_loras.items():
            # Skip if already selected (acceleration)
            if any(name == s[0] for s in selected):
                continue
            
            # Check if tags match motion requirements
            if any(tag in config["tags"] for tag in ["motion", "physics", "bounce"]):
                selected.append((
                    name,
                    config["strength"],
                    f"Motion enhancement (detected: {', '.join(analysis['motion_keywords'])})"
                ))
                break  # Only one motion LoRA to avoid conflicts
    
    return selected


def format_text_output(
    base_model: str,
    base_reason: str,
    loras: List[Tuple[str, Dict, str]],
    analysis: Dict
) -> str:
    """Format selection results as human-readable text.
    
    Args:
        base_model: Selected base model
        base_reason: Reason for base model selection
        loras: Selected LoRAs with config and reasons
        analysis: Prompt analysis
        
    Returns:
        Formatted text output
    """
    lines = []
    lines.append("=" * 60)
    lines.append("INTELLIGENT MODEL SELECTION")
    lines.append("=" * 60)
    lines.append("")
    
    # Prompt analysis
    lines.append("Prompt Analysis:")
    lines.append(f"  Type: {'Video' if analysis['is_video'] else 'Image'}")
    if analysis["motion_keywords"]:
        lines.append(f"  Motion: {', '.join(analysis['motion_keywords'])}")
    if analysis["style_keywords"]:
        lines.append(f"  Style: {', '.join(analysis['style_keywords'])}")
    lines.append("")
    
    # Base model
    lines.append("Selected Base Model:")
    lines.append(f"  {base_model}")
    lines.append(f"  Reason: {base_reason}")
    lines.append("")
    
    # LoRAs
    if loras:
        lines.append(f"Selected LoRAs ({len(loras)}):")
        for i, (name, strength, reason) in enumerate(loras, 1):
            lines.append(f"  {i}. {name}")
            lines.append(f"     Strength: model={strength['model']}, clip={strength['clip']}")
            lines.append(f"     Reason: {reason}")
            lines.append("")
    else:
        lines.append("Selected LoRAs: None")
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_json_output(
    base_model: str,
    base_reason: str,
    loras: List[Tuple[str, Dict, str]],
    analysis: Dict
) -> str:
    """Format selection results as JSON.
    
    Args:
        base_model: Selected base model
        base_reason: Reason for base model selection
        loras: Selected LoRAs with config and reasons
        analysis: Prompt analysis
        
    Returns:
        JSON string
    """
    result = {
        "analysis": analysis,
        "base_model": {
            "filename": base_model,
            "reason": base_reason
        },
        "loras": [
            {
                "filename": name,
                "strength_model": strength["model"],
                "strength_clip": strength["clip"],
                "reason": reason
            }
            for name, strength, reason in loras
        ]
    }
    
    return json.dumps(result, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent model and LoRA selection based on prompt analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/select_model.py "a car driving fast"
  python scripts/select_model.py "portrait photo" --prefer-quality
  python scripts/select_model.py "dancing person" --output-format json
        """
    )
    parser.add_argument(
        "prompt",
        help="Text prompt to analyze"
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--prefer-speed",
        action="store_true",
        default=True,
        help="Prioritize speed over quality (default: true)"
    )
    parser.add_argument(
        "--prefer-quality",
        action="store_true",
        help="Prioritize quality over speed (disables acceleration LoRAs)"
    )
    args = parser.parse_args()
    
    # Determine speed preference
    prefer_speed = args.prefer_speed and not args.prefer_quality
    
    # Query available models
    print("[INFO] Querying available models from ComfyUI...", file=sys.stderr)
    available = query_available_models()
    
    if not available:
        print("[WARN] Using default model catalog (API unavailable)", file=sys.stderr)
        available = {
            "checkpoints": [DEFAULT_IMAGE_MODEL, DEFAULT_VIDEO_MODEL],
            "loras": list(LORA_CATALOG.keys())
        }
    
    # Analyze prompt
    analysis = analyze_prompt(args.prompt)
    
    # Select base model
    base_model, base_reason = select_base_model(analysis, available)
    
    # Select LoRAs
    loras = select_loras(
        base_model,
        analysis,
        available.get("loras", []),
        prefer_speed=prefer_speed
    )
    
    # Output results
    if args.output_format == "json":
        print(format_json_output(base_model, base_reason, loras, analysis))
    else:
        print(format_text_output(base_model, base_reason, loras, analysis))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
