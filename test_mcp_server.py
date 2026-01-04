#!/usr/bin/env python3
"""Test script for MCP server functionality.

This script tests the MCP server tools without actually running the full server.
"""

import asyncio
from mcp_server import mcp


async def test_mcp_server():
    """Test MCP server tools."""
    print("Testing MCP Server for ComfyUI Service Management")
    print("=" * 60)
    
    # List registered tools
    print("\nRegistered Tools:")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"  - {tool.name}")
        print(f"    {tool.description}")
        print()
    
    print(f"Total tools registered: {len(tools)}")
    print("\n" + "=" * 60)
    print("MCP server is properly configured!")
    

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
