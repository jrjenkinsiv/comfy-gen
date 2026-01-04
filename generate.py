#!/usr/bin/env python3
"""Programmatic image generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --negative-prompt "negative prompt" --output output.png
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

def load_workflow(workflow_path):
    """Load workflow JSON."""
    with open(workflow_path, 'r') as f:
        return json.load(f)

def modify_prompt(workflow, positive_prompt, negative_prompt=""):
    """Modify the prompt in the workflow."""
    # Update positive prompt (node 2)
    if "2" in workflow and "inputs" in workflow["2"] and "text" in workflow["2"]["inputs"]:
        workflow["2"]["inputs"]["text"] = positive_prompt
        print(f"Updated positive prompt in node 2")
    
    # Update negative prompt (node 3)
    if "3" in workflow and "inputs" in workflow["3"] and "text" in workflow["3"]["inputs"]:
        workflow["3"]["inputs"]["text"] = negative_prompt
        print(f"Updated negative prompt in node 3")
    
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

def auto_select_workflow(prompt, prefer_quality=False):
    """Automatically select workflow based on prompt analysis.
    
    Uses scripts/select_model.py to analyze prompt and suggest appropriate workflow.
    
    Args:
        prompt: Text prompt to analyze
        prefer_quality: Whether to prefer quality over speed
        
    Returns:
        Path to selected workflow file, or None if selection fails
    """
    import subprocess
    
    script_path = Path(__file__).parent / "scripts" / "select_model.py"
    
    if not script_path.exists():
        print(f"[ERROR] select_model.py not found at {script_path}")
        return None
    
    # Run select_model.py to get selection
    cmd = [sys.executable, str(script_path), prompt, "--output-format", "json"]
    if prefer_quality:
        cmd.append("--prefer-quality")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"[ERROR] Model selection failed: {result.stderr}")
            return None
        
        # Parse JSON output (skip stderr which contains INFO/WARN messages)
        selection = json.loads(result.stdout)
        
        # Determine workflow based on model
        base_model = selection["base_model"]["filename"]
        
        print(f"[INFO] Auto-selected model: {base_model}")
        if selection["loras"]:
            print(f"[INFO] Auto-selected {len(selection['loras'])} LoRA(s):")
            for lora in selection["loras"]:
                print(f"  - {lora['filename']} (strength: {lora['strength_model']})")
        
        # Map model to workflow
        workflows_dir = Path(__file__).parent / "workflows"
        
        if "wan2.2_t2v" in base_model:
            workflow_path = workflows_dir / "wan22-t2v.json"
        elif "wan2.2_i2v" in base_model:
            workflow_path = workflows_dir / "wan22-i2v.json"
        else:
            # Default to SD 1.5
            workflow_path = workflows_dir / "flux-dev.json"
        
        if not workflow_path.exists():
            print(f"[ERROR] Workflow not found: {workflow_path}")
            return None
        
        print(f"[INFO] Selected workflow: {workflow_path.name}")
        return str(workflow_path)
        
    except subprocess.TimeoutExpired:
        print("[ERROR] Model selection timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse selection output: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error during model selection: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", required=True, help="Positive text prompt")
    parser.add_argument("--negative-prompt", default="", help="Negative text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--auto-select", action="store_true", help="Automatically select workflow based on prompt")
    parser.add_argument("--prefer-quality", action="store_true", help="Prefer quality over speed (with --auto-select)")
    args = parser.parse_args()

    # Determine workflow
    if args.auto_select:
        workflow_path = auto_select_workflow(args.prompt, args.prefer_quality)
        if not workflow_path:
            print("[ERROR] Auto-selection failed. Please specify --workflow manually.")
            sys.exit(1)
    else:
        if not args.workflow:
            print("[ERROR] Either --workflow or --auto-select must be specified")
            sys.exit(1)
        workflow_path = args.workflow

    workflow = load_workflow(workflow_path)
    workflow = modify_prompt(workflow, args.prompt, args.negative_prompt)

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