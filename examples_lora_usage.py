#!/usr/bin/env python3
"""Example usage scenarios for LoRA injection feature.

This demonstrates various ways to use the LoRA injection feature.
Run with --dry-run to see the modified workflow without actually queuing it.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate import (
    load_workflow,
    inject_loras,
    parse_lora_arg,
    load_lora_presets
)

def example_single_lora():
    """Example: Single LoRA injection."""
    print("\n" + "="*60)
    print("Example 1: Single LoRA")
    print("="*60)
    
    cmd = """python3 generate.py \\
    --workflow workflows/flux-dev.json \\
    --prompt "a beautiful sunset over mountains" \\
    --lora "style_lora.safetensors:0.8" \\
    --output /tmp/sunset.png"""
    
    print(f"\nCommand:\n{cmd}\n")
    
    # Simulate
    workflow = load_workflow('workflows/flux-dev.json')
    loras = [parse_lora_arg("style_lora.safetensors:0.8")]
    modified = inject_loras(workflow, loras)
    
    print(f"Result: Added {len(modified) - len(workflow)} node(s)")
    print("Workflow modified successfully!")

def example_multiple_loras():
    """Example: Multiple chained LoRAs."""
    print("\n" + "="*60)
    print("Example 2: Multiple Chained LoRAs")
    print("="*60)
    
    cmd = """python3 generate.py \\
    --workflow workflows/flux-dev.json \\
    --prompt "a futuristic city at night" \\
    --lora "style_lora.safetensors:0.7" \\
    --lora "detail_enhancer.safetensors:0.5" \\
    --lora "lighting_lora.safetensors:0.6" \\
    --output /tmp/city.png"""
    
    print(f"\nCommand:\n{cmd}\n")
    
    # Simulate
    workflow = load_workflow('workflows/flux-dev.json')
    loras = [
        parse_lora_arg("style_lora.safetensors:0.7"),
        parse_lora_arg("detail_enhancer.safetensors:0.5"),
        parse_lora_arg("lighting_lora.safetensors:0.6")
    ]
    modified = inject_loras(workflow, loras)
    
    print(f"Result: Added {len(modified) - len(workflow)} node(s)")
    print("LoRAs chained in order: style -> detail -> lighting")
    print("Workflow modified successfully!")

def example_lora_preset():
    """Example: Using a LoRA preset."""
    print("\n" + "="*60)
    print("Example 3: LoRA Preset")
    print("="*60)
    
    cmd = """python3 generate.py \\
    --workflow workflows/wan22-t2v.json \\
    --prompt "a person dancing energetically" \\
    --lora-preset video-quality \\
    --output /tmp/dance.mp4"""
    
    print(f"\nCommand:\n{cmd}\n")
    
    # Simulate
    presets = load_lora_presets()
    preset = presets.get("video-quality", [])
    
    print("Preset 'video-quality' includes:")
    for lora_def in preset:
        print(f"  - {lora_def['name']} (strength={lora_def['strength']})")
    
    print("\nWorkflow would be modified with these LoRAs!")

def example_preset_plus_custom():
    """Example: Combining preset with custom LoRAs."""
    print("\n" + "="*60)
    print("Example 4: Preset + Custom LoRAs")
    print("="*60)
    
    cmd = """python3 generate.py \\
    --workflow workflows/wan22-t2v.json \\
    --prompt "a person walking on the beach" \\
    --lora-preset fast-generation \\
    --lora "custom_style.safetensors:0.7" \\
    --output /tmp/beach.mp4"""
    
    print(f"\nCommand:\n{cmd}\n")
    
    # Simulate
    presets = load_lora_presets()
    preset = presets.get("fast-generation", [])
    
    print("Applied in order:")
    print("\n1. Preset 'fast-generation':")
    for lora_def in preset:
        print(f"   - {lora_def['name']} (strength={lora_def['strength']})")
    
    print("\n2. Custom LoRAs:")
    print("   - custom_style.safetensors (strength=0.7)")
    
    print("\nAll LoRAs would be chained together!")

def example_list_loras():
    """Example: Listing available LoRAs."""
    print("\n" + "="*60)
    print("Example 5: List Available LoRAs")
    print("="*60)
    
    cmd = "python3 generate.py --list-loras"
    
    print(f"\nCommand:\n{cmd}\n")
    print("This would query the ComfyUI server and display all available LoRAs.")
    print("\nExample output:")
    print("  [INFO] Fetching available LoRAs from ComfyUI server...")
    print("  [OK] Found 15 LoRAs:")
    print()
    print("    - BoobPhysics_WAN_v6.safetensors")
    print("    - BounceHighWan2_2.safetensors")
    print("    - wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors")
    print("    - wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors")
    print("    - ... (and more)")

def example_strength_variations():
    """Example: Different strength values."""
    print("\n" + "="*60)
    print("Example 6: LoRA Strength Variations")
    print("="*60)
    
    print("\nStrength Guidelines:")
    print("  0.3-0.5: Subtle effect")
    print("  0.6-0.8: Moderate effect (recommended)")
    print("  0.9-1.0: Strong effect")
    print("  1.0+:    Very strong (may cause artifacts)")
    
    examples = [
        ("Subtle style hint", "style_lora.safetensors:0.3"),
        ("Standard application", "style_lora.safetensors:0.7"),
        ("Strong effect", "style_lora.safetensors:1.0"),
        ("Maximum effect", "style_lora.safetensors:1.5"),
    ]
    
    print("\nExamples:")
    for desc, lora_arg in examples:
        name, strength = parse_lora_arg(lora_arg)
        print(f"  {desc:20s}: --lora \"{lora_arg}\"")

def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("LoRA Injection Usage Examples")
    print("="*60)
    print("\nThese examples demonstrate various ways to use the LoRA")
    print("injection feature in ComfyGen.")
    
    example_single_lora()
    example_multiple_loras()
    example_lora_preset()
    example_preset_plus_custom()
    example_list_loras()
    example_strength_variations()
    
    print("\n" + "="*60)
    print("Examples Complete")
    print("="*60)
    print("\nFor detailed documentation, see: docs/LORA_INJECTION.md")
    print()

if __name__ == "__main__":
    main()
