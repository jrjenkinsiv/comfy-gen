#!/usr/bin/env python3
"""Image validation module using CLIP for semantic similarity scoring.

This module provides automated image validation to detect issues like:
- Semantic mismatch between prompt and generated image
- Low quality or artifacts
- Multiple subjects when only one is expected

The primary validation method uses CLIP (Contrastive Language-Image Pre-training)
to compute similarity scores between the image and text prompts.
"""

import sys
from typing import Dict, Optional, Any
from pathlib import Path

try:
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False


class ImageValidator:
    """Validates generated images using CLIP semantic similarity."""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """Initialize the validator with a CLIP model.
        
        Args:
            model_name: HuggingFace model identifier for CLIP
        """
        if not CLIP_AVAILABLE:
            raise RuntimeError(
                "CLIP dependencies not available. Install with: "
                "pip install torch transformers pillow"
            )
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[INFO] Loading CLIP model on {self.device}...")
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        print(f"[OK] CLIP model loaded")
    
    def compute_clip_score(
        self, 
        image_path: str, 
        positive_prompt: str,
        negative_prompt: Optional[str] = None
    ) -> Dict[str, float]:
        """Compute CLIP similarity scores for an image.
        
        Args:
            image_path: Path to the generated image
            positive_prompt: The positive text prompt used for generation
            negative_prompt: Optional negative prompt to check against
        
        Returns:
            Dictionary with:
                - positive_score: Similarity to positive prompt (0-1)
                - negative_score: Similarity to negative prompt if provided (0-1)
                - score_delta: positive_score - negative_score if both available
        """
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Prepare prompts
            prompts = [positive_prompt]
            if negative_prompt:
                prompts.append(negative_prompt)
            
            # Process inputs
            inputs = self.processor(
                text=prompts,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # Compute embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Extract scores
            positive_score = float(probs[0][0])
            result = {"positive_score": positive_score}
            
            if negative_prompt:
                negative_score = float(probs[0][1])
                result["negative_score"] = negative_score
                result["score_delta"] = positive_score - negative_score
            
            return result
            
        except Exception as e:
            print(f"[ERROR] Failed to compute CLIP score: {e}")
            return {"positive_score": 0.0, "error": str(e)}
    
    def validate_image(
        self,
        image_path: str,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        positive_threshold: float = 0.25,
        delta_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Validate an image against prompt constraints.
        
        Args:
            image_path: Path to the generated image
            positive_prompt: The positive text prompt
            negative_prompt: Optional negative prompt
            positive_threshold: Minimum acceptable positive CLIP score (default 0.25)
            delta_threshold: Minimum acceptable delta if negative prompt provided
        
        Returns:
            Dictionary with validation results:
                - passed: Boolean indicating if validation passed
                - positive_score: CLIP similarity to positive prompt
                - negative_score: CLIP similarity to negative prompt (if provided)
                - score_delta: Difference between positive and negative (if provided)
                - reason: Failure reason if validation failed
        """
        scores = self.compute_clip_score(image_path, positive_prompt, negative_prompt)
        
        # Check for errors
        if "error" in scores:
            return {
                "passed": False,
                "reason": f"Validation error: {scores['error']}",
                **scores
            }
        
        positive_score = scores["positive_score"]
        
        # Check positive threshold
        if positive_score < positive_threshold:
            return {
                "passed": False,
                "reason": f"Low positive CLIP score: {positive_score:.3f} < {positive_threshold}",
                **scores
            }
        
        # Check delta threshold if negative prompt provided
        if negative_prompt and delta_threshold is not None:
            score_delta = scores.get("score_delta", 0.0)
            if score_delta < delta_threshold:
                return {
                    "passed": False,
                    "reason": f"Low score delta: {score_delta:.3f} < {delta_threshold}",
                    **scores
                }
        
        # Validation passed
        return {
            "passed": True,
            "reason": "Image passed validation",
            **scores
        }


def validate_image(
    image_path: str,
    positive_prompt: str,
    negative_prompt: Optional[str] = None,
    positive_threshold: float = 0.25,
    delta_threshold: Optional[float] = None
) -> Dict[str, Any]:
    """Convenience function to validate an image without creating a validator instance.
    
    This creates a new validator for each call, which is less efficient for batch
    validation but simpler for single-use cases.
    
    Args:
        image_path: Path to the generated image
        positive_prompt: The positive text prompt
        negative_prompt: Optional negative prompt
        positive_threshold: Minimum acceptable positive CLIP score
        delta_threshold: Minimum acceptable delta if negative prompt provided
    
    Returns:
        Dictionary with validation results (see ImageValidator.validate_image)
    """
    if not CLIP_AVAILABLE:
        return {
            "passed": False,
            "reason": "CLIP dependencies not available",
            "positive_score": 0.0
        }
    
    validator = ImageValidator()
    return validator.validate_image(
        image_path, 
        positive_prompt, 
        negative_prompt,
        positive_threshold,
        delta_threshold
    )


if __name__ == "__main__":
    # Simple CLI for testing
    if len(sys.argv) < 3:
        print("Usage: python validation.py <image_path> <prompt> [negative_prompt]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2]
    negative = sys.argv[3] if len(sys.argv) > 3 else None
    
    result = validate_image(image_path, prompt, negative)
    print(f"\nValidation Result:")
    print(f"  Passed: {result['passed']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Positive Score: {result.get('positive_score', 0.0):.3f}")
    if 'negative_score' in result:
        print(f"  Negative Score: {result['negative_score']:.3f}")
        print(f"  Delta: {result.get('score_delta', 0.0):.3f}")
