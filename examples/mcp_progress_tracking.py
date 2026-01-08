#!/usr/bin/env python3
"""Example: MCP Progress Tracking and Local File Output

Demonstrates the new progress tracking and local file output features in the MCP server.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def example_json_progress():
    """Example: Generation with JSON progress updates."""
    print("\n" + "=" * 60)
    print("Example: JSON Progress Tracking")
    print("=" * 60)

    from clients.tools import generation

    # Generate with JSON progress enabled
    # Note: When json_progress=True, progress updates are collected in result['progress_updates']
    # If you also provide progress_callback, updates are sent to both
    result = await generation.generate_image(
        prompt="a sunset over mountains, cinematic lighting, highly detailed",
        negative_prompt="blurry, low quality, watermark",
        model="sd15",
        width=512,
        height=512,
        steps=20,
        json_progress=True,  # Enable structured progress collection
        # progress_callback can be omitted when using json_progress
        # or provided to get real-time updates in addition to collection
    )

    print(f"\nGeneration Status: {result['status']}")
    print(f"MinIO URL: {result.get('url', 'N/A')}")

    # Display progress summary if available
    if "progress_updates" in result:
        print(f"\nTotal Progress Updates: {len(result['progress_updates'])}")

        # Show sampling progress
        progress_updates = [u for u in result["progress_updates"] if u["type"] == "progress"]
        if progress_updates:
            print("\nSampling Progress:")
            for update in progress_updates[:5]:  # Show first 5
                print(f"  Step {update['step']}/{update['max_steps']} ({update['percent']}%)")
            if len(progress_updates) > 5:
                print(f"  ... and {len(progress_updates) - 5} more updates")


async def example_local_file_output():
    """Example: Save generated image to local file."""
    print("\n" + "=" * 60)
    print("Example: Local File Output")
    print("=" * 60)

    import tempfile

    from clients.tools import generation

    # Create temporary output path
    output_path = Path(tempfile.gettempdir()) / "comfygen_example.png"

    result = await generation.generate_image(
        prompt="a cat sitting on a windowsill, morning light",
        negative_prompt="blurry, low quality",
        model="sd15",
        width=512,
        height=512,
        output_path=str(output_path),  # Save to local file
        validate=False,  # Skip validation for example
    )

    print(f"\nGeneration Status: {result['status']}")
    print(f"MinIO URL: {result.get('url', 'N/A')}")
    print(f"Local File: {result.get('local_path', 'N/A')}")

    if result.get("local_path"):
        local_file = Path(result["local_path"])
        if local_file.exists():
            print(f"✓ File saved successfully ({local_file.stat().st_size} bytes)")
        else:
            print("✗ Local file not found")


async def example_workflow_validation():
    """Example: Validate workflow before generation (dry run)."""
    print("\n" + "=" * 60)
    print("Example: Workflow Validation (Dry Run)")
    print("=" * 60)

    import os

    from clients.comfyui_client import ComfyUIClient
    from clients.workflows import WorkflowManager

    # Get clients
    comfyui = ComfyUIClient(host=os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188"))
    workflow_mgr = WorkflowManager()

    # Check server availability
    if not comfyui.check_availability():
        print("[ERROR] ComfyUI server is not available")
        return

    # Load workflow
    workflow = workflow_mgr.load_workflow("flux-dev.json")
    if not workflow:
        print("[ERROR] Failed to load workflow")
        return

    # Validate workflow
    print("\nValidating workflow...")
    validation = workflow_mgr.validate_workflow(workflow, comfyui)

    print(f"\nValidation Result: {'✓ VALID' if validation['is_valid'] else '✗ INVALID'}")

    if validation["errors"]:
        print("\nErrors:")
        for error in validation["errors"]:
            print(f"  - {error}")

    if validation["warnings"]:
        print("\nWarnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    if validation["missing_models"]:
        print("\nMissing Models:")
        for model in validation["missing_models"]:
            print(f"  - {model['type']}: {model['name']}")

    if validation["is_valid"]:
        print("\n✓ Workflow is valid and ready for generation")
    else:
        print("\n✗ Workflow has errors, please fix before generating")


async def example_progress_polling():
    """Example: Poll for progress using get_progress tool."""
    print("\n" + "=" * 60)
    print("Example: Progress Polling")
    print("=" * 60)

    from clients.tools import control, generation

    print("\nStarting generation...")

    # Start generation without JSON progress
    result = await generation.generate_image(
        prompt="a spaceship in orbit, sci-fi, detailed",
        model="sd15",
        width=512,
        height=512,
        steps=30,
        json_progress=False,  # Don't use built-in progress
        validate=False,
    )

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        print("[ERROR] No prompt_id returned")
        return

    print(f"Prompt ID: {prompt_id}")
    print("\nPolling for progress...")

    # Poll for progress (in real usage, this would be in a loop)
    # For this example, we just show how to call it
    progress = await control.get_progress(prompt_id)

    print(f"\nProgress Status: {progress.get('status', 'unknown')}")
    if progress.get("position"):
        print(f"Queue Position: {progress['position']}")
    if progress.get("queue_length") is not None:
        print(f"Queue Length: {progress['queue_length']}")

    print(f"\nFinal Generation Status: {result['status']}")
    print(f"MinIO URL: {result.get('url', 'N/A')}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("MCP Progress Tracking & Local Output Examples")
    print("=" * 60)
    print("\nThese examples demonstrate:")
    print("  1. JSON progress tracking during generation")
    print("  2. Saving images to local files")
    print("  3. Dry-run workflow validation")
    print("  4. Polling for progress using get_progress")

    examples = [
        ("Workflow Validation", example_workflow_validation),
        ("Local File Output", example_local_file_output),
        ("JSON Progress Tracking", example_json_progress),
        ("Progress Polling", example_progress_polling),
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n[ERROR] Example '{name}' failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
