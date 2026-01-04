#!/usr/bin/env python3
"""Image validation module using CLIP-based semantic similarity.

This module provides functionality to validate generated images against prompts
using CLIP (Contrastive Language-Image Pre-training) to compute semantic similarity.
"""

import sys
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False


class ImageValidator:
    """Validates images using CLIP-based semantic similarity."""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """Initialize the validator with a CLIP model.
        
        Args:
            model_name: HuggingFace model identifier for CLIP
        """
        if not CLIP_AVAILABLE:
            raise ImportError(
                "CLIP validation requires 'transformers' and 'Pillow'. "
                "Install with: pip install transformers Pillow"
            )
        
        print(f"[INFO] Loading CLIP model: {model_name}")
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()
        
        # Move to GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        print(f"[INFO] CLIP model loaded on {self.device}")
    
    def validate_image(
        self,
        image_path: str,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        threshold: float = 0.25
    ) -> Dict[str, Any]:
        """Validate an image against positive and negative prompts.
        
        Args:
            image_path: Path to the image file or URL
            positive_prompt: The prompt the image should match
            negative_prompt: Optional prompt the image should NOT match
            threshold: Minimum CLIP score for positive prompt (0-1)
        
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'positive_score': float,
                'negative_score': float (if negative_prompt provided),
                'threshold': float,
                'diagnostics': str
            }
        """
        try:
            # Load image
            if image_path.startswith("http"):
                import requests
                from io import BytesIO
                response = requests.get(image_path)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            else:
                image = Image.open(image_path)
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Compute positive similarity
            positive_score = self._compute_similarity(image, positive_prompt)
            
            # Compute negative similarity if provided
            negative_score = None
            if negative_prompt:
                negative_score = self._compute_similarity(image, negative_prompt)
            
            # Determine validity
            valid = positive_score >= threshold
            if negative_score is not None:
                # Image should not match negative prompt strongly
                valid = valid and (negative_score < positive_score)
            
            # Generate diagnostics
            diagnostics = self._generate_diagnostics(
                positive_score, negative_score, threshold, valid
            )
            
            return {
                'valid': valid,
                'positive_score': round(positive_score, 3),
                'negative_score': round(negative_score, 3) if negative_score is not None else None,
                'threshold': threshold,
                'diagnostics': diagnostics
            }
            
        except Exception as e:
            return {
                'valid': False,
                'positive_score': 0.0,
                'negative_score': None,
                'threshold': threshold,
                'diagnostics': f"Validation error: {str(e)}"
            }
    
    def _compute_similarity(self, image: Image.Image, text: str) -> float:
        """Compute CLIP similarity between image and text.
        
        Args:
            image: PIL Image
            text: Text prompt
        
        Returns:
            Similarity score (0-1)
        """
        with torch.no_grad():
            inputs = self.processor(
                text=[text],
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get embeddings
            outputs = self.model(**inputs)
            
            # Compute cosine similarity
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)
            
            return probs[0][0].item()
    
    def _generate_diagnostics(
        self,
        positive_score: float,
        negative_score: Optional[float],
        threshold: float,
        valid: bool
    ) -> str:
        """Generate human-readable diagnostics.
        
        Args:
            positive_score: CLIP score for positive prompt
            negative_score: CLIP score for negative prompt (if any)
            threshold: Validation threshold
            valid: Whether validation passed
        
        Returns:
            Diagnostic string
        """
        if valid:
            msg = f"[OK] Image matches prompt (score: {positive_score:.3f} >= {threshold})"
            if negative_score is not None:
                msg += f", low negative score ({negative_score:.3f})"
            return msg
        else:
            if positive_score < threshold:
                msg = f"[WARN] Low positive match: {positive_score:.3f} < {threshold}"
            elif negative_score is not None and negative_score >= positive_score:
                msg = f"[WARN] Negative prompt score ({negative_score:.3f}) >= positive ({positive_score:.3f})"
            else:
                msg = "[WARN] Validation failed"
            return msg


def validate_image(
    image_path: str,
    positive_prompt: str,
    negative_prompt: Optional[str] = None,
    threshold: float = 0.25
) -> Dict[str, Any]:
    """Convenience function to validate an image.
    
    Args:
        image_path: Path to the image file or URL
        positive_prompt: The prompt the image should match
        negative_prompt: Optional prompt the image should NOT match
        threshold: Minimum CLIP score for positive prompt (0-1)
    
    Returns:
        Dictionary with validation results
    """
    validator = ImageValidator()
    return validator.validate_image(image_path, positive_prompt, negative_prompt, threshold)
