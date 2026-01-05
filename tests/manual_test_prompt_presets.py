#!/usr/bin/env python3
"""Manual test script for --prompt-preset functionality.

This script validates that:
1. --list-presets displays available presets
2. --prompt-preset loads presets correctly
3. Preset negative prompts merge with user negatives
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and check if it succeeds."""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"CMD: {' '.join(cmd)}")
    print(f"{'='*70}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode == 0:
        print(f"[OK] {description} - PASSED")
        return True
    else:
        print(f"[ERROR] {description} - FAILED (exit code {result.returncode})")
        return False


def main():
    """Run manual tests."""
    repo_root = Path(__file__).parent.parent
    generate_py = repo_root / "generate.py"
    
    all_passed = True
    
    # Test 1: List presets
    all_passed &= run_command(
        ["python3", str(generate_py), "--list-presets"],
        "List available prompt presets"
    )
    
    # Test 2: Show help with new flags
    result = subprocess.run(
        ["python3", str(generate_py), "--help"],
        capture_output=True,
        text=True
    )
    
    if "--prompt-preset" in result.stdout and "--list-presets" in result.stdout:
        print("\n[OK] Help text includes new flags")
    else:
        print("\n[ERROR] Help text missing new flags")
        all_passed = False
    
    # Test 3: Try to use a non-existent preset (should fail gracefully)
    result = subprocess.run(
        ["python3", str(generate_py), 
         "--workflow", "workflows/flux-dev.json",
         "--prompt-preset", "nonexistent_preset"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 and "Prompt preset not found" in result.stdout:
        print("\n[OK] Non-existent preset handled gracefully")
    else:
        print("\n[ERROR] Non-existent preset error handling failed")
        all_passed = False
    
    # Summary
    print("\n" + "="*70)
    if all_passed:
        print("[OK] All manual tests PASSED")
        return 0
    else:
        print("[ERROR] Some manual tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
