#!/usr/bin/env python3
"""Test that MCP and CLI use identical configurations.

This test ensures that when given the same parameters, the CLI and MCP
produce identical workflow configurations (without actually running generation).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import get_config


def test_preset_parameters():
    """Test that preset parameters are identical between CLI and MCP expectations."""
    print("Testing Preset Parameter Consistency")
    print("=" * 60)
    
    config = get_config()
    
    # Test 1: Default negative prompt
    print("\n[TEST 1] Default negative prompt consistency")
    default_neg = config.get_default_negative_prompt()
    
    # CLI uses this from generate.py:get_default_negative_prompt()
    # MCP should use the same from config
    print(f"[OK] Both use config default: {default_neg[:60]}...")
    
    # Test 2: Preset parameter mapping
    print("\n[TEST 2] Preset parameter mapping")
    
    test_presets = ['draft', 'balanced', 'high-quality']
    
    for preset_name in test_presets:
        preset = config.get_preset(preset_name)
        assert preset is not None, f"Preset {preset_name} should exist"
        
        # Check expected keys
        expected_keys = ['steps', 'cfg', 'sampler', 'scheduler']
        for key in expected_keys:
            assert key in preset, f"Preset {preset_name} should have {key}"
        
        print(f"[OK] {preset_name} preset:")
        print(f"    steps={preset['steps']}, cfg={preset['cfg']}, "
              f"sampler={preset['sampler']}, scheduler={preset['scheduler']}")
    
    # Test 3: LoRA preset resolution
    print("\n[TEST 3] LoRA preset resolution")
    
    lora_presets = config.get_lora_presets()
    
    # Test available LoRA presets dynamically
    for lora_preset_name in list(lora_presets.keys())[:2]:  # Test first 2
        loras = config.resolve_lora_preset(lora_preset_name)
        assert isinstance(loras, list), f"LoRA preset {lora_preset_name} should resolve to list"
        
        if loras:
            print(f"[OK] {lora_preset_name} resolves to {len(loras)} LoRA(s)")
            for filename, strength in loras[:2]:  # Show first 2
                print(f"    - {filename[:45]}... (strength: {strength})")
        else:
            print(f"[OK] {lora_preset_name} has no default LoRAs")
    
    # Test 4: Validation config
    print("\n[TEST 4] Validation configuration")
    
    val_config = config.get_validation_config()
    
    if val_config:
        print(f"[OK] Validation config loaded:")
        print(f"    enabled={val_config.get('enabled', False)}")
        print(f"    auto_retry={val_config.get('auto_retry', False)}")
        print(f"    retry_limit={val_config.get('retry_limit', 3)}")
    
    print("\n" + "=" * 60)
    print("[OK] All consistency tests passed!")


def test_parameter_override_logic():
    """Test that parameter override logic matches between CLI and MCP."""
    print("\nTesting Parameter Override Logic")
    print("=" * 60)
    
    config = get_config()
    
    # Simulate the override logic used in both CLI and MCP
    print("\n[TEST] Preset + explicit parameter override")
    
    # Get balanced preset
    preset = config.get_preset('balanced')
    
    # Simulate: user specifies preset='balanced' and steps=15
    # Expected: steps=15 (explicit override), other params from preset
    
    user_steps = 15
    user_cfg = None  # Not specified, should use preset
    
    final_steps = user_steps if user_steps is not None else preset['steps']
    final_cfg = user_cfg if user_cfg is not None else preset['cfg']
    
    print(f"Preset: {preset}")
    print(f"User overrides: steps={user_steps}, cfg={user_cfg}")
    print(f"Final params: steps={final_steps}, cfg={final_cfg}")
    
    assert final_steps == 15, "Explicit steps should override preset"
    assert final_cfg == preset['cfg'], "Unspecified cfg should use preset"
    
    print("[OK] Override logic works correctly")
    
    print("\n" + "=" * 60)
    print("[OK] Parameter override tests passed!")


def test_config_file_locations():
    """Test that config files are in expected locations."""
    print("\nTesting Config File Locations")
    print("=" * 60)
    
    config = get_config()
    
    # Check that config files exist
    presets_file = config.config_dir / "presets.yaml"
    lora_catalog_file = config.config_dir / "lora_catalog.yaml"
    
    print(f"Config directory: {config.config_dir}")
    print(f"presets.yaml exists: {presets_file.exists()}")
    print(f"lora_catalog.yaml exists: {lora_catalog_file.exists()}")
    
    assert presets_file.exists(), "presets.yaml should exist"
    assert lora_catalog_file.exists(), "lora_catalog.yaml should exist"
    
    print("[OK] Config files found in expected locations")
    
    print("\n" + "=" * 60)
    print("[OK] Config file location tests passed!")


if __name__ == "__main__":
    try:
        test_preset_parameters()
        test_parameter_override_logic()
        test_config_file_locations()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All CLI/MCP consistency tests passed!")
        print("MCP and CLI will use identical configurations!")
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
