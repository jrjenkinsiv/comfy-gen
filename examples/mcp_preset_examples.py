#!/usr/bin/env python3
"""Example demonstrating MCP preset functionality.

This example shows how to use the new preset and lora_preset parameters
in the MCP generate_image tool to match CLI behavior.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.tools.generation import generate_image
from comfygen.config import get_config_loader


async def example_default_negative_prompt():
    """Example: Using default negative prompt from presets.yaml."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Default Negative Prompt")
    print("=" * 60)
    
    config_loader = get_config_loader()
    default_neg = config_loader.get_default_negative_prompt()
    
    print(f"\nDefault negative prompt from presets.yaml:")
    print(f"  {default_neg}")
    
    print("\nWhen you call generate_image with empty negative_prompt:")
    print("  generate_image(prompt='a cat', negative_prompt='')")
    print("\nMCP will automatically use the default negative prompt from presets.yaml")
    print("This matches the CLI behavior when --negative-prompt is not specified")


async def example_using_preset():
    """Example: Using generation preset."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Using Generation Presets")
    print("=" * 60)
    
    config_loader = get_config_loader()
    
    # Show available presets
    presets = config_loader.load_presets()["presets"]
    print("\nAvailable presets:")
    for name, config in presets.items():
        print(f"\n  {name}:")
        print(f"    steps: {config['steps']}")
        print(f"    cfg: {config['cfg']}")
        print(f"    sampler: {config['sampler']}")
        print(f"    scheduler: {config['scheduler']}")
        if 'validate' in config:
            print(f"    validate: {config['validate']}")
    
    print("\n" + "-" * 60)
    print("To use a preset, call generate_image with preset parameter:")
    print("  generate_image(")
    print("    prompt='a sunset over mountains',")
    print("    preset='draft'  # Fast, low quality")
    print("  )")
    print("\nThe preset will set steps, cfg, sampler, scheduler, and validate")
    print("Individual parameters can still override preset values:")
    print("  generate_image(")
    print("    prompt='a sunset over mountains',")
    print("    preset='draft',")
    print("    steps=20  # Override draft's steps=10")
    print("  )")


async def example_using_lora_preset():
    """Example: Using LoRA preset."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Using LoRA Presets")
    print("=" * 60)
    
    config_loader = get_config_loader()
    
    # Show available LoRA presets
    catalog = config_loader.load_lora_catalog()
    suggestions = catalog["model_suggestions"]
    
    print("\nAvailable LoRA presets:")
    for name, config in suggestions.items():
        print(f"\n  {name}:")
        print(f"    model: {config['model']}")
        print(f"    workflow: {config['workflow']}")
        if config.get('default_loras'):
            print(f"    default LoRAs:")
            for lora in config['default_loras']:
                print(f"      - {lora}")
    
    print("\n" + "-" * 60)
    print("To use a LoRA preset, call generate_image with lora_preset parameter:")
    print("  generate_image(")
    print("    prompt='a person walking',")
    print("    lora_preset='text_to_video'")
    print("  )")
    print("\nThe lora_preset will automatically load the default LoRAs")
    print("with their recommended strengths from lora_catalog.yaml")


async def example_parameter_precedence():
    """Example: Parameter precedence (CLI args > preset > config defaults)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Parameter Precedence")
    print("=" * 60)
    
    print("\nParameter precedence order:")
    print("  1. User-provided parameters (highest priority)")
    print("  2. Preset values")
    print("  3. Config defaults from presets.yaml (lowest priority)")
    
    print("\nExample scenario:")
    print("  presets.yaml has:")
    print("    - default validation.enabled: true")
    print("    - draft preset: steps=10, cfg=5.0, validate=false")
    print("")
    print("  Call: generate_image(prompt='...', preset='draft', steps=30)")
    print("")
    print("  Result:")
    print("    steps: 30 (user override)")
    print("    cfg: 5.0 (from preset)")
    print("    validate: false (from preset)")
    print("    retry_limit: 3 (from config default)")


async def example_cli_mcp_parity():
    """Example: CLI and MCP parity."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: CLI and MCP Parity")
    print("=" * 60)
    
    print("\nCLI command:")
    print("  python generate.py \\")
    print("    --workflow workflows/flux-dev.json \\")
    print("    --prompt 'a cat' \\")
    print("    --preset draft")
    
    print("\nEquivalent MCP call:")
    print("  generate_image(")
    print("    prompt='a cat',")
    print("    preset='draft'")
    print("  )")
    
    print("\nBoth will use:")
    print("  - Same default negative prompt from presets.yaml")
    print("  - Same preset parameters (steps, cfg, sampler, scheduler)")
    print("  - Same validation settings")
    print("  - Same LoRA catalog")
    
    print("\n" + "-" * 60)
    print("CLI command with LoRA preset:")
    print("  python generate.py \\")
    print("    --workflow workflows/flux-dev.json \\")
    print("    --prompt 'a cat' \\")
    print("    --lora-preset simple_image")
    
    print("\nEquivalent MCP call:")
    print("  generate_image(")
    print("    prompt='a cat',")
    print("    lora_preset='simple_image'")
    print("  )")


async def run_examples():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MCP PRESET FUNCTIONALITY EXAMPLES")
    print("=" * 70)
    print("\nThese examples demonstrate the new preset integration that makes")
    print("MCP and CLI behavior consistent by sharing presets.yaml configuration.")
    
    await example_default_negative_prompt()
    await example_using_preset()
    await example_using_lora_preset()
    await example_parameter_precedence()
    await example_cli_mcp_parity()
    
    print("\n" + "=" * 70)
    print("END OF EXAMPLES")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  1. MCP now loads presets.yaml on startup (same as CLI)")
    print("  2. Empty negative_prompt uses default from config")
    print("  3. 'preset' parameter sets steps/cfg/sampler/scheduler/validate")
    print("  4. 'lora_preset' parameter auto-loads LoRAs from catalog")
    print("  5. User parameters always override preset values")
    print("  6. MCP and CLI produce identical output with same parameters")
    print("")


if __name__ == "__main__":
    asyncio.run(run_examples())
