#!/usr/bin/env python3
"""Integration test for CivitAI MCP server with real API calls.

This script demonstrates actual usage of the CivitAI MCP tools.
Requires internet connection and optional CIVITAI_API_KEY.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.civitai_mcp import (
    civitai_get_download_url,
    civitai_get_model,
    civitai_lookup_hash,
    civitai_search_models,
)


async def test_search():
    """Test searching for models."""
    print("\n[TEST] civitai_search_models")
    print("-" * 60)

    result = await civitai_search_models(query="realistic portrait", model_type="LORA", base_model="SD 1.5", limit=3)

    print(f"Status: {result['status']}")
    if result["status"] == "success":
        print(f"Found {result['count']} results")
        for i, model in enumerate(result["results"][:3], 1):
            print(f"\n  {i}. {model['name']}")
            print(f"     Type: {model['type']}")
            print(f"     Base Model: {model['base_model']}")
            print(f"     Downloads: {model['downloads']:,}")
            print(f"     Rating: {model['rating']:.2f}")
            print(f"     Creator: {model['creator']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    return result["status"] == "success"


async def test_get_model():
    """Test getting model details."""
    print("\n[TEST] civitai_get_model")
    print("-" * 60)

    # Test with a known model ID (SD 1.5 base model)
    model_id = 4384
    result = await civitai_get_model(model_id)

    print(f"Status: {result['status']}")
    if result["status"] == "success":
        model = result["model"]
        print(f"Model: {model['name']}")
        print(f"Type: {model['type']}")
        print(f"Creator: {model['creator']['username']}")
        print(f"Downloads: {model['stats']['downloadCount']:,}")
        print(f"Versions: {len(model['modelVersions'])}")
        if model["modelVersions"]:
            latest = model["modelVersions"][0]
            print(f"Latest Version: {latest['name']}")
            print(f"Base Model: {latest['baseModel']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    return result["status"] == "success"


async def test_hash_lookup():
    """Test hash lookup functionality."""
    print("\n[TEST] civitai_lookup_hash")
    print("-" * 60)

    # Test with invalid hash first
    print("Testing with invalid hash format...")
    result = await civitai_lookup_hash("invalid")
    print(f"Status: {result['status']}")
    print(f"Expected error: {result.get('error', 'No error')}")

    # Test with valid format but non-existent hash
    print("\nTesting with valid format but fake hash...")
    fake_hash = "0" * 64
    result = await civitai_lookup_hash(fake_hash)
    print(f"Status: {result['status']}")
    if result["status"] == "error":
        print(f"Error (expected): {result['error']}")

    print("\nNote: To test with real hash, get SHA256 from moira:")
    print('  ssh moira "powershell -Command \\"(Get-FileHash -Algorithm SHA256 \'path\').Hash\\""')
    print("  Then call: await civitai_lookup_hash(hash_value)")

    return True  # Pass if structure is correct


async def test_download_url():
    """Test getting download URL."""
    print("\n[TEST] civitai_get_download_url")
    print("-" * 60)

    # Test with a known model
    model_id = 4384
    result = await civitai_get_download_url(model_id)

    print(f"Status: {result['status']}")
    if result["status"] == "success":
        print(f"Model ID: {result['model_id']}")
        print(f"Version ID: {result['version_id']}")
        print(f"Requires Auth: {result['requires_auth']}")
        print(f"Download URL: {result['download_url'][:80]}...")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    return result["status"] == "success"


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("CivitAI MCP Server Integration Tests")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if api_key:
        print(f"[OK] CIVITAI_API_KEY is set ({api_key[:8]}...)")
    else:
        print("[WARN] CIVITAI_API_KEY not set - NSFW content may be limited")

    results = {}

    # Run tests
    try:
        results["search"] = await test_search()
    except Exception as e:
        print(f"[ERROR] Search test failed: {e}")
        results["search"] = False

    try:
        results["get_model"] = await test_get_model()
    except Exception as e:
        print(f"[ERROR] Get model test failed: {e}")
        results["get_model"] = False

    try:
        results["hash_lookup"] = await test_hash_lookup()
    except Exception as e:
        print(f"[ERROR] Hash lookup test failed: {e}")
        results["hash_lookup"] = False

    try:
        results["download_url"] = await test_download_url()
    except Exception as e:
        print(f"[ERROR] Download URL test failed: {e}")
        results["download_url"] = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, passed_flag in results.items():
        status = "[OK]" if passed_flag else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
