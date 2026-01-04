#!/usr/bin/env python3
"""Programmatic image and video generation using ComfyUI API.

Usage:
    python generate.py --workflow workflow.json --prompt "your prompt" --output output.png
    python generate.py --workflow workflow.json --prompt "your prompt" --output output.mp4
"""

import argparse
import json
import requests
import time
import sys
import datetime
from pathlib import Path
from typing import Optional, Dict, Any
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

def modify_prompt(workflow, new_prompt, negative_prompt=None):
    """Modify the prompt in the workflow.
    
    Args:
        workflow: Workflow dictionary
        new_prompt: Positive prompt text
        negative_prompt: Optional negative prompt text
    
    Returns:
        Modified workflow
    """
    # This depends on the workflow structure
    # Assume there's a node with "text" field for prompt
    positive_node_updated = False
    negative_node_updated = False
    
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            if "text" in node["inputs"]:
                # Check if this is a positive or negative prompt node
                node_title = node.get("_meta", {}).get("title", "")
                
                if "negative" in node_title.lower() and negative_prompt and not negative_node_updated:
                    node["inputs"]["text"] = negative_prompt
                    print(f"Updated negative prompt in node {node_id}")
                    negative_node_updated = True
                elif not positive_node_updated and "negative" not in node_title.lower():
                    node["inputs"]["text"] = new_prompt
                    print(f"Updated positive prompt in node {node_id}")
                    positive_node_updated = True
    
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
    """Download the generated image or video."""
    # Assume output is in outputs node
    outputs = status.get("outputs", {})
    for node_id, node_outputs in outputs.items():
        # Check for images first
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
        # Check for videos (VHS_VideoCombine outputs under "gifs" key)
        if "gifs" in node_outputs:
            for video in node_outputs["gifs"]:
                filename = video["filename"]
                subfolder = video.get("subfolder", "")
                url = f"{COMFYUI_HOST}/view?filename={filename}&subfolder={subfolder}&type=output"
                response = requests.get(url)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Saved video to {output_path}")
                    return True
                else:
                    print(f"Error downloading video: {response.text}")
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

def adjust_prompt_for_retry(prompt: str, negative_prompt: str, attempt: int) -> tuple[str, str]:
    """Adjust prompts for retry attempts to improve quality.
    
    Args:
        prompt: Original positive prompt
        negative_prompt: Original negative prompt
        attempt: Current retry attempt (1-indexed)
    
    Returns:
        Tuple of (adjusted_positive_prompt, adjusted_negative_prompt)
    """
    # Strategy: progressively strengthen emphasis and negative terms
    strength_multiplier = 1.0 + (attempt * 0.3)  # 1.3, 1.6, 1.9, etc.
    
    # Add emphasis to key terms in positive prompt
    adjusted_positive = prompt
    if "single" not in adjusted_positive.lower():
        adjusted_positive = f"single subject, {adjusted_positive}"
    if "one" not in adjusted_positive.lower():
        adjusted_positive = f"one, {adjusted_positive}"
    
    # Strengthen existing emphasis (if using weight syntax)
    adjusted_positive = f"({adjusted_positive}:{strength_multiplier:.1f})"
    
    # Add stronger negative terms
    additional_negatives = [
        "duplicate", "cloned", "multiple", "ghosting", 
        "mirrored", "double", "twin", "two", "several"
    ]
    
    # Append negatives that aren't already present
    negative_parts = [negative_prompt] if negative_prompt else []
    for neg_term in additional_negatives:
        if neg_term not in negative_prompt.lower():
            negative_parts.append(neg_term)
    
    adjusted_negative = ", ".join(filter(None, negative_parts))
    
    print(f"[INFO] Retry {attempt}: Adjusted prompts")
    print(f"  Positive: {adjusted_positive}")
    print(f"  Negative: {adjusted_negative}")
    
    return adjusted_positive, adjusted_negative

def generate_image(
    workflow_path: str,
    prompt: str,
    negative_prompt: str,
    output_path: str
) -> Optional[str]:
    """Generate a single image.
    
    Args:
        workflow_path: Path to workflow JSON
        prompt: Positive prompt
        negative_prompt: Negative prompt
        output_path: Local output file path
    
    Returns:
        MinIO URL of generated image, or None on failure
    """
    workflow = load_workflow(workflow_path)
    workflow = modify_prompt(workflow, prompt, negative_prompt)
    
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        return None
    
    status = wait_for_completion(prompt_id)
    if not status:
        return None
    
    if not download_output(status, output_path):
        return None
    
    # Upload to MinIO
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    object_name = f"{timestamp}_{Path(output_path).name}"
    minio_url = upload_to_minio(output_path, object_name)
    
    return minio_url

def main():
    parser = argparse.ArgumentParser(description="Generate images and videos with ComfyUI")
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON")
    parser.add_argument("--prompt", required=True, help="Text prompt")
    parser.add_argument("--negative-prompt", default="", help="Negative prompt")
    parser.add_argument("--output", default="output.png", help="Output file path (e.g., output.png or output.mp4)")
    parser.add_argument("--validate", action="store_true", help="Validate generated image using CLIP")
    parser.add_argument("--auto-retry", action="store_true", help="Automatically retry on validation failure")
    parser.add_argument("--retry-limit", type=int, default=3, help="Maximum retry attempts (default: 3)")
    parser.add_argument("--validation-threshold", type=float, default=0.25, 
                       help="CLIP similarity threshold for validation (default: 0.25)")
    args = parser.parse_args()

    # Import validation module if needed
    validator = None
    if args.validate:
        try:
            from comfy_gen.validation import ImageValidator
            validator = ImageValidator()
        except ImportError as e:
            print(f"[ERROR] Cannot import validation module: {e}")
            print("[ERROR] Install dependencies: pip install transformers Pillow")
            sys.exit(1)
    
    max_attempts = args.retry_limit if args.auto_retry else 1
    current_prompt = args.prompt
    current_negative = args.negative_prompt
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(f"\n[INFO] Retry attempt {attempt}/{max_attempts}")
            current_prompt, current_negative = adjust_prompt_for_retry(
                args.prompt, args.negative_prompt, attempt
            )
        else:
            print(f"[INFO] Generation attempt 1/{max_attempts}")
        
        # Generate image
        minio_url = generate_image(
            args.workflow,
            current_prompt,
            current_negative,
            args.output
        )
        
        if not minio_url:
            print("[ERROR] Generation failed")
            if attempt < max_attempts and args.auto_retry:
                print("[INFO] Retrying with adjusted prompts...")
                continue
            else:
                sys.exit(1)
        
        print(f"Output available at: {minio_url}")
        
        # Validate if requested
        if args.validate and validator:
            print(f"[INFO] Validating image...")
            validation_result = validator.validate_image(
                minio_url,
                args.prompt,  # Use original prompt for validation
                args.negative_prompt if args.negative_prompt else None,
                args.validation_threshold
            )
            
            print(f"[INFO] Validation result: {validation_result['diagnostics']}")
            print(f"  Positive score: {validation_result['positive_score']}")
            if validation_result['negative_score'] is not None:
                print(f"  Negative score: {validation_result['negative_score']}")
            
            if validation_result['valid']:
                print("[OK] Validation passed!")
                break
            else:
                print("[WARN] Validation failed")
                if args.auto_retry and attempt < max_attempts:
                    print("[INFO] Retrying with adjusted prompts...")
                    continue
                else:
                    print("[ERROR] Final validation failed after all attempts")
                    sys.exit(1)
        else:
            # No validation, success
            break
    
    print("[OK] Generation complete!")

if __name__ == "__main__":
    main()