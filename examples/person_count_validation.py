#!/usr/bin/env python3
"""Person count validation example using YOLO.

This example demonstrates:
- YOLO-based person detection in generated images
- Automatic person count validation
- Detection of person count mismatches

Usage:
    python3 examples/person_count_validation.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validation import YOLO_AVAILABLE, extract_expected_person_count


def main():
    """Demonstrate person count validation."""
    print("=" * 60)
    print("Person Count Validation Example")
    print("=" * 60)

    # Check YOLO availability
    print("\n[1/3] Checking YOLO availability...")
    if not YOLO_AVAILABLE:
        print("[WARN] YOLO not available")
        print("Install with: pip install ultralytics")
        print("\nThis example will show prompt parsing but not actual detection.")
    else:
        print("[OK] YOLO is available")

    # Test prompt parsing
    print("\n[2/3] Testing person count extraction from prompts...")
    print("-" * 60)

    test_prompts = [
        "solo woman standing in a field, detailed portrait",
        "single person walking down the street",
        "two women having a conversation in a cafe",
        "three people sitting on a bench in a park",
        "group of five children playing soccer",
        "landscape with mountains and trees",  # No person count
    ]

    for prompt in test_prompts:
        expected_count = extract_expected_person_count(prompt)
        if expected_count is not None:
            print(f"[OK] '{prompt[:50]}...'")
            print(f"     Expected persons: {expected_count}")
        else:
            print(f"[INFO] '{prompt[:50]}...'")
            print("     No specific count detected")
        print()

    # Example validation workflow
    print("[3/3] Example validation usage...")
    print("-" * 60)
    print("\nTo use person count validation in generation:\n")

    examples = [
        {
            "description": "Solo portrait validation",
            "command": """python3 generate.py \\
    --workflow workflows/flux-dev.json \\
    --prompt "solo woman standing in a field, detailed portrait" \\
    --output /tmp/solo_portrait.png \\
    --validate --validate-person-count""",
        },
        {
            "description": "Two people validation",
            "command": """python3 generate.py \\
    --workflow workflows/flux-dev.json \\
    --prompt "two women having a conversation, cafe setting" \\
    --output /tmp/conversation.png \\
    --validate --validate-person-count""",
        },
        {
            "description": "Person count with auto-retry",
            "command": """python3 generate.py \\
    --workflow workflows/flux-dev.json \\
    --prompt "solo person hiking on a mountain trail" \\
    --output /tmp/hiker.png \\
    --validate --validate-person-count \\
    --auto-retry --retry-limit 3""",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}:")
        print(f"   {example['command']}")
        print()

    # Show validation result structure
    print("\nValidation Result Structure:")
    print("-" * 60)
    print("""
When --validate-person-count is used, the validation result includes:

{
    "passed": True/False,
    "reason": "Validation reason",
    "positive_score": 0.XXX,           # CLIP score
    "person_count": N,                  # Detected count
    "expected_person_count": M,         # Expected from prompt
    "person_count_error": "..."        # If YOLO failed
}

Example successful validation:
  [INFO] Validation result: Image passed validation
  [INFO] Positive score: 0.320
  [INFO] Detected persons: 1
  [INFO] Expected persons: 1
  [OK] Image passed validation

Example failed validation:
  [INFO] Validation result: Person count mismatch: expected 1, detected 2
  [INFO] Positive score: 0.310
  [INFO] Detected persons: 2
  [INFO] Expected persons: 1
  [WARN] Image failed validation: Person count mismatch
""")

    # Use cases
    print("\nCommon Use Cases:")
    print("-" * 60)
    print("""
1. Solo Portraits
   - Ensure single subject, no duplicates
   - Avoid common model issues with merged subjects
   - Keywords: "solo", "single", "one person"

2. Group Shots
   - Validate correct number of people
   - Ensure all subjects are present
   - Keywords: "two people", "three women", "group of five"

3. Quality Control
   - Detect generation artifacts (duplicate subjects)
   - Catch merged/stacked people
   - Use with auto-retry for automatic correction

4. Production Workflows
   - Automated validation in CI/CD
   - Batch generation with quality gates
   - Consistent subject count across generations
""")

    print("=" * 60)
    print("Example Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
