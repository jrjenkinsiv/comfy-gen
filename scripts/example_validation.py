#!/usr/bin/env python3
"""Example script demonstrating image validation and auto-retry.

This script shows how to use the validation and auto-retry features
to generate high-quality images with automated quality control.
"""

import subprocess
import sys

def run_example():
    """Run example generation with validation."""
    
    print("=" * 60)
    print("ComfyGen Validation Example")
    print("=" * 60)
    print()
    print("This example demonstrates:")
    print("  1. Image generation with CLIP validation")
    print("  2. Auto-retry with progressive prompt strengthening")
    print("  3. Quality control for single-subject images")
    print()
    print("=" * 60)
    print()
    
    # Example 1: Basic validation (no retry)
    print("[Example 1] Basic validation (no auto-retry)")
    print("-" * 60)
    cmd1 = [
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev.json",
        "--prompt", "a beautiful sunset over mountains",
        "--output", "/tmp/sunset.png",
        "--validate"
    ]
    print("Command:", " ".join(cmd1))
    print()
    print("This will:")
    print("  - Generate an image")
    print("  - Validate it using CLIP")
    print("  - Report validation score")
    print("  - Exit (no retry even if validation fails)")
    print()
    
    # Example 2: Validation with auto-retry
    print("[Example 2] Validation with auto-retry")
    print("-" * 60)
    cmd2 = [
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev.json",
        "--prompt", "a single red Porsche 911 on a mountain road",
        "--negative-prompt", "multiple cars, duplicate, cloned, blurry",
        "--output", "/tmp/porsche.png",
        "--validate",
        "--auto-retry",
        "--retry-limit", "3"
    ]
    print("Command:", " ".join(cmd2))
    print()
    print("This will:")
    print("  - Generate an image")
    print("  - Validate using CLIP")
    print("  - If validation fails:")
    print("    * Strengthen prompt emphasis")
    print("    * Add negative terms (duplicate, ghosting, etc.)")
    print("    * Retry up to 3 times")
    print("  - Report final result")
    print()
    
    # Example 3: High-threshold validation
    print("[Example 3] High-quality with strict threshold")
    print("-" * 60)
    cmd3 = [
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev.json",
        "--prompt", "(single Porsche 911:2.0), one car only, isolated subject",
        "--negative-prompt", "multiple cars, duplicate, cloned, ghosting, mirrored",
        "--output", "/tmp/porsche_strict.png",
        "--validate",
        "--auto-retry",
        "--retry-limit", "5",
        "--validation-threshold", "0.30"
    ]
    print("Command:", " ".join(cmd3))
    print()
    print("This will:")
    print("  - Use strong initial emphasis (weight 2.0)")
    print("  - Require CLIP score >= 0.30 (higher than default 0.25)")
    print("  - Retry up to 5 times with progressive strengthening")
    print("  - Ensure high-quality single-subject output")
    print()
    
    print("=" * 60)
    print("To run these examples, execute this script on a machine")
    print("with access to the ComfyUI server (moira).")
    print("=" * 60)

if __name__ == "__main__":
    run_example()
