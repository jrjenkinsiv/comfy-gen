#!/usr/bin/env python3
"""
LoRA Strength Experimentation Script

Generates multiple images with the same prompt and seed but varying LoRA strengths
for easy comparison. Optionally creates a comparison grid.

Usage:
    python3 scripts/lora_strength_test.py \
      --workflow workflows/pony-realism.json \
      --prompt "1girl, nude, ..." \
      --lora zy_AmateurStyle_v2.safetensors \
      --strengths 0.4,0.6,0.8,1.0,1.2 \
      --seed 12345
"""

import argparse
import os
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

# Paths
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"

# Exit codes
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG_ERROR = 2

# Grid layout constants
GRID_LABEL_HEIGHT = 40
GRID_PADDING = 10


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test LoRA strength variations with consistent prompt and seed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test single LoRA at multiple strengths
  python3 scripts/lora_strength_test.py \\
    --workflow workflows/pony-realism.json \\
    --prompt "score_9, 1girl, nude, looking at camera" \\
    --lora zy_AmateurStyle_v2.safetensors \\
    --strengths 0.4,0.6,0.8,1.0,1.2 \\
    --seed 12345

  # Test multiple LoRAs with grid output
  python3 scripts/lora_strength_test.py \\
    --workflow workflows/pony-realism.json \\
    --prompt "beautiful portrait, detailed skin" \\
    --lora zy_AmateurStyle_v2.safetensors \\
    --lora realcumv6.55.safetensors \\
    --strengths 0.5,0.7,0.9 \\
    --grid \\
    --output-dir /tmp/lora_tests
        """
    )

    parser.add_argument(
        "--workflow",
        required=True,
        help="Path to workflow JSON file"
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="Positive text prompt (same for all generations)"
    )
    parser.add_argument(
        "--negative-prompt",
        "-n",
        default="",
        help="Negative text prompt (optional)"
    )
    parser.add_argument(
        "--lora",
        action="append",
        metavar="LORA_FILE",
        required=True,
        help="LoRA filename (e.g., zy_AmateurStyle_v2.safetensors). Can be repeated for multiple LoRAs."
    )
    parser.add_argument(
        "--strengths",
        required=True,
        help="Comma-separated list of strength values to test (e.g., '0.4,0.6,0.8,1.0,1.2')"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (optional, generates random if not specified)"
    )
    parser.add_argument(
        "--output-dir",
        default="/tmp/lora_strength_test",
        help="Output directory for generated images (default: /tmp/lora_strength_test)"
    )
    parser.add_argument(
        "--prefix",
        default="test",
        help="Filename prefix for output images (default: 'test')"
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Create a comparison grid image after generation"
    )
    parser.add_argument(
        "--grid-cols",
        type=int,
        default=None,
        help="Number of columns in grid (default: auto-calculate)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Number of sampling steps (optional, uses workflow default if not specified)"
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=None,
        help="CFG scale (optional, uses workflow default if not specified)"
    )
    parser.add_argument(
        "--sampler",
        default=None,
        help="Sampler algorithm (optional)"
    )
    parser.add_argument(
        "--scheduler",
        default=None,
        help="Scheduler (optional)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output from generation"
    )

    return parser.parse_args()


def parse_strengths(strengths_str):
    """Parse comma-separated strength values.

    Args:
        strengths_str: String like "0.4,0.6,0.8,1.0"

    Returns:
        List of float values

    Raises:
        ValueError: If parsing fails
    """
    try:
        strengths = [float(s.strip()) for s in strengths_str.split(',')]
        if not strengths:
            raise ValueError("No strength values provided")
        for s in strengths:
            if s < 0:
                raise ValueError(f"Strength must be non-negative: {s}")
        return strengths
    except ValueError as e:
        raise ValueError(f"Invalid strength values: {e}")


def generate_image(
    workflow,
    prompt,
    negative_prompt,
    lora_specs,
    output_path,
    seed=None,
    steps=None,
    cfg=None,
    sampler=None,
    scheduler=None,
    quiet=False
):
    """Generate a single image with specified LoRA strengths.

    Args:
        workflow: Path to workflow JSON
        prompt: Positive prompt text
        negative_prompt: Negative prompt text
        lora_specs: List of (lora_name, strength) tuples
        output_path: Path for output image
        seed: Random seed (optional)
        steps: Sampling steps (optional)
        cfg: CFG scale (optional)
        sampler: Sampler name (optional)
        scheduler: Scheduler name (optional)
        quiet: Suppress output (optional)

    Returns:
        bool: True if generation succeeded, False otherwise
    """
    cmd = [
        sys.executable,
        str(GENERATE_PY),
        "--workflow", str(workflow),
        "--prompt", prompt,
        "--output", str(output_path)
    ]

    # Add negative prompt if provided
    if negative_prompt:
        cmd.extend(["--negative-prompt", negative_prompt])

    # Add LoRAs with strengths
    for lora_name, strength in lora_specs:
        cmd.extend(["--lora", f"{lora_name}:{strength}"])

    # Add optional parameters
    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    if steps is not None:
        cmd.extend(["--steps", str(steps)])
    if cfg is not None:
        cmd.extend(["--cfg", str(cfg)])
    if sampler is not None:
        cmd.extend(["--sampler", sampler])
    if scheduler is not None:
        cmd.extend(["--scheduler", scheduler])
    if quiet:
        cmd.append("--quiet")

    # Run generation
    result = subprocess.run(
        cmd,
        cwd=str(COMFY_GEN_DIR),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] Generation failed: {result.stderr}")
        return False

    return True


def create_comparison_grid(image_paths, labels, output_path, cols=None):
    """Create a comparison grid from multiple images.

    Note: Text labels are not currently rendered in the grid. Images are arranged
    in the grid and can be identified by their position and filename.

    Args:
        image_paths: List of paths to images
        labels: List of label strings for each image (currently unused)
        output_path: Path for output grid image
        cols: Number of columns (None for auto-calculate)

    Returns:
        bool: True if grid creation succeeded, False otherwise
    """
    if not image_paths:
        print("[ERROR] No images to create grid")
        return False

    try:
        # Load all images
        images = []
        for path in image_paths:
            if not os.path.exists(path):
                print(f"[WARN] Image not found: {path}")
                continue
            images.append(Image.open(path))

        if not images:
            print("[ERROR] No valid images found for grid")
            return False

        # Calculate grid dimensions
        n_images = len(images)
        if cols is None:
            # Auto-calculate columns (prefer square-ish layout)
            sqrt_n = n_images ** 0.5
            cols = int(sqrt_n) + (1 if sqrt_n % 1 > 0 else 0)
            cols = max(1, min(cols, n_images))

        rows = (n_images + cols - 1) // cols

        # Get image dimensions (assume all same size)
        img_width, img_height = images[0].size

        # Create grid canvas
        grid_width = cols * img_width + (cols + 1) * GRID_PADDING
        grid_height = rows * (img_height + GRID_LABEL_HEIGHT) + (rows + 1) * GRID_PADDING
        grid = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))

        # Paste images into grid
        for idx, img in enumerate(images):
            row = idx // cols
            col = idx % cols

            x = col * img_width + (col + 1) * GRID_PADDING
            y = row * (img_height + GRID_LABEL_HEIGHT) + (row + 1) * GRID_PADDING

            grid.paste(img, (x, y))

        # Save grid
        grid.save(output_path)
        print(f"[OK] Comparison grid saved to: {output_path}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to create grid: {e}")
        return False


def main():
    """Main entry point."""
    args = parse_args()

    # Parse strength values
    try:
        strengths = parse_strengths(args.strengths)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(EXIT_CONFIG_ERROR)

    # Validate workflow exists
    if not os.path.exists(args.workflow):
        print(f"[ERROR] Workflow file not found: {args.workflow}")
        sys.exit(EXIT_CONFIG_ERROR)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate random seed if not provided
    if args.seed is None:
        args.seed = random.randint(0, 2**32 - 1)
        print(f"[OK] Generated random seed: {args.seed}")

    # Display test configuration
    print("\n[OK] LoRA Strength Test Configuration:")
    print(f"  Workflow: {args.workflow}")
    print(f"  Prompt: {args.prompt}")
    if args.negative_prompt:
        print(f"  Negative: {args.negative_prompt}")
    print(f"  LoRAs: {', '.join(args.lora)}")
    print(f"  Strengths: {', '.join(str(s) for s in strengths)}")
    print(f"  Seed: {args.seed}")
    print(f"  Output: {args.output_dir}")
    if args.steps:
        print(f"  Steps: {args.steps}")
    if args.cfg:
        print(f"  CFG: {args.cfg}")
    print()

    # Generate images for each strength
    generated_images = []
    labels = []

    for strength in strengths:
        # Build LoRA specs (all LoRAs use the same strength for this test)
        lora_specs = [(lora_name, strength) for lora_name in args.lora]

        # Build output filename
        strength_str = f"{strength:.1f}".replace('.', '_')
        output_filename = f"{args.prefix}_strength_{strength_str}.png"
        output_path = output_dir / output_filename

        print(f"[INFO] Generating with strength {strength}...")

        success = generate_image(
            workflow=args.workflow,
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            lora_specs=lora_specs,
            output_path=output_path,
            seed=args.seed,
            steps=args.steps,
            cfg=args.cfg,
            sampler=args.sampler,
            scheduler=args.scheduler,
            quiet=args.quiet
        )

        if success:
            print(f"[OK] Generated: {output_path}")
            generated_images.append(output_path)
            labels.append(f"Strength: {strength}")
        else:
            print(f"[ERROR] Failed to generate image with strength {strength}")

    # Summary
    print(f"\n[OK] Generated {len(generated_images)}/{len(strengths)} images")
    print(f"[OK] Output directory: {output_dir}")

    # Create comparison grid if requested
    if args.grid and generated_images:
        grid_path = output_dir / f"{args.prefix}_comparison_grid.png"
        print("\n[INFO] Creating comparison grid...")
        if create_comparison_grid(generated_images, labels, grid_path, cols=args.grid_cols):
            print(f"[OK] Grid dimensions: {len(labels)} images")
        else:
            print("[WARN] Grid creation failed, but individual images are available")

    # Exit with appropriate code
    if len(generated_images) == 0:
        sys.exit(EXIT_FAILURE)
    elif len(generated_images) < len(strengths):
        print("[WARN] Some generations failed")
        sys.exit(EXIT_SUCCESS)
    else:
        sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
