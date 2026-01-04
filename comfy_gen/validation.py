"""Image validation using CLIP for semantic similarity checking.

This module provides automated validation of generated images against prompts
using CLIP (Contrastive Language-Image Pre-training) to compute semantic similarity.
"""

import sys
from typing import Dict, Optional
from io import BytesIO

try:
    import requests
    from PIL import Image
    import torch
    from transformers import CLIPProcessor, CLIPModel
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class ImageValidator:
    """Validates generated images using CLIP semantic similarity."""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """Initialize the validator with a CLIP model.
        
        Args:
            model_name: HuggingFace model identifier for CLIP
        """
        if not HAS_DEPS:
            raise RuntimeError(
                "Missing dependencies. Install with: pip install transformers pillow torch"
            )
        
        print(f"[INFO] Loading CLIP model: {model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        print(f"[OK] CLIP model loaded on {self.device}")
    
    def validate_image(
        self,
        image_url: str,
        positive_prompt: str,
        negative_prompt: str = "",
        threshold: float = 0.25
    ) -> Dict:
        """Validate an image against prompts using CLIP.
        
        Args:
            image_url: URL or local path to the image
            positive_prompt: Expected content description
            negative_prompt: Content to avoid
            threshold: Minimum similarity score (0-1) to pass validation
        
        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "clip_score": float,
                "negative_score": float,
                "threshold": float,
                "diagnostics": str
            }
        """
        try:
            # Load image
            if image_url.startswith("http://") or image_url.startswith("https://"):
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            else:
                image = Image.open(image_url)
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Prepare inputs
            inputs = self.processor(
                text=[positive_prompt, negative_prompt] if negative_prompt else [positive_prompt],
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Extract scores
            positive_score = float(probs[0][0])
            negative_score = float(probs[0][1]) if negative_prompt else 0.0
            
            # Determine validity
            valid = positive_score >= threshold
            
            diagnostics = []
            if positive_score < threshold:
                diagnostics.append(
                    f"Low CLIP similarity: {positive_score:.3f} < {threshold:.3f}"
                )
            if negative_prompt and negative_score > positive_score:
                diagnostics.append(
                    f"Negative prompt scored higher: {negative_score:.3f} > {positive_score:.3f}"
                )
                valid = False
            
            return {
                "valid": valid,
                "clip_score": positive_score,
                "negative_score": negative_score,
                "threshold": threshold,
                "diagnostics": "; ".join(diagnostics) if diagnostics else "OK"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "clip_score": 0.0,
                "negative_score": 0.0,
                "threshold": threshold,
                "diagnostics": f"Error: {str(e)}"
            }


def validate_image(
    image_url: str,
    positive_prompt: str,
    negative_prompt: str = "",
    threshold: float = 0.25
) -> Dict:
    """Convenience function to validate an image without creating a validator instance.
    
    This creates a new validator each time, which is less efficient for multiple validations.
    For batch validation, create an ImageValidator instance and reuse it.
    
    Args:
        image_url: URL or local path to the image
        positive_prompt: Expected content description
        negative_prompt: Content to avoid
        threshold: Minimum similarity score (0-1) to pass validation
    
    Returns:
        Dictionary with validation results
    """
    validator = ImageValidator()
    return validator.validate_image(image_url, positive_prompt, negative_prompt, threshold)


# For command-line testing
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python validation.py <image_url> <prompt> [negative_prompt] [threshold]")
        sys.exit(1)
    
    image_url = sys.argv[1]
    prompt = sys.argv[2]
    negative = sys.argv[3] if len(sys.argv) > 3 else ""
    threshold = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    
    result = validate_image(image_url, prompt, negative, threshold)
    print(f"\nValidation Results:")
    print(f"  Valid: {result['valid']}")
    print(f"  CLIP Score: {result['clip_score']:.3f}")
    print(f"  Negative Score: {result['negative_score']:.3f}")
    print(f"  Threshold: {result['threshold']:.3f}")
    print(f"  Diagnostics: {result['diagnostics']}")
    
    sys.exit(0 if result['valid'] else 1)
