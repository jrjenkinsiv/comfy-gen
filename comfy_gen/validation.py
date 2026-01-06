#!/usr/bin/env python3
"""Image validation module using CLIP for semantic similarity scoring.

This module provides automated image validation to detect issues like:
- Semantic mismatch between prompt and generated image
- Low quality or artifacts
- Multiple subjects when only one is expected
- Person count mismatch (using YOLO)

The primary validation method uses CLIP (Contrastive Language-Image Pre-training)
to compute similarity scores between the image and text prompts.

Person count validation uses YOLO for object detection to count people in images.
"""

import sys
import re
from typing import Dict, Optional, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    import torch as torch_type
else:
    torch_type = None  # type: ignore

try:
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel

    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# Constants for person detection
PERSON_TERMS = ("person", "people", "woman", "women", "man", "men", "individual", "subject")
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

# Module-level YOLO model cache
_yolo_model = None


def _get_yolo_model():
    """Get or create cached YOLO model instance."""
    global _yolo_model
    if _yolo_model is None and YOLO_AVAILABLE:
        _yolo_model = YOLO("yolov8n.pt")
    return _yolo_model


class ImageValidator:
    """Validates generated images using CLIP semantic similarity."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """Initialize the validator with a CLIP model.

        Args:
            model_name: HuggingFace model identifier for CLIP
        """
        if not CLIP_AVAILABLE:
            raise RuntimeError("CLIP dependencies not available. Install with: pip install torch transformers pillow")

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[INFO] Loading CLIP model on {self.device}...")
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        print(f"[OK] CLIP model loaded")

    def _chunk_prompt(self, prompt: str, max_chars: int = 250) -> list[str]:
        """Split a long prompt into chunks that fit within CLIP's token limit.

        CLIP has a 77-token limit. This function splits long prompts into
        manageable chunks that are processed separately and averaged.

        Args:
            prompt: The full text prompt
            max_chars: Maximum characters per chunk (conservative token estimate)

        Returns:
            List of prompt chunks
        """
        words = prompt.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            word_len = len(word) + 1  # +1 for space
            if current_length + word_len > max_chars and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_len
            else:
                current_chunk.append(word)
                current_length += word_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks if chunks else [prompt]

    def _get_text_embedding(self, prompt: str):
        """Get averaged text embedding for a prompt, handling long prompts via chunking.

        Args:
            prompt: Text prompt (can be longer than 77 tokens)

        Returns:
            Normalized text embedding tensor
        """
        chunks = self._chunk_prompt(prompt)

        if len(chunks) > 1:
            print(f"[INFO] Processing prompt in {len(chunks)} chunks (long prompt)")

        embeddings = []
        for chunk in chunks:
            inputs = self.processor(text=[chunk], return_tensors="pt", padding=True, truncation=True, max_length=77).to(
                self.device
            )

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                embeddings.append(text_features)

        # Average embeddings if multiple chunks
        if len(embeddings) > 1:
            avg_embedding = torch.stack(embeddings).mean(dim=0)
            avg_embedding = avg_embedding / avg_embedding.norm(dim=-1, keepdim=True)
            return avg_embedding
        else:
            return embeddings[0]

    def compute_clip_score(
        self, image_path: str, positive_prompt: str, negative_prompt: Optional[str] = None
    ) -> Dict[str, float]:
        """Compute CLIP similarity scores for an image.

        Handles long prompts by chunking them into 77-token segments,
        processing each separately, and averaging the embeddings.

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
            # Validate that the image file exists
            if not Path(image_path).exists():
                return {"positive_score": 0.0, "error": f"Image file not found: {image_path}"}

            # Load image
            image = Image.open(image_path).convert("RGB")

            # Get image embedding
            image_inputs = self.processor(images=image, return_tensors="pt").to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**image_inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

                # Get text embeddings (chunked for long prompts)
                positive_embedding = self._get_text_embedding(positive_prompt)

                # Compute cosine similarity for positive prompt
                positive_sim = (image_features @ positive_embedding.T).squeeze()
                # Transform cosine similarity [-1, 1] to probability-like score [0, 1]
                # Good matches typically have cosine sim of 0.2-0.35
                positive_score = float(torch.clamp((positive_sim + 1) / 2, 0.0, 1.0))

                result = {"positive_score": positive_score}

                if negative_prompt:
                    negative_embedding = self._get_text_embedding(negative_prompt)
                    negative_sim = (image_features @ negative_embedding.T).squeeze()
                    negative_score = float(torch.clamp((negative_sim + 1) / 2, 0.0, 1.0))
                    result["negative_score"] = negative_score
                    result["score_delta"] = positive_score - negative_score

            return result

        except Exception as e:
            print(f"[ERROR] Failed to compute CLIP score: {e}")
            import traceback

            traceback.print_exc()
            return {"positive_score": 0.0, "error": str(e)}

    def validate_image(
        self,
        image_path: str,
        positive_prompt: str,
        negative_prompt: Optional[str] = None,
        positive_threshold: float = 0.25,
        delta_threshold: Optional[float] = None,
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
            return {"passed": False, "reason": f"Validation error: {scores['error']}", **scores}

        positive_score = scores["positive_score"]

        # Check positive threshold
        if positive_score < positive_threshold:
            return {
                "passed": False,
                "reason": f"Low positive CLIP score: {positive_score:.3f} < {positive_threshold}",
                **scores,
            }

        # Check delta threshold if negative prompt provided
        if negative_prompt and delta_threshold is not None:
            score_delta = scores.get("score_delta", 0.0)
            if score_delta < delta_threshold:
                return {"passed": False, "reason": f"Low score delta: {score_delta:.3f} < {delta_threshold}", **scores}

        # Validation passed
        return {"passed": True, "reason": "Image passed validation", **scores}


def extract_expected_person_count(prompt: str) -> Optional[int]:
    """Extract expected person count from prompt using heuristics.

    Args:
        prompt: The text prompt

    Returns:
        Expected person count (int) or None if not specified

    Examples:
        "solo woman" -> 1
        "one person" -> 1
        "two women" -> 2
        "three people" -> 3
        "group of five" -> 5
    """
    # Normalize to lowercase for matching
    prompt_lower = prompt.lower()

    # Pattern 1: "solo" or "single" -> 1 person
    if re.search(r"\b(solo|single)\b", prompt_lower):
        return 1

    # Build pattern using person terms constant
    person_pattern = "|".join(PERSON_TERMS)

    # Pattern 2: Number words followed by person-related terms
    for word, count in NUMBER_WORDS.items():
        pattern = rf"\b{word}\s+({person_pattern})\b"
        if re.search(pattern, prompt_lower):
            return count

    # Pattern 3: Digit followed by person-related terms
    digit_match = re.search(rf"\b(\d+)\s+({person_pattern})\b", prompt_lower)
    if digit_match:
        return int(digit_match.group(1))

    # Pattern 4: "group of [number]"
    group_match = re.search(r"group\s+of\s+(\w+)", prompt_lower)
    if group_match:
        word = group_match.group(1)
        if word in NUMBER_WORDS:
            return NUMBER_WORDS[word]
        elif word.isdigit():
            return int(word)

    # No specific count found
    return None


def count_persons_yolo(image_path: str, confidence: float = 0.5) -> Dict[str, Any]:
    """Count persons in image using YOLO object detection.

    Uses cached YOLO model instance for efficiency across multiple calls.

    Args:
        image_path: Path to the image
        confidence: Minimum confidence threshold for detections (default: 0.5)

    Returns:
        Dictionary with:
            - person_count: Number of persons detected
            - detections: List of detection dicts with bbox, confidence
            - error: Error message if detection failed
    """
    if not YOLO_AVAILABLE:
        return {"person_count": None, "error": "YOLO not available. Install with: pip install ultralytics"}

    try:
        # Validate image exists
        if not Path(image_path).exists():
            return {"person_count": None, "error": f"Image file not found: {image_path}"}

        # Get cached model instance
        model = _get_yolo_model()
        if model is None:
            return {"person_count": None, "error": "Failed to load YOLO model"}

        # Run inference
        results = model(image_path, verbose=False)

        # COCO class ID for person is 0
        person_class_id = 0

        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                # Filter for person class and confidence threshold
                if cls == person_class_id and conf >= confidence:
                    detections.append(
                        {
                            "confidence": conf,
                            "bbox": box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                        }
                    )

        return {"person_count": len(detections), "detections": detections}

    except Exception as e:
        return {"person_count": None, "error": f"YOLO detection failed: {str(e)}"}


def validate_image(
    image_path: str,
    positive_prompt: str,
    negative_prompt: Optional[str] = None,
    positive_threshold: float = 0.25,
    delta_threshold: Optional[float] = None,
    validate_person_count: bool = False,
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
        validate_person_count: Whether to validate person count using YOLO

    Returns:
        Dictionary with validation results (see ImageValidator.validate_image)
    """
    if not CLIP_AVAILABLE:
        result = {"passed": False, "reason": "CLIP dependencies not available", "positive_score": 0.0}
    else:
        validator = ImageValidator()
        result = validator.validate_image(
            image_path, positive_prompt, negative_prompt, positive_threshold, delta_threshold
        )

    # Add person count validation if requested
    if validate_person_count:
        expected_count = extract_expected_person_count(positive_prompt)
        yolo_result = count_persons_yolo(image_path)

        # Add YOLO results to validation result
        result["person_count"] = yolo_result.get("person_count")
        result["expected_person_count"] = expected_count

        # Check if YOLO detection failed
        if "error" in yolo_result:
            result["person_count_error"] = yolo_result["error"]
            # Store warning in result instead of printing
            # The calling code in generate.py will handle displaying this
        elif expected_count is not None and yolo_result.get("person_count") is not None:
            # Validate count matches expectation
            actual_count = yolo_result["person_count"]
            if actual_count != expected_count:
                result["passed"] = False
                result["reason"] = f"Person count mismatch: expected {expected_count}, detected {actual_count}"

    return result


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
    if "negative_score" in result:
        print(f"  Negative Score: {result['negative_score']:.3f}")
        print(f"  Delta: {result.get('score_delta', 0.0):.3f}")
