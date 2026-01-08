"""Tests for validation module (pytest version)."""

import os
import tempfile

import pytest

from utils.validation import (
    CLIP_AVAILABLE,
    YOLO_AVAILABLE,
    ImageValidator,
    count_persons_yolo,
    extract_expected_person_count,
    validate_image,
)


class TestValidationModule:
    """Tests for validation module imports and constants."""

    def test_validation_import(self):
        """Test that validation module can be imported."""
        from utils import validation

        assert validation is not None

    def test_clip_availability(self):
        """Test CLIP availability detection."""
        assert isinstance(CLIP_AVAILABLE, bool)

    def test_yolo_availability(self):
        """Test YOLO availability detection."""
        assert isinstance(YOLO_AVAILABLE, bool)


class TestValidateImage:
    """Tests for validate_image function."""

    def test_validate_image_signature(self):
        """Test that validate_image function has correct signature."""
        nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
        result = validate_image(nonexistent_path, "test prompt")

        # Check that result has expected keys
        assert "passed" in result
        assert "reason" in result
        assert "positive_score" in result

    def test_validate_image_with_person_count(self):
        """Test that validate_image accepts person count parameter."""
        nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
        result = validate_image(nonexistent_path, "solo woman portrait", validate_person_count=True)

        # Check that result has expected keys
        assert "passed" in result
        assert "reason" in result
        assert "person_count" in result
        assert "expected_person_count" in result


class TestExtractExpectedPersonCount:
    """Tests for extract_expected_person_count function."""

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            ("solo woman portrait", 1),
            ("single person standing", 1),
            ("one man walking", 1),
            ("two women talking", 2),
            ("three people sitting", 3),
            ("group of five children", 5),
            ("5 people in a room", 5),
            ("landscape with mountains", None),
            ("crowd of people", None),
        ],
    )
    def test_person_count_extraction(self, prompt, expected):
        """Test person count extraction from various prompts."""
        result = extract_expected_person_count(prompt)
        assert result == expected


class TestImageValidator:
    """Tests for ImageValidator class."""

    def test_validator_class_exists(self):
        """Test ImageValidator class can be imported."""
        assert ImageValidator is not None

    @pytest.mark.skipif(not CLIP_AVAILABLE, reason="CLIP not available")
    def test_validator_initialization(self):
        """Test ImageValidator can be instantiated."""
        validator = ImageValidator()
        assert validator is not None


class TestCountPersonsYolo:
    """Tests for count_persons_yolo function."""

    def test_count_persons_yolo_missing_file(self):
        """Test that count_persons_yolo handles missing files gracefully."""
        nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
        result = count_persons_yolo(nonexistent_path)

        # Should return error or None for person_count
        assert "person_count" in result

        if YOLO_AVAILABLE:
            # If YOLO is available, should have error for missing file
            assert result["person_count"] is None or "error" in result
        else:
            # If YOLO not available, should indicate that
            assert "error" in result

    @pytest.mark.skipif(not YOLO_AVAILABLE, reason="YOLO not available")
    def test_count_persons_yolo_returns_dict(self):
        """Test that count_persons_yolo returns proper dict structure."""
        nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent_test_image.png")
        result = count_persons_yolo(nonexistent_path)

        assert isinstance(result, dict)
        assert "person_count" in result
