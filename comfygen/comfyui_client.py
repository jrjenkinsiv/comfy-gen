"""Client for interacting with ComfyUI API."""

import json
import time
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple, Callable
import requests

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


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
        self._ws_url = self.host.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
    
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
        poll_interval: float = 2.0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """Wait for a workflow to complete.
        
        Args:
            prompt_id: The prompt ID to wait for
            timeout: Maximum time to wait in seconds (None for no timeout)
            poll_interval: Time between status polls in seconds
            progress_callback: Optional callback for progress updates (receives dict with progress info)
            
        Returns:
            Workflow status on completion, None on timeout or error
        """
        # Start WebSocket progress tracker if callback provided and WebSocket available
        ws_tracker = None
        if progress_callback and WEBSOCKET_AVAILABLE:
            ws_tracker = self._start_progress_tracker(prompt_id, progress_callback)
        
        start_time = time.time()
        
        try:
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
        finally:
            # Stop WebSocket tracker
            if ws_tracker:
                self._stop_progress_tracker(ws_tracker)
    
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
    
    def _start_progress_tracker(
        self,
        prompt_id: str,
        progress_callback: Callable[[Dict[str, Any]], None]
    ) -> Optional[Dict[str, Any]]:
        """Start WebSocket progress tracking for a prompt.
        
        Args:
            prompt_id: The prompt ID to track
            progress_callback: Callback function for progress updates
            
        Returns:
            Tracker state dictionary or None if WebSocket not available
        """
        if not WEBSOCKET_AVAILABLE:
            return None
        
        tracker_state = {
            'prompt_id': prompt_id,
            'callback': progress_callback,
            'ws': None,
            'thread': None,
            'running': False,
            'completed': False,
            'start_time': time.time()
        }
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Only process messages for our prompt_id
                if msg_type == "execution_start":
                    prompt_info = data.get("data", {}).get("prompt_id")
                    if prompt_info == prompt_id:
                        progress_callback({
                            "type": "start",
                            "prompt_id": prompt_id,
                            "message": "Generation started"
                        })
                        
                elif msg_type == "executing":
                    exec_data = data.get("data", {})
                    if exec_data.get("prompt_id") == prompt_id:
                        node = exec_data.get("node")
                        if node is None:
                            # Execution complete
                            tracker_state['completed'] = True
                            elapsed = time.time() - tracker_state['start_time']
                            progress_callback({
                                "type": "complete",
                                "prompt_id": prompt_id,
                                "elapsed_seconds": elapsed,
                                "message": f"Generation complete in {elapsed:.1f}s"
                            })
                        else:
                            progress_callback({
                                "type": "node",
                                "prompt_id": prompt_id,
                                "node": node,
                                "message": f"Executing node {node}"
                            })
                            
                elif msg_type == "progress":
                    prog_data = data.get("data", {})
                    if prog_data.get("prompt_id") == prompt_id:
                        step = prog_data.get("value", 0)
                        max_steps = prog_data.get("max", 0)
                        
                        # Calculate ETA
                        eta = None
                        if tracker_state['start_time'] and max_steps > 0 and step > 0:
                            elapsed = time.time() - tracker_state['start_time']
                            time_per_step = elapsed / step
                            remaining_steps = max_steps - step
                            eta = time_per_step * remaining_steps
                        
                        progress_callback({
                            "type": "progress",
                            "prompt_id": prompt_id,
                            "step": step,
                            "max_steps": max_steps,
                            "percent": int((step / max_steps) * 100) if max_steps > 0 else 0,
                            "eta_seconds": eta,
                            "message": f"Sampling: {step}/{max_steps} steps ({int((step / max_steps) * 100)}%)" if max_steps > 0 else f"Step {step}"
                        })
                        
                elif msg_type == "execution_cached":
                    cached_data = data.get("data", {})
                    if cached_data.get("prompt_id") == prompt_id:
                        nodes = cached_data.get("nodes", [])
                        if nodes:
                            progress_callback({
                                "type": "cached",
                                "prompt_id": prompt_id,
                                "cached_nodes": len(nodes),
                                "message": f"Using cached results for {len(nodes)} node(s)"
                            })
                            
            except json.JSONDecodeError:
                pass  # Ignore malformed messages
            except Exception as e:
                progress_callback({
                    "type": "error",
                    "prompt_id": prompt_id,
                    "error": str(e),
                    "message": f"WebSocket error: {e}"
                })
        
        def on_error(ws, error):
            if not isinstance(error, websocket.WebSocketConnectionClosedException):
                progress_callback({
                    "type": "error",
                    "prompt_id": prompt_id,
                    "error": str(error),
                    "message": f"WebSocket error: {error}"
                })
        
        def on_close(ws, close_status_code, close_msg):
            tracker_state['running'] = False
        
        def on_open(ws):
            tracker_state['running'] = True
            progress_callback({
                "type": "connected",
                "prompt_id": prompt_id,
                "message": "Connected to progress stream"
            })
        
        # Create WebSocket with client ID
        client_id = str(uuid.uuid4())
        ws_url_with_id = f"{self._ws_url}?clientId={client_id}"
        
        try:
            ws = websocket.WebSocketApp(
                ws_url_with_id,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            tracker_state['ws'] = ws
            
            # Run in background thread
            thread = threading.Thread(target=ws.run_forever, daemon=True)
            tracker_state['thread'] = thread
            thread.start()
            
            # Give WebSocket time to connect
            time.sleep(0.5)
            
            return tracker_state
        except Exception as e:
            progress_callback({
                "type": "error",
                "prompt_id": prompt_id,
                "error": str(e),
                "message": f"Failed to start WebSocket: {e}"
            })
            return None
    
    def _stop_progress_tracker(self, tracker_state: Dict[str, Any]) -> None:
        """Stop WebSocket progress tracking.
        
        Args:
            tracker_state: Tracker state dictionary from _start_progress_tracker
        """
        if not tracker_state:
            return
        
        ws = tracker_state.get('ws')
        if ws:
            ws.close()
        
        thread = tracker_state.get('thread')
        if thread:
            thread.join(timeout=2)
