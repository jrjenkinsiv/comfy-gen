#!/usr/bin/env python3
"""Tests for MCP preset integration.

This test validates that the MCP server correctly applies presets and
configuration defaults.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_mcp_preset_integration():
    """Test that MCP server correctly handles presets."""
    print("Testing MCP Preset Integration")
    print("=" * 60)
    
    # Import after path is set up
    import mcp_server
    from comfygen.config import get_config
    
    # Get config for comparison
    config = get_config()
    
    # Test 1: Config loaded on startup
    print("\n[TEST 1] Config loaded on startup")
    assert mcp_server._config is not None, "MCP server should have config loaded"
    print("[OK] Config loaded successfully")
    
    # Test 2: List tools and verify generate_image parameters
    print("\n[TEST 2] Verify generate_image tool schema")
    tools = await mcp_server.mcp.list_tools()
    gen_tool = next((t for t in tools if t.name == 'generate_image'), None)
    
    assert gen_tool is not None, "generate_image tool should exist"
    schema = gen_tool.inputSchema
    props = schema.get('properties', {})
    
    # Check for new parameters
    assert 'preset' in props, "generate_image should have preset parameter"
    assert 'lora_preset' in props, "generate_image should have lora_preset parameter"
    
    # Check that parameters are optional (not in required list)
    required = schema.get('required', [])
    assert 'preset' not in required, "preset should be optional"
    assert 'lora_preset' not in required, "lora_preset should be optional"
    
    print("[OK] generate_image has preset and lora_preset parameters")
    print(f"    Required params: {required}")
    print(f"    Optional params include: preset, lora_preset")
    
    # Test 3: Verify parameter defaults match config
    print("\n[TEST 3] Verify default negative prompt behavior")
    # The default should now be empty string, relying on config
    assert props['negative_prompt'].get('default') == "", \
        "negative_prompt default should be empty to use config default"
    print("[OK] negative_prompt defaults to empty (will use config default)")
    
    # Test 4: Verify other generation tools also use config
    print("\n[TEST 4] Verify other generation tools use config defaults")
    for tool_name in ['img2img', 'generate_video', 'image_to_video']:
        tool = next((t for t in tools if t.name == tool_name), None)
        assert tool is not None, f"{tool_name} tool should exist"
        
        tool_schema = tool.inputSchema
        tool_props = tool_schema.get('properties', {})
        
        # Check that negative_prompt defaults to empty
        if 'negative_prompt' in tool_props:
            default = tool_props['negative_prompt'].get('default', None)
            # Allow empty string or no default
            assert default == "" or default is None, \
                f"{tool_name} negative_prompt should default to empty"
        
        print(f"[OK] {tool_name} uses config defaults")
    
    # Test 5: Verify config values are accessible
    print("\n[TEST 5] Verify config values match expected")
    default_neg = config.get_default_negative_prompt()
    assert len(default_neg) > 0, "Config should have non-empty default negative prompt"
    print(f"[OK] Config default negative: {default_neg[:50]}...")
    
    presets = config.get_presets()
    assert len(presets) >= 3, "Should have at least 3 presets"
    print(f"[OK] Config has {len(presets)} presets")
    
    lora_presets = config.get_lora_presets()
    assert len(lora_presets) >= 1, "Should have at least 1 LoRA preset"
    print(f"[OK] Config has {len(lora_presets)} LoRA presets")
    
    print("\n" + "=" * 60)
    print("[OK] All MCP preset integration tests passed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_preset_integration())
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
