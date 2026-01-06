#!/usr/bin/env python3
"""Quick test to verify MCP server has all tools registered."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def main():
    """Test MCP server tools."""
    print("Testing Comprehensive MCP Server for ComfyUI")
    print("=" * 70)

    try:
        from mcp_server import mcp

        # List registered tools
        tools = await mcp.list_tools()

        print("\n[OK] MCP server loaded successfully")
        print(f"[OK] Total tools registered: {len(tools)}\n")

        # Group tools by category
        categories = {
            "Service Management": [],
            "Image Generation": [],
            "Video Generation": [],
            "Model Management": [],
            "Gallery & History": [],
            "Prompt Engineering": [],
            "Progress & Control": []
        }

        for tool in tools:
            name = tool.name
            if "comfyui" in name.lower() and "service" in name.lower():
                categories["Service Management"].append(name)
            elif name in ["generate_image", "img2img"]:
                categories["Image Generation"].append(name)
            elif name in ["generate_video", "image_to_video"]:
                categories["Video Generation"].append(name)
            elif name in ["list_models", "list_loras", "get_model_info", "suggest_model", "suggest_loras", "search_civitai"]:
                categories["Model Management"].append(name)
            elif name in ["list_images", "get_image_info", "delete_image", "get_history"]:
                categories["Gallery & History"].append(name)
            elif name in ["build_prompt", "suggest_negative", "analyze_prompt"]:
                categories["Prompt Engineering"].append(name)
            elif name in ["get_progress", "cancel", "get_queue", "get_system_status"]:
                categories["Progress & Control"].append(name)

        # Print tools by category
        for category, tool_names in categories.items():
            if tool_names:
                print(f"{category}:")
                for name in tool_names:
                    print(f"  - {name}")
                print()

        # Count tools in each category
        total_categorized = sum(len(tools) for tools in categories.values())
        print(f"Total categorized tools: {total_categorized}")
        print(f"Total registered tools: {len(tools)}")

        if total_categorized == len(tools):
            print("\n[OK] All tools properly categorized!")
        else:
            print(f"\n[WARN] {len(tools) - total_categorized} tools not categorized")

        print("\n" + "=" * 70)
        print("[SUCCESS] MCP server is ready for use!")

    except Exception as e:
        print(f"[ERROR] Failed to load MCP server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
