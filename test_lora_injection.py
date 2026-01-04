#!/usr/bin/env python3
"""Tests for LoRA injection functionality."""

import json
import sys
from pathlib import Path

# Add current directory to path to import generate module
sys.path.insert(0, str(Path(__file__).parent))

from generate import (
    parse_lora_arg,
    find_checkpoint_loader,
    find_consumers,
    inject_loras,
    load_lora_presets
)

def test_parse_lora_arg():
    """Test LoRA argument parsing."""
    print("[TEST] Testing parse_lora_arg...")
    
    # Test with strength
    name, strength = parse_lora_arg("test_lora.safetensors:0.8")
    assert name == "test_lora.safetensors", f"Expected 'test_lora.safetensors', got '{name}'"
    assert strength == 0.8, f"Expected 0.8, got {strength}"
    
    # Test without strength
    name, strength = parse_lora_arg("test_lora.safetensors")
    assert name == "test_lora.safetensors", f"Expected 'test_lora.safetensors', got '{name}'"
    assert strength == 1.0, f"Expected 1.0, got {strength}"
    
    # Test with invalid strength
    name, strength = parse_lora_arg("test_lora.safetensors:invalid")
    assert name == "test_lora.safetensors", f"Expected 'test_lora.safetensors', got '{name}'"
    assert strength == 1.0, f"Expected 1.0 (default), got {strength}"
    
    print("[OK] parse_lora_arg tests passed")

def test_find_checkpoint_loader():
    """Test finding CheckpointLoader node."""
    print("[TEST] Testing find_checkpoint_loader...")
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["1", 1]}
        }
    }
    
    node_id = find_checkpoint_loader(workflow)
    assert node_id == "1", f"Expected '1', got '{node_id}'"
    
    # Test with no checkpoint loader
    workflow_no_ckpt = {
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test"}
        }
    }
    
    node_id = find_checkpoint_loader(workflow_no_ckpt)
    assert node_id is None, f"Expected None, got '{node_id}'"
    
    print("[OK] find_checkpoint_loader tests passed")

def test_find_consumers():
    """Test finding consumer nodes."""
    print("[TEST] Testing find_consumers...")
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["1", 1]}
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "negative", "clip": ["1", 1]}
        },
        "4": {
            "class_type": "KSampler",
            "inputs": {"model": ["1", 0]}
        }
    }
    
    # Find clip consumers (output 1)
    clip_consumers = find_consumers(workflow, "1", 1)
    assert len(clip_consumers) == 2, f"Expected 2 CLIP consumers, got {len(clip_consumers)}"
    assert ("2", "clip") in clip_consumers, "Expected node 2 to consume CLIP"
    assert ("3", "clip") in clip_consumers, "Expected node 3 to consume CLIP"
    
    # Find model consumers (output 0)
    model_consumers = find_consumers(workflow, "1", 0)
    assert len(model_consumers) == 1, f"Expected 1 model consumer, got {len(model_consumers)}"
    assert ("4", "model") in model_consumers, "Expected node 4 to consume model"
    
    print("[OK] find_consumers tests passed")

def test_inject_single_lora():
    """Test injecting a single LoRA."""
    print("[TEST] Testing inject_single_lora...")
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["1", 1]}
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {"model": ["1", 0]}
        }
    }
    
    loras = [("test_lora.safetensors", 0.8)]
    modified = inject_loras(workflow.copy(), loras)
    
    # Check that a new node was added
    assert "4" in modified, "Expected new node '4' to be added"
    assert modified["4"]["class_type"] == "LoraLoader", "Expected LoraLoader node"
    assert modified["4"]["inputs"]["lora_name"] == "test_lora.safetensors"
    assert modified["4"]["inputs"]["strength_model"] == 0.8
    assert modified["4"]["inputs"]["strength_clip"] == 0.8
    
    # Check that connections were rewired
    assert modified["2"]["inputs"]["clip"] == ["4", 1], "CLIP should be rewired to LoRA output"
    assert modified["3"]["inputs"]["model"] == ["4", 0], "Model should be rewired to LoRA output"
    
    print("[OK] inject_single_lora tests passed")

def test_inject_multiple_loras():
    """Test injecting multiple chained LoRAs."""
    print("[TEST] Testing inject_multiple_loras...")
    
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "test.safetensors"}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "test", "clip": ["1", 1]}
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {"model": ["1", 0]}
        }
    }
    
    loras = [
        ("lora1.safetensors", 0.7),
        ("lora2.safetensors", 0.5)
    ]
    modified = inject_loras(workflow.copy(), loras)
    
    # Check that two new nodes were added
    assert "4" in modified, "Expected new node '4' to be added"
    assert "5" in modified, "Expected new node '5' to be added"
    
    # Check first LoRA connects to checkpoint
    assert modified["4"]["inputs"]["model"] == ["1", 0]
    assert modified["4"]["inputs"]["clip"] == ["1", 1]
    
    # Check second LoRA connects to first LoRA
    assert modified["5"]["inputs"]["model"] == ["4", 0]
    assert modified["5"]["inputs"]["clip"] == ["4", 1]
    
    # Check that final connections go to last LoRA
    assert modified["2"]["inputs"]["clip"] == ["5", 1], "CLIP should be rewired to last LoRA"
    assert modified["3"]["inputs"]["model"] == ["5", 0], "Model should be rewired to last LoRA"
    
    print("[OK] inject_multiple_loras tests passed")

def test_load_lora_presets():
    """Test loading LoRA presets."""
    print("[TEST] Testing load_lora_presets...")
    
    presets = load_lora_presets()
    
    # Check that presets were loaded
    assert "video-quality" in presets, "Expected 'video-quality' preset"
    assert "fast-generation" in presets, "Expected 'fast-generation' preset"
    
    # Check video-quality preset structure
    vq_preset = presets["video-quality"]
    assert len(vq_preset) >= 2, "video-quality should have at least 2 LoRAs"
    assert vq_preset[0]["name"] == "BoobPhysics_WAN_v6.safetensors"
    assert vq_preset[0]["strength"] == 0.7
    
    print("[OK] load_lora_presets tests passed")

def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running LoRA injection tests...")
    print("="*60 + "\n")
    
    try:
        test_parse_lora_arg()
        test_find_checkpoint_loader()
        test_find_consumers()
        test_inject_single_lora()
        test_inject_multiple_loras()
        test_load_lora_presets()
        
        print("\n" + "="*60)
        print("[OK] All tests passed!")
        print("="*60 + "\n")
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
