"""Configuration loader for ComfyGen.

This module provides shared configuration loading for both CLI and MCP server.
Loads presets.yaml and lora_catalog.yaml for consistent behavior across interfaces.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


def get_config_path(filename: str = "presets.yaml") -> Path:
    """Get path to configuration file.
    
    Args:
        filename: Configuration filename
        
    Returns:
        Path to configuration file
    """
    # Look for config file in project root
    # This works for both CLI and MCP server
    config_path = Path(__file__).parent.parent / filename
    return config_path


def load_presets_config() -> Dict[str, Any]:
    """Load full configuration from presets.yaml.
    
    Returns:
        Dictionary with keys:
            - presets: Dict of preset configurations
            - default_negative_prompt: Default negative prompt string
            - validation: Validation settings
            - negative_prompts: Subject-specific negative prompts
            - positive_emphasis: Positive prompt helpers
    """
    config_path = get_config_path("presets.yaml")
    
    if not config_path.exists():
        return {
            "presets": {},
            "default_negative_prompt": "",
            "validation": {},
            "negative_prompts": {},
            "positive_emphasis": {}
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return {
            "presets": data.get("presets", {}),
            "default_negative_prompt": data.get("default_negative_prompt", ""),
            "validation": data.get("validation", {}),
            "negative_prompts": data.get("negative_prompts", {}),
            "positive_emphasis": data.get("positive_emphasis", {})
        }
    except Exception as e:
        print(f"[ERROR] Failed to load presets.yaml: {e}")
        return {
            "presets": {},
            "default_negative_prompt": "",
            "validation": {},
            "negative_prompts": {},
            "positive_emphasis": {}
        }


def load_lora_catalog() -> Dict[str, Any]:
    """Load LoRA catalog from lora_catalog.yaml.
    
    Returns:
        Dictionary with keys:
            - loras: List of LoRA metadata
            - model_suggestions: Predefined scenarios
            - keyword_mappings: Keywords to tag mappings
    """
    catalog_path = get_config_path("lora_catalog.yaml")
    
    if not catalog_path.exists():
        return {
            "loras": [],
            "model_suggestions": {},
            "keyword_mappings": {}
        }
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = yaml.safe_load(f) or {}
        
        return {
            "loras": catalog.get("loras", []),
            "model_suggestions": catalog.get("model_suggestions", {}),
            "keyword_mappings": catalog.get("keyword_mappings", {})
        }
    except Exception as e:
        print(f"[ERROR] Failed to load lora_catalog.yaml: {e}")
        return {
            "loras": [],
            "model_suggestions": {},
            "keyword_mappings": {}
        }


def get_preset(preset_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific preset by name.
    
    Args:
        preset_name: Name of the preset (e.g., 'draft', 'balanced', 'high-quality')
        
    Returns:
        Preset configuration dictionary or None if not found
    """
    config = load_presets_config()
    presets = config.get("presets", {})
    return presets.get(preset_name)


def get_lora_preset(preset_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific LoRA preset by name.
    
    Args:
        preset_name: Name of the LoRA preset from model_suggestions
        
    Returns:
        LoRA preset configuration or None if not found
    """
    catalog = load_lora_catalog()
    suggestions = catalog.get("model_suggestions", {})
    return suggestions.get(preset_name)


def apply_preset_to_params(
    params: Dict[str, Any],
    preset: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply preset values to parameters.
    
    Preset values are used as defaults. Explicit parameter values override preset.
    
    Args:
        params: Current parameters (user-provided values)
        preset: Preset configuration
        
    Returns:
        Updated parameters dictionary
    """
    # Create a copy to avoid modifying the original
    result = params.copy()
    
    # Apply preset values only if not already set
    preset_keys = ['steps', 'cfg', 'sampler', 'scheduler', 'validate', 
                   'auto_retry', 'positive_threshold', 'width', 'height']
    
    for key in preset_keys:
        if key in preset and key not in result:
            result[key] = preset[key]
    
    return result
