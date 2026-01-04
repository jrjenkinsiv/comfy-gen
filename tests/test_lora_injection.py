#!/usr/bin/env python3
"""Tests for LoRA injection functionality."""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_load_lora_presets_success():
    """Test loading LoRA presets from catalog."""
    # Mock the catalog file
    mock_catalog = {
        "loras": [
            {
                "filename": "test_lora.safetensors",
                "recommended_strength": 0.8
            }
        ],
        "model_suggestions": {
            "test_preset": {
                "default_loras": ["test_lora.safetensors"]
            }
        }
    }
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = ""  # Not used due to patch
        with patch('yaml.safe_load', return_value=mock_catalog):
            with patch.object(Path, 'exists', return_value=True):
                catalog = generate.load_lora_presets()
                assert catalog is not None
                assert "loras" in catalog
                assert "model_suggestions" in catalog
                print("[OK] load_lora_presets loads catalog successfully")


def test_load_lora_presets_missing_file():
    """Test load_lora_presets when file doesn't exist."""
    with patch.object(Path, 'exists', return_value=False):
        catalog = generate.load_lora_presets()
        assert catalog == {}
        print("[OK] load_lora_presets handles missing file")


def test_list_available_loras():
    """Test listing available LoRAs from API."""
    mock_models = {
        "loras": ["lora1.safetensors", "lora2.safetensors"]
    }
    
    loras = generate.list_available_loras(mock_models)
    assert loras == ["lora1.safetensors", "lora2.safetensors"]
    print("[OK] list_available_loras returns LoRA list")


def test_list_available_loras_no_loras():
    """Test listing when no LoRAs available."""
    mock_models = {}
    
    loras = generate.list_available_loras(mock_models)
    assert loras == []
    print("[OK] list_available_loras handles empty list")


def test_validate_lora_exists_success():
    """Test LoRA validation when LoRA exists."""
    available_loras = ["test_lora.safetensors", "another_lora.safetensors"]
    
    result = generate.validate_lora_exists("test_lora.safetensors", available_loras)
    assert result is True
    print("[OK] validate_lora_exists returns True for existing LoRA")


def test_validate_lora_exists_failure():
    """Test LoRA validation when LoRA doesn't exist."""
    available_loras = ["test_lora.safetensors"]
    
    result = generate.validate_lora_exists("missing_lora.safetensors", available_loras)
    assert result is False
    print("[OK] validate_lora_exists returns False for missing LoRA")


def test_find_model_output_connections():
    """Test finding connections from a node output."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["1", 1]
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0]
            }
        }
    }
    
    # Find connections to node 1, output 0 (model)
    connections = generate.find_model_output_connections(workflow, "1", 0)
    assert len(connections) == 1
    assert ("3", "model") in connections
    print("[OK] find_model_output_connections finds model connections")
    
    # Find connections to node 1, output 1 (clip)
    connections = generate.find_model_output_connections(workflow, "1", 1)
    assert len(connections) == 1
    assert ("2", "clip") in connections
    print("[OK] find_model_output_connections finds CLIP connections")


def test_inject_lora_sd15_workflow():
    """Test injecting LoRA into SD 1.5 workflow."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd15.safetensors"
            }
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0]
            }
        }
    }
    
    modified, new_id = generate.inject_lora(
        workflow,
        "test_lora.safetensors",
        strength_model=0.8,
        strength_clip=0.8
    )
    
    assert new_id is not None
    assert new_id in modified
    assert modified[new_id]["class_type"] == "LoraLoader"
    assert modified[new_id]["inputs"]["lora_name"] == "test_lora.safetensors"
    assert modified[new_id]["inputs"]["strength_model"] == 0.8
    assert modified[new_id]["inputs"]["strength_clip"] == 0.8
    
    # Check that KSampler now connects to LoRA instead of checkpoint
    assert modified["2"]["inputs"]["model"] == [new_id, 0]
    print("[OK] inject_lora injects LoRA into SD 1.5 workflow")


def test_inject_lora_wan22_workflow():
    """Test injecting LoRA into Wan 2.2 workflow."""
    workflow = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.2.safetensors"
            }
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {}
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0]
            }
        }
    }
    
    modified, new_id = generate.inject_lora(
        workflow,
        "wan_lora.safetensors",
        strength_model=1.0,
        strength_clip=1.0
    )
    
    assert new_id is not None
    assert new_id in modified
    assert modified[new_id]["class_type"] == "LoraLoader"
    
    # Check that KSampler connects to LoRA
    assert modified["3"]["inputs"]["model"] == [new_id, 0]
    print("[OK] inject_lora injects LoRA into Wan 2.2 workflow")


def test_inject_lora_chain():
    """Test chaining multiple LoRAs."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd15.safetensors"
            }
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0]
            }
        }
    }
    
    lora_specs = [
        ("lora1.safetensors", 0.7, 0.7),
        ("lora2.safetensors", 0.5, 0.5)
    ]
    
    available_loras = ["lora1.safetensors", "lora2.safetensors"]
    
    modified = generate.inject_lora_chain(workflow, lora_specs, available_loras)
    
    # Count LoRA nodes
    lora_nodes = [
        node_id for node_id, node in modified.items()
        if node.get("class_type") == "LoraLoader"
    ]
    
    assert len(lora_nodes) == 2
    print(f"[OK] inject_lora_chain creates {len(lora_nodes)} LoRA nodes")
    
    # Verify they are chained (second LoRA connects to first)
    lora1_id = lora_nodes[0]
    lora2_id = lora_nodes[1]
    
    # Second LoRA should connect to first LoRA's output
    assert modified[lora2_id]["inputs"]["model"] == [lora1_id, 0]
    print("[OK] inject_lora_chain chains LoRAs correctly")


def test_inject_lora_chain_missing_lora():
    """Test that inject_lora_chain fails gracefully with missing LoRA."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {}
        }
    }
    
    lora_specs = [
        ("missing_lora.safetensors", 0.8, 0.8)
    ]
    
    available_loras = ["other_lora.safetensors"]
    
    # Should return unmodified workflow
    modified = generate.inject_lora_chain(workflow, lora_specs, available_loras)
    
    # No LoRA nodes should be added
    lora_nodes = [
        node_id for node_id, node in modified.items()
        if node.get("class_type") == "LoraLoader"
    ]
    
    assert len(lora_nodes) == 0
    print("[OK] inject_lora_chain handles missing LoRA gracefully")


def test_inject_lora_no_checkpoint():
    """Test that inject_lora fails when no checkpoint loader found."""
    workflow = {
        "1": {
            "class_type": "SomeOtherNode",
            "inputs": {}
        }
    }
    
    modified, new_id = generate.inject_lora(workflow, "test_lora.safetensors")
    
    assert new_id is None
    print("[OK] inject_lora handles missing checkpoint loader")


def test_inject_lora_empty_workflow():
    """Test that inject_lora fails gracefully with empty workflow."""
    workflow = {}
    
    modified, new_id = generate.inject_lora(workflow, "test_lora.safetensors")
    
    assert new_id is None
    print("[OK] inject_lora handles empty workflow")


def test_inject_lora_non_numeric_keys():
    """Test that inject_lora fails gracefully with non-numeric keys."""
    workflow = {
        "abc": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {}
        }
    }
    
    modified, new_id = generate.inject_lora(workflow, "test_lora.safetensors")
    
    assert new_id is None
    print("[OK] inject_lora handles non-numeric keys")


if __name__ == "__main__":
    print("Running LoRA injection tests...\n")
    
    tests = [
        test_load_lora_presets_success,
        test_load_lora_presets_missing_file,
        test_list_available_loras,
        test_list_available_loras_no_loras,
        test_validate_lora_exists_success,
        test_validate_lora_exists_failure,
        test_find_model_output_connections,
        test_inject_lora_sd15_workflow,
        test_inject_lora_wan22_workflow,
        test_inject_lora_chain,
        test_inject_lora_chain_missing_lora,
        test_inject_lora_no_checkpoint,
        test_inject_lora_empty_workflow,
        test_inject_lora_non_numeric_keys,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning {test.__name__}...")
            test()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    sys.exit(0 if failed == 0 else 1)
