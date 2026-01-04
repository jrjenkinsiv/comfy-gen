"""Image generation MCP tools."""

import os
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


# Lazy initialization of clients
_comfyui = None
_minio = None
_workflow_mgr = None
_model_registry = None


def _get_comfyui():
    """Get or create ComfyUI client."""
    global _comfyui
    if _comfyui is None:
        from comfygen.comfyui_client import ComfyUIClient
        _comfyui = ComfyUIClient(
            host=os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188")
        )
    return _comfyui


def _get_minio():
    """Get or create MinIO client."""
    global _minio
    if _minio is None:
        from comfygen.minio_client import MinIOClient
        _minio = MinIOClient(
            endpoint=os.getenv("MINIO_ENDPOINT", "192.168.1.215:9000"),
            bucket=os.getenv("MINIO_BUCKET", "comfy-gen")
        )
    return _minio


def _get_workflow_mgr():
    """Get or create Workflow manager."""
    global _workflow_mgr
    if _workflow_mgr is None:
        from comfygen.workflows import WorkflowManager
        _workflow_mgr = WorkflowManager()
    return _workflow_mgr


def _get_model_registry():
    """Get or create Model registry."""
    global _model_registry
    if _model_registry is None:
        from comfygen.models import ModelRegistry
        _model_registry = ModelRegistry()
    return _model_registry


def _generate_filename(prefix: str = "output", extension: str = "png") -> str:
    """Generate timestamped filename.
    
    Args:
        prefix: Filename prefix
        extension: File extension
        
    Returns:
        Timestamped filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{prefix}.{extension}"


async def generate_image(
    prompt: str,
    negative_prompt: str = "blurry, low quality, watermark",
    model: str = "sd15",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg: float = 7.0,
    sampler: str = "euler",
    scheduler: str = "normal",
    seed: int = -1,
    loras: Optional[List[Dict[str, Any]]] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate image from text prompt.
    
    Args:
        prompt: Positive text prompt
        negative_prompt: Negative text prompt (what to avoid)
        model: Model to use (sd15, flux, sdxl)
        width: Output width in pixels
        height: Output height in pixels
        steps: Number of sampling steps
        cfg: CFG scale
        sampler: Sampler algorithm
        scheduler: Scheduler type
        seed: Random seed (-1 for random)
        loras: List of LoRAs with name and strength
        filename: Output filename (auto-generated if None)
        
    Returns:
        Dictionary with status, url, and metadata
    """
    try:
        # Get clients
        comfyui = _get_comfyui()
        minio = _get_minio()
        workflow_mgr = _get_workflow_mgr()
        
        # Check server availability
        if not comfyui.check_availability():
            return {
                "status": "error",
                "error": "ComfyUI server is not available"
            }
        
        # Load appropriate workflow
        workflow_map = {
            "sd15": "flux-dev.json",  # Using flux-dev as base SD workflow
            "flux": "flux-dev.json",
            "sdxl": "flux-dev.json"
        }
        workflow_file = workflow_map.get(model, "flux-dev.json")
        
        workflow = workflow_mgr.load_workflow(workflow_file)
        if not workflow:
            return {
                "status": "error",
                "error": f"Failed to load workflow: {workflow_file}"
            }
        
        # Apply parameters to workflow
        workflow = workflow_mgr.set_prompt(workflow, prompt, negative_prompt)
        workflow = workflow_mgr.set_dimensions(workflow, width, height)
        workflow = workflow_mgr.set_seed(workflow, seed)
        workflow = workflow_mgr.set_sampler_params(
            workflow,
            steps=steps,
            cfg=cfg,
            sampler_name=sampler,
            scheduler=scheduler
        )
        
        # Apply LoRAs if specified
        if loras:
            for lora_spec in loras:
                lora_name = lora_spec.get("name")
                strength = lora_spec.get("strength", 1.0)
                if lora_name:
                    workflow = workflow_mgr.inject_lora(workflow, lora_name, strength, strength)
        
        # Queue workflow
        prompt_id = comfyui.queue_prompt(workflow)
        if not prompt_id:
            return {
                "status": "error",
                "error": "Failed to queue workflow"
            }
        
        # Wait for completion
        result = comfyui.wait_for_completion(prompt_id, timeout=300)
        if not result:
            return {
                "status": "error",
                "error": "Generation timed out or failed",
                "prompt_id": prompt_id
            }
        
        # Extract output image path from result
        outputs = result.get("outputs", {})
        if not outputs:
            return {
                "status": "error",
                "error": "No outputs in result",
                "prompt_id": prompt_id
            }
        
        # Find the SaveImage node output
        image_url = None
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                images = node_output["images"]
                if images:
                    # Images are saved in ComfyUI output directory
                    # MinIO should already have them if auto-upload is configured
                    img_info = images[0]
                    img_filename = img_info.get("filename", "")
                    if img_filename:
                        # Construct MinIO URL
                        image_url = f"http://{minio.endpoint}/{minio.bucket}/{img_filename}"
                        break
        
        if not image_url:
            return {
                "status": "error",
                "error": "Failed to get output image URL",
                "prompt_id": prompt_id
            }
        
        return {
            "status": "success",
            "url": image_url,
            "prompt_id": prompt_id,
            "metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg": cfg,
                "sampler": sampler,
                "scheduler": scheduler,
                "seed": seed if seed != -1 else "random",
                "loras": loras
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def img2img(
    input_image: str,
    prompt: str,
    negative_prompt: str = "",
    denoise: float = 0.7,
    model: str = "sd15",
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = -1,
    loras: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Transform existing image with prompt guidance.
    
    Args:
        input_image: URL or path to input image
        prompt: Positive text prompt
        negative_prompt: Negative text prompt
        denoise: Denoise strength (0.0-1.0, lower preserves more of original)
        model: Model to use
        steps: Number of sampling steps
        cfg: CFG scale
        seed: Random seed (-1 for random)
        loras: List of LoRAs with name and strength
        
    Returns:
        Dictionary with status, url, and metadata
    """
    try:
        # Get clients
        comfyui = _get_comfyui()
        workflow_mgr = _get_workflow_mgr()
        
        # Check server availability
        if not comfyui.check_availability():
            return {
                "status": "error",
                "error": "ComfyUI server is not available"
            }
        
        # Load img2img workflow
        workflow = workflow_mgr.load_workflow("sd15-img2img.json")
        if not workflow:
            return {
                "status": "error",
                "error": "Failed to load img2img workflow"
            }
        
        # TODO: Upload input image to ComfyUI if it's a local file
        # For now, assume image is already accessible
        
        # Apply parameters
        workflow = workflow_mgr.set_prompt(workflow, prompt, negative_prompt)
        workflow = workflow_mgr.set_seed(workflow, seed)
        workflow = workflow_mgr.set_sampler_params(
            workflow,
            steps=steps,
            cfg=cfg,
            denoise=denoise
        )
        
        # Apply LoRAs if specified
        if loras:
            for lora_spec in loras:
                lora_name = lora_spec.get("name")
                strength = lora_spec.get("strength", 1.0)
                if lora_name:
                    workflow = workflow_mgr.inject_lora(workflow, lora_name, strength, strength)
        
        # Queue workflow
        prompt_id = comfyui.queue_prompt(workflow)
        if not prompt_id:
            return {
                "status": "error",
                "error": "Failed to queue workflow"
            }
        
        # Wait for completion
        result = comfyui.wait_for_completion(prompt_id, timeout=300)
        if not result:
            return {
                "status": "error",
                "error": "Generation timed out or failed",
                "prompt_id": prompt_id
            }
        
        # Extract output
        image_url = _extract_image_url(result)
        if not image_url:
            return {
                "status": "error",
                "error": "Failed to get output image URL",
                "prompt_id": prompt_id
            }
        
        return {
            "status": "success",
            "url": image_url,
            "prompt_id": prompt_id,
            "metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "denoise": denoise,
                "model": model,
                "steps": steps,
                "cfg": cfg,
                "seed": seed if seed != -1 else "random"
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def inpaint(
    input_image: str,
    mask_image: str,
    prompt: str,
    negative_prompt: str = "",
    denoise: float = 1.0,
    model: str = "sd15",
) -> Dict[str, Any]:
    """Inpaint masked region of image.
    
    Args:
        input_image: URL or path to input image
        mask_image: URL or path to mask (white = inpaint area)
        prompt: Positive text prompt for inpainted region
        negative_prompt: Negative text prompt
        denoise: Denoise strength (0.0-1.0)
        model: Model to use
        
    Returns:
        Dictionary with status, url, and metadata
    """
    return {
        "status": "error",
        "error": "Inpainting not yet implemented - requires custom workflow"
    }


async def upscale(
    input_image: str,
    scale: int = 4,
    model: str = "RealESRGAN_x4plus",
) -> Dict[str, Any]:
    """AI upscale image.
    
    Args:
        input_image: URL or path to input image
        scale: Upscale factor (2x or 4x)
        model: Upscale model to use
        
    Returns:
        Dictionary with status, url, and metadata
    """
    return {
        "status": "error",
        "error": "Upscaling not yet implemented - requires custom workflow"
    }


async def face_restore(
    input_image: str,
    model: str = "codeformer",
    strength: float = 0.8,
) -> Dict[str, Any]:
    """Restore/enhance faces in image.
    
    Args:
        input_image: URL or path to input image
        model: Face restoration model (codeformer, GFPGAN)
        strength: Restoration strength (0.0-1.0)
        
    Returns:
        Dictionary with status, url, and metadata
    """
    return {
        "status": "error",
        "error": "Face restoration not yet implemented - requires custom workflow"
    }


def _extract_image_url(result: Dict[str, Any]) -> Optional[str]:
    """Extract image URL from workflow result.
    
    Args:
        result: Workflow execution result
        
    Returns:
        Image URL or None
    """
    minio = _get_minio()
    outputs = result.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            images = node_output["images"]
            if images:
                img_info = images[0]
                img_filename = img_info.get("filename", "")
                if img_filename:
                    return f"http://{minio.endpoint}/{minio.bucket}/{img_filename}"
    return None
