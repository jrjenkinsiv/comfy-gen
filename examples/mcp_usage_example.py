#!/usr/bin/env python3
"""Example demonstrating comprehensive MCP server usage.

This example shows how AI agents can use the MCP tools for:
- Model selection
- Image generation
- Video generation
- Gallery management
- Prompt engineering
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def example_simple_generation():
    """Example 1: Simple image generation."""
    print("\n" + "=" * 70)
    print("Example 1: Simple Image Generation")
    print("=" * 70)

    from clients.tools import generation

    result = await generation.generate_image(
        prompt="a sunset over mountains, highly detailed, 8k", width=768, height=512, steps=25
    )

    print(f"\nStatus: {result.get('status')}")
    if result.get("status") == "success":
        print(f"Image URL: {result.get('url')}")
        print(f"Prompt ID: {result.get('prompt_id')}")
    else:
        print(f"Error: {result.get('error')}")


async def example_intelligent_workflow():
    """Example 2: Intelligent model selection workflow."""
    print("\n" + "=" * 70)
    print("Example 2: Intelligent Model Selection Workflow")
    print("=" * 70)

    from clients.tools import models, prompts

    # Step 1: Get model recommendation
    print("\n[1/3] Getting model recommendation...")
    model_result = await models.suggest_model(task="portrait", style="realistic")
    print(f"Recommended model: {model_result.get('recommended')}")
    print(f"Reason: {model_result.get('reason')}")

    # Step 2: Analyze and improve prompt
    print("\n[2/3] Analyzing prompt...")
    prompt_text = "woman portrait"
    analysis = await prompts.analyze_prompt(prompt_text)
    print(f"Analysis: {len(analysis.get('analysis', {}).get('suggestions', []))} suggestions")
    for suggestion in analysis.get("analysis", {}).get("suggestions", [])[:2]:
        print(f"  - {suggestion}")

    # Step 3: Build improved prompt
    print("\n[3/3] Building improved prompt...")
    improved = await prompts.build_prompt(
        subject="woman portrait with detailed face",
        style="photorealistic, professional photography",
        setting="studio lighting, neutral background",
    )
    print(f"Improved prompt: {improved.get('prompt')}")


async def example_video_creation():
    """Example 3: Text-to-video generation."""
    print("\n" + "=" * 70)
    print("Example 3: Text-to-Video Generation")
    print("=" * 70)

    from clients.tools import models, video

    # Get LoRA suggestions for video
    print("\n[1/2] Getting LoRA suggestions for video...")
    lora_result = await models.suggest_loras(
        prompt="a flowing river through a forest",
        model="wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors",
        max_suggestions=2,
    )

    print(f"Found {lora_result.get('count', 0)} LoRA suggestions:")
    for lora in lora_result.get("suggestions", []):
        print(f"  - {lora.get('name')}: {lora.get('reason')}")

    # Generate video
    print("\n[2/2] Generating video...")
    video_result = await video.generate_video(
        prompt="a flowing river through a forest, gentle movement, natural lighting", steps=30, frames=81
    )

    print(f"\nStatus: {video_result.get('status')}")
    if video_result.get("status") == "success":
        print(f"Video URL: {video_result.get('url')}")
    else:
        print(f"Error: {video_result.get('error')}")


async def example_gallery_management():
    """Example 4: Gallery and history management."""
    print("\n" + "=" * 70)
    print("Example 4: Gallery and History Management")
    print("=" * 70)

    from clients.tools import gallery

    # List recent images
    print("\n[1/2] Listing recent images...")
    images = await gallery.list_images(limit=5, sort="newest")

    print(f"Found {images.get('count', 0)} images:")
    for img in images.get("images", [])[:3]:
        print(f"  - {img.get('name')} ({img.get('size')} bytes)")

    # Get generation history
    print("\n[2/2] Getting generation history...")
    history = await gallery.get_history(limit=3)

    print(f"\nFound {history.get('count', 0)} history entries:")
    for entry in history.get("history", []):
        params = entry.get("parameters", {})
        print(f"  - Prompt ID: {entry.get('prompt_id')}")
        print(f"    Prompt: {params.get('positive_prompt', 'N/A')[:50]}...")


async def example_system_monitoring():
    """Example 5: System monitoring and control."""
    print("\n" + "=" * 70)
    print("Example 5: System Monitoring and Control")
    print("=" * 70)

    from clients.tools import control

    # Check system status
    print("\n[1/3] Checking system status...")
    status = await control.get_system_status()

    if status.get("status") == "online":
        print("ComfyUI server is online")
        gpu_info = status.get("gpu", [])
        if gpu_info:
            for gpu in gpu_info:
                print(f"  - {gpu.get('name')}: {gpu.get('vram_used_percent', 0):.1f}% VRAM used")
    else:
        print(f"Server status: {status.get('status')}")

    # Check queue
    print("\n[2/3] Checking queue...")
    queue = await control.get_queue()

    print(f"Running jobs: {queue.get('running_count', 0)}")
    print(f"Pending jobs: {queue.get('pending_count', 0)}")

    # Check progress
    print("\n[3/3] Checking progress...")
    progress = await control.get_progress()

    if progress.get("is_processing"):
        print(f"Currently processing: {progress.get('current_job', {}).get('prompt_id')}")
    else:
        print("No active generation")


async def example_model_discovery():
    """Example 6: Model discovery with CivitAI."""
    print("\n" + "=" * 70)
    print("Example 6: Model Discovery with CivitAI")
    print("=" * 70)

    from clients.tools import models

    # Search for models
    print("\n[1/2] Searching CivitAI for detail enhancer LoRAs...")
    search_results = await models.search_civitai(
        query="detail enhancer", model_type="lora", base_model="SD 1.5", limit=3
    )

    print(f"Found {search_results.get('count', 0)} results:")
    for model in search_results.get("results", []):
        print(f"  - {model.get('name')}")
        print(f"    Type: {model.get('type')}, Downloads: {model.get('downloads')}")
        print(f"    Rating: {model.get('rating', 0):.2f}")

    # List installed models
    print("\n[2/2] Listing installed models...")
    installed = await models.list_models()

    print(f"Installed checkpoints: {installed.get('count', 0)}")
    for checkpoint in installed.get("checkpoints", [])[:3]:
        print(f"  - {checkpoint}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("ComfyGen MCP Server - Comprehensive Examples")
    print("=" * 70)
    print("\nThese examples demonstrate the MCP server capabilities.")
    print("Note: Most examples will show 'error' responses because")
    print("they require an active ComfyUI server connection.")
    print("=" * 70)

    try:
        # Run all examples
        await example_simple_generation()
        await example_intelligent_workflow()
        await example_video_creation()
        await example_gallery_management()
        await example_system_monitoring()
        await example_model_discovery()

        print("\n" + "=" * 70)
        print("Examples completed!")
        print("=" * 70)
        print("\nTo use these tools in an MCP client (like Claude Desktop):")
        print("1. Add the MCP server config to your client settings")
        print("2. Simply describe what you want to generate")
        print("3. The AI will use the appropriate tools automatically")
        print("\nSee docs/USAGE.md for full documentation.")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
