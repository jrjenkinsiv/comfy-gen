#!/usr/bin/env python3
"""Tests for PNG metadata embedding functionality."""

import sys
import json
import tempfile
from pathlib import Path
from PIL import Image

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfy_gen.metadata import (
    embed_metadata_in_png,
    read_metadata_from_png,
    format_civitai_parameters,
    format_metadata_for_display
)


def create_test_png(path):
    """Create a simple test PNG file."""
    img = Image.new('RGB', (100, 100), color='red')
    img.save(path, 'PNG')
    return path


def test_embed_and_read_metadata():
    """Test embedding and reading metadata from PNG."""
    # Create test metadata
    metadata = {
        "timestamp": "2026-01-05T10:00:00",
        "generation_id": "test-123",
        "input": {
            "prompt": "a beautiful sunset",
            "negative_prompt": "ugly, blurry",
            "preset": "high-quality"
        },
        "workflow": {
            "name": "flux-dev.json",
            "model": "flux1-dev-fp8.safetensors",
            "vae": "ae.safetensors"
        },
        "parameters": {
            "seed": 42,
            "steps": 30,
            "cfg": 7.5,
            "sampler": "euler",
            "scheduler": "normal",
            "resolution": [1024, 768],
            "loras": [
                {"name": "style.safetensors", "strength": 0.8}
            ]
        },
        "quality": {
            "composite_score": 7.5,
            "grade": "B"
        },
        "storage": {
            "minio_url": "http://192.168.1.215:9000/comfy-gen/test.png",
            "file_size_bytes": 1024000,
            "format": "png",
            "generation_time_seconds": 45.2
        }
    }
    
    # Create temporary PNG
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    
    try:
        create_test_png(temp_path)
        
        # Embed metadata
        success = embed_metadata_in_png(temp_path, metadata)
        assert success, "Failed to embed metadata"
        
        # Read metadata back
        read_meta = read_metadata_from_png(temp_path)
        
        assert read_meta is not None, "Failed to read metadata"
        assert read_meta["generation_id"] == "test-123"
        assert read_meta["input"]["prompt"] == "a beautiful sunset"
        assert read_meta["parameters"]["seed"] == 42
        assert read_meta["parameters"]["steps"] == 30
        assert read_meta["workflow"]["model"] == "flux1-dev-fp8.safetensors"
        
        print("[OK] embed_and_read_metadata test passed")
        
    finally:
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def test_civitai_format():
    """Test CivitAI parameter formatting."""
    metadata = {
        "input": {
            "prompt": "a beautiful landscape",
            "negative_prompt": "ugly, bad quality"
        },
        "workflow": {
            "model": "flux1-dev-fp8.safetensors",
            "vae": "ae.safetensors"
        },
        "parameters": {
            "seed": 12345,
            "steps": 30,
            "cfg": 7.5,
            "sampler": "euler",
            "resolution": [1024, 768],
            "loras": [
                {"name": "style.safetensors", "strength": 0.8}
            ]
        }
    }
    
    params = format_civitai_parameters(metadata)
    
    # Check that key fields are present
    assert "a beautiful landscape" in params
    assert "Negative prompt: ugly, bad quality" in params
    assert "Steps: 30" in params
    assert "Sampler: euler" in params
    assert "CFG scale: 7.5" in params
    assert "Seed: 12345" in params
    assert "Size: 1024x768" in params
    assert "Model: flux1-dev-fp8.safetensors" in params
    assert "Lora: style.safetensors:0.8" in params
    
    print("[OK] civitai_format test passed")


def test_read_individual_fields():
    """Test reading metadata from individual PNG text chunks."""
    # Create PNG with only individual fields (no full metadata)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    
    try:
        from PIL.PngImagePlugin import PngInfo
        
        img = Image.new('RGB', (100, 100), color='blue')
        png_info = PngInfo()
        
        # Add individual fields (no comfygen_metadata)
        png_info.add_text("prompt", "test prompt")
        png_info.add_text("negative_prompt", "test negative")
        png_info.add_text("model", "test-model.safetensors")
        png_info.add_text("seed", "12345")
        png_info.add_text("steps", "30")
        png_info.add_text("cfg", "7.5")
        png_info.add_text("sampler", "euler")
        
        img.save(temp_path, "PNG", pnginfo=png_info)
        
        # Read metadata
        metadata = read_metadata_from_png(temp_path)
        
        assert metadata is not None
        assert metadata["input"]["prompt"] == "test prompt"
        assert metadata["input"]["negative_prompt"] == "test negative"
        assert metadata["workflow"]["model"] == "test-model.safetensors"
        assert metadata["parameters"]["seed"] == 12345
        assert metadata["parameters"]["steps"] == 30
        assert metadata["parameters"]["cfg"] == 7.5
        assert metadata["parameters"]["sampler"] == "euler"
        
        print("[OK] read_individual_fields test passed")
        
    finally:
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def test_format_for_display():
    """Test human-readable metadata formatting."""
    metadata = {
        "timestamp": "2026-01-05T10:00:00",
        "generation_id": "test-123",
        "input": {
            "prompt": "a sunset",
            "negative_prompt": "ugly",
            "preset": "draft"
        },
        "workflow": {
            "name": "flux-dev.json",
            "model": "flux1-dev-fp8.safetensors"
        },
        "parameters": {
            "seed": 42,
            "steps": 20,
            "cfg": 7.0,
            "resolution": [512, 512],
            "loras": []
        },
        "storage": {
            "file_size_bytes": 1048576,
            "generation_time_seconds": 30.5
        }
    }
    
    display = format_metadata_for_display(metadata)
    
    assert "Generation Metadata" in display
    assert "test-123" in display
    assert "a sunset" in display
    assert "Seed: 42" in display
    assert "Steps: 20" in display
    assert "Resolution: 512x512" in display
    assert "1.00 MB" in display
    assert "30.5s" in display
    
    print("[OK] format_for_display test passed")


def test_non_png_file():
    """Test that non-PNG files return None."""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        temp_path = f.name
    
    try:
        # Create a JPEG using PIL
        img = Image.new('RGB', (100, 100), color='green')
        img.save(temp_path, 'JPEG')
        
        metadata = read_metadata_from_png(temp_path)
        assert metadata is None, "Should return None for non-PNG files"
        
        print("[OK] non_png_file test passed")
        
    finally:
        if Path(temp_path).exists():
            Path(temp_path).unlink()


def test_embed_preserves_image():
    """Test that embedding metadata doesn't corrupt the image."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    
    try:
        # Create test image
        original = Image.new('RGB', (200, 150), color='purple')
        original.save(temp_path, 'PNG')
        
        # Get original size
        original_size = original.size
        
        # Embed metadata
        metadata = {
            "input": {"prompt": "test"},
            "parameters": {"seed": 123}
        }
        
        embed_metadata_in_png(temp_path, metadata)
        
        # Reload image and check it's still valid
        reloaded = Image.open(temp_path)
        assert reloaded.size == original_size
        assert reloaded.mode == original.mode
        
        print("[OK] embed_preserves_image test passed")
        
    finally:
        if Path(temp_path).exists():
            Path(temp_path).unlink()


if __name__ == "__main__":
    # Run all tests
    test_embed_and_read_metadata()
    test_civitai_format()
    test_read_individual_fields()
    test_format_for_display()
    test_non_png_file()
    test_embed_preserves_image()
    
    print("\n[OK] All metadata embedding tests passed!")
