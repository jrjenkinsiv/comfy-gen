#!/usr/bin/env python3
"""
Batch NSFW Test Generation Script

Generates 40-50 images with systematic variations across:
- Models (majicMIX, Realistic Vision)
- LoRAs (anatomy enhancers)
- Demographics (race, gender)
- Body types (slim, athletic, curvy, muscular)
- Anatomy variations (erect/flaccid, circumcised/uncircumcised, natural/enhanced breasts)
- Scenarios (solo, couples)
- Actions (cum, no cum)

Usage:
    python3 scripts/batch_nsfw_test.py [--dry-run] [--start N] [--count N]
"""

import argparse
import json
import random
import subprocess
from datetime import datetime
from pathlib import Path

# Base settings
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_SCRIPT = COMFY_GEN_DIR / "generate.py"

# Available models and their workflows
MODELS = {
    "majicmix": {
        "workflow": "workflows/majicmix-realistic.json",
        "cfg": 6.5,
        "steps": 50,
        "strength": "asian, realistic"
    },
    "realistic-vision": {
        "workflow": "workflows/realistic-vision.json",
        "cfg": 5.5,
        "steps": 50,
        "strength": "photorealistic, western"
    }
}

# SD 1.5 compatible LoRAs for anatomy
LORAS = {
    "erect_penis": "erect_penis_epoch_80.safetensors",
    "flaccid_penis": "flaccid_penis_epoch_100.safetensors",
    "dicks": "dicks_epoch_100.safetensors",
    "big_breasts": "big_breasts_v2_epoch_30.safetensors",
    "add_detail": "add_detail.safetensors",
    "more_details": "more_details.safetensors",
}

# Test variations
GENDERS = ["male", "female"]
RACES = ["caucasian", "black", "asian", "latina", "indian"]
BODY_TYPES_MALE = ["athletic muscular", "slim toned", "average build", "muscular bodybuilder"]
BODY_TYPES_FEMALE = ["slim petite", "athletic toned", "curvy hourglass", "voluptuous thick"]

# Anatomy variations
MALE_ANATOMY = {
    "erect_circumcised": {"prompt": "large erect circumcised penis, visible glans", "lora": "erect_penis", "strength": 0.7},
    "erect_uncircumcised": {"prompt": "large erect uncircumcised penis with foreskin", "lora": "erect_penis", "strength": 0.7},
    "flaccid": {"prompt": "flaccid penis hanging naturally", "lora": "flaccid_penis", "strength": 0.6},
    "semi_erect": {"prompt": "semi-erect penis", "lora": "dicks", "strength": 0.5},
}

FEMALE_ANATOMY = {
    "natural_small": {"prompt": "natural small breasts, A cup, perky nipples", "lora": None, "strength": 0},
    "natural_medium": {"prompt": "natural medium breasts, C cup, soft natural shape", "lora": None, "strength": 0},
    "natural_large": {"prompt": "natural large breasts, DD cup, slight sag natural shape", "lora": "big_breasts", "strength": 0.4},
    "enhanced": {"prompt": "enhanced large round breasts, implants, fake looking", "lora": "big_breasts", "strength": 0.6},
}

# Scenarios
SCENARIOS_SOLO_MALE = [
    "standing confidently in luxury bathroom, full frontal nude, natural pose",
    "laying on bed, nude, relaxed pose, looking at camera",
    "standing in modern gym locker room, post-workout, towel nearby",
    "outdoor private pool area, nude, sunny day, wet skin",
]

SCENARIOS_SOLO_FEMALE = [
    "laying seductively on white satin sheets in luxury bedroom",
    "standing in elegant marble bathroom, steam from shower",
    "reclining on leather couch in modern living room",
    "nude on private beach, sunset lighting, waves in background",
]

SCENARIOS_COUPLE = [
    "intimate moment on bed, missionary position, passionate",
    "standing embrace, nude bodies pressed together",
]

# Cum variations (male only or couple)
CUM_VARIATIONS = [
    {"enabled": False, "prompt": ""},
    {"enabled": True, "prompt": ", cum on stomach, fresh ejaculation"},
    {"enabled": True, "prompt": ", cum dripping, messy"},
]

# Base prompts
def build_prompt(gender, race, body_type, anatomy_desc, scenario, cum_prompt="", is_couple=False):
    """Build a detailed prompt from components."""

    age_range = random.choice(["early 20s", "mid 20s", "late 20s", "early 30s"])

    if gender == "male":
        base = f"professional photograph of a handsome {race} man in his {age_range}, {body_type} build"
        features = random.choice([
            "short hair, light stubble",
            "short fade haircut, clean shaven",
            "medium length hair, well groomed",
            "buzz cut, defined jawline",
        ])
    else:
        base = f"professional photograph of a beautiful {race} woman in her {age_range}, {body_type} figure"
        features = random.choice([
            "long flowing hair, natural makeup",
            "short bob haircut, minimal makeup",
            "wavy hair, soft features",
            "straight hair, striking eyes",
        ])

    camera = random.choice([
        "shot on canon 5d mark iv, 85mm lens, shallow depth of field",
        "shot on sony a7riv, 50mm lens f1.8",
        "shot on hasselblad medium format, 80mm lens",
        "professional studio lighting, high-end camera",
    ])

    quality = "natural skin texture, skin pores visible, photorealistic, raw photo, realistic body proportions"

    prompt = f"{base}, {features}, {anatomy_desc}, {scenario}{cum_prompt}, {camera}, {quality}"
    return prompt

def build_negative_prompt():
    """Build standard negative prompt."""
    return (
        "cartoon, anime, 3d render, painting, illustration, oversaturated, overprocessed, "
        "plastic skin, airbrushed, fake, mannequin, doll, bad anatomy, deformed, blurry, "
        "low quality, watermark, text, extra limbs, missing limbs, floating limbs, "
        "disconnected body parts, ugly, disgusting"
    )

def generate_test_matrix():
    """Generate the full test matrix of variations."""
    tests = []
    test_id = 1

    # Solo male tests
    for race in RACES:
        for body_type in BODY_TYPES_MALE:
            for anatomy_key, anatomy_data in MALE_ANATOMY.items():
                for scenario in SCENARIOS_SOLO_MALE[:2]:  # Limit scenarios
                    for model_key in MODELS.keys():
                        # Some with cum, some without
                        cum = random.choice(CUM_VARIATIONS)

                        tests.append({
                            "id": test_id,
                            "gender": "male",
                            "race": race,
                            "body_type": body_type,
                            "anatomy_key": anatomy_key,
                            "anatomy_prompt": anatomy_data["prompt"],
                            "lora": anatomy_data["lora"],
                            "lora_strength": anatomy_data["strength"],
                            "scenario": scenario,
                            "cum": cum["enabled"],
                            "cum_prompt": cum["prompt"] if cum["enabled"] else "",
                            "model": model_key,
                            "is_couple": False,
                        })
                        test_id += 1

    # Solo female tests
    for race in RACES:
        for body_type in BODY_TYPES_FEMALE:
            for anatomy_key, anatomy_data in FEMALE_ANATOMY.items():
                for scenario in SCENARIOS_SOLO_FEMALE[:2]:  # Limit scenarios
                    for model_key in MODELS.keys():
                        tests.append({
                            "id": test_id,
                            "gender": "female",
                            "race": race,
                            "body_type": body_type,
                            "anatomy_key": anatomy_key,
                            "anatomy_prompt": anatomy_data["prompt"],
                            "lora": anatomy_data["lora"],
                            "lora_strength": anatomy_data["strength"],
                            "scenario": scenario,
                            "cum": False,
                            "cum_prompt": "",
                            "model": model_key,
                            "is_couple": False,
                        })
                        test_id += 1

    return tests

def select_diverse_subset(tests, count=50):
    """Select a diverse subset of tests covering all variations."""
    selected = []

    # Ensure coverage of key dimensions
    dimensions = {
        "gender": set(),
        "race": set(),
        "anatomy_key": set(),
        "model": set(),
    }

    # Shuffle to randomize selection
    random.shuffle(tests)

    for test in tests:
        if len(selected) >= count:
            break

        # Prioritize tests that add new coverage
        adds_coverage = False
        for dim, values in dimensions.items():
            if test[dim] not in values:
                adds_coverage = True
                break

        if adds_coverage or len(selected) < count // 2:
            selected.append(test)
            for dim in dimensions:
                dimensions[dim].add(test[dim])

    # Fill remaining slots randomly
    remaining = [t for t in tests if t not in selected]
    random.shuffle(remaining)
    while len(selected) < count and remaining:
        selected.append(remaining.pop())

    # Sort by ID for consistent ordering
    selected.sort(key=lambda x: x["id"])

    # Renumber
    for i, test in enumerate(selected, 1):
        test["id"] = i

    return selected

def run_generation(test, dry_run=False):
    """Run a single generation."""
    model_config = MODELS[test["model"]]

    prompt = build_prompt(
        gender=test["gender"],
        race=test["race"],
        body_type=test["body_type"],
        anatomy_desc=test["anatomy_prompt"],
        scenario=test["scenario"],
        cum_prompt=test["cum_prompt"],
        is_couple=test["is_couple"],
    )

    negative_prompt = build_negative_prompt()

    # Build output filename
    datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"batch_{test['id']:03d}_{test['gender']}_{test['race']}_{test['anatomy_key']}_{test['model']}.png"
    output_path = f"/tmp/{filename}"

    # Build command
    cmd = [
        "python3", str(GENERATE_SCRIPT),
        "--workflow", model_config["workflow"],
        "--prompt", prompt,
        "--negative-prompt", negative_prompt,
        "--steps", str(model_config["steps"]),
        "--cfg", str(model_config["cfg"]),
        "--seed", str(random.randint(1, 999999)),
        "--output", output_path,
    ]

    # Add LoRA if specified
    if test["lora"] and test["lora_strength"] > 0:
        lora_file = LORAS.get(test["lora"])
        if lora_file:
            cmd.extend(["--lora", f"{lora_file}:{test['lora_strength']}"])

    print(f"\n{'='*60}")
    print(f"Test {test['id']}: {test['gender']} {test['race']} {test['anatomy_key']}")
    print(f"Model: {test['model']}, LoRA: {test['lora']} @ {test['lora_strength']}")
    print(f"Cum: {test['cum']}")
    print(f"{'='*60}")

    if dry_run:
        print("[DRY RUN] Would execute:")
        print(f"  {' '.join(cmd[:6])}...")
        print(f"  Prompt: {prompt[:100]}...")
        return {"status": "dry_run", "test": test}

    try:
        result = subprocess.run(
            cmd,
            cwd=str(COMFY_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per image
        )

        # Parse output for score
        score = None
        url = None
        for line in result.stdout.split("\n"):
            if "Score:" in line:
                try:
                    score = float(line.split(":")[-1].strip())
                except:
                    pass
            if "Image available at:" in line:
                url = line.split("at:")[-1].strip()

        success = result.returncode == 0
        print(f"[{'OK' if success else 'FAIL'}] Score: {score}, URL: {url}")

        return {
            "status": "success" if success else "failed",
            "test": test,
            "score": score,
            "url": url,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Generation took too long")
        return {"status": "timeout", "test": test}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "error", "test": test, "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Batch NSFW test generation")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--start", type=int, default=1, help="Start from test number N")
    parser.add_argument("--count", type=int, default=50, help="Number of tests to run")
    parser.add_argument("--list", action="store_true", help="List all tests without running")
    args = parser.parse_args()

    print("Generating test matrix...")
    all_tests = generate_test_matrix()
    print(f"Total possible combinations: {len(all_tests)}")

    tests = select_diverse_subset(all_tests, args.count)
    print(f"Selected {len(tests)} diverse tests")

    if args.list:
        print("\nTest Matrix:")
        print("-" * 80)
        for test in tests:
            print(f"{test['id']:3d}. {test['gender']:6s} {test['race']:10s} {test['anatomy_key']:20s} {test['model']:15s} cum={test['cum']}")
        return

    # Filter to requested range
    tests = [t for t in tests if t["id"] >= args.start][:args.count]

    print(f"\nRunning {len(tests)} tests starting from #{args.start}")
    print(f"Estimated time: {len(tests) * 1.5:.0f} minutes")

    results = []
    for test in tests:
        result = run_generation(test, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    timeout = [r for r in results if r["status"] == "timeout"]

    print(f"Success: {len(success)}")
    print(f"Failed: {len(failed)}")
    print(f"Timeout: {len(timeout)}")

    if success:
        scores = [r["score"] for r in success if r.get("score")]
        if scores:
            print(f"Average score: {sum(scores)/len(scores):.3f}")
            print(f"Score range: {min(scores):.3f} - {max(scores):.3f}")

    # Save results
    results_file = COMFY_GEN_DIR / "batch_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_file}")

if __name__ == "__main__":
    main()
