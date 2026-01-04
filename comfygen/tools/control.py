"""Progress and control MCP tools."""

import os
from typing import Dict, Any, Optional


# Lazy initialization of clients
_comfyui = None


def _get_comfyui():
    """Get or create ComfyUI client."""
    global _comfyui
    if _comfyui is None:
        from comfygen.comfyui_client import ComfyUIClient
        _comfyui = ComfyUIClient(
            host=os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188")
        )
    return _comfyui


async def get_progress(prompt_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current generation progress.
    
    Args:
        prompt_id: Optional specific prompt ID to check
        
    Returns:
        Dictionary with progress information
    """
    try:
        # Get queue status
        queue = _get_comfyui().get_queue()
        if not queue:
            return {
                "status": "error",
                "error": "Failed to get queue status"
            }
        
        queue_running = queue.get("queue_running", [])
        queue_pending = queue.get("queue_pending", [])
        
        # If specific prompt_id requested, check if it's in queue
        if prompt_id:
            # Check running queue
            for item in queue_running:
                if len(item) >= 2 and item[1] == prompt_id:
                    return {
                        "status": "running",
                        "prompt_id": prompt_id,
                        "position": "current",
                        "queue_length": len(queue_pending)
                    }
            
            # Check pending queue
            for idx, item in enumerate(queue_pending):
                if len(item) >= 2 and item[1] == prompt_id:
                    return {
                        "status": "pending",
                        "prompt_id": prompt_id,
                        "position": idx + 1,
                        "queue_length": len(queue_pending)
                    }
            
            # Not in queue - check history
            history = _get_comfyui().get_history(prompt_id)
            if history and prompt_id in history:
                return {
                    "status": "completed",
                    "prompt_id": prompt_id
                }
            
            return {
                "status": "not_found",
                "prompt_id": prompt_id
            }
        
        # No specific prompt - return general queue status
        current_job = None
        if queue_running:
            item = queue_running[0]
            if len(item) >= 2:
                current_job = {
                    "prompt_id": item[1],
                    "number": item[0]
                }
        
        return {
            "status": "success",
            "current_job": current_job,
            "queue_length": len(queue_pending),
            "is_processing": len(queue_running) > 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def cancel(prompt_id: Optional[str] = None) -> Dict[str, Any]:
    """Cancel current or specific generation job.
    
    Args:
        prompt_id: Optional specific prompt ID to cancel (cancels current if None)
        
    Returns:
        Dictionary with cancellation status
    """
    try:
        if prompt_id:
            # Cancel specific prompt
            success = _get_comfyui().cancel_prompt(prompt_id)
            if success:
                return {
                    "status": "success",
                    "message": f"Cancelled prompt {prompt_id}"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Failed to cancel prompt {prompt_id}"
                }
        else:
            # Interrupt current generation
            success = _get_comfyui().interrupt()
            if success:
                return {
                    "status": "success",
                    "message": "Interrupted current generation"
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to interrupt current generation"
                }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def get_queue() -> Dict[str, Any]:
    """View queued jobs.
    
    Returns:
        Dictionary with queue information
    """
    try:
        queue = _get_comfyui().get_queue()
        if not queue:
            return {
                "status": "error",
                "error": "Failed to get queue status"
            }
        
        queue_running = queue.get("queue_running", [])
        queue_pending = queue.get("queue_pending", [])
        
        # Format running jobs
        running_jobs = []
        for item in queue_running:
            if len(item) >= 2:
                running_jobs.append({
                    "number": item[0],
                    "prompt_id": item[1]
                })
        
        # Format pending jobs
        pending_jobs = []
        for item in queue_pending:
            if len(item) >= 2:
                pending_jobs.append({
                    "number": item[0],
                    "prompt_id": item[1]
                })
        
        return {
            "status": "success",
            "running": running_jobs,
            "pending": pending_jobs,
            "running_count": len(running_jobs),
            "pending_count": len(pending_jobs)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def get_system_status() -> Dict[str, Any]:
    """Get GPU/VRAM/server health information.
    
    Returns:
        Dictionary with system status
    """
    try:
        # Check if server is available
        if not _get_comfyui().check_availability():
            return {
                "status": "offline",
                "message": "ComfyUI server is not available"
            }
        
        # Get system stats
        stats = _get_comfyui().get_system_stats()
        if not stats:
            return {
                "status": "error",
                "error": "Failed to get system stats"
            }
        
        # Extract relevant information
        system_info = {
            "status": "online",
            "system": stats.get("system", {}),
            "devices": stats.get("devices", [])
        }
        
        # Parse device information for GPU/VRAM
        devices = stats.get("devices", [])
        if devices:
            gpu_info = []
            for device in devices:
                if device.get("type") in ["cuda", "mps"]:
                    gpu_info.append({
                        "name": device.get("name"),
                        "type": device.get("type"),
                        "vram_total": device.get("vram_total"),
                        "vram_free": device.get("vram_free"),
                        "vram_used_percent": (
                            (1 - device.get("vram_free", 0) / device.get("vram_total", 1)) * 100
                            if device.get("vram_total", 0) > 0 else 0
                        )
                    })
            
            system_info["gpu"] = gpu_info
        
        return system_info
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
