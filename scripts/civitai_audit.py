#!/usr/bin/env python3
"""
LoRA Audit Tool (CivitAI + HuggingFace)

Audits LoRA files on moira by looking up their SHA256 hashes on CivitAI API,
and validates HuggingFace-sourced LoRAs via metadata in lora_catalog.yaml.

This is the AUTHORITATIVE way to determine base model compatibility - NOT file size.

Sources supported:
- CivitAI: Hash-based lookup via API
- HuggingFace: Metadata validation from catalog's source field

Usage:
    python3 scripts/civitai_audit.py                    # Audit all LoRAs
    python3 scripts/civitai_audit.py --file <name>      # Audit single file
    python3 scripts/civitai_audit.py --update-catalog   # Update lora_catalog.yaml
    python3 scripts/civitai_audit.py --verify-sources   # Verify HuggingFace sources are reachable
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
HUGGINGFACE_API_BASE = "https://huggingface.co/api"

# Known HuggingFace repos for LoRAs (used for source verification)
KNOWN_HF_REPOS = {
    "lightx2v/Wan2.2-Distill-Loras": ["wan2.2_t2v_lightx2v", "wan2.2_i2v_lightx2v"],
    "XLabs-AI/flux-lora-collection": ["art_lora", "disney_lora", "mjv6_lora", "scenery_lora", "anime_lora"],
    "Kijai/WanVideo_comfy": ["Seko"],
}


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
                "source": "CivitAI",
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


def lookup_huggingface_repo(repo_id: str) -> dict[str, Any] | None:
    """Verify a HuggingFace repo exists and get metadata."""
    try:
        resp = requests.get(
            f"{HUGGINGFACE_API_BASE}/models/{repo_id}",
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "source": f"HuggingFace {repo_id}",
                "hf_repo_id": repo_id,
                "hf_model_id": data.get("modelId"),
                "hf_tags": data.get("tags", []),
                "hf_downloads": data.get("downloads"),
                "hf_likes": data.get("likes"),
                "hf_verified": True,
            }
        elif resp.status_code == 404:
            return {"error": f"HuggingFace repo {repo_id} not found", "hf_verified": False}
    except requests.RequestException as e:
        return {"error": str(e), "hf_verified": False}
    return None


def check_catalog_source(filename: str, catalog_path: str = "lora_catalog.yaml") -> dict[str, Any] | None:
    """Check if a LoRA has source info in the catalog."""
    try:
        with open(catalog_path, "r") as f:
            catalog = yaml.safe_load(f)
        
        for lora in catalog.get("loras", []):
            if lora.get("filename") == filename:
                source = lora.get("source")
                if source and "HuggingFace" in source:
                    # Extract repo ID from source like "HuggingFace lightx2v/Wan2.2-Distill-Loras"
                    parts = source.replace("HuggingFace ", "").strip()
                    return {
                        "catalog_source": source,
                        "hf_repo_id": parts if "/" in parts else None,
                        "civitai_verified": lora.get("civitai_verified", False),
                        "base_model": lora.get("base_model") or lora.get("civitai_base_model"),
                    }
                elif source:
                    return {
                        "catalog_source": source,
                        "civitai_verified": lora.get("civitai_verified", False),
                    }
    except Exception:
        pass
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


def audit_lora(filename: str, catalog_path: str = "lora_catalog.yaml") -> dict[str, Any]:
    """Audit a single LoRA file against CivitAI and HuggingFace."""
    result = {"filename": filename}
    
    # First check catalog for existing source info (HuggingFace entries)
    catalog_info = check_catalog_source(filename, catalog_path)
    if catalog_info and catalog_info.get("hf_repo_id"):
        # This is a known HuggingFace LoRA - verify the repo exists
        hf_info = lookup_huggingface_repo(catalog_info["hf_repo_id"])
        if hf_info and hf_info.get("hf_verified"):
            result.update(hf_info)
            result["base_model"] = catalog_info.get("base_model", "See catalog")
            result["status"] = "verified_hf"
            return result
        else:
            result["catalog_source"] = catalog_info.get("catalog_source")
            result["status"] = "hf_unverified"
            return result
    
    # Try CivitAI hash lookup
    hash_val = get_hash_from_moira(filename)
    if not hash_val:
        result["status"] = "hash_error"
        if catalog_info:
            result["catalog_source"] = catalog_info.get("catalog_source", "unknown")
        return result
    
    result["sha256"] = hash_val
    
    civitai_info = lookup_civitai_by_hash(hash_val)
    if civitai_info and "base_model" in civitai_info:
        result.update(civitai_info)
        result["status"] = "verified_civitai"
    elif catalog_info:
        # Not on CivitAI but has catalog source
        result["catalog_source"] = catalog_info.get("catalog_source")
        result["status"] = "catalog_only"
    else:
        result["status"] = "unknown"
    
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
    print("\n" + "=" * 110)
    print("LoRA AUDIT RESULTS - CivitAI + HuggingFace Verification")
    print("=" * 110)
    print(f"{'Filename':<45} | {'Source':<20} | {'Base Model':<20} | {'Status':<12}")
    print("-" * 110)
    
    for r in sorted(results, key=lambda x: x.get("status", "zzz")):
        filename = r["filename"][:44]
        source = r.get("source", r.get("catalog_source", "unknown"))[:19]
        base = r.get("base_model", "-")[:19]
        status = r.get("status", "ERROR")
        
        # Color coding via prefix
        status_icon = {
            "verified_civitai": "[OK]",
            "verified_hf": "[OK]",
            "catalog_only": "[CATALOG]",
            "hf_unverified": "[WARN]",
            "unknown": "[?]",
            "hash_error": "[ERR]",
        }.get(status, "[?]")
        
        print(f"{filename:<45} | {source:<20} | {base:<20} | {status_icon}")
    
    # Summary
    print("\n" + "=" * 110)
    print("SUMMARY:")
    
    status_counts = {}
    for r in results:
        status = r.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    verified = status_counts.get("verified_civitai", 0) + status_counts.get("verified_hf", 0)
    catalog = status_counts.get("catalog_only", 0)
    unknown = status_counts.get("unknown", 0) + status_counts.get("hf_unverified", 0)
    errors = status_counts.get("hash_error", 0)
    
    print(f"  [OK] Verified (CivitAI): {status_counts.get('verified_civitai', 0)}")
    print(f"  [OK] Verified (HuggingFace): {status_counts.get('verified_hf', 0)}")
    print(f"  [CATALOG] Catalog-only (community): {catalog}")
    print(f"  [?] Unknown source: {unknown}")
    if errors:
        print(f"  [ERR] Hash errors: {errors}")
    print(f"\n  Total: {len(results)} | Verified: {verified} | Tracked: {verified + catalog} | Unknown: {unknown}")


def update_catalog(results: list[dict], catalog_path: str = "lora_catalog.yaml") -> None:
    """Update lora_catalog.yaml with CivitAI verification data."""
    # Read existing catalog
    with open(catalog_path, "r") as f:
        catalog = yaml.safe_load(f)
    
    if "loras" not in catalog:
        print("[ERROR] No 'loras' key found in catalog")
        return
    
    # Build lookup from audit results
    audit_map = {r["filename"]: r for r in results}
    
    updated = 0
    added = 0
    
    # Update existing entries
    for lora in catalog["loras"]:
        filename = lora.get("filename")
        if filename in audit_map:
            audit = audit_map[filename]
            if audit.get("base_model") and audit["base_model"] not in ("not_found", "hash_error"):
                lora["civitai_verified"] = True
                lora["civitai_base_model"] = audit["base_model"]
                if audit.get("civitai_model_id"):
                    lora["civitai_model_id"] = audit["civitai_model_id"]
                if audit.get("trained_words"):
                    lora["civitai_triggers"] = audit["trained_words"]
                updated += 1
            else:
                lora["civitai_verified"] = False
                lora["civitai_base_model"] = "unknown (not on CivitAI)"
    
    # Find LoRAs on moira not in catalog
    catalog_filenames = {l.get("filename") for l in catalog["loras"]}
    missing = [r for r in results if r["filename"] not in catalog_filenames]
    
    if missing:
        print(f"\n[WARN] {len(missing)} LoRAs on moira not in catalog:")
        for m in missing:
            print(f"  - {m['filename']} ({m.get('base_model', 'unknown')})")
    
    # Write updated catalog
    with open(catalog_path, "w") as f:
        yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"\n[OK] Updated {updated} entries in {catalog_path}")
    print(f"[INFO] {len(missing)} LoRAs not in catalog (add manually if needed)")


def verify_hf_sources(catalog_path: str = "lora_catalog.yaml") -> None:
    """Verify all HuggingFace sources in the catalog are reachable."""
    print("[INFO] Verifying HuggingFace sources in catalog...")
    
    try:
        with open(catalog_path, "r") as f:
            catalog = yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read catalog: {e}")
        return
    
    hf_sources = set()
    for lora in catalog.get("loras", []):
        source = lora.get("source", "")
        if "HuggingFace" in source:
            # Extract repo ID
            repo_id = source.replace("HuggingFace ", "").strip()
            if "/" in repo_id:
                hf_sources.add(repo_id)
    
    print(f"[INFO] Found {len(hf_sources)} unique HuggingFace repos to verify")
    
    for repo_id in sorted(hf_sources):
        info = lookup_huggingface_repo(repo_id)
        if info and info.get("hf_verified"):
            downloads = info.get("hf_downloads", 0)
            likes = info.get("hf_likes", 0)
            print(f"  [OK] {repo_id} ({downloads:,} downloads, {likes} likes)")
        else:
            print(f"  [ERR] {repo_id} - NOT FOUND OR UNREACHABLE")


def main():
    parser = argparse.ArgumentParser(description="Audit LoRAs via CivitAI + HuggingFace")
    parser.add_argument("--file", "-f", help="Audit a specific file only")
    parser.add_argument("--update-catalog", action="store_true", help="Update lora_catalog.yaml")
    parser.add_argument("--verify-sources", action="store_true", help="Verify HuggingFace sources are reachable")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    args = parser.parse_args()
    
    if args.verify_sources:
        verify_hf_sources()
        return
    
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
        status = result.get("status", "?")
        source = result.get("source", result.get("catalog_source", ""))[:30]
        print(f"{status} ({source})")
    
    print_audit_results(results)
    
    if args.update_catalog:
        update_catalog(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[INFO] Results saved to {args.output}")


if __name__ == "__main__":
    main()
