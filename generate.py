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
import tempfile
import uuid
import re
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image

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

def adjust_prompt_for_retry(
    positive_prompt: str, 
    negative_prompt: str, 
    attempt: int
) -> tuple:
    """Adjust prompts for retry attempt to improve quality.
    
    Args:
        positive_prompt: Original positive prompt
        negative_prompt: Original negative prompt
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
    
    # Strengthen negative prompt
    adjusted_negative = negative_prompt
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
        if term not in adjusted_negative.lower():
            adjusted_negative = f"{adjusted_negative}, {term}" if adjusted_negative else term
    
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
    uploaded_image_filename: str = None
) -> tuple:
    """Run a single generation attempt.
    
    Args:
        workflow: The workflow dict with prompts already set
        output_path: Path to save the output
        uploaded_image_filename: Optional uploaded input image filename
    
    Returns:
        Tuple of (success: bool, minio_url: str or None)
    """
    global current_prompt_id
    
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        return False, None
    
    # Track prompt ID for cancellation
    current_prompt_id = prompt_id

    status = wait_for_completion(prompt_id)
    if status:
        if download_output(status, output_path):
            # Upload to MinIO
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_{Path(output_path).name}"
            minio_url = upload_to_minio(output_path, object_name)
            if minio_url:
                print(f"[OK] Image available at: {minio_url}")
                return True, minio_url
            else:
                print("[ERROR] Failed to upload to MinIO")
                return False, None
    
    return False, None

def main():
    global current_prompt_id, current_output_path
    
    parser = argparse.ArgumentParser(description="Generate images with ComfyUI")
    parser.add_argument("--workflow", help="Path to workflow JSON")
    parser.add_argument("--prompt", help="Positive text prompt")
    parser.add_argument("--negative-prompt", default="", help="Negative text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("--input-image", "-i", help="Input image path (local file or URL) for img2img/I2V")
    parser.add_argument("--resize", help="Resize input image to WxH (e.g., 512x512)")
    parser.add_argument("--crop", choices=['center', 'cover', 'contain'], help="Crop mode for resize")
    parser.add_argument("--denoise", type=float, help="Denoise strength (0.0-1.0) for img2img")
    parser.add_argument("--cancel", metavar="PROMPT_ID", help="Cancel a specific prompt by ID")
    parser.add_argument("--validate", action="store_true", help="Run validation after generation")
    parser.add_argument("--auto-retry", action="store_true", help="Automatically retry if validation fails")
    parser.add_argument("--retry-limit", type=int, default=3, help="Maximum retry attempts (default: 3)")
    parser.add_argument("--positive-threshold", type=float, default=0.25, help="Minimum CLIP score for positive prompt (default: 0.25)")
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
                    sys.exit(1)
                image_path = temp_file.name
            else:
                # Use local file
                if not os.path.exists(args.input_image):
                    print(f"[ERROR] Input image not found: {args.input_image}")
                    sys.exit(1)
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
                    sys.exit(1)
            
            image_path = preprocess_image(image_path, resize=resize, crop=args.crop)
            
            # Upload to ComfyUI
            uploaded_filename = upload_image_to_comfyui(image_path)
            if not uploaded_filename:
                print("[ERROR] Failed to upload input image to ComfyUI")
                sys.exit(1)
            
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

    # Validation and retry loop
    attempt = 0
    max_attempts = args.retry_limit if args.auto_retry else 1
    minio_url = None
    validation_result = None
    
    while attempt < max_attempts:
        attempt += 1
        
        if attempt > 1:
            print(f"\n[INFO] Retry attempt {attempt}/{max_attempts}")
            # Adjust prompts for retry
            adjusted_positive, adjusted_negative = adjust_prompt_for_retry(
                args.prompt, args.negative_prompt, attempt - 1
            )
            print(f"[INFO] Adjusted positive prompt: {adjusted_positive}")
            print(f"[INFO] Adjusted negative prompt: {adjusted_negative}")
            workflow = modify_prompt(workflow, adjusted_positive, adjusted_negative)
        
        # Run generation
        success, minio_url = run_generation(workflow, args.output, uploaded_filename if args.input_image else None)
        
        if not success:
            print(f"[ERROR] Generation failed on attempt {attempt}")
            if attempt >= max_attempts:
                sys.exit(1)
            continue
        
        # Run validation if requested
        if args.validate:
            try:
                from comfy_gen.validation import validate_image
                
                print(f"[INFO] Running validation...")
                validation_result = validate_image(
                    args.output,
                    args.prompt,
                    args.negative_prompt if args.negative_prompt else None,
                    positive_threshold=args.positive_threshold
                )
                
                print(f"[INFO] Validation result: {validation_result['reason']}")
                print(f"[INFO] Positive score: {validation_result.get('positive_score', 0.0):.3f}")
                
                if validation_result.get('negative_score'):
                    print(f"[INFO] Negative score: {validation_result['negative_score']:.3f}")
                    print(f"[INFO] Delta: {validation_result.get('score_delta', 0.0):.3f}")
                
                if validation_result['passed']:
                    print(f"[OK] Image passed validation")
                    break
                else:
                    print(f"[WARN] Image failed validation: {validation_result['reason']}")
                    if not args.auto_retry:
                        # Validation failed but no retry requested
                        break
                    elif attempt >= max_attempts:
                        print(f"[ERROR] Max retries reached. Final validation result:")
                        print(f"  Reason: {validation_result['reason']}")
                        print(f"  Positive score: {validation_result.get('positive_score', 0.0):.3f}")
                        break
                    # Continue to next retry attempt
                    
            except ImportError:
                print("[WARN] Validation module not available. Install dependencies: pip install transformers")
                break
            except Exception as e:
                print(f"[ERROR] Validation failed: {e}")
                break
        else:
            # No validation requested, we're done
            break
    
    # Final output
    if minio_url:
        print(f"\nImage available at: {minio_url}")
        if validation_result:
            print(f"Validation: {'PASSED' if validation_result['passed'] else 'FAILED'}")
            print(f"Score: {validation_result.get('positive_score', 0.0):.3f}")


if __name__ == "__main__":
    main()