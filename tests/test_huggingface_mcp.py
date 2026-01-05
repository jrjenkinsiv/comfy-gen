#!/usr/bin/env python3
"""Test script for HuggingFace Hub MCP server functionality.

This script tests the HuggingFace MCP server tools without requiring actual API calls.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.huggingface_mcp import mcp


async def test_huggingface_mcp():
    """Test HuggingFace Hub MCP server tools."""
    print("Testing HuggingFace Hub MCP Server for Model Discovery")
    print("=" * 60)
    
    # List registered tools
    print("\nRegistered Tools:")
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"\n  Tool: {tool.name}")
        print(f"  {tool.description}")
        
        # Show parameters
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            schema = tool.inputSchema
            if 'properties' in schema:
                print(f"  Parameters:")
                for param_name, param_info in schema['properties'].items():
                    param_type = param_info.get('type', 'unknown')
                    param_desc = param_info.get('description', 'No description')
                    required = param_name in schema.get('required', [])
                    req_marker = " (required)" if required else " (optional)"
                    print(f"    - {param_name} ({param_type}){req_marker}: {param_desc[:80]}...")
    
    print(f"\n{len(tools)} tools registered")
    print("\n" + "=" * 60)
    
    # Verify expected tools
    expected_tools = [
        "hf_search_models",
        "hf_get_model_info",
        "hf_list_files",
        "hf_download"
    ]
    
    tool_names = [t.name for t in tools]
    
    print("\nVerifying expected tools:")
    all_found = True
    for expected in expected_tools:
        if expected in tool_names:
            print(f"  [OK] {expected}")
        else:
            print(f"  [MISSING] {expected}")
            all_found = False
    
    if all_found:
        print("\n[OK] All expected tools are registered!")
    else:
        print("\n[ERROR] Some tools are missing!")
        return 1
    
    print("\n" + "=" * 60)
    print("HuggingFace Hub MCP server is properly configured!")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_huggingface_mcp())
    sys.exit(exit_code)
