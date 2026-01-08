"""Tests for quality scoring module (pytest version)."""

import tempfile

import pytest

from utils.quality import PYIQA_AVAILABLE, QualityScorer, score_image


class TestQualityModule:
    """Tests for quality module imports and constants."""

    def test_quality_import(self):
        """Test that quality module can be imported."""
        from utils import quality

        assert quality is not None

    def test_pyiqa_availability(self):
        """Test pyiqa availability detection."""
        assert isinstance(PYIQA_AVAILABLE, bool)


class TestScoreImage:
    """Tests for score_image function."""

    def test_score_image_signature(self):
        """Test that score_image function has correct signature."""
        # Create unique non-existent path
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            nonexistent_path = tmp.name + "_nonexistent"

        result = score_image(nonexistent_path)

        # Check that result has expected keys
        assert "composite_score" in result
        assert "grade" in result

    def test_score_image_missing_file(self):
        """Test score_image handles missing files."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            nonexistent_path = tmp.name + "_nonexistent"

        result = score_image(nonexistent_path)

        # Should have error or valid structure
        assert isinstance(result, dict)
        assert "composite_score" in result or "error" in result

    def test_score_image_result_structure(self):
        """Test that score_image returns proper structure."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            nonexistent_path = tmp.name + "_nonexistent"

        result = score_image(nonexistent_path)

        # Verify structure matches metadata schema
        assert isinstance(result.get("technical"), (dict, type(None)))
        assert isinstance(result.get("aesthetic"), (float, int, type(None)))
        assert isinstance(result.get("detail"), (float, int, type(None)))


class TestQualityScorer:
    """Tests for QualityScorer class."""

    @pytest.mark.skipif(not PYIQA_AVAILABLE, reason="pyiqa not available")
    def test_quality_scorer_initialization(self):
        """Test QualityScorer class initialization."""
        scorer = QualityScorer()
        assert scorer is not None

    @pytest.mark.skipif(not PYIQA_AVAILABLE, reason="pyiqa not available")
    def test_quality_scorer_score_image(self):
        """Test QualityScorer.score_image method."""
        scorer = QualityScorer()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            nonexistent_path = tmp.name + "_nonexistent"

        result = scorer.score_image(nonexistent_path)

        assert isinstance(result, dict)
        assert "error" in result or "composite_score" in result

    @pytest.mark.skipif(not PYIQA_AVAILABLE, reason="pyiqa not available")
    def test_assign_grade(self):
        """Test that grades are assigned correctly."""
        scorer = QualityScorer()

        # Test grade assignment logic
        assert scorer._assign_grade(9.0) == "A"
        assert scorer._assign_grade(7.5) == "B"
        assert scorer._assign_grade(5.5) == "C"
        assert scorer._assign_grade(4.0) == "D"
        assert scorer._assign_grade(2.0) == "F"

    @pytest.mark.skipif(not PYIQA_AVAILABLE, reason="pyiqa not available")
    @pytest.mark.parametrize(
        "score,expected_grade",
        [
            (10.0, "A"),
            (8.5, "A"),
            (7.8, "B"),
            (6.5, "C"),
            (4.5, "D"),
            (3.0, "F"),
            (0.0, "F"),
        ],
    )
    def test_grade_ranges(self, score, expected_grade):
        """Test grade assignment for various score ranges."""
        scorer = QualityScorer()
        assert scorer._assign_grade(score) == expected_grade
