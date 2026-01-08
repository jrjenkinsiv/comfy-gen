#!/usr/bin/env python3
"""Tests for image validation module."""

import os
import sys
import tempfile
import traceback  # Used for detailed error reporting in exception handler
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validation import CLIP_AVAILABLE, YOLO_AVAILABLE


def test_validation_import():
    """Test that validation module can be imported."""
    from utils import validation

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


def test_validation_yolo_availability():
    """Test YOLO availability detection."""
    print(f"[INFO] YOLO available: {YOLO_AVAILABLE}")
    if not YOLO_AVAILABLE:
        print("[WARN] YOLO not available - person count validation will be unavailable")
        print("[INFO] To install YOLO: pip install ultralytics")
    else:
        print("[OK] YOLO is available")


def test_validation_function_signature():
    """Test that validate_image function has correct signature."""
    from utils.validation import validate_image

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


def test_validation_function_person_count_signature():
    """Test that validate_image accepts person count parameter."""
    from utils.validation import validate_image

    # Test with person count validation enabled
    nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
    result = validate_image(nonexistent_path, "solo woman portrait", validate_person_count=True)

    # Check that result has expected keys
    assert "passed" in result, "Result should have 'passed' key"
    assert "reason" in result, "Result should have 'reason' key"

    # Check for person count specific keys
    assert "person_count" in result, "Result should have 'person_count' key when validate_person_count=True"
    assert "expected_person_count" in result, "Result should have 'expected_person_count' key"

    print("[OK] validate_image accepts validate_person_count parameter")
    print(f"[INFO] Result keys: {list(result.keys())}")


def test_extract_expected_person_count():
    """Test person count extraction from prompts."""
    from utils.validation import extract_expected_person_count

    test_cases = [
        ("solo woman portrait", 1),
        ("single person standing", 1),
        ("one man walking", 1),
        ("two women talking", 2),
        ("three people sitting", 3),
        ("group of five children", 5),
        ("5 people in a room", 5),
        ("landscape with mountains", None),  # No person count
        ("crowd of people", None),  # Unspecified count
    ]

    passed = 0
    failed = 0

    for prompt, expected in test_cases:
        result = extract_expected_person_count(prompt)
        if result == expected:
            print(f"[OK] '{prompt}' -> {result}")
            passed += 1
        else:
            print(f"[FAILED] '{prompt}' -> {result}, expected {expected}")
            failed += 1

    print(f"[INFO] Person count extraction: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} test cases failed"


def test_validator_class():
    """Test ImageValidator class can be imported."""
    from utils.validation import ImageValidator

    # Just check the class exists
    assert ImageValidator is not None
    print("[OK] ImageValidator class exists")


def test_count_persons_yolo_function():
    """Test that count_persons_yolo function exists and handles errors gracefully."""
    from utils.validation import count_persons_yolo

    # Test with non-existent file
    nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
    result = count_persons_yolo(nonexistent_path)

    # Should return error or None for person_count
    assert "person_count" in result, "Result should have 'person_count' key"

    if YOLO_AVAILABLE:
        # If YOLO is available, should have error for missing file
        assert result["person_count"] is None or "error" in result
        print("[OK] count_persons_yolo handles missing files gracefully")
    else:
        # If YOLO not available, should indicate that
        assert "error" in result
        print(f"[OK] count_persons_yolo reports unavailability: {result['error']}")


if __name__ == "__main__":
    print("Running validation tests...\n")

    tests = [
        test_validation_import,
        test_validation_clip_availability,
        test_validation_yolo_availability,
        test_validation_function_signature,
        test_validation_function_person_count_signature,
        test_extract_expected_person_count,
        test_validator_class,
        test_count_persons_yolo_function,
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
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)
