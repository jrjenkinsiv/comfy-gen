#!/usr/bin/env python3
"""Download LoRAs from CivitAI or HuggingFace to moira.

Usage:
    python3 scripts/download_lora.py <model_version_id>       # CivitAI version ID
    python3 scripts/download_lora.py --url <huggingface_url>  # Direct HuggingFace URL
    python3 scripts/download_lora.py --search <query>         # Search CivitAI
    python3 scripts/download_lora.py --list-popular           # List popular CivitAI LoRAs
    python3 scripts/download_lora.py --list-hf                # List ComfyUI-Manager LoRAs (HF)

Examples:
    python3 scripts/download_lora.py 804967                   # Download Hands LoRA
    python3 scripts/download_lora.py --search anime           # Search for anime LoRAs
    python3 scripts/download_lora.py --list-popular           # List top CivitAI LoRAs
    python3 scripts/download_lora.py --url "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/realism_lora.safetensors"
"""

import argparse
import subprocess
import sys

try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip3 install requests")
    sys.exit(1)

# Target path on moira
LORA_PATH = r"C:\Users\jrjen\comfy\models\loras"
CIVITAI_API = "https://civitai.com/api/v1"


def search_loras(query="", base_model="Flux.1 D", nsfw=False, limit=15):
    """Search CivitAI for LoRAs."""
    params = {
        "types": "LORA",
        "sort": "Most Downloaded",
        "limit": limit,
        "nsfw": str(nsfw).lower(),
    }
    if base_model:
        params["baseModels"] = base_model
    if query:
        params["query"] = query

    url = f"{CIVITAI_API}/models"
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json().get("items", [])


def get_model_version(version_id):
    """Get details about a specific model version."""
    url = f"{CIVITAI_API}/model-versions/{version_id}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def list_loras(query="", base_model="Flux.1 D"):
    """List available LoRAs."""
    items = search_loras(query=query, base_model=base_model)

    title = "Top Flux LoRAs"
    if query:
        title += f" for '{query}'"
    print(f"\n{title}:\n")
    print("-" * 80)

    for m in items:
        # Find Flux version
        flux_ver = None
        for v in m.get("modelVersions", []):
            if base_model in v.get("baseModel", ""):
                flux_ver = v
                break

        if flux_ver:
            name = m["name"][:50]
            dls = m["stats"]["downloadCount"]
            vid = flux_ver["id"]
            words = flux_ver.get("trainedWords", [])[:3]

            print(f"  Version ID: {vid}")
            print(f"  Name: {name}")
            print(f"  Downloads: {dls:,}")
            if words:
                print(f"  Triggers: {', '.join(words)}")
            print()

    print("-" * 80)
    print("\nTo download: python3 scripts/download_lora.py <version_id>")


def download_url(url, filename=None):
    """Download a file from URL to moira using curl."""
    if not filename:
        filename = url.split("/")[-1]

    print(f"[INFO] Downloading: {filename}")
    print(f"[INFO] From: {url[:80]}...")

    target = f"{LORA_PATH}\\{filename}"

    # Use curl which is more reliable for large files
    cmd = ["ssh", "moira", f'curl -L -o "{target}" "{url}"']

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            # Verify file exists
            check = subprocess.run(["ssh", "moira", f'dir "{target}"'], capture_output=True, text=True)
            if check.returncode == 0:
                print(f"[OK] Downloaded: {filename}")
                print(f'[OK] Use: --lora "{filename}:0.8"')
                return True

        print("[ERROR] Download failed")
        if result.stderr:
            print(result.stderr)
        return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Download timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"[ERROR] SSH command failed: {e}")
        return False


def download_lora(version_id):
    """Download a LoRA from CivitAI to moira."""
    print(f"[INFO] Fetching version {version_id} info from CivitAI...")

    try:
        data = get_model_version(version_id)
    except Exception as e:
        print(f"[ERROR] Failed to get model info: {e}")
        return False

    # Get download URL and filename
    files = data.get("files", [])
    if not files:
        print("[ERROR] No files found for this version")
        return False

    # Find safetensor file
    download_file = None
    for f in files:
        if f.get("name", "").endswith(".safetensors"):
            download_file = f
            break

    if not download_file:
        download_file = files[0]

    filename = download_file["name"]
    download_url = data.get("downloadUrl")
    model_name = data.get("model", {}).get("name", "Unknown")
    trained_words = data.get("trainedWords", [])

    print(f"[OK] Model: {model_name}")
    print(f"[OK] File: {filename}")
    print(f"[OK] Size: {download_file.get('sizeKB', 0) / 1024:.1f} MB")
    if trained_words:
        print(f"[OK] Trigger words: {', '.join(trained_words[:5])}")

    # Download using curl
    return download_url(download_url, filename)


# ComfyUI-Manager curated HuggingFace LoRAs
HF_LORAS = [
    {
        "name": "Hyper-FLUX.1-dev-8steps-lora",
        "url": "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-FLUX.1-dev-8steps-lora.safetensors",
        "description": "Faster generation (8 steps instead of 20+)",
        "size": "1.3GB",
    },
    {
        "name": "realism_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/realism_lora.safetensors",
        "description": "Photorealistic enhancement",
        "size": "22MB",
    },
    {
        "name": "scenery_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/scenery_lora.safetensors",
        "description": "Landscape and scenery improvement",
        "size": "43MB",
    },
    {
        "name": "mjv6_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/mjv6_lora.safetensors",
        "description": "Midjourney v6 style",
        "size": "43MB",
    },
    {
        "name": "art_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/art_lora.safetensors",
        "description": "Artistic style",
        "size": "43MB",
    },
    {
        "name": "anime_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/anime_lora.safetensors",
        "description": "Anime style",
        "size": "43MB",
    },
    {
        "name": "disney_lora",
        "url": "https://huggingface.co/XLabs-AI/flux-lora-collection/resolve/main/disney_lora.safetensors",
        "description": "Disney animation style",
        "size": "43MB",
    },
]


def list_hf_loras():
    """List HuggingFace LoRAs from ComfyUI-Manager."""
    print("\nHuggingFace Flux LoRAs (from XLabs-AI & ByteDance):\n")
    print("-" * 80)

    for i, lora in enumerate(HF_LORAS):
        print(f"  [{i + 1}] {lora['name']}")
        print(f"      {lora['description']} ({lora['size']})")
        print()

    print("-" * 80)
    print("\nTo download: python3 scripts/download_lora.py --url <url>")
    print("Or use number: python3 scripts/download_lora.py --hf 1")


def download_hf_lora(index):
    """Download a HuggingFace LoRA by index."""
    if index < 1 or index > len(HF_LORAS):
        print(f"[ERROR] Invalid index. Use 1-{len(HF_LORAS)}")
        return False

    lora = HF_LORAS[index - 1]
    print(f"[INFO] Downloading: {lora['name']}")
    print(f"[INFO] {lora['description']}")

    return download_url(lora["url"])


def main():
    parser = argparse.ArgumentParser(description="Download LoRAs from CivitAI or HuggingFace")
    parser.add_argument("version_id", nargs="?", type=int, help="CivitAI model version ID to download")
    parser.add_argument("--url", "-u", help="Direct URL to download (HuggingFace, etc.)")
    parser.add_argument("--hf", type=int, help="Download HuggingFace LoRA by index (from --list-hf)")
    parser.add_argument("--search", "-s", help="Search CivitAI for LoRAs by keyword")
    parser.add_argument("--list-popular", "-l", action="store_true", help="List popular CivitAI Flux LoRAs")
    parser.add_argument("--list-hf", action="store_true", help="List HuggingFace LoRAs")
    parser.add_argument("--base-model", default="Flux.1 D", help="Base model filter (default: Flux.1 D)")

    args = parser.parse_args()

    if args.list_hf:
        list_hf_loras()
    elif args.list_popular or args.search:
        list_loras(query=args.search or "", base_model=args.base_model)
    elif args.url:
        success = download_url(args.url)
        sys.exit(0 if success else 1)
    elif args.hf:
        success = download_hf_lora(args.hf)
        sys.exit(0 if success else 1)
    elif args.version_id:
        success = download_lora(args.version_id)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\n[INFO] Quick start:")
        print("  --list-hf        List quality HuggingFace LoRAs")
        print("  --list-popular   List popular CivitAI LoRAs")
        print("  --hf 1           Download HF LoRA #1")
        print("  804967           Download CivitAI version ID")


if __name__ == "__main__":
    main()
