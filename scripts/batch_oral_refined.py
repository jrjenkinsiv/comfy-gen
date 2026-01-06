#!/usr/bin/env python3
"""
Refined oral/handjob batch - 10 high-quality varied shots.
Focus: Multiple angles (not just POV), realism, varied compositions.
"""

import random
import subprocess
import sys
from pathlib import Path

import mlflow

MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfy-gen-oral-refined"
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/batch_oral_refined")

# High quality settings - pushing for max detail
HQ_SAMPLERS = ["dpmpp_2m_sde", "dpmpp_2m", "euler_ancestral"]
HQ_CFGS = [6.0, 6.5, 7.0]
HQ_STEPS = [120, 150]  # Higher steps for refinement
HQ_SCHEDULERS = ["karras"]

# Quality prefix/suffix for Pony Realism
QUALITY_PREFIX = "score_9, score_8_up, score_7_up, source_photo, raw photo, photorealistic, hyperrealistic, ultra detailed, masterpiece"
QUALITY_SUFFIX = "8k uhd, high resolution, professional photography, sharp focus, intricate details, studio lighting"

BASE_NEGATIVE = "score_6, score_5, score_4, blurry, low quality, jpeg artifacts, pixelated, grainy, bad anatomy, deformed, disfigured, mutation, extra limbs, watermark, signature, text, logo, cartoon, anime, illustration, drawing, painting, 3d render, cgi"

# Diverse subjects
SUBJECTS = [
    "beautiful young japanese woman, porcelain skin, dark silky hair, delicate features",
    "gorgeous korean model, flawless skin, elegant bone structure, natural beauty",
    "stunning latina woman, caramel skin, voluptuous curves, passionate expression",
    "attractive caucasian woman, fair complexion, striking blue eyes, natural makeup",
    "beautiful black woman, rich ebony skin, full lips, statuesque beauty",
    "exotic thai woman, warm golden skin, expressive dark eyes, graceful",
    "mixed race woman, unique features, honey skin tone, captivating beauty",
]

# 10 carefully designed scenes - varied angles and compositions
SCENES = [
    {
        "name": "side_angle_oral",
        "prompt": "side angle view, woman giving oral sex, mouth around shaft, side profile visible, intimate bedroom setting, soft warm lighting, {subject}, sensual expression, wet lips, natural pose",
        "negative_add": "pov, first person view",
    },
    {
        "name": "kneeling_oral_3quarter",
        "prompt": "three quarter view, woman kneeling giving blowjob, looking up with eye contact, {subject}, kneeling position, hands on thighs, bedroom floor, soft diffused lighting, intimate atmosphere",
        "negative_add": "pov, overhead view",
    },
    {
        "name": "lying_oral_side",
        "prompt": "side view, woman lying on bed giving oral, {subject}, relaxed pose on silk sheets, one hand stroking shaft, bedroom setting, warm ambient light, sensual mood",
        "negative_add": "standing, kneeling",
    },
    {
        "name": "handjob_front_view",
        "prompt": "front view, woman giving handjob with both hands, {subject}, sitting on bed, focused expression, hands wrapped around erect penis, natural lighting, intimate bedroom",
        "negative_add": "pov, oral",
    },
    {
        "name": "handjob_side_profile",
        "prompt": "side profile view, woman giving handjob, {subject}, seated position, one hand stroking, other hand on chest, soft studio lighting, clean background",
        "negative_add": "pov, front view",
    },
    {
        "name": "oral_overhead_angle",
        "prompt": "overhead angle, woman giving oral sex looking up at camera, {subject}, on knees, hands on thighs of partner, eye contact with viewer, dramatic lighting from above",
        "negative_add": "side view, flat angle",
    },
    {
        "name": "deepthroat_side",
        "prompt": "side angle, deepthroat, {subject}, full insertion, throat bulge visible, watery eyes, mascara slightly smudged, intense expression, professional photography",
        "negative_add": "shallow, pov",
    },
    {
        "name": "handjob_closeup_hands",
        "prompt": "medium close up, handjob focus on hands, {subject}, delicate fingers wrapped around shaft, manicured nails, skin texture detail, soft bokeh background",
        "negative_add": "face focus, wide shot",
    },
    {
        "name": "licking_shaft_side",
        "prompt": "side view, woman licking shaft, tongue extended, {subject}, teasing expression, saliva trail, sensual pose, soft rim lighting, intimate setting",
        "negative_add": "full insertion, deepthroat",
    },
    {
        "name": "two_hand_twist_front",
        "prompt": "front view, two-handed handjob with twist motion, {subject}, both hands gripping shaft, motion blur on hands, focused expression, natural bedroom lighting",
        "negative_add": "single hand, oral",
    },
]

# LoRA combinations for realism - stacking multiple
LORA_COMBOS = [
    # Realism focus
    [("zy_AmateurStyle_v2.safetensors", 0.4), ("add_detail.safetensors", 0.3)],
    # Skin detail focus
    [("zy_AmateurStyle_v2.safetensors", 0.35), ("realora_skin.safetensors", 0.3)],
    # High detail
    [("zy_AmateurStyle_v2.safetensors", 0.4), ("more_details.safetensors", 0.25)],
    # Pure amateur style
    [("zy_AmateurStyle_v2.safetensors", 0.5)],
    # Skin texture emphasis
    [("polyhedron_skin.safetensors", 0.4), ("add_detail.safetensors", 0.3)],
]


def build_prompt(subject: str, scene: dict) -> tuple:
    """Build detailed prompt with subject inserted."""
    prompt_template = scene["prompt"]
    prompt_body = prompt_template.replace("{subject}", subject)

    full_prompt = f"{QUALITY_PREFIX}, {prompt_body}, {QUALITY_SUFFIX}"
    full_negative = f"{BASE_NEGATIVE}, {scene['negative_add']}"

    return full_prompt, full_negative


def run_generation(
    prompt: str,
    negative: str,
    sampler: str,
    cfg: float,
    steps: int,
    scheduler: str,
    loras: list,
    output_path: Path,
) -> dict:
    """Run generation with multiple LoRAs."""

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

    # Add multiple LoRAs
    for lora_name, lora_strength in loras:
        cmd.extend(["--lora", f"{lora_name}:{lora_strength}"])

    lora_str = "+".join([f"{l[0].split('.')[0]}@{l[1]}" for l in loras])
    print(f"  {sampler} s={steps} cfg={cfg} LoRAs: {lora_str}")

    result = subprocess.run(
        cmd,
        cwd=str(COMFY_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=600,
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


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Refined oral/handjob batch")
    parser.add_argument("--count", type=int, default=10, help="Number of images")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate experiments - one per scene, varied subjects and LoRAs
    experiments = []
    for i, scene in enumerate(SCENES[:args.count]):
        subject = random.choice(SUBJECTS)
        loras = random.choice(LORA_COMBOS)

        experiments.append({
            "scene": scene,
            "subject": subject,
            "sampler": random.choice(HQ_SAMPLERS),
            "cfg": random.choice(HQ_CFGS),
            "steps": random.choice(HQ_STEPS),
            "scheduler": random.choice(HQ_SCHEDULERS),
            "loras": loras,
        })

    print(f"[INFO] {len(experiments)} refined oral/handjob experiments")
    print(f"[INFO] Steps: {HQ_STEPS}, CFG: {HQ_CFGS}, Samplers: {HQ_SAMPLERS}")
    print("[INFO] Using multiple stacked LoRAs for realism")

    if args.dry_run:
        for i, exp in enumerate(experiments):
            scene_name = exp["scene"]["name"]
            lora_str = "+".join([l[0].split(".")[0] for l in exp["loras"]])
            print(f"  {i+1}. {scene_name} - {exp['sampler']} s={exp['steps']} - {lora_str}")
        return

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    results = []
    for i, exp in enumerate(experiments):
        scene_name = exp["scene"]["name"]
        print(f"\n[{i+1}/{len(experiments)}] {scene_name}")

        prompt, negative = build_prompt(exp["subject"], exp["scene"])
        output_path = OUTPUT_DIR / f"oral_{i:02d}_{scene_name}.png"

        try:
            with mlflow.start_run():
                mlflow.log_param("scene", scene_name)
                mlflow.log_param("subject", exp["subject"][:50])
                mlflow.log_param("sampler", exp["sampler"])
                mlflow.log_param("cfg", exp["cfg"])
                mlflow.log_param("steps", exp["steps"])
                mlflow.log_param("loras", str([l[0] for l in exp["loras"]]))
                mlflow.log_param("prompt_preview", prompt[:200])

                result = run_generation(
                    prompt=prompt,
                    negative=negative,
                    sampler=exp["sampler"],
                    cfg=exp["cfg"],
                    steps=exp["steps"],
                    scheduler=exp["scheduler"],
                    loras=exp["loras"],
                    output_path=output_path,
                )

                mlflow.log_metric("success", 1 if result["success"] else 0)
                if result["validation_score"]:
                    mlflow.log_metric("validation_score", result["validation_score"])
                if result["minio_url"]:
                    mlflow.set_tag("minio_url", result["minio_url"])

                results.append({**exp, **result})

                status = "[OK]" if result["success"] else "[FAIL]"
                score = f"score={result['validation_score']:.3f}" if result["validation_score"] else ""
                print(f"  {status} {score}")
                if result["minio_url"]:
                    print(f"  URL: {result['minio_url']}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({**exp, "success": False, "error": str(e)})

    # Summary
    print("\n" + "="*60)
    print("REFINED ORAL/HANDJOB BATCH SUMMARY")
    print("="*60)
    successes = sum(1 for r in results if r.get("success"))
    scores = [r["validation_score"] for r in results if r.get("validation_score")]

    print(f"Total: {len(results)}")
    print(f"Success: {successes} ({100*successes/len(results):.1f}%)")
    if scores:
        print(f"Avg Score: {sum(scores)/len(scores):.3f}")
        print(f"Best Score: {max(scores):.3f}")

    print("\nURLs:")
    for r in results:
        if r.get("minio_url"):
            print(f"  {r['scene']['name']}: {r['minio_url']}")


if __name__ == "__main__":
    main()
