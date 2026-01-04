"""Image generation MCP tools."""

import os
import random
import re
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


def _adjust_prompt_for_retry(
    positive_prompt: str, 
    negative_prompt: str, 
    attempt: int
) -> tuple:
    """Adjust prompts for retry attempt to improve quality.
    
    Args:
        positive_prompt: Original positive prompt
        negative_prompt: Original negative prompt (can be empty string)
        attempt: Current retry attempt number (1-based)
    
    Returns:
        Tuple of (adjusted_positive, adjusted_negative)
    """
    # Increase emphasis on key terms
    adjusted_positive = positive_prompt
    
    # Add emphasis to "single" and "one" if they appear
    if "single" in adjusted_positive.lower() or "one" in adjusted_positive.lower():
        # Increase weight multiplier based on attempt
        multiplier = 1.0 + (attempt * 0.3)
        
        # Apply weight to single/one car phrases
        adjusted_positive = re.sub(
            r'\bsingle\s+car\b', 
            f'(single car:{multiplier:.1f})',
            adjusted_positive,
            flags=re.IGNORECASE
        )
        adjusted_positive = re.sub(
            r'\bone\s+car\b',
            f'(one car:{multiplier:.1f})',
            adjusted_positive,
            flags=re.IGNORECASE
        )
    
    # Strengthen negative prompt (handle empty string)
    adjusted_negative = negative_prompt if negative_prompt else ""
    retry_negative_terms = [
        "multiple cars",
        "duplicate",
        "cloned",
        "ghosting",
        "mirrored",
        "two cars",
        "extra car"
    ]
    
    # Add retry-specific negative terms if not already present
    for term in retry_negative_terms:
        if adjusted_negative and term not in adjusted_negative.lower():
            adjusted_negative = f"{adjusted_negative}, {term}"
        elif not adjusted_negative:
            adjusted_negative = term if not adjusted_negative else f"{adjusted_negative}, {term}"
    
    return adjusted_positive, adjusted_negative


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
    validate: bool = True,
    auto_retry: bool = True,
    retry_limit: int = 3,
    positive_threshold: float = 0.25,
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
        validate: Run CLIP validation after generation (default: True)
        auto_retry: Automatically retry if validation fails (default: True)
        retry_limit: Maximum retry attempts (default: 3)
        positive_threshold: Minimum CLIP score for positive prompt (default: 0.25)
        
    Returns:
        Dictionary with status, url, metadata, and validation results
    """
    # Determine max attempts based on validation settings
    max_attempts = retry_limit if (validate and auto_retry) else 1
    
    # Store original prompts for retries
    original_prompt = prompt
    original_negative = negative_prompt
    
    # Track validation results
    validation_result = None
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Adjust prompts for retry attempts
            if attempt > 1:
                current_prompt, current_negative = _adjust_prompt_for_retry(
                    original_prompt,
                    original_negative,
                    attempt - 1
                )
            else:
                current_prompt = prompt
                current_negative = negative_prompt
            
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
            workflow = workflow_mgr.set_prompt(workflow, current_prompt, current_negative)
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
                last_error = "Failed to queue workflow"
                if attempt >= max_attempts:
                    return {
                        "status": "error",
                        "error": last_error
                    }
                continue
            
            # Wait for completion
            result = comfyui.wait_for_completion(prompt_id, timeout=300)
            if not result:
                last_error = "Generation timed out or failed"
                if attempt >= max_attempts:
                    return {
                        "status": "error",
                        "error": last_error,
                        "prompt_id": prompt_id
                    }
                continue
            
            # Extract output image path from result
            outputs = result.get("outputs", {})
            if not outputs:
                last_error = "No outputs in result"
                if attempt >= max_attempts:
                    return {
                        "status": "error",
                        "error": last_error,
                        "prompt_id": prompt_id
                    }
                continue
            
            # Find the SaveImage node output
            image_url = None
            image_filename = None
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    images = node_output["images"]
                    if images:
                        # Images are saved in ComfyUI output directory
                        # MinIO should already have them if auto-upload is configured
                        img_info = images[0]
                        image_filename = img_info.get("filename", "")
                        if image_filename:
                            # Construct MinIO URL
                            image_url = f"http://{minio.endpoint}/{minio.bucket}/{image_filename}"
                            break
            
            if not image_url:
                last_error = "Failed to get output image URL"
                if attempt >= max_attempts:
                    return {
                        "status": "error",
                        "error": last_error,
                        "prompt_id": prompt_id
                    }
                continue
            
            # Run validation if requested
            if validate:
                try:
                    from comfy_gen.validation import validate_image as validate_image_fn
                    
                    # Download image to temporary location for validation
                    import requests
                    response = requests.get(image_url, timeout=30)
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                            tmp_file.write(response.content)
                            tmp_path = tmp_file.name
                        
                        try:
                            # Run validation
                            validation_result = validate_image_fn(
                                tmp_path,
                                original_prompt,  # Use original prompt for validation
                                original_negative if original_negative else None,
                                positive_threshold=positive_threshold
                            )
                            
                            # Clean up temp file
                            os.unlink(tmp_path)
                            
                            # Check if validation passed
                            if validation_result.get('passed'):
                                # Success! Return result
                                return {
                                    "status": "success",
                                    "url": image_url,
                                    "prompt_id": prompt_id,
                                    "attempt": attempt,
                                    "validation": {
                                        "passed": True,
                                        "positive_score": validation_result.get('positive_score', 0.0),
                                        "negative_score": validation_result.get('negative_score'),
                                        "score_delta": validation_result.get('score_delta'),
                                        "reason": validation_result.get('reason', '')
                                    },
                                    "metadata": {
                                        "prompt": current_prompt,
                                        "original_prompt": original_prompt,
                                        "negative_prompt": current_negative,
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
                            else:
                                # Validation failed
                                if attempt >= max_attempts:
                                    # Max retries reached, return with validation failure
                                    return {
                                        "status": "success",
                                        "url": image_url,
                                        "prompt_id": prompt_id,
                                        "attempt": attempt,
                                        "validation": {
                                            "passed": False,
                                            "positive_score": validation_result.get('positive_score', 0.0),
                                            "negative_score": validation_result.get('negative_score'),
                                            "score_delta": validation_result.get('score_delta'),
                                            "reason": validation_result.get('reason', ''),
                                            "warning": f"Max retries ({retry_limit}) reached"
                                        },
                                        "metadata": {
                                            "prompt": current_prompt,
                                            "original_prompt": original_prompt,
                                            "negative_prompt": current_negative,
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
                                # Continue to next retry
                                continue
                        except Exception as e:
                            # Validation error, clean up and continue
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                            raise e
                    else:
                        # Failed to download image for validation
                        last_error = f"Failed to download image for validation: HTTP {response.status_code}"
                        if attempt >= max_attempts:
                            return {
                                "status": "error",
                                "error": last_error,
                                "url": image_url,
                                "prompt_id": prompt_id
                            }
                        continue
                        
                except ImportError:
                    # Validation not available, return without validation
                    return {
                        "status": "success",
                        "url": image_url,
                        "prompt_id": prompt_id,
                        "validation": {
                            "passed": None,
                            "reason": "CLIP validation dependencies not available"
                        },
                        "metadata": {
                            "prompt": current_prompt,
                            "negative_prompt": current_negative,
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
            else:
                # Validation not requested, return success
                return {
                    "status": "success",
                    "url": image_url,
                    "prompt_id": prompt_id,
                    "metadata": {
                        "prompt": current_prompt,
                        "negative_prompt": current_negative,
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
            last_error = str(e)
            if attempt >= max_attempts:
                return {
                    "status": "error",
                    "error": last_error,
                    "attempt": attempt
                }
            continue
    
    # Should not reach here, but return error if we do
    return {
        "status": "error",
        "error": last_error or "Unknown error during generation"
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
