"""Model management and discovery MCP tools."""

import os
from typing import Any, Dict, Optional

# Lazy initialization of clients
_comfyui = None
_civitai = None
_model_registry = None


def _get_comfyui():
    """Get or create ComfyUI client."""
    global _comfyui
    if _comfyui is None:
        from comfygen.comfyui_client import ComfyUIClient

        _comfyui = ComfyUIClient(host=os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188"))
    return _comfyui


def _get_civitai():
    """Get or create CivitAI client."""
    global _civitai
    if _civitai is None:
        from comfygen.civitai_client import CivitAIClient

        _civitai = CivitAIClient(api_key=os.getenv("CIVITAI_API_KEY"))
    return _civitai


def _get_model_registry():
    """Get or create Model registry."""
    global _model_registry
    if _model_registry is None:
        from comfygen.models import ModelRegistry

        _model_registry = ModelRegistry()
    return _model_registry


async def list_models() -> Dict[str, Any]:
    """List installed checkpoint models.

    Returns:
        Dictionary with list of installed models
    """
    try:
        models = _get_comfyui().get_available_models()
        if not models:
            return {"status": "error", "error": "Failed to retrieve models from ComfyUI"}

        return {
            "status": "success",
            "checkpoints": models.get("checkpoints", []),
            "diffusion_models": models.get("diffusion_models", []),
            "vae": models.get("vae", []),
            "count": len(models.get("checkpoints", [])),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def list_loras() -> Dict[str, Any]:
    """List installed LoRAs with compatibility info.

    Returns:
        Dictionary with list of installed LoRAs
    """
    try:
        models = _get_comfyui().get_available_models()
        if not models:
            return {"status": "error", "error": "Failed to retrieve LoRAs from ComfyUI"}

        loras_list = models.get("loras", [])

        # Enrich with metadata from catalog
        enriched_loras = []
        for lora_name in loras_list:
            lora_info = _get_model_registry().get_lora_info(lora_name)
            if lora_info:
                enriched_loras.append(
                    {
                        "name": lora_name,
                        "tags": lora_info.get("tags", []),
                        "compatible_with": lora_info.get("compatible_with", []),
                        "recommended_strength": lora_info.get("recommended_strength", 1.0),
                        "description": lora_info.get("description", ""),
                    }
                )
            else:
                # LoRA not in catalog
                enriched_loras.append(
                    {
                        "name": lora_name,
                        "tags": [],
                        "compatible_with": [],
                        "recommended_strength": 1.0,
                        "description": "No catalog entry",
                    }
                )

        return {"status": "success", "loras": enriched_loras, "count": len(enriched_loras)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_model_info(model_name: str) -> Dict[str, Any]:
    """Get detailed metadata about a model.

    Args:
        model_name: Model filename

    Returns:
        Dictionary with model metadata
    """
    try:
        models = _get_comfyui().get_available_models()
        if not models:
            return {"status": "error", "error": "Failed to retrieve models from ComfyUI"}

        # Check if model exists
        all_models = (
            models.get("checkpoints", [])
            + models.get("diffusion_models", [])
            + models.get("loras", [])
            + models.get("vae", [])
        )

        if model_name not in all_models:
            return {"status": "error", "error": f"Model not found: {model_name}"}

        # Determine model type
        model_type = "unknown"
        if model_name in models.get("checkpoints", []):
            model_type = "checkpoint"
        elif model_name in models.get("diffusion_models", []):
            model_type = "diffusion_model"
        elif model_name in models.get("loras", []):
            model_type = "lora"
        elif model_name in models.get("vae", []):
            model_type = "vae"

        # Get additional info from catalog if it's a LoRA
        catalog_info = {}
        if model_type == "lora":
            lora_info = _get_model_registry().get_lora_info(model_name)
            if lora_info:
                catalog_info = lora_info

        return {"status": "success", "name": model_name, "type": model_type, **catalog_info}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def suggest_model(
    task: str,
    style: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Recommend best model for a task.

    Args:
        task: Task type (portrait, landscape, anime, video, etc.)
        style: Optional style preference
        subject: Optional subject matter

    Returns:
        Dictionary with model recommendation
    """
    try:
        suggestion = _get_model_registry().suggest_model(task, style, subject)
        return {"status": "success", **suggestion}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def suggest_loras(
    prompt: str,
    model: str,
    max_suggestions: int = 3,
) -> Dict[str, Any]:
    """Recommend LoRAs based on prompt content.

    Args:
        prompt: Generation prompt
        model: Model being used
        max_suggestions: Maximum number of suggestions

    Returns:
        Dictionary with LoRA suggestions
    """
    try:
        suggestions = _get_model_registry().suggest_loras(prompt, model, max_suggestions)
        return {"status": "success", "suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def search_civitai(
    query: str,
    model_type: str = "all",
    base_model: Optional[str] = None,
    sort: str = "Most Downloaded",
    nsfw: bool = True,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search CivitAI for models.

    Args:
        query: Search query
        model_type: Filter by type (checkpoint, lora, vae, etc.)
        base_model: Filter by base model (SD 1.5, SDXL, etc.)
        sort: Sort method (Most Downloaded, Highest Rated, Newest)
        nsfw: Include NSFW results
        limit: Maximum results

    Returns:
        Dictionary with search results
    """
    try:
        # Normalize model_type
        type_param = None if model_type == "all" else model_type

        results = _get_civitai().search_models(
            query=query, model_type=type_param, base_model=base_model, sort=sort, nsfw=nsfw, limit=limit
        )

        return {"status": "success", "results": results, "count": len(results)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_civitai_model(model_id: int) -> Dict[str, Any]:
    """Get detailed info about a CivitAI model.

    Args:
        model_id: CivitAI model ID

    Returns:
        Dictionary with model details
    """
    try:
        model = _get_civitai().get_model(model_id)
        if not model:
            return {"status": "error", "error": f"Model not found: {model_id}"}

        return {"status": "success", "model": model}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def download_model(
    civitai_id: int,
    version_id: Optional[int] = None,
    destination: str = "auto",
) -> Dict[str, Any]:
    """Download model from CivitAI to moira.

    Args:
        civitai_id: CivitAI model ID
        version_id: Optional specific version ID (latest if None)
        destination: Destination directory (auto-detect from type)

    Returns:
        Dictionary with download status
    """
    try:
        # Get model info
        model = _get_civitai().get_model(civitai_id)
        if not model:
            return {"status": "error", "error": f"Model not found: {civitai_id}"}

        # Get download URL
        download_url = _get_civitai().get_download_url(civitai_id, version_id)
        if not download_url:
            return {"status": "error", "error": "Failed to get download URL"}

        # TODO: Implement actual download to moira
        # This would require SSH access or a download endpoint on moira

        return {"status": "error", "error": "Model download not yet fully implemented - requires moira access"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_download_progress(download_id: str) -> Dict[str, Any]:
    """Check download progress.

    Args:
        download_id: Download ID from download_model

    Returns:
        Dictionary with progress info
    """
    return {"status": "error", "error": "Download progress tracking not yet implemented"}
