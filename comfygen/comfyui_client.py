"""Client for interacting with ComfyUI API."""

import json
import time
from typing import Any, Dict, List, Optional, Tuple
import requests


class ComfyUIClient:
    """Client for ComfyUI API interactions."""
    
    def __init__(self, host: str = "http://192.168.1.215:8188", timeout: int = 30):
        """Initialize ComfyUI client.
        
        Args:
            host: ComfyUI server URL
            timeout: Default timeout for requests in seconds
        """
        self.host = host.rstrip("/")
        self.timeout = timeout
    
    def check_availability(self) -> bool:
        """Check if ComfyUI server is available.
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Get system statistics including GPU and VRAM usage.
        
        Returns:
            Dictionary with system stats or None on failure
        """
        try:
            response = requests.get(f"{self.host}/system_stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_object_info(self) -> Optional[Dict[str, Any]]:
        """Get ComfyUI object info including available nodes.
        
        Returns:
            Dictionary with object info or None on failure
        """
        try:
            response = requests.get(f"{self.host}/object_info", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_available_models(self) -> Optional[Dict[str, List[str]]]:
        """Query available models from ComfyUI API.
        
        Returns:
            Dictionary of available models by type (checkpoints, loras, vae, etc.)
        """
        object_info = self.get_object_info()
        if not object_info:
            return None
        
        models = {}
        
        # Get checkpoints (CheckpointLoaderSimple)
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                if "ckpt_name" in checkpoint_info["input"]["required"]:
                    models["checkpoints"] = checkpoint_info["input"]["required"]["ckpt_name"][0]
        
        # Get LoRAs (LoraLoader)
        if "LoraLoader" in object_info:
            lora_info = object_info["LoraLoader"]
            if "input" in lora_info and "required" in lora_info["input"]:
                if "lora_name" in lora_info["input"]["required"]:
                    models["loras"] = lora_info["input"]["required"]["lora_name"][0]
        
        # Get VAE models (VAELoader)
        if "VAELoader" in object_info:
            vae_info = object_info["VAELoader"]
            if "input" in vae_info and "required" in vae_info["input"]:
                if "vae_name" in vae_info["input"]["required"]:
                    models["vae"] = vae_info["input"]["required"]["vae_name"][0]
        
        # Get diffusion models (UNETLoader)
        if "UNETLoader" in object_info:
            unet_info = object_info["UNETLoader"]
            if "input" in unet_info and "required" in unet_info["input"]:
                if "unet_name" in unet_info["input"]["required"]:
                    models["diffusion_models"] = unet_info["input"]["required"]["unet_name"][0]
        
        # Get text encoders (DualCLIPLoader, TripleCLIPLoader)
        if "DualCLIPLoader" in object_info:
            clip_info = object_info["DualCLIPLoader"]
            if "input" in clip_info and "required" in clip_info["input"]:
                if "clip_name1" in clip_info["input"]["required"]:
                    models["text_encoders"] = clip_info["input"]["required"]["clip_name1"][0]
        
        return models
    
    def queue_prompt(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Queue a workflow for execution.
        
        Args:
            workflow: Workflow dictionary to queue
            
        Returns:
            Prompt ID on success, None on failure
        """
        try:
            response = requests.post(
                f"{self.host}/prompt",
                json={"prompt": workflow},
                timeout=self.timeout
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("prompt_id")
            return None
        except Exception:
            return None
    
    def get_history(self, prompt_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get workflow execution history.
        
        Args:
            prompt_id: Optional specific prompt ID to query
            
        Returns:
            History dictionary or None on failure
        """
        try:
            url = f"{self.host}/history"
            if prompt_id:
                url += f"/{prompt_id}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def get_queue(self) -> Optional[Dict[str, Any]]:
        """Get current queue status.
        
        Returns:
            Queue information or None on failure
        """
        try:
            response = requests.get(f"{self.host}/queue", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def interrupt(self) -> bool:
        """Interrupt current generation.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(f"{self.host}/interrupt", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def cancel_prompt(self, prompt_id: str) -> bool:
        """Cancel a specific prompt by ID.
        
        Args:
            prompt_id: The prompt ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.host}/queue",
                json={"delete": [prompt_id]},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: Optional[int] = None,
        poll_interval: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """Wait for a workflow to complete.
        
        Args:
            prompt_id: The prompt ID to wait for
            timeout: Maximum time to wait in seconds (None for no timeout)
            poll_interval: Time between status polls in seconds
            
        Returns:
            Workflow status on completion, None on timeout or error
        """
        start_time = time.time()
        
        while True:
            history = self.get_history(prompt_id)
            
            if history and prompt_id in history:
                status = history[prompt_id]
                if "outputs" in status:
                    # Workflow completed successfully
                    return status
                elif "status" in status:
                    status_info = status["status"]
                    if status_info.get("completed") is False:
                        # Still in progress
                        pass
                    elif status_info.get("status_str") == "error":
                        # Error occurred
                        return status
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            time.sleep(poll_interval)
    
    def upload_image(self, image_path: str, subfolder: str = "", overwrite: bool = False) -> Optional[Dict[str, Any]]:
        """Upload an image to ComfyUI.
        
        Args:
            image_path: Path to image file
            subfolder: Optional subfolder in input directory
            overwrite: Whether to overwrite existing file
            
        Returns:
            Upload result dictionary or None on failure
        """
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {
                    'subfolder': subfolder,
                    'overwrite': str(overwrite).lower()
                }
                response = requests.post(
                    f"{self.host}/upload/image",
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception:
            return None
