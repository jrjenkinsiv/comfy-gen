#!/usr/bin/env python3
"""Test HuggingFace Hub client functionality."""

import sys
from pathlib import Path
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.huggingface_client import HuggingFaceClient


def test_huggingface_client_initialization():
    """Test HuggingFaceClient initialization."""
    print("\n[TEST] HuggingFaceClient initialization")
    print("=" * 60)
    
    # Create client without token
    client = HuggingFaceClient()
    assert client.api is not None
    print("[OK] Client initialized successfully")
    
    # Create client with mock token
    client_with_token = HuggingFaceClient(token="hf_test_token")
    assert client_with_token.token == "hf_test_token"
    print("[OK] Client initialized with token")
    
    print("[OK] HuggingFaceClient initialization test passed")


def test_search_models():
    """Test searching for models on HuggingFace Hub."""
    print("\n[TEST] Search models")
    print("=" * 60)
    
    client = HuggingFaceClient()
    
    # Search for diffusers models
    results = client.search_models(
        query="flux",
        library="diffusers",
        limit=5
    )
    
    print(f"[OK] Found {len(results)} models")
    
    if results:
        # Check result structure
        first_result = results[0]
        assert "id" in first_result
        assert "name" in first_result
        assert "author" in first_result
        assert "downloads" in first_result
        assert "tags" in first_result
        
        print(f"[OK] First result: {first_result['id']}")
        print(f"     Author: {first_result['author']}")
        print(f"     Downloads: {first_result['downloads']}")
        print(f"     Tags: {first_result['tags'][:3]}...")
    
    print("[OK] Search models test passed")


def test_get_model_info():
    """Test getting model information."""
    print("\n[TEST] Get model info")
    print("=" * 60)
    
    client = HuggingFaceClient()
    
    # Use a well-known public model
    model_id = "stabilityai/stable-diffusion-2-1"
    info = client.get_model_info(model_id)
    
    if info and "error" not in info:
        assert "id" in info
        assert "author" in info
        assert "tags" in info
        assert info["id"] == model_id
        
        print(f"[OK] Model ID: {info['id']}")
        print(f"[OK] Author: {info['author']}")
        print(f"[OK] Downloads: {info.get('downloads', 0)}")
        print(f"[OK] Likes: {info.get('likes', 0)}")
        print(f"[OK] Tags: {info.get('tags', [])[:5]}")
        print("[OK] Get model info test passed")
    else:
        print("[WARN] Model info not available or requires auth")
        print(f"[WARN] Response: {info}")


def test_get_model_files():
    """Test listing files in a model repository."""
    print("\n[TEST] Get model files")
    print("=" * 60)
    
    client = HuggingFaceClient()
    
    # Use a well-known public model
    model_id = "stabilityai/stable-diffusion-2-1"
    files = client.get_model_files(model_id)
    
    print(f"[OK] Found {len(files)} files")
    
    if files:
        # Check file structure
        first_file = files[0]
        assert "filename" in first_file
        
        print(f"[OK] First file: {first_file['filename']}")
        print(f"     Size: {first_file.get('size', 'N/A')}")
        
        # Look for common model files
        filenames = [f["filename"] for f in files]
        print(f"[OK] Files: {filenames[:5]}...")
    
    print("[OK] Get model files test passed")


def test_search_with_filters():
    """Test searching with various filters."""
    print("\n[TEST] Search with filters")
    print("=" * 60)
    
    client = HuggingFaceClient()
    
    # Search for text-to-image models
    results = client.search_models(
        library="diffusers",
        pipeline_tag="text-to-image",
        sort="downloads",
        limit=3
    )
    
    print(f"[OK] Found {len(results)} text-to-image models")
    
    if results:
        for i, model in enumerate(results, 1):
            print(f"  {i}. {model['id']}")
            print(f"     Pipeline: {model.get('pipeline_tag', 'N/A')}")
            print(f"     Library: {model.get('library_name', 'N/A')}")
    
    print("[OK] Search with filters test passed")


def test_error_handling():
    """Test error handling for invalid requests."""
    print("\n[TEST] Error handling")
    print("=" * 60)
    
    client = HuggingFaceClient()
    
    # Try to get info for non-existent model
    info = client.get_model_info("this-model-definitely-does-not-exist-12345")
    assert info is None or "error" in info
    print("[OK] Non-existent model handled correctly")
    
    # Try to list files for non-existent model
    files = client.get_model_files("this-model-definitely-does-not-exist-12345")
    assert files == []
    print("[OK] Non-existent model files handled correctly")
    
    print("[OK] Error handling test passed")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("HuggingFace Client Test Suite")
    print("=" * 60)
    
    try:
        test_huggingface_client_initialization()
        test_search_models()
        test_get_model_info()
        test_get_model_files()
        test_search_with_filters()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("[OK] All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
