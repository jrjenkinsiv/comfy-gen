#!/usr/bin/env python3
"""Vision model content validation for prompt adherence.

This module uses vision-language models to validate that generated images
actually match the detailed prompt requirements, going beyond CLIP semantic
similarity to detect:
- Subject count mismatches
- Attribute errors (color, pose, clothing)
- Style mismatches
- Missing or extra elements

Uses BLIP-2 for image captioning and analysis. Can be upgraded to LLaVA
or Qwen2-VL via model-manager for better quality (see model-manager#40).
"""

import re
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import torch
    from PIL import Image
    from transformers import BlipProcessor, BlipForConditionalGeneration, BlipForQuestionAnswering

    BLIP_AVAILABLE = True
except ImportError:
    BLIP_AVAILABLE = False

# Model configuration - using BLIP (more stable than BLIP-2 on various platforms)
BLIP_CAPTION_MODEL = "Salesforce/blip-image-captioning-base"
BLIP_VQA_MODEL = "Salesforce/blip-vqa-base"

# Module-level model cache
_caption_model = None
_caption_processor = None
_vqa_model = None
_vqa_processor = None


def _get_device():
    """Get best available device."""
    if torch.cuda.is_available():
        return "cuda"
    # Skip MPS due to compatibility issues with some models
    return "cpu"


def _load_caption_model():
    """Load BLIP caption model (cached)."""
    global _caption_model, _caption_processor

    if _caption_model is None and BLIP_AVAILABLE:
        device = _get_device()
        print(f"[INFO] Loading BLIP caption model on {device}...")

        _caption_processor = BlipProcessor.from_pretrained(BLIP_CAPTION_MODEL)
        _caption_model = BlipForConditionalGeneration.from_pretrained(BLIP_CAPTION_MODEL)
        _caption_model = _caption_model.to(device)

        print("[OK] BLIP caption model loaded")

    return _caption_model, _caption_processor


def _load_vqa_model():
    """Load BLIP VQA model (cached)."""
    global _vqa_model, _vqa_processor

    if _vqa_model is None and BLIP_AVAILABLE:
        device = _get_device()
        print(f"[INFO] Loading BLIP VQA model on {device}...")

        _vqa_processor = BlipProcessor.from_pretrained(BLIP_VQA_MODEL)
        _vqa_model = BlipForQuestionAnswering.from_pretrained(BLIP_VQA_MODEL)
        _vqa_model = _vqa_model.to(device)

        print("[OK] BLIP VQA model loaded")

    return _vqa_model, _vqa_processor


def generate_caption(image_path: str) -> Optional[str]:
    """Generate a descriptive caption for an image.

    Args:
        image_path: Path to image file

    Returns:
        Generated caption string or None on error
    """
    if not BLIP_AVAILABLE:
        return None

    if not Path(image_path).exists():
        return None

    try:
        model, processor = _load_caption_model()
        if model is None:
            return None

        device = _get_device()
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, return_tensors="pt").to(device)

        generated_ids = model.generate(**inputs, max_new_tokens=100)
        caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        return caption
    except Exception as e:
        print(f"[ERROR] Caption generation failed: {e}")
        return None


def ask_about_image(image_path: str, question: str) -> Optional[str]:
    """Ask a question about an image using VQA.

    Args:
        image_path: Path to image file
        question: Question to ask about the image

    Returns:
        Answer string or None on error
    """
    if not BLIP_AVAILABLE:
        return None

    if not Path(image_path).exists():
        return None

    try:
        model, processor = _load_vqa_model()
        if model is None:
            return None

        device = _get_device()
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, question, return_tensors="pt").to(device)

        generated_ids = model.generate(**inputs, max_new_tokens=50)
        answer = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        return answer
    except Exception as e:
        print(f"[ERROR] VQA failed: {e}")
        return None


def extract_key_elements(prompt: str) -> dict[str, Any]:
    """Extract key validation elements from a prompt.

    Args:
        prompt: Generation prompt

    Returns:
        Dictionary with extracted elements:
        - subject_count: Expected number of main subjects
        - colors: List of mentioned colors
        - subject_type: Type of subject (person, animal, object, scene)
        - attributes: List of descriptive attributes
    """
    prompt_lower = prompt.lower()

    # Subject count patterns
    count = 1  # default
    if re.search(r"\b(solo|single|one|1)\s*(person|woman|man|girl|boy|figure)", prompt_lower):
        count = 1
    elif re.search(r"\b(two|2|pair|couple)\s*(people|women|men|persons|girls|boys|figures)", prompt_lower):
        count = 2
    elif re.search(r"\b(three|3)\s*(people|women|men|persons)", prompt_lower):
        count = 3
    elif re.search(r"\b(group|crowd|many|multiple|several)\b", prompt_lower):
        count = -1  # indeterminate

    # Colors
    color_pattern = r"\b(red|blue|green|yellow|orange|purple|pink|black|white|brown|gray|grey|golden|silver)\b"
    colors = list(set(re.findall(color_pattern, prompt_lower)))

    # Subject type
    subject_type = "unknown"
    if re.search(r"\b(woman|women|man|men|person|people|girl|girls|boy|boys|portrait|figure|figures)\b", prompt_lower):
        subject_type = "person"
    elif re.search(r"\b(cat|dog|animal|horse|bird|pet)\b", prompt_lower):
        subject_type = "animal"
    elif re.search(r"\b(car|building|house|object|item|thing)\b", prompt_lower):
        subject_type = "object"
    elif re.search(r"\b(landscape|scene|view|background|sky|mountain|forest|city)\b", prompt_lower):
        subject_type = "scene"

    # Key attributes (clothing, poses, accessories)
    attributes = []
    attribute_patterns = [
        r"\b(standing|sitting|lying|walking|running|dancing)\b",
        r"\b(dress|shirt|pants|suit|bikini|nude|naked|clothed)\b",
        r"\b(long hair|short hair|blonde|brunette|redhead)\b",
        r"\b(smiling|serious|happy|sad|angry)\b",
        r"\b(indoors|outdoors|studio|street|nature)\b",
    ]
    for pattern in attribute_patterns:
        matches = re.findall(pattern, prompt_lower)
        attributes.extend(matches)

    return {"subject_count": count, "colors": colors, "subject_type": subject_type, "attributes": list(set(attributes))}


def validate_content(
    image_path: str,
    prompt: str,
    check_subject_count: bool = True,
    check_colors: bool = True,
    check_attributes: bool = True,
) -> dict[str, Any]:
    """Validate image content against prompt requirements.

    Uses BLIP-2 VQA to check if the generated image matches the prompt.

    Args:
        image_path: Path to generated image
        prompt: Original generation prompt
        check_subject_count: Whether to validate subject count
        check_colors: Whether to validate mentioned colors
        check_attributes: Whether to validate key attributes

    Returns:
        Dictionary with validation results:
        - valid: Overall validation passed
        - caption: Generated image description
        - checks: Individual check results
        - issues: List of detected issues
        - reason: Human-readable summary
    """
    if not BLIP_AVAILABLE:
        return {
            "valid": True,  # Pass if VLM unavailable
            "reason": "VLM unavailable - validation skipped",
            "error": "BLIP-2 not available. Install with: pip install transformers torch",
        }

    if not Path(image_path).exists():
        return {"valid": False, "reason": f"Image not found: {image_path}", "error": "file_not_found"}

    # Extract expected elements from prompt
    expected = extract_key_elements(prompt)

    # Generate caption for context
    caption = generate_caption(image_path)

    checks = {}
    issues = []

    # Check subject count
    if check_subject_count and expected["subject_count"] > 0:
        if expected["subject_type"] == "person":
            answer = ask_about_image(image_path, "How many people are in this image?")
            if answer:
                # Parse count from answer
                detected_count = None
                answer_lower = answer.lower()
                if any(w in answer_lower for w in ["one", "1", "single", "a person", "one person"]):
                    detected_count = 1
                elif any(w in answer_lower for w in ["two", "2", "pair", "couple"]):
                    detected_count = 2
                elif any(w in answer_lower for w in ["three", "3"]):
                    detected_count = 3
                elif any(w in answer_lower for w in ["no", "none", "zero", "0"]):
                    detected_count = 0
                elif any(w in answer_lower for w in ["many", "several", "multiple", "group"]):
                    detected_count = -1  # Multiple

                checks["subject_count"] = {
                    "expected": expected["subject_count"],
                    "detected": detected_count,
                    "answer": answer,
                    "passed": detected_count is None
                    or detected_count == expected["subject_count"]
                    or (expected["subject_count"] == -1 and detected_count and detected_count > 1),
                }

                if not checks["subject_count"]["passed"]:
                    issues.append(
                        f"Subject count mismatch: expected {expected['subject_count']}, detected {detected_count}"
                    )

    # Check colors
    if check_colors and expected["colors"]:
        color_checks = {}
        for color in expected["colors"][:3]:  # Check up to 3 colors
            answer = ask_about_image(image_path, f"Is there anything {color} in this image?")
            if answer:
                # Check for positive response
                answer_lower = answer.lower()
                found = any(w in answer_lower for w in ["yes", "there is", "the", color])
                found = found and not any(w in answer_lower for w in ["no", "not", "isn't", "aren't"])
                color_checks[color] = {"found": found, "answer": answer}
                if not found:
                    issues.append(f"Expected color '{color}' not clearly visible")

        checks["colors"] = color_checks

    # Check key attributes
    if check_attributes and expected["attributes"]:
        attr_checks = {}
        for attr in expected["attributes"][:3]:  # Check up to 3 attributes
            answer = ask_about_image(image_path, f"Is the subject {attr}?")
            if answer:
                answer_lower = answer.lower()
                found = "yes" in answer_lower or attr in answer_lower
                found = found and "no" not in answer_lower.split()[:2]  # Check first 2 words for "no"
                attr_checks[attr] = {"found": found, "answer": answer}
                if not found:
                    issues.append(f"Expected attribute '{attr}' not detected")

        checks["attributes"] = attr_checks

    # Determine overall validity
    # Fail if subject count is wrong (critical), warn on colors/attributes
    critical_issues = [i for i in issues if "Subject count" in i]
    valid = len(critical_issues) == 0

    # Build reason
    if valid and not issues:
        reason = "Content validation passed - image matches prompt"
    elif valid and issues:
        reason = f"Content validation passed with warnings: {'; '.join(issues)}"
    else:
        reason = f"Content validation failed: {'; '.join(critical_issues)}"

    return {
        "valid": valid,
        "caption": caption,
        "expected": expected,
        "checks": checks,
        "issues": issues,
        "reason": reason,
    }


# CLI for testing
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python content_validator.py <image_path> "<prompt>"')
        print("")
        print("Examples:")
        print('  python content_validator.py image.png "solo woman in red dress"')
        print('  python content_validator.py photo.jpg "two men walking in park"')
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]

    print(f"\nValidating: {image_path}")
    print(f"Prompt: {prompt}")
    print("-" * 50)

    result = validate_content(image_path, prompt)

    print(f"\nCaption: {result.get('caption', 'N/A')}")
    print(f"\nExpected elements:")
    expected = result.get("expected", {})
    print(f"  Subject count: {expected.get('subject_count', 'N/A')}")
    print(f"  Subject type: {expected.get('subject_type', 'N/A')}")
    print(f"  Colors: {', '.join(expected.get('colors', [])) or 'none'}")
    print(f"  Attributes: {', '.join(expected.get('attributes', [])) or 'none'}")

    print(f"\nChecks:")
    for check_name, check_result in result.get("checks", {}).items():
        print(f"  {check_name}: {check_result}")

    print(f"\nIssues: {result.get('issues', [])}")
    print(f"\nResult: {'PASSED' if result['valid'] else 'FAILED'}")
    print(f"Reason: {result['reason']}")
