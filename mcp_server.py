#!/usr/bin/env python3
"""Comprehensive MCP Server for ComfyUI Image/Video Generation.

This server exposes tools for:

Core Generation:
- Image generation (generate_image, img2img)
- Video generation (generate_video, image_to_video)

Intelligent Composition:
- compose_recipe: Parse natural language + @tags into generation recipes
- list_categories: Discover available generation categories

Model Management:
- list_models, list_loras, get_model_info
- suggest_model, suggest_loras
- search_civitai (model discovery)

Gallery & History:
- list_images, get_image_info, delete_image, get_history

Prompt Engineering:
- build_prompt, suggest_negative, analyze_prompt

Progress & Control:
- get_progress, cancel, get_queue, get_system_status

Service Management:
- start, stop, restart, check ComfyUI server status

Advanced features (pending custom workflows):
- Inpainting, upscaling, face restoration

Run this server to allow MCP clients (like Claude Desktop) to generate images/videos.
"""

import os
import sys
from pathlib import Path
from typing import Literal, Optional

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

import check_comfyui_status  # noqa: E402
import restart_comfyui  # noqa: E402

# Import our service management scripts
import start_comfyui  # noqa: E402
import stop_comfyui  # noqa: E402
from mcp.server import FastMCP  # noqa: E402

# Import typed API client for compose/category operations
from comfy_gen.client import ComfyGenClient, ComfyGenError  # noqa: E402

# Import config loader
from comfygen.config import get_config_loader  # noqa: E402

# Import generation tools
from comfygen.tools import control, gallery, generation, models, prompts, video  # noqa: E402

# Initialize FastMCP server
mcp = FastMCP("ComfyUI Comprehensive Generation Server")

# Lazy-loaded configuration (loaded on first use)
config_loader = None
presets_config = None
lora_catalog = None

# Lazy-loaded API client
_api_client: Optional[ComfyGenClient] = None


def _get_api_client() -> ComfyGenClient:
    """Get or create the typed API client instance."""
    global _api_client
    if _api_client is None:
        api_url = os.environ.get("COMFYGEN_API_URL", "http://localhost:8000")
        _api_client = ComfyGenClient(base_url=api_url, timeout=60.0)
    return _api_client


def _ensure_config_loaded():
    """Ensure configuration is loaded (lazy loading)."""
    global config_loader, presets_config, lora_catalog
    if config_loader is None:
        config_loader = get_config_loader()
        presets_config = config_loader.load_presets()
        lora_catalog = config_loader.load_lora_catalog()

        # Log loaded configuration
        print(f"[OK] Loaded {len(presets_config.get('presets', {}))} generation presets")
        print(f"[OK] Loaded {len(lora_catalog.get('loras', []))} LoRAs from catalog")
        print(f"[OK] Default negative prompt: {presets_config.get('default_negative_prompt', 'none')[:50]}...")
        print(f"[OK] Validation enabled: {presets_config.get('validation', {}).get('enabled', False)}")


@mcp.tool()
def start_comfyui_service() -> str:
    """Start the ComfyUI server on moira.

    This tool starts ComfyUI as a background process. The server will be
    available at http://192.168.1.215:8188.

    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = start_comfyui.main()
        if result == 0:
            return "ComfyUI started successfully. API available at http://192.168.1.215:8188"
        else:
            return "Failed to start ComfyUI. Check logs for details."
    except Exception as e:
        return f"Error starting ComfyUI: {str(e)}"


@mcp.tool()
def stop_comfyui_service() -> str:
    """Stop the ComfyUI server on moira.

    This tool terminates the running ComfyUI process.

    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = stop_comfyui.stop_comfyui()
        if result == 0:
            return "ComfyUI stopped successfully"
        else:
            return "Failed to stop ComfyUI or ComfyUI was not running"
    except Exception as e:
        return f"Error stopping ComfyUI: {str(e)}"


@mcp.tool()
def restart_comfyui_service() -> str:
    """Restart the ComfyUI server on moira.

    This tool stops and then starts the ComfyUI process, useful for
    applying configuration changes or recovering from errors.

    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = restart_comfyui.restart_comfyui()
        if result == 0:
            return "ComfyUI restarted successfully. API available at http://192.168.1.215:8188"
        else:
            return "Failed to restart ComfyUI. Check logs for details."
    except Exception as e:
        return f"Error restarting ComfyUI: {str(e)}"


@mcp.tool()
def check_comfyui_service_status() -> str:
    """Check the status of the ComfyUI server.

    This tool checks if ComfyUI process is running and if the API is responding.

    Returns:
        str: Status report including process state and API health
    """
    try:
        # Capture output from check_status
        import contextlib
        import io

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            check_comfyui_status.check_status()

        output = f.getvalue()
        return output
    except Exception as e:
        return f"Error checking ComfyUI status: {str(e)}"


# ============================================================================
# IMAGE GENERATION TOOLS
# ============================================================================


@mcp.tool()
async def generate_image(
    prompt: str,
    negative_prompt: str = None,
    model: str = "sd15",
    width: int = 512,
    height: int = 512,
    steps: int = None,
    cfg: float = None,
    sampler: str = None,
    scheduler: str = None,
    seed: int = -1,
    preset: str = None,
    lora_preset: str = None,
    transparent: bool = False,
    output_path: str = None,
    json_progress: bool = False,
    validate: bool = None,
    auto_retry: bool = None,
    retry_limit: int = None,
    positive_threshold: float = None,
) -> dict:
    """Generate image from text prompt with optional CLIP validation.

    Args:
        prompt: Positive text prompt describing what to generate
        negative_prompt: Negative prompt (what to avoid). If None, uses default from presets.yaml.
                        Set to empty string "" to disable negative prompt.
        model: Model to use (sd15, flux, sdxl)
        width: Output width in pixels (default: 512)
        height: Output height in pixels (default: 512)
        steps: Number of sampling steps. If None, uses preset or default (20)
        cfg: CFG scale. If None, uses preset or default (7.0)
        sampler: Sampler algorithm. If None, uses preset or default (euler)
        scheduler: Scheduler type. If None, uses preset or default (normal)
        seed: Random seed, -1 for random (default: -1)
        preset: Generation preset (draft, balanced, high-quality, fast, ultra). Overrides steps/cfg/sampler/scheduler
        lora_preset: LoRA preset name from lora_catalog.yaml model_suggestions
                    (e.g., text_to_video, simple_image, battleship_ship_icon)
        transparent: Generate image with transparent background (requires SAM model)
        output_path: Optional local file path to save the generated image (in addition to MinIO)
        json_progress: If True, returns progress updates as structured JSON instead of text (default: False)
        validate: Run CLIP validation after generation. If None, uses preset or config default
        auto_retry: Automatically retry if validation fails. If None, uses preset or config default
        retry_limit: Maximum retry attempts. If None, uses preset or config default (3)
        positive_threshold: Minimum CLIP score for positive prompt. If None, uses preset or config default (0.25)

    Returns:
        Dictionary with status, url, local_path (if output_path provided), generation metadata,
        validation results, and progress_updates (if json_progress=True)
    """
    # Ensure config is loaded
    _ensure_config_loaded()

    # Load preset if specified
    preset_params = {}
    if preset:
        preset_params = config_loader.get_preset(preset) or {}
        if not preset_params:
            return {
                "status": "error",
                "error": f"Preset '{preset}' not found. Available: {', '.join(presets_config.get('presets', {}).keys())}",
            }

    # Load LoRA preset if specified
    loras = None
    if lora_preset:
        lora_preset_data = config_loader.get_lora_preset(lora_preset)
        if lora_preset_data:
            default_loras = lora_preset_data.get("default_loras", [])
            if default_loras:
                # Convert LoRA filenames to format expected by generate_image
                loras = []
                for lora_filename in default_loras:
                    # Find LoRA details in catalog
                    lora_info = None
                    for lora in lora_catalog.get("loras", []):
                        if lora.get("filename") == lora_filename:
                            lora_info = lora
                            break

                    strength = lora_info.get("recommended_strength", 1.0) if lora_info else 1.0
                    loras.append({"name": lora_filename, "strength": strength})
        else:
            available_presets = ", ".join(lora_catalog.get("model_suggestions", {}).keys())
            return {
                "status": "error",
                "error": f"LoRA preset '{lora_preset}' not found in model_suggestions. Available LoRA presets: {available_presets}",
            }

    # Apply defaults from config and preset (CLI args > preset > config defaults)
    validation_config = presets_config.get("validation", {})

    # Use default negative prompt if not provided (None)
    # Empty string "" means explicitly no negative prompt
    if negative_prompt is None:
        negative_prompt = presets_config.get("default_negative_prompt", "blurry, low quality, watermark")

    # Merge preset and config defaults
    final_steps = steps if steps is not None else preset_params.get("steps", 20)
    final_cfg = cfg if cfg is not None else preset_params.get("cfg", 7.0)
    final_sampler = sampler if sampler is not None else preset_params.get("sampler", "euler")
    final_scheduler = scheduler if scheduler is not None else preset_params.get("scheduler", "normal")
    final_validate = (
        validate if validate is not None else preset_params.get("validate", validation_config.get("enabled", True))
    )
    final_auto_retry = (
        auto_retry
        if auto_retry is not None
        else preset_params.get("auto_retry", validation_config.get("auto_retry", True))
    )
    final_retry_limit = (
        retry_limit
        if retry_limit is not None
        else preset_params.get("retry_limit", validation_config.get("retry_limit", 3))
    )
    final_positive_threshold = (
        positive_threshold
        if positive_threshold is not None
        else preset_params.get("positive_threshold", validation_config.get("positive_threshold", 0.25))
    )

    # Set up progress callback if json_progress is enabled
    progress_updates = []
    progress_callback = None

    if json_progress:

        def capture_progress(update: dict):
            """Capture progress updates for JSON output."""
            progress_updates.append(update)

        progress_callback = capture_progress

    result = await generation.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model,
        width=width,
        height=height,
        steps=final_steps,
        cfg=final_cfg,
        sampler=final_sampler,
        scheduler=final_scheduler,
        seed=seed,
        loras=loras,
        transparent=transparent,
        output_path=output_path,
        progress_callback=progress_callback,
        validate=final_validate,
        auto_retry=final_auto_retry,
        retry_limit=final_retry_limit,
        positive_threshold=final_positive_threshold,
    )

    # Add progress updates to result if json_progress was enabled
    if json_progress and progress_updates:
        result["progress_updates"] = progress_updates

    return result


@mcp.tool()
async def img2img(
    input_image: str,
    prompt: str,
    negative_prompt: str = "",
    denoise: float = 0.7,
    model: str = "sd15",
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = -1,
) -> dict:
    """Transform existing image with prompt guidance.

    Args:
        input_image: URL or path to input image
        prompt: Positive text prompt for transformation
        negative_prompt: Negative prompt
        denoise: Denoise strength 0.0-1.0 (lower preserves more original, default: 0.7)
        model: Model to use (default: sd15)
        steps: Number of sampling steps (default: 20)
        cfg: CFG scale (default: 7.0)
        seed: Random seed, -1 for random (default: -1)

    Returns:
        Dictionary with status, url, and generation metadata
    """
    return await generation.img2img(
        input_image=input_image,
        prompt=prompt,
        negative_prompt=negative_prompt,
        denoise=denoise,
        model=model,
        steps=steps,
        cfg=cfg,
        seed=seed,
    )


# ============================================================================
# INTELLIGENT COMPOSITION TOOLS (via API Client)
# ============================================================================


@mcp.tool()
async def compose_recipe(
    input_text: str,
    dry_run: bool = True,
    max_categories: int = 3,
    min_confidence: float = 0.3,
    policy_tier: Literal["general", "mature", "explicit"] = "general",
) -> dict:
    """Compose categories into a generation recipe with full explainability.

    This tool parses natural language input (with optional @tags) and composes
    a generation recipe by selecting appropriate categories, prompts, and settings.
    Returns detailed explanation of how the recipe was composed.

    Args:
        input_text: User input with optional @tags (e.g., "@portrait @outdoor professional headshot")
        dry_run: If True, returns recipe without executing generation (default: True)
        max_categories: Maximum number of categories to include (1-10, default: 3)
        min_confidence: Minimum confidence for inferred categories (0.0-1.0, default: 0.3)
        policy_tier: Content policy tier - general, mature, or explicit (default: general)

    Returns:
        Dictionary with:
        - recipe: The composed generation recipe with prompts, settings, LoRAs
        - explanation: Detailed breakdown of how recipe was composed including:
            - summary: Human-readable summary
            - explicit_tags: @tags found in input
            - inferred_categories: Categories inferred from keywords with confidence scores
            - remaining_prompt: User text after @tag extraction
            - final_categories: Category IDs used in composition
            - steps: Detailed composition steps for provenance
            - warnings: Non-fatal issues during composition
            - suggestions: Suggestions for improving results
        - dry_run: Whether this was a dry run

    Example:
        compose_recipe("@portrait professional headshot natural lighting")
        -> Returns recipe with portrait category settings, prompts for professional headshot,
           and explanation of why portrait was selected and how prompts were composed.
    """
    try:
        client = _get_api_client()
        response = client.compose(
            input_text=input_text,
            dry_run=dry_run,
            max_categories=max_categories,
            min_confidence=min_confidence,
            policy_tier=policy_tier,
        )

        # Convert to dict for MCP response
        return {
            "status": "success",
            "recipe": response.recipe,
            "explanation": {
                "summary": response.explanation.summary,
                "explicit_tags": response.explanation.explicit_tags,
                "inferred_categories": response.explanation.inferred_categories,
                "remaining_prompt": response.explanation.remaining_prompt,
                "final_categories": response.explanation.final_categories,
                "steps": [
                    {
                        "phase": step.phase,
                        "action": step.action,
                        "detail": step.detail,
                        "source": step.source,
                    }
                    for step in response.explanation.steps
                ],
                "warnings": response.explanation.warnings,
                "suggestions": response.explanation.suggestions,
            },
            "dry_run": response.dry_run,
        }
    except ComfyGenError as e:
        return {"status": "error", "error": str(e), "status_code": e.status_code}
    except Exception as e:
        return {"status": "error", "error": f"Failed to compose recipe: {str(e)}"}


@mcp.tool()
async def list_available_categories(
    category_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List available generation categories for intelligent composition.

    Categories define generation presets including prompts, LoRAs, and settings.
    Use these category IDs with @tags in compose_recipe (e.g., "@portrait").

    Args:
        category_type: Filter by type - subject, setting, modifier, or style (optional)
        page: Page number for pagination (default: 1)
        page_size: Items per page, 1-100 (default: 20)

    Returns:
        Dictionary with:
        - items: List of categories with id, type, display_name, description, keywords
        - total: Total number of categories matching filter
        - page: Current page number
        - page_size: Number of items per page

    Example:
        list_available_categories(category_type="subject")
        -> Returns subject categories like portrait, landscape, etc.
    """
    try:
        client = _get_api_client()
        # Map string to enum if provided
        cat_type = None
        if category_type:
            from comfy_gen.api.schemas.category import CategoryType

            try:
                cat_type = CategoryType(category_type)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid category type: {category_type}. Valid types: subject, setting, modifier, style",
                }

        response = client.list_categories(type=cat_type, page=page, page_size=page_size)
        return {"status": "success", **response}
    except ComfyGenError as e:
        return {"status": "error", "error": str(e), "status_code": e.status_code}
    except Exception as e:
        return {"status": "error", "error": f"Failed to list categories: {str(e)}"}


@mcp.tool()
async def search_available_categories(query: str) -> dict:
    """Search categories by keyword for intelligent composition.

    Searches across category names, descriptions, and keywords.
    Useful for discovering relevant categories when you're not sure
    which @tags to use.

    Args:
        query: Search keyword or phrase (minimum 2 characters)

    Returns:
        Dictionary with:
        - query: The search query
        - results: List of matching categories
        - count: Number of results

    Example:
        search_available_categories("portrait")
        -> Returns categories related to portraits, headshots, etc.
    """
    try:
        client = _get_api_client()
        response = client.search_categories(query)
        return {"status": "success", **response}
    except ComfyGenError as e:
        return {"status": "error", "error": str(e), "status_code": e.status_code}
    except Exception as e:
        return {"status": "error", "error": f"Failed to search categories: {str(e)}"}


@mcp.tool()
async def get_category_details(category_id: str) -> dict:
    """Get detailed information about a specific category.

    Returns full category details including prompts, LoRAs, settings,
    and composition rules. Use this to understand what a category
    will contribute to a generation recipe.

    Args:
        category_id: The category ID (e.g., "portrait", "night", "cinematic")

    Returns:
        Dictionary with full category details including:
        - id: Category identifier
        - type: Category type (subject, setting, modifier, style)
        - display_name: Human-friendly name
        - description: What the category is for
        - keywords: Primary and secondary keywords for inference
        - prompts: Positive and negative prompt additions
        - loras: LoRA configurations
        - settings: Generation settings overrides
        - composition: Composition rules (conflicts, requires, etc.)

    Example:
        get_category_details("portrait")
        -> Returns full portrait category with prompt templates, LoRA suggestions, etc.
    """
    try:
        client = _get_api_client()
        category = client.get_category(category_id)
        return {"status": "success", "category": category.model_dump()}
    except ComfyGenError as e:
        return {"status": "error", "error": str(e), "status_code": e.status_code}
    except Exception as e:
        return {"status": "error", "error": f"Failed to get category: {str(e)}"}


# ============================================================================
# VIDEO GENERATION TOOLS
# ============================================================================


@mcp.tool()
async def generate_video(
    prompt: str,
    negative_prompt: str = "static, blurry, watermark",
    width: int = 832,
    height: int = 480,
    frames: int = 81,
    fps: int = 16,
    steps: int = 30,
    cfg: float = 6.0,
    seed: int = -1,
) -> dict:
    """Generate video from text prompt using Wan 2.2 T2V.

    Args:
        prompt: Positive text prompt describing the video
        negative_prompt: Negative prompt (default: "static, blurry, watermark")
        width: Video width in pixels (default: 832)
        height: Video height in pixels (default: 480)
        frames: Number of frames, ~5 sec at 16fps = 81 frames (default: 81)
        fps: Frames per second (default: 16)
        steps: Number of sampling steps (default: 30)
        cfg: CFG scale (default: 6.0)
        seed: Random seed, -1 for random (default: -1)

    Returns:
        Dictionary with status, url, and generation metadata
    """
    return await video.generate_video(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        frames=frames,
        fps=fps,
        steps=steps,
        cfg=cfg,
        seed=seed,
    )


@mcp.tool()
async def image_to_video(
    input_image: str,
    prompt: str,
    negative_prompt: str = "",
    motion_strength: float = 1.0,
    frames: int = 81,
    fps: int = 16,
    steps: int = 30,
    seed: int = -1,
) -> dict:
    """Animate image to video using Wan 2.2 I2V.

    Args:
        input_image: URL or path to input image
        prompt: Positive text prompt describing desired motion
        negative_prompt: Negative prompt
        motion_strength: How much movement 0.0-1.0+ (default: 1.0)
        frames: Number of frames (default: 81)
        fps: Frames per second (default: 16)
        steps: Number of sampling steps (default: 30)
        seed: Random seed, -1 for random (default: -1)

    Returns:
        Dictionary with status, url, and generation metadata
    """
    return await video.image_to_video(
        input_image=input_image,
        prompt=prompt,
        negative_prompt=negative_prompt,
        motion_strength=motion_strength,
        frames=frames,
        fps=fps,
        steps=steps,
        seed=seed,
    )


# ============================================================================
# MODEL MANAGEMENT TOOLS
# ============================================================================


@mcp.tool()
async def list_models() -> dict:
    """List all installed checkpoint models.

    Returns:
        Dictionary with list of available models
    """
    return await models.list_models()


@mcp.tool()
async def list_loras() -> dict:
    """List all installed LoRAs with compatibility information.

    Returns:
        Dictionary with list of LoRAs and their metadata
    """
    return await models.list_loras()


@mcp.tool()
async def get_model_info(model_name: str) -> dict:
    """Get detailed information about a specific model.

    Args:
        model_name: Model filename

    Returns:
        Dictionary with model metadata
    """
    return await models.get_model_info(model_name)


@mcp.tool()
async def suggest_model(
    task: str,
    style: str = None,
    subject: str = None,
) -> dict:
    """Recommend best model for a task.

    Args:
        task: Task type (portrait, landscape, anime, video, text-to-video, image-to-video)
        style: Optional style preference
        subject: Optional subject matter

    Returns:
        Dictionary with recommended model and alternatives
    """
    return await models.suggest_model(task, style, subject)


@mcp.tool()
async def suggest_loras(
    prompt: str,
    model: str,
    max_suggestions: int = 3,
) -> dict:
    """Recommend LoRAs based on prompt content and model.

    Args:
        prompt: Generation prompt
        model: Model being used
        max_suggestions: Maximum number of suggestions (default: 3)

    Returns:
        Dictionary with LoRA suggestions
    """
    return await models.suggest_loras(prompt, model, max_suggestions)


@mcp.tool()
async def search_civitai(
    query: str,
    model_type: str = "all",
    base_model: str = None,
    sort: str = "Most Downloaded",
    nsfw: bool = True,
    limit: int = 10,
) -> dict:
    """Search CivitAI for models and LoRAs.

    Args:
        query: Search query
        model_type: Filter by type - all, checkpoint, lora, vae (default: all)
        base_model: Filter by base model - SD 1.5, SDXL, etc. (optional)
        sort: Sort method - Most Downloaded, Highest Rated, Newest (default: Most Downloaded)
        nsfw: Include NSFW results (default: True)
        limit: Maximum results (default: 10)

    Returns:
        Dictionary with search results
    """
    return await models.search_civitai(
        query=query, model_type=model_type, base_model=base_model, sort=sort, nsfw=nsfw, limit=limit
    )


# ============================================================================
# GALLERY & HISTORY TOOLS
# ============================================================================


@mcp.tool()
async def list_images(
    limit: int = 20,
    prefix: str = "",
    sort: str = "newest",
) -> dict:
    """Browse generated images from storage.

    Args:
        limit: Maximum number of images to return (default: 20)
        prefix: Filter by filename prefix (optional)
        sort: Sort order - newest, oldest, name (default: newest)

    Returns:
        Dictionary with list of images
    """
    return await gallery.list_images(limit, prefix, sort)


@mcp.tool()
async def get_image_info(image_name: str) -> dict:
    """Get generation parameters and metadata for an image.

    Args:
        image_name: Image filename in storage

    Returns:
        Dictionary with image metadata and generation parameters
    """
    return await gallery.get_image_info(image_name)


@mcp.tool()
async def delete_image(image_name: str) -> dict:
    """Remove image from storage.

    Args:
        image_name: Image filename to delete

    Returns:
        Dictionary with deletion status
    """
    return await gallery.delete_image(image_name)


@mcp.tool()
async def get_history(limit: int = 10) -> dict:
    """Get recent generations with full parameters.

    Args:
        limit: Maximum number of history entries (default: 10)

    Returns:
        Dictionary with generation history
    """
    return await gallery.get_history(limit)


# ============================================================================
# PROMPT ENGINEERING TOOLS
# ============================================================================


@mcp.tool()
async def build_prompt(
    subject: str,
    style: str = None,
    setting: str = None,
) -> dict:
    """Construct a well-formed prompt from components.

    Args:
        subject: Main subject of the image
        style: Art style or aesthetic (optional)
        setting: Scene or environment (optional)

    Returns:
        Dictionary with constructed prompt
    """
    return await prompts.build_prompt(subject, style, setting)


@mcp.tool()
async def suggest_negative(model_type: str = "sd15") -> dict:
    """Get recommended negative prompt for model type.

    Args:
        model_type: Model type - sd15, sdxl, flux, wan (default: sd15)

    Returns:
        Dictionary with negative prompt suggestions
    """
    return await prompts.suggest_negative(model_type)


@mcp.tool()
async def analyze_prompt(prompt: str) -> dict:
    """Analyze prompt and suggest improvements.

    Args:
        prompt: Prompt to analyze

    Returns:
        Dictionary with analysis and suggestions
    """
    return await prompts.analyze_prompt(prompt)


# ============================================================================
# PROGRESS & CONTROL TOOLS
# ============================================================================


@mcp.tool()
async def get_progress(prompt_id: str = None) -> dict:
    """Get current generation progress.

    Args:
        prompt_id: Optional specific prompt ID to check

    Returns:
        Dictionary with progress information
    """
    return await control.get_progress(prompt_id)


@mcp.tool()
async def cancel(prompt_id: str = None) -> dict:
    """Cancel current or specific generation job.

    Args:
        prompt_id: Optional specific prompt ID to cancel (cancels current if not provided)

    Returns:
        Dictionary with cancellation status
    """
    return await control.cancel(prompt_id)


@mcp.tool()
async def get_queue() -> dict:
    """View queued jobs.

    Returns:
        Dictionary with queue information
    """
    return await control.get_queue()


@mcp.tool()
async def get_system_status() -> dict:
    """Get GPU/VRAM/server health information.

    Returns:
        Dictionary with system status
    """
    return await control.get_system_status()


@mcp.tool()
async def validate_workflow(
    model: str = "sd15",
    prompt: str = "test prompt",
    width: int = 512,
    height: int = 512,
) -> dict:
    """Validate workflow without generating an image (dry run).

    This tool validates that:
    - The workflow file exists and can be loaded
    - All required models are available on the server
    - The workflow has the required nodes (sampler, model loader, save node)

    Args:
        model: Model to use (sd15, flux, sdxl) - determines which workflow to load
        prompt: Test prompt (not used for generation, just for validation)
        width: Output width for validation
        height: Output height for validation

    Returns:
        Dictionary with validation results including:
        - status: "valid" or "invalid"
        - workflow_file: Name of the workflow file validated
        - is_valid: Boolean indicating if workflow is valid
        - errors: List of validation errors
        - warnings: List of validation warnings
        - missing_models: List of missing models
    """
    try:
        import os

        from comfygen.comfyui_client import ComfyUIClient
        from comfygen.workflows import WorkflowManager

        # Get clients
        comfyui = ComfyUIClient(host=os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188"))
        workflow_mgr = WorkflowManager()

        # Check server availability
        if not comfyui.check_availability():
            return {"status": "error", "error": "ComfyUI server is not available"}

        # Load appropriate workflow
        workflow_map = {
            "sd15": "flux-dev.json",  # TODO: Update to use sd15-specific workflow when available
            "flux": "flux-dev.json",
            "sdxl": "flux-dev.json",  # TODO: Update to use sdxl-specific workflow when available
        }
        workflow_file = workflow_map.get(model, "flux-dev.json")

        workflow = workflow_mgr.load_workflow(workflow_file)
        if not workflow:
            return {
                "status": "invalid",
                "workflow_file": workflow_file,
                "error": f"Failed to load workflow: {workflow_file}",
            }

        # Apply test parameters to workflow (to validate parameter application)
        workflow = workflow_mgr.set_prompt(workflow, prompt, "")
        workflow = workflow_mgr.set_dimensions(workflow, width, height)

        # Validate workflow
        validation_result = workflow_mgr.validate_workflow(workflow, comfyui)

        return {
            "status": "valid" if validation_result["is_valid"] else "invalid",
            "workflow_file": workflow_file,
            **validation_result,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
