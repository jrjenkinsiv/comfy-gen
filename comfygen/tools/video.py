"""Video generation MCP tools."""

import os
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
    loras: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate video from text (Wan 2.2 T2V).
    
    Args:
        prompt: Positive text prompt
        negative_prompt: Negative text prompt
        width: Video width in pixels
        height: Video height in pixels
        frames: Number of frames (~5 sec at 16fps = 81 frames)
        fps: Frames per second
        steps: Number of sampling steps
        cfg: CFG scale
        seed: Random seed (-1 for random)
        loras: List of LoRAs with name and strength
        
    Returns:
        Dictionary with status, url, and metadata
    """
    try:
        # Check server availability
        if not _get_comfyui().check_availability():
            return {
                "status": "error",
                "error": "ComfyUI server is not available"
            }
        
        # Load Wan 2.2 T2V workflow
        workflow = _get_workflow_mgr().load_workflow("wan22-t2v.json")
        if not workflow:
            return {
                "status": "error",
                "error": "Failed to load Wan 2.2 T2V workflow"
            }
        
        # Apply parameters
        workflow = _get_workflow_mgr().set_prompt(workflow, prompt, negative_prompt)
        workflow = _get_workflow_mgr().set_seed(workflow, seed)
        workflow = _get_workflow_mgr().set_sampler_params(
            workflow,
            steps=steps,
            cfg=cfg
        )
        
        # Set video-specific parameters
        workflow = _get_workflow_mgr().set_video_params(
            workflow,
            width=width,
            height=height,
            length=frames
        )
        workflow = _get_workflow_mgr().set_video_fps(workflow, fps=fps)
        
        # Apply LoRAs if specified
        if loras:
            for lora_spec in loras:
                lora_name = lora_spec.get("name")
                strength = lora_spec.get("strength", 1.0)
                if lora_name:
                    workflow = _get_workflow_mgr().inject_lora(workflow, lora_name, strength, strength)
        
        # Queue workflow
        prompt_id = _get_comfyui().queue_prompt(workflow)
        if not prompt_id:
            return {
                "status": "error",
                "error": "Failed to queue workflow"
            }
        
        # Wait for completion (videos take longer)
        result = _get_comfyui().wait_for_completion(prompt_id, timeout=600)
        if not result:
            return {
                "status": "error",
                "error": "Generation timed out or failed",
                "prompt_id": prompt_id
            }
        
        # Extract output video URL
        video_url = _extract_video_url(result)
        if not video_url:
            return {
                "status": "error",
                "error": "Failed to get output video URL",
                "prompt_id": prompt_id
            }
        
        return {
            "status": "success",
            "url": video_url,
            "prompt_id": prompt_id,
            "metadata": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "frames": frames,
                "fps": fps,
                "steps": steps,
                "cfg": cfg,
                "seed": seed if seed != -1 else "random",
                "loras": loras
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def image_to_video(
    input_image: str,
    prompt: str,
    negative_prompt: str = "",
    motion_strength: float = 1.0,
    frames: int = 81,
    fps: int = 16,
    steps: int = 30,
    seed: int = -1,
    loras: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Animate image to video (Wan 2.2 I2V).
    
    Args:
        input_image: URL or path to input image
        prompt: Positive text prompt describing motion
        negative_prompt: Negative text prompt
        motion_strength: How much movement (0.0-1.0+)
        frames: Number of frames
        fps: Frames per second
        steps: Number of sampling steps
        seed: Random seed (-1 for random)
        loras: List of LoRAs with name and strength
        
    Returns:
        Dictionary with status, url, and metadata
    """
    try:
        # Check server availability
        if not _get_comfyui().check_availability():
            return {
                "status": "error",
                "error": "ComfyUI server is not available"
            }
        
        # Load Wan 2.2 I2V workflow
        workflow = _get_workflow_mgr().load_workflow("wan22-i2v.json")
        if not workflow:
            return {
                "status": "error",
                "error": "Failed to load Wan 2.2 I2V workflow"
            }
        
        # TODO: Upload input image to ComfyUI if needed
        
        # Apply parameters
        workflow = _get_workflow_mgr().set_prompt(workflow, prompt, negative_prompt)
        workflow = _get_workflow_mgr().set_seed(workflow, seed)
        workflow = _get_workflow_mgr().set_sampler_params(
            workflow,
            steps=steps
        )
        
        # Set video-specific parameters
        workflow = _get_workflow_mgr().set_video_params(
            workflow,
            length=frames
        )
        workflow = _get_workflow_mgr().set_video_fps(workflow, fps=fps)
        
        # Apply LoRAs if specified
        if loras:
            for lora_spec in loras:
                lora_name = lora_spec.get("name")
                strength = lora_spec.get("strength", 1.0)
                if lora_name:
                    workflow = _get_workflow_mgr().inject_lora(workflow, lora_name, strength, strength)
        
        # Queue workflow
        prompt_id = _get_comfyui().queue_prompt(workflow)
        if not prompt_id:
            return {
                "status": "error",
                "error": "Failed to queue workflow"
            }
        
        # Wait for completion
        result = _get_comfyui().wait_for_completion(prompt_id, timeout=600)
        if not result:
            return {
                "status": "error",
                "error": "Generation timed out or failed",
                "prompt_id": prompt_id
            }
        
        # Extract output video URL
        video_url = _extract_video_url(result)
        if not video_url:
            return {
                "status": "error",
                "error": "Failed to get output video URL",
                "prompt_id": prompt_id
            }
        
        return {
            "status": "success",
            "url": video_url,
            "prompt_id": prompt_id,
            "metadata": {
                "input_image": input_image,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "motion_strength": motion_strength,
                "frames": frames,
                "fps": fps,
                "steps": steps,
                "seed": seed if seed != -1 else "random",
                "loras": loras
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def video_extend(
    input_video: str,
    prompt: str,
    extend_frames: int = 81,
) -> Dict[str, Any]:
    """Extend existing video.
    
    Args:
        input_video: URL or path to input video
        prompt: Prompt for continuation
        extend_frames: Number of frames to add
        
    Returns:
        Dictionary with status, url, and metadata
    """
    return {
        "status": "error",
        "error": "Video extension not yet implemented - requires custom workflow"
    }


async def interpolate_frames(
    input_video: str,
    target_fps: int = 30,
) -> Dict[str, Any]:
    """Frame interpolation for smoother video.
    
    Args:
        input_video: URL or path to input video
        target_fps: Target frames per second
        
    Returns:
        Dictionary with status, url, and metadata
    """
    return {
        "status": "error",
        "error": "Frame interpolation not yet implemented - requires custom workflow"
    }


def _extract_video_url(result: Dict[str, Any]) -> Optional[str]:
    """Extract video URL from workflow result.
    
    Args:
        result: Workflow execution result
        
    Returns:
        Video URL or None
    """
    outputs = result.get("outputs", {})
    for node_id, node_output in outputs.items():
        # Check for video outputs (different nodes may save videos differently)
        if "gifs" in node_output or "videos" in node_output:
            videos = node_output.get("gifs") or node_output.get("videos", [])
            if videos:
                video_info = videos[0]
                video_filename = video_info.get("filename", "")
                if video_filename:
                    return f"http://{_get_minio().endpoint}/{_get_minio().bucket}/{video_filename}"
        
        # Also check images in case video is saved as image sequence
        if "images" in node_output:
            images = node_output["images"]
            if images:
                img_info = images[0]
                img_filename = img_info.get("filename", "")
                # Check if it's actually a video file
                if img_filename and any(img_filename.endswith(ext) for ext in [".mp4", ".gif", ".webm"]):
                    return f"http://{_get_minio().endpoint}/{_get_minio().bucket}/{img_filename}"
    
    return None
