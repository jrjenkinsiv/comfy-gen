#!/usr/bin/env python3
"""Multi-dimensional image quality assessment using pyiqa.

This module provides comprehensive quality scoring across multiple dimensions:
- Technical quality: Artifacts, noise, blur, jaggedness (BRISQUE, NIQE)
- Aesthetic quality: Visual appeal, composition (LAION Aesthetic)
- Prompt adherence: Semantic match to text description (CLIP)
- Detail quality: Fine detail preservation, textures (TOPIQ)

Usage:
    # As a module
    from comfy_gen.quality import QualityScorer
    scorer = QualityScorer()
    result = scorer.score_image("image.png", prompt="a sunset")
    
    # As a CLI tool
    python3 -m comfy_gen.quality <image> [prompt]
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

# Try to import CLIP for prompt adherence scoring
try:
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False


class QualityScorer:
    """Multi-dimensional quality scorer for generated images."""
    
    def __init__(self):
        """Initialize quality scorer with pyiqa metrics and CLIP."""
        if not PYIQA_AVAILABLE:
            raise RuntimeError(
                "pyiqa not available. Install with: pip install pyiqa"
            )
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[INFO] Loading quality metrics on {self.device}...")
        
        # Technical quality metrics (no-reference)
        # BRISQUE: Blind/Referenceless Image Spatial Quality Evaluator
        # Lower scores = better quality (0-100 range)
        self.brisque = pyiqa.create_metric('brisque', device=self.device)
        
        # NIQE: Natural Image Quality Evaluator
        # Lower scores = better quality (measures deviation from natural statistics)
        self.niqe = pyiqa.create_metric('niqe', device=self.device)
        
        # Aesthetic quality metric
        # LAION Aesthetic Predictor: predicts human aesthetic preferences
        # Higher scores = better aesthetics (typically 1-10 scale)
        try:
            self.laion_aes = pyiqa.create_metric('laion_aes', device=self.device)
        except Exception as e:
            print(f"[WARN] Failed to load LAION aesthetic predictor: {e}")
            self.laion_aes = None
        
        # Detail/perceptual quality metric
        # TOPIQ: Task-Oriented Perceptual Image Quality
        # Higher scores = better perceptual quality (0-1 range typically)
        try:
            self.topiq = pyiqa.create_metric('topiq_nr', device=self.device)
        except Exception as e:
            print(f"[WARN] Failed to load TOPIQ metric: {e}")
            self.topiq = None
        
        # CLIP for prompt adherence (optional)
        self.clip_model = None
        self.clip_processor = None
        if CLIP_AVAILABLE:
            try:
                print("[INFO] Loading CLIP model for prompt adherence...")
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                print("[OK] CLIP model loaded for prompt adherence scoring")
            except OSError as e:
                print(f"[WARN] Failed to download CLIP model (network/cache issue): {e}")
                print("[INFO] Quality scoring will continue without prompt adherence metrics")
            except Exception as e:
                print(f"[WARN] Failed to load CLIP model: {e}")
                print("[INFO] Quality scoring will continue without prompt adherence metrics")
        
        print("[OK] Quality metrics loaded")
    
    def _normalize_brisque(self, score: float) -> float:
        """Normalize BRISQUE score to 0-10 scale (inverted, higher is better).
        
        BRISQUE typically ranges 0-100, where lower is better.
        We invert and normalize to 0-10 scale.
        """
        # Clamp to reasonable range (0-100)
        score = max(0.0, min(100.0, score))
        # Invert and normalize: 100 becomes 0, 0 becomes 10
        normalized = 10.0 * (1.0 - score / 100.0)
        return normalized
    
    def _normalize_niqe(self, score: float) -> float:
        """Normalize NIQE score to 0-10 scale (inverted, higher is better).
        
        NIQE typically ranges 0-100, where lower is better.
        We invert and normalize to 0-10 scale.
        """
        # Clamp to reasonable range (0-100)
        score = max(0.0, min(100.0, score))
        # Invert and normalize: 100 becomes 0, 0 becomes 10
        normalized = 10.0 * (1.0 - score / 100.0)
        return normalized
    
    def _normalize_topiq(self, score: float) -> float:
        """Normalize TOPIQ score to 0-10 scale.
        
        TOPIQ typically ranges 0-1, where higher is better.
        """
        # Clamp to 0-1 range
        score = max(0.0, min(1.0, score))
        # Scale to 0-10
        normalized = score * 10.0
        return normalized
    
    def _normalize_laion_aes(self, score: float) -> float:
        """Normalize LAION aesthetic score to 0-10 scale.
        
        LAION aesthetic typically outputs in 0-10 range already.
        """
        # Clamp to 0-10 range
        normalized = max(0.0, min(10.0, score))
        return normalized
    
    def _normalize_clip(self, score: float) -> float:
        """Normalize CLIP score to 0-10 scale.
        
        CLIP similarity typically ranges 0-1, where higher is better.
        """
        # Clamp to 0-1 range
        score = max(0.0, min(1.0, score))
        # Scale to 0-10
        normalized = score * 10.0
        return normalized
    
    def _compute_clip_score(self, image_path: str, prompt: str) -> float:
        """Compute CLIP similarity score between image and prompt.
        
        Args:
            image_path: Path to the image
            prompt: Text prompt to compare against
            
        Returns:
            CLIP similarity score (0-1 range)
        """
        if not self.clip_model or not self.clip_processor:
            return 0.0
        
        try:
            image = Image.open(image_path).convert("RGB")
            
            inputs = self.clip_processor(
                text=[prompt],
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                # Get cosine similarity between image and text embeddings
                # logits_per_image is already the cosine similarity scaled by temperature
                # For a single text prompt, we take the similarity value
                similarity = outputs.logits_per_image[0, 0]
                
                # CLIP similarity is typically in range [-100, 100] due to temperature scaling
                # Normalize to 0-1 range using sigmoid-like function
                # Original CLIP uses temperature=100, so we scale accordingly
                normalized_score = torch.sigmoid(similarity / 100.0)
                
            return float(normalized_score)
        except Exception as e:
            print(f"[ERROR] Failed to compute CLIP score: {e}")
            return 0.0
    
    def _assign_grade(self, composite_score: float) -> str:
        """Assign letter grade based on composite score.
        
        Args:
            composite_score: Composite quality score (0-10)
            
        Returns:
            Letter grade (A, B, C, D, or F)
        """
        if composite_score >= 8.0:
            return "A"
        elif composite_score >= 6.5:
            return "B"
        elif composite_score >= 5.0:
            return "C"
        elif composite_score >= 3.0:
            return "D"
        else:
            return "F"
    
    def score_image(
        self,
        image_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Score image quality across multiple dimensions.
        
        Args:
            image_path: Path to the image file
            prompt: Optional text prompt for prompt adherence scoring
            
        Returns:
            Dictionary with quality scores and breakdown:
            {
                "composite_score": float,  # 0-10 overall score
                "grade": str,               # A, B, C, D, or F
                "technical": {
                    "brisque": float,       # 0-10 (normalized, higher=better)
                    "niqe": float           # 0-10 (normalized, higher=better)
                },
                "aesthetic": float,         # 0-10 LAION aesthetic score
                "prompt_adherence": {
                    "clip": float           # 0-10 CLIP similarity (if prompt provided)
                },
                "detail": float             # 0-10 TOPIQ score
            }
        """
        # Validate image path
        if not Path(image_path).exists():
            return {
                "error": f"Image file not found: {image_path}",
                "composite_score": 0.0,
                "grade": "F"
            }
        
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Compute technical quality
            brisque_raw = float(self.brisque(image_path))
            niqe_raw = float(self.niqe(image_path))
            
            brisque_norm = self._normalize_brisque(brisque_raw)
            niqe_norm = self._normalize_niqe(niqe_raw)
            
            technical_score = (0.70 * brisque_norm + 0.30 * niqe_norm)
            
            # Compute aesthetic quality
            aesthetic_score = 5.0  # Default if metric not available
            if self.laion_aes:
                try:
                    laion_raw = float(self.laion_aes(image_path))
                    aesthetic_score = self._normalize_laion_aes(laion_raw)
                except Exception as e:
                    print(f"[WARN] LAION aesthetic scoring failed: {e}")
            
            # Compute detail quality
            detail_score = 5.0  # Default if metric not available
            if self.topiq:
                try:
                    topiq_raw = float(self.topiq(image_path))
                    detail_score = self._normalize_topiq(topiq_raw)
                except Exception as e:
                    print(f"[WARN] TOPIQ scoring failed: {e}")
            
            # Compute prompt adherence (if prompt provided)
            prompt_adherence_score = None
            if prompt and self.clip_model:
                clip_raw = self._compute_clip_score(image_path, prompt)
                prompt_adherence_score = self._normalize_clip(clip_raw)
            
            # Compute composite score
            # Weights from QUALITY_SYSTEM.md:
            # - Technical: 30%
            # - Aesthetic: 25%
            # - Prompt adherence: 25% (if available, otherwise redistribute)
            # - Detail: 20%
            
            if prompt_adherence_score is not None:
                # All dimensions available
                composite_score = (
                    0.30 * technical_score +
                    0.25 * aesthetic_score +
                    0.25 * prompt_adherence_score +
                    0.20 * detail_score
                )
            else:
                # No prompt - redistribute weights
                composite_score = (
                    0.40 * technical_score +  # 30% -> 40%
                    0.35 * aesthetic_score +  # 25% -> 35%
                    0.25 * detail_score       # 20% -> 25%
                )
            
            # Assign grade
            grade = self._assign_grade(composite_score)
            
            # Build result
            result = {
                "composite_score": round(composite_score, 2),
                "grade": grade,
                "technical": {
                    "brisque": round(brisque_norm, 2),
                    "niqe": round(niqe_norm, 2),
                    "raw_brisque": round(brisque_raw, 2),
                    "raw_niqe": round(niqe_raw, 2)
                },
                "aesthetic": round(aesthetic_score, 2),
                "detail": round(detail_score, 2)
            }
            
            if prompt_adherence_score is not None:
                result["prompt_adherence"] = {
                    "clip": round(prompt_adherence_score, 2)
                }
            else:
                result["prompt_adherence"] = None
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Failed to score image: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "composite_score": 0.0,
                "grade": "F"
            }


def score_image(image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to score an image without creating a scorer instance.
    
    This creates a new scorer for each call, which is less efficient for batch
    scoring but simpler for single-use cases.
    
    Args:
        image_path: Path to the image file
        prompt: Optional text prompt for prompt adherence scoring
        
    Returns:
        Dictionary with quality scores (see QualityScorer.score_image)
    """
    if not PYIQA_AVAILABLE:
        return {
            "error": "pyiqa not available. Install with: pip install pyiqa",
            "composite_score": 0.0,
            "grade": "F"
        }
    
    scorer = QualityScorer()
    return scorer.score_image(image_path, prompt)


def main():
    """CLI entry point for quality scoring."""
    if len(sys.argv) < 2:
        print("Usage: python3 -m comfy_gen.quality <image_path> [prompt]")
        print("")
        print("Examples:")
        print("  python3 -m comfy_gen.quality output.png")
        print("  python3 -m comfy_gen.quality output.png \"a beautiful sunset\"")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not PYIQA_AVAILABLE:
        print("[ERROR] pyiqa not available. Install with: pip install pyiqa")
        sys.exit(1)
    
    print(f"[INFO] Scoring image: {image_path}")
    if prompt:
        print(f"[INFO] Prompt: {prompt}")
    
    result = score_image(image_path, prompt)
    
    # Check for errors
    if "error" in result:
        print(f"\n[ERROR] {result['error']}")
        sys.exit(1)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Quality Assessment Results")
    print(f"{'='*60}")
    print(f"\nOverall Grade: {result['grade']} (Composite Score: {result['composite_score']}/10)")
    print(f"\nDimension Breakdown:")
    print(f"  Technical Quality:    {result['technical']['brisque']:.2f}/10 (BRISQUE)")
    print(f"                        {result['technical']['niqe']:.2f}/10 (NIQE)")
    print(f"  Aesthetic Quality:    {result['aesthetic']:.2f}/10")
    print(f"  Detail Quality:       {result['detail']:.2f}/10")
    
    if result.get('prompt_adherence'):
        print(f"  Prompt Adherence:     {result['prompt_adherence']['clip']:.2f}/10 (CLIP)")
    
    print(f"\nGrade Scale:")
    print(f"  A (8.0-10.0): Production ready")
    print(f"  B (6.5-7.9):  Good, minor issues")
    print(f"  C (5.0-6.4):  Acceptable")
    print(f"  D (3.0-4.9):  Poor")
    print(f"  F (0.0-2.9):  Failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
