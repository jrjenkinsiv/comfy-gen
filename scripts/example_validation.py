#!/usr/bin/env python3
"""Example: Generate with validation and auto-retry.

This script demonstrates the validation and auto-retry features of generate.py.

Note: This is a demonstration script. In a real scenario, you would run this
against the actual ComfyUI server on moira (192.168.1.215:8188).

The script shows:
1. Basic validation usage
2. Auto-retry with prompt adjustments
3. Validation threshold tuning
"""

import os
import sys

print("="*70)
print("ComfyGen Validation & Auto-Retry Examples")
print("="*70)

print("\n[EXAMPLE 1] Basic validation (no retry)")
print("-"*70)
cmd1 = """python3 generate.py --workflow workflows/flux-dev.json \\
    --prompt "a red Porsche 911 sports car" \\
    --output /tmp/porsche.png \\
    --validate"""
print(cmd1)
print("\nThis will generate the image and validate it using CLIP scoring.")
print("If validation fails, it will report the issue but NOT retry.")

print("\n[EXAMPLE 2] Auto-retry with default settings")
print("-"*70)
cmd2 = """python3 generate.py --workflow workflows/flux-dev.json \\
    --prompt "(Porsche 911:2.0) single car, one car only" \\
    --negative-prompt "multiple cars, duplicate, cloned" \\
    --output /tmp/porsche_retry.png \\
    --validate --auto-retry"""
print(cmd2)
print("\nThis will:")
print("  1. Generate the image")
print("  2. Validate with CLIP")
print("  3. If validation fails, adjust prompts and retry (up to 3 times)")

print("\n[EXAMPLE 3] Strict validation with custom threshold")
print("-"*70)
cmd3 = """python3 generate.py --workflow workflows/flux-dev.json \\
    --prompt "(Porsche 911:2.0) (single car:1.5), photorealistic" \\
    --negative-prompt "multiple cars, duplicate, ghosting, mirrored" \\
    --output /tmp/porsche_strict.png \\
    --validate --auto-retry --retry-limit 5 \\
    --positive-threshold 0.30"""
print(cmd3)
print("\nThis uses:")
print("  - Higher retry limit (5 instead of 3)")
print("  - Stricter threshold (0.30 instead of 0.25)")
print("  - Stronger prompt weighting")

print("\n[EXAMPLE 4] Video generation with validation")
print("-"*70)
cmd4 = """python3 generate.py --workflow workflows/wan22-t2v.json \\
    --prompt "a single Porsche 911 driving down a winding mountain road" \\
    --output /tmp/porsche_drive.mp4 \\
    --validate --auto-retry"""
print(cmd4)
print("\nValidation also works for video generation workflows.")

print("\n" + "="*70)
print("To run any example, copy the command and execute it in your shell.")
print("Make sure ComfyUI is running on moira: http://192.168.1.215:8188")
print("="*70)

print("\n[INFO] Testing validation module availability...")
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from comfy_gen.validation import CLIP_AVAILABLE
    if CLIP_AVAILABLE:
        print("[OK] CLIP is available - validation will work")
    else:
        print("[WARN] CLIP not available - install with: pip install transformers")
except ImportError as e:
    print(f"[WARN] Could not import validation module: {e}")
    print("[INFO] This is expected if dependencies are not installed yet")

print("\n[INFO] Run tests with: python3 tests/test_validation.py")
