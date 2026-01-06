#!/usr/bin/env python3
"""
Download upscale models for HD enhancement
Run this on moira to get upscaling capabilities
"""

import urllib.request
from pathlib import Path

UPSCALE_MODELS = {
    "RealESRGAN_x4plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
    "4x-UltraSharp.pth": "https://huggingface.co/Kim2091/UltraSharp/resolve/main/4x-UltraSharp.pth",
    "4x_NMKD-Superscale-SP_178000_G.pth": "https://huggingface.co/gemasai/4x_NMKD-Superscale-SP_178000_G/resolve/main/4x_NMKD-Superscale-SP_178000_G.pth",
}

def download_model(name: str, url: str, dest_dir: Path):
    """Download upscale model"""
    dest_path = dest_dir / name

    if dest_path.exists():
        print(f"[SKIP] {name} already exists")
        return

    print(f"[DOWNLOAD] {name}")
    print(f"  From: {url}")
    print(f"  To: {dest_path}")

    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"[OK] Downloaded {name}")
    except Exception as e:
        print(f"[ERROR] Failed to download {name}: {e}")

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python download_upscale_models.py <upscale_models_dir>")
        print("Example: python download_upscale_models.py C:\\Users\\jrjen\\comfy\\models\\upscale_models")
        sys.exit(1)

    dest_dir = Path(sys.argv[1])
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("DOWNLOADING UPSCALE MODELS")
    print(f"{'='*60}")
    print(f"Destination: {dest_dir}\n")

    for name, url in UPSCALE_MODELS.items():
        download_model(name, url, dest_dir)
        print()

    print(f"{'='*60}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*60}")
    print(f"\nModels saved in: {dest_dir}")
    print("\nRecommendations:")
    print("  - RealESRGAN_x4plus.pth: General purpose, photorealistic")
    print("  - 4x-UltraSharp.pth: Best for faces and people")
    print("  - RealESRGAN_x4plus_anime_6B.pth: For anime/cartoon style")

if __name__ == "__main__":
    main()
