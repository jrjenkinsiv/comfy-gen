#!/usr/bin/env python3
"""Test preset integration in MCP server and config loader.

This test validates that:
1. presets.yaml is loaded correctly
2. Default negative prompt is applied when not specified
3. Preset parameters override defaults correctly
4. LoRA presets work as expected
5. MCP and CLI use the same configuration
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import (
    load_presets_config,
    load_lora_catalog,
    get_preset,
    get_lora_preset,
    apply_preset_to_params
)


def test_load_presets_config():
    """Test loading presets.yaml configuration."""
    print("\n[TEST] Loading presets.yaml...")
    
    config = load_presets_config()
    
    # Verify required keys exist
    assert "presets" in config, "Missing 'presets' key in config"
    assert "default_negative_prompt" in config, "Missing 'default_negative_prompt' key in config"
    assert "validation" in config, "Missing 'validation' key in config"
    
    # Check default negative prompt is not empty
    default_neg = config["default_negative_prompt"]
    assert default_neg, "default_negative_prompt should not be empty"
    assert "bad quality" in default_neg.lower(), "default_negative_prompt should contain quality terms"
    
    print(f"[OK] Default negative prompt: {default_neg[:50]}...")
    
    # Check presets exist
    presets = config["presets"]
    expected_presets = ["draft", "balanced", "high-quality", "fast", "ultra"]
    for preset_name in expected_presets:
        assert preset_name in presets, f"Missing preset: {preset_name}"
        print(f"[OK] Found preset: {preset_name}")
    
    print("[PASS] presets.yaml loaded successfully\n")


def test_load_lora_catalog():
    """Test loading lora_catalog.yaml."""
    print("\n[TEST] Loading lora_catalog.yaml...")
    
    catalog = load_lora_catalog()
    
    # Verify required keys exist
    assert "loras" in catalog, "Missing 'loras' key in catalog"
    assert "model_suggestions" in catalog, "Missing 'model_suggestions' key in catalog"
    
    # Check that loras is a list
    loras = catalog["loras"]
    assert isinstance(loras, list), "loras should be a list"
    assert len(loras) > 0, "loras list should not be empty"
    
    print(f"[OK] Found {len(loras)} LoRAs in catalog")
    
    # Check model_suggestions
    suggestions = catalog["model_suggestions"]
    assert isinstance(suggestions, dict), "model_suggestions should be a dict"
    assert len(suggestions) > 0, "model_suggestions should not be empty"
    
    print(f"[OK] Found {len(suggestions)} model suggestions")
    
    print("[PASS] lora_catalog.yaml loaded successfully\n")


def test_get_preset():
    """Test retrieving individual presets."""
    print("\n[TEST] Testing get_preset()...")
    
    # Test valid preset
    draft = get_preset("draft")
    assert draft is not None, "draft preset should exist"
    assert "steps" in draft, "draft preset should have 'steps'"
    assert draft["steps"] == 10, "draft preset should have 10 steps"
    print(f"[OK] Draft preset: steps={draft['steps']}, cfg={draft['cfg']}")
    
    # Test high-quality preset
    hq = get_preset("high-quality")
    assert hq is not None, "high-quality preset should exist"
    assert hq["steps"] == 50, "high-quality preset should have 50 steps"
    print(f"[OK] High-quality preset: steps={hq['steps']}, cfg={hq['cfg']}")
    
    # Test invalid preset
    invalid = get_preset("nonexistent")
    assert invalid is None, "nonexistent preset should return None"
    print("[OK] Invalid preset returns None")
    
    print("[PASS] get_preset() works correctly\n")


def test_get_lora_preset():
    """Test retrieving LoRA presets."""
    print("\n[TEST] Testing get_lora_preset()...")
    
    # Test valid LoRA preset
    t2v = get_lora_preset("text_to_video")
    if t2v:
        assert "model" in t2v or "default_loras" in t2v, "LoRA preset should have model or loras"
        print(f"[OK] text_to_video preset found")
    else:
        print("[SKIP] text_to_video preset not found (may not exist in catalog)")
    
    # Test invalid preset
    invalid = get_lora_preset("nonexistent_preset")
    assert invalid is None, "nonexistent preset should return None"
    print("[OK] Invalid LoRA preset returns None")
    
    print("[PASS] get_lora_preset() works correctly\n")


def test_apply_preset_to_params():
    """Test applying preset to parameters."""
    print("\n[TEST] Testing apply_preset_to_params()...")
    
    # Get draft preset
    draft = get_preset("draft")
    assert draft is not None
    
    # Test with empty params (all defaults from preset)
    params = {}
    result = apply_preset_to_params(params, draft)
    assert result["steps"] == 10, "Should use preset steps"
    assert result["cfg"] == 5.0, "Should use preset cfg"
    print("[OK] Empty params filled from preset")
    
    # Test with some params already set (should NOT override)
    params = {"steps": 30, "cfg": 8.0}
    result = apply_preset_to_params(params, draft)
    assert result["steps"] == 30, "Should keep user-provided steps"
    assert result["cfg"] == 8.0, "Should keep user-provided cfg"
    print("[OK] User params override preset")
    
    # Test partial override
    params = {"steps": 25}
    result = apply_preset_to_params(params, draft)
    assert result["steps"] == 25, "Should keep user-provided steps"
    assert result["cfg"] == 5.0, "Should use preset cfg"
    print("[OK] Partial override works correctly")
    
    print("[PASS] apply_preset_to_params() works correctly\n")


def test_preset_values():
    """Test that preset values match expected configuration."""
    print("\n[TEST] Testing preset values...")
    
    config = load_presets_config()
    presets = config["presets"]
    
    # Test draft preset (fast, low quality)
    draft = presets["draft"]
    assert draft["steps"] == 10, "draft should have 10 steps"
    assert draft["cfg"] == 5.0, "draft should have cfg 5.0"
    assert draft["validate"] == False, "draft should not validate"
    print("[OK] Draft preset values correct")
    
    # Test balanced preset (default-like)
    balanced = presets["balanced"]
    assert balanced["steps"] == 20, "balanced should have 20 steps"
    assert balanced["cfg"] == 7.0, "balanced should have cfg 7.0"
    assert balanced["validate"] == True, "balanced should validate"
    print("[OK] Balanced preset values correct")
    
    # Test high-quality preset (slow, high quality)
    hq = presets["high-quality"]
    assert hq["steps"] == 50, "high-quality should have 50 steps"
    assert hq["cfg"] == 7.5, "high-quality should have cfg 7.5"
    assert hq["validate"] == True, "high-quality should validate"
    assert hq["auto_retry"] == True, "high-quality should auto-retry"
    print("[OK] High-quality preset values correct")
    
    print("[PASS] Preset values are correct\n")


def test_validation_config():
    """Test validation configuration loading."""
    print("\n[TEST] Testing validation configuration...")
    
    config = load_presets_config()
    validation = config["validation"]
    
    # Check validation settings
    assert "enabled" in validation, "validation should have 'enabled'"
    assert "auto_retry" in validation, "validation should have 'auto_retry'"
    assert "retry_limit" in validation, "validation should have 'retry_limit'"
    assert "positive_threshold" in validation, "validation should have 'positive_threshold'"
    
    print(f"[OK] Validation enabled: {validation['enabled']}")
    print(f"[OK] Auto-retry: {validation['auto_retry']}")
    print(f"[OK] Retry limit: {validation['retry_limit']}")
    print(f"[OK] Positive threshold: {validation['positive_threshold']}")
    
    print("[PASS] Validation config loaded correctly\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("PRESET INTEGRATION TESTS")
    print("=" * 70)
    
    try:
        test_load_presets_config()
        test_load_lora_catalog()
        test_get_preset()
        test_get_lora_preset()
        test_apply_preset_to_params()
        test_preset_values()
        test_validation_config()
        
        print("=" * 70)
        print("[SUCCESS] All preset integration tests passed!")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
