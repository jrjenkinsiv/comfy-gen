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
import signal
import glob
from pathlib import Path
from minio import Minio
from minio.error import S3Error

COMFYUI_HOST = "http://192.168.1.215:8188"  # ComfyUI running on moira

# Global variable to track current prompt ID for cleanup
current_prompt_id = None

# MinIO configuration
MINIO_ENDPOINT = "192.168.1.215:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
BUCKET_NAME = "comfy-gen"

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
    global current_prompt_id
    url = f"{COMFYUI_HOST}/prompt"
    response = requests.post(url, json={"prompt": workflow})
    if response.status_code == 200:
        result = response.json()
        prompt_id = result["prompt_id"]
        current_prompt_id = prompt_id
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

def cancel_generation(prompt_id):
    """Cancel a specific generation by prompt ID."""
    # First, try to delete from queue
    url = f"{COMFYUI_HOST}/queue"
    payload = {"delete": [prompt_id]}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[OK] Cancelled generation {prompt_id}")
            return True
    except requests.RequestException as e:
        # Queue deletion failed, continue to try interrupt
        pass
    
    # Also interrupt current generation in case it's running
    try:
        interrupt_url = f"{COMFYUI_HOST}/interrupt"
        requests.post(interrupt_url)
        print(f"[OK] Interrupted current generation")
        return True
    except requests.RequestException as e:
        print(f"[ERROR] Failed to cancel: {e}")
        return False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n[WARN] Cancellation requested...")
    if current_prompt_id:
        print(f"[INFO] Cancelling generation {current_prompt_id}...")
        cancel_generation(current_prompt_id)
        # Clean up partial output if it exists
        cleanup_partial_outputs()
    print("[OK] Cancelled successfully")
    sys.exit(0)

def cleanup_partial_outputs():
    """Clean up any partial output files."""
    # Remove temporary output files that might be partially downloaded
    # Note: Using /tmp is Linux-specific but matches project's Linux-based infrastructure
    try:
        temp_files = glob.glob("/tmp/*.png.tmp") + glob.glob("/tmp/*.mp4.tmp")
        for f in temp_files:
            try:
                Path(f).unlink()
                print(f"[INFO] Cleaned up partial file: {f}")
            except OSError as e:
                # Ignore errors during cleanup (file may not exist, permission issues, etc.)
                pass
    except Exception as e:
        # Ignore glob errors - cleanup is best-effort
        pass

def main():
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--cancel", metavar="PROMPT_ID", help="Cancel generation by prompt ID")
    args = parser.parse_args()

    # Handle cancellation mode
    if args.cancel:
        success = cancel_generation(args.cancel)
        sys.exit(0 if success else 1)
    
    # Validate required arguments for generation mode
    if not args.workflow or not args.prompt:
        parser.error("--workflow and --prompt are required for generation")

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