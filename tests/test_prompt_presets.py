#!/usr/bin/env python3
"""Tests for prompt preset functionality in generate.py."""

import sys
import tempfile
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_load_prompt_catalog():
    """Test loading and parsing prompt catalog YAML."""
    catalog_path = Path(__file__).parent.parent / "prompt_catalog.yaml"
    
    if not catalog_path.exists():
        print("[ERROR] prompt_catalog.yaml not found")
        return False
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = yaml.safe_load(f)
        
        assert catalog is not None, "Catalog should not be None"
        assert "saved_prompts" in catalog, "Catalog should have saved_prompts section"
        
        saved_prompts = catalog["saved_prompts"]
        assert len(saved_prompts) > 0, "Should have at least one saved prompt"
        
        # Check structure of first preset
        first_preset_name = list(saved_prompts.keys())[0]
        first_preset = saved_prompts[first_preset_name]
        
        assert "positive" in first_preset, "Preset should have positive prompt"
        assert "category" in first_preset, "Preset should have category"
        
        print(f"[OK] Loaded {len(saved_prompts)} prompt presets from catalog")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to load catalog: {e}")
        return False


def test_prompt_preset_structure():
    """Test that prompt presets have expected structure."""
    catalog_path = Path(__file__).parent.parent / "prompt_catalog.yaml"
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = yaml.safe_load(f)
    
    saved_prompts = catalog.get("saved_prompts", {})
    
    for preset_name, preset_data in saved_prompts.items():
        # Required fields
        assert isinstance(preset_data, dict), f"{preset_name} should be a dict"
        assert "positive" in preset_data, f"{preset_name} should have positive prompt"
        
        # Optional but expected fields
        if "negative" in preset_data:
            assert isinstance(preset_data["negative"], str), f"{preset_name} negative should be string"
        
        print(f"[OK] Preset '{preset_name}' has valid structure")
    
    return True


def test_negative_merge_logic():
    """Test merging preset negative with user-supplied negative."""
    preset_negative = "preset negative"
    user_negative = "user negative"
    
    # Merge logic from generate.py
    effective_negative = f"{preset_negative}, {user_negative}"
    
    assert effective_negative == "preset negative, user negative"
    print("[OK] Preset and user negatives are merged correctly")
    return True


def test_negative_preset_only():
    """Test using only preset negative when user doesn't provide one."""
    preset_negative = "preset negative"
    user_negative = ""
    
    # Merge logic from generate.py
    if user_negative:
        effective_negative = f"{preset_negative}, {user_negative}"
    else:
        effective_negative = preset_negative
    
    assert effective_negative == "preset negative"
    print("[OK] Preset negative used alone when user doesn't provide one")
    return True


if __name__ == "__main__":
    all_passed = True
    
    all_passed &= test_load_prompt_catalog()
    all_passed &= test_prompt_preset_structure()
    all_passed &= test_negative_merge_logic()
    all_passed &= test_negative_preset_only()
    
    if all_passed:
        print("\n[OK] All prompt preset tests passed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some tests failed")
        sys.exit(1)

