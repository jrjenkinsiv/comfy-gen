#!/usr/bin/env python3
"""Test configuration loader for presets and LoRA catalogs."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import ConfigLoader, get_config_loader


def test_config_loader_initialization():
    """Test ConfigLoader initialization."""
    print("\n[TEST] ConfigLoader initialization")
    print("=" * 60)

    # Create a loader
    loader = ConfigLoader()

    # Check paths are set correctly
    assert loader.presets_path.name == "presets.yaml"
    assert loader.lora_catalog_path.name == "lora_catalog.yaml"

    print(f"[OK] Presets path: {loader.presets_path}")
    print(f"[OK] LoRA catalog path: {loader.lora_catalog_path}")
    print("[OK] ConfigLoader initialization test passed")


def test_load_presets():
    """Test loading presets.yaml."""
    print("\n[TEST] Loading presets.yaml")
    print("=" * 60)

    loader = ConfigLoader()
    config = loader.load_presets()

    # Check required keys
    assert "presets" in config
    assert "default_negative_prompt" in config
    assert "validation" in config

    # Check presets exist
    presets = config["presets"]
    assert len(presets) > 0, "No presets found"

    # Check expected presets
    expected_presets = ["draft", "balanced", "high-quality", "fast", "ultra"]
    for preset_name in expected_presets:
        assert preset_name in presets, f"Preset '{preset_name}' not found"
        print(f"[OK] Found preset: {preset_name}")

    # Check default negative prompt
    default_neg = config["default_negative_prompt"]
    assert len(default_neg) > 0, "Default negative prompt is empty"
    print(f"[OK] Default negative prompt: {default_neg[:50]}...")

    # Check validation settings
    validation = config["validation"]
    assert "enabled" in validation
    assert "auto_retry" in validation
    assert "retry_limit" in validation
    assert "positive_threshold" in validation
    print(f"[OK] Validation settings: {validation}")

    print("[OK] Load presets test passed")


def test_get_preset():
    """Test getting specific preset."""
    print("\n[TEST] Getting specific preset")
    print("=" * 60)

    loader = ConfigLoader()

    # Test valid preset
    draft = loader.get_preset("draft")
    assert draft is not None, "Draft preset not found"
    assert "steps" in draft
    assert "cfg" in draft
    assert "sampler" in draft
    assert "scheduler" in draft
    print(f"[OK] Draft preset: {draft}")

    # Test invalid preset
    invalid = loader.get_preset("nonexistent")
    assert invalid is None, "Should return None for invalid preset"
    print("[OK] Returns None for invalid preset")

    print("[OK] Get preset test passed")


def test_get_default_negative_prompt():
    """Test getting default negative prompt."""
    print("\n[TEST] Getting default negative prompt")
    print("=" * 60)

    loader = ConfigLoader()
    default_neg = loader.get_default_negative_prompt()

    assert isinstance(default_neg, str)
    assert len(default_neg) > 0
    print(f"[OK] Default negative prompt: {default_neg}")

    print("[OK] Get default negative prompt test passed")


def test_get_validation_settings():
    """Test getting validation settings."""
    print("\n[TEST] Getting validation settings")
    print("=" * 60)

    loader = ConfigLoader()
    validation = loader.get_validation_settings()

    assert isinstance(validation, dict)
    assert "enabled" in validation
    assert "auto_retry" in validation
    print(f"[OK] Validation settings: {validation}")

    print("[OK] Get validation settings test passed")


def test_load_lora_catalog():
    """Test loading lora_catalog.yaml."""
    print("\n[TEST] Loading lora_catalog.yaml")
    print("=" * 60)

    loader = ConfigLoader()
    catalog = loader.load_lora_catalog()

    # Check required keys
    assert "loras" in catalog
    assert "model_suggestions" in catalog
    assert "keyword_mappings" in catalog

    # Check LoRAs exist
    loras = catalog["loras"]
    assert len(loras) > 0, "No LoRAs found"
    print(f"[OK] Found {len(loras)} LoRAs")

    # Check a LoRA has expected fields
    first_lora = loras[0]
    assert "filename" in first_lora
    assert "tags" in first_lora
    assert "compatible_with" in first_lora
    assert "recommended_strength" in first_lora
    print(f"[OK] First LoRA: {first_lora['filename']}")

    # Check model suggestions
    suggestions = catalog["model_suggestions"]
    assert len(suggestions) > 0, "No model suggestions found"
    print(f"[OK] Found {len(suggestions)} model suggestions")

    print("[OK] Load LoRA catalog test passed")


def test_get_lora_preset():
    """Test getting specific LoRA preset."""
    print("\n[TEST] Getting specific LoRA preset")
    print("=" * 60)

    loader = ConfigLoader()

    # Test valid preset
    t2v = loader.get_lora_preset("text_to_video")
    assert t2v is not None, "text_to_video preset not found"
    assert "model" in t2v
    assert "workflow" in t2v
    assert "default_loras" in t2v
    print(f"[OK] text_to_video preset: {t2v}")

    # Test invalid preset
    invalid = loader.get_lora_preset("nonexistent")
    assert invalid is None, "Should return None for invalid preset"
    print("[OK] Returns None for invalid preset")

    print("[OK] Get LoRA preset test passed")


def test_global_config_loader():
    """Test global config loader singleton."""
    print("\n[TEST] Global config loader singleton")
    print("=" * 60)

    loader1 = get_config_loader()
    loader2 = get_config_loader()

    # Should be same instance
    assert loader1 is loader2, "Should return same instance"
    print("[OK] Global config loader returns same instance")

    print("[OK] Global config loader test passed")


def test_caching():
    """Test that configs are cached."""
    print("\n[TEST] Configuration caching")
    print("=" * 60)

    loader = ConfigLoader()

    # Load presets twice
    config1 = loader.load_presets()
    config2 = loader.load_presets()

    # Should be same object (cached)
    assert config1 is config2, "Should return cached config"
    print("[OK] Presets are cached")

    # Load catalog twice
    catalog1 = loader.load_lora_catalog()
    catalog2 = loader.load_lora_catalog()

    # Should be same object (cached)
    assert catalog1 is catalog2, "Should return cached catalog"
    print("[OK] LoRA catalog is cached")

    # Force reload should return new object
    config3 = loader.load_presets(force_reload=True)
    assert config3 is not config1, "Force reload should return new object"
    print("[OK] Force reload returns new object")

    print("[OK] Configuration caching test passed")


def test_preset_parameters():
    """Test that presets have expected parameters."""
    print("\n[TEST] Preset parameters validation")
    print("=" * 60)

    loader = ConfigLoader()
    presets = loader.load_presets()["presets"]

    # Check each preset has required fields
    for preset_name, preset_config in presets.items():
        print(f"\n[OK] Checking preset: {preset_name}")

        # All presets should have these
        assert "steps" in preset_config, f"{preset_name} missing 'steps'"
        assert "cfg" in preset_config, f"{preset_name} missing 'cfg'"
        assert "sampler" in preset_config, f"{preset_name} missing 'sampler'"
        assert "scheduler" in preset_config, f"{preset_name} missing 'scheduler'"

        # Validate types and ranges
        assert isinstance(preset_config["steps"], int)
        assert preset_config["steps"] > 0
        assert isinstance(preset_config["cfg"], (int, float))
        assert preset_config["cfg"] > 0
        assert isinstance(preset_config["sampler"], str)
        assert isinstance(preset_config["scheduler"], str)

        print(f"    steps: {preset_config['steps']}")
        print(f"    cfg: {preset_config['cfg']}")
        print(f"    sampler: {preset_config['sampler']}")
        print(f"    scheduler: {preset_config['scheduler']}")

    print("\n[OK] All presets have valid parameters")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RUNNING CONFIG LOADER TESTS")
    print("=" * 60)

    try:
        test_config_loader_initialization()
        test_load_presets()
        test_get_preset()
        test_get_default_negative_prompt()
        test_get_validation_settings()
        test_load_lora_catalog()
        test_get_lora_preset()
        test_global_config_loader()
        test_caching()
        test_preset_parameters()

        print("\n" + "=" * 60)
        print("ALL CONFIG LOADER TESTS PASSED")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
