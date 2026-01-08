#!/usr/bin/env python3
"""CLI entry point for comfy_gen package.

This package provides utilities for generate.py:
- metadata: PNG metadata embedding
- prompt_enhancer: LLM-based prompt enhancement
- quality: Image quality scoring
- validation: CLIP validation
- pose_validation: YOLOv8 pose validation
- content_validator: Content validation
- mlflow_logger: MLflow experiment logging

Usage:
    python3 generate.py --workflow workflows/flux-dev.json --prompt "your prompt"

For direct module usage:
    python3 -m comfy_gen.quality <image_path> [prompt]
"""

import sys


def main():
    """Print usage help."""
    print(__doc__)
    print("\nAvailable modules:")
    print("  comfy_gen.quality       - Image quality scoring")
    print("  comfy_gen.validation    - CLIP validation")
    print("  comfy_gen.mlflow_logger - MLflow logging")
    print("\nMain CLI: python3 generate.py --help")
    sys.exit(0)


if __name__ == "__main__":
    main()
