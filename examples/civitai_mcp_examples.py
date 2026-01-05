#!/usr/bin/env python3
"""Example usage of CivitAI MCP server tools.

This demonstrates common workflows for model discovery and verification.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.civitai_mcp import (
    civitai_search_models,
    civitai_get_model,
    civitai_lookup_hash,
    civitai_get_download_url
)


async def example_1_search_loras():
    """Example 1: Search for LoRAs by keyword and base model."""
    print("\n=== Example 1: Search for Realistic Portrait LoRAs ===\n")
    
    result = await civitai_search_models(
        query="realistic portrait",
        model_type="LORA",
        base_model="SD 1.5",
        sort="Most Downloaded",
        limit=5
    )
    
    if result['status'] == 'success':
        print(f"Found {result['count']} results:\n")
        for model in result['results']:
            print(f"  {model['name']}")
            print(f"    ID: {model['id']}")
            print(f"    Base: {model['base_model']}")
            print(f"    Downloads: {model['downloads']:,}")
            print(f"    Rating: {model['rating']:.1f}")
            print(f"    Preview: {model['preview_url']}")
            print()


async def example_2_verify_lora_compatibility():
    """Example 2: Verify LoRA compatibility using hash lookup."""
    print("\n=== Example 2: Verify LoRA Base Model ===\n")
    
    # In practice, get this from moira:
    # ssh moira "powershell -Command \"(Get-FileHash -Algorithm SHA256 'C:\\path\\to\\lora.safetensors').Hash\""
    
    # Example hash (fake - replace with real)
    example_hash = "A1B2C3D4E5F6789012345678901234567890123456789012345678901234ABCD"
    
    print(f"Looking up hash: {example_hash}\n")
    
    result = await civitai_lookup_hash(example_hash)
    
    if result['status'] == 'success':
        print(f"Model: {result['model_name']}")
        print(f"Base Model: {result['base_model']}")
        print(f"Version: {result['version_name']}")
        print(f"Trained Words: {', '.join(result['trained_words'])}")
        
        # Check compatibility
        base = result['base_model']
        if 'SD 1.5' in base or 'SD1.5' in base:
            print("\n[OK] Compatible with SD 1.5 image generation")
        elif 'Wan Video' in base or 'WAN' in base:
            print("\n[WARN] Video-only LoRA - DO NOT use for image generation")
        elif 'SDXL' in base:
            print("\n[OK] Compatible with SDXL image generation")
        else:
            print(f"\n[?] Unknown base model: {base}")
    else:
        print(f"Error: {result['error']}")
        if "Not found" in result['error']:
            print("This LoRA may be custom or not on CivitAI")


async def example_3_get_model_details():
    """Example 3: Get detailed information about a specific model."""
    print("\n=== Example 3: Get Model Details ===\n")
    
    # Example: Get details for a popular checkpoint
    model_id = 4384  # DreamShaper (example)
    
    result = await civitai_get_model(model_id)
    
    if result['status'] == 'success':
        model = result['model']
        print(f"Name: {model['name']}")
        print(f"Type: {model['type']}")
        print(f"Creator: {model['creator']['username']}")
        print(f"NSFW: {model.get('nsfw', False)}")
        print(f"\nStats:")
        print(f"  Downloads: {model['stats']['downloadCount']:,}")
        print(f"  Rating: {model['stats']['rating']:.2f}")
        print(f"  Favorites: {model['stats']['favoriteCount']:,}")
        print(f"\nVersions:")
        for version in model['modelVersions'][:3]:  # Show first 3
            print(f"  - {version['name']} (Base: {version['baseModel']})")
    else:
        print(f"Error: {result['error']}")


async def example_4_download_workflow():
    """Example 4: Complete workflow to find and download a model."""
    print("\n=== Example 4: Find and Get Download URL ===\n")
    
    # Step 1: Search for models
    print("Step 1: Search for 'anime style' checkpoints\n")
    search_result = await civitai_search_models(
        query="anime style",
        model_type="Checkpoint",
        base_model="SD 1.5",
        limit=3
    )
    
    if search_result['status'] == 'success' and search_result['results']:
        # Step 2: Pick first result
        chosen = search_result['results'][0]
        print(f"Chosen model: {chosen['name']}")
        print(f"  ID: {chosen['id']}")
        print(f"  Version ID: {chosen['version_id']}")
        print(f"  Downloads: {chosen['downloads']:,}\n")
        
        # Step 3: Get download URL
        print("Step 2: Get download URL\n")
        download_result = await civitai_get_download_url(
            chosen['id'],
            chosen['version_id']
        )
        
        if download_result['status'] == 'success':
            print(f"Download URL: {download_result['download_url']}")
            print(f"Requires Auth: {download_result['requires_auth']}")
            
            if download_result['requires_auth']:
                print("\n[INFO] Set CIVITAI_API_KEY environment variable to download")
            else:
                print("\n[OK] Ready to download")
                print("\nNext steps:")
                print(f"  1. SSH to moira")
                print(f"  2. wget '{download_result['download_url']}' -O filename.safetensors")
                print(f"  3. Move to C:\\Users\\jrjen\\comfy\\models\\checkpoints\\")
        else:
            print(f"Error getting download URL: {download_result['error']}")
    else:
        print("No results found or error occurred")


async def example_5_batch_verify_loras():
    """Example 5: Batch verify multiple LoRAs from moira."""
    print("\n=== Example 5: Batch LoRA Verification ===\n")
    
    # Example: List of LoRA files and their hashes
    # In practice, get these from moira via SSH
    loras_to_verify = [
        {
            "filename": "realistic_skin.safetensors",
            "hash": "HASH1_REPLACE_WITH_REAL_64_CHAR_HASH_FROM_MOIRA_000000000000000"
        },
        {
            "filename": "anime_style.safetensors", 
            "hash": "HASH2_REPLACE_WITH_REAL_64_CHAR_HASH_FROM_MOIRA_000000000000000"
        },
    ]
    
    print("Verifying LoRA compatibility...\n")
    
    compatible_sd15 = []
    compatible_wan = []
    unknown = []
    
    for lora in loras_to_verify:
        print(f"Checking: {lora['filename']}")
        
        result = await civitai_lookup_hash(lora['hash'])
        
        if result['status'] == 'success':
            base = result['base_model']
            print(f"  Base Model: {base}")
            
            if 'SD 1.5' in base:
                compatible_sd15.append(lora['filename'])
            elif 'Wan Video' in base:
                compatible_wan.append(lora['filename'])
            else:
                unknown.append(lora['filename'])
        else:
            print(f"  Error: {result['error']}")
            unknown.append(lora['filename'])
        
        print()
    
    # Summary
    print("\n--- Verification Summary ---")
    print(f"\nSD 1.5 Image LoRAs ({len(compatible_sd15)}):")
    for name in compatible_sd15:
        print(f"  - {name}")
    
    print(f"\nWan Video LoRAs ({len(compatible_wan)}):")
    for name in compatible_wan:
        print(f"  - {name}")
    
    print(f"\nUnknown/Error ({len(unknown)}):")
    for name in unknown:
        print(f"  - {name}")


async def main():
    """Run all examples."""
    print("=" * 70)
    print("CivitAI MCP Server - Usage Examples")
    print("=" * 70)
    
    # Check API key
    if os.getenv("CIVITAI_API_KEY"):
        print("\n[OK] CIVITAI_API_KEY is set")
    else:
        print("\n[WARN] CIVITAI_API_KEY not set - some features may be limited")
    
    print("\nNote: These examples require internet access to civitai.com")
    print("Run with: python3 examples/civitai_mcp_examples.py\n")
    
    # Run examples (comment out as needed)
    # await example_1_search_loras()
    # await example_2_verify_lora_compatibility()
    # await example_3_get_model_details()
    # await example_4_download_workflow()
    # await example_5_batch_verify_loras()
    
    print("\nExamples are commented out by default.")
    print("Uncomment the desired example in main() to run it.")


if __name__ == "__main__":
    asyncio.run(main())
