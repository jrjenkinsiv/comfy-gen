#!/usr/bin/env python3
"""Tests for config module."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import Config, get_config

# Display constants
MAX_LORA_NAME_DISPLAY = 40  # Max characters to display for LoRA names


def test_config_loading():
    """Test that config loads successfully."""
    config = Config()
    
    # Test preset loading
    presets = config.get_presets()
    assert isinstance(presets, dict), "Presets should be a dictionary"
    assert len(presets) > 0, "Should have at least one preset"
    
    # Check for commonly expected presets (flexible - at least one should exist)
    common_presets = ['draft', 'balanced', 'high-quality']
    found_presets = [p for p in common_presets if p in presets]
    assert len(found_presets) > 0, f"Should have at least one common preset from {common_presets}"
    
    print(f"[OK] Loaded {len(presets)} presets: {list(presets.keys())}")


def test_default_negative_prompt():
    """Test that default negative prompt is loaded."""
    config = Config()
    
    negative = config.get_default_negative_prompt()
    assert isinstance(negative, str), "Default negative prompt should be a string"
    assert len(negative) > 0, "Default negative prompt should not be empty"
    assert "quality" in negative.lower(), "Default negative should mention quality"
    
    print(f"[OK] Default negative prompt: {negative[:50]}...")


def test_preset_details():
    """Test preset configuration details."""
    config = Config()
    
    presets = config.get_presets()
    
    # Test first available preset (flexible approach)
    if len(presets) > 0:
        first_preset_name = list(presets.keys())[0]
        first_preset = config.get_preset(first_preset_name)
        assert first_preset is not None, f"{first_preset_name} preset should exist"
        
        # Check for common preset keys
        common_keys = ['steps', 'cfg', 'sampler', 'scheduler']
        found_keys = [k for k in common_keys if k in first_preset]
        assert len(found_keys) >= 2, "Preset should have at least 2 common keys"
        
        print(f"[OK] {first_preset_name} preset: {first_preset}")
    
    # If balanced preset exists, test it specifically
    if 'balanced' in presets:
        balanced = config.get_preset('balanced')
        assert 'steps' in balanced, "Balanced preset should have steps"
        print(f"[OK] Balanced preset validated")
    
    # If draft exists and balanced exists, compare them
    if 'draft' in presets and 'balanced' in presets:
        draft = config.get_preset('draft')
        balanced = config.get_preset('balanced')
        if 'steps' in draft and 'steps' in balanced:
            assert draft['steps'] < balanced['steps'], "Draft should have fewer steps than balanced"
            print(f"[OK] Draft has fewer steps than balanced")


def test_lora_catalog():
    """Test LoRA catalog loading."""
    config = Config()
    
    lora_presets = config.get_lora_presets()
    assert isinstance(lora_presets, dict), "LoRA presets should be a dictionary"
    assert len(lora_presets) > 0, "Should have at least one LoRA preset"
    
    print(f"[OK] Loaded {len(lora_presets)} LoRA presets: {list(lora_presets.keys())}")


def test_lora_preset_resolution():
    """Test resolving LoRA presets to file/strength tuples."""
    config = Config()
    
    # Test text_to_video preset
    t2v = config.resolve_lora_preset('text_to_video')
    assert isinstance(t2v, list), "Resolved preset should be a list"
    assert len(t2v) > 0, "text_to_video preset should have at least one LoRA"
    
    # Check structure
    for lora_filename, strength in t2v:
        assert isinstance(lora_filename, str), "LoRA filename should be a string"
        assert isinstance(strength, (int, float)), "Strength should be numeric"
        assert strength > 0, "Strength should be positive"
        assert lora_filename.endswith('.safetensors'), "LoRA should be a safetensors file"
    
    print(f"[OK] text_to_video preset resolved to {len(t2v)} LoRAs")
    lora_display = t2v[0][0][:MAX_LORA_NAME_DISPLAY] + "..." if len(t2v[0][0]) > MAX_LORA_NAME_DISPLAY else t2v[0][0]
    print(f"    First LoRA: {lora_display} (strength: {t2v[0][1]})")


def test_validation_config():
    """Test validation configuration loading."""
    config = Config()
    
    validation = config.get_validation_config()
    assert isinstance(validation, dict), "Validation config should be a dictionary"
    
    # Check expected keys
    if 'enabled' in validation:
        assert isinstance(validation['enabled'], bool), "enabled should be boolean"
        print(f"[OK] Validation enabled: {validation['enabled']}")
    
    if 'auto_retry' in validation:
        assert isinstance(validation['auto_retry'], bool), "auto_retry should be boolean"
        print(f"[OK] Auto retry: {validation['auto_retry']}")


def test_singleton_pattern():
    """Test that get_config returns the same instance."""
    config1 = get_config()
    config2 = get_config()
    
    assert config1 is config2, "get_config should return the same instance"
    print("[OK] Singleton pattern working correctly")


def test_nonexistent_preset():
    """Test handling of nonexistent presets."""
    config = Config()
    
    preset = config.get_preset('nonexistent_preset')
    assert preset is None, "Nonexistent preset should return None"
    
    lora_preset = config.get_lora_preset('nonexistent_lora_preset')
    assert lora_preset is None, "Nonexistent LoRA preset should return None"
    
    print("[OK] Nonexistent presets handled correctly")


def test_lora_info():
    """Test LoRA info lookup."""
    config = Config()
    
    # Try to find a specific LoRA
    lora_catalog = config.lora_catalog
    if 'loras' in lora_catalog and len(lora_catalog['loras']) > 0:
        first_lora = lora_catalog['loras'][0]
        filename = first_lora.get('filename')
        
        if filename:
            info = config.get_lora_info(filename)
            assert info is not None, f"Should find LoRA info for {filename}"
            assert info.get('filename') == filename, "Returned info should match requested filename"
            assert 'recommended_strength' in info, "LoRA info should have recommended_strength"
            
            lora_display = filename[:MAX_LORA_NAME_DISPLAY] + "..." if len(filename) > MAX_LORA_NAME_DISPLAY else filename
            print(f"[OK] Found LoRA info for {lora_display}")
            print(f"    Strength: {info['recommended_strength']}")
    else:
        print("[SKIP] No LoRAs in catalog to test")


if __name__ == "__main__":
    print("Testing Config Module")
    print("=" * 60)
    
    try:
        test_config_loading()
        test_default_negative_prompt()
        test_preset_details()
        test_lora_catalog()
        test_lora_preset_resolution()
        test_validation_config()
        test_singleton_pattern()
        test_nonexistent_preset()
        test_lora_info()
        
        print("\n" + "=" * 60)
        print("[OK] All config tests passed!")
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
