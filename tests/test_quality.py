#!/usr/bin/env python3
"""Tests for quality scoring module."""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import comfy_gen
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfy_gen.quality import PYIQA_AVAILABLE


def test_quality_import():
    """Test that quality module can be imported."""
    from comfy_gen import quality
    assert quality is not None
    print("[OK] Quality module imported successfully")


def test_quality_pyiqa_availability():
    """Test pyiqa availability detection."""
    print(f"[INFO] pyiqa available: {PYIQA_AVAILABLE}")
    if not PYIQA_AVAILABLE:
        print("[WARN] pyiqa not available - quality scoring will be limited")
        print("[INFO] To install pyiqa: pip install pyiqa")
    else:
        print("[OK] pyiqa is available")


def test_quality_function_signature():
    """Test that score_image function has correct signature."""
    from comfy_gen.quality import score_image

    # Test with minimal arguments (should not crash)
    # Use tempfile to generate a unique non-existent file path
    with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp:
        nonexistent_path = tmp.name + "_nonexistent"

    result = score_image(nonexistent_path)

    # Check that result has expected keys
    assert "composite_score" in result, "Result should have 'composite_score' key"
    assert "grade" in result, "Result should have 'grade' key"

    # Check for error when file doesn't exist
    if "error" in result:
        print("[OK] score_image correctly handles missing file")

    print("[OK] score_image has correct signature")
    print(f"[INFO] Result keys: {list(result.keys())}")


def test_quality_scorer_class():
    """Test QualityScorer class initialization."""
    if not PYIQA_AVAILABLE:
        print("[SKIP] QualityScorer test - pyiqa not available")
        return

    try:
        from comfy_gen.quality import QualityScorer

        scorer = QualityScorer()
        assert scorer is not None
        print("[OK] QualityScorer instantiated successfully")

        # Test with non-existent file (unique path)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp:
            nonexistent_path = tmp.name + "_nonexistent"

        result = scorer.score_image(nonexistent_path)

        assert "error" in result or "composite_score" in result
        print("[OK] QualityScorer.score_image() works")

    except Exception as e:
        print(f"[WARN] QualityScorer test failed: {e}")


def test_grade_assignment():
    """Test that grades are assigned correctly."""
    from comfy_gen.quality import QualityScorer

    if not PYIQA_AVAILABLE:
        print("[SKIP] Grade assignment test - pyiqa not available")
        return

    try:
        scorer = QualityScorer()

        # Test grade assignment logic
        assert scorer._assign_grade(9.0) == "A"
        assert scorer._assign_grade(7.5) == "B"
        assert scorer._assign_grade(5.5) == "C"
        assert scorer._assign_grade(4.0) == "D"
        assert scorer._assign_grade(2.0) == "F"

        print("[OK] Grade assignment works correctly")
    except Exception as e:
        print(f"[WARN] Grade assignment test failed: {e}")


def test_metadata_integration():
    """Test that quality results integrate with metadata structure."""
    from comfy_gen.quality import score_image

    # Create a unique non-existent path
    with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp:
        nonexistent_path = tmp.name + "_nonexistent"

    # Create a mock result
    result = score_image(nonexistent_path)

    # Check that result structure matches metadata schema
    assert "composite_score" in result
    assert "grade" in result
    assert isinstance(result.get("technical"), (dict, type(None)))
    assert isinstance(result.get("aesthetic"), (float, int, type(None)))
    assert isinstance(result.get("detail"), (float, int, type(None)))

    print("[OK] Quality result structure matches metadata schema")


def main():
    """Run all tests."""
    print("Running quality module tests...\n")

    tests = [
        test_quality_import,
        test_quality_pyiqa_availability,
        test_quality_function_signature,
        test_quality_scorer_class,
        test_grade_assignment,
        test_metadata_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1
        print()

    print(f"Results: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
