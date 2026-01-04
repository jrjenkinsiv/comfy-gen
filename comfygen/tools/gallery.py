"""Gallery and history management MCP tools."""

import os
from typing import Dict, Any, Optional, List


# Lazy initialization of clients
_comfyui = None
_minio = None


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


async def list_images(
    limit: int = 20,
    prefix: str = "",
    sort: str = "newest",
) -> Dict[str, Any]:
    """Browse generated images from MinIO storage.
    
    Args:
        limit: Maximum number of images to return
        prefix: Filter by filename prefix
        sort: Sort order (newest, oldest, name)
        
    Returns:
        Dictionary with list of images
    """
    try:
        objects = _get_minio().list_objects(prefix=prefix)
        
        # Filter to only image files
        images = [
            obj for obj in objects
            if any(obj["name"].lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])
        ]
        
        # Sort
        if sort == "newest":
            images.sort(key=lambda x: x.get("last_modified", ""), reverse=True)
        elif sort == "oldest":
            images.sort(key=lambda x: x.get("last_modified", ""))
        elif sort == "name":
            images.sort(key=lambda x: x.get("name", ""))
        
        # Limit results
        images = images[:limit]
        
        return {
            "status": "success",
            "images": images,
            "count": len(images),
            "total_in_bucket": len(objects)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def get_image_info(image_name: str) -> Dict[str, Any]:
    """Get generation parameters and metadata for an image.
    
    Args:
        image_name: Image filename in MinIO
        
    Returns:
        Dictionary with image metadata
    """
    try:
        # Get object info from MinIO
        obj_info = _get_minio().get_object_info(image_name)
        if not obj_info:
            return {
                "status": "error",
                "error": f"Image not found: {image_name}"
            }
        
        # Try to get generation parameters from ComfyUI history
        # This is a best-effort attempt - may not always have the data
        history = _get_comfyui().get_history()
        
        generation_params = None
        if history:
            # Search through history for matching output
            for prompt_id, prompt_data in history.items():
                outputs = prompt_data.get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            if img.get("filename") == image_name:
                                # Found the prompt that generated this image
                                # Extract the prompt data
                                prompt_obj = prompt_data.get("prompt", [])
                                if prompt_obj and len(prompt_obj) >= 3:
                                    workflow = prompt_obj[2]
                                    # Try to extract useful params
                                    generation_params = _extract_generation_params(workflow)
                                break
        
        return {
            "status": "success",
            "name": image_name,
            "url": obj_info["url"],
            "size": obj_info["size"],
            "last_modified": obj_info["last_modified"],
            "generation_params": generation_params or "Not available"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def delete_image(image_name: str) -> Dict[str, Any]:
    """Remove image from MinIO storage.
    
    Args:
        image_name: Image filename to delete
        
    Returns:
        Dictionary with deletion status
    """
    try:
        success = _get_minio().delete_object(image_name)
        if success:
            return {
                "status": "success",
                "message": f"Deleted {image_name}"
            }
        else:
            return {
                "status": "error",
                "error": f"Failed to delete {image_name}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def get_history(limit: int = 10) -> Dict[str, Any]:
    """Get recent generations with full parameters.
    
    Args:
        limit: Maximum number of history entries
        
    Returns:
        Dictionary with generation history
    """
    try:
        history = _get_comfyui().get_history()
        if not history:
            return {
                "status": "success",
                "history": [],
                "count": 0
            }
        
        # Convert to list and sort by most recent
        history_list = []
        for prompt_id, prompt_data in history.items():
            outputs = prompt_data.get("outputs", {})
            status_info = prompt_data.get("status", {})
            
            # Extract output files
            output_files = []
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img in node_output["images"]:
                        output_files.append({
                            "type": "image",
                            "filename": img.get("filename"),
                            "url": f"http://{_get_minio().endpoint}/{_get_minio().bucket}/{img.get('filename')}"
                        })
                if "gifs" in node_output or "videos" in node_output:
                    videos = node_output.get("gifs") or node_output.get("videos", [])
                    for vid in videos:
                        output_files.append({
                            "type": "video",
                            "filename": vid.get("filename"),
                            "url": f"http://{_get_minio().endpoint}/{_get_minio().bucket}/{vid.get('filename')}"
                        })
            
            # Extract generation parameters
            prompt_obj = prompt_data.get("prompt", [])
            workflow = {}
            if prompt_obj and len(prompt_obj) >= 3:
                workflow = prompt_obj[2]
            
            params = _extract_generation_params(workflow)
            
            history_list.append({
                "prompt_id": prompt_id,
                "outputs": output_files,
                "status": status_info,
                "parameters": params
            })
        
        # Sort by prompt_id (newer IDs are larger)
        history_list.sort(key=lambda x: x["prompt_id"], reverse=True)
        
        # Limit results
        history_list = history_list[:limit]
        
        return {
            "status": "success",
            "history": history_list,
            "count": len(history_list)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def _extract_generation_params(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Extract generation parameters from workflow.
    
    Args:
        workflow: Workflow dictionary
        
    Returns:
        Dictionary of extracted parameters
    """
    params = {}
    
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        
        # Extract prompts
        if class_type == "CLIPTextEncode":
            text = inputs.get("text", "")
            if text:
                # Try to distinguish positive from negative
                if any(kw in text.lower() for kw in ["bad", "blurry", "worst", "ugly"]):
                    params["negative_prompt"] = text
                else:
                    params["positive_prompt"] = text
        
        # Extract sampler settings
        if class_type in ["KSampler", "KSamplerAdvanced"]:
            params["steps"] = inputs.get("steps")
            params["cfg"] = inputs.get("cfg")
            params["sampler"] = inputs.get("sampler_name")
            params["scheduler"] = inputs.get("scheduler")
            params["seed"] = inputs.get("seed")
            params["denoise"] = inputs.get("denoise")
        
        # Extract dimensions
        if class_type == "EmptyLatentImage":
            params["width"] = inputs.get("width")
            params["height"] = inputs.get("height")
        
        # Extract model
        if class_type == "CheckpointLoaderSimple":
            params["checkpoint"] = inputs.get("ckpt_name")
        
        # Extract LoRAs
        if class_type == "LoraLoader":
            if "loras" not in params:
                params["loras"] = []
            params["loras"].append({
                "name": inputs.get("lora_name"),
                "strength_model": inputs.get("strength_model"),
                "strength_clip": inputs.get("strength_clip")
            })
    
    return params
