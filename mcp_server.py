#!/usr/bin/env python3
"""MCP server for ComfyGen - AI assistant integration.

This server exposes ComfyUI image/video generation capabilities via the Model Context Protocol,
allowing AI assistants to generate images through tool calls.

Usage:
    python3 mcp_server.py

VS Code MCP Configuration:
    {
      "mcpServers": {
        "comfy-gen": {
          "command": "python3",
          "args": ["/path/to/comfy-gen/mcp_server.py"],
          "env": {
            "COMFYUI_HOST": "http://192.168.1.215:8188",
            "MINIO_ENDPOINT": "192.168.1.215:9000"
          }
        }
      }
    }
"""

import os
import sys
import json
import asyncio
import logging
import aiohttp
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from minio import Minio
from minio.error import S3Error

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables with defaults
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.1.215:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "comfy-gen")

# Create MCP server
mcp = FastMCP("comfy-gen")

# Global state for tracking current generation
current_prompt_id: Optional[str] = None
current_workflow: Optional[Dict] = None


def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False  # HTTP, not HTTPS
    )


def load_workflow_template(workflow_type: str) -> Dict:
    """Load workflow template from workflows directory."""
    workflow_map = {
        "sd15": "flux-dev.json",  # Using flux-dev as base template
        "flux": "flux-dev.json",
    }
    
    workflow_file = workflow_map.get(workflow_type, "flux-dev.json")
    workflow_path = Path(__file__).parent / "workflows" / workflow_file
    
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow template not found: {workflow_path}")
    
    with open(workflow_path, 'r') as f:
        return json.load(f)


def modify_workflow_prompt(workflow: Dict, prompt: str, negative_prompt: str = "") -> Dict:
    """Modify the prompt in the workflow JSON."""
    # Find and update text nodes in the workflow
    found_positive = False
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            if "text" in node["inputs"]:
                # First text node is typically the positive prompt
                if not found_positive:
                    node["inputs"]["text"] = prompt
                    found_positive = True
                elif negative_prompt:
                    # Second text node is typically the negative prompt
                    node["inputs"]["text"] = negative_prompt
                    break
    
    return workflow


def modify_workflow_parameters(
    workflow: Dict,
    width: Optional[int] = None,
    height: Optional[int] = None,
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    seed: Optional[int] = None,
) -> Dict:
    """Modify sampling parameters in the workflow."""
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            inputs = node["inputs"]
            
            # Update KSampler or similar nodes
            if "steps" in inputs and steps is not None:
                inputs["steps"] = steps
            if "cfg" in inputs and cfg is not None:
                inputs["cfg"] = cfg
            if "seed" in inputs and seed is not None:
                inputs["seed"] = seed if seed >= 0 else int(datetime.now().timestamp())
            
            # Update latent image size
            if "width" in inputs and width is not None:
                inputs["width"] = width
            if "height" in inputs and height is not None:
                inputs["height"] = height
    
    return workflow


def add_loras_to_workflow(workflow: Dict, loras: List[Dict]) -> Dict:
    """Add LoRA loaders to the workflow.
    
    Args:
        workflow: Base workflow JSON
        loras: List of dicts with 'name' and 'strength' keys
    
    Returns:
        Modified workflow with LoRA loaders
    """
    if not loras:
        return workflow
    
    # This is a simplified implementation
    # In practice, we'd need to properly insert LoraLoader nodes
    # and rewire the connections in the workflow graph
    # For now, we'll just note this limitation
    logger.warning("LoRA support not fully implemented in workflow modification")
    return workflow


@mcp.tool()
async def generate_image(
    prompt: str,
    negative_prompt: str = "blurry, low quality, bad anatomy, watermark",
    model: str = "sd15",
    loras: Optional[List[Dict[str, Any]]] = None,
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = -1,
) -> Dict[str, Any]:
    """Generate an image using ComfyUI.
    
    Args:
        prompt: Text description of the image to generate
        negative_prompt: Things to avoid in the image
        model: Model to use (sd15, flux)
        loras: List of LoRAs with format [{"name": "lora.safetensors", "strength": 0.8}]
        width: Image width in pixels
        height: Image height in pixels
        steps: Number of sampling steps
        cfg: CFG scale (guidance strength)
        seed: Random seed (-1 for random)
    
    Returns:
        Dict with status, prompt_id, and image_url when complete
    """
    global current_prompt_id, current_workflow
    
    try:
        # Load and modify workflow
        workflow = load_workflow_template(model)
        workflow = modify_workflow_prompt(workflow, prompt, negative_prompt)
        workflow = modify_workflow_parameters(workflow, width, height, steps, cfg, seed)
        
        if loras:
            workflow = add_loras_to_workflow(workflow, loras)
        
        current_workflow = workflow
        
        # Queue the workflow using async HTTP
        url = f"{COMFYUI_HOST}/prompt"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"prompt": workflow}) as response:
                if response.status != 200:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"Failed to queue workflow: {text}"
                    }
                
                result = await response.json()
                current_prompt_id = result["prompt_id"]
        
        # Wait for completion
        status = await wait_for_completion(current_prompt_id)
        
        if not status:
            return {
                "status": "error",
                "error": "Workflow failed to complete"
            }
        
        # Download and upload to MinIO
        output_path = f"/tmp/output_{current_prompt_id}.png"
        if await download_output(status, output_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_generated.png"
            image_url = upload_to_minio(output_path, object_name)
            
            return {
                "status": "success",
                "prompt_id": current_prompt_id,
                "image_url": image_url,
                "parameters": {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg": cfg,
                    "seed": seed
                }
            }
        else:
            return {
                "status": "error",
                "error": "Failed to download output"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        current_prompt_id = None
        current_workflow = None


@mcp.tool()
async def generate_video(
    prompt: str,
    negative_prompt: str = "blurry, low quality, distorted",
    width: int = 512,
    height: int = 512,
    frames: int = 16,
    steps: int = 20,
    cfg: float = 7.0,
    seed: int = -1,
) -> Dict[str, Any]:
    """Generate a video using Wan 2.2 model.
    
    Args:
        prompt: Text description of the video to generate
        negative_prompt: Things to avoid in the video
        width: Video width in pixels
        height: Video height in pixels
        frames: Number of frames to generate
        steps: Number of sampling steps
        cfg: CFG scale (guidance strength)
        seed: Random seed (-1 for random)
    
    Returns:
        Dict with status, prompt_id, and video_url when complete
    """
    return {
        "status": "error",
        "error": "Video generation not yet implemented. Wan 2.2 workflow template needed."
    }


@mcp.tool()
async def list_models() -> Dict[str, List[str]]:
    """List available checkpoint models from ComfyUI.
    
    Returns:
        Dict with 'checkpoints' list and status
    """
    try:
        url = f"{COMFYUI_HOST}/object_info"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"Failed to fetch models: {text}",
                        "checkpoints": []
                    }
                
                data = await response.json()
        
        # Extract checkpoint names
        checkpoints = []
        if "CheckpointLoaderSimple" in data:
            loader_info = data["CheckpointLoaderSimple"]
            if "input" in loader_info and "required" in loader_info["input"]:
                ckpt_list = loader_info["input"]["required"].get("ckpt_name", [[]])[0]
                checkpoints = ckpt_list
        
        return {
            "status": "success",
            "checkpoints": checkpoints
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "checkpoints": []
        }



@mcp.tool()
async def list_loras() -> Dict[str, Any]:
    """List available LoRA files from ComfyUI.
    
    Returns:
        Dict with 'loras' list and status
    """
    try:
        url = f"{COMFYUI_HOST}/object_info"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"Failed to fetch LoRAs: {text}",
                        "loras": []
                    }
                
                data = await response.json()
        
        # Extract LoRA names
        loras = []
        if "LoraLoader" in data:
            loader_info = data["LoraLoader"]
            if "input" in loader_info and "required" in loader_info["input"]:
                lora_list = loader_info["input"]["required"].get("lora_name", [[]])[0]
                loras = [{"name": lora} for lora in lora_list]
        
        return {
            "status": "success",
            "loras": loras,
            "count": len(loras)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "loras": []
        }



@mcp.tool()
async def get_progress() -> Dict[str, Any]:
    """Check the progress of the current generation job.
    
    Returns:
        Dict with current progress information
    """
    global current_prompt_id
    
    if not current_prompt_id:
        return {
            "status": "idle",
            "message": "No active generation"
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Check queue status
            url = f"{COMFYUI_HOST}/queue"
            async with session.get(url) as response:
                if response.status != 200:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"Failed to check queue: {text}"
                    }
                
                queue_data = await response.json()
            
            # Check if our prompt is in the queue
            queue_running = queue_data.get("queue_running", [])
            queue_pending = queue_data.get("queue_pending", [])
            
            for item in queue_running:
                if len(item) > 0 and item[1] == current_prompt_id:
                    return {
                        "status": "running",
                        "prompt_id": current_prompt_id,
                        "message": "Generation in progress"
                    }
            
            for item in queue_pending:
                if len(item) > 0 and item[1] == current_prompt_id:
                    position = queue_pending.index(item)
                    return {
                        "status": "queued",
                        "prompt_id": current_prompt_id,
                        "position": position,
                        "message": f"Queued at position {position}"
                    }
            
            # Check history to see if completed
            history_url = f"{COMFYUI_HOST}/history/{current_prompt_id}"
            async with session.get(history_url) as history_response:
                if history_response.status == 200:
                    history = await history_response.json()
                    if current_prompt_id in history:
                        return {
                            "status": "completed",
                            "prompt_id": current_prompt_id,
                            "message": "Generation completed"
                        }
        
        return {
            "status": "unknown",
            "prompt_id": current_prompt_id,
            "message": "Status unknown"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def cancel_generation() -> Dict[str, Any]:
    """Cancel the current generation job.
    
    Returns:
        Dict with cancellation status
    """
    global current_prompt_id
    
    if not current_prompt_id:
        return {
            "status": "error",
            "message": "No active generation to cancel"
        }
    
    try:
        url = f"{COMFYUI_HOST}/interrupt"
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                if response.status == 200:
                    cancelled_id = current_prompt_id
                    current_prompt_id = None
                    return {
                        "status": "success",
                        "message": f"Cancelled generation {cancelled_id}"
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"Failed to cancel: {text}"
                    }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def list_images(limit: int = 50) -> Dict[str, Any]:
    """List generated images in MinIO bucket.
    
    Args:
        limit: Maximum number of images to return
    
    Returns:
        Dict with list of image URLs and metadata
    """
    try:
        client = get_minio_client()
        
        # Check if bucket exists
        if not client.bucket_exists(BUCKET_NAME):
            return {
                "status": "error",
                "error": f"Bucket {BUCKET_NAME} does not exist",
                "images": []
            }
        
        # List objects in bucket
        objects = client.list_objects(BUCKET_NAME)
        
        images = []
        for obj in objects:
            if len(images) >= limit:
                break
            
            # Filter for image files
            if obj.object_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                images.append({
                    "name": obj.object_name,
                    "url": f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{obj.object_name}",
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None
                })
        
        return {
            "status": "success",
            "images": images,
            "count": len(images)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "images": []
        }


@mcp.tool()
async def get_image_url(filename: str) -> Dict[str, Any]:
    """Get the URL for a specific image in MinIO.
    
    Args:
        filename: Name of the image file
    
    Returns:
        Dict with image URL and metadata
    """
    try:
        client = get_minio_client()
        
        # Check if object exists
        try:
            stat = client.stat_object(BUCKET_NAME, filename)
            return {
                "status": "success",
                "url": f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{filename}",
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "content_type": stat.content_type
            }
        except S3Error as e:
            if e.code == "NoSuchKey":
                return {
                    "status": "error",
                    "error": f"Image {filename} not found"
                }
            raise
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def wait_for_completion(prompt_id: str, timeout: int = 300) -> Optional[Dict]:
    """Wait for workflow to complete with async polling.
    
    Args:
        prompt_id: The prompt ID to wait for
        timeout: Maximum time to wait in seconds
    
    Returns:
        History status dict or None if failed
    """
    url = f"{COMFYUI_HOST}/history/{prompt_id}"
    start_time = asyncio.get_event_loop().time()
    
    async with aiohttp.ClientSession() as session:
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.error(f"Timeout waiting for prompt {prompt_id}")
                return None
            
            async with session.get(url) as response:
                if response.status == 200:
                    history = await response.json()
                    if prompt_id in history:
                        status = history[prompt_id]
                        if "outputs" in status:
                            return status
            
            # Wait before next poll
            await asyncio.sleep(2)


async def download_output(status: Dict, output_path: str) -> bool:
    """Download the generated image from ComfyUI.
    
    Args:
        status: History status dict from ComfyUI
        output_path: Local path to save the image
    
    Returns:
        True if successful, False otherwise
    """
    outputs = status.get("outputs", {})
    async with aiohttp.ClientSession() as session:
        for node_id, node_outputs in outputs.items():
            if "images" in node_outputs:
                for image in node_outputs["images"]:
                    filename = image["filename"]
                    subfolder = image.get("subfolder", "")
                    url = f"{COMFYUI_HOST}/view?filename={filename}&subfolder={subfolder}&type=output"
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            with open(output_path, 'wb') as f:
                                f.write(content)
                            return True
    return False


def upload_to_minio(file_path: str, object_name: str) -> str:
    """Upload file to MinIO bucket.
    
    Args:
        file_path: Local file path
        object_name: Object name in MinIO
    
    Returns:
        Public URL of the uploaded file
    """
    try:
        client = get_minio_client()
        
        # Make bucket if not exists
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
        
        # Determine content type
        ext = Path(file_path).suffix.lower()
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
        }
        content_type = content_types.get(ext, "application/octet-stream")
        
        # Upload file
        client.fput_object(
            BUCKET_NAME,
            object_name,
            file_path,
            content_type=content_type
        )
        
        return f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{object_name}"
        
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        return ""


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
