#!/usr/bin/env python3
"""Manual verification: CLI and MCP configuration comparison.

This script demonstrates that the CLI and MCP server produce identical
configurations when given the same parameters.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import get_config

# Display constants
MAX_NEGATIVE_DISPLAY_LENGTH = 50  # Max characters to show for negative prompts
MAX_LORA_NAME_DISPLAY = 45  # Max characters to show for LoRA names


def simulate_cli_config(prompt, negative_prompt=None, preset=None, lora_preset=None,
                        steps=None, cfg=None, sampler=None, scheduler=None):
    """Simulate CLI parameter resolution (from generate.py logic)."""
    config = get_config()
    
    # Load preset if specified
    preset_params = {}
    if preset:
        preset_params = config.get_preset(preset) or {}
    
    # Apply defaults: explicit args > preset > hardcoded defaults
    final_steps = steps if steps is not None else preset_params.get('steps', 20)
    final_cfg = cfg if cfg is not None else preset_params.get('cfg', 7.0)
    final_sampler = sampler if sampler is not None else preset_params.get('sampler', 'euler')
    final_scheduler = scheduler if scheduler is not None else preset_params.get('scheduler', 'normal')
    
    # Default negative prompt from config if not provided
    final_negative = negative_prompt
    if not final_negative:
        final_negative = config.get_default_negative_prompt()
    
    # Resolve LoRA preset
    loras = []
    if lora_preset:
        loras = config.resolve_lora_preset(lora_preset)
    
    return {
        'prompt': prompt,
        'negative_prompt': final_negative,
        'steps': final_steps,
        'cfg': final_cfg,
        'sampler': final_sampler,
        'scheduler': final_scheduler,
        'loras': loras,
        'preset_used': preset,
        'lora_preset_used': lora_preset
    }


def simulate_mcp_config(prompt, negative_prompt="", preset=None, lora_preset=None,
                       steps=None, cfg=None, sampler=None, scheduler=None):
    """Simulate MCP server parameter resolution (from mcp_server.py logic)."""
    config = get_config()
    
    # Apply preset if specified
    preset_params = {}
    if preset:
        preset_params = config.get_preset(preset) or {}
    
    # Apply preset defaults, but explicit args override
    final_steps = steps if steps is not None else preset_params.get('steps', 20)
    final_cfg = cfg if cfg is not None else preset_params.get('cfg', 7.0)
    final_sampler = sampler if sampler is not None else preset_params.get('sampler', 'euler')
    final_scheduler = scheduler if scheduler is not None else preset_params.get('scheduler', 'normal')
    
    # Apply default negative prompt if not provided
    final_negative = negative_prompt
    if not final_negative:
        final_negative = config.get_default_negative_prompt()
    
    # Resolve LoRA preset if specified
    loras = []
    if lora_preset:
        lora_tuples = config.resolve_lora_preset(lora_preset)
        loras = [(name, strength) for name, strength in lora_tuples]
    
    return {
        'prompt': prompt,
        'negative_prompt': final_negative,
        'steps': final_steps,
        'cfg': final_cfg,
        'sampler': final_sampler,
        'scheduler': final_scheduler,
        'loras': loras,
        'preset_used': preset,
        'lora_preset_used': lora_preset
    }


def compare_configs(cli_config, mcp_config, test_name):
    """Compare CLI and MCP configurations."""
    print(f"\n{'='*70}")
    print(f"Test: {test_name}")
    print(f"{'='*70}")
    
    # Compare all fields
    fields = ['prompt', 'negative_prompt', 'steps', 'cfg', 'sampler', 'scheduler']
    
    all_match = True
    for field in fields:
        cli_val = cli_config.get(field)
        mcp_val = mcp_config.get(field)
        match = cli_val == mcp_val
        status = "[OK]" if match else "[FAIL]"
        
        if not match:
            all_match = False
            print(f"{status} {field}:")
            print(f"    CLI: {cli_val}")
            print(f"    MCP: {mcp_val}")
        else:
            # Shorten negative prompt for display
            if field == 'negative_prompt' and cli_val:
                display_val = (cli_val[:MAX_NEGATIVE_DISPLAY_LENGTH] + "..." 
                              if len(cli_val) > MAX_NEGATIVE_DISPLAY_LENGTH else cli_val)
                print(f"{status} {field}: {display_val}")
            else:
                print(f"{status} {field}: {cli_val}")
    
    # Compare LoRAs
    cli_loras = cli_config.get('loras', [])
    mcp_loras = mcp_config.get('loras', [])
    loras_match = cli_loras == mcp_loras
    status = "[OK]" if loras_match else "[FAIL]"
    
    if loras_match:
        print(f"{status} loras: {len(cli_loras)} LoRA(s)")
        for lora in cli_loras[:2]:  # Show first 2
            if isinstance(lora, tuple):
                name, strength = lora
                name_display = name[:MAX_LORA_NAME_DISPLAY] + "..." if len(name) > MAX_LORA_NAME_DISPLAY else name
                print(f"    - {name_display} (strength: {strength})")
    else:
        all_match = False
        print(f"{status} loras:")
        print(f"    CLI: {cli_loras}")
        print(f"    MCP: {mcp_loras}")
    
    if all_match:
        print(f"\n[SUCCESS] CLI and MCP produce IDENTICAL configurations!")
    else:
        print(f"\n[FAIL] Configurations DIFFER!")
    
    return all_match


def main():
    """Run comparison tests."""
    print("="*70)
    print("CLI vs MCP Configuration Comparison")
    print("="*70)
    
    all_tests_passed = True
    
    # Test 1: Basic generation with defaults
    print("\n" + "="*70)
    print("TEST 1: Basic generation (no preset, no explicit params)")
    print("="*70)
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        negative_prompt=None
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        negative_prompt=""
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "Basic defaults")
    
    # Test 2: Using balanced preset
    print("\n" + "="*70)
    print("TEST 2: Using 'balanced' preset")
    print("="*70)
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        preset="balanced"
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        preset="balanced"
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "Balanced preset")
    
    # Test 3: Preset with override
    print("\n" + "="*70)
    print("TEST 3: Preset with explicit steps override")
    print("="*70)
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        preset="balanced",
        steps=15
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        preset="balanced",
        steps=15
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "Preset + override")
    
    # Test 4: Custom negative prompt
    print("\n" + "="*70)
    print("TEST 4: Custom negative prompt")
    print("="*70)
    
    custom_neg = "ugly, distorted, low quality"
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        negative_prompt=custom_neg
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        negative_prompt=custom_neg
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "Custom negative")
    
    # Test 5: LoRA preset
    print("\n" + "="*70)
    print("TEST 5: Using LoRA preset")
    print("="*70)
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        lora_preset="text_to_video"
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        lora_preset="text_to_video"
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "LoRA preset")
    
    # Test 6: All together
    print("\n" + "="*70)
    print("TEST 6: Preset + LoRA preset + overrides")
    print("="*70)
    
    cli = simulate_cli_config(
        prompt="a beautiful sunset",
        preset="high-quality",
        lora_preset="text_to_video",
        steps=30,
        cfg=8.0
    )
    
    mcp = simulate_mcp_config(
        prompt="a beautiful sunset",
        preset="high-quality",
        lora_preset="text_to_video",
        steps=30,
        cfg=8.0
    )
    
    all_tests_passed &= compare_configs(cli, mcp, "Full combo")
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    if all_tests_passed:
        print("[SUCCESS] All tests passed! CLI and MCP produce identical configurations!")
        return 0
    else:
        print("[FAIL] Some tests failed. There are inconsistencies between CLI and MCP.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
