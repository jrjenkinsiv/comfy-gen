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
import os
import tempfile
import urllib.request
import datetime
from pathlib import Path
from shutil import copyfile
from minio import Minio
from minio.error import S3Error
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

def download_image_from_url(url, temp_path):
    """Download image from URL to temporary file."""
    try:
        print(f"Downloading image from {url}...")
        urllib.request.urlretrieve(url, temp_path)
        print(f"Downloaded image to {temp_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download image: {e}")
        return False

def preprocess_image(image_path, resize=None, crop=None):
    """Preprocess image with resize and crop options."""
    try:
        img = Image.open(image_path)
        print(f"Loaded image: {img.size} ({img.mode})")
        
        if resize:
            # Parse resize dimensions (e.g., "512x512")
            try:
                parts = resize.lower().split('x')
                if len(parts) != 2:
                    raise ValueError("Resize format must be 'WIDTHxHEIGHT'")
                width, height = int(parts[0]), int(parts[1])
                if width <= 0 or height <= 0:
                    raise ValueError("Width and height must be positive integers")
            except ValueError as e:
                print(f"[ERROR] Invalid resize format '{resize}': {e}")
                return False
            
            if crop == "center":
                # Center crop to target aspect ratio, then resize
                target_ratio = width / height
                img_ratio = img.width / img.height
                
                if img_ratio > target_ratio:
                    # Image is wider, crop width
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, img.height))
                else:
                    # Image is taller, crop height
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) // 2
                    img = img.crop((0, top, img.width, top + new_height))
                
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                print(f"Center cropped and resized to {width}x{height}")
            
            elif crop == "cover":
                # Scale to cover target dimensions, then crop
                scale = max(width / img.width, height / img.height)
                new_width = int(img.width * scale)
                new_height = int(img.height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                left = (new_width - width) // 2
                top = (new_height - height) // 2
                img = img.crop((left, top, left + width, top + height))
                print(f"Cover crop and resized to {width}x{height}")
            
            elif crop == "contain":
                # Scale to fit within target dimensions, maintain aspect ratio
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
                print(f"Contain resized to {img.size}")
            
            else:
                # Simple resize without preserving aspect ratio
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                print(f"Resized to {width}x{height}")
        
        # Save back to same path
        img.save(image_path)
        return True
    
    except Exception as e:
        print(f"[ERROR] Failed to preprocess image: {e}")
        return False

def upload_image_to_comfyui(image_path):
    """Upload image to ComfyUI's input directory.
    
    Returns:
        str: Uploaded filename that can be referenced in workflow, or None on failure
    """
    try:
        url = f"{COMFYUI_HOST}/upload/image"
        
        with open(image_path, 'rb') as f:
            files = {'image': (Path(image_path).name, f, 'image/png')}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            filename = result.get("name")
            print(f"[OK] Uploaded image to ComfyUI: {filename}")
            return filename
        else:
            print(f"[ERROR] Failed to upload image: {response.text}")
            return None
    
    except Exception as e:
        print(f"[ERROR] Exception uploading image: {e}")
        return None

def modify_workflow_for_input_image(workflow, uploaded_filename, denoise=None):
    """Modify workflow to use uploaded input image.
    
    Searches for LoadImage node and updates the image reference.
    If denoise is specified, updates KSampler denoise value.
    """
    for node_id, node in workflow.items():
        if isinstance(node, dict):
            # Update LoadImage node
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = uploaded_filename
                print(f"Updated LoadImage node {node_id} with image: {uploaded_filename}")
            
            # Update denoise in KSampler if specified
            if denoise is not None and node.get("class_type") == "KSampler":
                node["inputs"]["denoise"] = denoise
                print(f"Updated KSampler node {node_id} with denoise: {denoise}")
    
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
    parser.add_argument("--prompt", required=True, help="Text prompt")
    parser.add_argument("--output", default="output.png", help="Output image path")
    parser.add_argument("-i", "--input-image", help="Input image path or URL (for img2img/I2V)")
    parser.add_argument("--denoise", type=float, help="Denoise strength for img2img (0.0-1.0, default workflow value)")
    parser.add_argument("--resize", help="Resize input image to dimensions (e.g., '512x512')")
    parser.add_argument("--crop", choices=["center", "cover", "contain"], help="Crop mode when resizing")
    args = parser.parse_args()

    workflow = load_workflow(args.workflow)
    workflow = modify_prompt(workflow, args.prompt)

    # Handle input image if provided
    if args.input_image:
        temp_image_path = None
        is_from_url = False
        try:
            # Check if input is URL or local file
            if args.input_image.startswith("http://") or args.input_image.startswith("https://"):
                # Download from URL to temp file
                temp_fd, temp_image_path = tempfile.mkstemp(suffix=".png")
                os.close(temp_fd)
                
                if not download_image_from_url(args.input_image, temp_image_path):
                    print("[ERROR] Failed to download input image")
                    sys.exit(1)
                
                image_to_process = temp_image_path
                is_from_url = True
            else:
                # Use local file
                if not os.path.exists(args.input_image):
                    print(f"[ERROR] Input image not found: {args.input_image}")
                    sys.exit(1)
                image_to_process = args.input_image
            
            # Preprocess image if resize/crop specified
            if args.resize or args.crop:
                # If using original local file, create a temp copy to avoid modifying it
                if not is_from_url and temp_image_path is None:
                    temp_fd, temp_image_path = tempfile.mkstemp(suffix=".png")
                    os.close(temp_fd)
                    # Copy original to temp
                    copyfile(args.input_image, temp_image_path)
                    image_to_process = temp_image_path
                
                if not preprocess_image(image_to_process, resize=args.resize, crop=args.crop):
                    print("[ERROR] Failed to preprocess image")
                    sys.exit(1)
            
            # Upload to ComfyUI
            uploaded_filename = upload_image_to_comfyui(image_to_process)
            if not uploaded_filename:
                print("[ERROR] Failed to upload image to ComfyUI")
                sys.exit(1)
            
            # Modify workflow to use uploaded image
            workflow = modify_workflow_for_input_image(workflow, uploaded_filename, args.denoise)
        
        finally:
            # Clean up temp file if created
            if temp_image_path and os.path.exists(temp_image_path):
                os.unlink(temp_image_path)

    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        sys.exit(1)

    status = wait_for_completion(prompt_id)
    if status:
        if download_output(status, args.output):
            # Upload to MinIO
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_{Path(args.output).name}"
            minio_url = upload_to_minio(args.output, object_name)
            if minio_url:
                print(f"Image available at: {minio_url}")
            else:
                print("Failed to upload to MinIO")

if __name__ == "__main__":
    main()