#!/usr/bin/env python3
"""
Migrate MLflow experiments from moira (SQLite) to cerebro (PostgreSQL).

Usage:
    python3 scripts/migrate_mlflow_to_cerebro.py          # Migrate all experiments
    python3 scripts/migrate_mlflow_to_cerebro.py --clean  # Delete existing experiments on cerebro first
"""
import argparse
import requests
import sys
from typing import Dict, List

SOURCE_MLFLOW = "http://192.168.1.215:5000"  # moira (SQLite)
TARGET_MLFLOW = "http://192.168.1.162:5001"  # cerebro (PostgreSQL)


def get_experiments(mlflow_uri: str) -> List[Dict]:
    """Get all experiments from MLflow server."""
    url = f"{mlflow_uri}/api/2.0/mlflow/experiments/search"
    response = requests.post(url, json={"max_results": 1000})
    response.raise_for_status()
    return response.json().get("experiments", [])


def get_runs(mlflow_uri: str, experiment_id: str) -> List[Dict]:
    """Get all runs for an experiment."""
    url = f"{mlflow_uri}/api/2.0/mlflow/runs/search"
    response = requests.post(
        url, json={"experiment_ids": [experiment_id], "max_results": 10000}
    )
    response.raise_for_status()
    return response.json().get("runs", [])


def create_or_get_experiment(mlflow_uri: str, name: str) -> str:
    """Create experiment or get existing one."""
    # Try to create
    url = f"{mlflow_uri}/api/2.0/mlflow/experiments/create"
    response = requests.post(url, json={"name": name})
    
    if response.status_code == 200:
        return response.json()["experiment_id"]
    
    # If failed, try to restore deleted experiment
    url = f"{mlflow_uri}/api/2.0/mlflow/experiments/restore"
    response = requests.post(url, json={"experiment_id": name})
    
    if response.status_code == 200:
        print(f"  [OK] Restored deleted experiment '{name}'")
        # Get the experiment ID
        url = f"{mlflow_uri}/api/2.0/mlflow/experiments/get-by-name"
        response = requests.get(url, params={"experiment_name": name})
        response.raise_for_status()
        return response.json()["experiment"]["experiment_id"]
    
    # If still failed, experiment exists - get its ID
    url = f"{mlflow_uri}/api/2.0/mlflow/experiments/get-by-name"
    response = requests.get(url, params={"experiment_name": name})
    
    if response.status_code == 200:
        exp_id = response.json()["experiment"]["experiment_id"]
        print(f"  [OK] Experiment already exists (id={exp_id})")
        return exp_id
    
    raise Exception(f"Failed to create or get experiment '{name}'")


def migrate_run(source_uri: str, target_uri: str, run: Dict, target_exp_id: str):
    """Migrate a single run to target MLflow."""
    run_info = run["info"]
    data = run.get("data", {})
    
    # Parse params/metrics/tags (they're lists of {key, value} dicts)
    params = {item["key"]: item["value"] for item in data.get("params", [])}
    metrics = {}
    for item in data.get("metrics", []):
        metrics[item["key"]] = item["value"]
    tags = {item["key"]: item["value"] for item in data.get("tags", [])}
    
    # Create run
    url = f"{target_uri}/api/2.0/mlflow/runs/create"
    payload = {
        "experiment_id": target_exp_id,
        "start_time": run_info["start_time"],
        "tags": [{"key": k, "value": v} for k, v in tags.items()],
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    new_run_id = response.json()["run"]["info"]["run_id"]
    
    # Log params
    if params:
        url = f"{target_uri}/api/2.0/mlflow/runs/log-batch"
        payload = {
            "run_id": new_run_id,
            "params": [{"key": k, "value": v} for k, v in params.items()],
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
    
    # Log metrics
    if metrics:
        url = f"{target_uri}/api/2.0/mlflow/runs/log-batch"
        payload = {
            "run_id": new_run_id,
            "metrics": [
                {"key": k, "value": v, "timestamp": run_info["start_time"]}
                for k, v in metrics.items()
            ],
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
    
    # End run
    url = f"{target_uri}/api/2.0/mlflow/runs/update"
    payload = {
        "run_id": new_run_id,
        "status": run_info["status"],
        "end_time": run_info.get("end_time", run_info["start_time"]),
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()


def delete_experiments(mlflow_uri: str):
    """Delete all experiments on target server."""
    experiments = get_experiments(mlflow_uri)
    for exp in experiments:
        if exp["name"] == "Default":
            continue
        exp_id = exp["experiment_id"]
        url = f"{mlflow_uri}/api/2.0/mlflow/experiments/delete"
        response = requests.post(url, json={"experiment_id": exp_id})
        if response.status_code == 200:
            print(f"  [OK] Deleted experiment '{exp['name']}' (id={exp_id})")


def main():
    parser = argparse.ArgumentParser(description="Migrate MLflow experiments")
    parser.add_argument(
        "--clean", action="store_true", help="Delete existing experiments on target"
    )
    args = parser.parse_args()
    
    if args.clean:
        print(f"[WARN] Deleting all experiments on {TARGET_MLFLOW}...")
        delete_experiments(TARGET_MLFLOW)
        print()
    
    # Get all experiments from source
    print(f"[INFO] Fetching experiments from {SOURCE_MLFLOW}...")
    source_experiments = get_experiments(SOURCE_MLFLOW)
    print(f"[OK] Found {len(source_experiments)} experiments\n")
    
    total_migrated = 0
    
    for exp in source_experiments:
        exp_id = exp["experiment_id"]
        exp_name = exp["name"]
        
        if exp_name == "Default":
            continue
        
        print(f"[INFO] Processing experiment '{exp_name}' (id={exp_id})")
        
        # Get all runs
        runs = get_runs(SOURCE_MLFLOW, exp_id)
        print(f"  [INFO] Found {len(runs)} runs")
        
        if not runs:
            print(f"  [SKIP] No runs to migrate\n")
            continue
        
        # Create experiment on target
        target_exp_id = create_or_get_experiment(TARGET_MLFLOW, exp_name)
        
        # Migrate runs
        print(f"  [INFO] Migrating {len(runs)} runs...")
        for i, run in enumerate(runs, 1):
            try:
                migrate_run(SOURCE_MLFLOW, TARGET_MLFLOW, run, target_exp_id)
                if i % 10 == 0:
                    print(f"    Migrated {i}/{len(runs)} runs...")
            except Exception as e:
                print(f"    [ERROR] Failed to migrate run {run['info']['run_id']}: {e}")
                continue
        
        print(f"  [OK] Migrated {len(runs)} runs\n")
        total_migrated += len(runs)
    
    print(f"[OK] Migration complete! Total runs migrated: {total_migrated}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[WARN] Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
