#!/usr/bin/env python3
"""Programmatic image generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --negative-prompt "negative prompt" --output output.png
"""

import argparse
import json
import requests
import time
import sys
import signal
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

def main():
    global current_prompt_id, current_output_path
    
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", help="Positive text prompt")
    parser.add_argument("--negative-prompt", default="", help="Negative text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--cancel", metavar="PROMPT_ID", help="Cancel a specific prompt by ID")
    args = parser.parse_args()
    
    # Handle cancel mode
    if args.cancel:
        if cancel_prompt(args.cancel):
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Validate required args for generation mode
    if not args.workflow or not args.prompt:
        parser.error("--workflow and --prompt are required (unless using --cancel)")
    
    # Set up Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)
    current_output_path = args.output

    workflow = load_workflow(args.workflow)
    workflow = modify_prompt(workflow, args.prompt, args.negative_prompt)

    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        sys.exit(1)
    
    # Track prompt ID for cancellation
    current_prompt_id = prompt_id

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