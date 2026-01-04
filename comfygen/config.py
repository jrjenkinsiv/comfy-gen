"""Configuration loading for ComfyGen.

This module handles loading and accessing configuration from presets.yaml
and lora_catalog.yaml files. Used by both CLI and MCP server to ensure
consistent behavior.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class Config:
    """Centralized configuration loader for ComfyGen."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing config files (defaults to project root)
        """
        if config_dir is None:
            # Default to project root (parent of comfygen package)
            config_dir = Path(__file__).parent.parent
        
        self.config_dir = Path(config_dir)
        self._presets_config = None
        self._lora_catalog = None
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML file from config directory.
        
        Args:
            filename: Name of YAML file
            
        Returns:
            Parsed YAML data or empty dict on error
        """
        filepath = self.config_dir / filename
        if not filepath.exists():
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return data if data else {}
        except (OSError, yaml.YAMLError) as e:
            print(f"[WARN] Failed to load {filename}: {e}")
            return {}
    
    @property
    def presets_config(self) -> Dict[str, Any]:
        """Get presets configuration (cached).
        
        Returns:
            Full presets.yaml configuration
        """
        if self._presets_config is None:
            self._presets_config = self._load_yaml("presets.yaml")
        return self._presets_config
    
    @property
    def lora_catalog(self) -> Dict[str, Any]:
        """Get LoRA catalog (cached).
        
        Returns:
            Full lora_catalog.yaml configuration
        """
        if self._lora_catalog is None:
            self._lora_catalog = self._load_yaml("lora_catalog.yaml")
        return self._lora_catalog
    
    def get_default_negative_prompt(self) -> str:
        """Get default negative prompt from config.
        
        Returns:
            Default negative prompt string or empty string
        """
        return self.presets_config.get("default_negative_prompt", "")
    
    def get_presets(self) -> Dict[str, Any]:
        """Get generation presets.
        
        Returns:
            Dictionary of presets (draft, balanced, high-quality, etc.)
        """
        return self.presets_config.get("presets", {})
    
    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific preset by name.
        
        Args:
            name: Preset name (e.g., 'draft', 'balanced', 'high-quality')
            
        Returns:
            Preset configuration or None if not found
        """
        presets = self.get_presets()
        return presets.get(name)
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation settings.
        
        Returns:
            Validation configuration dictionary
        """
        return self.presets_config.get("validation", {})
    
    def get_lora_presets(self) -> Dict[str, Any]:
        """Get LoRA presets from catalog.
        
        Returns:
            Dictionary of LoRA presets from model_suggestions
        """
        return self.lora_catalog.get("model_suggestions", {})
    
    def get_lora_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific LoRA preset by name.
        
        Args:
            name: Preset name (e.g., 'text_to_video', 'image_to_video')
            
        Returns:
            LoRA preset configuration or None if not found
        """
        presets = self.get_lora_presets()
        return presets.get(name)
    
    def get_lora_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get LoRA information by filename.
        
        Args:
            filename: LoRA filename
            
        Returns:
            LoRA metadata or None if not found
        """
        loras = self.lora_catalog.get("loras", [])
        for lora in loras:
            if lora.get("filename") == filename:
                return lora
        return None
    
    def resolve_lora_preset(self, preset_name: str) -> list:
        """Resolve LoRA preset to list of (filename, strength) tuples.
        
        Args:
            preset_name: Name of the LoRA preset
            
        Returns:
            List of (lora_filename, strength) tuples
        """
        preset = self.get_lora_preset(preset_name)
        if not preset or "default_loras" not in preset:
            return []
        
        result = []
        for lora_filename in preset["default_loras"]:
            lora_info = self.get_lora_info(lora_filename)
            strength = lora_info.get("recommended_strength", 1.0) if lora_info else 1.0
            result.append((lora_filename, strength))
        
        return result


# Global config instance (singleton pattern)
_global_config = None


def get_config(config_dir: Optional[Path] = None) -> Config:
    """Get global config instance.
    
    Args:
        config_dir: Optional config directory (only used on first call)
        
    Returns:
        Shared Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config(config_dir)
    return _global_config
