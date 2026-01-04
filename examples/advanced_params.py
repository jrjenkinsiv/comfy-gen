#!/usr/bin/env python3
"""
Example script demonstrating advanced generation parameters.

This script shows how to use the new parameters for different use cases.
"""

import subprocess
import sys

def run_command(description, args):
    """Run a generate.py command with description."""
    print(f"\n{'='*60}")
    print(f"Example: {description}")
    print(f"{'='*60}")
    cmd = ["python3", "generate.py"] + args
    print(f"Command: {' '.join(cmd)}\n")
    
    # For demonstration, we'll just show the command
    # In a real environment with ComfyUI running, you would execute it
    print("[INFO] This would execute:")
    print(f"  {' '.join(cmd)}")
    print("\n[INFO] Expected behavior:")
    return cmd


def main():
    """Demonstrate various parameter combinations."""
    
    print("Advanced Generation Parameters - Examples")
    print("=" * 60)
    print("These examples show different use cases for the new parameters.")
    print("Note: ComfyUI server must be running for actual execution.\n")
    
    examples = []
    
    # Example 1: Using a preset
    examples.append({
        "description": "Quick draft with preset",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "a futuristic city at sunset",
            "--preset", "draft",
            "--output", "/tmp/draft.png"
        ],
        "expected": "Fast generation with 10 steps, CFG 5.0, euler sampler"
    })
    
    # Example 2: High quality with custom parameters
    examples.append({
        "description": "High quality with custom settings",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "detailed portrait of a warrior, highly detailed",
            "--steps", "50",
            "--cfg", "7.5",
            "--sampler", "dpmpp_2m_sde",
            "--scheduler", "karras",
            "--output", "/tmp/high_quality.png"
        ],
        "expected": "Slow, high-quality generation with 50 steps and karras scheduler"
    })
    
    # Example 3: Reproducible generation with seed
    examples.append({
        "description": "Reproducible generation with fixed seed",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "a red sports car on a mountain road",
            "--seed", "12345",
            "--steps", "30",
            "--output", "/tmp/reproducible.png"
        ],
        "expected": "Same output every time with seed 12345"
    })
    
    # Example 4: Custom dimensions
    examples.append({
        "description": "Wide panoramic image",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "panoramic view of a mountain range",
            "--width", "768",
            "--height", "512",
            "--steps", "25",
            "--output", "/tmp/panorama.png"
        ],
        "expected": "768x512 image (3:2 aspect ratio)"
    })
    
    # Example 5: Preset with overrides
    examples.append({
        "description": "Preset with parameter overrides",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "cyberpunk street scene",
            "--preset", "high-quality",
            "--seed", "42",
            "--width", "768",
            "--output", "/tmp/override.png"
        ],
        "expected": "High-quality preset but with custom seed and width"
    })
    
    # Example 6: Fast sampler for iteration
    examples.append({
        "description": "Fast iteration for prompt testing",
        "args": [
            "--workflow", "workflows/flux-dev.json",
            "--prompt", "test prompt variations",
            "--steps", "15",
            "--cfg", "7.0",
            "--sampler", "dpmpp_2m",
            "--output", "/tmp/test.png"
        ],
        "expected": "Quick results for testing different prompts"
    })
    
    # Print all examples
    for i, example in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Example {i}: {example['description']}")
        print(f"{'='*60}")
        print(f"Command:")
        print(f"  python3 generate.py \\")
        for j, arg in enumerate(example['args']):
            if j < len(example['args']) - 1:
                if not arg.startswith('--'):
                    print(f"    {arg} \\")
                else:
                    print(f"    {arg}", end='')
                    # Add space after flag if next arg is a value
                    if j + 1 < len(example['args']) and not example['args'][j + 1].startswith('--'):
                        print(" ", end='')
                    print("\\")
            else:
                print(f"    {arg}")
        print(f"\nExpected: {example['expected']}")
    
    print("\n" + "="*60)
    print("Parameter Quick Reference")
    print("="*60)
    print("""
Steps (--steps):
  10-15:  Fast draft quality
  20-30:  Balanced quality/speed
  40-60:  High quality
  80-150: Maximum quality (diminishing returns)

CFG (--cfg):
  1.0-4.0:  Loose prompt adherence, creative
  5.0-7.0:  Balanced (recommended)
  8.0-12.0: Strict prompt following
  13.0+:    Risk of over-saturation

Samplers (--sampler):
  euler:          Fast, simple
  euler_ancestral: Adds randomness
  dpmpp_2m:       Fast, high quality
  dpmpp_2m_sde:   Slower, better quality

Schedulers (--scheduler):
  normal:  Standard linear noise
  karras:  Better detail (recommended)
  exponential: Alternative distribution

Presets (--preset):
  draft:        10 steps, fast
  balanced:     20 steps, good balance
  high-quality: 50 steps, best quality
  fast:         15 steps, quick quality
  ultra:        100 steps, maximum quality
""")
    
    print("="*60)
    print("For more information, see docs/AGENT_GUIDE.md")
    print("="*60)


if __name__ == "__main__":
    main()
