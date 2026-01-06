"""Model registry and recommendation system."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ModelRegistry:
    """Model registry for managing and recommending models."""

    def __init__(self, lora_catalog_path: Optional[str] = None):
        """Initialize model registry.

        Args:
            lora_catalog_path: Path to lora_catalog.yaml
        """
        if lora_catalog_path:
            self.catalog_path = Path(lora_catalog_path)
        else:
            self.catalog_path = Path(__file__).parent.parent / "lora_catalog.yaml"

        self.catalog = self._load_catalog()

    def _load_catalog(self) -> Dict[str, Any]:
        """Load LoRA catalog from YAML file.

        Returns:
            Catalog dictionary
        """
        if not self.catalog_path.exists():
            return {"loras": [], "model_suggestions": {}, "keyword_mappings": {}}

        try:
            with open(self.catalog_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {"loras": [], "model_suggestions": {}, "keyword_mappings": {}}

    def suggest_model(self, task: str, style: Optional[str] = None, subject: Optional[str] = None) -> Dict[str, Any]:
        """Suggest best model for a task.

        Args:
            task: Task type (portrait, landscape, anime, video, etc.)
            style: Optional style preference
            subject: Optional subject matter

        Returns:
            Dictionary with recommended model and alternatives
        """
        task_lower = task.lower()

        # Default recommendations based on task
        recommendations = {
            "portrait": {
                "recommended": "v1-5-pruned-emaonly-fp16.safetensors",
                "alternatives": ["flux-dev", "sdxl_base"],
                "reason": "SD 1.5 is fast and good for photorealistic portraits",
            },
            "landscape": {
                "recommended": "v1-5-pruned-emaonly-fp16.safetensors",
                "alternatives": ["flux-dev"],
                "reason": "SD 1.5 works well for landscape generation",
            },
            "anime": {
                "recommended": "v1-5-pruned-emaonly-fp16.safetensors",
                "alternatives": [],
                "reason": "SD 1.5 with anime LoRAs produces good results",
            },
            "video": {
                "recommended": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                "alternatives": ["wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
                "reason": "Wan 2.2 is the primary video generation model",
            },
            "text-to-video": {
                "recommended": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
                "alternatives": ["wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors"],
                "reason": "Wan 2.2 T2V for text-to-video generation",
            },
            "image-to-video": {
                "recommended": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                "alternatives": ["wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"],
                "reason": "Wan 2.2 I2V for animating images",
            },
        }

        # Check catalog for custom suggestions
        catalog_suggestions = self.catalog.get("model_suggestions", {})
        if task_lower in catalog_suggestions:
            return catalog_suggestions[task_lower]

        # Return default recommendation
        return recommendations.get(
            task_lower,
            {
                "recommended": "v1-5-pruned-emaonly-fp16.safetensors",
                "alternatives": [],
                "reason": "General purpose SD 1.5 model",
            },
        )

    def suggest_loras(self, prompt: str, model: str, max_suggestions: int = 3) -> List[Dict[str, Any]]:
        """Suggest LoRAs based on prompt and model.

        Args:
            prompt: Generation prompt
            model: Model being used
            max_suggestions: Maximum number of suggestions

        Returns:
            List of LoRA suggestions with metadata
        """
        suggestions = []
        prompt_lower = prompt.lower()
        model_lower = model.lower()

        loras = self.catalog.get("loras", [])

        for lora in loras:
            # Check if LoRA is compatible with model
            compatible_models = lora.get("compatible_with", [])
            if compatible_models:
                # Check if model matches any compatible model pattern
                is_compatible = any(
                    comp.lower() in model_lower or model_lower in comp.lower() for comp in compatible_models
                )
                if not is_compatible:
                    continue

            # Calculate relevance score based on tags and use cases
            score = 0
            matched_reasons = []

            # Check tags
            tags = lora.get("tags", [])
            for tag in tags:
                if tag.lower() in prompt_lower:
                    score += 2
                    matched_reasons.append(f"matches '{tag}' in prompt")

            # Check use cases
            use_cases = lora.get("use_cases", [])
            for use_case in use_cases:
                if use_case.lower() in prompt_lower:
                    score += 3
                    matched_reasons.append(f"useful for '{use_case}'")

            # Special handling for acceleration LoRAs - always suggest for video
            if "acceleration" in tags and "wan" in model_lower:
                score += 5
                matched_reasons.append("accelerates video generation")

            if score > 0:
                suggestions.append(
                    {
                        "name": lora.get("filename"),
                        "suggested_strength": lora.get("recommended_strength", 1.0),
                        "reason": lora.get("description"),
                        "score": score,
                        "matched_reasons": matched_reasons,
                    }
                )

        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:max_suggestions]

    def get_lora_info(self, lora_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific LoRA.

        Args:
            lora_name: LoRA filename

        Returns:
            LoRA metadata or None if not found
        """
        loras = self.catalog.get("loras", [])

        for lora in loras:
            if lora.get("filename") == lora_name:
                return lora

        return None

    def is_lora_compatible(self, lora_name: str, model: str) -> bool:
        """Check if a LoRA is compatible with a model.

        Args:
            lora_name: LoRA filename
            model: Model filename

        Returns:
            True if compatible, False otherwise
        """
        lora_info = self.get_lora_info(lora_name)
        if not lora_info:
            return True  # Assume compatible if not in catalog

        compatible_models = lora_info.get("compatible_with", [])
        if not compatible_models:
            return True  # No restrictions

        model_lower = model.lower()
        return any(comp.lower() in model_lower or model_lower in comp.lower() for comp in compatible_models)

    def get_default_negative_prompt(self, model_type: str = "sd15") -> str:
        """Get default negative prompt for model type.

        Args:
            model_type: Model type (sd15, sdxl, flux, wan, etc.)

        Returns:
            Default negative prompt string
        """
        negative_prompts = {
            "sd15": "bad quality, blurry, low resolution, watermark, text, deformed, ugly, duplicate",
            "sdxl": "bad quality, blurry, low resolution, watermark, text, deformed",
            "flux": "blurry, low quality, distorted",
            "wan": "static, blurry, watermark, low quality",
            "default": "blurry, low quality, watermark",
        }

        return negative_prompts.get(model_type, negative_prompts["default"])
