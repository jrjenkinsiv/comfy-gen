#!/usr/bin/env python3
"""Example: Using MCP generate_image with CLIP validation.

This example demonstrates the new validation features available in MCP:
- CLIP-based validation to check if generated images match the prompt
- Automatic retry if validation fails
- Configurable validation thresholds

Usage:
    python3 examples/mcp_validation_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfygen.tools import generation


async def example_with_validation():
    """Example: Generate image with validation enabled (default)."""
    print("=" * 60)
    print("Example 1: Generate with Validation (Default)")
    print("=" * 60)

    result = await generation.generate_image(
        prompt="single red car on a country road",
        negative_prompt="multiple cars, duplicate, blurry",
        width=512,
        height=512,
        steps=20,
        # Validation is enabled by default
        # validate=True,
        # auto_retry=True,
        # retry_limit=3,
        # positive_threshold=0.25
    )

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"URL: {result['url']}")
        print(f"Attempt: {result.get('attempt', 1)}")
        if 'validation' in result:
            print("\nValidation:")
            print(f"  Passed: {result['validation'].get('passed')}")
            print(f"  Positive Score: {result['validation'].get('positive_score', 'N/A')}")
            print(f"  Reason: {result['validation'].get('reason', 'N/A')}")
    else:
        print(f"Error: {result.get('error')}")

    return result


async def example_without_validation():
    """Example: Generate image without validation."""
    print("\n" + "=" * 60)
    print("Example 2: Generate without Validation")
    print("=" * 60)

    result = await generation.generate_image(
        prompt="landscape with mountains",
        negative_prompt="blurry, low quality",
        width=512,
        height=512,
        steps=20,
        validate=False  # Disable validation
    )

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"URL: {result['url']}")
        print("Validation: Disabled")
    else:
        print(f"Error: {result.get('error')}")

    return result


async def example_custom_validation():
    """Example: Generate with custom validation settings."""
    print("\n" + "=" * 60)
    print("Example 3: Custom Validation Settings")
    print("=" * 60)

    result = await generation.generate_image(
        prompt="single cat sitting on a windowsill",
        negative_prompt="multiple cats, duplicate, blurry",
        width=512,
        height=512,
        steps=20,
        validate=True,
        auto_retry=True,
        retry_limit=5,  # More retries
        positive_threshold=0.30  # Higher threshold for stricter validation
    )

    print(f"\nStatus: {result['status']}")
    if result['status'] == 'success':
        print(f"URL: {result['url']}")
        print(f"Attempt: {result.get('attempt', 1)}")
        if 'validation' in result:
            print("\nValidation:")
            print(f"  Passed: {result['validation'].get('passed')}")
            print(f"  Positive Score: {result['validation'].get('positive_score', 'N/A'):.3f}")
            print("  Threshold: 0.30")
            print(f"  Reason: {result['validation'].get('reason', 'N/A')}")
    else:
        print(f"Error: {result.get('error')}")

    return result


async def main():
    """Run all examples."""
    print("\nMCP CLIP Validation Examples")
    print("=" * 60)
    print("\nNote: These examples require a running ComfyUI server.")
    print("If the server is not available, you'll see error messages.")
    print("=" * 60)

    # Example 1: Default validation
    try:
        await example_with_validation()
    except Exception as e:
        print(f"Example 1 failed: {e}")

    # Example 2: No validation
    try:
        await example_without_validation()
    except Exception as e:
        print(f"Example 2 failed: {e}")

    # Example 3: Custom validation
    try:
        await example_custom_validation()
    except Exception as e:
        print(f"Example 3 failed: {e}")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
