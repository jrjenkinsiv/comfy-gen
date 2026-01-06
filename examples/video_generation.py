#!/usr/bin/env python3
"""Video generation example using Wan 2.2.

This example demonstrates:
- Text-to-video generation
- Image-to-video animation
- Wan 2.2 model usage

Usage:
    python3 examples/video_generation.py
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


def text_to_video_example():
    """Generate a video from text prompt using Wan 2.2."""
    print("\n" + "=" * 60)
    print("Text-to-Video Generation (Wan 2.2)")
    print("=" * 60)

    workflow_path = "workflows/wan22-t2v.json"
    prompt = "a person walking through a park on a sunny day, cinematic camera movement"
    output_path = "/tmp/t2v_example.mp4"

    print("\n[1/4] Loading text-to-video workflow...")
    try:
        workflow = load_workflow(workflow_path)
        print(f"[OK] Loaded: {workflow_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load workflow: {e}")
        return 1

    print("\n[2/4] Setting prompt...")
    print(f"  Prompt: {prompt}")
    print("  Note: Wan 2.2 generates 848x480, 81 frames, ~10 seconds @ 8fps")
    workflow = modify_prompt(workflow, prompt, "")

    print("\n[3/4] Queuing video generation...")
    print("  (This may take 2-5 minutes depending on GPU)")
    prompt_id = queue_workflow(workflow)
    if not prompt_id:
        print("[ERROR] Failed to queue")
        return 1

    status = wait_for_completion(prompt_id)

    print("\n[4/4] Downloading video...")
    if download_output(status, output_path):
        print(f"[OK] Saved to: {output_path}")

        # Upload to MinIO
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        object_name = f"{timestamp}_t2v_example.mp4"

        url = upload_to_minio(output_path, object_name)
        if url:
            print(f"[OK] MinIO URL: {url}")
            print("\n[SUCCESS] Text-to-video complete!")
            print(f"View at: {url}")
            return 0
        else:
            print("[WARN] MinIO upload failed")
            return 0
    else:
        print("[ERROR] Failed to download video")
        return 1


def image_to_video_example():
    """Animate an existing image using Wan 2.2 I2V."""
    print("\n" + "=" * 60)
    print("Image-to-Video Animation (Wan 2.2)")
    print("=" * 60)
    print("\n[INFO] Image-to-video requires an input image.")
    print("[INFO] This example is a template - you need to:")
    print("  1. Provide an input image")
    print("  2. Upload it to ComfyUI")
    print("  3. Modify the workflow to reference it")
    print("\nSee img2img_workflow.py for input image handling example.")
    print("\nWorkflow: workflows/wan22-i2v.json")
    print("Prompt example: 'camera slowly pans right, smooth motion'")
    print("\n[SKIPPED] - Template only")
    return 0


def main():
    """Run video generation examples."""
    print("=" * 60)
    print("ComfyGen Video Generation Examples")
    print("=" * 60)

    # Check server
    print("\n[INFO] Checking ComfyUI server...")
    if not check_server_availability():
        print("[ERROR] Server unavailable")
        print("Start it with: ssh moira 'python C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py'")
        return EXIT_CONFIG_ERROR

    # Run text-to-video example
    result = text_to_video_example()
    if result != 0:
        return result

    # Show image-to-video template
    image_to_video_example()

    print("\n" + "=" * 60)
    print("All Examples Complete")
    print("=" * 60)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
