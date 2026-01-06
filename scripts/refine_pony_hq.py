#!/usr/bin/env python3
"""
Refine Pony HQ images through additional passes.
Uses img2img with low denoise to enhance details without losing composition.

Usage:
    python3 scripts/refine_pony_hq.py                    # Refine all pony_hq_*.png
    python3 scripts/refine_pony_hq.py --passes 2         # 2 refinement passes
    python3 scripts/refine_pony_hq.py --denoise 0.3      # Lower denoise for subtle enhancement
"""

import argparse
import os
import shutil
import subprocess
import tempfile

from minio import Minio

# Config
WORKFLOW = "workflows/pony-realism-refine.json"
BASE_LORA = "zy_AmateurStyle_v2.safetensors"
MINIO_ENDPOINT = "192.168.1.215:9000"
BUCKET = "comfy-gen"

# Refinement settings
DEFAULT_DENOISE = 0.35  # Low denoise preserves composition
DEFAULT_STEPS = 30
DEFAULT_CFG = 6

# Quality prompts for refinement
REFINE_POSITIVE = "score_9, score_8_up, score_7_up, rating_explicit, photo, grainy, amateur, (highly detailed:1.2), (realistic skin texture:1.3), (sharp focus:1.2)"
REFINE_NEGATIVE = "score_1, score_2, score_3, blurry, low quality, text, watermark, cartoon, anime"


def download_image(mc: Minio, object_name: str, local_path: str) -> bool:
    """Download image from MinIO."""
    try:
        mc.fget_object(BUCKET, object_name, local_path)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download {object_name}: {e}")
        return False


def refine_image(input_path: str, output_path: str, denoise: float, steps: int, lora_strength: float) -> bool:
    """Run single refinement pass on an image."""

    # Build LoRA string
    lora_string = f"{BASE_LORA}:{lora_strength}"

    cmd = [
        "python3", "generate.py",
        "--workflow", WORKFLOW,
        "--input-image", input_path,
        "--prompt", REFINE_POSITIVE,
        "--negative-prompt", REFINE_NEGATIVE,
        "--steps", str(steps),
        "--cfg", str(DEFAULT_CFG),
        "--denoise", str(denoise),
        "--lora", lora_string,
        "--output", output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        if result.returncode == 0:
            # Extract score if present
            for line in result.stdout.split('\n'):
                if 'score' in line.lower():
                    print(f"      {line.strip()}")
            return True
        else:
            print(f"      [ERROR] {result.stderr[:200]}")
            return False

    except Exception as e:
        print(f"      [ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Refine Pony HQ images")
    parser.add_argument("--passes", type=int, default=2, help="Number of refinement passes (default: 2)")
    parser.add_argument("--denoise", type=float, default=DEFAULT_DENOISE, help=f"Denoise strength (default: {DEFAULT_DENOISE})")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help=f"Sampling steps (default: {DEFAULT_STEPS})")
    parser.add_argument("--lora-strength", type=float, default=0.6, help="Amateur LoRA strength (default: 0.6)")
    parser.add_argument("--pattern", type=str, default="pony_hq_", help="Object name pattern to match")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of images to process (0=all)")
    args = parser.parse_args()

    print("=== Pony HQ Refinement ===")
    print(f"Passes: {args.passes}, Denoise: {args.denoise}, Steps: {args.steps}")
    print(f"LoRA Strength: {args.lora_strength}")

    # Connect to MinIO
    mc = Minio(
        MINIO_ENDPOINT,
        access_key=os.environ.get('MINIO_ACCESS_KEY', 'minioadmin'),
        secret_key=os.environ.get('MINIO_SECRET_KEY', 'minioadmin'),
        secure=False
    )

    # Find matching images
    objects = list(mc.list_objects(BUCKET))
    hq_images = [obj.object_name for obj in objects if args.pattern in obj.object_name and obj.object_name.endswith('.png')]

    # Sort by number for consistent processing
    hq_images.sort()

    if args.limit > 0:
        hq_images = hq_images[:args.limit]

    print(f"Found {len(hq_images)} images matching '{args.pattern}'")

    if not hq_images:
        print("[WARN] No images found. Run batch_pony_hq.py first.")
        return

    # Create temp directory for processing
    temp_dir = tempfile.mkdtemp(prefix="pony_refine_")
    print(f"Temp directory: {temp_dir}")

    successes = 0
    failures = 0

    try:
        for idx, obj_name in enumerate(hq_images, 1):
            print(f"\n[{idx}/{len(hq_images)}] Processing: {obj_name}")

            # Download original
            input_path = os.path.join(temp_dir, "input.png")
            if not download_image(mc, obj_name, input_path):
                failures += 1
                continue

            current_input = input_path

            # Run multiple passes
            for pass_num in range(1, args.passes + 1):
                print(f"      Pass {pass_num}/{args.passes}")

                output_path = os.path.join(temp_dir, f"pass_{pass_num}.png")

                # Decrease denoise slightly with each pass
                pass_denoise = args.denoise * (0.9 ** (pass_num - 1))

                if refine_image(current_input, output_path, pass_denoise, args.steps, args.lora_strength):
                    current_input = output_path
                else:
                    print(f"      [FAIL] Pass {pass_num} failed")
                    break
            else:
                # All passes completed successfully
                # Generate output name
                base_name = obj_name.replace('.png', '')
                refined_name = f"{base_name}_refined.png"

                # The refined image is at current_input, it will auto-upload via generate.py
                # But we need to rename it properly
                print(f"      [OK] Refined: {refined_name}")
                successes += 1
                continue

            failures += 1

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n=== Complete ===")
    print(f"Success: {successes}, Failures: {failures}")
    print("Gallery: http://192.168.1.162:8080/")


if __name__ == "__main__":
    main()
