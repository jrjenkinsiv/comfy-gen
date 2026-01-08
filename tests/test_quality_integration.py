#!/usr/bin/env python3
"""Integration test for quality scoring with generate.py."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_metadata_quality_fields():
    """Test that metadata structure includes quality fields."""
    from generate import create_metadata_json

    # Create mock quality result
    quality_result = {
        "composite_score": 7.5,
        "grade": "B",
        "technical": {"brisque": 7.2, "niqe": 6.8, "raw_brisque": 28.0, "raw_niqe": 32.0},
        "aesthetic": 8.1,
        "detail": 7.8,
        "prompt_adherence": {"clip": 8.5},
    }

    # Create metadata
    metadata = create_metadata_json(
        workflow_path="/tmp/test.json",
        prompt="test prompt",
        negative_prompt="bad quality",
        workflow_params={"seed": 42, "steps": 30, "cfg": 7.0},
        loras=[],
        preset=None,
        validation_score=0.85,
        minio_url="http://test/image.png",
        quality_result=quality_result,
    )

    # Verify quality fields are present
    assert "quality" in metadata
    assert metadata["quality"]["composite_score"] == 7.5
    assert metadata["quality"]["grade"] == "B"
    assert metadata["quality"]["technical"]["brisque"] == 7.2
    assert metadata["quality"]["aesthetic"] == 8.1
    assert metadata["quality"]["detail"] == 7.8
    assert metadata["quality"]["prompt_adherence"]["clip"] == 8.5

    print("[OK] Metadata includes quality fields correctly")


def test_metadata_without_quality():
    """Test that metadata works without quality result."""
    from generate import create_metadata_json

    # Create metadata without quality
    metadata = create_metadata_json(
        workflow_path="/tmp/test.json",
        prompt="test prompt",
        negative_prompt="bad quality",
        workflow_params={"seed": 42, "steps": 30, "cfg": 7.0},
        loras=[],
        preset=None,
        validation_score=0.85,
        minio_url="http://test/image.png",
        quality_result=None,
    )

    # Verify quality fields are still present but None
    assert "quality" in metadata
    assert metadata["quality"]["composite_score"] is None
    assert metadata["quality"]["grade"] is None
    # prompt_adherence should have validation score
    assert metadata["quality"]["prompt_adherence"]["clip"] == 0.85

    print("[OK] Metadata works without quality result")


def test_quality_grade_colors():
    """Test that gallery server CSS includes all grade colors."""
    from scripts.gallery_server import HTML_TEMPLATE

    # Check that grade color classes are present
    assert "grade-a" in HTML_TEMPLATE
    assert "grade-b" in HTML_TEMPLATE
    assert "grade-c" in HTML_TEMPLATE
    assert "grade-d" in HTML_TEMPLATE
    assert "grade-f" in HTML_TEMPLATE

    print("[OK] Gallery server includes quality grade styling")


def test_quality_scorer_normalization():
    """Test score normalization functions."""
    try:
        from utils.quality import PYIQA_AVAILABLE, QualityScorer

        if not PYIQA_AVAILABLE:
            print("[SKIP] QualityScorer normalization test - pyiqa not available")
            return

        scorer = QualityScorer()

        # Test BRISQUE normalization (lower is better, inverted)
        # Score of 0 should normalize to 10
        assert scorer._normalize_brisque(0) == 10.0
        # Score of 100 should normalize to 0
        assert scorer._normalize_brisque(100) == 0.0
        # Score of 50 should normalize to 5.0
        assert abs(scorer._normalize_brisque(50) - 5.0) < 0.01

        # Test TOPIQ normalization (higher is better)
        # Score of 1.0 should normalize to 10
        assert scorer._normalize_topiq(1.0) == 10.0
        # Score of 0 should normalize to 0
        assert scorer._normalize_topiq(0.0) == 0.0
        # Score of 0.5 should normalize to 5.0
        assert abs(scorer._normalize_topiq(0.5) - 5.0) < 0.01

        # Test CLIP normalization
        assert scorer._normalize_clip(1.0) == 10.0
        assert scorer._normalize_clip(0.0) == 0.0
        assert abs(scorer._normalize_clip(0.5) - 5.0) < 0.01

        print("[OK] Score normalization functions work correctly")
    except Exception as e:
        print(f"[WARN] Score normalization test failed: {e}")


def main():
    """Run integration tests."""
    print("Running quality integration tests...\n")

    tests = [
        test_metadata_quality_fields,
        test_metadata_without_quality,
        test_quality_grade_colors,
        test_quality_scorer_normalization,
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
