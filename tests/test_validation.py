#!/usr/bin/env python3
"""Tests for image validation module."""

import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path to import comfy_gen
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfy_gen.validation import CLIP_AVAILABLE


def test_validation_import():
    """Test that validation module can be imported."""
    from comfy_gen import validation
    assert validation is not None
    print("[OK] Validation module imported successfully")


def test_validation_clip_availability():
    """Test CLIP availability detection."""
    print(f"[INFO] CLIP available: {CLIP_AVAILABLE}")
    if not CLIP_AVAILABLE:
        print("[WARN] CLIP not available - validation will be limited")
        print("[INFO] To install CLIP: pip install torch transformers")
    else:
        print("[OK] CLIP is available")


def test_validation_function_signature():
    """Test that validate_image function has correct signature."""
    from comfy_gen.validation import validate_image
    
    # Test with minimal arguments (should not crash)
    # Use tempfile to generate a cross-platform non-existent file path
    nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
    result = validate_image(nonexistent_path, "test prompt")
    
    # Check that result has expected keys
    assert "passed" in result, "Result should have 'passed' key"
    assert "reason" in result, "Result should have 'reason' key"
    assert "positive_score" in result, "Result should have 'positive_score' key"
    
    print("[OK] validate_image has correct signature")
    print(f"[INFO] Result keys: {list(result.keys())}")


def test_validator_class():
    """Test ImageValidator class can be imported."""
    from comfy_gen.validation import ImageValidator
    
    # Just check the class exists
    assert ImageValidator is not None
    print("[OK] ImageValidator class exists")


if __name__ == "__main__":
    print("Running validation tests...\n")
    
    tests = [
        test_validation_import,
        test_validation_clip_availability,
        test_validation_function_signature,
        test_validator_class,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning {test.__name__}...")
            test()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    sys.exit(0 if failed == 0 else 1)
