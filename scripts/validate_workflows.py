#!/usr/bin/env python3
"""
Validate workflow JSON files.

This script checks that all workflow JSON files in the workflows/ directory
are valid JSON.

Usage:
    python scripts/validate_workflows.py
"""

import json
import sys
from pathlib import Path


def main() -> int:
    """Validate all workflow JSON files."""
    workflows_dir = Path("workflows")

    if not workflows_dir.exists():
        print("[WARN] No workflows directory found")
        return 0

    workflow_files = list(workflows_dir.glob("*.json"))

    if not workflow_files:
        print("[WARN] No workflow JSON files found")
        return 0

    print(f"Validating {len(workflow_files)} workflow file(s)...")
    print()

    errors = []
    for wf in workflow_files:
        try:
            with open(wf) as f:
                json.load(f)
            print(f"[OK] {wf.name}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] {wf.name}: {e}")
            errors.append(wf.name)

    print()

    if errors:
        print(f"[ERROR] {len(errors)} workflow(s) have invalid JSON:")
        for name in errors:
            print(f"  - {name}")
        return 1
    else:
        print("[OK] All workflow JSON files are valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
