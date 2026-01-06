#!/usr/bin/env python3
"""
High-quality batch experiment runner.
30 images with high steps, detailed prompts, and varied parameters.
"""

import random
import subprocess
import sys
from pathlib import Path

import mlflow

MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfy-gen-hq"
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/batch_hq")

# High quality parameters
HQ_SAMPLERS = ["dpmpp_2m_sde", "dpmpp_2m", "euler_ancestral", "heun"]
HQ_CFGS = [5.5, 6.0, 6.5, 7.0]
HQ_STEPS = [100, 120, 150]
HQ_SCHEDULERS = ["karras", "sgm_uniform"]

# Detailed prompt components
SUBJECTS = [
    ("young japanese woman", "delicate features, porcelain skin, dark silky hair"),
    ("korean model", "flawless skin, natural beauty, elegant bone structure"),
    ("chinese woman", "refined features, graceful expression, luminous skin"),
    ("thai woman", "warm golden skin tone, exotic beauty, expressive eyes"),
    ("filipina woman", "sun-kissed skin, radiant smile, natural glow"),
    ("caucasian woman", "fair complexion, striking features, piercing eyes"),
    ("latina woman", "caramel skin, voluptuous curves, passionate expression"),
    ("black woman", "deep ebony skin, statuesque beauty, regal features"),
    ("indian woman", "warm brown skin, large expressive eyes, exotic beauty"),
    ("mixed race woman", "unique blend of features, striking beauty, distinctive look"),
]

SCENARIOS = [
    {
        "key": "glamour_portrait",
        "desc": "glamour portrait, studio lighting, three-point lighting setup, soft diffused key light, subtle rim light on hair, shallow depth of field, professional fashion photography, high-end magazine quality",
        "negative_add": "harsh shadows, flat lighting, amateur lighting",
    },
    {
        "key": "boudoir_bedroom",
        "desc": "elegant boudoir photography, luxurious bedroom setting, silk sheets, warm ambient lighting, soft window light streaming in, intimate atmosphere, artistic nude, tasteful sensuality",
        "negative_add": "cheap hotel, harsh flash, unflattering angles",
    },
    {
        "key": "natural_outdoor",
        "desc": "natural outdoor setting, golden hour lighting, warm sunlight, dappled shade, lush green environment, relaxed nude pose, connection with nature, organic beauty",
        "negative_add": "overexposed, harsh midday sun, cluttered background",
    },
    {
        "key": "shower_wet",
        "desc": "shower photography, wet glistening skin, water droplets on body, steam and mist, dramatic lighting through water, sensual atmosphere, artistic wet look",
        "negative_add": "dirty bathroom, harsh overhead light",
    },
    {
        "key": "intimate_closeup",
        "desc": "intimate close-up, macro detail on skin texture, shallow depth of field, soft focus background, warm skin tones, artistic nude photography, emphasis on curves and form",
        "negative_add": "pores too visible, skin imperfections",
    },
    {
        "key": "artistic_pose",
        "desc": "artistic nude photography, classical pose inspired by renaissance art, dramatic chiaroscuro lighting, sculptural body form, museum quality composition, fine art aesthetic",
        "negative_add": "awkward pose, unflattering angle, amateur composition",
    },
]

LORA_OPTIONS = [
    None,
    ("zy_AmateurStyle_v2.safetensors", 0.35),
    ("zy_AmateurStyle_v2.safetensors", 0.45),
]

# Base quality tags for Pony Realism
QUALITY_PREFIX = "score_9, score_8_up, score_7_up, source_photo, raw photo, photorealistic, hyperrealistic, ultra detailed, masterpiece"
QUALITY_SUFFIX = "8k uhd, high resolution, professional photography, sharp focus, intricate details"

BASE_NEGATIVE = "score_6, score_5, score_4, blurry, low quality, jpeg artifacts, compression artifacts, pixelated, grainy, oversaturated, undersaturated, overexposed, underexposed, bad anatomy, deformed, disfigured, mutation, extra limbs, missing limbs, bad proportions, gross proportions, watermark, signature, text, logo"


def build_prompt(subject: tuple, scenario: dict) -> tuple[str, str]:
    """Build detailed prompt and negative prompt."""
    subject_name, subject_desc = subject

    prompt = f"{QUALITY_PREFIX}, {subject_name}, {subject_desc}, {scenario['desc']}, {QUALITY_SUFFIX}"
    negative = f"{BASE_NEGATIVE}, {scenario['negative_add']}"

    return prompt, negative


def run_generation(
    prompt: str,
    negative: str,
    sampler: str,
    cfg: float,
    steps: int,
    scheduler: str,
    lora,
    output_path: Path,
) -> dict:
    """Run a single high-quality generation."""

    cmd = [
        sys.executable, str(GENERATE_PY),
        "--workflow", "workflows/pony-realism.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", str(steps),
        "--cfg", str(cfg),
        "--sampler", sampler,
        "--scheduler", scheduler,
        "--output", str(output_path),
    ]

    if lora:
        lora_name, lora_strength = lora
        cmd.extend(["--lora", f"{lora_name}:{lora_strength}"])

    print(f"  Generating: {sampler} cfg={cfg} steps={steps} sched={scheduler}")

    result = subprocess.run(
        cmd,
        cwd=str(COMFY_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=600,  # 10 minute timeout for high-step images
    )

    # Parse output
    output = result.stdout + result.stderr
    minio_url = None
    validation_score = None
    passed = False

    import re
    for line in output.split("\n"):
        if "http://192.168.1.215:9000/comfy-gen/" in line and ".png" in line and ".json" not in line:
            match = re.search(r'(http://192\.168\.1\.215:9000/comfy-gen/[^\s]+\.png)', line)
            if match:
                minio_url = match.group(1)
        if "Score:" in line:
            try:
                validation_score = float(line.split(":")[-1].strip())
            except:
                pass
        if "Validation: PASSED" in line:
            passed = True

    return {
        "success": result.returncode == 0,
        "minio_url": minio_url,
        "validation_score": validation_score,
        "validation_passed": passed,
    }


def generate_experiments(count: int = 30) -> list:
    """Generate diverse high-quality experiments."""
    experiments = []

    for _i in range(count):
        subject = random.choice(SUBJECTS)
        scenario = random.choice(SCENARIOS)

        experiments.append({
            "subject": subject,
            "scenario": scenario,
            "sampler": random.choice(HQ_SAMPLERS),
            "cfg": random.choice(HQ_CFGS),
            "steps": random.choice(HQ_STEPS),
            "scheduler": random.choice(HQ_SCHEDULERS),
            "lora": random.choice(LORA_OPTIONS),
        })

    return experiments


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run high-quality batch experiments")
    parser.add_argument("--count", type=int, default=30, help="Number of experiments")
    parser.add_argument("--dry-run", action="store_true", help="Print without running")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    experiments = generate_experiments(args.count)

    print(f"[INFO] Generated {len(experiments)} high-quality experiments")
    print(f"[INFO] Steps: {HQ_STEPS}, CFG: {HQ_CFGS}")

    if args.dry_run:
        for i, exp in enumerate(experiments[:5]):
            subj = exp["subject"][0]
            scen = exp["scenario"]["key"]
            print(f"  {i+1}. {subj} - {scen} ({exp['sampler']} s={exp['steps']})")
        print(f"  ... and {len(experiments) - 5} more")
        return

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    results = []
    for i, exp in enumerate(experiments):
        subject_name = exp["subject"][0]
        scenario_key = exp["scenario"]["key"]

        print(f"\n[{i+1}/{len(experiments)}] {subject_name} - {scenario_key}")

        prompt, negative = build_prompt(exp["subject"], exp["scenario"])
        output_path = OUTPUT_DIR / f"hq_{i:04d}.png"

        try:
            with mlflow.start_run():
                mlflow.log_param("subject", subject_name)
                mlflow.log_param("scenario", scenario_key)
                mlflow.log_param("sampler", exp["sampler"])
                mlflow.log_param("cfg", exp["cfg"])
                mlflow.log_param("steps", exp["steps"])
                mlflow.log_param("scheduler", exp["scheduler"])
                mlflow.log_param("lora", exp["lora"][0] if exp["lora"] else "none")
                mlflow.log_param("lora_strength", exp["lora"][1] if exp["lora"] else 0.0)
                mlflow.log_param("prompt_preview", prompt[:200])

                result = run_generation(
                    prompt=prompt,
                    negative=negative,
                    sampler=exp["sampler"],
                    cfg=exp["cfg"],
                    steps=exp["steps"],
                    scheduler=exp["scheduler"],
                    lora=exp["lora"],
                    output_path=output_path,
                )

                mlflow.log_metric("success", 1 if result["success"] else 0)
                mlflow.log_metric("validation_passed", 1 if result["validation_passed"] else 0)
                if result["validation_score"]:
                    mlflow.log_metric("validation_score", result["validation_score"])
                if result["minio_url"]:
                    mlflow.set_tag("minio_url", result["minio_url"])

                results.append({**exp, **result})

                status = "[OK]" if result["success"] else "[FAIL]"
                score = f"score={result['validation_score']:.3f}" if result["validation_score"] else ""
                print(f"  {status} {score}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({**exp, "success": False, "error": str(e)})

    # Summary
    print("\n" + "="*60)
    print("HIGH QUALITY BATCH SUMMARY")
    print("="*60)
    successes = sum(1 for r in results if r.get("success"))
    scores = [r["validation_score"] for r in results if r.get("validation_score")]

    print(f"Total: {len(results)}")
    print(f"Success: {successes} ({100*successes/len(results):.1f}%)")
    if scores:
        print(f"Avg Score: {sum(scores)/len(scores):.3f}")
        print(f"Best Score: {max(scores):.3f}")


if __name__ == "__main__":
    main()
