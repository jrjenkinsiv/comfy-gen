#!/usr/bin/env python3
"""Basic text-to-image generation example.

This example demonstrates:
- Simple image generation from text prompt
- Error handling
- MinIO upload

Usage:
    python3 examples/basic_generation.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import (
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    check_server_availability,
    download_output,
    load_workflow,
    modify_prompt,
    queue_workflow,
    upload_to_minio,
    wait_for_completion,
)


def main():
    """Generate a simple image from text prompt."""
    print("=" * 60)
    print("Basic Text-to-Image Generation Example")
    print("=" * 60)

    # Configuration
    workflow_path = "workflows/flux-dev.json"
    prompt = "a beautiful mountain landscape at sunset, cinematic lighting, highly detailed"
    negative_prompt = "blurry, low quality, watermark, text"
    output_path = "/tmp/basic_example.png"

    # Step 1: Check server availability
    print("\n[1/6] Checking ComfyUI server...")
    if not check_server_availability():
        print("[ERROR] ComfyUI server is not available")
        print("Start it with: ssh moira 'python C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py'")
        return EXIT_CONFIG_ERROR

    # Step 2: Load workflow
    print("\n[2/6] Loading workflow...")
    try:
        workflow = load_workflow(workflow_path)
        print(f"[OK] Loaded workflow: {workflow_path}")
    except FileNotFoundError:
        print(f"[ERROR] Workflow not found: {workflow_path}")
        return EXIT_CONFIG_ERROR
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return EXIT_CONFIG_ERROR

    # Step 3: Modify prompts
    print("\n[3/6] Setting prompts...")
    print(f"  Positive: {prompt}")
    print(f"  Negative: {negative_prompt}")
    workflow = modify_prompt(workflow, prompt, negative_prompt)

    # Step 4: Queue workflow
    print("\n[4/6] Queuing workflow to ComfyUI...")
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        print("[ERROR] Failed to queue workflow")
        return 1

    # Step 5: Wait for completion
    print("\n[5/6] Waiting for generation to complete...")
    print("(This may take 10-30 seconds depending on the model)")
    status = wait_for_completion(prompt_id)

    # Step 6: Download and upload
    print("\n[6/6] Downloading and uploading result...")
    if download_output(status, output_path):
        print(f"[OK] Saved locally to: {output_path}")

        # Upload to MinIO
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{timestamp}_basic_example.png"

        url = upload_to_minio(output_path, object_name)
        if url:
            print(f"[OK] Uploaded to MinIO: {url}")
            print("\n" + "=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"View your image at: {url}")
            return EXIT_SUCCESS
        else:
            print("[WARN] Failed to upload to MinIO, but local file saved")
            return EXIT_SUCCESS
    else:
        print("[ERROR] Failed to download output")
        return 1


if __name__ == "__main__":
    sys.exit(main())
