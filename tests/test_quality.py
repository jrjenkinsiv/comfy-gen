#!/usr/bin/env python3
"""Tests for quality scoring module."""

import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path to import comfy_gen
sys.path.insert(0, str(Path(__file__).parent.parent))

from comfy_gen.quality import PYIQA_AVAILABLE, CLIP_AVAILABLE


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


def test_quality_clip_availability():
    """Test CLIP availability detection."""
    print(f"[INFO] CLIP available: {CLIP_AVAILABLE}")
    if not CLIP_AVAILABLE:
        print("[WARN] CLIP not available - prompt adherence scoring will be limited")
        print("[INFO] To install CLIP: pip install torch transformers")
    else:
        print("[OK] CLIP is available")


def test_quality_function_signature():
    """Test that score_image function has correct signature."""
    from comfy_gen.quality import score_image
    
    # Test with minimal arguments (should not crash)
    # Use tempfile to generate a cross-platform non-existent file path
    nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
    result = score_image(nonexistent_path, "test prompt")
    
    # Check that result has expected keys
    assert "composite_score" in result, "Result should have 'composite_score' key"
    assert "grade" in result, "Result should have 'grade' key"
    
    # Should have error since file doesn't exist or pyiqa not available
    if not PYIQA_AVAILABLE or not os.path.exists(nonexistent_path):
        assert "error" in result or result["composite_score"] == 0.0, \
            "Result should have 'error' key or zero score for nonexistent file"
    
    print("[OK] score_image has correct signature")
    print(f"[INFO] Result keys: {list(result.keys())}")


def test_quality_scorer_class():
    """Test QualityScorer class can be imported."""
    from comfy_gen.quality import QualityScorer
    
    # Just check the class exists
    assert QualityScorer is not None
    print("[OK] QualityScorer class exists")


def test_grade_thresholds():
    """Test that grade thresholds are defined correctly."""
    from comfy_gen.quality import GRADE_THRESHOLDS
    
    assert "A" in GRADE_THRESHOLDS
    assert "B" in GRADE_THRESHOLDS
    assert "C" in GRADE_THRESHOLDS
    assert "D" in GRADE_THRESHOLDS
    assert "F" in GRADE_THRESHOLDS
    
    # Check thresholds are in descending order
    assert GRADE_THRESHOLDS["A"] >= GRADE_THRESHOLDS["B"]
    assert GRADE_THRESHOLDS["B"] >= GRADE_THRESHOLDS["C"]
    assert GRADE_THRESHOLDS["C"] >= GRADE_THRESHOLDS["D"]
    assert GRADE_THRESHOLDS["D"] >= GRADE_THRESHOLDS["F"]
    
    print("[OK] Grade thresholds defined correctly")
    print(f"[INFO] Thresholds: {GRADE_THRESHOLDS}")


def test_weights():
    """Test that composite score weights sum to 1.0."""
    from comfy_gen.quality import WEIGHTS
    
    total_weight = sum(WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.001, f"Weights should sum to 1.0, got {total_weight}"
    
    print("[OK] Weights sum to 1.0")
    print(f"[INFO] Weights: {WEIGHTS}")


if __name__ == "__main__":
    print("Running quality scoring tests...\n")
    
    tests = [
        test_quality_import,
        test_quality_pyiqa_availability,
        test_quality_clip_availability,
        test_quality_function_signature,
        test_quality_scorer_class,
        test_grade_thresholds,
        test_weights,
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print(f"{'='*60}")
    
    sys.exit(0 if failed == 0 else 1)
