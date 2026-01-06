#!/usr/bin/env python3
"""
Batch experiment runner for comfy-gen using the generate.py CLI.

Runs stratified experiments across parameter space and logs to MLflow.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

import mlflow

# MLflow setup
MLFLOW_URI = "http://192.168.1.162:5001"
EXPERIMENT_NAME = "comfy-gen-batch"

# Paths
COMFY_GEN_DIR = Path(__file__).parent.parent
GENERATE_PY = COMFY_GEN_DIR / "generate.py"
OUTPUT_DIR = Path("/tmp/batch_experiments")

# Parameter space
SAMPLERS = ["euler", "euler_ancestral", "dpmpp_2m_sde", "dpmpp_2m", "dpmpp_sde", "heun", "ddim", "uni_pc"]
CFG_VALUES = [4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]
STEP_VALUES = [30, 50, 70, 100]
SCHEDULERS = ["normal", "karras", "sgm_uniform"]

ETHNICITIES = [
    "asian woman", "japanese woman", "korean woman", "chinese woman",
    "caucasian woman", "european woman", "american woman",
    "latina woman", "mexican woman", "brazilian woman",
    "black woman", "african woman", "ebony woman",
    "indian woman", "middle eastern woman"
]

SCENARIOS = {
    "portrait": "beautiful face, looking at camera, soft lighting",
    "nude_standing": "full body, nude, standing pose, natural lighting",
    "nude_bedroom": "nude, lying on bed, bedroom setting, soft lighting",
    "topless": "topless, large natural breasts, casual pose",
    "lingerie": "sexy lingerie, seductive pose, bedroom",
    "shower": "wet skin, shower, water droplets, steam",
    "outdoor": "nude, outdoor setting, natural environment, sunlight",
    "solo_touch": "nude, touching herself sensually, intimate moment",
    "oral_pov": "pov blowjob, looking up at camera, eye contact",
    "doggy": "doggystyle sex, from behind, arched back",
    "cowgirl": "cowgirl position, riding, breasts bouncing",
    "missionary": "missionary sex, legs spread, intimate",
    "cumshot_facial": "facial cumshot, cum on face, eyes closed",
    "cumshot_body": "cum on breasts, cum on stomach, post-sex",
    "threesome_ffm": "threesome ffm, two women one man, group sex",
}

LORAS = [
    None,  # baseline without LoRA
    ("zy_AmateurStyle_v2.safetensors", 0.3),
    ("zy_AmateurStyle_v2.safetensors", 0.5),
]

def build_prompt(ethnicity: str, scenario_key: str, scenario_desc: str) -> str:
    """Build a full prompt with quality tags."""
    return f"score_9, score_8_up, photo, {ethnicity}, {scenario_desc}, realistic, high quality"

def run_experiment(
    prompt: str,
    sampler: str,
    cfg: float,
    steps: int,
    scheduler: str,
    lora,
    output_path: Path,
) -> dict:
    """Run a single generation experiment."""

    cmd = [
        sys.executable, str(GENERATE_PY),
        "--workflow", "workflows/pony-realism.json",
        "--prompt", prompt,
        "--steps", str(steps),
        "--cfg", str(cfg),
        "--sampler", sampler,
        "--scheduler", scheduler,
        "--output", str(output_path),
    ]

    if lora:
        lora_name, lora_strength = lora
        cmd.extend(["--lora", f"{lora_name}:{lora_strength}"])

    print(f"[RUN] {sampler} cfg={cfg} steps={steps} sched={scheduler}")

    result = subprocess.run(
        cmd,
        cwd=str(COMFY_GEN_DIR),
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
    )

    # Parse output for MinIO URL and validation score
    output = result.stdout + result.stderr
    minio_url = None
    validation_score = None
    passed = False

    for line in output.split("\n"):
        if "http://192.168.1.215:9000/comfy-gen/" in line and ".png" in line and ".json" not in line:
            # Extract URL
            import re
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
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

def generate_experiment_combinations(target_count: int = 200) -> list:
    """Generate stratified sample of experiments."""

    experiments = []

    # Ensure coverage of all samplers and CFG values
    for sampler in SAMPLERS:
        for cfg in CFG_VALUES:
            # Sample a subset of other params
            steps = random.choice(STEP_VALUES)
            scheduler = random.choice(SCHEDULERS)
            ethnicity = random.choice(ETHNICITIES)
            scenario_key, scenario_desc = random.choice(list(SCENARIOS.items()))
            lora = random.choice(LORAS)

            experiments.append({
                "sampler": sampler,
                "cfg": cfg,
                "steps": steps,
                "scheduler": scheduler,
                "ethnicity": ethnicity,
                "scenario_key": scenario_key,
                "scenario_desc": scenario_desc,
                "lora": lora,
            })

    # Add more random combinations to reach target
    while len(experiments) < target_count:
        experiments.append({
            "sampler": random.choice(SAMPLERS),
            "cfg": random.choice(CFG_VALUES),
            "steps": random.choice(STEP_VALUES),
            "scheduler": random.choice(SCHEDULERS),
            "ethnicity": random.choice(ETHNICITIES),
            "scenario_key": random.choice(list(SCENARIOS.keys())),
            "scenario_desc": SCENARIOS[random.choice(list(SCENARIOS.keys()))],
            "lora": random.choice(LORAS),
        })

    # Fix scenario_desc for added experiments
    for exp in experiments:
        exp["scenario_desc"] = SCENARIOS[exp["scenario_key"]]

    random.shuffle(experiments)
    return experiments[:target_count]

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run batch experiments")
    parser.add_argument("--count", type=int, default=100, help="Number of experiments to run")
    parser.add_argument("--dry-run", action="store_true", help="Print experiments without running")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate experiments
    experiments = generate_experiment_combinations(args.count)
    print(f"[INFO] Generated {len(experiments)} experiments")

    if args.dry_run:
        for i, exp in enumerate(experiments[:10]):
            print(f"  {i+1}. {exp['sampler']} cfg={exp['cfg']} steps={exp['steps']} {exp['ethnicity']} - {exp['scenario_key']}")
        print(f"  ... and {len(experiments) - 10} more")
        return

    # Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    results = []

    for i, exp in enumerate(experiments):
        print(f"\n[EXPERIMENT {i+1}/{len(experiments)}]")

        prompt = build_prompt(exp["ethnicity"], exp["scenario_key"], exp["scenario_desc"])
        output_path = OUTPUT_DIR / f"exp_{i:04d}.png"

        try:
            with mlflow.start_run():
                # Log parameters
                mlflow.log_param("sampler", exp["sampler"])
                mlflow.log_param("cfg", exp["cfg"])
                mlflow.log_param("steps", exp["steps"])
                mlflow.log_param("scheduler", exp["scheduler"])
                mlflow.log_param("ethnicity", exp["ethnicity"])
                mlflow.log_param("scenario", exp["scenario_key"])
                mlflow.log_param("lora", exp["lora"][0] if exp["lora"] else "none")
                mlflow.log_param("lora_strength", exp["lora"][1] if exp["lora"] else 0.0)
                mlflow.log_param("prompt", prompt[:250])  # Truncate for display

                # Run experiment
                result = run_experiment(
                    prompt=prompt,
                    sampler=exp["sampler"],
                    cfg=exp["cfg"],
                    steps=exp["steps"],
                    scheduler=exp["scheduler"],
                    lora=exp["lora"],
                    output_path=output_path,
                )

                # Log metrics
                mlflow.log_metric("success", 1 if result["success"] else 0)
                mlflow.log_metric("validation_passed", 1 if result["validation_passed"] else 0)
                if result["validation_score"]:
                    mlflow.log_metric("validation_score", result["validation_score"])

                # Log URL as tag
                if result["minio_url"]:
                    mlflow.set_tag("minio_url", result["minio_url"])

                results.append({**exp, **result})

                status = "[OK]" if result["success"] else "[FAIL]"
                score = f"score={result['validation_score']:.3f}" if result["validation_score"] else "no score"
                print(f"  {status} {score}")

        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({**exp, "success": False, "error": str(e)})

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    successes = sum(1 for r in results if r.get("success"))
    print(f"Total: {len(results)}")
    print(f"Success: {successes} ({100*successes/len(results):.1f}%)")

    # Save results
    results_file = OUTPUT_DIR / "results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {results_file}")

if __name__ == "__main__":
    main()
