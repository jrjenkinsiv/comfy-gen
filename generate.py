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
import os
import tempfile
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from PIL import Image
from urllib.parse import urlparse

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

def preprocess_image(image_path, resize=None, crop=None):
    """Preprocess image with resize and crop options.
    
    Args:
        image_path: Path to the image file
        resize: Tuple of (width, height) for target dimensions
        crop: Crop mode - 'center', 'cover', or 'contain'
    
    Returns:
        Path to the processed image (or original if no processing)
    """
    if not resize and not crop:
        return image_path
    
    img = Image.open(image_path)
    
    if resize:
        target_width, target_height = resize
        
        if crop == 'center':
            # Center crop to target aspect ratio, then resize
            aspect_ratio = target_width / target_height
            img_aspect = img.width / img.height
            
            if img_aspect > aspect_ratio:
                # Image is wider, crop width
                new_width = int(img.height * aspect_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            else:
                # Image is taller, crop height
                new_height = int(img.width / aspect_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
            
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        elif crop == 'cover':
            # Scale to cover target, crop excess
            aspect_ratio = target_width / target_height
            img_aspect = img.width / img.height
            
            if img_aspect > aspect_ratio:
                # Scale by height
                scale = target_height / img.height
                new_width = int(img.width * scale)
                img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                left = (new_width - target_width) // 2
                img = img.crop((left, 0, left + target_width, target_height))
            else:
                # Scale by width
                scale = target_width / img.width
                new_height = int(img.height * scale)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                top = (new_height - target_height) // 2
                img = img.crop((0, top, target_width, top + target_height))
        
        elif crop == 'contain':
            # Scale to fit inside target, pad if needed
            img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Create new image with target size and paste thumbnail centered
            new_img = Image.new('RGB', (target_width, target_height), (0, 0, 0))
            paste_x = (target_width - img.width) // 2
            paste_y = (target_height - img.height) // 2
            new_img.paste(img, (paste_x, paste_y))
            img = new_img
        
        else:
            # No crop mode, just resize
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Save to temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
    os.close(temp_fd)
    img.save(temp_path, 'PNG')
    return temp_path

def download_image_from_url(url):
    """Download image from URL to temporary file.
    
    Args:
        url: URL of the image to download
    
    Returns:
        Path to the downloaded temporary file
    """
    print(f"Downloading image from {url}...")
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        print(f"[ERROR] Failed to download image: HTTP {response.status_code}")
        return None
    
    # Save to temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix=Path(urlparse(url).path).suffix or '.png')
    os.close(temp_fd)
    
    with open(temp_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded to {temp_path}")
    return temp_path

def upload_image_to_comfyui(image_path):
    """Upload image to ComfyUI's input directory.
    
    Args:
        image_path: Path to the image file to upload
    
    Returns:
        Uploaded filename on success, None on failure
    """
    url = f"{COMFYUI_HOST}/upload/image"
    
    with open(image_path, 'rb') as f:
        files = {'image': (Path(image_path).name, f, 'image/png')}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        uploaded_name = result.get('name')
        print(f"[OK] Uploaded image as: {uploaded_name}")
        return uploaded_name
    else:
        print(f"[ERROR] Failed to upload image: {response.text}")
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
    """Update LoadImage nodes in workflow to use uploaded image.
    
    Args:
        workflow: Workflow JSON dict
        uploaded_filename: Name of the uploaded image file
    
    Returns:
        Modified workflow
    """
    for node_id, node in workflow.items():
        if node.get("class_type") == "LoadImage":
            if "inputs" in node and "image" in node["inputs"]:
                node["inputs"]["image"] = uploaded_filename
                print(f"Updated LoadImage node {node_id} with image: {uploaded_filename}")
    
    return workflow

def modify_denoise(workflow, denoise_strength):
    """Update denoise parameter in KSampler nodes.
    
    Args:
        workflow: Workflow JSON dict
        denoise_strength: Denoise strength value (0.0 to 1.0)
    
    Returns:
        Modified workflow
    """
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            if "inputs" in node and "denoise" in node["inputs"]:
                node["inputs"]["denoise"] = denoise_strength
                print(f"Updated KSampler node {node_id} denoise: {denoise_strength}")
    
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
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON")
    parser.add_argument("--prompt", required=True, help="Positive text prompt")
    parser.add_argument("--negative-prompt", default="", help="Negative text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    
    # Input image arguments
    parser.add_argument("-i", "--input-image", help="Input image path or URL (for img2img/i2v)")
    parser.add_argument("--resize", help="Resize to WIDTHxHEIGHT (e.g., 512x512)")
    parser.add_argument("--crop", choices=["center", "cover", "contain"], 
                       help="Crop mode: center, cover, or contain")
    parser.add_argument("--denoise", type=float, 
                       help="Denoise strength for img2img (0.0-1.0, default varies by workflow)")
    
    args = parser.parse_args()

    workflow = load_workflow(args.workflow)
    workflow = modify_prompt(workflow, args.prompt, args.negative_prompt)
    
    # Handle input image if provided
    temp_files_to_cleanup = []
    if args.input_image:
        # Determine if it's a URL or local file
        parsed = urlparse(args.input_image)
        if parsed.scheme in ('http', 'https'):
            # Download from URL
            image_path = download_image_from_url(args.input_image)
            if not image_path:
                print("[ERROR] Failed to download input image")
                sys.exit(1)
            temp_files_to_cleanup.append(image_path)
        else:
            # Local file
            image_path = args.input_image
            if not os.path.exists(image_path):
                print(f"[ERROR] Input image not found: {image_path}")
                sys.exit(1)
        
        # Preprocess image if needed
        resize_dims = None
        if args.resize:
            try:
                width, height = args.resize.split('x')
                resize_dims = (int(width), int(height))
            except ValueError:
                print(f"[ERROR] Invalid resize format. Use WIDTHxHEIGHT (e.g., 512x512)")
                sys.exit(1)
        
        processed_path = preprocess_image(image_path, resize=resize_dims, crop=args.crop)
        if processed_path != image_path:
            temp_files_to_cleanup.append(processed_path)
        
        # Upload to ComfyUI
        uploaded_filename = upload_image_to_comfyui(processed_path)
        if not uploaded_filename:
            print("[ERROR] Failed to upload image to ComfyUI")
            # Cleanup temp files
            for temp_file in temp_files_to_cleanup:
                try:
                    os.unlink(temp_file)
                except:
                    pass
            sys.exit(1)
        
        # Update workflow to use uploaded image
        workflow = modify_input_image(workflow, uploaded_filename)
    
    # Handle denoise parameter
    if args.denoise is not None:
        if not (0.0 <= args.denoise <= 1.0):
            print("[ERROR] Denoise strength must be between 0.0 and 1.0")
            sys.exit(1)
        workflow = modify_denoise(workflow, args.denoise)

    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        # Cleanup temp files
        for temp_file in temp_files_to_cleanup:
            try:
                os.unlink(temp_file)
            except:
                pass
        sys.exit(1)

    status = wait_for_completion(prompt_id)
    
    # Cleanup temp files
    for temp_file in temp_files_to_cleanup:
        try:
            os.unlink(temp_file)
        except:
            pass
    
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