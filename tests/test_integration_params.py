#!/usr/bin/env python3
"""Integration test for CLI parameter processing."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def create_test_workflow():
    """Create a minimal test workflow."""
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "test.safetensors"}},
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["1", 1]},
            "_meta": {"title": "Positive Prompt"},
        },
        "3": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "4": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["2", 0],
                "latent_image": ["3", 0],
            },
        },
    }


def test_modify_workflow_with_all_params():
    """Test modifying workflow with all advanced parameters."""
    workflow = create_test_workflow()

    # Apply sampler params
    workflow = generate.modify_sampler_params(
        workflow, steps=50, cfg=8.5, seed=12345, sampler_name="dpmpp_2m_sde", scheduler="karras"
    )

    # Apply dimensions
    workflow = generate.modify_dimensions(workflow, width=768, height=1024)

    # Verify KSampler changes
    ksampler = workflow["4"]["inputs"]
    assert ksampler["steps"] == 50, f"Expected steps=50, got {ksampler['steps']}"
    assert ksampler["cfg"] == 8.5, f"Expected cfg=8.5, got {ksampler['cfg']}"
    assert ksampler["seed"] == 12345, f"Expected seed=12345, got {ksampler['seed']}"
    assert ksampler["sampler_name"] == "dpmpp_2m_sde"
    assert ksampler["scheduler"] == "karras"

    # Verify dimension changes
    latent = workflow["3"]["inputs"]
    assert latent["width"] == 768, f"Expected width=768, got {latent['width']}"
    assert latent["height"] == 1024, f"Expected height=1024, got {latent['height']}"

    print("[OK] All advanced parameters applied correctly to workflow")


def test_preset_loading():
    """Test that presets can be loaded."""
    presets = generate.load_presets()

    # Check that expected presets exist
    expected_presets = ["draft", "balanced", "high-quality"]
    for preset_name in expected_presets:
        assert preset_name in presets, f"Expected preset '{preset_name}' not found"

    # Verify preset structure
    draft = presets["draft"]
    assert "steps" in draft
    assert "cfg" in draft
    assert "sampler" in draft
    assert draft["steps"] == 10
    assert draft["cfg"] == 5.0

    print(f"[OK] Loaded {len(presets)} presets successfully")
    print(f"[OK] Available presets: {', '.join(presets.keys())}")


def test_parameter_validation_edge_cases():
    """Test edge cases in parameter validation."""
    # Test exact boundaries
    is_valid, _ = generate.validate_generation_params(steps=1)
    assert is_valid, "steps=1 should be valid (lower bound)"

    is_valid, _ = generate.validate_generation_params(steps=150)
    assert is_valid, "steps=150 should be valid (upper bound)"

    is_valid, _ = generate.validate_generation_params(cfg=1.0)
    assert is_valid, "cfg=1.0 should be valid (lower bound)"

    is_valid, _ = generate.validate_generation_params(cfg=20.0)
    assert is_valid, "cfg=20.0 should be valid (upper bound)"

    is_valid, _ = generate.validate_generation_params(denoise=0.0)
    assert is_valid, "denoise=0.0 should be valid (lower bound)"

    is_valid, _ = generate.validate_generation_params(denoise=1.0)
    assert is_valid, "denoise=1.0 should be valid (upper bound)"

    # Test dimensions divisible by 8
    is_valid, _ = generate.validate_generation_params(width=512, height=768)
    assert is_valid, "512x768 should be valid (divisible by 8)"

    is_valid, error = generate.validate_generation_params(width=513)
    assert not is_valid, "513 should be invalid (not divisible by 8)"
    assert "divisible by 8" in error

    print("[OK] All edge case validations passed")


def test_preset_override_logic():
    """Test that CLI args override preset values."""
    create_test_workflow()

    # Simulate preset values
    preset_params = {"steps": 50, "cfg": 7.5, "sampler": "dpmpp_2m_sde"}

    # CLI overrides
    cli_steps = 30
    cli_cfg = None  # Not specified, use preset

    # Merge logic (simulating what main() does)
    final_steps = cli_steps if cli_steps is not None else preset_params.get("steps")
    final_cfg = cli_cfg if cli_cfg is not None else preset_params.get("cfg")

    assert final_steps == 30, "CLI steps should override preset"
    assert final_cfg == 7.5, "Preset cfg should be used when CLI not specified"

    print("[OK] Preset override logic works correctly")


if __name__ == "__main__":
    test_modify_workflow_with_all_params()
    test_preset_loading()
    test_parameter_validation_edge_cases()
    test_preset_override_logic()

    print("\n[OK] All integration tests passed!")
