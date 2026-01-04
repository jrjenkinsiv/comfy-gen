#!/usr/bin/env python3
"""Programmatic image generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --output output.png
"""

import argparse
import json
import requests
import time
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from minio import Minio
from minio.error import S3Error
import yaml

COMFYUI_HOST = "http://192.168.1.215:8188"  # ComfyUI running on moira

# MinIO configuration
MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

def load_workflow(workflow_path):
    """Load workflow JSON."""
    with open(workflow_path, 'r') as f:
        return json.load(f)

def get_available_loras() -> List[str]:
    """Fetch available LoRAs from ComfyUI API."""
    try:
        url = f"{COMFYUI_HOST}/object_info"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            lora_loader_info = data.get("LoraLoader", {})
            lora_input = lora_loader_info.get("input", {})
            required = lora_input.get("required", {})
            lora_name_info = required.get("lora_name", [[]])
            if isinstance(lora_name_info, list) and len(lora_name_info) > 0:
                return lora_name_info[0]
        return []
    except Exception as e:
        print(f"[ERROR] Failed to fetch available LoRAs: {e}")
        return []

def load_lora_presets(preset_file: str = "lora_presets.yaml") -> Dict[str, List[Dict[str, Any]]]:
    """Load LoRA presets from YAML file."""
    preset_path = Path(__file__).parent / preset_file
    if not preset_path.exists():
        return {}
    
    try:
        with open(preset_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get("presets", {})
    except Exception as e:
        print(f"[ERROR] Failed to load LoRA presets: {e}")
        return {}

def parse_lora_arg(lora_str: str) -> Tuple[str, float]:
    """Parse LoRA argument in format 'name:strength' or just 'name'."""
    if ":" in lora_str:
        name, strength_str = lora_str.rsplit(":", 1)
        try:
            strength = float(strength_str)
        except ValueError:
            print(f"[WARN] Invalid strength '{strength_str}' for LoRA '{name}', using 1.0")
            strength = 1.0
    else:
        name = lora_str
        strength = 1.0
    return name, strength

def find_checkpoint_loader(workflow: Dict[str, Any]) -> Optional[str]:
    """Find the CheckpointLoaderSimple node in the workflow."""
    for node_id, node in workflow.items():
        if isinstance(node, dict):
            if node.get("class_type") == "CheckpointLoaderSimple":
                return node_id
    return None

def find_consumers(workflow: Dict[str, Any], source_node_id: str, output_index: int) -> List[Tuple[str, str]]:
    """Find all nodes that consume a specific output from a source node.
    
    Returns list of tuples: (consumer_node_id, input_name)
    """
    consumers = []
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            for input_name, input_value in node["inputs"].items():
                if isinstance(input_value, list) and len(input_value) >= 2:
                    if input_value[0] == source_node_id and input_value[1] == output_index:
                        consumers.append((node_id, input_name))
    return consumers

def inject_loras(workflow: Dict[str, Any], loras: List[Tuple[str, float]]) -> Dict[str, Any]:
    """Inject LoRA nodes into the workflow.
    
    Args:
        workflow: The workflow dictionary to modify
        loras: List of (lora_name, strength) tuples
        
    Returns:
        Modified workflow dictionary
    """
    if not loras:
        return workflow
    
    # Find the checkpoint loader
    checkpoint_node_id = find_checkpoint_loader(workflow)
    if not checkpoint_node_id:
        print("[ERROR] No CheckpointLoaderSimple node found in workflow")
        return workflow
    
    print(f"[INFO] Found CheckpointLoader at node {checkpoint_node_id}")
    
    # Find all consumers of the checkpoint's model (output 0) and clip (output 1)
    model_consumers = find_consumers(workflow, checkpoint_node_id, 0)
    clip_consumers = find_consumers(workflow, checkpoint_node_id, 1)
    
    print(f"[INFO] Model consumers: {model_consumers}")
    print(f"[INFO] CLIP consumers: {clip_consumers}")
    
    # Find the highest node ID
    max_id = max(int(k) for k in workflow.keys())
    
    # Chain LoRAs
    current_model_source = [checkpoint_node_id, 0]
    current_clip_source = [checkpoint_node_id, 1]
    
    for idx, (lora_name, strength) in enumerate(loras):
        new_id = str(max_id + 1 + idx)
        
        # Create LoraLoader node
        workflow[new_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": current_model_source,
                "clip": current_clip_source,
                "lora_name": lora_name,
                "strength_model": strength,
                "strength_clip": strength
            },
            "_meta": {
                "title": f"LoRA {idx + 1}: {lora_name}"
            }
        }
        
        print(f"[INFO] Added LoraLoader node {new_id}: {lora_name} (strength={strength})")
        
        # Update sources for next LoRA in chain
        current_model_source = [new_id, 0]
        current_clip_source = [new_id, 1]
    
    # Rewire all model consumers to use the last LoRA's output
    for consumer_id, input_name in model_consumers:
        workflow[consumer_id]["inputs"][input_name] = current_model_source
        print(f"[INFO] Rewired node {consumer_id}.{input_name} -> {current_model_source}")
    
    # Rewire all clip consumers to use the last LoRA's output
    for consumer_id, input_name in clip_consumers:
        workflow[consumer_id]["inputs"][input_name] = current_clip_source
        print(f"[INFO] Rewired node {consumer_id}.{input_name} -> {current_clip_source}")
    
    return workflow

def validate_loras(loras: List[Tuple[str, float]]) -> bool:
    """Validate that all specified LoRAs exist on the server."""
    available_loras = get_available_loras()
    if not available_loras:
        print("[WARN] Could not fetch available LoRAs from server")
        return True  # Proceed anyway, server will error if LoRA doesn't exist
    
    all_valid = True
    for lora_name, _ in loras:
        if lora_name not in available_loras:
            print(f"[ERROR] LoRA not found: {lora_name}")
            print(f"[ERROR] Available LoRAs: {', '.join(available_loras[:5])}...")
            all_valid = False
    
    return all_valid

def modify_prompt(workflow, new_prompt):
    """Modify the prompt in the workflow."""
    # This depends on the workflow structure
    # Assume there's a node with "text" field for prompt
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            if "text" in node["inputs"]:
                node["inputs"]["text"] = new_prompt
                print(f"Updated prompt in node {node_id}")
                break
    return workflow

def queue_workflow(workflow):
    """Send workflow to ComfyUI server."""
    url = f"{COMFYUI_HOST}/prompt"
    response = requests.post(url, json={"prompt": workflow})
    if response.status_code == 200:
        result = response.json()
        prompt_id = result["prompt_id"]
        print(f"Queued workflow with ID: {prompt_id}")
        return prompt_id
    else:
        print(f"Error queuing workflow: {response.text}")
        return None

def wait_for_completion(prompt_id):
    """Wait for workflow to complete."""
    url = f"{COMFYUI_HOST}/history/{prompt_id}"
    while True:
        response = requests.get(url)
        if response.status_code == 200:
            history = response.json()
            if prompt_id in history:
                status = history[prompt_id]
                if "outputs" in status:
                    print("Workflow completed!")
                    return status
                elif "status" in status and status["status"]["completed"] is False:
                    print("Workflow in progress...")
                else:
                    print("Workflow status unknown")
            else:
                print("Prompt ID not found in history")
        else:
            print(f"Error checking status: {response.text}")
        time.sleep(5)

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

def main():
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--lora", action="append", dest="loras", metavar="NAME:STRENGTH",
                        help="Add LoRA (can be repeated). Format: lora_name.safetensors:strength")
    parser.add_argument("--lora-preset", metavar="PRESET_NAME",
                        help="Use a LoRA preset from lora_presets.yaml")
    parser.add_argument("--list-loras", action="store_true",
                        help="List available LoRAs and exit")
    args = parser.parse_args()

    # Handle --list-loras
    if args.list_loras:
        print("[INFO] Fetching available LoRAs from ComfyUI server...")
        loras = get_available_loras()
        if loras:
            print(f"\n[OK] Found {len(loras)} LoRAs:\n")
            for lora in sorted(loras):
                print(f"  - {lora}")
        else:
            print("[ERROR] No LoRAs found or failed to connect to server")
            sys.exit(1)
        sys.exit(0)

    # Validate required arguments for generation
    if not args.workflow:
        parser.error("--workflow is required for generation")
    if not args.prompt:
        parser.error("--prompt is required for generation")

    # Parse LoRA arguments
    loras_to_inject: List[Tuple[str, float]] = []
    
    # Handle --lora-preset
    if args.lora_preset:
        presets = load_lora_presets()
        if args.lora_preset in presets:
            preset_loras = presets[args.lora_preset]
            for lora_def in preset_loras:
                lora_name = lora_def.get("name")
                strength = lora_def.get("strength", 1.0)
                if lora_name:
                    loras_to_inject.append((lora_name, strength))
                    print(f"[INFO] Added LoRA from preset '{args.lora_preset}': {lora_name} (strength={strength})")
        else:
            print(f"[ERROR] LoRA preset '{args.lora_preset}' not found")
            presets_list = list(presets.keys())
            if presets_list:
                print(f"[ERROR] Available presets: {', '.join(presets_list)}")
            sys.exit(1)
    
    # Handle --lora arguments
    if args.loras:
        for lora_arg in args.loras:
            lora_name, strength = parse_lora_arg(lora_arg)
            loras_to_inject.append((lora_name, strength))
            print(f"[INFO] Added LoRA: {lora_name} (strength={strength})")
    
    # Validate LoRAs if any were specified
    if loras_to_inject:
        if not validate_loras(loras_to_inject):
            print("[ERROR] LoRA validation failed")
            sys.exit(1)

    workflow = load_workflow(args.workflow)
    
    # Inject LoRAs if specified
    if loras_to_inject:
        workflow = inject_loras(workflow, loras_to_inject)
    
    workflow = modify_prompt(workflow, args.prompt)

    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        sys.exit(1)

    status = wait_for_completion(prompt_id)
    if status:
        if download_output(status, args.output):
            # Upload to MinIO
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_{Path(args.output).name}"
            minio_url = upload_to_minio(args.output, object_name)
            if minio_url:
                print(f"Image available at: {minio_url}")
            else:
                print("Failed to upload to MinIO")

if __name__ == "__main__":
    main()