#!/usr/bin/env python3
"""Download Flux Dev FP8 model to the correct location."""

import os
from huggingface_hub import hf_hub_download


def main():
    # ComfyUI models directory
    models_base = r"C:\Users\jrjen\comfy\models"
    diffusion_dir = os.path.join(models_base, "diffusion_models")
    
    # Ensure directory exists
    os.makedirs(diffusion_dir, exist_ok=True)
    
    target_path = os.path.join(diffusion_dir, "flux1-dev-fp8.safetensors")
    
    # Delete if exists (possibly corrupted)
    if os.path.exists(target_path):
        print(f"[INFO] Removing existing file: {target_path}")
        os.remove(target_path)
    
    print("[INFO] Downloading Flux Dev FP8 (~12GB)...")
    print("[INFO] This will take several minutes...")
    
    # Download from Kijai's repo which has the properly quantized version
    downloaded_path = hf_hub_download(
        repo_id="Kijai/flux-fp8",
        filename="flux1-dev-fp8.safetensors",
        local_dir=diffusion_dir,
        resume_download=True
    )
    
    print(f"[OK] Downloaded to: {downloaded_path}")
    
    # Verify file size
    file_size = os.path.getsize(downloaded_path)
    print(f"[INFO] File size: {file_size / 1024 / 1024 / 1024:.2f} GB")
    
    if file_size < 10 * 1024 * 1024 * 1024:  # Less than 10GB
        print("[WARN] File seems too small, may be corrupted")
    else:
        print("[OK] File size looks correct")
    
    print("\n[DONE] Flux Dev FP8 downloaded!")


if __name__ == "__main__":
    main()
