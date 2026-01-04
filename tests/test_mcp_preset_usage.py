#!/usr/bin/env python3
"""Test MCP server preset integration end-to-end.

This test validates that the MCP server correctly applies presets
and default configurations when generating images.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_mcp_default_negative_prompt():
    """Test that default negative prompt is applied when not specified."""
    print("\n[TEST] Testing default negative prompt application...")
    
    from mcp_server import _config
    from comfygen.tools import generation
    
    # Mock the actual generation to avoid needing ComfyUI server
    with patch.object(generation, 'generate_image', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "success", "url": "http://test.com/image.png"}
        
        # Import after patching
        from mcp_server import generate_image
        
        # Call without negative prompt
        result = await generate_image(
            prompt="a beautiful sunset",
            negative_prompt=""  # Empty string
        )
        
        # Verify the mock was called with default negative prompt
        mock_gen.assert_called_once()
        call_args = mock_gen.call_args
        
        # Check that negative_prompt was filled with default
        default_neg = _config.get("default_negative_prompt", "")
        assert call_args.kwargs["negative_prompt"] == default_neg, \
            f"Expected default negative prompt, got: {call_args.kwargs['negative_prompt']}"
        
        print(f"[OK] Default negative prompt applied: {default_neg[:50]}...")
    
    print("[PASS] Default negative prompt test passed\n")


async def test_mcp_preset_application():
    """Test that presets are correctly applied."""
    print("\n[TEST] Testing preset application...")
    
    from comfygen.tools import generation
    
    # Mock the actual generation
    with patch.object(generation, 'generate_image', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "success", "url": "http://test.com/image.png"}
        
        from mcp_server import generate_image
        
        # Test with draft preset
        result = await generate_image(
            prompt="a test image",
            preset="draft"
        )
        
        # Verify the mock was called with draft preset parameters
        mock_gen.assert_called_once()
        call_args = mock_gen.call_args
        
        # Draft preset should have steps=10, cfg=5.0
        assert call_args.kwargs["steps"] == 10, \
            f"Expected steps=10 from draft preset, got {call_args.kwargs['steps']}"
        assert call_args.kwargs["cfg"] == 5.0, \
            f"Expected cfg=5.0 from draft preset, got {call_args.kwargs['cfg']}"
        assert call_args.kwargs["validate"] == False, \
            f"Expected validate=False from draft preset"
        
        print("[OK] Draft preset parameters applied correctly")
        
        # Reset mock
        mock_gen.reset_mock()
        
        # Test with high-quality preset
        result = await generate_image(
            prompt="a test image",
            preset="high-quality"
        )
        
        call_args = mock_gen.call_args
        
        # High-quality preset should have steps=50, cfg=7.5
        assert call_args.kwargs["steps"] == 50, \
            f"Expected steps=50 from high-quality preset, got {call_args.kwargs['steps']}"
        assert call_args.kwargs["cfg"] == 7.5, \
            f"Expected cfg=7.5 from high-quality preset, got {call_args.kwargs['cfg']}"
        assert call_args.kwargs["validate"] == True, \
            f"Expected validate=True from high-quality preset"
        assert call_args.kwargs["auto_retry"] == True, \
            f"Expected auto_retry=True from high-quality preset"
        
        print("[OK] High-quality preset parameters applied correctly")
    
    print("[PASS] Preset application test passed\n")


async def test_mcp_preset_override():
    """Test that explicit parameters override preset values."""
    print("\n[TEST] Testing preset override with explicit parameters...")
    
    from comfygen.tools import generation
    
    # Mock the actual generation
    with patch.object(generation, 'generate_image', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "success", "url": "http://test.com/image.png"}
        
        from mcp_server import generate_image
        
        # Use draft preset but override steps
        result = await generate_image(
            prompt="a test image",
            preset="draft",  # draft has steps=10
            steps=30  # Override with 30
        )
        
        call_args = mock_gen.call_args
        
        # Should use overridden steps, but other draft params
        assert call_args.kwargs["steps"] == 30, \
            f"Expected steps=30 (override), got {call_args.kwargs['steps']}"
        assert call_args.kwargs["cfg"] == 5.0, \
            f"Expected cfg=5.0 from draft preset, got {call_args.kwargs['cfg']}"
        
        print("[OK] Explicit parameters override preset values")
    
    print("[PASS] Preset override test passed\n")


async def test_mcp_lora_preset():
    """Test that LoRA presets are applied."""
    print("\n[TEST] Testing LoRA preset application...")
    
    from comfygen.tools import generation
    from mcp_server import _lora_catalog
    
    # Mock the actual generation
    with patch.object(generation, 'generate_image', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "success", "url": "http://test.com/image.png"}
        
        from mcp_server import generate_image
        
        # Check if text_to_video preset exists
        if "text_to_video" in _lora_catalog.get("model_suggestions", {}):
            result = await generate_image(
                prompt="a test video",
                lora_preset="text_to_video"
            )
            
            call_args = mock_gen.call_args
            
            # Should have LoRAs applied
            loras = call_args.kwargs.get("loras")
            if loras is not None:
                assert isinstance(loras, list), "LoRAs should be a list"
                assert len(loras) > 0, "LoRAs list should not be empty"
                print(f"[OK] LoRA preset applied {len(loras)} LoRA(s)")
            else:
                print("[SKIP] LoRA preset did not specify default_loras")
        else:
            print("[SKIP] text_to_video preset not found in catalog")
    
    print("[PASS] LoRA preset test passed\n")


async def test_mcp_invalid_preset():
    """Test error handling for invalid presets."""
    print("\n[TEST] Testing invalid preset handling...")
    
    from mcp_server import generate_image
    
    # Call with invalid preset
    result = await generate_image(
        prompt="a test image",
        preset="invalid_preset_name"
    )
    
    # Should return error status
    assert result["status"] == "error", "Expected error status for invalid preset"
    assert "Unknown preset" in result["error"], \
        f"Expected 'Unknown preset' error message, got: {result['error']}"
    
    print("[OK] Invalid preset returns error")
    print("[PASS] Invalid preset handling test passed\n")


async def run_all_tests():
    """Run all MCP preset tests."""
    print("=" * 70)
    print("MCP SERVER PRESET INTEGRATION TESTS")
    print("=" * 70)
    
    try:
        await test_mcp_default_negative_prompt()
        await test_mcp_preset_application()
        await test_mcp_preset_override()
        await test_mcp_lora_preset()
        await test_mcp_invalid_preset()
        
        print("=" * 70)
        print("[SUCCESS] All MCP preset integration tests passed!")
        print("=" * 70)
        return 0
        
    except AssertionError as e:
        print(f"\n[FAIL] Test assertion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_all_tests()))
