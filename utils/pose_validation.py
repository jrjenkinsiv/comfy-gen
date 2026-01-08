#!/usr/bin/env python3
"""Pose estimation validation module using MediaPipe and YOLO.

This module provides skeleton-based validation for generated images:
- Detects poses using MediaPipe Pose Landmarker (Tasks API)
- Validates skeleton coherence (all major joints visible/connected)
- Supports multi-person detection via YOLO + MediaPipe combination
- Reports pose quality metrics

Multi-person support:
1. YOLO detects all persons in the image (bounding boxes)
2. MediaPipe runs pose estimation on each detected person crop
3. Results aggregated with per-person coherence scores
"""

import sys
import urllib.request
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision

    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# MediaPipe pose landmark indices for key body joints (Tasks API uses same indices)
# These are the minimum joints that should be visible for a coherent skeleton
KEY_LANDMARKS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_knee": 25,
    "right_knee": 26,
}

# Minimum visibility threshold for a landmark to be considered "present"
DEFAULT_VISIBILITY_THRESHOLD = 0.5

# YOLO confidence threshold for person detection
DEFAULT_PERSON_CONFIDENCE = 0.5

# Padding ratio when cropping person regions for pose estimation
CROP_PADDING_RATIO = 0.1

# Model file for MediaPipe Pose Landmarker
POSE_LANDMARKER_MODEL = "pose_landmarker_lite.task"
POSE_LANDMARKER_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

# Module-level model caches
_yolo_model = None
_pose_landmarker = None


def _get_yolo_model():
    """Get or create cached YOLO model instance."""
    global _yolo_model
    if _yolo_model is None and YOLO_AVAILABLE:
        _yolo_model = YOLO("yolov8n.pt")
    return _yolo_model


def _download_pose_model():
    """Download MediaPipe pose landmarker model if not present."""
    # Store in user's cache directory
    cache_dir = Path.home() / ".cache" / "comfy-gen" / "models"
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / POSE_LANDMARKER_MODEL

    if not model_path.exists():
        print(f"[INFO] Downloading MediaPipe pose model to {model_path}...")
        urllib.request.urlretrieve(POSE_LANDMARKER_URL, model_path)
        print("[OK] Model downloaded successfully")

    return str(model_path)


def _get_pose_landmarker():
    """Get or create cached MediaPipe Pose Landmarker instance."""
    global _pose_landmarker
    if _pose_landmarker is None and MEDIAPIPE_AVAILABLE:
        model_path = _download_pose_model()
        base_options = mp_tasks.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            num_poses=1,  # We run on cropped single-person images
        )
        _pose_landmarker = vision.PoseLandmarker.create_from_options(options)
    return _pose_landmarker


def detect_persons_yolo(image: np.ndarray, confidence: float = DEFAULT_PERSON_CONFIDENCE) -> list[dict]:
    """Detect all persons in image using YOLO.

    Args:
        image: OpenCV image (BGR format)
        confidence: Minimum confidence threshold

    Returns:
        List of person detections with bounding boxes:
        [{'bbox': [x1, y1, x2, y2], 'confidence': float}, ...]
    """
    if not YOLO_AVAILABLE:
        return []

    model = _get_yolo_model()
    if model is None:
        return []

    results = model(image, verbose=False)

    persons = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            # COCO class ID 0 = person
            if cls == 0 and conf >= confidence:
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                persons.append({"bbox": bbox, "confidence": conf})

    return persons


def crop_person_region(
    image: np.ndarray, bbox: list[float], padding_ratio: float = CROP_PADDING_RATIO
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Crop a person region from image with padding.

    Args:
        image: Full image (BGR)
        bbox: Bounding box [x1, y1, x2, y2]
        padding_ratio: Extra padding around bbox (fraction of bbox size)

    Returns:
        Tuple of (cropped_image, adjusted_bbox)
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox

    # Calculate padding
    box_w = x2 - x1
    box_h = y2 - y1
    pad_w = int(box_w * padding_ratio)
    pad_h = int(box_h * padding_ratio)

    # Apply padding with bounds checking
    x1_padded = max(0, int(x1) - pad_w)
    y1_padded = max(0, int(y1) - pad_h)
    x2_padded = min(w, int(x2) + pad_w)
    y2_padded = min(h, int(y2) + pad_h)

    cropped = image[y1_padded:y2_padded, x1_padded:x2_padded]

    return cropped, (x1_padded, y1_padded, x2_padded, y2_padded)


def estimate_pose_single(
    image: np.ndarray, visibility_threshold: float = DEFAULT_VISIBILITY_THRESHOLD
) -> dict[str, Any]:
    """Run pose estimation on a single-person image.

    Args:
        image: OpenCV image (BGR format) containing one person
        visibility_threshold: Minimum visibility for landmark to count as present

    Returns:
        Dictionary with pose results:
        - detected: bool - whether a pose was detected
        - landmarks: list of landmark dicts if detected
        - coherent: bool - whether skeleton is coherent (key joints visible)
        - coherence_score: float - fraction of key landmarks visible (0-1)
        - visible_landmarks: list of visible landmark names
        - missing_landmarks: list of missing landmark names
    """
    if not MEDIAPIPE_AVAILABLE:
        return {"detected": False, "error": "MediaPipe not available. Install with: pip install mediapipe"}

    landmarker = _get_pose_landmarker()
    if landmarker is None:
        return {"detected": False, "error": "Failed to initialize MediaPipe pose detector"}

    # Convert BGR to RGB for MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Create MediaPipe Image from numpy array
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

    # Run pose detection
    results = landmarker.detect(mp_image)

    if not results.pose_landmarks or len(results.pose_landmarks) == 0:
        return {
            "detected": False,
            "coherent": False,
            "coherence_score": 0.0,
            "visible_landmarks": [],
            "missing_landmarks": list(KEY_LANDMARKS.keys()),
        }

    # Get first (and only) pose - we run on cropped single-person images
    pose_landmarks = results.pose_landmarks[0]

    # Extract landmarks
    landmarks = []
    for i, lm in enumerate(pose_landmarks):
        landmarks.append(
            {
                "index": i,
                "x": lm.x,
                "y": lm.y,
                "z": lm.z,
                "visibility": lm.visibility if hasattr(lm, "visibility") else lm.presence,
            }
        )

    # Check coherence - are key landmarks visible?
    visible = []
    missing = []

    for name, idx in KEY_LANDMARKS.items():
        if idx < len(landmarks):
            vis = landmarks[idx].get("visibility", 0)
            if vis >= visibility_threshold:
                visible.append(name)
            else:
                missing.append(name)
        else:
            missing.append(name)

    coherence_score = len(visible) / len(KEY_LANDMARKS) if KEY_LANDMARKS else 0.0

    # Consider coherent if at least 60% of key landmarks are visible
    # and core joints (shoulders + hips) are present
    core_joints = {"left_shoulder", "right_shoulder", "left_hip", "right_hip"}
    core_visible = core_joints.issubset(set(visible))
    coherent = coherence_score >= 0.6 and core_visible

    return {
        "detected": True,
        "landmarks": landmarks,
        "coherent": coherent,
        "coherence_score": coherence_score,
        "visible_landmarks": visible,
        "missing_landmarks": missing,
        "core_joints_visible": core_visible,
    }


def validate_pose(
    image_path: str,
    expected_persons: Optional[int] = None,
    visibility_threshold: float = DEFAULT_VISIBILITY_THRESHOLD,
    person_confidence: float = DEFAULT_PERSON_CONFIDENCE,
) -> dict[str, Any]:
    """Validate pose estimation for an image with multi-person support.

    This is the main entry point for pose validation:
    1. Uses YOLO to detect all persons
    2. Runs MediaPipe pose estimation on each person
    3. Validates coherence and person count

    Args:
        image_path: Path to image file
        expected_persons: Expected number of persons (None = no validation)
        visibility_threshold: Min visibility for landmarks
        person_confidence: YOLO confidence threshold for person detection

    Returns:
        Dictionary with validation results:
        - valid: bool - overall validation passed
        - person_count: int - number of persons detected
        - expected_count: int or None - expected count if specified
        - persons: list of per-person pose results
        - all_coherent: bool - all detected persons have coherent poses
        - coherent_count: int - number of persons with coherent poses
        - reason: str - human-readable result description
    """
    # Validate dependencies
    if not MEDIAPIPE_AVAILABLE:
        return {
            "valid": False,
            "error": "MediaPipe not available. Install with: pip install mediapipe",
            "person_count": None,
        }

    # Load image
    if not Path(image_path).exists():
        return {"valid": False, "error": f"Image file not found: {image_path}", "person_count": None}

    image = cv2.imread(image_path)
    if image is None:
        return {"valid": False, "error": f"Failed to load image: {image_path}", "person_count": None}

    # Step 1: Detect persons with YOLO
    if YOLO_AVAILABLE:
        persons_detected = detect_persons_yolo(image, person_confidence)
    else:
        # Fallback: treat entire image as single person
        h, w = image.shape[:2]
        persons_detected = [{"bbox": [0, 0, w, h], "confidence": 1.0}]

    person_count = len(persons_detected)

    # Handle no persons detected
    if person_count == 0:
        valid = expected_persons == 0 if expected_persons is not None else True
        return {
            "valid": valid,
            "person_count": 0,
            "expected_count": expected_persons,
            "persons": [],
            "all_coherent": True,  # Vacuously true
            "coherent_count": 0,
            "reason": "No persons detected in image" if not valid else "No persons expected or detected",
        }

    # Step 2: Run pose estimation on each detected person
    person_results = []
    coherent_count = 0

    for i, person in enumerate(persons_detected):
        bbox = person["bbox"]

        # Crop person region
        cropped, adjusted_bbox = crop_person_region(image, bbox)

        # Run pose estimation on crop
        pose_result = estimate_pose_single(cropped, visibility_threshold)

        # Add metadata
        pose_result["person_index"] = i
        pose_result["bbox"] = bbox
        pose_result["detection_confidence"] = person["confidence"]

        if pose_result.get("coherent", False):
            coherent_count += 1

        person_results.append(pose_result)

    # Step 3: Validate results
    all_coherent = coherent_count == person_count
    count_matches = expected_persons is None or person_count == expected_persons

    # Determine overall validity
    valid = count_matches and all_coherent

    # Build reason string
    reasons = []
    if not count_matches:
        reasons.append(f"Person count mismatch: expected {expected_persons}, detected {person_count}")
    if not all_coherent:
        incoherent = person_count - coherent_count
        reasons.append(f"{incoherent} person(s) have incoherent poses (missing key joints)")

    if valid:
        reason = f"Validation passed: {person_count} person(s) with coherent poses"
    else:
        reason = "; ".join(reasons)

    return {
        "valid": valid,
        "person_count": person_count,
        "expected_count": expected_persons,
        "persons": person_results,
        "all_coherent": all_coherent,
        "coherent_count": coherent_count,
        "reason": reason,
    }


def visualize_pose(
    image_path: str, output_path: Optional[str] = None, draw_landmarks: bool = True, draw_bboxes: bool = True
) -> Optional[np.ndarray]:
    """Visualize pose estimation results on image.

    Args:
        image_path: Path to input image
        output_path: Path to save visualization (None = don't save)
        draw_landmarks: Whether to draw pose landmarks
        draw_bboxes: Whether to draw person bounding boxes

    Returns:
        Annotated image as numpy array, or None on error
    """
    if not MEDIAPIPE_AVAILABLE:
        print("[ERROR] MediaPipe not available for visualization")
        return None

    image = cv2.imread(image_path)
    if image is None:
        print(f"[ERROR] Failed to load image: {image_path}")
        return None

    # Get pose validation results
    results = validate_pose(image_path)

    if "error" in results:
        print(f"[ERROR] {results['error']}")
        return None

    # Draw on image

    for person in results.get("persons", []):
        bbox = person.get("bbox", [])

        # Draw bounding box
        if draw_bboxes and bbox:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            color = (0, 255, 0) if person.get("coherent", False) else (0, 0, 255)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

            # Add label
            label = f"Person {person['person_index']}: {'OK' if person.get('coherent') else 'INCOHERENT'}"
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Draw pose landmarks (simplified - just key points)
        if draw_landmarks and person.get("detected", False):
            landmarks = person.get("landmarks", [])
            h, w = image.shape[:2]

            # Draw key landmarks as circles
            for _name, idx in KEY_LANDMARKS.items():
                if idx < len(landmarks):
                    lm = landmarks[idx]
                    if lm["visibility"] >= DEFAULT_VISIBILITY_THRESHOLD:
                        # Adjust coordinates back to full image
                        if bbox:
                            crop_x1, crop_y1, crop_x2, crop_y2 = [int(v) for v in bbox]
                            crop_w = crop_x2 - crop_x1
                            crop_h = crop_y2 - crop_y1
                            px = int(crop_x1 + lm["x"] * crop_w)
                            py = int(crop_y1 + lm["y"] * crop_h)
                        else:
                            px = int(lm["x"] * w)
                            py = int(lm["y"] * h)

                        cv2.circle(image, (px, py), 5, (255, 0, 255), -1)

    # Add summary text
    summary = f"Persons: {results['person_count']} | Coherent: {results['coherent_count']}"
    cv2.putText(image, summary, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Save if output path provided
    if output_path:
        cv2.imwrite(output_path, image)
        print(f"[OK] Saved visualization to {output_path}")

    return image


# CLI for testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pose_validation.py <image_path> [expected_persons] [--visualize output.png]")
        print("")
        print("Examples:")
        print("  python pose_validation.py image.png")
        print("  python pose_validation.py image.png 1")
        print("  python pose_validation.py image.png 2 --visualize annotated.png")
        sys.exit(1)

    image_path = sys.argv[1]
    expected = None
    viz_output = None

    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--visualize" and i + 1 < len(sys.argv):
            viz_output = sys.argv[i + 1]
            i += 2
        elif sys.argv[i].isdigit():
            expected = int(sys.argv[i])
            i += 1
        else:
            i += 1

    # Run validation
    result = validate_pose(image_path, expected_persons=expected)

    print("\nPose Validation Result:")
    print(f"  Valid: {result.get('valid', False)}")
    print(f"  Person Count: {result.get('person_count', 0)}")
    if result.get("expected_count") is not None:
        print(f"  Expected Count: {result['expected_count']}")
    print(f"  Coherent Poses: {result.get('coherent_count', 0)}/{result.get('person_count', 0)}")
    print(f"  Reason: {result.get('reason', 'N/A')}")

    # Per-person details
    for person in result.get("persons", []):
        print(f"\n  Person {person['person_index']}:")
        print(f"    Detected: {person.get('detected', False)}")
        print(f"    Coherent: {person.get('coherent', False)}")
        print(f"    Coherence Score: {person.get('coherence_score', 0):.2f}")
        if person.get("missing_landmarks"):
            print(f"    Missing: {', '.join(person['missing_landmarks'])}")

    # Visualization
    if viz_output:
        visualize_pose(image_path, viz_output)
