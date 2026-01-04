#!/usr/bin/env python3
"""Programmatic image generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --negative-prompt "negative prompt" --output output.png
"""

import argparse
import json
import os
import random
import re
import signal
import sys
import tempfile
import threading
import time
import uuid
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
import websocket
import yaml
from minio import Minio
from minio.error import S3Error
from PIL import Image

COMFYUI_HOST = "http://192.168.1.215:8188"  # ComfyUI running on moira

# MinIO configuration
MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG_ERROR = 2

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
RETRY_BACKOFF = 2  # exponential backoff multiplier

# Default negative prompts
DEFAULT_SD_NEGATIVE_PROMPT = "bad quality, blurry, low resolution, watermark, text, deformed, ugly, duplicate"

# WebSocket configuration
WS_CONNECT_DELAY = 0.5  # seconds to wait for WebSocket connection
WS_POLL_INTERVAL = 2  # seconds between status polling
WS_THREAD_JOIN_TIMEOUT = 2  # seconds to wait for thread to join
WS_COMPLETION_CHECK_INTERVAL = 0.5  # seconds between completion checks


class ProgressTracker:
    """Track real-time progress via ComfyUI WebSocket."""
    
    def __init__(self, prompt_id, quiet=False, json_progress=False):
        """Initialize progress tracker.
        
        Args:
            prompt_id: The prompt ID to track
            quiet: Suppress progress output
            json_progress: Output machine-readable JSON progress
        """
        self.prompt_id = prompt_id
        self.quiet = quiet
        self.json_progress = json_progress
        self.ws = None
        self.completed = False
        self.error = None
        self.start_time = None
        self.current_node = None
        self.running = False
        self.thread = None
        
    def _log(self, message, prefix="[INFO]"):
        """Log a message respecting quiet mode."""
        if not self.quiet and not self.json_progress:
            print(f"{prefix} {message}")
    
    def _log_progress(self, data):
        """Log progress update."""
        if self.json_progress:
            print(json.dumps(data))
        elif not self.quiet:
            # Format human-readable progress
            if "step" in data and "max_steps" in data:
                step = data["step"]
                max_steps = data["max_steps"]
                percent = int((step / max_steps) * 100) if max_steps > 0 else 0
                eta_str = ""
                if "eta_seconds" in data and data["eta_seconds"] is not None:
                    eta_str = f" - ETA: {int(data['eta_seconds'])}s"
                print(f"[PROGRESS] Sampling: {step}/{max_steps} steps ({percent}%){eta_str}")
            elif "node" in data:
                print(f"[PROGRESS] {data['node']}")
    
    def _on_message(self, ws, message):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # Only process messages for our prompt_id
            if msg_type == "execution_start":
                prompt_info = data.get("data", {}).get("prompt_id")
                if prompt_info == self.prompt_id:
                    self.start_time = time.time()
                    self._log("Generation started")
                    
            elif msg_type == "executing":
                exec_data = data.get("data", {})
                if exec_data.get("prompt_id") == self.prompt_id:
                    node = exec_data.get("node")
                    if node is None:
                        # Execution complete
                        self.completed = True
                        elapsed = time.time() - self.start_time if self.start_time else 0
                        self._log(f"Generation complete in {elapsed:.1f}s", "[OK]")
                    else:
                        self.current_node = node
                        
            elif msg_type == "progress":
                prog_data = data.get("data", {})
                if prog_data.get("prompt_id") == self.prompt_id:
                    step = prog_data.get("value", 0)
                    max_steps = prog_data.get("max", 0)
                    
                    # Calculate ETA
                    eta = None
                    if self.start_time and max_steps > 0 and step > 0:
                        elapsed = time.time() - self.start_time
                        time_per_step = elapsed / step
                        remaining_steps = max_steps - step
                        eta = time_per_step * remaining_steps
                    
                    self._log_progress({
                        "step": step,
                        "max_steps": max_steps,
                        "eta_seconds": eta,
                        "node": self.current_node
                    })
                    
            elif msg_type == "execution_cached":
                cached_data = data.get("data", {})
                if cached_data.get("prompt_id") == self.prompt_id:
                    nodes = cached_data.get("nodes", [])
                    if nodes:
                        self._log(f"Using cached results for {len(nodes)} node(s)")
                        
            elif msg_type == "executed":
                exec_data = data.get("data", {})
                if exec_data.get("prompt_id") == self.prompt_id:
                    node = exec_data.get("node")
                    if node:
                        self._log_progress({"node": f"Completed node {node}"})
                        
        except json.JSONDecodeError as e:
            # Log malformed JSON in non-quiet mode for debugging
            if not self.quiet:
                print(f"[WARN] Malformed WebSocket message: {e}")
        except Exception as e:
            if not self.quiet:
                print(f"[WARN] Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        if not isinstance(error, websocket.WebSocketConnectionClosedException):
            self.error = str(error)
            if not self.quiet:
                print(f"[WARN] WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close."""
        self.running = False
    
    def _on_open(self, ws):
        """Handle WebSocket open."""
        self.running = True
        self._log("Connected to progress stream")
    
    def start(self):
        """Start tracking progress in background thread."""
        ws_url = "ws://192.168.1.215:8188/ws"
        
        # Create WebSocket with client ID
        client_id = str(uuid.uuid4())
        ws_url_with_id = f"{ws_url}?clientId={client_id}"
        
        self.ws = websocket.WebSocketApp(
            ws_url_with_id,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Run in background thread
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        
        # Give WebSocket time to connect
        time.sleep(WS_CONNECT_DELAY)
    
    def stop(self):
        """Stop tracking progress."""
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=WS_THREAD_JOIN_TIMEOUT)
    
    def wait_for_completion(self, timeout=None):
        """Wait for generation to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (None for no timeout)
            
        Returns:
            bool: True if completed, False if timed out or error
        """
        start = time.time()
        while not self.completed:
            if self.error:
                return False
            if timeout and (time.time() - start) > timeout:
                return False
            time.sleep(WS_COMPLETION_CHECK_INTERVAL)
        return True


def check_server_availability():
    """Check if ComfyUI server is available.
    
    Returns:
        bool: True if server is reachable, False otherwise
    """
    try:
        response = requests.get(f"{COMFYUI_HOST}/system_stats", timeout=5)
        if response.status_code == 200:
            print("[OK] ComfyUI server is available")
            return True
        else:
            print(f"[ERROR] ComfyUI server returned status {response.status_code}")
            print(f"[ERROR] Server may be starting up or experiencing issues. Please check the server logs.")
            return False
    except requests.ConnectionError:
        print(f"[ERROR] Cannot connect to ComfyUI server at {COMFYUI_HOST}")
        print(f"[ERROR] Make sure ComfyUI is running on moira (192.168.1.215:8188)")
        return False
    except requests.Timeout:
        print(f"[ERROR] Connection to ComfyUI server timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to check server availability: {e}")
        return False

def get_available_models():
    """Query available models from ComfyUI API.
    
    Returns:
        dict: Dictionary of available models by type, or None on failure
    """
    try:
        response = requests.get(f"{COMFYUI_HOST}/object_info", timeout=10)
        if response.status_code == 200:
            object_info = response.json()
            
            # Extract model information
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
            
            print(f"[OK] Retrieved available models from server")
            return models
        else:
            print(f"[ERROR] Failed to get model list: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to query available models: {e}")
        return None

def find_model_fallbacks(requested_model, available_models, model_type="checkpoints"):
    """Suggest fallback models when requested model is not found.
    
    Args:
        requested_model: The model that was requested
        available_models: Dictionary of available models from get_available_models()
        model_type: Type of model (checkpoints, loras, vae)
    
    Returns:
        list: List of suggested fallback models
    """
    if not available_models or model_type not in available_models:
        return []
    
    models = available_models[model_type]
    if not models:
        return []
    
    # Simple string matching - suggest models with similar names
    requested_lower = requested_model.lower()
    suggestions = []
    
    # Extract key terms from requested model
    requested_base = requested_lower.replace('.safetensors', '').replace('.ckpt', '').replace('.pt', '')
    
    for model in models:
        model_base = model.lower().replace('.safetensors', '').replace('.ckpt', '').replace('.pt', '')
        
        # Check for substring matches
        if requested_base in model_base or model_base in requested_base:
            suggestions.append(model)
        # Check for common prefixes (e.g., "sd15" matches "sd15-v1-5")
        elif any(term in model_base for term in requested_base.split('-')):
            suggestions.append(model)
    
    return suggestions[:5]  # Return top 5 suggestions

def validate_workflow_models(workflow, available_models):
    """Validate that all models referenced in workflow exist.
    
    Args:
        workflow (dict): The workflow dictionary containing node definitions
        available_models (dict): Dictionary of available models from get_available_models()
    
    Returns:
        tuple: (is_valid (bool), missing_models (list of tuples), suggestions (dict))
            - is_valid: True if all models exist, False otherwise
            - missing_models: List of (model_type, model_name) tuples for missing models
            - suggestions: Dict mapping missing model names to lists of suggested alternatives
    """
    if not available_models:
        print("[WARN] Cannot validate models - model list unavailable")
        return True, [], {}
    
    missing_models = []
    suggestions = {}
    
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})
        
        # Check checkpoint models
        if class_type == "CheckpointLoaderSimple" and "ckpt_name" in inputs:
            ckpt = inputs["ckpt_name"]
            if "checkpoints" in available_models and ckpt not in available_models["checkpoints"]:
                missing_models.append(("checkpoint", ckpt))
                fallbacks = find_model_fallbacks(ckpt, available_models, "checkpoints")
                if fallbacks:
                    suggestions[ckpt] = fallbacks
        
        # Check LoRA models
        elif class_type == "LoraLoader" and "lora_name" in inputs:
            lora = inputs["lora_name"]
            if "loras" in available_models and lora not in available_models["loras"]:
                missing_models.append(("lora", lora))
                fallbacks = find_model_fallbacks(lora, available_models, "loras")
                if fallbacks:
                    suggestions[lora] = fallbacks
        
        # Check VAE models
        elif class_type == "VAELoader" and "vae_name" in inputs:
            vae = inputs["vae_name"]
            if "vae" in available_models and vae not in available_models["vae"]:
                missing_models.append(("vae", vae))
                fallbacks = find_model_fallbacks(vae, available_models, "vae")
                if fallbacks:
                    suggestions[vae] = fallbacks
    
    is_valid = len(missing_models) == 0
    return is_valid, missing_models, suggestions

def load_lora_presets():
    """Load LoRA catalog from lora_catalog.yaml.
    
    Returns:
        dict: Catalog dictionary with 'loras' (list of LoRA metadata) and 
              'model_suggestions' (dict of presets), or empty dict on failure
    """
    catalog_path = Path(__file__).parent / "lora_catalog.yaml"
    if not catalog_path.exists():
        print("[WARN] lora_catalog.yaml not found")
        return {}
    
    try:
        with open(catalog_path, 'r') as f:
            catalog = yaml.safe_load(f)
        return catalog or {}
    except Exception as e:
        print(f"[ERROR] Failed to load lora_catalog.yaml: {e}")
        return {}

def list_available_loras(available_models=None):
    """List available LoRAs from ComfyUI server and catalog.
    
    Args:
        available_models: Optional pre-fetched model dict from get_available_models()
    
    Returns:
        list: List of available LoRA filenames
    """
    if available_models is None:
        available_models = get_available_models()
    
    if available_models and "loras" in available_models:
        return available_models["loras"]
    return []

def validate_lora_exists(lora_name, available_loras=None):
    """Validate that a LoRA file exists on the server.
    
    Args:
        lora_name: The LoRA filename to validate
        available_loras: Optional pre-fetched list of available LoRAs
    
    Returns:
        bool: True if LoRA exists, False otherwise
    """
    if available_loras is None:
        available_loras = list_available_loras()
    
    return lora_name in available_loras

def find_model_output_connections(workflow, node_id, output_index=0):
    """Find all nodes that connect to a specific output of a node.
    
    Args:
        workflow: The workflow dictionary
        node_id: The source node ID
        output_index: The output index to search for (default 0)
    
    Returns:
        list: List of tuples (target_node_id, input_key) that connect to this output
    """
    connections = []
    for target_id, target_node in workflow.items():
        if "inputs" not in target_node:
            continue
        
        for input_key, input_value in target_node["inputs"].items():
            # Input connections are [node_id, output_index]
            if isinstance(input_value, list) and len(input_value) == 2:
                if input_value[0] == node_id and input_value[1] == output_index:
                    connections.append((target_id, input_key))
    
    return connections

def inject_lora(workflow, lora_name, strength_model=1.0, strength_clip=1.0, insert_after=None):
    """Inject a LoRA loader node into the workflow.
    
    Args:
        workflow: The workflow dictionary
        lora_name: The LoRA filename
        strength_model: Model strength (default 1.0)
        strength_clip: CLIP strength (default 1.0)
        insert_after: Optional node ID to insert after. If None, finds CheckpointLoader or UNETLoader
    
    Returns:
        tuple: (modified_workflow, new_node_id) or (workflow, None) on failure
    """
    # Find the highest node ID
    numeric_keys = [int(k) for k in workflow.keys() if k.isdigit()]
    if not numeric_keys:
        print("[ERROR] Cannot inject LoRA: No numeric node IDs found in workflow")
        return workflow, None
    
    max_id = max(numeric_keys)
    new_id = str(max_id + 1)
    
    # Find the model loader node if not specified
    if insert_after is None:
        # Look for CheckpointLoaderSimple (SD 1.5) or UNETLoader (Wan 2.2)
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            if class_type in ["CheckpointLoaderSimple", "UNETLoader"]:
                insert_after = node_id
                break
    
    if insert_after is None:
        print("[ERROR] Cannot inject LoRA: No checkpoint or UNET loader found in workflow")
        return workflow, None
    
    # Get the source node
    source_node = workflow.get(insert_after)
    if not source_node:
        print(f"[ERROR] Cannot inject LoRA: Source node {insert_after} not found")
        return workflow, None
    
    source_class = source_node.get("class_type", "")
    
    # Determine which outputs to use based on source node type
    if source_class == "CheckpointLoaderSimple":
        # CheckpointLoader outputs: [0]=MODEL, [1]=CLIP, [2]=VAE
        model_output = [insert_after, 0]
        clip_output = [insert_after, 1]
    elif source_class == "UNETLoader":
        # UNETLoader outputs: [0]=MODEL only
        model_output = [insert_after, 0]
        # For Wan 2.2, CLIP comes from DualCLIPLoader - find it
        clip_output = None
        for node_id, node in workflow.items():
            if node.get("class_type") == "DualCLIPLoader":
                clip_output = [node_id, 0]
                break
        if clip_output is None:
            print("[WARN] No CLIP loader found for LoRA, using model connection only")
            clip_output = model_output  # Fallback
    elif source_class == "LoraLoader":
        # Chaining LoRAs - connect to previous LoRA's outputs
        model_output = [insert_after, 0]
        clip_output = [insert_after, 1]
    else:
        print(f"[ERROR] Cannot inject LoRA after node type: {source_class}")
        return workflow, None
    
    # Create the LoRA loader node
    lora_node = {
        "class_type": "LoraLoader",
        "inputs": {
            "model": model_output,
            "clip": clip_output,
            "lora_name": lora_name,
            "strength_model": strength_model,
            "strength_clip": strength_clip
        },
        "_meta": {
            "title": f"LoRA: {lora_name}"
        }
    }
    
    # Add the node to workflow
    workflow[new_id] = lora_node
    
    # Find all connections from the source node's model output (index 0)
    # and redirect them to the new LoRA node
    connections = find_model_output_connections(workflow, insert_after, 0)
    
    for target_id, input_key in connections:
        # Skip the LoRA node we just created
        if target_id == new_id:
            continue
        
        # Redirect this connection to point to the LoRA node instead
        workflow[target_id]["inputs"][input_key] = [new_id, 0]
    
    # Also redirect CLIP connections if applicable
    if source_class == "CheckpointLoaderSimple":
        clip_connections = find_model_output_connections(workflow, insert_after, 1)
        for target_id, input_key in clip_connections:
            if target_id == new_id:
                continue
            workflow[target_id]["inputs"][input_key] = [new_id, 1]
    
    print(f"[OK] Injected LoRA '{lora_name}' as node {new_id} (strength: {strength_model})")
    return workflow, new_id

def inject_lora_chain(workflow, lora_specs, available_loras=None):
    """Inject multiple LoRAs in a chain.
    
    Args:
        workflow: The workflow dictionary
        lora_specs: List of tuples (lora_name, strength_model, strength_clip)
        available_loras: Optional pre-fetched list of available LoRAs
    
    Returns:
        dict: Modified workflow with LoRA chain injected
    """
    if not lora_specs:
        return workflow
    
    # Validate all LoRAs exist before injecting
    if available_loras is None:
        available_loras = list_available_loras()
    
    for lora_name, _, _ in lora_specs:
        if not validate_lora_exists(lora_name, available_loras):
            print(f"[ERROR] LoRA not found: {lora_name}")
            print(f"[ERROR] Available LoRAs: {', '.join(available_loras[:10])}...")
            return workflow
    
    # Inject LoRAs in order, chaining them together
    last_node_id = None
    for lora_name, strength_model, strength_clip in lora_specs:
        workflow, last_node_id = inject_lora(
            workflow, 
            lora_name, 
            strength_model, 
            strength_clip,
            insert_after=last_node_id  # Chain to previous LoRA
        )
        if last_node_id is None:
            print(f"[ERROR] Failed to inject LoRA: {lora_name}")
            break
    
    return workflow

def load_workflow(workflow_path):
    """Load workflow JSON."""
    with open(workflow_path, 'r') as f:
        return json.load(f)

def download_image(url, temp_path):
    """Download image from URL to temporary file."""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            print(f"[OK] Downloaded image from {url}")
            return True
        else:
            print(f"[ERROR] Failed to download image: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to download image: {e}")
        return False

def preprocess_image(image_path, resize=None, crop=None):
    """Preprocess image with resize and crop options.
    
    Args:
        image_path: Path to input image
        resize: Tuple of (width, height) or None
        crop: Crop mode - 'center', 'cover', 'contain', or None
    
    Returns:
        Path to processed image (same as input if no processing)
    """
    if not resize and not crop:
        return image_path
    
    try:
        img = Image.open(image_path)
        original_size = img.size
        
        # Handle resize
        if resize:
            target_w, target_h = resize
            
            if crop == 'cover':
                # Scale to cover target, crop excess
                scale = max(target_w / img.width, target_h / img.height)
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Center crop
                left = (new_w - target_w) // 2
                top = (new_h - target_h) // 2
                img = img.crop((left, top, left + target_w, top + target_h))
                
            elif crop == 'contain':
                # Scale to fit inside target, pad if needed
                scale = min(target_w / img.width, target_h / img.height)
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                
                # Create padded image
                padded = Image.new('RGB', (target_w, target_h), (0, 0, 0))
                paste_x = (target_w - new_w) // 2
                paste_y = (target_h - new_h) // 2
                padded.paste(img, (paste_x, paste_y))
                img = padded
                
            elif crop == 'center':
                # Resize then center crop
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            else:
                # Simple resize
                img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Save processed image
        img.save(image_path)
        print(f"[OK] Preprocessed image: {original_size} -> {img.size}")
        return image_path
        
    except Exception as e:
        print(f"[ERROR] Failed to preprocess image: {e}")
        return image_path

def upload_image_to_comfyui(image_path):
    """Upload image to ComfyUI input directory.
    
    Args:
        image_path: Local path to image file
    
    Returns:
        Uploaded filename (without path) or None on failure
    """
    try:
        # Generate unique filename to avoid conflicts
        ext = Path(image_path).suffix.lower()
        filename = f"input_{uuid.uuid4().hex[:8]}{ext}"
        
        # Determine MIME type based on extension
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        mime_type = mime_types.get(ext, 'image/png')
        
        url = f"{COMFYUI_HOST}/upload/image"
        with open(image_path, 'rb') as f:
            files = {'image': (filename, f, mime_type)}
            data = {'overwrite': 'true'}
            response = requests.post(url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            uploaded_name = result.get('name', filename)
            print(f"[OK] Uploaded image to ComfyUI: {uploaded_name}")
            return uploaded_name
        else:
            print(f"[ERROR] Failed to upload image: {response.text}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to upload image to ComfyUI: {e}")
        return None

def find_prompt_nodes(workflow):
    """Find positive and negative prompt nodes in workflow.
    
    Searches for CLIPTextEncode nodes by title patterns:
    - Positive: "Positive Prompt", "Motion Prompt", or first CLIPTextEncode
    - Negative: "Negative Prompt"
    
    Returns:
        tuple: (positive_node_id, negative_node_id) where IDs can be None
    """
    positive_node = None
    negative_node = None
    first_clip_node = None
    
    for node_id, node in workflow.items():
        if node.get("class_type") != "CLIPTextEncode":
            continue
            
        # Track first CLIP node as fallback
        if first_clip_node is None:
            first_clip_node = node_id
        
        # Normalize title for matching: lowercase and remove special chars
        title = node.get("_meta", {}).get("title", "")
        title_normalized = re.sub(r'[^a-z0-9]', '', title.lower())
        
        # Match positive prompt patterns (normalized)
        positive_patterns = ['positive', 'motionprompt']
        if any(pattern in title_normalized for pattern in positive_patterns):
            positive_node = node_id
        # Match negative prompt patterns (normalized)
        elif 'negative' in title_normalized:
            negative_node = node_id
    
    # Fallback: use first CLIP node if no positive found
    if positive_node is None and first_clip_node is not None:
        positive_node = first_clip_node
    
    return positive_node, negative_node


def get_default_negative_prompt(workflow):
    """Get default negative prompt based on workflow type.
    
    Args:
        workflow (dict): The workflow dictionary
    
    Returns:
        str: Default negative prompt or empty string
    """
    # Detect workflow type by examining nodes
    has_unet_loader = any(
        node.get("class_type") == "UNETLoader" 
        for node in workflow.values()
    )
    
    has_video_combine = any(
        node.get("class_type") == "VHS_VideoCombine"
        for node in workflow.values()
    )
    
    # Wan 2.2 video workflows (typically don't use negative prompts)
    if has_unet_loader or has_video_combine:
        return ""
    
    # SD 1.5 and similar checkpoints - use quality-focused negative
    return DEFAULT_SD_NEGATIVE_PROMPT


def modify_prompt(workflow, positive_prompt, negative_prompt=""):
    """Modify the prompt in the workflow.
    
    Args:
        workflow (dict): The workflow dictionary
        positive_prompt (str): Positive prompt text
        negative_prompt (str): Negative prompt text (optional)
    
    Returns:
        dict: Modified workflow
    """
    # Find prompt nodes intelligently
    pos_node, neg_node = find_prompt_nodes(workflow)
    
    # Update positive prompt
    if pos_node and "inputs" in workflow[pos_node] and "text" in workflow[pos_node]["inputs"]:
        workflow[pos_node]["inputs"]["text"] = positive_prompt
        print(f"[OK] Updated positive prompt in node {pos_node}")
    else:
        print("[WARN] No positive prompt node found in workflow")
    
    # Handle negative prompt
    if neg_node:
        # Node exists, update it
        if "inputs" in workflow[neg_node] and "text" in workflow[neg_node]["inputs"]:
            # Use provided negative or default
            if not negative_prompt:
                negative_prompt = get_default_negative_prompt(workflow)
            workflow[neg_node]["inputs"]["text"] = negative_prompt
            if negative_prompt:
                print(f"[OK] Updated negative prompt in node {neg_node}")
            else:
                print(f"[OK] Cleared negative prompt in node {neg_node}")
    else:
        # No negative node in workflow
        if negative_prompt:
            print("[WARN] Workflow has no negative prompt node (this is normal for Wan 2.2 workflows)")
    
    return workflow

def modify_input_image(workflow, uploaded_filename):
    """Modify workflow to use uploaded input image.
    
    Searches for LoadImage nodes and updates the image filename.
    """
    found = False
    for node_id, node in workflow.items():
        if node.get("class_type") == "LoadImage":
            if "inputs" in node:
                node["inputs"]["image"] = uploaded_filename
                print(f"Updated input image in node {node_id}: {uploaded_filename}")
                found = True
    
    if not found:
        print("[WARN] No LoadImage node found in workflow")
    
    return workflow

def modify_denoise(workflow, denoise_value):
    """Modify denoise strength in KSampler node."""
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            if "inputs" in node:
                node["inputs"]["denoise"] = denoise_value
                print(f"Updated denoise strength in node {node_id}: {denoise_value}")
    return workflow

def modify_sampler_params(workflow, steps=None, cfg=None, seed=None, sampler_name=None, scheduler=None):
    """Modify KSampler parameters in workflow.
    
    Args:
        workflow: The workflow dictionary
        steps: Number of sampling steps (optional)
        cfg: Classifier-free guidance scale (optional)
        seed: Random seed (optional)
        sampler_name: Sampler algorithm (optional)
        scheduler: Noise scheduler (optional)
    
    Returns:
        dict: Modified workflow
    """
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            if "inputs" in node:
                if steps is not None:
                    node["inputs"]["steps"] = steps
                    print(f"[OK] Updated steps in node {node_id}: {steps}")
                if cfg is not None:
                    node["inputs"]["cfg"] = cfg
                    print(f"[OK] Updated CFG in node {node_id}: {cfg}")
                if seed is not None:
                    node["inputs"]["seed"] = seed
                    print(f"[OK] Updated seed in node {node_id}: {seed}")
                if sampler_name is not None:
                    node["inputs"]["sampler_name"] = sampler_name
                    print(f"[OK] Updated sampler in node {node_id}: {sampler_name}")
                if scheduler is not None:
                    node["inputs"]["scheduler"] = scheduler
                    print(f"[OK] Updated scheduler in node {node_id}: {scheduler}")
    return workflow

def modify_dimensions(workflow, width=None, height=None):
    """Modify output dimensions in EmptyLatentImage node.
    
    Args:
        workflow: The workflow dictionary
        width: Output width in pixels (optional)
        height: Output height in pixels (optional)
    
    Returns:
        dict: Modified workflow
    """
    for node_id, node in workflow.items():
        if node.get("class_type") == "EmptyLatentImage":
            if "inputs" in node:
                if width is not None:
                    node["inputs"]["width"] = width
                    print(f"[OK] Updated width in node {node_id}: {width}")
                if height is not None:
                    node["inputs"]["height"] = height
                    print(f"[OK] Updated height in node {node_id}: {height}")
    return workflow

def validate_generation_params(steps=None, cfg=None, denoise=None, width=None, height=None):
    """Validate generation parameters are within acceptable ranges.
    
    Args:
        steps: Number of sampling steps
        cfg: Classifier-free guidance scale
        denoise: Denoising strength
        width: Output width
        height: Output height
    
    Returns:
        tuple: (is_valid, error_message) where error_message is None if valid
    """
    if steps is not None:
        if not isinstance(steps, int) or steps < 1 or steps > 150:
            return False, f"Steps must be an integer between 1 and 150, got: {steps}"
    
    if cfg is not None:
        if not isinstance(cfg, (int, float)) or cfg < 1.0 or cfg > 20.0:
            return False, f"CFG must be a number between 1.0 and 20.0, got: {cfg}"
    
    if denoise is not None:
        if not isinstance(denoise, (int, float)) or denoise < 0.0 or denoise > 1.0:
            return False, f"Denoise must be a number between 0.0 and 1.0, got: {denoise}"
    
    if width is not None:
        if not isinstance(width, int) or width < 64 or width > 2048:
            return False, f"Width must be an integer between 64 and 2048, got: {width}"
        if width % 8 != 0:
            return False, f"Width must be divisible by 8, got: {width}"
    
    if height is not None:
        if not isinstance(height, int) or height < 64 or height > 2048:
            return False, f"Height must be an integer between 64 and 2048, got: {height}"
        if height % 8 != 0:
            return False, f"Height must be divisible by 8, got: {height}"
    
    return True, None

def load_presets():
    """Load generation presets from presets.yaml.
    
    Returns:
        dict: Presets dictionary or empty dict on failure
    """
    presets_path = Path(__file__).parent / "presets.yaml"
    if not presets_path.exists():
        return {}
    
    try:
        with open(presets_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get("presets", {}) if data else {}
    except Exception as e:
        print(f"[ERROR] Failed to load presets.yaml: {e}")
        return {}


def load_config():
    """Load full configuration from presets.yaml including validation settings.
    
    Returns:
        dict: Full config with keys: presets, default_negative_prompt, validation
    """
    presets_path = Path(__file__).parent / "presets.yaml"
    if not presets_path.exists():
        return {"presets": {}, "default_negative_prompt": "", "validation": {}}
    
    try:
        with open(presets_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        return {
            "presets": data.get("presets", {}),
            "default_negative_prompt": data.get("default_negative_prompt", ""),
            "validation": data.get("validation", {})
        }
    except Exception as e:
        print(f"[ERROR] Failed to load presets.yaml: {e}")
        return {"presets": {}, "default_negative_prompt": "", "validation": {}}

def queue_workflow(workflow, retry=True):
    """Send workflow to ComfyUI server with retry logic.
    
    Args:
        workflow: The workflow dictionary
        retry: Whether to retry on transient failures
    
    Returns:
        str: prompt_id on success, None on failure
    """
    url = f"{COMFYUI_HOST}/prompt"
    
    # Filter out metadata keys (non-numeric) - ComfyUI only accepts node IDs
    filtered_workflow = {k: v for k, v in workflow.items() if k.isdigit()}
    
    max_attempts = MAX_RETRIES if retry else 1
    delay = RETRY_DELAY
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(url, json={"prompt": filtered_workflow}, timeout=30)
            if response.status_code == 200:
                result = response.json()
                prompt_id = result["prompt_id"]
                print(f"Queued workflow with ID: {prompt_id}")
                return prompt_id
            else:
                print(f"[ERROR] Failed to queue workflow: HTTP {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                
                # Don't retry on client errors (4xx)
                if 400 <= response.status_code < 500:
                    return None
                
                # Retry on server errors (5xx)
                if attempt < max_attempts:
                    print(f"[INFO] Retrying in {delay} seconds... (attempt {attempt}/{max_attempts})")
                    time.sleep(delay)
                    delay *= RETRY_BACKOFF
                    continue
                
                return None
                
        except requests.ConnectionError as e:
            print(f"[ERROR] Connection error: {e}")
            if attempt < max_attempts:
                print(f"[INFO] Retrying in {delay} seconds... (attempt {attempt}/{max_attempts})")
                time.sleep(delay)
                delay *= RETRY_BACKOFF
                continue
            return None
            
        except requests.Timeout as e:
            print(f"[ERROR] Request timed out: {e}")
            if attempt < max_attempts:
                print(f"[INFO] Retrying in {delay} seconds... (attempt {attempt}/{max_attempts})")
                time.sleep(delay)
                delay *= RETRY_BACKOFF
                continue
            return None
            
        except Exception as e:
            print(f"[ERROR] Unexpected error queuing workflow: {e}")
            return None
    
    return None

def wait_for_completion(prompt_id, quiet=False, json_progress=False):
    """Wait for workflow to complete with real-time progress tracking.
    
    Args:
        prompt_id: The prompt ID to wait for
        quiet: Suppress progress output
        json_progress: Output machine-readable JSON progress
        
    Returns:
        dict: Workflow status/history on completion, None on error
    """
    # Start WebSocket progress tracker
    tracker = ProgressTracker(prompt_id, quiet=quiet, json_progress=json_progress)
    tracker.start()
    
    try:
        # Poll history endpoint to get final status
        url = f"{COMFYUI_HOST}/history/{prompt_id}"
        while True:
            response = requests.get(url)
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    status = history[prompt_id]
                    if "outputs" in status:
                        # Workflow completed successfully
                        tracker.stop()
                        return status
                    elif "status" in status and status["status"].get("completed") is False:
                        # Still in progress, keep waiting
                        pass
                    else:
                        # Unknown status
                        if not quiet:
                            print("[WARN] Workflow status unknown")
                else:
                    # Prompt not in history yet
                    pass
            else:
                if not quiet:
                    print(f"[ERROR] Error checking status: {response.text}")
            
            time.sleep(WS_POLL_INTERVAL)  # Poll less frequently since we have WebSocket updates
    finally:
        tracker.stop()
    
    return None

def download_output(status, output_path):
    """Download the generated image."""
    # Assume output is in outputs node
    outputs = status.get("outputs", {})
    for node_id, node_outputs in outputs.items():
        if "images" in node_outputs:
            for image in node_outputs["images"]:
                filename = image["filename"]
                subfolder = image.get("subfolder", "")
                url = f"{COMFYUI_HOST}/view?filename={filename}&subfolder={subfolder}&type=output"
                response = requests.get(url)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Saved image to {output_path}")
                    return True
                else:
                    print(f"Error downloading image: {response.text}")
    return False

def upload_to_minio(file_path, object_name):
    """Upload file to MinIO with correct content type for browser viewing."""
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False  # HTTP, not HTTPS
        )

        # Make bucket if not exists
        if not client.bucket_exists(BUCKET_NAME):
            client.make_bucket(BUCKET_NAME)
            print(f"[INFO] Created bucket {BUCKET_NAME}")

        # Determine content type based on extension
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

        # Upload with correct content type so browser displays instead of downloads
        client.fput_object(
            BUCKET_NAME, 
            object_name, 
            file_path,
            content_type=content_type
        )
        print(f"[OK] Uploaded {file_path} to MinIO as {object_name}")
        return f"http://192.168.1.215:9000/{BUCKET_NAME}/{object_name}"
    except S3Error as e:
        print(f"[ERROR] MinIO error: {e}")
        return None

def extract_workflow_params(workflow):
    """Extract generation parameters from workflow.
    
    Args:
        workflow: The workflow dictionary
    
    Returns:
        dict: Extracted parameters (seed, steps, cfg, sampler, scheduler)
    """
    params = {
        "seed": None,
        "steps": None,
        "cfg": None,
        "sampler": None,
        "scheduler": None
    }
    
    # Find KSampler node
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            inputs = node.get("inputs", {})
            params["seed"] = inputs.get("seed")
            params["steps"] = inputs.get("steps")
            params["cfg"] = inputs.get("cfg")
            params["sampler"] = inputs.get("sampler_name")
            params["scheduler"] = inputs.get("scheduler")
            break
    
    return params

def extract_loras_from_workflow(workflow):
    """Extract LoRA information from workflow.
    
    Args:
        workflow: The workflow dictionary
    
    Returns:
        list: List of dicts with 'name' and 'strength' for each LoRA
    """
    loras = []
    
    for node_id, node in workflow.items():
        if node.get("class_type") == "LoraLoader":
            inputs = node.get("inputs", {})
            lora_name = inputs.get("lora_name")
            strength_model = inputs.get("strength_model", 1.0)
            
            if lora_name:
                loras.append({
                    "name": lora_name,
                    "strength": strength_model
                })
    
    return loras

def create_metadata_json(
    workflow_path,
    prompt,
    negative_prompt,
    workflow_params,
    loras,
    preset,
    validation_score,
    minio_url
):
    """Create metadata JSON for experiment tracking.
    
    Args:
        workflow_path: Path to workflow file
        prompt: Positive text prompt
        negative_prompt: Negative text prompt
        workflow_params: Dict of workflow parameters (seed, steps, cfg, etc.)
        loras: List of LoRA dicts with name and strength
        preset: Preset name if used
        validation_score: CLIP validation score if validation was run
        minio_url: URL to the generated image in MinIO
    
    Returns:
        dict: Metadata dictionary ready for JSON serialization
    """
    import datetime
    
    metadata = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt": prompt,
        "negative_prompt": negative_prompt if negative_prompt else "",
        "workflow": Path(workflow_path).name,
        "seed": workflow_params.get("seed"),
        "steps": workflow_params.get("steps"),
        "cfg": workflow_params.get("cfg"),
        "sampler": workflow_params.get("sampler"),
        "scheduler": workflow_params.get("scheduler"),
        "loras": loras,
        "preset": preset if preset else None,
        "validation_score": validation_score,
        "minio_url": minio_url
    }
    
    return metadata

def upload_metadata_to_minio(metadata, object_name):
    """Upload metadata JSON to MinIO as a sidecar file.
    
    Args:
        metadata: Metadata dictionary
        object_name: Base object name (e.g., "image.png")
    
    Returns:
        str: URL to uploaded metadata JSON, or None on failure
    """
    try:
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(metadata, f, indent=2)
            temp_path = f.name
        
        try:
            # Upload with .json extension
            json_object_name = f"{object_name}.json"
            
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False
            )
            
            client.fput_object(
                BUCKET_NAME,
                json_object_name,
                temp_path,
                content_type="application/json"
            )
            
            print(f"[OK] Uploaded metadata to MinIO as {json_object_name}")
            return f"http://192.168.1.215:9000/{BUCKET_NAME}/{json_object_name}"
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        print(f"[ERROR] Failed to upload metadata: {e}")
        return None

def interrupt_generation():
    """Interrupt currently running generation."""
    try:
        url = f"{COMFYUI_HOST}/interrupt"
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            print("[OK] Interrupted current generation")
            return True
        else:
            print(f"[ERROR] Failed to interrupt: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to ComfyUI: {e}")
        return False

def delete_from_queue(prompt_ids):
    """Delete specific prompts from queue.
    
    Args:
        prompt_ids: List of prompt IDs to delete
    """
    try:
        url = f"{COMFYUI_HOST}/queue"
        payload = {"delete": prompt_ids}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Deleted {len(prompt_ids)} prompt(s) from queue")
            return True
        else:
            print(f"[ERROR] Failed to delete from queue: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to ComfyUI: {e}")
        return False

def cancel_prompt(prompt_id):
    """Cancel a specific prompt by ID."""
    # First interrupt (in case it's running)
    interrupt_generation()
    # Then delete from queue
    if delete_from_queue([prompt_id]):
        print(f"[OK] Cancelled prompt {prompt_id}")
        return True
    return False

def cleanup_partial_output(output_path):
    """Remove partial output file if it exists."""
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            print(f"[OK] Cleaned up partial output: {output_path}")
        except Exception as e:
            print(f"[WARN] Failed to clean up {output_path}: {e}")

def adjust_prompt_for_retry(
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
    # Extract existing weights from prompt
    weight_pattern = r'\(([^:]+):(\d+\.?\d*)\)'
    
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

# Global variable to track current prompt for signal handler
current_prompt_id = None
current_output_path = None

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n[INFO] Cancellation requested...")
    if current_prompt_id:
        cancel_prompt(current_prompt_id)
    if current_output_path:
        cleanup_partial_output(current_output_path)
    print("[INFO] Cancelled. Exiting.")
    sys.exit(0)

def run_generation(
    workflow: dict,
    output_path: str,
    uploaded_image_filename: str = None,
    quiet: bool = False,
    json_progress: bool = False
) -> tuple:
    """Run a single generation attempt.
    
    Args:
        workflow: The workflow dict with prompts already set
        output_path: Path to save the output
        uploaded_image_filename: Optional uploaded input image filename
        quiet: Suppress progress output
        json_progress: Output machine-readable JSON progress
    
    Returns:
        Tuple of (success: bool, minio_url: str or None, object_name: str or None)
    """
    global current_prompt_id
    
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        return False, None, None
    
    # Track prompt ID for cancellation
    current_prompt_id = prompt_id

    status = wait_for_completion(prompt_id, quiet=quiet, json_progress=json_progress)
    if status:
        if download_output(status, output_path):
            # Upload to MinIO
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_{Path(output_path).name}"
            minio_url = upload_to_minio(output_path, object_name)
            if minio_url:
                if not quiet:
                    print(f"[OK] Image available at: {minio_url}")
                return True, minio_url, object_name
            else:
                if not quiet:
                    print("[ERROR] Failed to upload to MinIO")
                return False, None, None
    
    return False, None, None

def main():
    global current_prompt_id, current_output_path
    
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", help="Positive text prompt")
    parser.add_argument("--negative-prompt", "-n", default="", 
                        help=f"Negative text prompt (what to avoid). If not specified, SD workflows use default: '{DEFAULT_SD_NEGATIVE_PROMPT}'")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--input-image", "-i", help="Input image path (local file or URL) for img2img/I2V")
    parser.add_argument("--resize", help="Resize input image to WxH (e.g., 512x512)")
    parser.add_argument("--crop", choices=['center', 'cover', 'contain'], help="Crop mode for resize")
    parser.add_argument("--denoise", type=float, help="Denoise strength (0.0-1.0) for img2img")
    parser.add_argument("--lora", action="append", metavar="NAME:STRENGTH", 
                        help="Add LoRA with strength (e.g., 'style.safetensors:0.8'). Can be repeated for multiple LoRAs.")
    parser.add_argument("--lora-preset", metavar="PRESET_NAME",
                        help="Use a predefined LoRA preset from lora_catalog.yaml")
    parser.add_argument("--list-loras", action="store_true", 
                        help="List available LoRAs and presets, then exit")
    parser.add_argument("--cancel", metavar="PROMPT_ID", help="Cancel a specific prompt by ID")
    parser.add_argument("--dry-run", action="store_true", help="Validate workflow without generating")
    parser.add_argument("--validate", action="store_true", help="Run validation after generation (default: from config)")
    parser.add_argument("--no-validate", action="store_true", help="Disable validation even if config enables it")
    parser.add_argument("--auto-retry", action="store_true", help="Automatically retry if validation fails (default: from config)")
    parser.add_argument("--retry-limit", type=int, default=None, help="Maximum retry attempts (default: from config or 3)")
    parser.add_argument("--positive-threshold", type=float, default=None, help="Minimum CLIP score for positive prompt (default: from config or 0.25)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--json-progress", action="store_true", help="Output machine-readable JSON progress")
    parser.add_argument("--no-metadata", action="store_true", help="Disable JSON metadata sidecar upload")
    
    # Advanced generation parameters
    parser.add_argument("--steps", type=int, help="Number of sampling steps (1-150, default: 20)")
    parser.add_argument("--cfg", type=float, help="Classifier-free guidance scale (1.0-20.0, default: 7.0)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility (-1 for random, default: random)")
    parser.add_argument("--width", type=int, help="Output width in pixels (must be divisible by 8)")
    parser.add_argument("--height", type=int, help="Output height in pixels (must be divisible by 8)")
    parser.add_argument("--sampler", help="Sampler algorithm (e.g., euler, dpmpp_2m, dpmpp_2m_sde)")
    parser.add_argument("--scheduler", help="Noise scheduler (e.g., normal, karras, exponential)")
    parser.add_argument("--preset", help="Use a generation preset (draft, balanced, high-quality)")
    
    args = parser.parse_args()
    
    # Load configuration for defaults
    config = load_config()
    validation_config = config.get("validation", {})
    
    # Apply config defaults to args (CLI args override config)
    # Validation: --validate forces on, --no-validate forces off, otherwise use config
    if args.no_validate:
        args.validate = False
    elif not args.validate:
        args.validate = validation_config.get("enabled", False)
    
    # Auto-retry: CLI overrides config
    if not args.auto_retry:
        args.auto_retry = validation_config.get("auto_retry", False)
    
    # Retry limit: CLI overrides config
    if args.retry_limit is None:
        args.retry_limit = validation_config.get("retry_limit", 3)
    
    # Positive threshold: CLI overrides config
    if args.positive_threshold is None:
        args.positive_threshold = validation_config.get("positive_threshold", 0.25)
    
    # Default negative prompt from config (applied later if user didn't provide one)
    config_negative_prompt = config.get("default_negative_prompt", "")
    
    # Handle list-loras mode
    if args.list_loras:
        print("[INFO] Querying available LoRAs from ComfyUI server...")
        
        # Check server availability
        if not check_server_availability():
            print("[ERROR] ComfyUI server is not available")
            sys.exit(EXIT_CONFIG_ERROR)
        
        # Get available LoRAs
        available_loras = list_available_loras()
        if available_loras:
            print(f"\n[OK] Available LoRAs ({len(available_loras)}):")
            for lora in sorted(available_loras):
                print(f"  - {lora}")
        else:
            print("[WARN] No LoRAs found")
        
        # Load and display presets
        catalog = load_lora_presets()
        if catalog and "model_suggestions" in catalog:
            presets = {}
            # Extract presets from model_suggestions
            for scenario_name, scenario_data in catalog["model_suggestions"].items():
                if "default_loras" in scenario_data and scenario_data["default_loras"]:
                    presets[scenario_name] = scenario_data["default_loras"]
            
            if presets:
                print(f"\n[OK] Available LoRA presets:")
                for preset_name, lora_list in presets.items():
                    print(f"  - {preset_name}:")
                    for lora_name in lora_list:
                        # Find strength from catalog
                        strength = 1.0
                        if "loras" in catalog:
                            for lora_entry in catalog["loras"]:
                                if lora_entry.get("filename") == lora_name:
                                    strength = lora_entry.get("recommended_strength", 1.0)
                                    break
                        print(f"      {lora_name} (strength: {strength})")
        
        sys.exit(EXIT_SUCCESS)
    
    # Handle cancel mode
    if args.cancel:
        if cancel_prompt(args.cancel):
            sys.exit(EXIT_SUCCESS)
        else:
            sys.exit(EXIT_FAILURE)
    
    # Validate required args for generation mode
    # Note: --cancel and --list-loras exit early and never reach these checks
    if not args.workflow:
        parser.error("--workflow is required")
    
    if not args.dry_run and not args.prompt:
        parser.error("--prompt is required (unless using --dry-run)")
    
    # Check server availability first
    if not check_server_availability():
        print("[ERROR] ComfyUI server is not available")
        sys.exit(EXIT_CONFIG_ERROR)
    
    # Load workflow
    try:
        workflow = load_workflow(args.workflow)
    except FileNotFoundError:
        print(f"[ERROR] Workflow file not found: {args.workflow}")
        sys.exit(EXIT_CONFIG_ERROR)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in workflow file: {e}")
        sys.exit(EXIT_CONFIG_ERROR)
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        sys.exit(EXIT_CONFIG_ERROR)
    
    # Get available models and validate workflow
    available_models = get_available_models()
    if available_models:
        is_valid, missing_models, suggestions = validate_workflow_models(workflow, available_models)
        
        if not is_valid:
            print("[ERROR] Workflow validation failed - missing models:")
            for model_type, model_name in missing_models:
                print(f"  - {model_type}: {model_name}")
                if model_name in suggestions:
                    print(f"    Suggested fallbacks:")
                    for suggestion in suggestions[model_name]:
                        print(f"      * {suggestion}")
            sys.exit(EXIT_CONFIG_ERROR)
        else:
            print("[OK] Workflow validation passed - all models available")
    
    # Handle dry-run mode
    if args.dry_run:
        print("[OK] Dry-run mode - workflow is valid")
        print(f"[OK] Workflow: {args.workflow}")
        if args.prompt:
            print(f"[OK] Prompt: {args.prompt}")
        print("[OK] Validation complete - no generation performed")
        sys.exit(EXIT_SUCCESS)
    
    # Set up Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)
    current_output_path = args.output

    # Apply default negative prompt from config if not provided
    effective_negative_prompt = args.negative_prompt
    if not effective_negative_prompt and config_negative_prompt:
        effective_negative_prompt = config_negative_prompt
        if not args.quiet:
            print(f"[OK] Using default negative prompt from config")

    # Modify workflow with prompts
    workflow = modify_prompt(workflow, args.prompt, effective_negative_prompt)
    
    # Handle input image if provided
    temp_file = None
    uploaded_filename = None
    if args.input_image:
        try:
            # Check if input is URL or local file
            parsed = urlparse(args.input_image)
            if parsed.scheme in ('http', 'https'):
                # Download from URL
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_file.close()
                if not download_image(args.input_image, temp_file.name):
                    print("[ERROR] Failed to download input image")
                    sys.exit(EXIT_FAILURE)
                image_path = temp_file.name
            else:
                # Use local file
                if not os.path.exists(args.input_image):
                    print(f"[ERROR] Input image not found: {args.input_image}")
                    sys.exit(EXIT_CONFIG_ERROR)
                # Copy to temp file for preprocessing
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(args.input_image).suffix)
                temp_file.close()
                with open(args.input_image, 'rb') as src:
                    with open(temp_file.name, 'wb') as dst:
                        dst.write(src.read())
                image_path = temp_file.name
            
            # Preprocess image if needed
            resize = None
            if args.resize:
                try:
                    parts = args.resize.lower().split('x', 1)
                    if len(parts) != 2:
                        raise ValueError("Invalid format")
                    w, h = parts
                    resize = (int(w), int(h))
                except (ValueError, IndexError):
                    print(f"[ERROR] Invalid resize format: {args.resize}. Use WxH (e.g., 512x512)")
                    sys.exit(EXIT_CONFIG_ERROR)
            
            image_path = preprocess_image(image_path, resize=resize, crop=args.crop)
            
            # Upload to ComfyUI
            uploaded_filename = upload_image_to_comfyui(image_path)
            if not uploaded_filename:
                print("[ERROR] Failed to upload input image to ComfyUI")
                sys.exit(EXIT_FAILURE)
            
            # Modify workflow to use uploaded image
            workflow = modify_input_image(workflow, uploaded_filename)
            
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except OSError:
                    pass
    
    # Apply denoise strength if specified
    if args.denoise is not None:
        workflow = modify_denoise(workflow, args.denoise)
    
    # Process LoRA arguments
    lora_specs = []
    
    # Handle --lora-preset
    if args.lora_preset:
        catalog = load_lora_presets()
        if catalog and "model_suggestions" in catalog:
            preset_found = False
            for scenario_name, scenario_data in catalog["model_suggestions"].items():
                if scenario_name == args.lora_preset:
                    preset_found = True
                    if "default_loras" in scenario_data and scenario_data["default_loras"]:
                        print(f"[OK] Loading LoRA preset '{args.lora_preset}'")
                        for lora_name in scenario_data["default_loras"]:
                            # Find recommended strength from catalog
                            strength = 1.0
                            if "loras" in catalog:
                                for lora_entry in catalog["loras"]:
                                    if lora_entry.get("filename") == lora_name:
                                        strength = lora_entry.get("recommended_strength", 1.0)
                                        break
                            lora_specs.append((lora_name, strength, strength))
                            print(f"  - {lora_name} (strength: {strength})")
                    break
            
            if not preset_found:
                print(f"[ERROR] LoRA preset not found: {args.lora_preset}")
                print(f"[ERROR] Available presets: {', '.join(catalog['model_suggestions'].keys())}")
                sys.exit(EXIT_CONFIG_ERROR)
        else:
            print(f"[ERROR] Cannot load LoRA presets from lora_catalog.yaml")
            sys.exit(EXIT_CONFIG_ERROR)
    
    # Handle --lora arguments
    if args.lora:
        for lora_spec in args.lora:
            # Parse "name:strength" format
            # Note: Using rsplit(':', 1) to split from right, which correctly handles
            # paths with colons (e.g., "C:\\path\\lora.safetensors:0.8")
            if ':' in lora_spec:
                parts = lora_spec.rsplit(':', 1)
                lora_name = parts[0]
                try:
                    strength = float(parts[1])
                    if strength < 0:
                        print(f"[ERROR] LoRA strength must be non-negative: {parts[1]}")
                        print(f"[ERROR] Format: 'lora_name.safetensors:0.8'")
                        sys.exit(EXIT_CONFIG_ERROR)
                except ValueError:
                    print(f"[ERROR] Invalid LoRA strength: {parts[1]}")
                    print(f"[ERROR] Format: 'lora_name.safetensors:0.8'")
                    sys.exit(EXIT_CONFIG_ERROR)
            else:
                # No strength specified, use 1.0
                lora_name = lora_spec
                strength = 1.0
            
            lora_specs.append((lora_name, strength, strength))
            print(f"[OK] Adding LoRA: {lora_name} (strength: {strength})")
    
    # Inject LoRAs into workflow
    if lora_specs:
        available_models = get_available_models()
        available_loras = available_models.get("loras", []) if available_models else []
        workflow = inject_lora_chain(workflow, lora_specs, available_loras)
    
    # Handle generation preset
    preset_params = {}
    if args.preset:
        presets = load_presets()
        if args.preset in presets:
            preset_params = presets[args.preset]
            print(f"[OK] Loaded preset '{args.preset}': {preset_params}")
        else:
            available_presets = ', '.join(presets.keys()) if presets else 'none'
            print(f"[ERROR] Preset not found: {args.preset}")
            print(f"[ERROR] Available presets: {available_presets}")
            sys.exit(EXIT_CONFIG_ERROR)
    
    # Merge preset with CLI args (CLI args override preset)
    steps = args.steps if args.steps is not None else preset_params.get('steps')
    cfg = args.cfg if args.cfg is not None else preset_params.get('cfg')
    seed = args.seed if args.seed is not None else preset_params.get('seed')
    width = args.width if args.width is not None else preset_params.get('width')
    height = args.height if args.height is not None else preset_params.get('height')
    sampler = args.sampler if args.sampler is not None else preset_params.get('sampler')
    scheduler = args.scheduler if args.scheduler is not None else preset_params.get('scheduler')
    
    # Handle seed=-1 for random seed generation
    if seed == -1:
        seed = random.randint(0, 2**32 - 1)
        print(f"[OK] Generated random seed: {seed}")
    
    # Validate parameters
    is_valid, error_msg = validate_generation_params(
        steps=steps,
        cfg=cfg,
        denoise=args.denoise,
        width=width,
        height=height
    )
    if not is_valid:
        print(f"[ERROR] Parameter validation failed: {error_msg}")
        sys.exit(EXIT_CONFIG_ERROR)
    
    # Apply sampler parameters to workflow
    if any(p is not None for p in [steps, cfg, seed, sampler, scheduler]):
        workflow = modify_sampler_params(
            workflow,
            steps=steps,
            cfg=cfg,
            seed=seed,
            sampler_name=sampler,
            scheduler=scheduler
        )
    
    # Apply dimension parameters to workflow
    if width is not None or height is not None:
        workflow = modify_dimensions(workflow, width=width, height=height)

    # Extract workflow parameters and LoRAs for metadata
    workflow_params = extract_workflow_params(workflow)
    loras_metadata = extract_loras_from_workflow(workflow)
    
    # Validation and retry loop
    attempt = 0
    max_attempts = args.retry_limit if args.auto_retry else 1
    minio_url = None
    validation_result = None
    
    while attempt < max_attempts:
        attempt += 1
        
        if attempt > 1:
            if not args.quiet:
                print(f"\n[INFO] Retry attempt {attempt}/{max_attempts}")
            # Adjust prompts for retry
            adjusted_positive, adjusted_negative = adjust_prompt_for_retry(
                args.prompt, effective_negative_prompt, attempt - 1
            )
            if not args.quiet:
                print(f"[INFO] Adjusted positive prompt: {adjusted_positive}")
                print(f"[INFO] Adjusted negative prompt: {adjusted_negative}")
            workflow = modify_prompt(workflow, adjusted_positive, adjusted_negative)
        
        # Create metadata for this generation attempt
        metadata = None
        if not args.no_metadata:
            # Get current prompt (may be adjusted for retry)
            current_positive = args.prompt if attempt == 1 else adjusted_positive
            current_negative = effective_negative_prompt if attempt == 1 else adjusted_negative
            
            metadata = create_metadata_json(
                workflow_path=args.workflow,
                prompt=current_positive,
                negative_prompt=current_negative,
                workflow_params=workflow_params,
                loras=loras_metadata,
                preset=args.preset,
                validation_score=None,  # Will be updated if validation runs
                minio_url=None  # Will be updated after upload
            )
        
        # Run generation
        success, minio_url, object_name = run_generation(
            workflow, 
            args.output, 
            uploaded_filename if args.input_image else None,
            quiet=args.quiet,
            json_progress=args.json_progress
        )
        
        if not success:
            if not args.quiet:
                print(f"[ERROR] Generation failed on attempt {attempt}")
            if attempt >= max_attempts:
                sys.exit(EXIT_FAILURE)
            continue
        
        # Run validation if requested
        if args.validate:
            try:
                from comfy_gen.validation import validate_image
                
                if not args.quiet:
                    print(f"[INFO] Running validation...")
                validation_result = validate_image(
                    args.output,
                    args.prompt,
                    effective_negative_prompt if effective_negative_prompt else None,
                    positive_threshold=args.positive_threshold
                )
                
                # Update metadata with validation score
                if metadata and validation_result:
                    metadata["validation_score"] = validation_result.get('positive_score')
                
                if not args.quiet:
                    print(f"[INFO] Validation result: {validation_result['reason']}")
                    print(f"[INFO] Positive score: {validation_result.get('positive_score', 0.0):.3f}")
                    
                    if validation_result.get('negative_score'):
                        print(f"[INFO] Negative score: {validation_result['negative_score']:.3f}")
                        print(f"[INFO] Delta: {validation_result.get('score_delta', 0.0):.3f}")
                
                if validation_result['passed']:
                    if not args.quiet:
                        print(f"[OK] Image passed validation")
                    # Upload metadata after successful validation
                    if metadata and object_name:
                        metadata["minio_url"] = minio_url
                        metadata_url = upload_metadata_to_minio(metadata, object_name)
                        if metadata_url and not args.quiet:
                            print(f"[OK] Metadata available at: {metadata_url}")
                    break
                else:
                    if not args.quiet:
                        print(f"[WARN] Image failed validation: {validation_result['reason']}")
                    if not args.auto_retry:
                        # Validation failed but no retry requested - still save metadata
                        if metadata and object_name:
                            metadata["minio_url"] = minio_url
                            metadata_url = upload_metadata_to_minio(metadata, object_name)
                            if metadata_url and not args.quiet:
                                print(f"[OK] Metadata available at: {metadata_url}")
                        break
                    elif attempt >= max_attempts:
                        if not args.quiet:
                            print(f"[ERROR] Max retries reached. Final validation result:")
                            print(f"  Reason: {validation_result['reason']}")
                            print(f"  Positive score: {validation_result.get('positive_score', 0.0):.3f}")
                        # Save metadata for failed attempt
                        if metadata and object_name:
                            metadata["minio_url"] = minio_url
                            metadata_url = upload_metadata_to_minio(metadata, object_name)
                            if metadata_url and not args.quiet:
                                print(f"[OK] Metadata available at: {metadata_url}")
                        break
                    # Continue to next retry attempt
                    
            except ImportError:
                if not args.quiet:
                    print("[WARN] Validation module not available. Install dependencies: pip install transformers")
                # Upload metadata even if validation failed to import
                if metadata and object_name:
                    metadata["minio_url"] = minio_url
                    metadata_url = upload_metadata_to_minio(metadata, object_name)
                    if metadata_url and not args.quiet:
                        print(f"[OK] Metadata available at: {metadata_url}")
                break
            except Exception as e:
                if not args.quiet:
                    print(f"[ERROR] Validation failed: {e}")
                # Upload metadata even if validation failed
                if metadata and object_name:
                    metadata["minio_url"] = minio_url
                    metadata_url = upload_metadata_to_minio(metadata, object_name)
                    if metadata_url and not args.quiet:
                        print(f"[OK] Metadata available at: {metadata_url}")
                break
        else:
            # No validation requested - upload metadata immediately
            if metadata and object_name:
                metadata["minio_url"] = minio_url
                metadata_url = upload_metadata_to_minio(metadata, object_name)
                if metadata_url and not args.quiet:
                    print(f"[OK] Metadata available at: {metadata_url}")
            break
    
    # Final output
    if minio_url:
        if not args.quiet:
            print(f"\nImage available at: {minio_url}")
        if validation_result and not args.quiet:
            print(f"Validation: {'PASSED' if validation_result['passed'] else 'FAILED'}")
            print(f"Score: {validation_result.get('positive_score', 0.0):.3f}")


if __name__ == "__main__":
    main()