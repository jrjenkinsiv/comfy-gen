#!/usr/bin/env python3
"""
Migrate MLflow experiments from moira (SQLite) to cerebro (PostgreSQL).

This script:
1. Exports all experiments and runs from moira's MLflow (http://192.168.1.215:5000)
2. Imports them to cerebro's MLflow (http://192.168.1.162:5001)
3. Handles experiment name conflicts
4. Preserves all metrics, params, tags, and metadata
"""

import argparse
import sys
from typing import Any, Dict, List

import requests

MOIRA_MLFLOW = "http://192.168.1.215:5000"
CEREBRO_MLFLOW = "http://192.168.1.162:5001"


def get_experiments(uri: str) -> List[Dict[str, Any]]:
    """Get all experiments from an MLflow server."""
    resp = requests.get(f"{uri}/api/2.0/mlflow/experiments/search", params={"max_results": 100})
    resp.raise_for_status()
    return resp.json().get("experiments", [])


def get_runs(uri: str, experiment_id: str) -> List[Dict[str, Any]]:
    """Get all runs for an experiment."""
    resp = requests.post(
        f"{uri}/api/2.0/mlflow/runs/search", json={"experiment_ids": [experiment_id], "max_results": 1000}
    )
    resp.raise_for_status()
    return resp.json().get("runs", [])


def create_experiment(uri: str, name: str) -> str:
    """Create or restore experiment on destination server. Returns experiment_id."""
    # Check if exists (active)
    exps = get_experiments(uri)
    for exp in exps:
        if exp["name"] == name:
            print(f"  [OK] Experiment '{name}' already exists (id={exp['experiment_id']})")
            return exp["experiment_id"]

    # Check if deleted
    resp = requests.get(
        f"{uri}/api/2.0/mlflow/experiments/search", params={"max_results": 100, "view_type": "DELETED_ONLY"}
    )
    deleted_exps = resp.json().get("experiments", [])
    for exp in deleted_exps:
        if exp["name"] == name:
            print(f"  [OK] Restoring deleted experiment '{name}' (id={exp['experiment_id']})")
            requests.post(f"{uri}/api/2.0/mlflow/experiments/restore", json={"experiment_id": exp["experiment_id"]})
            return exp["experiment_id"]

    # Create new
    resp = requests.post(f"{uri}/api/2.0/mlflow/experiments/create", json={"name": name})
    resp.raise_for_status()
    exp_id = resp.json()["experiment_id"]
    print(f"  [OK] Created experiment '{name}' (id={exp_id})")
    return exp_id


def create_run(uri: str, experiment_id: str, run_data: Dict[str, Any]) -> str:
    """Create a run on destination server. Returns run_id."""
    info = run_data["info"]
    data = run_data["data"]

    # Create run - tags are a list of {key, value} dicts
    payload = {
        "experiment_id": experiment_id,
        "start_time": info["start_time"],
        "tags": data.get("tags", []),  # Already in correct format
    }

    # Add run_name if present
    if "run_name" in info:
        payload["run_name"] = info["run_name"]

    resp = requests.post(f"{uri}/api/2.0/mlflow/runs/create", json=payload)
    resp.raise_for_status()
    new_run_id = resp.json()["run"]["info"]["run_id"]

    # Log params - params are a list of {key, value} dicts
    for param in data.get("params", []):
        requests.post(
            f"{uri}/api/2.0/mlflow/runs/log-parameter",
            json={"run_id": new_run_id, "key": param["key"], "value": param["value"]},
        )

    # Log metrics - metrics are a list of {key, value, timestamp, step} dicts
    for metric in data.get("metrics", []):
        requests.post(
            f"{uri}/api/2.0/mlflow/runs/log-metric",
            json={
                "run_id": new_run_id,
                "key": metric["key"],
                "value": metric["value"],
                "timestamp": metric.get("timestamp", info["start_time"]),
                "step": metric.get("step", 0),
            },
        )

    # Update run status and end_time
    if info.get("status") == "FINISHED":
        requests.post(
            f"{uri}/api/2.0/mlflow/runs/update",
            json={"run_id": new_run_id, "status": "FINISHED", "end_time": info.get("end_time")},
        )

    return new_run_id


def migrate():
    """Migrate all experiments and runs from moira to cerebro."""
    print(f"[INFO] Migrating from {MOIRA_MLFLOW} to {CEREBRO_MLFLOW}\n")

    # Get source experiments
    print("[INFO] Fetching experiments from moira...")
    source_exps = get_experiments(MOIRA_MLFLOW)
    print(f"[OK] Found {len(source_exps)} experiments\n")

    total_runs_migrated = 0

    for exp in source_exps:
        exp_name = exp["name"]
        exp_id = exp["experiment_id"]

        # Skip Default experiment
        if exp_name == "Default":
            print("[SKIP] Skipping Default experiment\n")
            continue

        print(f"[INFO] Processing experiment '{exp_name}' (id={exp_id})")

        # Get runs
        runs = get_runs(MOIRA_MLFLOW, exp_id)
        print(f"  [INFO] Found {len(runs)} runs")

        if len(runs) == 0:
            print("  [SKIP] No runs to migrate\n")
            continue

        # Create experiment on destination
        dest_exp_id = create_experiment(CEREBRO_MLFLOW, exp_name)

        # Migrate runs
        print(f"  [INFO] Migrating {len(runs)} runs...")
        success_count = 0
        for i, run in enumerate(runs):
            try:
                create_run(CEREBRO_MLFLOW, dest_exp_id, run)
                success_count += 1
                if (i + 1) % 10 == 0:
                    print(f"    Migrated {i + 1}/{len(runs)} runs...")
            except Exception as e:
                print(f"    [ERROR] Failed to migrate run {run['info'].get('run_id')}: {e}")
                continue

        total_runs_migrated += success_count
        print(f"  [OK] Migrated {success_count}/{len(runs)} runs\n")

    print(f"[OK] Migration complete! Migrated {total_runs_migrated} runs")
    print(f"\nView experiments at: {CEREBRO_MLFLOW}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate MLflow experiments from moira to cerebro")
    parser.add_argument(
        "--clean", action="store_true", help="Delete all existing experiments on cerebro first (except Default)"
    )
    args = parser.parse_args()

    if args.clean:
        print("[WARN] --clean flag: Deleting all experiments on cerebro...\n")
        try:
            exps = get_experiments(CEREBRO_MLFLOW)
            for exp in exps:
                if exp["name"] != "Default":
                    print(f"  Deleting experiment '{exp['name']}' (id={exp['experiment_id']})")
                    requests.post(
                        f"{CEREBRO_MLFLOW}/api/2.0/mlflow/experiments/delete",
                        json={"experiment_id": exp["experiment_id"]},
                    )
            print("[OK] Cerebro experiments deleted\n")
        except Exception as e:
            print(f"[ERROR] Failed to clean experiments: {e}")
            sys.exit(1)

    try:
        migrate()
    except KeyboardInterrupt:
        print("\n[WARN] Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
