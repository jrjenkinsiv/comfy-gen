#!/usr/bin/env python3
"""
Iterative HD Enhancement Pipeline
Performs multiple img2img passes with progressively refined settings
Similar to Topaz Gigapixel / Magnific AI iterative enhancement
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_enhancement_pass(
    input_path: str,
    output_path: str,
    workflow: str,
    prompt: str,
    negative_prompt: str,
    steps: int,
    cfg: float,
    denoise: float,
    seed: int,
    loras: list[str] = None,
) -> dict:
    """Run a single img2img enhancement pass"""

    cmd = [
        "python3",
        "generate.py",
        "--workflow", workflow,
        "--input", input_path,
        "--prompt", prompt,
        "--negative-prompt", negative_prompt,
        "--steps", str(steps),
        "--cfg", str(cfg),
        "--denoise", str(denoise),
        "--seed", str(seed),
        "--output", output_path,
    ]

    # Add LoRAs if specified
    if loras:
        for lora in loras:
            cmd.extend(["--lora", lora])

    print("\n[PASS] Running enhancement...")
    print(f"  Input: {input_path}")
    print(f"  Denoise: {denoise}")
    print(f"  Steps: {steps}")
    print(f"  CFG: {cfg}")
    if loras:
        print(f"  LoRAs: {', '.join(loras)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] Enhancement pass failed:")
        print(result.stderr)
        sys.exit(1)

    # Extract CLIP score from output
    score = None
    for line in result.stdout.split('\n'):
        if 'Positive score:' in line:
            try:
                score = float(line.split(':')[1].strip())
            except:
                pass

    return {
        'output': output_path,
        'score': score,
    }


def iterative_enhance(
    input_image: str,
    output_dir: str,
    workflow: str,
    prompt: str,
    negative_prompt: str,
    num_passes: int = 5,
    strategy: str = "progressive",
) -> str:
    """
    Perform iterative enhancement on an image

    Args:
        input_image: Path to input image
        output_dir: Directory for output images
        workflow: ComfyUI workflow to use
        prompt: Enhancement prompt
        negative_prompt: Negative prompt
        num_passes: Number of refinement passes
        strategy: Enhancement strategy (progressive, detail, lighting)

    Returns:
        Path to final enhanced image
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    current_input = input_image
    base_seed = 5000

    print(f"\n{'='*60}")
    print("ITERATIVE HD ENHANCEMENT PIPELINE")
    print(f"{'='*60}")
    print(f"Input: {input_image}")
    print(f"Passes: {num_passes}")
    print(f"Strategy: {strategy}")
    print(f"{'='*60}\n")

    for i in range(num_passes):
        pass_num = i + 1
        output_path = str(output_dir / f"pass_{pass_num:02d}.png")

        print(f"\n{'─'*60}")
        print(f"PASS {pass_num}/{num_passes}")
        print(f"{'─'*60}")

        # Strategy-specific parameters
        if strategy == "progressive":
            # Gradually decrease denoise, increase steps
            denoise = max(0.25, 0.45 - (i * 0.04))
            steps = min(60, 35 + (i * 5))
            cfg = 6.0 + (i * 0.1)
            loras = None

        elif strategy == "detail":
            # Focus on adding details with LoRAs
            denoise = 0.35
            steps = 40 + (i * 2)
            cfg = 6.0
            # Progressively increase detail LoRA strength
            strength = min(0.8, 0.4 + (i * 0.08))
            loras = [f"more_details.safetensors:{strength:.2f}"]

        elif strategy == "lighting":
            # Focus on lighting and realism
            denoise = 0.30 - (i * 0.02)
            steps = 45
            cfg = 6.5
            loras = ["polyhedron_skin.safetensors:0.6"]

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        result = run_enhancement_pass(
            input_path=current_input,
            output_path=output_path,
            workflow=workflow,
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            seed=base_seed + i,
            loras=loras,
        )

        print(f"[OK] Pass {pass_num} complete")
        if result['score']:
            print(f"  Quality score: {result['score']:.3f}")
        print(f"  Saved: {output_path}")

        # Use this pass's output as next pass's input
        current_input = output_path

    print(f"\n{'='*60}")
    print("ENHANCEMENT COMPLETE")
    print(f"{'='*60}")
    print(f"Final output: {current_input}")
    print(f"All passes saved in: {output_dir}")

    return current_input


def main():
    parser = argparse.ArgumentParser(
        description="Iterative HD enhancement pipeline for images"
    )
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output-dir", default="/tmp/enhanced", help="Output directory")
    parser.add_argument(
        "--workflow",
        default="workflows/pony-img2img.json",
        help="Workflow to use",
    )
    parser.add_argument(
        "--prompt",
        default="score_9, score_8_up, source_realistic, photorealistic, highly detailed, sharp focus, professional photography",
        help="Enhancement prompt",
    )
    parser.add_argument(
        "--negative-prompt",
        default="score_6, score_5, source_anime, cartoon, blurry, low quality",
        help="Negative prompt",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=5,
        help="Number of refinement passes (default: 5)",
    )
    parser.add_argument(
        "--strategy",
        choices=["progressive", "detail", "lighting"],
        default="progressive",
        help="Enhancement strategy",
    )

    args = parser.parse_args()

    final_output = iterative_enhance(
        input_image=args.input,
        output_dir=args.output_dir,
        workflow=args.workflow,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        num_passes=args.passes,
        strategy=args.strategy,
    )

    print(f"\n✓ Final enhanced image: {final_output}")


if __name__ == "__main__":
    main()
