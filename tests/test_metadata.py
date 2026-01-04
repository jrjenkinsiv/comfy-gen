#!/usr/bin/env python3
"""Tests for metadata tracking functionality."""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_extract_workflow_params():
    """Test extracting parameters from workflow."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 12345,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal"
            }
        }
    }
    
    params = generate.extract_workflow_params(workflow)
    
    assert params["seed"] == 12345
    assert params["steps"] == 30
    assert params["cfg"] == 7.5
    assert params["sampler"] == "euler"
    assert params["scheduler"] == "normal"
    
    print("[OK] extract_workflow_params extracts KSampler parameters correctly")


def test_extract_workflow_params_no_ksampler():
    """Test extracting parameters when no KSampler exists."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        }
    }
    
    params = generate.extract_workflow_params(workflow)
    
    assert params["seed"] is None
    assert params["steps"] is None
    assert params["cfg"] is None
    assert params["sampler"] is None
    assert params["scheduler"] is None
    
    print("[OK] extract_workflow_params handles missing KSampler")


def test_extract_loras_from_workflow():
    """Test extracting LoRA information from workflow."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        },
        "10": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "style.safetensors",
                "strength_model": 0.8,
                "strength_clip": 0.8
            }
        },
        "11": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "detail.safetensors",
                "strength_model": 0.5
            }
        }
    }
    
    loras = generate.extract_loras_from_workflow(workflow)
    
    assert len(loras) == 2
    assert loras[0]["name"] == "style.safetensors"
    assert loras[0]["strength"] == 0.8
    assert loras[1]["name"] == "detail.safetensors"
    assert loras[1]["strength"] == 0.5
    
    print("[OK] extract_loras_from_workflow extracts LoRA information")


def test_extract_loras_from_workflow_no_loras():
    """Test extracting LoRAs when none exist."""
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"}
        }
    }
    
    loras = generate.extract_loras_from_workflow(workflow)
    
    assert len(loras) == 0
    
    print("[OK] extract_loras_from_workflow handles workflows without LoRAs")


def test_create_metadata_json():
    """Test creating metadata JSON structure."""
    workflow_params = {
        "seed": 12345,
        "steps": 30,
        "cfg": 7.5,
        "sampler": "euler",
        "scheduler": "normal"
    }
    
    loras = [
        {"name": "style.safetensors", "strength": 0.8}
    ]
    
    metadata = generate.create_metadata_json(
        workflow_path="/path/to/workflow.json",
        prompt="a beautiful landscape",
        negative_prompt="ugly, bad",
        workflow_params=workflow_params,
        loras=loras,
        preset="high-quality",
        validation_score=0.85,
        minio_url="http://192.168.1.215:9000/comfy-gen/image.png"
    )
    
    # Check all required fields
    assert "timestamp" in metadata
    assert metadata["prompt"] == "a beautiful landscape"
    assert metadata["negative_prompt"] == "ugly, bad"
    assert metadata["workflow"] == "workflow.json"
    assert metadata["seed"] == 12345
    assert metadata["steps"] == 30
    assert metadata["cfg"] == 7.5
    assert metadata["sampler"] == "euler"
    assert metadata["scheduler"] == "normal"
    assert metadata["loras"] == loras
    assert metadata["preset"] == "high-quality"
    assert metadata["validation_score"] == 0.85
    assert metadata["minio_url"] == "http://192.168.1.215:9000/comfy-gen/image.png"
    
    print("[OK] create_metadata_json creates complete metadata structure")


def test_create_metadata_json_minimal():
    """Test creating metadata with minimal parameters."""
    workflow_params = {
        "seed": 12345,
        "steps": 20,
        "cfg": 7.0,
        "sampler": None,
        "scheduler": None
    }
    
    metadata = generate.create_metadata_json(
        workflow_path="workflow.json",
        prompt="test",
        negative_prompt="",
        workflow_params=workflow_params,
        loras=[],
        preset=None,
        validation_score=None,
        minio_url=None
    )
    
    assert metadata["prompt"] == "test"
    assert metadata["negative_prompt"] == ""
    assert metadata["loras"] == []
    assert metadata["preset"] is None
    assert metadata["validation_score"] is None
    assert metadata["minio_url"] is None
    
    print("[OK] create_metadata_json handles minimal parameters")


def test_upload_metadata_to_minio():
    """Test uploading metadata to MinIO."""
    metadata = {
        "timestamp": "2024-01-01T12:00:00",
        "prompt": "test",
        "seed": 12345
    }
    
    # Mock MinIO client
    with patch('generate.Minio') as mock_minio_class:
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        mock_client.fput_object.return_value = None
        
        result = generate.upload_metadata_to_minio(metadata, "test.png")
        
        # Verify client was created with correct parameters
        mock_minio_class.assert_called_once_with(
            "192.168.1.215:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
        # Verify upload was called
        assert mock_client.fput_object.called
        call_args = mock_client.fput_object.call_args
        
        # Check bucket name and object name
        assert call_args[0][0] == "comfy-gen"
        assert call_args[0][1] == "test.png.json"
        
        # Check content type
        assert call_args[1]["content_type"] == "application/json"
        
        # Check return value
        assert result == "http://192.168.1.215:9000/comfy-gen/test.png.json"
    
    print("[OK] upload_metadata_to_minio uploads JSON with correct parameters")


if __name__ == "__main__":
    # Run all tests
    test_extract_workflow_params()
    test_extract_workflow_params_no_ksampler()
    test_extract_loras_from_workflow()
    test_extract_loras_from_workflow_no_loras()
    test_create_metadata_json()
    test_create_metadata_json_minimal()
    test_upload_metadata_to_minio()
    
    print("\n[OK] All metadata tests passed!")
