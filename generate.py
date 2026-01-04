#!/usr/bin/env python3
"""Programmatic image generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --output output.png
    python generate.py --auto-select --prompt "your prompt" --output output.png
"""

import argparse
import json
import requests
import time
import sys
import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error

COMFYUI_HOST = "http://192.168.1.215:8188"  # ComfyUI running on moira

# MinIO configuration
MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

def load_workflow(workflow_path):
    """Load workflow JSON."""
    with open(workflow_path, 'r') as f:
        return json.load(f)

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

def create_default_workflow(model_name, prompt, loras=None):
    """Create a default workflow for the given model and prompt.
    
    Args:
        model_name: Model checkpoint filename
        prompt: Text prompt
        loras: Optional list of LoRA dicts with filename, strength_model, strength_clip
        
    Returns:
        Workflow dictionary
    """
    # Basic SD 1.5 workflow structure
    workflow = {
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": model_name
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1
            }
        }
    }
    
    # Determine which model/clip outputs to use for text encoding
    # Start with checkpoint outputs
    model_output = ["3", 0]
    clip_output = ["3", 1]
    
    # If we have LoRAs, chain them
    if loras:
        for i, lora in enumerate(loras):
            node_id = str(10 + i)  # Start LoRA nodes at 10
            workflow[node_id] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "model": model_output,
                    "clip": clip_output,
                    "lora_name": lora["filename"],
                    "strength_model": lora.get("strength_model", 1.0),
                    "strength_clip": lora.get("strength_clip", 1.0)
                }
            }
            # Update outputs to point to this LoRA
            model_output = [node_id, 0]
            clip_output = [node_id, 1]
    
    # Add text encoding nodes
    workflow["6"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": prompt,
            "clip": clip_output
        }
    }
    
    workflow["7"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "bad quality, blurry, low resolution, watermark, text",
            "clip": clip_output
        }
    }
    
    # Add sampler
    workflow["3_sampler"] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": int(time.time()),
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": model_output,
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["4", 0]
        }
    }
    
    # Add VAE decoder
    workflow["8"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3_sampler", 0],
            "vae": ["3", 2]
        }
    }
    
    # Add image save
    workflow["9"] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": ["8", 0]
        }
    }
    
    return workflow

def main():
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON (required unless --auto-select is used)")
    parser.add_argument("--prompt", required=True, help="Text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--auto-select", action="store_true", 
                       help="Automatically select model and LoRAs based on prompt")
    args = parser.parse_args()

    # Validate arguments
    if not args.auto_select and not args.workflow:
        parser.error("--workflow is required unless --auto-select is used")
    
    # If auto-select is enabled, use intelligent selection
    if args.auto_select:
        try:
            import select_model
            print("[INFO] Auto-selecting model and LoRAs based on prompt...")
            
            # Query API for available models
            available_models, available_loras = select_model.query_available_models()
            if available_models:
                print(f"[OK] Found {len(available_models)} models and {len(available_loras)} LoRAs")
            
            # Analyze prompt
            analysis = select_model.analyze_prompt(args.prompt)
            
            # Select model and LoRAs
            model = select_model.select_model(analysis, available_models if available_models else None)
            loras = select_model.select_loras(analysis, model, available_loras if available_loras else None)
            
            # Show selection reasoning
            print(f"[OK] Selected model: {model}")
            if loras:
                print(f"[OK] Selected {len(loras)} LoRAs:")
                for lora in loras[:3]:  # Top 3
                    print(f"  - {lora['filename']} (strength: {lora['strength_model']}) - {', '.join(lora['reasons'])}")
            else:
                print("[INFO] No LoRAs selected (using base model)")
            
            # Create workflow with selected model and LoRAs
            workflow = create_default_workflow(model, args.prompt, loras[:3])
            
        except ImportError:
            print("[ERROR] Could not import select_model module")
            print("[ERROR] Make sure scripts/select_model.py exists")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Auto-selection failed: {e}")
            print("[ERROR] Falling back to default model")
            workflow = create_default_workflow("v1-5-pruned-emaonly-fp16.safetensors", args.prompt)
    else:
        # Load workflow from file
        workflow = load_workflow(args.workflow)
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