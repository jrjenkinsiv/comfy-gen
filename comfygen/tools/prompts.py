"""Prompt engineering and analysis MCP tools."""

from typing import Any, Dict, List, Optional

# Lazy initialization
_model_registry = None


def _get_model_registry():
    """Get or create Model registry."""
    global _model_registry
    if _model_registry is None:
        from comfygen.models import ModelRegistry

        _model_registry = ModelRegistry()
    return _model_registry


async def build_prompt(
    subject: str,
    style: Optional[str] = None,
    setting: Optional[str] = None,
    details: Optional[List[str]] = None,
    emphasis: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Construct a weighted prompt from components.

    Args:
        subject: Main subject of the image
        style: Art style or aesthetic
        setting: Scene or environment
        details: Additional details to include
        emphasis: Dict mapping terms to weight multipliers (e.g., {"detailed": 1.2})

    Returns:
        Dictionary with constructed prompt
    """
    try:
        parts = []

        # Add subject
        if subject:
            parts.append(subject)

        # Add style
        if style:
            parts.append(style)

        # Add setting
        if setting:
            parts.append(setting)

        # Add details
        if details:
            parts.extend(details)

        # Build basic prompt
        prompt = ", ".join(parts)

        # Apply emphasis weights using ComfyUI syntax (word:weight)
        if emphasis:
            for term, weight in emphasis.items():
                if weight != 1.0:
                    prompt = prompt.replace(term, f"({term}:{weight:.2f})")

        return {
            "status": "success",
            "prompt": prompt,
            "components": {
                "subject": subject,
                "style": style,
                "setting": setting,
                "details": details,
                "emphasis": emphasis,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def suggest_negative(model_type: str = "sd15") -> Dict[str, Any]:
    """Get recommended negative prompt for model type.

    Args:
        model_type: Model type (sd15, sdxl, flux, wan)

    Returns:
        Dictionary with negative prompt suggestion
    """
    try:
        negative_prompt = _get_model_registry().get_default_negative_prompt(model_type)

        # Additional context-specific suggestions
        suggestions_by_type = {
            "sd15": {
                "general": "bad quality, blurry, low resolution, watermark, text, deformed, ugly, duplicate",
                "portrait": "bad quality, blurry, deformed face, asymmetrical eyes, ugly, disfigured",
                "landscape": "bad quality, blurry, distorted perspective, unrealistic lighting",
                "anime": "bad quality, blurry, bad anatomy, extra limbs, mutation",
            },
            "sdxl": {
                "general": "bad quality, blurry, low resolution, watermark, text, deformed",
                "portrait": "bad quality, deformed face, asymmetrical, disfigured",
                "landscape": "bad quality, blurry, distorted, unrealistic",
            },
            "flux": {
                "general": "blurry, low quality, distorted",
                "portrait": "blurry, deformed, asymmetrical",
                "landscape": "blurry, distorted, unrealistic",
            },
            "wan": {
                "general": "static, blurry, watermark, low quality",
                "video": "static, no movement, frozen, blurry, low framerate",
            },
        }

        context_suggestions = suggestions_by_type.get(model_type, suggestions_by_type["sd15"])

        return {
            "status": "success",
            "default": negative_prompt,
            "suggestions": context_suggestions,
            "model_type": model_type,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def analyze_prompt(prompt: str) -> Dict[str, Any]:
    """Analyze prompt and suggest improvements.

    Args:
        prompt: Prompt to analyze

    Returns:
        Dictionary with analysis and suggestions
    """
    try:
        analysis = {
            "length": len(prompt),
            "word_count": len(prompt.split()),
            "issues": [],
            "suggestions": [],
            "detected_elements": [],
        }

        prompt_lower = prompt.lower()

        # Check for common issues
        if len(prompt) < 10:
            analysis["issues"].append("Prompt is very short - add more details for better results")
            analysis["suggestions"].append("Add descriptive adjectives and specify the style")

        if len(prompt) > 500:
            analysis["issues"].append("Prompt is very long - may not all be used effectively")
            analysis["suggestions"].append("Focus on the most important elements")

        # Detect prompt elements
        style_keywords = [
            "photorealistic",
            "anime",
            "painting",
            "sketch",
            "3d render",
            "cartoon",
            "oil painting",
            "watercolor",
        ]
        for keyword in style_keywords:
            if keyword in prompt_lower:
                analysis["detected_elements"].append(f"Style: {keyword}")

        quality_keywords = ["detailed", "high quality", "8k", "4k", "masterpiece", "professional"]
        has_quality = any(kw in prompt_lower for kw in quality_keywords)
        if not has_quality:
            analysis["suggestions"].append("Consider adding quality modifiers like 'detailed', 'high quality', or '8k'")
        else:
            for keyword in quality_keywords:
                if keyword in prompt_lower:
                    analysis["detected_elements"].append(f"Quality: {keyword}")

        # Check for negative keywords in positive prompt
        negative_keywords = ["bad", "ugly", "blurry", "low quality", "worst"]
        for keyword in negative_keywords:
            if keyword in prompt_lower:
                analysis["issues"].append(f"Negative keyword '{keyword}' found in prompt - move to negative prompt")

        # Detect subject matter
        subject_keywords = {
            "portrait": ["portrait", "face", "headshot", "person", "woman", "man"],
            "landscape": ["landscape", "scenery", "mountains", "forest", "ocean", "sky"],
            "object": ["object", "product", "item"],
            "animal": ["animal", "cat", "dog", "bird", "wildlife"],
        }

        for category, keywords in subject_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                analysis["detected_elements"].append(f"Subject: {category}")

        # Suggestions based on detected elements
        if not analysis["detected_elements"]:
            analysis["suggestions"].append("Specify what you want to generate (subject, style, setting)")

        return {"status": "success", "analysis": analysis, "prompt": prompt}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def expand_prompt(
    base_prompt: str,
    add_quality: bool = True,
    add_style: Optional[str] = None,
    add_lighting: bool = False,
) -> Dict[str, Any]:
    """Expand a basic prompt with enhancements.

    Args:
        base_prompt: Base prompt to expand
        add_quality: Add quality modifiers
        add_style: Add specific style (e.g., "cinematic", "photorealistic")
        add_lighting: Add lighting descriptions

    Returns:
        Dictionary with expanded prompt
    """
    try:
        parts = [base_prompt]

        if add_quality:
            parts.append("highly detailed, high quality, 8k resolution")

        if add_style:
            parts.append(add_style)

        if add_lighting:
            parts.append("professional lighting, dramatic shadows")

        expanded = ", ".join(parts)

        return {
            "status": "success",
            "original": base_prompt,
            "expanded": expanded,
            "additions": {"quality": add_quality, "style": add_style, "lighting": add_lighting},
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
