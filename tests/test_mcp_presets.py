#!/usr/bin/env python3
"""Test MCP server preset integration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.config import get_config_loader


async def test_mcp_preset_integration():
    """Test that MCP server loads and uses presets correctly."""
    print("\n" + "=" * 60)
    print("TESTING MCP PRESET INTEGRATION")
    print("=" * 60)

    # Test 1: Config loader is available
    print("\n[TEST] Config loader availability")
    print("-" * 60)

    config_loader = get_config_loader()
    assert config_loader is not None
    print("[OK] Config loader initialized")

    # Test 2: Load presets
    print("\n[TEST] Loading presets")
    print("-" * 60)

    presets = config_loader.load_presets()
    assert "presets" in presets
    assert "default_negative_prompt" in presets
    assert "validation" in presets

    preset_names = list(presets["presets"].keys())
    print(f"[OK] Loaded {len(preset_names)} presets: {', '.join(preset_names)}")

    # Test 3: Default negative prompt
    print("\n[TEST] Default negative prompt")
    print("-" * 60)

    default_neg = config_loader.get_default_negative_prompt()
    assert len(default_neg) > 0
    print(f"[OK] Default negative prompt: {default_neg[:70]}...")

    # Test 4: Get specific presets
    print("\n[TEST] Getting specific presets")
    print("-" * 60)

    test_presets = ["draft", "balanced", "high-quality"]
    for preset_name in test_presets:
        preset = config_loader.get_preset(preset_name)
        assert preset is not None, f"Preset '{preset_name}' not found"
        assert "steps" in preset
        assert "cfg" in preset
        assert "sampler" in preset
        assert "scheduler" in preset
        print(f"[OK] {preset_name}: steps={preset['steps']}, cfg={preset['cfg']}, sampler={preset['sampler']}")

    # Test 5: Load LoRA catalog
    print("\n[TEST] Loading LoRA catalog")
    print("-" * 60)

    catalog = config_loader.load_lora_catalog()
    assert "loras" in catalog
    assert "model_suggestions" in catalog

    lora_count = len(catalog["loras"])
    suggestion_count = len(catalog["model_suggestions"])
    print(f"[OK] Loaded {lora_count} LoRAs and {suggestion_count} model suggestions")

    # Test 6: Get LoRA presets
    print("\n[TEST] Getting LoRA presets")
    print("-" * 60)

    test_lora_presets = ["text_to_video", "simple_image"]
    for lora_preset_name in test_lora_presets:
        lora_preset = config_loader.get_lora_preset(lora_preset_name)
        assert lora_preset is not None, f"LoRA preset '{lora_preset_name}' not found"
        assert "model" in lora_preset
        assert "workflow" in lora_preset
        assert "default_loras" in lora_preset
        print(f"[OK] {lora_preset_name}: {len(lora_preset.get('default_loras', []))} default LoRAs")

    # Test 7: Validation settings
    print("\n[TEST] Validation settings")
    print("-" * 60)

    validation = config_loader.get_validation_settings()
    assert "enabled" in validation
    assert "auto_retry" in validation
    assert "retry_limit" in validation
    assert "positive_threshold" in validation
    print(
        f"[OK] Validation: enabled={validation['enabled']}, auto_retry={validation['auto_retry']}, retry_limit={validation['retry_limit']}"
    )

    # Test 8: Preset parameter merging logic simulation
    print("\n[TEST] Preset parameter merging logic")
    print("-" * 60)

    # Simulate what the MCP server does when merging preset with user params
    preset = config_loader.get_preset("draft")
    validation_config = config_loader.get_validation_settings()

    # User provides no parameters (all None)
    user_steps = None
    user_cfg = None
    user_sampler = None
    user_validate = None

    # Apply defaults (preset > config defaults)
    final_steps = user_steps if user_steps is not None else preset.get("steps", 20)
    final_cfg = user_cfg if user_cfg is not None else preset.get("cfg", 7.0)
    final_sampler = user_sampler if user_sampler is not None else preset.get("sampler", "euler")
    final_validate = (
        user_validate if user_validate is not None else preset.get("validate", validation_config.get("enabled", True))
    )

    assert final_steps == 10  # From draft preset
    assert final_cfg == 5.0  # From draft preset
    assert final_sampler == "euler"  # From draft preset
    assert not final_validate  # From draft preset
    print(
        f"[OK] Merged params: steps={final_steps}, cfg={final_cfg}, sampler={final_sampler}, validate={final_validate}"
    )

    # Test 9: User override of preset
    print("\n[TEST] User override of preset")
    print("-" * 60)

    # User provides some parameters
    user_steps = 30
    user_cfg = None  # Will use preset

    final_steps = user_steps if user_steps is not None else preset.get("steps", 20)
    final_cfg = user_cfg if user_cfg is not None else preset.get("cfg", 7.0)

    assert final_steps == 30  # User override
    assert final_cfg == 5.0  # From preset
    print(f"[OK] User override: steps={final_steps} (user), cfg={final_cfg} (preset)")

    # Test 10: LoRA preset conversion
    print("\n[TEST] LoRA preset conversion")
    print("-" * 60)

    lora_preset_data = config_loader.get_lora_preset("text_to_video")
    default_loras = lora_preset_data.get("default_loras", [])

    # Convert to format expected by generate_image
    loras = []
    for lora_filename in default_loras:
        # Find LoRA details in catalog
        lora_info = None
        for lora in catalog.get("loras", []):
            if lora.get("filename") == lora_filename:
                lora_info = lora
                break

        strength = lora_info.get("recommended_strength", 1.0) if lora_info else 1.0
        loras.append({"name": lora_filename, "strength": strength})

    assert len(loras) > 0, "No LoRAs converted"
    print(f"[OK] Converted {len(loras)} LoRAs:")
    for lora in loras:
        print(f"    - {lora['name']}: strength={lora['strength']}")

    print("\n" + "=" * 60)
    print("ALL MCP PRESET INTEGRATION TESTS PASSED")
    print("=" * 60)


def test_cli_mcp_parity():
    """Test that CLI and MCP use same configuration."""
    print("\n" + "=" * 60)
    print("TESTING CLI/MCP CONFIGURATION PARITY")
    print("=" * 60)

    # Import both config loaders
    import sys

    from comfygen.config import get_config_loader as mcp_config_loader

    # Add generate.py to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from generate import load_config as cli_load_config

    print("\n[TEST] Loading configs from both CLI and MCP")
    print("-" * 60)

    # Load configs
    mcp_loader = mcp_config_loader()
    mcp_config = mcp_loader.load_presets()
    cli_config = cli_load_config()

    # Compare default_negative_prompt
    print("\n[TEST] Comparing default negative prompts")
    assert mcp_config["default_negative_prompt"] == cli_config["default_negative_prompt"]
    print("[OK] Both use same default negative prompt")

    # Compare validation settings
    print("\n[TEST] Comparing validation settings")
    mcp_val = mcp_config["validation"]
    cli_val = cli_config["validation"]

    assert mcp_val["enabled"] == cli_val["enabled"]
    assert mcp_val["auto_retry"] == cli_val["auto_retry"]
    assert mcp_val["retry_limit"] == cli_val["retry_limit"]
    assert mcp_val["positive_threshold"] == cli_val["positive_threshold"]
    print("[OK] Both use same validation settings")

    # Compare presets
    print("\n[TEST] Comparing presets")
    mcp_presets = mcp_config["presets"]
    cli_presets = cli_config["presets"]

    assert set(mcp_presets.keys()) == set(cli_presets.keys())
    print(f"[OK] Both have same preset names: {', '.join(mcp_presets.keys())}")

    # Compare each preset
    for preset_name in mcp_presets.keys():
        mcp_preset = mcp_presets[preset_name]
        cli_preset = cli_presets[preset_name]

        assert mcp_preset["steps"] == cli_preset["steps"]
        assert mcp_preset["cfg"] == cli_preset["cfg"]
        assert mcp_preset["sampler"] == cli_preset["sampler"]
        assert mcp_preset["scheduler"] == cli_preset["scheduler"]

    print(f"[OK] All {len(mcp_presets)} presets match between CLI and MCP")

    print("\n" + "=" * 60)
    print("CLI/MCP PARITY TESTS PASSED")
    print("=" * 60)


async def run_all_tests():
    """Run all async tests."""
    try:
        await test_mcp_preset_integration()
        test_cli_mcp_parity()
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
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
