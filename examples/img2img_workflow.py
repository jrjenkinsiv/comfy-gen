#!/usr/bin/env python3
"""Image-to-image transformation example.

This example demonstrates:
- Loading an input image
- Preprocessing (resize, crop)
- Image transformation with denoise control
- Error handling

Usage:
    python3 examples/img2img_workflow.py
    
Note: You'll need an input image. Update INPUT_IMAGE_PATH below.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import (
    check_server_availability,
    load_workflow,
    modify_prompt,
    modify_input_image,
    modify_denoise,
    upload_image_to_comfyui,
    preprocess_image,
    queue_workflow,
    wait_for_completion,
    download_output,
    upload_to_minio,
    EXIT_SUCCESS,
    EXIT_CONFIG_ERROR
)
import tempfile
import shutil


# Configuration - UPDATE THIS PATH
INPUT_IMAGE_PATH = "/tmp/input.png"  # Change this to your input image
# Alternative: Download from MinIO
# INPUT_IMAGE_URL = "http://192.168.1.215:9000/comfy-gen/some_image.png"


def main():
    """Transform an image using img2img workflow."""
    print("=" * 60)
    print("Image-to-Image Transformation Example")
    print("=" * 60)
    
    # Configuration
    workflow_path = "workflows/sd15-img2img.json"
    prompt = "oil painting style, artistic, impressionist, vibrant colors"
    negative_prompt = "photograph, realistic, low quality, blurry"
    denoise = 0.7  # 0.0 = identical to input, 1.0 = completely new
    output_path = "/tmp/img2img_example.png"
    
    # Image preprocessing options
    resize = (512, 512)  # Target size
    crop = "cover"  # Scale to cover, crop excess
    
    # Step 1: Check server
    print("\n[1/7] Checking ComfyUI server...")
    if not check_server_availability():
        print("[ERROR] Server unavailable")
        return EXIT_CONFIG_ERROR
    
    # Step 2: Verify input image exists
    print("\n[2/7] Checking input image...")
    if not Path(INPUT_IMAGE_PATH).exists():
        print(f"[ERROR] Input image not found: {INPUT_IMAGE_PATH}")
        print("Please update INPUT_IMAGE_PATH in this script to point to a real image")
        return EXIT_CONFIG_ERROR
    print(f"[OK] Found input image: {INPUT_IMAGE_PATH}")
    
    # Step 3: Load workflow
    print("\n[3/7] Loading img2img workflow...")
    try:
        workflow = load_workflow(workflow_path)
        print(f"[OK] Loaded: {workflow_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return EXIT_CONFIG_ERROR
    
    # Step 4: Preprocess and upload input image
    print("\n[4/7] Preprocessing and uploading input image...")
    
    # Create temp copy for preprocessing
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file.close()
    shutil.copy(INPUT_IMAGE_PATH, temp_file.name)
    
    try:
        # Preprocess
        print(f"  Resizing to {resize[0]}x{resize[1]} with crop mode: {crop}")
        preprocess_image(temp_file.name, resize=resize, crop=crop)
        
        # Upload to ComfyUI
        uploaded_filename = upload_image_to_comfyui(temp_file.name)
        if not uploaded_filename:
            print("[ERROR] Failed to upload image to ComfyUI")
            return 1
        
        print(f"[OK] Uploaded as: {uploaded_filename}")
    finally:
        # Clean up temp file
        Path(temp_file.name).unlink(missing_ok=True)
    
    # Step 5: Configure workflow
    print("\n[5/7] Configuring workflow...")
    print(f"  Prompt: {prompt}")
    print(f"  Denoise: {denoise} (lower = more faithful to input)")
    
    workflow = modify_prompt(workflow, prompt, negative_prompt)
    workflow = modify_input_image(workflow, uploaded_filename)
    workflow = modify_denoise(workflow, denoise)
    
    # Step 6: Queue and generate
    print("\n[6/7] Generating transformed image...")
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        print("[ERROR] Failed to queue workflow")
        return 1
    
    print("Waiting for completion...")
    status = wait_for_completion(prompt_id)
    
    # Step 7: Download and upload
    print("\n[7/7] Downloading result...")
    if download_output(status, output_path):
        print(f"[OK] Saved to: {output_path}")
        
        # Upload to MinIO
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{timestamp}_img2img_example.png"
        
        url = upload_to_minio(output_path, object_name)
        if url:
            print(f"[OK] MinIO URL: {url}")
            print("\n" + "=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"Original:    {INPUT_IMAGE_PATH}")
            print(f"Transformed: {url}")
            return EXIT_SUCCESS
        else:
            print("[WARN] MinIO upload failed, but local file saved")
            return EXIT_SUCCESS
    else:
        print("[ERROR] Failed to download output")
        return 1


if __name__ == "__main__":
    sys.exit(main())
