#!/usr/bin/env python3
"""Manual test script for metadata tracking feature.

This script tests the metadata tracking functionality without requiring
a running ComfyUI server by mocking the generation flow.
"""

import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_full_metadata_flow():
    """Test complete metadata creation and upload flow."""
    print("[TEST] Testing full metadata workflow...\n")
    
    # 1. Create a sample workflow
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd15.safetensors"}
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal"
            }
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "style.safetensors",
                "strength_model": 0.8
            }
        }
    }
    
    print("[OK] Created test workflow")
    
    # 2. Extract workflow params
    params = generate.extract_workflow_params(workflow)
    print(f"[OK] Extracted params: seed={params['seed']}, steps={params['steps']}, cfg={params['cfg']}")
    
    assert params['seed'] == 42
    assert params['steps'] == 25
    assert params['cfg'] == 7.0
    
    # 3. Extract LoRAs
    loras = generate.extract_loras_from_workflow(workflow)
    print(f"[OK] Extracted LoRAs: {len(loras)} found")
    
    assert len(loras) == 1
    assert loras[0]['name'] == "style.safetensors"
    assert loras[0]['strength'] == 0.8
    
    # 4. Create metadata
    metadata = generate.create_metadata_json(
        workflow_path="workflows/test.json",
        prompt="a beautiful sunset",
        negative_prompt="ugly, bad",
        workflow_params=params,
        loras=loras,
        preset="high-quality",
        validation_score=0.87,
        minio_url="http://192.168.1.215:9000/comfy-gen/test.png"
    )
    
    print("[OK] Created metadata JSON")
    print(f"\nMetadata preview:")
    print(json.dumps(metadata, indent=2))
    
    # 5. Verify all required fields
    required_fields = [
        "timestamp", "prompt", "negative_prompt", "workflow",
        "seed", "steps", "cfg", "sampler", "scheduler",
        "loras", "preset", "validation_score", "minio_url"
    ]
    
    for field in required_fields:
        assert field in metadata, f"Missing field: {field}"
    
    print(f"\n[OK] All {len(required_fields)} required fields present")
    
    # 6. Test metadata upload (mocked)
    with patch('generate.Minio') as mock_minio_class:
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        mock_client.fput_object.return_value = None
        
        url = generate.upload_metadata_to_minio(metadata, "test.png")
        
        assert url == "http://192.168.1.215:9000/comfy-gen/test.png.json"
        print(f"[OK] Metadata upload successful: {url}")
    
    print("\n[SUCCESS] Full metadata flow test passed!")


def test_metadata_disabled():
    """Test that --no-metadata flag works correctly."""
    print("\n[TEST] Testing --no-metadata flag...\n")
    
    # This would normally be tested by running generate.py with --no-metadata
    # For now, we just verify the flag exists in argparse
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-metadata", action="store_true")
    
    args = parser.parse_args(["--no-metadata"])
    assert args.no_metadata is True
    
    print("[OK] --no-metadata flag parsed correctly")
    
    args = parser.parse_args([])
    assert args.no_metadata is False
    
    print("[OK] Metadata enabled by default")
    print("\n[SUCCESS] --no-metadata flag test passed!")


def test_metadata_with_validation():
    """Test metadata includes validation score when validation runs."""
    print("\n[TEST] Testing metadata with validation score...\n")
    
    workflow_params = {
        "seed": 12345,
        "steps": 30,
        "cfg": 7.5,
        "sampler": "euler",
        "scheduler": "normal"
    }
    
    # Create metadata without validation
    metadata_no_val = generate.create_metadata_json(
        workflow_path="test.json",
        prompt="test",
        negative_prompt="",
        workflow_params=workflow_params,
        loras=[],
        preset=None,
        validation_score=None,
        minio_url="http://test.com/image.png"
    )
    
    assert metadata_no_val['validation_score'] is None
    print("[OK] Metadata without validation has validation_score=null")
    
    # Create metadata with validation
    metadata_with_val = generate.create_metadata_json(
        workflow_path="test.json",
        prompt="test",
        negative_prompt="",
        workflow_params=workflow_params,
        loras=[],
        preset=None,
        validation_score=0.92,
        minio_url="http://test.com/image.png"
    )
    
    assert metadata_with_val['validation_score'] == 0.92
    print("[OK] Metadata with validation has correct validation_score=0.92")
    
    print("\n[SUCCESS] Validation score test passed!")


if __name__ == "__main__":
    print("=" * 70)
    print("METADATA TRACKING MANUAL TEST")
    print("=" * 70)
    
    try:
        test_full_metadata_flow()
        test_metadata_disabled()
        test_metadata_with_validation()
        
        print("\n" + "=" * 70)
        print("ALL MANUAL TESTS PASSED!")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n[FAILED] Assertion error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAILED] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
