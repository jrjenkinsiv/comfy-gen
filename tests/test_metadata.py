#!/usr/bin/env python3
"""Tests for metadata tracking functionality."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path to import generate
sys.path.insert(0, str(Path(__file__).parent.parent))

import generate


def test_extract_workflow_params():
    """Test extracting parameters from workflow."""
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
        "5": {
            "class_type": "KSampler",
            "inputs": {"seed": 12345, "steps": 30, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal"},
        },
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
    workflow = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}}}

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
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
        "10": {
            "class_type": "LoraLoader",
            "inputs": {"lora_name": "style.safetensors", "strength_model": 0.8, "strength_clip": 0.8},
        },
        "11": {"class_type": "LoraLoader", "inputs": {"lora_name": "detail.safetensors", "strength_model": 0.5}},
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
    workflow = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}}}

    loras = generate.extract_loras_from_workflow(workflow)

    assert len(loras) == 0

    print("[OK] extract_loras_from_workflow handles workflows without LoRAs")


def test_extract_model_from_workflow():
    """Test extracting model name from workflow."""
    # Test CheckpointLoaderSimple
    workflow = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}}}

    model = generate.extract_model_from_workflow(workflow)
    assert model == "flux1-dev-fp8.safetensors"

    # Test UNETLoader
    workflow2 = {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan22-diffusion.safetensors"}}}

    model2 = generate.extract_model_from_workflow(workflow2)
    assert model2 == "wan22-diffusion.safetensors"

    # Test no model loader
    workflow3 = {"1": {"class_type": "KSampler", "inputs": {"steps": 30}}}

    model3 = generate.extract_model_from_workflow(workflow3)
    assert model3 is None

    print("[OK] extract_model_from_workflow extracts model names correctly")


def test_extract_vae_from_workflow():
    """Test extracting VAE name from workflow."""
    # Test with VAE
    workflow = {"1": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}}}

    vae = generate.extract_vae_from_workflow(workflow)
    assert vae == "ae.safetensors"

    # Test without VAE
    workflow2 = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}}}

    vae2 = generate.extract_vae_from_workflow(workflow2)
    assert vae2 is None

    print("[OK] extract_vae_from_workflow extracts VAE names correctly")


def test_extract_resolution_from_workflow():
    """Test extracting resolution from workflow."""
    # Test with EmptyLatentImage
    workflow = {"1": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 768, "batch_size": 1}}}

    resolution = generate.extract_resolution_from_workflow(workflow)
    assert resolution == [1024, 768]

    # Test without EmptyLatentImage
    workflow2 = {"1": {"class_type": "KSampler", "inputs": {"steps": 30}}}

    resolution2 = generate.extract_resolution_from_workflow(workflow2)
    assert resolution2 is None

    print("[OK] extract_resolution_from_workflow extracts resolution correctly")


def test_create_metadata_json():
    """Test creating metadata JSON structure."""
    workflow_params = {"seed": 12345, "steps": 30, "cfg": 7.5, "sampler": "euler", "scheduler": "normal"}

    loras = [{"name": "style.safetensors", "strength": 0.8}]

    # Create a mock workflow for extraction
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "3": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 768}},
    }

    # Create temporary output file for file size test
    with tempfile.NamedTemporaryFile(mode="w", suffix=".png", delete=False) as f:
        f.write("fake image content")
        temp_path = f.name

    try:
        metadata = generate.create_metadata_json(
            workflow_path="/path/to/workflow.json",
            prompt="a beautiful landscape",
            negative_prompt="ugly, bad",
            workflow_params=workflow_params,
            loras=loras,
            preset="high-quality",
            validation_score=0.85,
            minio_url="http://192.168.1.215:9000/comfy-gen/image.png",
            workflow=workflow,
            output_path=temp_path,
            generation_time_seconds=45.2,
        )

        # Check top-level fields
        assert "timestamp" in metadata
        assert "generation_id" in metadata

        # Check input section
        assert metadata["input"]["prompt"] == "a beautiful landscape"
        assert metadata["input"]["negative_prompt"] == "ugly, bad"
        assert metadata["input"]["preset"] == "high-quality"

        # Check workflow section
        assert metadata["workflow"]["name"] == "workflow.json"
        assert metadata["workflow"]["model"] == "flux1-dev-fp8.safetensors"
        assert metadata["workflow"]["vae"] == "ae.safetensors"

        # Check parameters section
        assert metadata["parameters"]["seed"] == 12345
        assert metadata["parameters"]["steps"] == 30
        assert metadata["parameters"]["cfg"] == 7.5
        assert metadata["parameters"]["sampler"] == "euler"
        assert metadata["parameters"]["scheduler"] == "normal"
        assert metadata["parameters"]["resolution"] == [1024, 768]
        assert metadata["parameters"]["loras"] == loras

        # Check quality section
        assert metadata["quality"]["prompt_adherence"]["clip"] == 0.85

        # Check storage section
        assert metadata["storage"]["minio_url"] == "http://192.168.1.215:9000/comfy-gen/image.png"
        assert metadata["storage"]["file_size_bytes"] > 0
        assert metadata["storage"]["format"] == "png"
        assert metadata["storage"]["generation_time_seconds"] == 45.2

        print("[OK] create_metadata_json creates complete nested metadata structure")
    finally:
        # Clean up temp file
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink()


def test_create_metadata_json_minimal():
    """Test creating metadata with minimal parameters."""
    workflow_params = {"seed": 12345, "steps": 20, "cfg": 7.0, "sampler": None, "scheduler": None}

    metadata = generate.create_metadata_json(
        workflow_path="workflow.json",
        prompt="test",
        negative_prompt="",
        workflow_params=workflow_params,
        loras=[],
        preset=None,
        validation_score=None,
        minio_url=None,
    )

    # Check nested structure exists
    assert "input" in metadata
    assert "workflow" in metadata
    assert "parameters" in metadata
    assert "quality" in metadata
    assert "storage" in metadata

    # Check input section
    assert metadata["input"]["prompt"] == "test"
    assert metadata["input"]["negative_prompt"] == ""
    assert metadata["input"]["preset"] is None

    # Check parameters
    assert metadata["parameters"]["loras"] == []
    assert metadata["parameters"]["sampler"] is None
    assert metadata["parameters"]["scheduler"] is None

    # Check quality section
    assert metadata["quality"]["prompt_adherence"] is None

    # Check storage
    assert metadata["storage"]["minio_url"] is None

    print("[OK] create_metadata_json handles minimal parameters with nested structure")


def test_upload_metadata_to_minio():
    """Test uploading metadata to MinIO."""
    metadata = {"timestamp": "2024-01-01T12:00:00", "prompt": "test", "seed": 12345}

    # Mock MinIO client
    with patch("generate.Minio") as mock_minio_class:
        mock_client = Mock()
        mock_minio_class.return_value = mock_client
        mock_client.fput_object.return_value = None

        result = generate.upload_metadata_to_minio(metadata, "test.png")

        # Verify client was created with correct parameters
        mock_minio_class.assert_called_once_with(
            "192.168.1.215:9000", access_key="minioadmin", secret_key="minioadmin", secure=False
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
    test_extract_model_from_workflow()
    test_extract_vae_from_workflow()
    test_extract_resolution_from_workflow()
    test_create_metadata_json()
    test_create_metadata_json_minimal()
    test_upload_metadata_to_minio()

    print("\n[OK] All metadata tests passed!")
