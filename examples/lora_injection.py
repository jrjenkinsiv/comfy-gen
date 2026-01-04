#!/usr/bin/env python3
"""
Example: Dynamic LoRA Injection

Demonstrates how to use the --lora CLI argument to dynamically inject LoRAs
into workflows without modifying the workflow JSON files.
"""

import subprocess
import sys

def run_command(description, command):
    """Run a command and display output."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(command)}\n")
    
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print()

# Example 1: List available LoRAs
run_command(
    "Example 1: List Available LoRAs",
    ["python3", "generate.py", "--list-loras"]
)

# Example 2: Single LoRA injection
run_command(
    "Example 2: Generate with Single LoRA",
    [
        "python3", "generate.py",
        "--workflow", "workflows/flux-dev.json",
        "--prompt", "a beautiful sunset over mountains",
        "--lora", "style_lora.safetensors:0.8",
        "--dry-run"  # Dry run to avoid actual generation
    ]
)

# Example 3: Multiple LoRAs (chained)
run_command(
    "Example 3: Generate with Multiple LoRAs (Chained)",
    [
        "python3", "generate.py",
        "--workflow", "workflows/wan22-t2v.json",
        "--prompt", "a person walking through a park",
        "--lora", "BoobPhysics_WAN_v6.safetensors:0.7",
        "--lora", "BounceHighWan2_2.safetensors:0.6",
        "--dry-run"
    ]
)

# Example 4: LoRA preset
run_command(
    "Example 4: Generate with LoRA Preset",
    [
        "python3", "generate.py",
        "--workflow", "workflows/wan22-t2v.json",
        "--prompt", "dynamic motion scene",
        "--lora-preset", "text_to_video",
        "--dry-run"
    ]
)

print("\n" + "="*60)
print("NOTES:")
print("="*60)
print("""
1. LoRAs are injected dynamically - workflow JSON files remain unchanged
2. Multiple --lora arguments chain LoRAs in order
3. LoRA format: --lora "filename.safetensors:strength"
4. Strength typically ranges from 0.5 to 1.0
5. Use --list-loras to see all available LoRAs and presets
6. Presets are defined in lora_catalog.yaml
""")
