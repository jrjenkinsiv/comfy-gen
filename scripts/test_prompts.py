#!/usr/bin/env python3
"""
Prompt Engineering Test Suite
Issue #68: Empirical testing of prompt patterns

Runs randomized generations to test prompt effectiveness.
Logs validation scores for analysis.
"""

import json
import os
import random
import subprocess
from datetime import datetime
from pathlib import Path

# Test configuration
NUM_TESTS = 20
OUTPUT_DIR = "/tmp/prompt_tests"
RESULTS_FILE = "prompt_test_results.json"

# Randomization pools
SUBJECTS = [
    "a sports car",
    "a battleship",
    "a mountain landscape",
    "a portrait of a woman",
    "a futuristic city",
    "a forest scene",
    "a coffee cup",
    "a sunset over ocean",
    "a medieval castle",
    "a space station",
]

QUALITY_BOOSTERS = [
    "",  # baseline - no boosters
    "8K resolution",
    "highly detailed",
    "sharp focus",
    "professional photography",
    "cinematic lighting",
    "8K resolution, sharp focus, highly detailed",
    "masterpiece, best quality",
    "award-winning photograph, 8K",
    "ultra detailed, cinematic, professional",
]

NEGATIVE_PRESETS = {
    "none": "",
    "minimal": "blurry, low quality",
    "standard": "bad quality, blurry, low resolution, watermark, text",
    "comprehensive": "bad quality, blurry, low resolution, watermark, text, signature, jpeg artifacts, distorted, cropped, out of frame, cartoon, anime",
}

STEPS_OPTIONS = [20, 30, 50, 80]
CFG_OPTIONS = [7.0, 7.5, 8.0, 8.5]


def generate_test_prompt(subject, quality_booster):
    """Generate a test prompt with optional quality boosters."""
    if quality_booster:
        return f"{subject}, {quality_booster}"
    return subject


def run_generation(prompt, negative, steps, cfg, seed, output_path):
    """Run a single generation and capture validation score."""
    cmd = [
        "python3",
        "generate.py",
        "--workflow",
        "workflows/flux-dev.json",
        "--prompt",
        prompt,
        "--negative-prompt",
        negative,
        "--steps",
        str(steps),
        "--cfg",
        str(cfg),
        "--seed",
        str(seed),
        "--output",
        output_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(Path(__file__).parent.parent),
        )

        # Parse validation score from output
        score = None
        for line in result.stdout.split("\n"):
            if "Score:" in line:
                try:
                    score = float(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "Positive score:" in line:
                try:
                    score = float(line.split(":")[-1].strip())
                except ValueError:
                    pass

        passed = "PASSED" in result.stdout
        return {
            "success": result.returncode == 0,
            "validation_passed": passed,
            "validation_score": score,
            "stdout": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
            "stderr": result.stderr[-200:] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Run randomized prompt engineering tests."""
    print(f"[INFO] Starting {NUM_TESTS} randomized prompt tests")
    print(f"[INFO] Output directory: {OUTPUT_DIR}")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    start_time = datetime.now()

    for i in range(NUM_TESTS):
        test_id = f"{i + 1:03d}"
        seed = random.randint(1, 999999)

        # Random selections
        subject = random.choice(SUBJECTS)
        quality_booster = random.choice(QUALITY_BOOSTERS)
        negative_key = random.choice(list(NEGATIVE_PRESETS.keys()))
        negative = NEGATIVE_PRESETS[negative_key]
        steps = random.choice(STEPS_OPTIONS)
        cfg = random.choice(CFG_OPTIONS)

        # Generate prompt
        prompt = generate_test_prompt(subject, quality_booster)
        output_path = f"{OUTPUT_DIR}/test_{test_id}_seed{seed}.png"

        print(f"\n[TEST {test_id}/{NUM_TESTS}]")
        print(f"  Subject: {subject}")
        print(f"  Quality: {quality_booster or '(none)'}")
        print(f"  Negative: {negative_key}")
        print(f"  Steps: {steps}, CFG: {cfg}, Seed: {seed}")

        # Run generation
        gen_result = run_generation(prompt, negative, steps, cfg, seed, output_path)

        # Record result
        test_result = {
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
            "seed": seed,
            "subject": subject,
            "quality_booster": quality_booster,
            "negative_preset": negative_key,
            "steps": steps,
            "cfg": cfg,
            "full_prompt": prompt,
            "negative_prompt": negative,
            "output_path": output_path,
            **gen_result,
        }
        results.append(test_result)

        # Print result
        if gen_result.get("success"):
            score = gen_result.get("validation_score", "N/A")
            passed = "[PASS]" if gen_result.get("validation_passed") else "[FAIL]"
            print(f"  Result: {passed} Score: {score}")
        else:
            print(f"  Result: [ERROR] {gen_result.get('error', 'unknown')}")

    # Save results
    results_path = f"{OUTPUT_DIR}/{RESULTS_FILE}"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    elapsed = datetime.now() - start_time
    successful = sum(1 for r in results if r.get("success"))
    passed = sum(1 for r in results if r.get("validation_passed"))
    scores = [r.get("validation_score") for r in results if r.get("validation_score") is not None]

    print(f"\n{'=' * 50}")
    print("TEST SUMMARY")
    print(f"{'=' * 50}")
    print(f"Total tests: {NUM_TESTS}")
    print(f"Successful generations: {successful}")
    print(f"Validation passed: {passed}")
    if scores:
        print(f"Average score: {sum(scores) / len(scores):.3f}")
        print(f"Min score: {min(scores):.3f}")
        print(f"Max score: {max(scores):.3f}")
    print(f"Elapsed time: {elapsed}")
    print(f"Results saved to: {results_path}")

    # Analyze by quality booster
    print(f"\n{'=' * 50}")
    print("ANALYSIS BY QUALITY BOOSTER")
    print(f"{'=' * 50}")
    booster_scores = {}
    for r in results:
        booster = r.get("quality_booster") or "(none)"
        score = r.get("validation_score")
        if score is not None:
            if booster not in booster_scores:
                booster_scores[booster] = []
            booster_scores[booster].append(score)

    for booster, scores in sorted(booster_scores.items(), key=lambda x: -sum(x[1]) / len(x[1]) if x[1] else 0):
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {booster[:40]:40} avg: {avg:.3f} (n={len(scores)})")

    # Analyze by negative preset
    print(f"\n{'=' * 50}")
    print("ANALYSIS BY NEGATIVE PRESET")
    print(f"{'=' * 50}")
    neg_scores = {}
    for r in results:
        neg = r.get("negative_preset", "unknown")
        score = r.get("validation_score")
        if score is not None:
            if neg not in neg_scores:
                neg_scores[neg] = []
            neg_scores[neg].append(score)

    for neg, scores in sorted(neg_scores.items(), key=lambda x: -sum(x[1]) / len(x[1]) if x[1] else 0):
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {neg:20} avg: {avg:.3f} (n={len(scores)})")


if __name__ == "__main__":
    main()
