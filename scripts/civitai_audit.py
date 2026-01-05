#!/usr/bin/env python3
"""
CivitAI LoRA Audit Tool

Audits LoRA files on moira by looking up their SHA256 hashes on CivitAI API.
This is the AUTHORITATIVE way to determine base model compatibility - NOT file size.

Usage:
    python3 scripts/civitai_audit.py                    # Audit all LoRAs
    python3 scripts/civitai_audit.py --file <name>      # Audit single file
    python3 scripts/civitai_audit.py --update-catalog   # Update lora_catalog.yaml
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests
import yaml

MOIRA_LORA_PATH = r"C:\Users\jrjen\comfy\models\loras"
CIVITAI_API_BASE = "https://civitai.com/api/v1"


def get_hash_from_moira(filename: str) -> str | None:
    """Get SHA256 hash of a LoRA file on moira via SSH."""
    cmd = f'ssh moira "powershell -Command \\"(Get-FileHash -Algorithm SHA256 \'{MOIRA_LORA_PATH}\\{filename}\').Hash\\"" 2>/dev/null'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        hash_val = result.stdout.strip()
        if len(hash_val) == 64:  # Valid SHA256
            return hash_val
    except subprocess.TimeoutExpired:
        print(f"[WARN] Timeout getting hash for {filename}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Failed to get hash for {filename}: {e}", file=sys.stderr)
    return None


def lookup_civitai_by_hash(hash_val: str) -> dict[str, Any] | None:
    """Look up model version on CivitAI by SHA256 hash."""
    try:
        resp = requests.get(
            f"{CIVITAI_API_BASE}/model-versions/by-hash/{hash_val}",
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "civitai_model_name": data.get("model", {}).get("name"),
                "civitai_model_id": data.get("modelId"),
                "civitai_version_id": data.get("id"),
                "base_model": data.get("baseModel"),
                "trained_words": data.get("trainedWords", []),
                "download_url": data.get("downloadUrl"),
            }
        elif resp.status_code == 404:
            return {"error": "Not found on CivitAI"}
    except requests.RequestException as e:
        return {"error": str(e)}
    return None


def list_loras_on_moira() -> list[str]:
    """List all .safetensors files in moira's loras directory."""
    cmd = f'ssh moira "dir {MOIRA_LORA_PATH}\\*.safetensors /b" 2>/dev/null'
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to list LoRAs: {e}", file=sys.stderr)
        return []


def audit_lora(filename: str) -> dict[str, Any]:
    """Audit a single LoRA file."""
    result = {"filename": filename}
    
    hash_val = get_hash_from_moira(filename)
    if not hash_val:
        result["status"] = "hash_error"
        return result
    
    result["sha256"] = hash_val
    
    civitai_info = lookup_civitai_by_hash(hash_val)
    if civitai_info:
        result.update(civitai_info)
        result["status"] = "found" if "base_model" in civitai_info else "not_found"
    else:
        result["status"] = "lookup_error"
    
    return result


def categorize_base_model(base_model: str | None) -> str:
    """Categorize base model into simple categories."""
    if not base_model:
        return "unknown"
    
    base_lower = base_model.lower()
    
    if "wan" in base_lower:
        return "video"  # Wan 2.x models are for video
    elif "sd 1" in base_lower or "sd1" in base_lower:
        return "sd15"
    elif "sdxl" in base_lower or "sd xl" in base_lower:
        return "sdxl"
    elif "pony" in base_lower:
        return "pony"
    elif "flux" in base_lower:
        return "flux"
    else:
        return "other"


def print_audit_results(results: list[dict]) -> None:
    """Print audit results in a table format."""
    print("\n" + "=" * 100)
    print("LoRA AUDIT RESULTS - CivitAI Hash Lookup")
    print("=" * 100)
    print(f"{'Filename':<45} | {'Base Model':<25} | {'Category':<8} | Triggers")
    print("-" * 100)
    
    for r in sorted(results, key=lambda x: categorize_base_model(x.get("base_model"))):
        filename = r["filename"][:44]
        base = r.get("base_model", r.get("status", "ERROR"))[:24]
        category = categorize_base_model(r.get("base_model"))
        triggers = r.get("trained_words", [])[:2]
        triggers_str = str(triggers) if triggers else "[]"
        print(f"{filename:<45} | {base:<25} | {category:<8} | {triggers_str}")
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY:")
    categories = {}
    for r in results:
        cat = categorize_base_model(r.get("base_model"))
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        safe = "[OK] " if cat in ("sd15", "sdxl", "pony") else "[VIDEO] " if cat == "video" else ""
        print(f"  {safe}{cat}: {count} LoRAs")


def main():
    parser = argparse.ArgumentParser(description="Audit LoRAs via CivitAI hash lookup")
    parser.add_argument("--file", "-f", help="Audit a specific file only")
    parser.add_argument("--update-catalog", action="store_true", help="Update lora_catalog.yaml")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    args = parser.parse_args()
    
    if args.file:
        result = audit_lora(args.file)
        print(json.dumps(result, indent=2))
        return
    
    # Audit all LoRAs
    print("[INFO] Listing LoRAs on moira...")
    loras = list_loras_on_moira()
    print(f"[INFO] Found {len(loras)} LoRA files")
    
    results = []
    for i, lora in enumerate(loras):
        print(f"[{i+1}/{len(loras)}] Auditing {lora}...", end=" ", flush=True)
        result = audit_lora(lora)
        results.append(result)
        status = result.get("base_model", result.get("status", "?"))
        print(status)
    
    print_audit_results(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[INFO] Results saved to {args.output}")


if __name__ == "__main__":
    main()
