#!/usr/bin/env python3
"""Example demonstrating PNG metadata embedding feature.

This example shows how metadata is automatically embedded in generated images
and how to read it back using the CLI or Python API.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


from PIL import Image

from comfy_gen.metadata import (
    embed_metadata_in_png,
    format_civitai_parameters,
    format_metadata_for_display,
    read_metadata_from_png,
)


def create_sample_metadata():
    """Create a sample metadata dictionary."""
    return {
        "timestamp": "2026-01-05T10:30:00",
        "generation_id": "example-550e8400",
        "input": {
            "prompt": "a majestic lion in the savanna at sunset, cinematic lighting, photorealistic, 8k quality",
            "negative_prompt": "cartoon, anime, illustration, low quality, blurry, distorted",
            "preset": "high-quality",
        },
        "workflow": {"name": "flux-dev.json", "model": "flux1-dev-fp8.safetensors", "vae": "ae.safetensors"},
        "parameters": {
            "seed": 1001,
            "steps": 80,
            "cfg": 8.5,
            "sampler": "dpmpp_2m",
            "scheduler": "karras",
            "resolution": [1024, 1024],
            "loras": [
                {"name": "photorealistic-v2.safetensors", "strength": 0.8},
                {"name": "detail-enhancer.safetensors", "strength": 0.5},
            ],
        },
        "quality": {
            "composite_score": 8.7,
            "grade": "A",
            "technical": {"brisque": 6.5, "niqe": 7.2},
            "aesthetic": {"laion": 8.9},
            "prompt_adherence": {"clip": 0.92},
            "detail": {"topiq": 8.5},
        },
        "storage": {
            "minio_url": "http://192.168.1.215:9000/comfy-gen/lion_sunset.png",
            "file_size_bytes": 3456789,
            "format": "png",
            "generation_time_seconds": 52.3,
        },
    }


def main():
    print("=== PNG Metadata Embedding Example ===\n")

    # Create sample image
    image_path = "/tmp/example_with_metadata.png"
    print(f"[1] Creating sample image at {image_path}")
    img = Image.new("RGB", (1024, 1024), color="#ff8800")
    img.save(image_path, "PNG")
    print(f"[OK] Created {1024}x{1024} image\n")

    # Create metadata
    print("[2] Creating comprehensive metadata")
    metadata = create_sample_metadata()
    print("[OK] Metadata includes: prompt, model, parameters, quality scores, etc.\n")

    # Embed metadata
    print("[3] Embedding metadata in PNG file")
    success = embed_metadata_in_png(image_path, metadata)
    if success:
        print("[OK] Metadata embedded successfully\n")
    else:
        print("[ERROR] Failed to embed metadata\n")
        return

    # Show CivitAI format
    print("[4] CivitAI-compatible parameter string:")
    civitai_params = format_civitai_parameters(metadata)
    print(f"{civitai_params}\n")

    # Read metadata back
    print("[5] Reading metadata from PNG file")
    read_meta = read_metadata_from_png(image_path)

    if read_meta:
        print("[OK] Metadata read successfully\n")

        # Display formatted metadata
        print("[6] Formatted metadata display:")
        print(format_metadata_for_display(read_meta))
    else:
        print("[ERROR] Failed to read metadata\n")
        return

    # Verify data integrity
    print("\n[7] Verifying data integrity:")
    checks = [
        ("Prompt", read_meta["input"]["prompt"] == metadata["input"]["prompt"]),
        ("Seed", read_meta["parameters"]["seed"] == metadata["parameters"]["seed"]),
        ("Model", read_meta["workflow"]["model"] == metadata["workflow"]["model"]),
        ("Quality Score", read_meta["quality"]["composite_score"] == metadata["quality"]["composite_score"]),
        ("LoRAs Count", len(read_meta["parameters"]["loras"]) == len(metadata["parameters"]["loras"])),
    ]

    for check_name, passed in checks:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {check_name}")

    # Show how to use from CLI
    print("\n[8] CLI Usage:")
    print("To view this metadata from command line, run:")
    print(f"  python3 generate.py metadata show {image_path}")
    print("\nOr use external tools:")
    print(f"  exiftool -parameters {image_path}")
    print(f"  exiftool -prompt {image_path}")

    print("\n=== Example Complete ===")
    print(f"\nGenerated image with embedded metadata: {image_path}")
    print("You can now move this file anywhere and the metadata travels with it!")


if __name__ == "__main__":
    main()
