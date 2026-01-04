#!/usr/bin/env python3
"""Test progress tracking and new MCP features."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from comfygen.comfyui_client import ComfyUIClient, WEBSOCKET_AVAILABLE
        print(f"  [OK] ComfyUIClient imported (WebSocket available: {WEBSOCKET_AVAILABLE})")
    except Exception as e:
        print(f"  [ERROR] Failed to import ComfyUIClient: {e}")
        return False
    
    try:
        from comfygen.workflows import WorkflowManager
        print("  [OK] WorkflowManager imported")
    except Exception as e:
        print(f"  [ERROR] Failed to import WorkflowManager: {e}")
        return False
    
    try:
        from comfygen.tools import generation
        print("  [OK] generation module imported")
    except Exception as e:
        print(f"  [ERROR] Failed to import generation: {e}")
        return False
    
    return True


def test_workflow_validation():
    """Test workflow validation."""
    print("\nTesting workflow validation...")
    
    try:
        from comfygen.workflows import WorkflowManager
        
        wf_mgr = WorkflowManager()
        
        # Test with an empty workflow
        result = wf_mgr.validate_workflow({})
        print(f"  Empty workflow validation: {result['is_valid']} (expected False)")
        assert not result['is_valid'], "Empty workflow should be invalid"
        assert len(result['errors']) > 0, "Empty workflow should have errors"
        
        # Test with a minimal workflow
        minimal_workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "test.safetensors"}
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {}
            },
            "3": {
                "class_type": "SaveImage",
                "inputs": {}
            }
        }
        
        result = wf_mgr.validate_workflow(minimal_workflow)
        print(f"  Minimal workflow validation: is_valid={result['is_valid']}, warnings={len(result['warnings'])}")
        # Should have warnings about missing models, but structure is valid
        
        print("  [OK] Workflow validation working")
        return True
        
    except Exception as e:
        print(f"  [ERROR] Workflow validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comfyui_client():
    """Test ComfyUI client with progress callback."""
    print("\nTesting ComfyUI client...")
    
    try:
        from comfygen.comfyui_client import ComfyUIClient
        
        client = ComfyUIClient()
        print(f"  ComfyUI client created: {client.host}")
        
        # Test that methods exist
        assert hasattr(client, 'wait_for_completion'), "wait_for_completion method exists"
        assert hasattr(client, '_start_progress_tracker'), "_start_progress_tracker method exists"
        assert hasattr(client, '_stop_progress_tracker'), "_stop_progress_tracker method exists"
        
        print("  [OK] ComfyUI client methods available")
        return True
        
    except Exception as e:
        print(f"  [ERROR] ComfyUI client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generation_signature():
    """Test that generate_image has the new parameters."""
    print("\nTesting generation function signature...")
    
    try:
        from comfygen.tools import generation
        import inspect
        
        sig = inspect.signature(generation.generate_image)
        params = sig.parameters
        
        # Check for new parameters
        assert 'output_path' in params, "output_path parameter exists"
        assert 'progress_callback' in params, "progress_callback parameter exists"
        
        print(f"  [OK] generate_image has {len(params)} parameters including:")
        print(f"    - output_path: {params['output_path'].default}")
        print(f"    - progress_callback: {params['progress_callback'].default}")
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Generation signature test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_server_tools():
    """Test MCP server tool registration."""
    print("\nTesting MCP server tools...")
    
    try:
        import asyncio
        import mcp_server
        
        async def check_tools():
            tools = await mcp_server.mcp.list_tools()
            tool_names = [tool.name for tool in tools]
            
            # Check for new/updated tools
            assert 'generate_image' in tool_names, "generate_image tool exists"
            assert 'validate_workflow' in tool_names, "validate_workflow tool exists"
            assert 'get_progress' in tool_names, "get_progress tool exists"
            
            print(f"  [OK] Found {len(tools)} MCP tools")
            print(f"    - generate_image: present")
            print(f"    - validate_workflow: present")
            print(f"    - get_progress: present")
            
            return True
        
        result = asyncio.run(check_tools())
        return result
        
    except Exception as e:
        print(f"  [ERROR] MCP server tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing MCP Progress Tracking and Local File Output")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Workflow Validation", test_workflow_validation),
        ("ComfyUI Client", test_comfyui_client),
        ("Generation Signature", test_generation_signature),
        ("MCP Server Tools", test_mcp_server_tools),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
