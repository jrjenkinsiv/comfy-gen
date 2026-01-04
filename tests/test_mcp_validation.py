#!/usr/bin/env python3
"""Test script for MCP CLIP validation functionality.

This script tests the validation features added to the MCP server.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_generate_image_signature():
    """Test that generate_image has validation parameters."""
    from comfygen.tools import generation
    
    import inspect
    sig = inspect.signature(generation.generate_image)
    params = sig.parameters
    
    # Check that validation parameters exist
    assert 'validate' in params, "Missing 'validate' parameter"
    assert 'auto_retry' in params, "Missing 'auto_retry' parameter"
    assert 'retry_limit' in params, "Missing 'retry_limit' parameter"
    assert 'positive_threshold' in params, "Missing 'positive_threshold' parameter"
    
    # Check defaults
    assert params['validate'].default == True, "validate default should be True"
    assert params['auto_retry'].default == True, "auto_retry default should be True"
    assert params['retry_limit'].default == 3, "retry_limit default should be 3"
    assert params['positive_threshold'].default == 0.25, "positive_threshold default should be 0.25"
    
    print("[OK] generate_image has correct validation parameters")


async def test_mcp_tool_signature():
    """Test that MCP tool wrapper has validation parameters."""
    import inspect
    
    # Import mcp_server to register tools
    from mcp_server import generate_image as mcp_generate_image
    
    sig = inspect.signature(mcp_generate_image)
    params = sig.parameters
    
    # Check that validation parameters exist
    assert 'validate' in params, "MCP tool missing 'validate' parameter"
    assert 'auto_retry' in params, "MCP tool missing 'auto_retry' parameter"
    assert 'retry_limit' in params, "MCP tool missing 'retry_limit' parameter"
    assert 'positive_threshold' in params, "MCP tool missing 'positive_threshold' parameter"
    
    print("[OK] MCP tool wrapper has correct validation parameters")


async def test_adjust_prompt_for_retry():
    """Test the prompt adjustment function."""
    from comfygen.tools.generation import _adjust_prompt_for_retry
    
    # Test basic adjustment with pattern that matches
    positive = "single car on a road"
    negative = "blurry"
    
    adj_pos, adj_neg = _adjust_prompt_for_retry(positive, negative, 1)
    
    # Check that "single car" gets weighted
    assert "(single car" in adj_pos.lower(), \
        f"Expected weight on 'single car', got: {adj_pos}"
    
    # Check that negative terms are added
    assert "duplicate" in adj_neg.lower(), \
        f"Expected 'duplicate' in negative prompt, got: {adj_neg}"
    
    print(f"[OK] Prompt adjustment works")
    print(f"     Adjusted positive: {adj_pos}")
    print(f"     Adjusted negative: {adj_neg}")


async def test_validation_module_import():
    """Test that validation module can be imported."""
    try:
        from comfy_gen.validation import validate_image
        print("[OK] Validation module imported successfully")
        return True
    except ImportError as e:
        print(f"[WARN] Validation module not available: {e}")
        print("[INFO] This is expected if CLIP dependencies are not installed")
        return False


async def test_generate_with_validation_disabled():
    """Test generation with validation disabled."""
    from comfygen.tools import generation
    
    # Mock the clients to avoid needing actual ComfyUI server
    mock_comfyui = MagicMock()
    mock_comfyui.check_availability.return_value = True
    mock_comfyui.queue_prompt.return_value = "test_prompt_id"
    mock_comfyui.wait_for_completion.return_value = {
        "outputs": {
            "1": {
                "images": [{"filename": "test_image.png"}]
            }
        }
    }
    
    mock_minio = MagicMock()
    mock_minio.endpoint = "192.168.1.215:9000"
    mock_minio.bucket = "comfy-gen"
    
    mock_workflow_mgr = MagicMock()
    mock_workflow_mgr.load_workflow.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_prompt.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_dimensions.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_seed.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_sampler_params.return_value = {"1": {"class_type": "KSampler"}}
    
    with patch('comfygen.tools.generation._get_comfyui', return_value=mock_comfyui), \
         patch('comfygen.tools.generation._get_minio', return_value=mock_minio), \
         patch('comfygen.tools.generation._get_workflow_mgr', return_value=mock_workflow_mgr):
        
        result = await generation.generate_image(
            prompt="test prompt",
            validate=False
        )
        
        # Check result structure
        assert result['status'] == 'success', f"Expected success, got: {result.get('status')}"
        assert 'url' in result, "Result should have 'url' key"
        assert 'validation' not in result or result.get('validation') is None, \
            "Validation should not run when disabled"
        
        print("[OK] Generation with validation disabled works")


async def test_validation_unavailable_handling():
    """Test graceful handling when validation dependencies are unavailable."""
    from comfygen.tools import generation
    
    # Mock the clients
    mock_comfyui = MagicMock()
    mock_comfyui.check_availability.return_value = True
    mock_comfyui.queue_prompt.return_value = "test_prompt_id"
    mock_comfyui.wait_for_completion.return_value = {
        "outputs": {
            "1": {
                "images": [{"filename": "test_image.png"}]
            }
        }
    }
    
    mock_minio = MagicMock()
    mock_minio.endpoint = "192.168.1.215:9000"
    mock_minio.bucket = "comfy-gen"
    
    mock_workflow_mgr = MagicMock()
    mock_workflow_mgr.load_workflow.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_prompt.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_dimensions.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_seed.return_value = {"1": {"class_type": "KSampler"}}
    mock_workflow_mgr.set_sampler_params.return_value = {"1": {"class_type": "KSampler"}}
    
    # Mock validation import to fail
    with patch('comfygen.tools.generation._get_comfyui', return_value=mock_comfyui), \
         patch('comfygen.tools.generation._get_minio', return_value=mock_minio), \
         patch('comfygen.tools.generation._get_workflow_mgr', return_value=mock_workflow_mgr), \
         patch.dict('sys.modules', {'comfy_gen.validation': None}):
        
        result = await generation.generate_image(
            prompt="test prompt",
            validate=True
        )
        
        # Should succeed but indicate validation unavailable
        assert result['status'] == 'success', f"Expected success, got: {result}"
        if 'validation' in result:
            assert result['validation'].get('passed') is None or \
                   'not available' in result['validation'].get('reason', '').lower(), \
                   f"Expected validation unavailable message, got: {result['validation']}"
        
        print("[OK] Graceful handling when validation unavailable")


async def run_all_tests():
    """Run all tests."""
    print("Testing MCP CLIP Validation Support")
    print("=" * 60)
    
    tests = [
        ("Parameter Signature", test_generate_image_signature),
        ("MCP Tool Signature", test_mcp_tool_signature),
        ("Prompt Adjustment", test_adjust_prompt_for_retry),
        ("Validation Module Import", test_validation_module_import),
        ("Generation with Validation Disabled", test_generate_with_validation_disabled),
        ("Validation Unavailable Handling", test_validation_unavailable_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            await test_func()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test_name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
