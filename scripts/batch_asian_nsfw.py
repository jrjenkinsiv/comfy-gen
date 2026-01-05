#!/usr/bin/env python3
"""
Batch Asian NSFW Test Generation Script

Generates images with systematic variations across:
- Asian ethnicities (Vietnamese, Korean, Japanese, Thai, Filipino, etc.)
- Models (MajicMix Realistic, Realistic Vision)
- LoRAs (skin enhancers, detail)
- Body types (slim, curvy, athletic, petite)
- Scenarios (bedroom, bathroom, studio, outdoor)
- Framing (portrait upper body, medium shot, close-up)

Key learnings applied:
- NO fixed seeds (enables variety)
- Heavy anti-duplicate negatives
- Multiple model/LoRA combinations

Usage:
    python3 scripts/batch_asian_nsfw.py [--dry-run] [--count N]
    
    # Run 50 generations in background
    nohup python3 scripts/batch_asian_nsfw.py --count 50 > /tmp/batch_asian_output.log 2>&1 &
"""

import subprocess
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

# Base settings
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_SCRIPT = COMFY_GEN_DIR / "generate.py"

# Available models and their workflows
MODELS = {
    "majicmix": {
        "workflow": "workflows/majicmix-realistic.json",
        "cfg_range": (6.0, 8.0),
        "steps_range": (60, 80),
        "description": "Best for Asian features, photorealistic"
    },
    # Can add more models here as we test them
    # "realistic-vision": {
    #     "workflow": "workflows/realistic-vision.json",
    #     "cfg_range": (5.0, 7.0),
    #     "steps_range": (50, 70),
    #     "description": "Alternative realistic model"
    # },
}

# LoRA configurations - vary strength randomly within range
LORAS = {
    "polyhedron_skin": {
        "file": "polyhedron_skin.safetensors",
        "strength_range": (0.4, 0.7),
        "description": "Realistic skin texture with pores"
    },
    "add_detail": {
        "file": "add_detail.safetensors",
        "strength_range": (0.2, 0.5),
        "description": "General detail enhancement"
    },
    "none": {
        "file": None,
        "strength_range": (0, 0),
        "description": "No LoRA - baseline comparison"
    }
}

# Asian ethnicities with visual descriptors
ETHNICITIES = {
    "vietnamese": {
        "skin": "golden tan",
        "features": "almond eyes, soft features",
    },
    "korean": {
        "skin": "fair porcelain",
        "features": "double eyelids, v-line jaw, clear skin",
    },
    "japanese": {
        "skin": "fair to light",
        "features": "delicate features, natural beauty",
    },
    "thai": {
        "skin": "golden bronze",
        "features": "warm eyes, full lips",
    },
    "filipino": {
        "skin": "medium tan",
        "features": "warm brown eyes, friendly features",
    },
    "chinese": {
        "skin": "fair to medium",
        "features": "elegant features, almond eyes",
    },
    "indonesian": {
        "skin": "warm tan",
        "features": "expressive eyes, natural beauty",
    },
    "malaysian": {
        "skin": "medium warm",
        "features": "mixed heritage beauty",
    },
    "taiwanese": {
        "skin": "fair",
        "features": "youthful features, clear skin",
    },
    "singaporean": {
        "skin": "medium",
        "features": "cosmopolitan beauty, refined features",
    },
}

# Body types
BODY_TYPES = [
    "slim petite figure",
    "athletic toned body",
    "curvy hourglass figure",
    "voluptuous thick body",
    "fit muscular physique",
    "natural average build",
]

# Age ranges
AGES = ["early 20s", "mid 20s", "late 20s", "early 30s"]

# Hair styles
HAIR_STYLES = [
    "long straight black hair",
    "shoulder length dark hair",
    "short bob haircut",
    "wavy black hair",
    "long flowing hair",
    "medium length hair with bangs",
]

# Scenarios (upper body focused to avoid anatomy issues)
SCENARIOS = [
    "nude upper body portrait in luxury bedroom, sitting on silk sheets",
    "topless in elegant bathroom, soft steam and warm lighting",
    "nude portrait in professional studio, simple white background",
    "bare chest in modern apartment, natural window light",
    "nude upper body on private balcony, sunset lighting",
    "topless relaxing in spa setting, soft ambient light",
    "nude portrait against dark backdrop, dramatic lighting",
    "bare upper body in art gallery setting, artistic pose",
]

# Breast variations
BREAST_TYPES = [
    "small perky breasts, A cup",
    "medium natural breasts, B cup",
    "full natural breasts, C cup",
    "large natural breasts, D cup",
    "petite breasts with prominent nipples",
    "round firm breasts",
]

# Expressions
EXPRESSIONS = [
    "looking directly at camera with sultry expression",
    "gazing seductively with parted lips",
    "confident pose with knowing smile",
    "relaxed expression with soft eyes",
    "playful expression with slight smile",
    "intense gaze with mysterious expression",
]

# Resolutions to try (all portrait-oriented for single person)
RESOLUTIONS = [
    (1024, 1536),  # 2:3 portrait
    (896, 1344),   # 2:3 smaller
    (1024, 1280),  # 4:5 portrait
    (768, 1152),   # 2:3 smaller still
]

# Heavy negative prompt to prevent duplicates and anatomy issues
NEGATIVE_PROMPT = """
two people, two women, multiple people, couple, pair, twins, clone, duplicate person,
mirror, reflection, split image, collage, diptych, side by side, crowd, group, extra person,
merged bodies, fused bodies, stacked bodies, overlapping figures,
bad anatomy, deformed, mutated, disfigured, malformed, twisted body,
detached limbs, floating limbs, disconnected body parts, extra limbs, missing limbs,
anime, cartoon, illustration, 3d render, CGI, painting, drawing,
fake, plastic skin, airbrushed, oversaturated, overprocessed,
blurry, low quality, watermark, text, signature,
full body, legs, feet, below waist
""".strip().replace("\n", " ")


def build_prompt(ethnicity: str, body_type: str, age: str, hair: str, 
                 scenario: str, breasts: str, expression: str) -> str:
    """Build a detailed prompt from components."""
    
    eth_data = ETHNICITIES[ethnicity]
    
    prompt = f"""extremely detailed RAW photograph, professional glamour photography,
portrait of one single beautiful {ethnicity} woman in her {age},
{eth_data['skin']} skin, {eth_data['features']},
{body_type}, {hair}, {breasts},
{scenario}, {expression},
upper body shot from waist up, one person only, solo portrait, no other people,
detailed skin texture, skin pores visible, photorealistic, natural lighting,
shot on Canon EOS R5, 85mm f/1.4 lens, shallow depth of field,
professional studio quality, high resolution""".strip().replace("\n", " ")
    
    return prompt


def generate_test_batch(count: int) -> list:
    """Generate a diverse batch of test configurations."""
    tests = []
    
    for i in range(count):
        # Random selections
        ethnicity = random.choice(list(ETHNICITIES.keys()))
        body_type = random.choice(BODY_TYPES)
        age = random.choice(AGES)
        hair = random.choice(HAIR_STYLES)
        scenario = random.choice(SCENARIOS)
        breasts = random.choice(BREAST_TYPES)
        expression = random.choice(EXPRESSIONS)
        model_key = random.choice(list(MODELS.keys()))
        lora_key = random.choice(list(LORAS.keys()))
        resolution = random.choice(RESOLUTIONS)
        
        model_config = MODELS[model_key]
        lora_config = LORAS[lora_key]
        
        # Random values within ranges
        cfg = round(random.uniform(*model_config["cfg_range"]), 1)
        steps = random.randint(*model_config["steps_range"])
        lora_strength = round(random.uniform(*lora_config["strength_range"]), 2) if lora_config["file"] else 0
        
        tests.append({
            "id": i + 1,
            "ethnicity": ethnicity,
            "body_type": body_type,
            "age": age,
            "hair": hair,
            "scenario": scenario,
            "breasts": breasts,
            "expression": expression,
            "model": model_key,
            "workflow": model_config["workflow"],
            "lora": lora_key,
            "lora_file": lora_config["file"],
            "lora_strength": lora_strength,
            "cfg": cfg,
            "steps": steps,
            "width": resolution[0],
            "height": resolution[1],
        })
    
    return tests


def run_generation(test: dict, dry_run: bool = False) -> dict:
    """Run a single generation."""
    
    prompt = build_prompt(
        ethnicity=test["ethnicity"],
        body_type=test["body_type"],
        age=test["age"],
        hair=test["hair"],
        scenario=test["scenario"],
        breasts=test["breasts"],
        expression=test["expression"],
    )
    
    # Build output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"asian_{test['id']:03d}_{test['ethnicity']}_{test['lora']}_{timestamp}.png"
    output_path = f"/tmp/{filename}"
    
    # Build command - NO SEED SPECIFIED (enables randomness)
    cmd = [
        "python3", str(GENERATE_SCRIPT),
        "--workflow", test["workflow"],
        "--prompt", prompt,
        "--negative-prompt", NEGATIVE_PROMPT,
        "--steps", str(test["steps"]),
        "--cfg", str(test["cfg"]),
        "--width", str(test["width"]),
        "--height", str(test["height"]),
        "--output", output_path,
    ]
    
    # Add LoRA if specified
    if test["lora_file"]:
        cmd.extend(["--lora", f"{test['lora_file']}:{test['lora_strength']}"])
    
    print(f"\n{'='*70}")
    print(f"Test {test['id']}: {test['ethnicity'].upper()} woman - {test['age']}")
    print(f"Body: {test['body_type'][:30]}...")
    print(f"Model: {test['model']}, LoRA: {test['lora']} @ {test['lora_strength']}")
    print(f"Resolution: {test['width']}x{test['height']}, CFG: {test['cfg']}, Steps: {test['steps']}")
    print(f"{'='*70}")
    
    if dry_run:
        print(f"[DRY RUN] Would execute generation")
        print(f"  Prompt: {prompt[:100]}...")
        return {"status": "dry_run", "test": test}
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(COMFY_GEN_DIR),
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per image
        )
        
        # Parse output for score and URL
        score = None
        url = None
        validation_passed = False
        
        for line in result.stdout.split("\n"):
            if "Score:" in line:
                try:
                    score = float(line.split(":")[-1].strip())
                except:
                    pass
            if "Image available at:" in line:
                url = line.split("at:")[-1].strip()
            if "Validation: PASSED" in line:
                validation_passed = True
        
        success = result.returncode == 0
        status = "success" if success else "failed"
        
        print(f"[{status.upper()}] Score: {score}, Validation: {'PASSED' if validation_passed else 'FAILED'}")
        if url:
            print(f"  URL: {url}")
        
        return {
            "status": status,
            "test": test,
            "prompt": prompt,
            "score": score,
            "validation_passed": validation_passed,
            "url": url,
            "output_path": output_path,
            "stdout": result.stdout[-500:] if result.stdout else "",  # Last 500 chars
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
        
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Generation took too long (>10 min)")
        return {"status": "timeout", "test": test}
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "error", "test": test, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Batch Asian NSFW test generation")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--count", type=int, default=50, help="Number of images to generate")
    parser.add_argument("--list", action="store_true", help="List all tests without running")
    args = parser.parse_args()
    
    print("=" * 70)
    print("BATCH ASIAN NSFW GENERATION")
    print("=" * 70)
    print(f"Target count: {args.count}")
    print(f"Ethnicities: {len(ETHNICITIES)}")
    print(f"Models: {len(MODELS)}")
    print(f"LoRAs: {len(LORAS)}")
    print(f"NOTE: Seeds are RANDOM (not fixed) for variety")
    print("=" * 70)
    
    tests = generate_test_batch(args.count)
    
    if args.list:
        print("\nTest Matrix:")
        print("-" * 80)
        for test in tests:
            print(f"{test['id']:3d}. {test['ethnicity']:12s} {test['lora']:15s} @ {test['lora_strength']:.2f} | {test['width']}x{test['height']} CFG:{test['cfg']}")
        return
    
    print(f"\nRunning {len(tests)} generations...")
    print(f"Estimated time: {len(tests) * 2:.0f} minutes (2 min/image average)")
    print("=" * 70)
    
    results = []
    start_time = datetime.now()
    
    for test in tests:
        result = run_generation(test, dry_run=args.dry_run)
        results.append(result)
        
        # Progress update every 10 images
        if test["id"] % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            remaining = elapsed / test["id"] * (len(tests) - test["id"])
            print(f"\n[PROGRESS] {test['id']}/{len(tests)} complete. Elapsed: {elapsed:.1f}m, ETA: {remaining:.1f}m\n")
    
    # Summary
    print("\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)
    
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    timeout = [r for r in results if r["status"] == "timeout"]
    
    print(f"Success: {len(success)}")
    print(f"Failed: {len(failed)}")
    print(f"Timeout: {len(timeout)}")
    
    if success:
        scores = [r["score"] for r in success if r.get("score")]
        validation_passed = [r for r in success if r.get("validation_passed")]
        
        if scores:
            print(f"\nScore Statistics:")
            print(f"  Average: {sum(scores)/len(scores):.3f}")
            print(f"  Range: {min(scores):.3f} - {max(scores):.3f}")
            print(f"  Validation passed: {len(validation_passed)}/{len(success)}")
        
        # Breakdown by ethnicity
        print(f"\nBy Ethnicity:")
        eth_scores = {}
        for r in success:
            eth = r["test"]["ethnicity"]
            if eth not in eth_scores:
                eth_scores[eth] = []
            if r.get("score"):
                eth_scores[eth].append(r["score"])
        
        for eth, scores in sorted(eth_scores.items()):
            if scores:
                print(f"  {eth:12s}: {len(scores):2d} images, avg score: {sum(scores)/len(scores):.3f}")
        
        # Breakdown by LoRA
        print(f"\nBy LoRA:")
        lora_scores = {}
        for r in success:
            lora = r["test"]["lora"]
            if lora not in lora_scores:
                lora_scores[lora] = []
            if r.get("score"):
                lora_scores[lora].append(r["score"])
        
        for lora, scores in sorted(lora_scores.items()):
            if scores:
                print(f"  {lora:15s}: {len(scores):2d} images, avg score: {sum(scores)/len(scores):.3f}")
    
    # Save detailed results
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    
    results_data = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_minutes": elapsed_total,
        "total_count": len(tests),
        "success_count": len(success),
        "failed_count": len(failed),
        "timeout_count": len(timeout),
        "results": results,
    }
    
    results_file = COMFY_GEN_DIR / "batch_asian_results.json"
    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {results_file}")
    
    # List all generated URLs for easy viewing
    print(f"\n{'='*70}")
    print("GENERATED IMAGES (view in browser):")
    print("=" * 70)
    for r in success:
        if r.get("url"):
            print(r["url"])


if __name__ == "__main__":
    main()
