#!/usr/bin/env python3
"""Test HuggingFace MCP tools integration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.tools import models


async def test_hf_search_models():
    """Test hf_search_models MCP tool."""
    print("\n[TEST] hf_search_models MCP tool")
    print("=" * 60)
    
    result = await models.hf_search_models(
        query="stable diffusion",
        library="diffusers",
        limit=3
    )
    
    assert result["status"] == "success"
    assert "results" in result
    assert "count" in result
    assert result["count"] <= 3
    
    print(f"[OK] Status: {result['status']}")
    print(f"[OK] Count: {result['count']}")
    
    if result["results"]:
        print(f"[OK] First model: {result['results'][0]['id']}")
    
    print("[OK] hf_search_models test passed")


async def test_hf_get_model_info():
    """Test hf_get_model_info MCP tool."""
    print("\n[TEST] hf_get_model_info MCP tool")
    print("=" * 60)
    
    result = await models.hf_get_model_info("stabilityai/stable-diffusion-2-1")
    
    # Result can be success or error (if model requires auth)
    assert "status" in result
    
    if result["status"] == "success":
        assert "model" in result
        model = result["model"]
        assert "id" in model
        assert "author" in model
        print(f"[OK] Model ID: {model['id']}")
        print(f"[OK] Author: {model['author']}")
        print("[OK] hf_get_model_info test passed")
    else:
        print(f"[WARN] Model info not available: {result.get('error', 'Unknown')}")
        print("[OK] Error handled correctly")


async def test_hf_list_files():
    """Test hf_list_files MCP tool."""
    print("\n[TEST] hf_list_files MCP tool")
    print("=" * 60)
    
    result = await models.hf_list_files("stabilityai/stable-diffusion-2-1")
    
    assert "status" in result
    
    if result["status"] == "success":
        assert "files" in result
        assert "count" in result
        print(f"[OK] File count: {result['count']}")
        
        if result["files"]:
            print(f"[OK] First file: {result['files'][0]['filename']}")
        
        print("[OK] hf_list_files test passed")
    else:
        print(f"[WARN] Files not available: {result.get('error', 'Unknown')}")
        print("[OK] Error handled correctly")


async def test_hf_search_with_filters():
    """Test hf_search_models with various filters."""
    print("\n[TEST] hf_search_models with filters")
    print("=" * 60)
    
    # Search for text-to-image models
    result = await models.hf_search_models(
        library="diffusers",
        pipeline_tag="text-to-image",
        tags=["sdxl"],
        sort="downloads",
        limit=5
    )
    
    assert result["status"] == "success"
    print(f"[OK] Found {result['count']} SDXL text-to-image models")
    
    # Search with query
    result2 = await models.hf_search_models(
        query="flux",
        limit=3
    )
    
    assert result2["status"] == "success"
    print(f"[OK] Found {result2['count']} models matching 'flux'")
    
    print("[OK] Filter tests passed")


async def test_error_handling():
    """Test error handling in MCP tools."""
    print("\n[TEST] Error handling")
    print("=" * 60)
    
    # Try non-existent model
    result = await models.hf_get_model_info("this-model-does-not-exist-12345")
    assert result["status"] == "error"
    assert "error" in result
    print("[OK] Non-existent model error handled correctly")
    
    # Try empty files list
    result = await models.hf_list_files("this-model-does-not-exist-12345")
    # Can be either empty success or error
    assert "status" in result
    print("[OK] Non-existent model files handled correctly")
    
    print("[OK] Error handling test passed")


async def test_all_hf_tools():
    """Run all HuggingFace MCP tool tests."""
    print("\n" + "=" * 60)
    print("HuggingFace MCP Tools Test Suite")
    print("=" * 60)
    
    try:
        await test_hf_search_models()
        await test_hf_get_model_info()
        await test_hf_list_files()
        await test_hf_search_with_filters()
        await test_error_handling()
        
        print("\n" + "=" * 60)
        print("[OK] All MCP tool tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_all_hf_tools())
    sys.exit(exit_code)
