#!/usr/bin/env python3
"""
Download models from CivitAI to moira.

Usage:
    # Download by CivitAI model ID (gets latest version)
    python scripts/download_model.py --model-id 43331 --type checkpoint

    # Download by version ID (specific version)
    python scripts/download_model.py --version-id 176425 --type checkpoint

    # Download a LoRA
    python scripts/download_model.py --model-id 82098 --type lora

    # Search for models
    python scripts/download_model.py --search "realistic" --type checkpoint --limit 10

Model types: checkpoint, lora, vae, embedding, hypernetwork
"""

import argparse
import os
import subprocess
import sys

import requests


def load_env():
    """Load environment variables from .env file."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val


def get_civitai_client():
    """Get authenticated CivitAI session."""
    load_env()
    api_key = os.getenv("CIVITAI_API_KEY")
    session = requests.Session()
    if api_key:
        session.headers.update({"Authorization": f"Bearer {api_key}"})
    return session, api_key


def search_models(query: str, model_type: str = None, limit: int = 10):
    """Search CivitAI for models."""
    session, _ = get_civitai_client()

    params = {"query": query, "limit": limit, "sort": "Most Downloaded", "nsfw": "true"}

    type_map = {
        "checkpoint": "Checkpoint",
        "lora": "LORA",
        "vae": "VAE",
        "embedding": "TextualInversion",
    }

    if model_type and model_type in type_map:
        params["types"] = type_map[model_type]

    resp = session.get("https://civitai.com/api/v1/models", params=params, timeout=30)
    if resp.status_code != 200:
        print(f"[ERROR] Search failed: HTTP {resp.status_code}")
        return []

    data = resp.json()
    return data.get("items", [])


def get_model_info(model_id: int = None, version_id: int = None):
    """Get model information from CivitAI."""
    session, _ = get_civitai_client()

    if version_id:
        # Get model by version ID
        resp = session.get(f"https://civitai.com/api/v1/model-versions/{version_id}", timeout=30)
        if resp.status_code == 200:
            version = resp.json()
            # Get parent model info
            model_id = version.get("modelId")
            if model_id:
                model_resp = session.get(f"https://civitai.com/api/v1/models/{model_id}", timeout=30)
                if model_resp.status_code == 200:
                    model = model_resp.json()
                    return model, version
        return None, None

    if model_id:
        resp = session.get(f"https://civitai.com/api/v1/models/{model_id}", timeout=30)
        if resp.status_code == 200:
            model = resp.json()
            versions = model.get("modelVersions", [])
            if versions:
                return model, versions[0]  # Latest version
        return None, None

    return None, None


def get_dest_path(model_type: str, filename: str) -> str:
    """Get destination path on moira based on model type."""
    base = r"C:\Users\jrjen\comfy\models"

    paths = {
        "checkpoint": f"{base}\\checkpoints\\{filename}",
        "lora": f"{base}\\loras\\{filename}",
        "vae": f"{base}\\vae\\{filename}",
        "embedding": f"{base}\\embeddings\\{filename}",
        "hypernetwork": f"{base}\\hypernetworks\\{filename}",
    }

    return paths.get(model_type, f"{base}\\{filename}")


def download_to_moira(url: str, dest_path: str, api_key: str = None) -> bool:
    """Download file to moira via SSH + curl."""
    # Add API key to URL if available
    if api_key and "?" in url:
        url = f"{url}&token={api_key}"
    elif api_key:
        url = f"{url}?token={api_key}"

    cmd = ["ssh", "moira", f'curl -L -o "{dest_path}" "{url}" --progress-bar']

    print(f"[INFO] Downloading to: {dest_path}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Download models from CivitAI to moira")
    parser.add_argument("--model-id", type=int, help="CivitAI model ID")
    parser.add_argument("--version-id", type=int, help="CivitAI version ID (specific version)")
    parser.add_argument(
        "--type", choices=["checkpoint", "lora", "vae", "embedding", "hypernetwork"], required=True, help="Model type"
    )
    parser.add_argument("--search", type=str, help="Search query instead of download")
    parser.add_argument("--limit", type=int, default=10, help="Search result limit")
    parser.add_argument("--dry-run", action="store_true", help="Show info without downloading")

    args = parser.parse_args()

    # Search mode
    if args.search:
        print(f"\n=== Searching CivitAI for '{args.search}' ({args.type}) ===\n")
        results = search_models(args.search, args.type, args.limit)

        if not results:
            print("[WARN] No results found")
            return

        for item in results:
            versions = item.get("modelVersions", [])
            v = versions[0] if versions else {}
            files = v.get("files", [])
            f = files[0] if files else {}

            print(f"[{item.get('type', '?')}] {item['name']}")
            print(f"    ID: {item['id']} | Version: {v.get('id', '?')}")
            print(f"    Base: {v.get('baseModel', '?')} | NSFW: {item.get('nsfw', False)}")
            print(f"    Downloads: {item.get('stats', {}).get('downloadCount', 0):,}")
            print(f"    File: {f.get('name', '?')} ({f.get('sizeKB', 0) / 1024:.0f} MB)")
            print()

        print(f"[TIP] To download: python scripts/download_model.py --model-id <ID> --type {args.type}")
        return

    # Download mode
    if not args.model_id and not args.version_id:
        parser.error("Either --model-id or --version-id is required for download")

    model, version = get_model_info(args.model_id, args.version_id)

    if not model or not version:
        print("[ERROR] Could not find model")
        sys.exit(1)

    files = version.get("files", [])
    if not files:
        print("[ERROR] No files found for this model version")
        sys.exit(1)

    f = files[0]
    filename = f.get("name", "unknown.safetensors")
    size_mb = f.get("sizeKB", 0) / 1024
    download_url = f.get("downloadUrl", "")

    print("\n=== Model Info ===")
    print(f"Name: {model['name']}")
    print(f"Type: {model.get('type', args.type)}")
    print(f"Base Model: {version.get('baseModel', 'Unknown')}")
    print(f"Downloads: {model.get('stats', {}).get('downloadCount', 0):,}")
    print(f"File: {filename} ({size_mb:.0f} MB)")
    print(f"NSFW: {model.get('nsfw', False)}")
    print()

    if args.dry_run:
        print("[DRY-RUN] Would download to:", get_dest_path(args.type, filename))
        print("[DRY-RUN] URL:", download_url)
        return

    # Download
    _, api_key = get_civitai_client()
    dest = get_dest_path(args.type, filename)

    print(f"[INFO] Starting download (~{size_mb:.0f} MB)...")
    if download_to_moira(download_url, dest, api_key):
        print(f"[OK] Download complete: {filename}")
        print("\n[TIP] Add to lora_catalog.yaml or MODEL_REGISTRY.md")
    else:
        print("[ERROR] Download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
