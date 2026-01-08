#!/usr/bin/env python3
"""Validation and auto-retry example.

This example demonstrates:
- CLIP-based image validation
- Automatic retry loop with prompt adjustment
- Quality control for generation

Usage:
    python3 examples/validation_workflow.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import (
    EXIT_CONFIG_ERROR,
    EXIT_SUCCESS,
    adjust_prompt_for_retry,
    check_server_availability,
    download_output,
    load_workflow,
    modify_prompt,
    queue_workflow,
    upload_to_minio,
    wait_for_completion,
)

try:
    from utils.validation import ImageValidator

    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


def main():
    """Generate image with validation and auto-retry."""
    print("=" * 60)
    print("Validation and Auto-Retry Example")
    print("=" * 60)

    if not VALIDATION_AVAILABLE:
        print("\n[ERROR] Validation dependencies not installed")
        print("Install with: pip install transformers")
        return EXIT_CONFIG_ERROR

    # Configuration
    workflow_path = "workflows/flux-dev.json"
    initial_prompt = "(Porsche 911:2.0) single car, one car only, driving down a country road"
    initial_negative = "multiple cars, duplicate"
    max_retries = 3
    positive_threshold = 0.28  # Higher threshold for quality
    output_base = "/tmp/validation_example"

    # Check server
    print("\n[1/2] Checking ComfyUI server...")
    if not check_server_availability():
        print("[ERROR] Server unavailable")
        return EXIT_CONFIG_ERROR

    # Load workflow and validator
    print("\n[2/2] Setting up validation...")
    try:
        workflow = load_workflow(workflow_path)
        validator = ImageValidator()
        print("[OK] Validator ready")
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        return EXIT_CONFIG_ERROR

    # Retry loop
    print("\n" + "=" * 60)
    print(f"Starting generation with validation (max {max_retries} attempts)")
    print("=" * 60)

    current_prompt = initial_prompt
    current_negative = initial_negative

    for attempt in range(1, max_retries + 1):
        print(f"\n--- Attempt {attempt}/{max_retries} ---")

        # Adjust prompts for retry
        if attempt > 1:
            current_prompt, current_negative = adjust_prompt_for_retry(initial_prompt, initial_negative, attempt - 1)
            print(f"[INFO] Adjusted positive: {current_prompt}")
            print(f"[INFO] Adjusted negative: {current_negative}")
        else:
            print(f"[INFO] Positive: {current_prompt}")
            print(f"[INFO] Negative: {current_negative}")

        # Generate
        print("\n[GENERATE] Queuing workflow...")
        workflow = modify_prompt(workflow, current_prompt, current_negative)
        prompt_id = queue_workflow(workflow)

        if not prompt_id:
            print("[ERROR] Failed to queue, trying next attempt...")
            continue

        print("[GENERATE] Waiting for completion...")
        status = wait_for_completion(prompt_id)

        output_path = f"{output_base}_attempt{attempt}.png"
        if not download_output(status, output_path):
            print("[ERROR] Download failed, trying next attempt...")
            continue

        print(f"[OK] Downloaded to: {output_path}")

        # Validate
        print("\n[VALIDATE] Running CLIP validation...")
        result = validator.validate_image(
            output_path, initial_prompt, initial_negative, positive_threshold=positive_threshold
        )

        print(f"[VALIDATE] Positive score: {result['positive_score']:.3f}")
        if result.get("negative_score"):
            print(f"[VALIDATE] Negative score: {result['negative_score']:.3f}")
            print(f"[VALIDATE] Delta: {result.get('score_delta', 0.0):.3f}")
        print(f"[VALIDATE] Threshold: {positive_threshold}")

        if result["passed"]:
            print(f"\n[SUCCESS] Validation passed on attempt {attempt}!")

            # Upload final result
            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{timestamp}_validated_example.png"

            url = upload_to_minio(output_path, object_name)
            if url:
                print(f"[OK] Uploaded to MinIO: {url}")

            print("\n" + "=" * 60)
            print("VALIDATION SUCCESS")
            print("=" * 60)
            print(f"Attempts: {attempt}")
            print(f"Final score: {result['positive_score']:.3f}")
            print(f"Image: {url if url else output_path}")
            return EXIT_SUCCESS
        else:
            print(f"\n[WARN] Validation failed: {result['reason']}")
            if attempt < max_retries:
                print("[INFO] Retrying with adjusted prompts...")
            else:
                print(f"[ERROR] Max retries ({max_retries}) reached")

    # All attempts failed
    print("\n" + "=" * 60)
    print("VALIDATION FAILED")
    print("=" * 60)
    print(f"Max attempts ({max_retries}) exhausted")
    print(f"Last score: {result['positive_score']:.3f}")
    print(f"Threshold: {positive_threshold}")
    print("\nTips:")
    print("  - Lower threshold: --positive-threshold 0.25")
    print("  - Simplify prompt: Remove complex requirements")
    print("  - Check negative prompt: May be too restrictive")
    return 1


if __name__ == "__main__":
    sys.exit(main())
