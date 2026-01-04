#!/usr/bin/env python3
"""Multi-dimensional image quality assessment using pyiqa.

This module provides comprehensive quality scoring across multiple dimensions:
- Technical quality: Artifacts, noise, blur (BRISQUE, NIQE)
- Aesthetic quality: Visual appeal, composition (LAION Aesthetic)
- Prompt adherence: Semantic similarity (CLIP)
- Detail quality: Fine details, textures (TOPIQ)

The composite score combines these dimensions with weighted averaging.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import torch
    from PIL import Image
    import pyiqa
    PYIQA_AVAILABLE = True
except ImportError:
    PYIQA_AVAILABLE = False

try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False


# Quality grade thresholds (Python 3.7+ preserves insertion order)
# Grades are checked in descending order: A -> B -> C -> D -> F
GRADE_THRESHOLDS = {
    'A': 8.0,
    'B': 6.5,
    'C': 5.0,
    'D': 3.0,
    'F': 0.0
}

# Composite score weights (must sum to 1.0)
WEIGHTS = {
    'technical': 0.30,
    'aesthetic': 0.25,
    'prompt_adherence': 0.25,
    'detail': 0.20
}


class QualityScorer:
    """Multi-dimensional image quality scorer using pyiqa and CLIP."""
    
    def __init__(self, device: Optional[str] = None):
        """Initialize the quality scorer.
        
        Args:
            device: Device to run models on ('cuda', 'cpu', or None for auto-detect)
        """
        if not PYIQA_AVAILABLE:
            raise RuntimeError(
                "pyiqa not available. Install with: pip install pyiqa"
            )
        
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        print(f"[INFO] Initializing quality scorer on {self.device}...")
        
        # Initialize technical quality metrics
        try:
            self.brisque = pyiqa.create_metric('brisque', device=self.device)
            print("[OK] BRISQUE metric loaded")
        except Exception as e:
            print(f"[WARN] Failed to load BRISQUE: {e}")
            self.brisque = None
        
        try:
            self.niqe = pyiqa.create_metric('niqe', device=self.device)
            print("[OK] NIQE metric loaded")
        except Exception as e:
            print(f"[WARN] Failed to load NIQE: {e}")
            self.niqe = None
        
        # Initialize aesthetic quality metric
        try:
            self.laion_aes = pyiqa.create_metric('laion_aes', device=self.device)
            print("[OK] LAION Aesthetic metric loaded")
        except Exception as e:
            print(f"[WARN] Failed to load LAION Aesthetic: {e}")
            self.laion_aes = None
        
        # Initialize detail quality metric
        try:
            self.topiq = pyiqa.create_metric('topiq_nr', device=self.device)
            print("[OK] TOPIQ metric loaded")
        except Exception as e:
            print(f"[WARN] Failed to load TOPIQ: {e}")
            self.topiq = None
        
        # Initialize CLIP for prompt adherence (optional)
        self.clip_model = None
        self.clip_processor = None
        if CLIP_AVAILABLE:
            try:
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                print("[OK] CLIP model loaded")
            except Exception as e:
                print(f"[WARN] Failed to load CLIP: {e}")
        
        print("[OK] Quality scorer initialized")
    
    def _normalize_brisque(self, score: float) -> float:
        """Normalize BRISQUE score to 0-10 scale (lower BRISQUE is better).
        
        BRISQUE range is typically 0-100, with lower being better quality.
        We invert and scale to 0-10.
        
        Args:
            score: Raw BRISQUE score (0-100, lower is better)
            
        Returns:
            Normalized score (0-10, higher is better)
        """
        # Clamp to expected range
        score = max(0, min(100, score))
        # Invert and scale: 0 -> 10, 100 -> 0
        return 10.0 * (1.0 - score / 100.0)
    
    def _normalize_niqe(self, score: float) -> float:
        """Normalize NIQE score to 0-10 scale (lower NIQE is better).
        
        NIQE range is typically 0-20+, with lower being better quality.
        We invert and scale to 0-10.
        
        Args:
            score: Raw NIQE score (typically 0-20, lower is better)
            
        Returns:
            Normalized score (0-10, higher is better)
        """
        # Clamp to expected range (most images are 0-15)
        score = max(0, min(15, score))
        # Invert and scale: 0 -> 10, 15 -> 0
        return 10.0 * (1.0 - score / 15.0)
    
    def _normalize_laion_aes(self, score: float) -> float:
        """Normalize LAION Aesthetic score to 0-10 scale.
        
        LAION Aesthetic already outputs in ~1-10 range, just clamp it.
        
        Args:
            score: Raw LAION Aesthetic score (typically 1-10)
            
        Returns:
            Normalized score (0-10)
        """
        return max(0, min(10, score))
    
    def _normalize_topiq(self, score: float) -> float:
        """Normalize TOPIQ score to 0-10 scale.
        
        TOPIQ outputs in 0-1 range, higher is better.
        Scale to 0-10.
        
        Args:
            score: Raw TOPIQ score (0-1, higher is better)
            
        Returns:
            Normalized score (0-10)
        """
        return max(0, min(10, score * 10.0))
    
    def _normalize_clip(self, score: float) -> float:
        """Normalize CLIP score to 0-10 scale.
        
        CLIP outputs probability in 0-1 range.
        Scale to 0-10.
        
        Args:
            score: Raw CLIP score (0-1, higher is better)
            
        Returns:
            Normalized score (0-10)
        """
        return max(0, min(10, score * 10.0))
    
    def compute_technical_quality(self, image_path: str) -> Dict[str, float]:
        """Compute technical quality metrics (artifacts, noise, blur).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with 'brisque', 'niqe', and 'composite' scores (0-10 scale)
        """
        result = {}
        scores = []
        
        if self.brisque:
            try:
                raw_score = float(self.brisque(image_path))
                normalized = self._normalize_brisque(raw_score)
                result['brisque'] = normalized
                scores.append(normalized)
            except Exception as e:
                print(f"[WARN] BRISQUE scoring failed: {e}")
                result['brisque'] = None
        else:
            result['brisque'] = None
        
        if self.niqe:
            try:
                raw_score = float(self.niqe(image_path))
                normalized = self._normalize_niqe(raw_score)
                result['niqe'] = normalized
                scores.append(normalized)
            except Exception as e:
                print(f"[WARN] NIQE scoring failed: {e}")
                result['niqe'] = None
        else:
            result['niqe'] = None
        
        # Composite is average of available scores
        result['composite'] = sum(scores) / len(scores) if scores else 0.0
        
        return result
    
    def compute_aesthetic_quality(self, image_path: str) -> Dict[str, float]:
        """Compute aesthetic quality metrics (visual appeal, composition).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with 'laion_aesthetic' and 'composite' scores (0-10 scale)
        """
        result = {}
        
        if self.laion_aes:
            try:
                raw_score = float(self.laion_aes(image_path))
                normalized = self._normalize_laion_aes(raw_score)
                result['laion_aesthetic'] = normalized
                result['composite'] = normalized
            except Exception as e:
                print(f"[WARN] LAION Aesthetic scoring failed: {e}")
                result['laion_aesthetic'] = None
                result['composite'] = 0.0
        else:
            result['laion_aesthetic'] = None
            result['composite'] = 0.0
        
        return result
    
    def compute_detail_quality(self, image_path: str) -> Dict[str, float]:
        """Compute detail quality metrics (fine details, textures).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with 'topiq' and 'composite' scores (0-10 scale)
        """
        result = {}
        
        if self.topiq:
            try:
                raw_score = float(self.topiq(image_path))
                normalized = self._normalize_topiq(raw_score)
                result['topiq'] = normalized
                result['composite'] = normalized
            except Exception as e:
                print(f"[WARN] TOPIQ scoring failed: {e}")
                result['topiq'] = None
                result['composite'] = 0.0
        else:
            result['topiq'] = None
            result['composite'] = 0.0
        
        return result
    
    def compute_prompt_adherence(
        self, 
        image_path: str, 
        prompt: str,
        negative_prompt: Optional[str] = None
    ) -> Dict[str, float]:
        """Compute prompt adherence using CLIP.
        
        Args:
            image_path: Path to the image file
            prompt: The positive text prompt
            negative_prompt: Optional negative prompt
            
        Returns:
            Dict with 'clip_score' and 'composite' scores (0-10 scale)
        """
        result = {}
        
        if not self.clip_model or not self.clip_processor:
            result['clip_score'] = None
            result['composite'] = 0.0
            return result
        
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Prepare prompts
            prompts = [prompt]
            if negative_prompt:
                prompts.append(negative_prompt)
            
            # Process inputs
            inputs = self.clip_processor(
                text=prompts,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # Compute embeddings
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Extract positive score
            raw_score = float(probs[0][0])
            normalized = self._normalize_clip(raw_score)
            
            result['clip_score'] = normalized
            result['composite'] = normalized
            
        except Exception as e:
            print(f"[WARN] CLIP scoring failed: {e}")
            result['clip_score'] = None
            result['composite'] = 0.0
        
        return result
    
    def calculate_grade(self, composite_score: float) -> str:
        """Calculate letter grade from composite score.
        
        Args:
            composite_score: Composite quality score (0-10)
            
        Returns:
            Letter grade ('A', 'B', 'C', 'D', or 'F')
        """
        for grade, threshold in GRADE_THRESHOLDS.items():
            if composite_score >= threshold:
                return grade
        return 'F'
    
    def score_image(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute comprehensive multi-dimensional quality scores.
        
        Args:
            image_path: Path to the image file
            prompt: Optional text prompt for CLIP scoring
            negative_prompt: Optional negative prompt for CLIP scoring
            
        Returns:
            Dictionary with:
                - technical: Dict of technical quality scores
                - aesthetic: Dict of aesthetic quality scores
                - prompt_adherence: Dict of prompt adherence scores (if prompt provided)
                - detail: Dict of detail quality scores
                - composite_score: Weighted composite score (0-10)
                - grade: Letter grade ('A'-'F')
        """
        if not Path(image_path).exists():
            return {
                "error": f"Image file not found: {image_path}",
                "composite_score": 0.0,
                "grade": "F"
            }
        
        print(f"[INFO] Scoring image: {image_path}")
        
        # Compute all dimensions
        technical = self.compute_technical_quality(image_path)
        aesthetic = self.compute_aesthetic_quality(image_path)
        detail = self.compute_detail_quality(image_path)
        
        # Compute prompt adherence if prompt provided
        if prompt:
            prompt_adherence = self.compute_prompt_adherence(image_path, prompt, negative_prompt)
        else:
            prompt_adherence = {'clip_score': None, 'composite': 0.0}
        
        # Calculate weighted composite score
        # Handle None composites by treating them as 0.0
        technical_composite = technical.get('composite', 0.0) or 0.0
        aesthetic_composite = aesthetic.get('composite', 0.0) or 0.0
        detail_composite = detail.get('composite', 0.0) or 0.0
        prompt_composite = prompt_adherence.get('composite', 0.0) or 0.0
        
        composite_score = (
            WEIGHTS['technical'] * technical_composite +
            WEIGHTS['aesthetic'] * aesthetic_composite +
            WEIGHTS['prompt_adherence'] * prompt_composite +
            WEIGHTS['detail'] * detail_composite
        )
        
        # Calculate grade
        grade = self.calculate_grade(composite_score)
        
        result = {
            'technical': technical,
            'aesthetic': aesthetic,
            'prompt_adherence': prompt_adherence,
            'detail': detail,
            'composite_score': round(composite_score, 2),
            'grade': grade
        }
        
        print(f"[OK] Quality score: {composite_score:.2f} (Grade: {grade})")
        
        return result


def score_image(
    image_path: str,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    device: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to score an image without creating a scorer instance.
    
    This creates a new scorer for each call, which is less efficient for batch
    scoring but simpler for single-use cases.
    
    Args:
        image_path: Path to the image file
        prompt: Optional text prompt for CLIP scoring
        negative_prompt: Optional negative prompt for CLIP scoring
        device: Device to run models on (None for auto-detect)
        
    Returns:
        Dictionary with quality scores (see QualityScorer.score_image)
    """
    if not PYIQA_AVAILABLE:
        return {
            "error": "pyiqa not available",
            "composite_score": 0.0,
            "grade": "F"
        }
    
    scorer = QualityScorer(device=device)
    return scorer.score_image(image_path, prompt, negative_prompt)


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 2:
        print("Usage: python -m comfy_gen.quality <image_path> [prompt] [negative_prompt]")
        print("\nScore an image's quality across multiple dimensions:")
        print("  - Technical: Artifacts, noise, blur")
        print("  - Aesthetic: Visual appeal, composition")
        print("  - Detail: Fine details, textures")
        print("  - Prompt Adherence: Semantic similarity (requires prompt)")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else None
    negative = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = score_image(image_path, prompt, negative)
    
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
        sys.exit(1)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Quality Assessment Results")
    print(f"{'='*60}\n")
    
    print(f"Composite Score: {result['composite_score']:.2f}/10.0")
    print(f"Grade: {result['grade']}\n")
    
    print(f"Technical Quality (artifacts, noise, blur):")
    tech = result['technical']
    if tech['brisque'] is not None:
        print(f"  BRISQUE: {tech['brisque']:.2f}")
    if tech['niqe'] is not None:
        print(f"  NIQE: {tech['niqe']:.2f}")
    print(f"  Composite: {tech['composite']:.2f}\n")
    
    print(f"Aesthetic Quality (visual appeal, composition):")
    aes = result['aesthetic']
    if aes['laion_aesthetic'] is not None:
        print(f"  LAION Aesthetic: {aes['laion_aesthetic']:.2f}")
    print(f"  Composite: {aes['composite']:.2f}\n")
    
    print(f"Detail Quality (fine details, textures):")
    det = result['detail']
    if det['topiq'] is not None:
        print(f"  TOPIQ: {det['topiq']:.2f}")
    print(f"  Composite: {det['composite']:.2f}\n")
    
    if prompt:
        print(f"Prompt Adherence (semantic similarity):")
        pa = result['prompt_adherence']
        if pa['clip_score'] is not None:
            print(f"  CLIP Score: {pa['clip_score']:.2f}")
        print(f"  Composite: {pa['composite']:.2f}\n")
    
    print(f"{'='*60}")
