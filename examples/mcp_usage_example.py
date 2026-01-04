#!/usr/bin/env python3
"""Example demonstrating how to interact with the MCP server programmatically.

This is a simple example showing how to call MCP tools directly.
In practice, MCP clients (like Claude Desktop) handle this automatically.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import (
    check_comfyui_service_status,
    start_comfyui_service,
    stop_comfyui_service,
    restart_comfyui_service,
)


async def main():
    """Example MCP tool usage."""
    print("ComfyUI Service Management Example")
    print("=" * 60)
    
    # Check status
    print("\n1. Checking ComfyUI status...")
    print("-" * 60)
    status = check_comfyui_service_status()
    print(status)
    
    # Example: You could start the service
    # print("\n2. Starting ComfyUI service...")
    # print("-" * 60)
    # result = start_comfyui_service()
    # print(result)
    
    # Example: You could restart the service
    # print("\n3. Restarting ComfyUI service...")
    # print("-" * 60)
    # result = restart_comfyui_service()
    # print(result)
    
    # Example: You could stop the service
    # print("\n4. Stopping ComfyUI service...")
    # print("-" * 60)
    # result = stop_comfyui_service()
    # print(result)
    
    print("\n" + "=" * 60)
    print("Note: Uncomment the examples above to test other operations.")
    print("These tools are designed to be called by MCP clients like Claude.")


if __name__ == "__main__":
    asyncio.run(main())
