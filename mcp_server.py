#!/usr/bin/env python3
"""Comprehensive MCP Server for ComfyUI Image/Video Generation.

This server exposes tools for:

Core Generation:
- Image generation (generate_image, img2img)
- Video generation (generate_video, image_to_video)

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

import sys
import os
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from mcp.server import FastMCP

# Import our service management scripts
import start_comfyui
import stop_comfyui
import restart_comfyui
import check_comfyui_status

# Import generation tools
from comfygen.tools import generation, video, models, gallery, prompts, control

# Import config loader
from comfygen.config import load_presets_config, load_lora_catalog

# Load configuration on startup
_config = load_presets_config()
_lora_catalog = load_lora_catalog()

# Initialize FastMCP server
mcp = FastMCP("ComfyUI Comprehensive Generation Server")


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
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = check_comfyui_status.check_status()
        
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
    negative_prompt: str = "",
    model: str = "sd15",
    width: int = None,
    height: int = None,
    steps: int = None,
    cfg: float = None,
    sampler: str = None,
    scheduler: str = None,
    seed: int = -1,
    validate: bool = None,
    auto_retry: bool = None,
    retry_limit: int = None,
    positive_threshold: float = None,
    preset: str = None,
    lora_preset: str = None,
) -> dict:
    """Generate image from text prompt with optional CLIP validation.
    
    Args:
        prompt: Positive text prompt describing what to generate
        negative_prompt: Negative prompt (what to avoid). Uses default from config if empty.
        model: Model to use (sd15, flux, sdxl)
        width: Output width in pixels (default from preset or 512)
        height: Output height in pixels (default from preset or 512)
        steps: Number of sampling steps (default from preset or 20)
        cfg: CFG scale (default from preset or 7.0)
        sampler: Sampler algorithm (default from preset or euler)
        scheduler: Scheduler type (default from preset or normal)
        seed: Random seed, -1 for random (default: -1)
        validate: Run CLIP validation after generation (default from preset or True)
        auto_retry: Automatically retry if validation fails (default from preset or True)
        retry_limit: Maximum retry attempts (default from preset or 3)
        positive_threshold: Minimum CLIP score for positive prompt (default from preset or 0.25)
        preset: Generation preset name (draft, balanced, high-quality, fast, ultra)
        lora_preset: LoRA preset name from lora_catalog.yaml model_suggestions
    
    Returns:
        Dictionary with status, url, generation metadata, and validation results
    """
    from comfygen.config import get_preset, get_lora_preset, apply_preset_to_params
    
    # Apply default negative prompt from config if not provided
    effective_negative = negative_prompt
    if not effective_negative:
        effective_negative = _config.get("default_negative_prompt", "")
    
    # Start with provided parameters (None values will be filled by preset or defaults)
    params = {
        "negative_prompt": effective_negative,
        "model": model,
        "seed": seed,
    }
    
    # Helper function to add optional parameters
    def add_if_not_none(key, value):
        if value is not None:
            params[key] = value
    
    # Add explicitly provided parameters
    optional_params = [
        ('width', width), ('height', height), ('steps', steps), ('cfg', cfg),
        ('sampler', sampler), ('scheduler', scheduler), ('validate', validate),
        ('auto_retry', auto_retry), ('retry_limit', retry_limit), 
        ('positive_threshold', positive_threshold)
    ]
    for key, value in optional_params:
        add_if_not_none(key, value)
    
    # Apply preset if specified (preset values used as defaults)
    if preset:
        preset_config = get_preset(preset)
        if preset_config:
            params = apply_preset_to_params(params, preset_config)
        else:
            available = ', '.join(_config.get("presets", {}).keys())
            return {
                "status": "error",
                "error": f"Unknown preset '{preset}'. Available: {available}"
            }
    
    # Apply LoRA preset if specified
    loras = None
    if lora_preset:
        lora_config = get_lora_preset(lora_preset)
        if lora_config:
            default_loras = lora_config.get("default_loras", [])
            if default_loras:
                # Convert to format expected by generate_image
                loras = [{"name": lora, "strength": 1.0} for lora in default_loras]
            # Also update model if specified in preset
            if "model" in lora_config:
                params["model"] = lora_config["model"]
            # Note: workflow from lora_config is informational only; 
            # actual workflow selection happens in WorkflowManager
        else:
            available = ', '.join(_lora_catalog.get("model_suggestions", {}).keys())
            return {
                "status": "error",
                "error": f"Unknown lora_preset '{lora_preset}'. Available: {available}"
            }
    
    # Apply final defaults for any still-missing values
    final_params = {
        "width": params.get("width", 512),
        "height": params.get("height", 512),
        "steps": params.get("steps", 20),
        "cfg": params.get("cfg", 7.0),
        "sampler": params.get("sampler", "euler"),
        "scheduler": params.get("scheduler", "normal"),
        "validate": params.get("validate", True),
        "auto_retry": params.get("auto_retry", True),
        "retry_limit": params.get("retry_limit", 3),
        "positive_threshold": params.get("positive_threshold", 0.25),
    }
    
    return await generation.generate_image(
        prompt=prompt,
        negative_prompt=params["negative_prompt"],
        model=params["model"],
        width=final_params["width"],
        height=final_params["height"],
        steps=final_params["steps"],
        cfg=final_params["cfg"],
        sampler=final_params["sampler"],
        scheduler=final_params["scheduler"],
        seed=params["seed"],
        loras=loras,
        validate=final_params["validate"],
        auto_retry=final_params["auto_retry"],
        retry_limit=final_params["retry_limit"],
        positive_threshold=final_params["positive_threshold"]
    )


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
        negative_prompt: Negative prompt. Uses default from config if empty.
        denoise: Denoise strength 0.0-1.0 (lower preserves more original, default: 0.7)
        model: Model to use (default: sd15)
        steps: Number of sampling steps (default: 20)
        cfg: CFG scale (default: 7.0)
        seed: Random seed, -1 for random (default: -1)
    
    Returns:
        Dictionary with status, url, and generation metadata
    """
    # Apply default negative prompt from config if not provided
    effective_negative = negative_prompt
    if not effective_negative:
        effective_negative = _config.get("default_negative_prompt", "")
    
    return await generation.img2img(
        input_image=input_image,
        prompt=prompt,
        negative_prompt=effective_negative,
        denoise=denoise,
        model=model,
        steps=steps,
        cfg=cfg,
        seed=seed
    )


# ============================================================================
# VIDEO GENERATION TOOLS
# ============================================================================

@mcp.tool()
async def generate_video(
    prompt: str,
    negative_prompt: str = "",
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
        negative_prompt: Negative prompt. Uses default from config if empty.
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
    # Apply default negative prompt from config if not provided
    effective_negative = negative_prompt
    if not effective_negative:
        effective_negative = _config.get("default_negative_prompt", "")
    
    return await video.generate_video(
        prompt=prompt,
        negative_prompt=effective_negative,
        width=width,
        height=height,
        frames=frames,
        fps=fps,
        steps=steps,
        cfg=cfg,
        seed=seed
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
        negative_prompt: Negative prompt. Uses default from config if empty.
        motion_strength: How much movement 0.0-1.0+ (default: 1.0)
        frames: Number of frames (default: 81)
        fps: Frames per second (default: 16)
        steps: Number of sampling steps (default: 30)
        seed: Random seed, -1 for random (default: -1)
    
    Returns:
        Dictionary with status, url, and generation metadata
    """
    # Apply default negative prompt from config if not provided
    effective_negative = negative_prompt
    if not effective_negative:
        effective_negative = _config.get("default_negative_prompt", "")
    
    return await video.image_to_video(
        input_image=input_image,
        prompt=prompt,
        negative_prompt=effective_negative,
        motion_strength=motion_strength,
        frames=frames,
        fps=fps,
        steps=steps,
        seed=seed
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
        query=query,
        model_type=model_type,
        base_model=base_model,
        sort=sort,
        nsfw=nsfw,
        limit=limit
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


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
