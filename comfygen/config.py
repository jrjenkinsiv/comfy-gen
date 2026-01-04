"""Configuration loader for presets and LoRA catalogs."""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class ConfigLoader:
    """Loads and manages configuration from presets.yaml and lora_catalog.yaml."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing config files. Defaults to repo root.
        """
        if config_dir is None:
            # Default to repo root (parent of comfygen package)
            config_dir = Path(__file__).parent.parent
        
        self.config_dir = config_dir
        self.presets_path = config_dir / "presets.yaml"
        self.lora_catalog_path = config_dir / "lora_catalog.yaml"
        
        # Cache loaded configs
        self._presets_cache = None
        self._lora_catalog_cache = None
    
    def load_presets(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load generation presets from presets.yaml.
        
        Args:
            force_reload: Force reload from disk even if cached
            
        Returns:
            Dictionary with full presets.yaml content including:
            - presets: Dict of preset configurations
            - default_negative_prompt: Default negative prompt string
            - validation: Validation settings
            - negative_prompts: Subject-specific negative prompts
            - positive_emphasis: Positive prompt helpers
        """
        if self._presets_cache is not None and not force_reload:
            return self._presets_cache
        
        if not self.presets_path.exists():
            self._presets_cache = {
                "presets": {},
                "default_negative_prompt": "",
                "validation": {},
                "negative_prompts": {},
                "positive_emphasis": {}
            }
            return self._presets_cache
        
        try:
            with open(self.presets_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            self._presets_cache = {
                "presets": data.get("presets", {}),
                "default_negative_prompt": data.get("default_negative_prompt", ""),
                "validation": data.get("validation", {}),
                "negative_prompts": data.get("negative_prompts", {}),
                "positive_emphasis": data.get("positive_emphasis", {})
            }
            return self._presets_cache
            
        except Exception as e:
            print(f"[ERROR] Failed to load presets.yaml: {e}")
            self._presets_cache = {
                "presets": {},
                "default_negative_prompt": "",
                "validation": {},
                "negative_prompts": {},
                "positive_emphasis": {}
            }
            return self._presets_cache
    
    def get_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset configuration.
        
        Args:
            preset_name: Name of preset (draft, balanced, high-quality, etc.)
            
        Returns:
            Preset configuration dict or None if not found
        """
        presets_data = self.load_presets()
        return presets_data.get("presets", {}).get(preset_name)
    
    def get_default_negative_prompt(self) -> str:
        """Get the default negative prompt.
        
        Returns:
            Default negative prompt string
        """
        presets_data = self.load_presets()
        return presets_data.get("default_negative_prompt", "")
    
    def get_validation_settings(self) -> Dict[str, Any]:
        """Get validation settings.
        
        Returns:
            Validation configuration dict
        """
        presets_data = self.load_presets()
        return presets_data.get("validation", {})
    
    def load_lora_catalog(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load LoRA catalog from lora_catalog.yaml.
        
        Args:
            force_reload: Force reload from disk even if cached
            
        Returns:
            Dictionary with:
            - loras: List of LoRA metadata
            - model_suggestions: Dict of predefined scenarios
            - keyword_mappings: Keyword to tag mappings
        """
        if self._lora_catalog_cache is not None and not force_reload:
            return self._lora_catalog_cache
        
        if not self.lora_catalog_path.exists():
            self._lora_catalog_cache = {
                "loras": [],
                "model_suggestions": {},
                "keyword_mappings": {}
            }
            return self._lora_catalog_cache
        
        try:
            with open(self.lora_catalog_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            self._lora_catalog_cache = {
                "loras": data.get("loras", []),
                "model_suggestions": data.get("model_suggestions", {}),
                "keyword_mappings": data.get("keyword_mappings", {})
            }
            return self._lora_catalog_cache
            
        except Exception as e:
            print(f"[ERROR] Failed to load lora_catalog.yaml: {e}")
            self._lora_catalog_cache = {
                "loras": [],
                "model_suggestions": {},
                "keyword_mappings": {}
            }
            return self._lora_catalog_cache
    
    def get_lora_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific LoRA preset from model_suggestions.
        
        Args:
            preset_name: Name of preset (text_to_video, simple_image, etc.)
            
        Returns:
            LoRA preset configuration or None if not found
        """
        catalog = self.load_lora_catalog()
        return catalog.get("model_suggestions", {}).get(preset_name)


# Global instance for easy import
_global_config_loader = None


def get_config_loader() -> ConfigLoader:
    """Get or create global ConfigLoader instance.
    
    Returns:
        Global ConfigLoader instance
    """
    global _global_config_loader
    if _global_config_loader is None:
        _global_config_loader = ConfigLoader()
    return _global_config_loader
