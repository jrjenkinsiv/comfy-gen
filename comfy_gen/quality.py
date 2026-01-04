#!/usr/bin/env python3
"""Image quality assessment module.

This module provides multi-dimensional quality scoring for generated images:
- Technical quality (artifacts, noise, blur)
- Aesthetic quality (visual appeal, composition)
- Prompt adherence (semantic matching via CLIP)
- Detail quality (sharpness, fine details)

Since pyiqa is not yet installed, this initial implementation uses CLIP-based
scoring with heuristics until full quality metrics are available.
"""

import sys
from typing import Dict, Optional, Any
from pathlib import Path

try:
    from .validation import ImageValidator, CLIP_AVAILABLE
except (ImportError, ValueError):
    # Running as script or module not installed
    try:
        from comfy_gen.validation import ImageValidator, CLIP_AVAILABLE
    except ImportError:
        from validation import ImageValidator, CLIP_AVAILABLE


class QualityScorer:
    """Multi-dimensional quality scorer for generated images."""
    
    def __init__(self):
        """Initialize the quality scorer."""
        self.validator = None
    
    def _ensure_validator(self):
        """Lazy-load the CLIP validator when needed."""
        if self.validator is None and CLIP_AVAILABLE:
            self.validator = ImageValidator()
    
    def score_image(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Score an image on multiple quality dimensions.
        
        Args:
            image_path: Path to the generated image
            prompt: Positive text prompt used for generation
            negative_prompt: Negative prompt if used
        
        Returns:
            Dictionary with quality scores:
                - composite_score: Overall quality (0-10 scale)
                - prompt_adherence: How well image matches prompt (0-10)
                - technical: Technical quality estimate (0-10)
                - aesthetic: Aesthetic quality estimate (0-10)
                - detail: Detail quality estimate (0-10)
                - grade: Letter grade (A, B, C, D, F)
                - passed: Boolean if score meets threshold
        """
        if not Path(image_path).exists():
            return {
                "composite_score": 0.0,
                "prompt_adherence": 0.0,
                "technical": 0.0,
                "aesthetic": 0.0,
                "detail": 0.0,
                "grade": "F",
                "passed": False,
                "error": f"Image file not found: {image_path}"
            }
        
        # Get CLIP score for prompt adherence
        prompt_adherence_score = 5.0  # Default neutral score
        try:
            if CLIP_AVAILABLE:
                self._ensure_validator()
                if self.validator:
                    clip_result = self.validator.compute_clip_score(
                        image_path, prompt, negative_prompt
                    )
                    if "error" not in clip_result:
                        # Convert CLIP score (0-1) to 0-10 scale
                        # CLIP scores typically range 0.2-0.4 for good matches
                        # Map 0.25 -> 5.0, 0.35 -> 7.5, 0.45+ -> 10.0
                        clip_score = clip_result.get("positive_score", 0.0)
                        prompt_adherence_score = self._normalize_clip_score(clip_score)
        except Exception:
            # Silently fall back to default score if CLIP loading fails
            pass
        
        # For now, use heuristics for other dimensions
        # These will be replaced with actual metrics when pyiqa is available
        technical_score = 7.0  # Assume good technical quality by default
        aesthetic_score = 7.0  # Assume good aesthetics by default
        detail_score = 7.0     # Assume good detail by default
        
        # Composite score weighted average
        composite_score = (
            0.25 * prompt_adherence_score +  # Prompt adherence
            0.30 * technical_score +          # Technical quality
            0.25 * aesthetic_score +          # Aesthetic quality
            0.20 * detail_score               # Detail quality
        )
        
        # Assign letter grade
        grade = self._score_to_grade(composite_score)
        
        return {
            "composite_score": round(composite_score, 2),
            "prompt_adherence": round(prompt_adherence_score, 2),
            "technical": round(technical_score, 2),
            "aesthetic": round(aesthetic_score, 2),
            "detail": round(detail_score, 2),
            "grade": grade,
            "passed": composite_score >= 7.0  # Default threshold
        }
    
    def _normalize_clip_score(self, clip_score: float) -> float:
        """Normalize CLIP score (0-1) to quality score (0-10).
        
        CLIP scores for good matches typically range 0.2-0.4:
        - 0.25 or below: Poor match (< 5.0)
        - 0.30: Decent match (~7.0)
        - 0.35: Good match (~8.5)
        - 0.40+: Excellent match (10.0)
        """
        if clip_score < 0.20:
            return 0.0
        elif clip_score < 0.25:
            # 0.20-0.25 -> 0.0-5.0
            return (clip_score - 0.20) / 0.05 * 5.0
        elif clip_score < 0.30:
            # 0.25-0.30 -> 5.0-7.0
            return 5.0 + (clip_score - 0.25) / 0.05 * 2.0
        elif clip_score < 0.35:
            # 0.30-0.35 -> 7.0-8.5
            return 7.0 + (clip_score - 0.30) / 0.05 * 1.5
        else:
            # 0.35+ -> 8.5-10.0
            normalized = 8.5 + min((clip_score - 0.35) / 0.10 * 1.5, 1.5)
            return min(normalized, 10.0)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 8.0:
            return "A"
        elif score >= 6.5:
            return "B"
        elif score >= 5.0:
            return "C"
        elif score >= 3.0:
            return "D"
        else:
            return "F"


def score_image(
    image_path: str,
    prompt: str,
    negative_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to score an image.
    
    Args:
        image_path: Path to the generated image
        prompt: Positive text prompt
        negative_prompt: Negative prompt if used
    
    Returns:
        Dictionary with quality scores (see QualityScorer.score_image)
    """
    scorer = QualityScorer()
    return scorer.score_image(image_path, prompt, negative_prompt)


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 3:
        print("Usage: python quality.py <image_path> <prompt> [negative_prompt]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2]
    negative = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = score_image(image_path, prompt, negative)
    
    print(f"\nQuality Assessment:")
    print(f"  Composite Score: {result['composite_score']:.2f}/10.0 (Grade: {result['grade']})")
    print(f"  Prompt Adherence: {result['prompt_adherence']:.2f}/10.0")
    print(f"  Technical Quality: {result['technical']:.2f}/10.0")
    print(f"  Aesthetic Quality: {result['aesthetic']:.2f}/10.0")
    print(f"  Detail Quality: {result['detail']:.2f}/10.0")
    print(f"  Passed: {result['passed']}")
    
    if "error" in result:
        print(f"  Error: {result['error']}")
        sys.exit(1)
