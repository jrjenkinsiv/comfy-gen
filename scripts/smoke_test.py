#!/usr/bin/env python3
"""
Smoke test for comfy-gen module imports.

This script validates that all modules can be imported successfully.
Run this as part of CI to catch import errors early.

Usage:
    python scripts/smoke_test.py
"""

import sys


def test_imports() -> int:
    """Test that all core modules can be imported."""
    errors = []

    # Core modules that should always import
    core_modules = [
        ("utils", "Main package"),
        ("utils.metadata", "Metadata handling"),
        ("utils.validation", "Validation utilities"),
        ("utils.quality", "Quality assessment"),
        ("utils.prompt_enhancer", "Prompt enhancement"),
        ("utils.mlflow_logger", "MLflow logging"),
    ]

    # Optional modules that may require extra dependencies
    optional_modules = [
        ("utils.pose_validation", "Pose validation (requires mediapipe)"),
        ("utils.content_validator", "Content validation (requires transformers)"),
    ]

    print("=" * 60)
    print("Comfy-Gen Smoke Test")
    print("=" * 60)
    print()

    # Test core modules
    print("Core Modules:")
    print("-" * 40)
    for module_name, description in core_modules:
        try:
            __import__(module_name)
            print(f"[OK] {module_name} - {description}")
        except ImportError as e:
            print(f"[ERROR] {module_name} - {description}")
            print(f"        Import error: {e}")
            errors.append(module_name)

    print()

    # Test optional modules
    print("Optional Modules (may require extra dependencies):")
    print("-" * 40)
    for module_name, description in optional_modules:
        try:
            __import__(module_name)
            print(f"[OK] {module_name} - {description}")
        except ImportError as e:
            print(f"[WARN] {module_name} - {description}")
            print(f"        Not available: {e}")
            # Optional modules don't count as errors

    print()
    print("=" * 60)

    if errors:
        print(f"[ERROR] {len(errors)} core module(s) failed to import:")
        for mod in errors:
            print(f"  - {mod}")
        return 1
    else:
        print("[OK] All core modules imported successfully!")
        return 0


def test_cli_entrypoint() -> int:
    """Test that CLI entrypoint exists."""
    print()
    print("CLI Entrypoint:")
    print("-" * 40)

    import os
    import sys

    try:
        # generate.py is the CLI - check if it exists and is executable
        cli_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generate.py")
        if os.path.exists(cli_path):
            print(f"[OK] CLI entrypoint 'generate.py' exists at {cli_path}")
            return 0
        else:
            print(f"[ERROR] CLI entrypoint not found at {cli_path}")
            return 1
    except Exception as e:
        print(f"[ERROR] CLI entrypoint check failed: {e}")
        return 1


def main() -> int:
    """Run all smoke tests."""
    result = 0

    result += test_imports()
    result += test_cli_entrypoint()

    print()
    if result == 0:
        print("[OK] All smoke tests passed!")
    else:
        print(f"[ERROR] {result} test(s) failed")

    return min(result, 1)  # Return 0 or 1


if __name__ == "__main__":
    sys.exit(main())
