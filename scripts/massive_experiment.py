#!/usr/bin/env python3
"""
Massive Experiment Runner for ComfyGen
======================================

Systematically tests combinations of:
- Checkpoints (Pony Realism, etc.)
- Samplers (euler, euler_ancestral, dpmpp_2m_sde, heun, etc.)
- CFG values (4.0 - 8.0)
- Steps (30, 50, 70, 100, 150)
- LoRAs (various at different strengths)
- Subjects (ethnicities, poses, scenarios)

Logs everything to MLflow for analysis.

Usage:
    python massive_experiment.py                    # Run all experiments
    python massive_experiment.py --count 50         # Run first 50
    python massive_experiment.py --dry-run          # Preview without running
    python massive_experiment.py --resume           # Resume from last run
    python massive_experiment.py --category solo    # Run only solo experiments
"""

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import mlflow

# =============================================================================
# CONFIGURATION
# =============================================================================

MLFLOW_URI = "http://192.168.1.215:5000"
EXPERIMENT_NAME = "comfygen-massive-sweep"
COMFYUI_URL = "http://192.168.1.215:8188"
OUTPUT_DIR = Path("/tmp/massive_experiments")
GENERATE_SCRIPT = Path(__file__).parent.parent / "generate.py"

# Progress tracking
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

# =============================================================================
# PARAMETER SPACE
# =============================================================================

CHECKPOINTS = [
    "ponyRealism_V22.safetensors",
    # Add more checkpoints as available
]

SAMPLERS = [
    "euler",
    "euler_ancestral",
    "dpmpp_2m_sde",
    "dpmpp_2m",
    "dpmpp_sde",
    "heun",
    "ddim",
    "uni_pc",
]

SCHEDULERS = [
    "karras",
    "normal",
    "exponential",
]

CFG_VALUES = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]

STEP_VALUES = [30, 50, 70, 100, 150]

# LoRAs with recommended strength ranges
LORAS = [
    None,  # No LoRA baseline
    ("zy_AmateurStyle_v2.safetensors", [0.2, 0.3, 0.4, 0.5]),
    # Add more LoRAs as needed
]

# =============================================================================
# SUBJECT VARIATIONS
# =============================================================================

ETHNICITIES = [
    ("asian", "korean"),
    ("asian", "japanese"),
    ("asian", "chinese"),
    ("asian", "thai"),
    ("asian", "vietnamese"),
    ("caucasian", "american"),
    ("caucasian", "european"),
    ("caucasian", "russian"),
    ("latina", "brazilian"),
    ("latina", "colombian"),
    ("black", "african american"),
    ("black", "caribbean"),
    ("indian", "south asian"),
    ("middle eastern", "persian"),
    ("mixed", "multiracial"),
]

# Scenario templates with positive/negative prompts
SCENARIOS = {
    # === SOLO ===
    "solo_portrait": {
        "category": "solo",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, beautiful face, {pose}, bedroom, natural light, realistic skin, skin pores",
        "negative": "score_6, worst quality, blurry, cartoon, anime, 3d, airbrushed, fake",
        "poses": ["looking at viewer", "side profile", "from behind looking over shoulder"],
    },
    "solo_nude": {
        "category": "solo",
        "prompt": "score_9, score_8_up, rating_explicit, photo, nude {ethnicity} woman, {subtype}, beautiful face, {pose}, full body, bedroom, soft lighting, realistic skin",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed, clothed",
        "poses": ["standing", "lying on bed", "sitting", "kneeling"],
    },

    # === BLOWJOB VARIATIONS ===
    "bj_pov": {
        "category": "oral",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, beautiful face, pov blowjob, big white cock in mouth, eye contact, {pose}, bedroom, natural light, realistic skin",
        "negative": "score_6, worst quality, blurry, cartoon, anime, 3d, airbrushed, fake",
        "poses": ["looking up at viewer", "eyes closed enjoying", "messy hair"],
    },
    "bj_side": {
        "category": "oral",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, blowjob side view, sucking cock, {pose}, hand on shaft, bedroom, soft light",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["balls visible", "two hands", "licking tip"],
    },
    "bj_deepthroat": {
        "category": "oral",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, deepthroat, cock deep in mouth, {pose}, sloppy, saliva, tears, bedroom",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["gagging", "mascara running", "hand on back of head"],
    },

    # === CUMSHOT VARIATIONS ===
    "facial_cumshot": {
        "category": "cumshot",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, facial cumshot, cum on face, {pose}, messy, bedroom, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed, clean face",
        "poses": ["mouth open tongue out", "eyes closed", "smiling with cum"],
    },
    "body_cumshot": {
        "category": "cumshot",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, cum on {pose}, messy, satisfied expression, bedroom",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed, clean",
        "poses": ["breasts", "stomach", "back"],
    },

    # === SEX POSITIONS ===
    "missionary": {
        "category": "sex",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, missionary position, {pose}, man on top, bedroom, intimate, realistic skin",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["legs spread", "legs wrapped around", "eye contact"],
    },
    "doggy": {
        "category": "sex",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, doggy style, {pose}, from behind, ass up, bedroom, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["looking back", "face down", "arched back"],
    },
    "cowgirl": {
        "category": "sex",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, cowgirl position, riding, {pose}, on top, bedroom, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["bouncing", "grinding", "leaning forward"],
    },
    "reverse_cowgirl": {
        "category": "sex",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, reverse cowgirl, {pose}, ass view, riding cock, bedroom",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["looking back", "hands on thighs", "bouncing"],
    },

    # === GROUP SCENARIOS ===
    "threesome_ffm": {
        "category": "group",
        "prompt": "score_9, score_8_up, rating_explicit, photo, two {ethnicity} women, threesome ffm, {pose}, one man, bedroom, intimate, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["one riding one sucking", "both licking cock", "kissing while fucking"],
    },
    "threesome_mmf": {
        "category": "group",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, threesome mmf, {pose}, two men, spitroast, bedroom",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["one in mouth one behind", "double handjob", "between two cocks"],
    },
    "gangbang": {
        "category": "group",
        "prompt": "score_9, score_8_up, rating_explicit, photo, {ethnicity} woman, {subtype}, gangbang, {pose}, multiple men, surrounded by cocks, bedroom",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed",
        "poses": ["center of attention", "on knees", "being passed around"],
    },

    # === LESBIAN ===
    "lesbian_kissing": {
        "category": "lesbian",
        "prompt": "score_9, score_8_up, rating_explicit, photo, two women, {ethnicity} and caucasian, lesbian kiss, {pose}, nude, intimate, bedroom, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed, man",
        "poses": ["passionate kiss", "tongue kiss", "gentle kiss"],
    },
    "lesbian_oral": {
        "category": "lesbian",
        "prompt": "score_9, score_8_up, rating_explicit, photo, two women, {ethnicity} woman receiving oral, {pose}, cunnilingus, bedroom, intimate, realistic",
        "negative": "score_6, worst quality, blurry, cartoon, anime, airbrushed, man, cock",
        "poses": ["lying back moaning", "sitting on face", "69 position"],
    },
}

# =============================================================================
# EXPERIMENT GENERATION
# =============================================================================

def generate_experiment_matrix(target_count: int = 300) -> List[Dict[str, Any]]:
    """
    Generate strategic experiment combinations.

    Instead of full cartesian product (184k+), we use stratified sampling:
    1. Cover ALL samplers with equal representation
    2. Cover ALL categories with equal representation
    3. Cover diverse ethnicities
    4. Sample CFG and steps strategically (key values, not all)
    """
    experiments = []
    exp_id = 0

    # Key CFG values to test (covers range, focuses on known sweet spot)
    KEY_CFGS = [5.0, 5.5, 6.0, 7.0]  # 4 values

    # Key step values
    KEY_STEPS = [50, 70, 100]  # 3 values

    # Calculate how many experiments per sampler/category combo
    num_samplers = len(SAMPLERS)
    num_categories = len(set(s["category"] for s in SCENARIOS.values()))
    experiments_per_combo = max(1, target_count // (num_samplers * num_categories))

    print(f"  Target: {target_count}, {num_samplers} samplers x {num_categories} categories")
    print(f"  Experiments per sampler/category: {experiments_per_combo}")

    # Group scenarios by category
    scenarios_by_category = {}
    for name, scenario in SCENARIOS.items():
        cat = scenario["category"]
        if cat not in scenarios_by_category:
            scenarios_by_category[cat] = []
        scenarios_by_category[cat].append((name, scenario))

    for sampler in SAMPLERS:
        for category, cat_scenarios in scenarios_by_category.items():
            # Distribute experiments across this category
            for _ in range(experiments_per_combo):
                # Random selections within constraints
                checkpoint = random.choice(CHECKPOINTS)
                scheduler = random.choice(SCHEDULERS)
                cfg = random.choice(KEY_CFGS)
                steps = random.choice(KEY_STEPS)
                lora_config = random.choice(LORAS)

                scenario_name, scenario = random.choice(cat_scenarios)
                ethnicity, subtype = random.choice(ETHNICITIES)
                pose = random.choice(scenario.get("poses", [""]))

                exp = {
                    "id": exp_id,
                    "checkpoint": checkpoint,
                    "sampler": sampler,
                    "scheduler": scheduler,
                    "cfg": cfg,
                    "steps": steps,
                    "lora": lora_config,
                    "scenario": scenario_name,
                    "category": category,
                    "ethnicity": ethnicity,
                    "subtype": subtype,
                    "pose": pose,
                    "prompt_template": scenario["prompt"],
                    "negative_template": scenario["negative"],
                }
                experiments.append(exp)
                exp_id += 1

    # Shuffle to randomize order
    random.shuffle(experiments)

    # Re-assign IDs after shuffle
    for i, exp in enumerate(experiments):
        exp["id"] = i

    return experiments


def build_prompt(exp: Dict[str, Any]) -> tuple[str, str]:
    """Build the actual prompt from template and variables."""
    prompt = exp["prompt_template"].format(
        ethnicity=exp["ethnicity"],
        subtype=exp["subtype"],
        pose=exp["pose"],
    )
    negative = exp["negative_template"]
    return prompt, negative


def generate_output_filename(exp: Dict[str, Any]) -> str:
    """Generate descriptive filename for the output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    lora_str = "nolora" if exp["lora"] is None else exp["lora"][0].split(".")[0][:10]
    return f"{timestamp}_{exp['id']:04d}_{exp['scenario']}_{exp['ethnicity']}_{exp['sampler']}_cfg{exp['cfg']}_s{exp['steps']}_{lora_str}.png"


# =============================================================================
# EXPERIMENT EXECUTION
# =============================================================================

def run_experiment(exp: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
    """Run a single experiment and return results."""

    prompt, negative = build_prompt(exp)
    output_file = OUTPUT_DIR / generate_output_filename(exp)

    # Build command
    cmd = [
        sys.executable, str(GENERATE_SCRIPT),
        "--workflow", "workflows/pony-realism.json",
        "--prompt", prompt,
        "--negative-prompt", negative,
        "--steps", str(exp["steps"]),
        "--cfg", str(exp["cfg"]),
        "--sampler", exp["sampler"],
        "--scheduler", exp["scheduler"],
        "--output", str(output_file),
    ]

    # Add LoRA if specified
    if exp["lora"] is not None:
        lora_name, strengths = exp["lora"]
        strength = random.choice(strengths) if isinstance(strengths, list) else strengths
        cmd.extend(["--lora", f"{lora_name}:{strength}"])
        exp["lora_strength"] = strength

    if dry_run:
        print(f"[DRY RUN] Would run: {' '.join(cmd[:6])}...")
        return {"status": "dry_run", "exp": exp}

    print(f"[{exp['id']:04d}] Running {exp['scenario']} / {exp['ethnicity']} / {exp['sampler']} / cfg={exp['cfg']} / steps={exp['steps']}")

    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start_time

        if result.returncode == 0:
            # Parse output for scores
            output = result.stdout
            scores = parse_scores(output)

            return {
                "status": "success",
                "duration": duration,
                "output_file": str(output_file),
                "scores": scores,
                "exp": exp,
            }
        else:
            error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
            print(f"  [ERROR] Return code: {result.returncode}")
            print(f"  [ERROR] {error_msg[:200]}")
            return {
                "status": "error",
                "error": error_msg,
                "exp": exp,
            }
    except subprocess.TimeoutExpired:
        print("  [TIMEOUT] Experiment timed out after 300s")
        return {"status": "timeout", "exp": exp}
    except Exception as e:
        print(f"  [EXCEPTION] {e}")
        return {"status": "exception", "error": str(e), "exp": exp}


def parse_scores(output: str) -> Dict[str, float]:
    """Parse CLIP scores from generate.py output."""
    scores = {}
    for line in output.split("\n"):
        if "Positive:" in line:
            try:
                scores["positive"] = float(line.split("Positive:")[1].split()[0])
            except:
                pass
        if "Negative:" in line:
            try:
                scores["negative"] = float(line.split("Negative:")[1].split()[0])
            except:
                pass
        if "Delta:" in line:
            try:
                scores["delta"] = float(line.split("Delta:")[1].split()[0])
            except:
                pass
    return scores


def log_to_mlflow(result: Dict[str, Any]):
    """Log experiment result to MLflow."""
    if result["status"] != "success":
        return

    exp = result["exp"]

    with mlflow.start_run(run_name=f"exp_{exp['id']:04d}_{exp['scenario']}"):
        # Parameters
        mlflow.log_param("experiment_id", exp["id"])
        mlflow.log_param("checkpoint", exp["checkpoint"])
        mlflow.log_param("sampler", exp["sampler"])
        mlflow.log_param("scheduler", exp["scheduler"])
        mlflow.log_param("cfg", exp["cfg"])
        mlflow.log_param("steps", exp["steps"])
        mlflow.log_param("scenario", exp["scenario"])
        mlflow.log_param("category", exp["category"])
        mlflow.log_param("ethnicity", exp["ethnicity"])
        mlflow.log_param("subtype", exp["subtype"])
        mlflow.log_param("pose", exp["pose"])

        if exp.get("lora"):
            mlflow.log_param("lora_name", exp["lora"][0])
            mlflow.log_param("lora_strength", exp.get("lora_strength", 0))
        else:
            mlflow.log_param("lora_name", "none")
            mlflow.log_param("lora_strength", 0)

        # Metrics
        mlflow.log_metric("duration_seconds", result["duration"])
        scores = result.get("scores", {})
        if scores.get("positive"):
            mlflow.log_metric("clip_positive", scores["positive"])
        if scores.get("negative"):
            mlflow.log_metric("clip_negative", scores["negative"])
        if scores.get("delta"):
            mlflow.log_metric("clip_delta", scores["delta"])

        # Tags
        mlflow.set_tag("status", result["status"])
        mlflow.set_tag("output_file", result.get("output_file", ""))


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

def load_progress() -> Dict[str, Any]:
    """Load progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed": [], "failed": [], "last_id": -1}


def save_progress(progress: Dict[str, Any]):
    """Save progress to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run massive experiment sweep")
    parser.add_argument("--count", type=int, default=300, help="Target number of experiments (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without running")
    parser.add_argument("--resume", action="store_true", help="Resume from last run")
    parser.add_argument("--category", type=str, help="Filter by category (solo, oral, sex, group, lesbian)")
    parser.add_argument("--shuffle", action="store_true", help="Randomize experiment order")
    parser.add_argument("--sampler", type=str, help="Filter to specific sampler")
    args = parser.parse_args()

    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # Generate experiments
    print("[....] Generating experiment matrix...")
    all_experiments = generate_experiment_matrix(target_count=args.count)
    # Filter by category if specified
    if args.category:
        all_experiments = [e for e in all_experiments if e["category"] == args.category]
        print(f"[OK] Filtered to {len(all_experiments)} {args.category} experiments")

    # Filter by sampler if specified
    if args.sampler:
        all_experiments = [e for e in all_experiments if e["sampler"] == args.sampler]
        print(f"[OK] Filtered to {len(all_experiments)} {args.sampler} experiments")

    # Load progress for resume
    progress = load_progress() if args.resume else {"completed": [], "failed": [], "last_id": -1}

    if args.resume:
        all_experiments = [e for e in all_experiments if e["id"] not in progress["completed"]]
        print(f"[OK] Resuming: {len(all_experiments)} experiments remaining")

    # Dry run summary
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN SUMMARY")
        print("=" * 60)

        categories = {}
        samplers = {}
        for exp in all_experiments:
            categories[exp["category"]] = categories.get(exp["category"], 0) + 1
            samplers[exp["sampler"]] = samplers.get(exp["sampler"], 0) + 1

        print("\nBy Category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count}")

        print("\nBy Sampler:")
        for samp, count in sorted(samplers.items()):
            print(f"  {samp}: {count}")

        print(f"\nTotal experiments: {len(all_experiments)}")
        print(f"Estimated time: {len(all_experiments) * 30 / 60:.1f} - {len(all_experiments) * 60 / 60:.1f} minutes")
        return

    # Run experiments
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print(f"RUNNING {len(all_experiments)} EXPERIMENTS")
    print("=" * 60 + "\n")

    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, exp in enumerate(all_experiments):
        print(f"\n[{i+1}/{len(all_experiments)}] ", end="")

        result = run_experiment(exp, dry_run=args.dry_run)

        if result["status"] == "success":
            success_count += 1
            progress["completed"].append(exp["id"])
            log_to_mlflow(result)
            print(f"  [OK] {result['duration']:.1f}s - Scores: {result.get('scores', {})}")
        else:
            error_count += 1
            progress["failed"].append(exp["id"])
            print(f"  [FAIL] {result['status']}")

        progress["last_id"] = exp["id"]
        save_progress(progress)

        # Brief pause between experiments
        time.sleep(1)

    # Final summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("EXPERIMENT SWEEP COMPLETE")
    print("=" * 60)
    print(f"Total: {len(all_experiments)}")
    print(f"Success: {success_count}")
    print(f"Failed: {error_count}")
    print(f"Duration: {elapsed/60:.1f} minutes")
    print(f"Avg per experiment: {elapsed/max(1, len(all_experiments)):.1f}s")
    print(f"\nMLflow: {MLFLOW_URI}/#/experiments")
    print("=" * 60)


if __name__ == "__main__":
    main()
