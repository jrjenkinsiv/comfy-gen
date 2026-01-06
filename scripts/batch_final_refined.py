#!/usr/bin/env python3
"""
Final refined batch - 15 high-quality images with:
- Better prompt adherence (explicit action verbs)
- Cumshots using realcumv6.55 + triggers
- Mixed oral/handjob/cumshot scenes
- Varied angles (no POV only)
- Full body in frame (legs visible)

Key learnings applied:
- Use explicit trigger words for LoRAs
- Negative prompt TS/trans features
- Full body framing to avoid missing legs
- Use "cumshot" trigger for NSFW POV All In One LoRA
"""

import random
import subprocess
import sys
from pathlib import Path

import mlflow

MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfy-gen-final-refined"
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/batch_final_refined")

# High quality settings
HQ_SAMPLERS = ["dpmpp_2m_sde", "dpmpp_2m"]
HQ_CFGS = [6.0, 6.5, 7.0]
HQ_STEPS = [120, 150]
HQ_SCHEDULERS = ["karras"]

# Quality prefix/suffix for Pony Realism
QUALITY_PREFIX = "score_9, score_8_up, score_7_up, source_photo, raw photo, photorealistic, hyperrealistic, ultra detailed, masterpiece"
QUALITY_SUFFIX = "8k uhd, high resolution, professional photography, sharp focus, intricate details"

# Enhanced negative prompt - includes anatomy fixes
BASE_NEGATIVE = """score_6, score_5, score_4, blurry, low quality, jpeg artifacts, pixelated, grainy,
bad anatomy, deformed, disfigured, mutation, extra limbs, missing limbs, missing legs,
watermark, signature, text, logo, cartoon, anime, illustration, drawing, painting, 3d render, cgi,
trans, transgender, futanari, futa, hermaphrodite, shemale, dickgirl,
cropped, out of frame, cut off"""

# Diverse subjects - all female
SUBJECTS = [
    "beautiful young japanese woman, petite body, porcelain skin, dark silky hair, delicate feminine features, small natural breasts",
    "gorgeous korean model, slim body, flawless skin, elegant bone structure, natural beauty, perky breasts",
    "stunning latina woman, curvy body, caramel skin, voluptuous curves, passionate expression, large natural breasts",
    "attractive caucasian woman, athletic body, fair complexion, striking blue eyes, natural makeup, medium breasts",
    "beautiful black woman, fit body, rich ebony skin, full lips, statuesque beauty, natural curves",
    "exotic thai woman, slim body, warm golden skin, expressive dark eyes, graceful, small perky breasts",
    "mixed race woman, hourglass figure, unique features, honey skin tone, captivating beauty, full breasts",
]

# 15 carefully designed scenes with EXPLICIT ACTION VERBS
# Using LoRA trigger words for better adherence
SCENES = [
    # ===== CUMSHOTS (5 scenes) - Using realcum triggers =====
    {
        "name": "facial_cumshot_kneeling",
        "prompt": "cum on face, facial, cumshot, {subject}, kneeling woman receiving facial, eyes closed, mouth open, cum dripping from chin, thick white cum on cheeks, bedroom setting, full body visible including legs, soft lighting",
        "negative_add": "clean face, no cum",
        "loras": [("realcumv6.55.safetensors", 0.7), ("zy_AmateurStyle_v2.safetensors", 0.3)],
    },
    {
        "name": "cumshot_open_mouth",
        "prompt": "cum in mouth, cum on tongue, cumshot, {subject}, woman with mouth wide open receiving cum, tongue out, cum dripping, looking up at camera, three quarter view, full body kneeling pose, legs visible",
        "negative_add": "closed mouth",
        "loras": [("realcumv6.55.safetensors", 0.7), ("add_detail.safetensors", 0.3)],
    },
    {
        "name": "cum_on_tits",
        "prompt": "cum covered, cum on breasts, cumshot on chest, {subject}, woman with cum covering her breasts, thick ropes of cum, sitting on bed, full body visible, legs spread, satisfied expression",
        "negative_add": "clean chest",
        "loras": [("realcumv6.55.safetensors", 0.7), ("zy_AmateurStyle_v2.safetensors", 0.3)],
    },
    {
        "name": "post_facial_dripping",
        "prompt": "cum on face, cum dripping, after cumshot, {subject}, woman with fresh cum on face dripping down, cum on lips, cum on chin, side angle view, sitting on floor, full body including legs, messy hair",
        "negative_add": "dry, clean",
        "loras": [("realcumv6.55.safetensors", 0.8), ("realora_skin.safetensors", 0.2)],
    },
    {
        "name": "bukkake_face",
        "prompt": "excessive cum, bukkake, cum covered face, {subject}, woman covered in thick cum, multiple loads on face and hair, cum dripping everywhere, kneeling full body pose, overwhelmed expression",
        "negative_add": "clean, minimal cum",
        "loras": [("realcumv6.55.safetensors", 0.6), ("extreme_bukkake_pony.safetensors", 0.5)],
    },

    # ===== BLOWJOBS (5 scenes) - varied angles =====
    {
        "name": "blowjob_side_angle",
        "prompt": "blowjob, fellatio, oral sex, {subject}, side angle view of woman giving blowjob, mouth wrapped around shaft, one hand on base, profile visible, bedroom setting, woman kneeling full body visible",
        "negative_add": "pov, first person",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("zy_AmateurStyle_v2.safetensors", 0.4)],
    },
    {
        "name": "deepthroat_side",
        "prompt": "deepthroat, blowjob, {subject}, side view of woman deepthroating, full insertion, throat bulge, watery eyes, mascara running, intense concentration, kneeling on bed, full body framing",
        "negative_add": "shallow insertion, pov",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("add_detail.safetensors", 0.3)],
    },
    {
        "name": "licking_cock_side",
        "prompt": "licking cock, tongue on penis, {subject}, woman licking shaft from base to tip, tongue extended, teasing expression, looking at camera, three quarter angle, sitting position, legs tucked",
        "negative_add": "mouth closed",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.3)],
    },
    {
        "name": "blowjob_from_above",
        "prompt": "blowjob, oral sex from above angle, {subject}, overhead view of woman giving blowjob, looking up with eye contact, hands on thighs, kneeling between legs, full body visible from above",
        "negative_add": "side view, front view",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("zy_AmateurStyle_v2.safetensors", 0.35)],
    },
    {
        "name": "two_hand_blowjob",
        "prompt": "blowjob, two hands on shaft, {subject}, woman using both hands while giving oral, mouth on tip, hands stroking shaft, front three quarter view, kneeling position, full body visible",
        "negative_add": "single hand",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("add_detail.safetensors", 0.3)],
    },

    # ===== HANDJOBS (5 scenes) - varied angles =====
    {
        "name": "handjob_front_sitting",
        "prompt": "handjob, stroking penis, {subject}, woman giving handjob while sitting facing camera, both hands wrapped around shaft, focused expression, sitting on bed, full body including legs spread",
        "negative_add": "oral, blowjob",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("zy_AmateurStyle_v2.safetensors", 0.4)],
    },
    {
        "name": "handjob_side_profile",
        "prompt": "handjob, side profile view, {subject}, side view of woman stroking penis, one hand grip, other hand on her thigh, seated on edge of bed, full body visible, looking at shaft",
        "negative_add": "oral, front view",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("realora_skin.safetensors", 0.3)],
    },
    {
        "name": "handjob_closeup_realistic",
        "prompt": "handjob, detailed hands, {subject}, medium shot of woman giving handjob, fingers wrapped around erect penis, detailed skin texture, natural grip, bedroom background soft focus",
        "negative_add": "wide shot, full body",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("polyhedron_skin.safetensors", 0.4)],
    },
    {
        "name": "two_hand_twist_handjob",
        "prompt": "handjob, two handed grip, twist motion, {subject}, woman using both hands with twisting motion on shaft, concentrated expression, sitting cross legged, full body visible, intimate setting",
        "negative_add": "single hand, oral",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.5), ("add_detail.safetensors", 0.3)],
    },
    {
        "name": "handjob_cumshot",
        "prompt": "handjob, cumshot, ejaculation, cum on hands, {subject}, woman giving handjob at moment of cumshot, cum spurting, cum on her hands, surprised expression, three quarter view, full body",
        "negative_add": "no cum, clean",
        "loras": [("NsfwPovAllInOne_SDXL_mini.safetensors", 0.4), ("realcumv6.55.safetensors", 0.5)],
    },
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

    lora_str = "+".join([f"{l[0].split('.')[0][:15]}@{l[1]}" for l in loras])
    print(f"  {sampler} s={steps} cfg={cfg} LoRAs: {lora_str}")

    result = subprocess.run(
        cmd,
        cwd=str(COMFY_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=900,  # 15 min timeout for high step counts
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
        "stderr": result.stderr[-500:] if result.returncode != 0 else "",
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Final refined batch")
    parser.add_argument("--count", type=int, default=15, help="Number of images")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Use all 15 scenes or subset
    scenes_to_use = SCENES[:args.count]

    # Generate experiments
    experiments = []
    for i, scene in enumerate(scenes_to_use):
        subject = random.choice(SUBJECTS)

        experiments.append({
            "scene": scene,
            "subject": subject,
            "sampler": random.choice(HQ_SAMPLERS),
            "cfg": random.choice(HQ_CFGS),
            "steps": random.choice(HQ_STEPS),
            "scheduler": random.choice(HQ_SCHEDULERS),
        })

    print(f"[INFO] {len(experiments)} final refined experiments")
    print(f"[INFO] Steps: {HQ_STEPS}, CFG: {HQ_CFGS}")
    print("[INFO] Scenes: 5 cumshots, 5 blowjobs, 5 handjobs")
    print("[INFO] Using realcumv6.55 + NSFW POV All In One + stacked LoRAs")

    if args.dry_run:
        for i, exp in enumerate(experiments):
            scene_name = exp["scene"]["name"]
            loras = exp["scene"]["loras"]
            lora_str = "+".join([l[0].split(".")[0][:15] for l in loras])
            print(f"  {i+1}. {scene_name} - {lora_str}")
        return

    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    results = []
    for i, exp in enumerate(experiments):
        scene = exp["scene"]
        scene_name = scene["name"]
        print(f"\n[{i+1}/{len(experiments)}] {scene_name}")

        prompt, negative = build_prompt(exp["subject"], scene)
        output_path = OUTPUT_DIR / f"final_{i:02d}_{scene_name}.png"

        try:
            with mlflow.start_run():
                mlflow.log_param("scene", scene_name)
                mlflow.log_param("subject", exp["subject"][:50])
                mlflow.log_param("sampler", exp["sampler"])
                mlflow.log_param("cfg", exp["cfg"])
                mlflow.log_param("steps", exp["steps"])
                mlflow.log_param("loras", str([l[0] for l in scene["loras"]]))
                mlflow.log_param("prompt_preview", prompt[:300])

                result = run_generation(
                    prompt=prompt,
                    negative=negative,
                    sampler=exp["sampler"],
                    cfg=exp["cfg"],
                    steps=exp["steps"],
                    scheduler=exp["scheduler"],
                    loras=scene["loras"],
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
                if not result["success"] and result.get("stderr"):
                    print(f"  Error: {result['stderr'][:200]}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({**exp, "success": False, "error": str(e)})

    # Summary
    print("\n" + "="*60)
    print("FINAL REFINED BATCH SUMMARY")
    print("="*60)
    successes = sum(1 for r in results if r.get("success"))
    scores = [r["validation_score"] for r in results if r.get("validation_score")]

    print(f"Total: {len(results)}")
    print(f"Success: {successes} ({100*successes/len(results):.1f}%)")
    if scores:
        print(f"Avg Score: {sum(scores)/len(scores):.3f}")
        print(f"Best Score: {max(scores):.3f}")

    print("\nBy Category:")
    categories = {"cumshot": [], "blowjob": [], "handjob": []}
    for r in results:
        name = r["scene"]["name"]
        for cat in categories:
            if cat in name or (cat == "cumshot" and "facial" in name) or (cat == "cumshot" and "bukkake" in name):
                categories[cat].append(r)
                break

    for cat, items in categories.items():
        success = sum(1 for r in items if r.get("success"))
        print(f"  {cat}: {success}/{len(items)} success")

    print("\nAll URLs:")
    for r in results:
        if r.get("minio_url"):
            print(f"  {r['scene']['name']}: {r['minio_url']}")


if __name__ == "__main__":
    main()
