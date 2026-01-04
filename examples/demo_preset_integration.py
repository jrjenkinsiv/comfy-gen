#!/usr/bin/env python3
"""Manual test to demonstrate preset integration in MCP server.

This script demonstrates:
1. Loading configuration on startup
2. Using default negative prompt
3. Applying presets
4. Overriding preset values
5. Using LoRA presets
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def demo_preset_integration():
    """Demonstrate preset integration features."""
    print("=" * 70)
    print("MCP SERVER PRESET INTEGRATION DEMONSTRATION")
    print("=" * 70)
    
    # Load configuration
    print("\n[STEP 1] Loading configuration on startup...")
    from mcp_server import _config, _lora_catalog
    
    print(f"[OK] Configuration loaded")
    print(f"     - Default negative prompt: {_config.get('default_negative_prompt', '')[:60]}...")
    print(f"     - Available presets: {list(_config.get('presets', {}).keys())}")
    print(f"     - LoRA catalog: {len(_lora_catalog.get('loras', []))} LoRAs")
    print(f"     - Model suggestions: {len(_lora_catalog.get('model_suggestions', {}))} presets")
    
    # Test default negative prompt
    print("\n[STEP 2] Testing default negative prompt...")
    print("When user doesn't provide negative_prompt (or provides empty string),")
    print("the default from presets.yaml is automatically applied.")
    print(f"Default: {_config.get('default_negative_prompt', '')}")
    
    # Test preset usage
    print("\n[STEP 3] Testing preset parameters...")
    from comfygen.config import get_preset
    
    presets_to_show = ["draft", "balanced", "high-quality"]
    for preset_name in presets_to_show:
        preset = get_preset(preset_name)
        if preset:
            print(f"\n{preset_name.upper()} preset:")
            print(f"  - Steps: {preset.get('steps')}")
            print(f"  - CFG: {preset.get('cfg')}")
            print(f"  - Sampler: {preset.get('sampler')}")
            print(f"  - Scheduler: {preset.get('scheduler')}")
            print(f"  - Validate: {preset.get('validate')}")
            if 'auto_retry' in preset:
                print(f"  - Auto-retry: {preset.get('auto_retry')}")
    
    # Test preset override logic
    print("\n[STEP 4] Testing preset override logic...")
    from comfygen.config import apply_preset_to_params
    
    draft = get_preset("draft")
    
    # Case 1: No user params - all from preset
    params1 = {}
    result1 = apply_preset_to_params(params1, draft)
    print("\nCase 1: No user params")
    print(f"  Input: {params1}")
    print(f"  Output: steps={result1.get('steps')}, cfg={result1.get('cfg')}")
    
    # Case 2: User overrides steps
    params2 = {"steps": 30}
    result2 = apply_preset_to_params(params2, draft)
    print("\nCase 2: User overrides steps=30")
    print(f"  Input: {params2}")
    print(f"  Output: steps={result2.get('steps')} (user), cfg={result2.get('cfg')} (preset)")
    
    # Test LoRA presets
    print("\n[STEP 5] Testing LoRA presets...")
    from comfygen.config import get_lora_preset
    
    lora_presets = ["text_to_video", "image_to_video", "simple_image"]
    for preset_name in lora_presets:
        preset = get_lora_preset(preset_name)
        if preset:
            print(f"\n{preset_name}:")
            print(f"  - Model: {preset.get('model', 'not specified')}")
            print(f"  - Workflow: {preset.get('workflow', 'not specified')}")
            print(f"  - Default LoRAs: {preset.get('default_loras', [])}")
    
    # Show how it works with MCP
    print("\n[STEP 6] MCP Server Usage Examples...")
    print("\nTo use presets with MCP server generate_image tool:")
    print("  1. Use preset only:")
    print("     generate_image(prompt='sunset', preset='draft')")
    print("     → Uses all draft preset values (steps=10, cfg=5.0, etc.)")
    print()
    print("  2. Override preset values:")
    print("     generate_image(prompt='sunset', preset='draft', steps=25)")
    print("     → Uses draft preset but overrides steps to 25")
    print()
    print("  3. Use LoRA preset:")
    print("     generate_image(prompt='sunset', lora_preset='text_to_video')")
    print("     → Automatically selects appropriate model and LoRAs for video")
    print()
    print("  4. Default negative prompt:")
    print("     generate_image(prompt='sunset')")
    print("     → Automatically uses default negative prompt from config")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] Preset integration demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_preset_integration())
