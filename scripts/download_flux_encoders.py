#!/usr/bin/env python3
"""Download Flux text encoders and VAE to the correct locations."""

import os

from huggingface_hub import hf_hub_download


def main():
    # ComfyUI models directory
    models_base = r"C:\Users\jrjen\comfy\models"
    clip_dir = os.path.join(models_base, "clip")
    vae_dir = os.path.join(models_base, "vae")
    text_enc_dir = os.path.join(models_base, "text_encoders")

    # Ensure directories exist
    os.makedirs(clip_dir, exist_ok=True)
    os.makedirs(vae_dir, exist_ok=True)
    os.makedirs(text_enc_dir, exist_ok=True)

    # Check if CLIP-L already exists
    clip_path = os.path.join(clip_dir, "clip_l.safetensors")
    if os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000000:
        print(f"[SKIP] CLIP-L already exists: {clip_path}")
    else:
        print("[INFO] Downloading CLIP-L encoder for Flux...")
        clip_path = hf_hub_download(
            repo_id="comfyanonymous/flux_text_encoders", filename="clip_l.safetensors", local_dir=clip_dir
        )
        print(f"[OK] CLIP-L downloaded to: {clip_path}")

    # Check if VAE already exists
    vae_path = os.path.join(vae_dir, "ae.safetensors")
    if os.path.exists(vae_path) and os.path.getsize(vae_path) > 1000000:
        print(f"[SKIP] Flux VAE already exists: {vae_path}")
    else:
        print("\n[INFO] Downloading Flux VAE (ae.safetensors)...")
        vae_path = hf_hub_download(repo_id="black-forest-labs/FLUX.1-dev", filename="ae.safetensors", local_dir=vae_dir)
        print(f"[OK] Flux VAE downloaded to: {vae_path}")

    # Check for T5 FP8 - try the FP8 version (smaller)
    t5_fp8_path = os.path.join(text_enc_dir, "t5xxl_fp8_e4m3fn.safetensors")
    if os.path.exists(t5_fp8_path) and os.path.getsize(t5_fp8_path) > 1000000:
        print(f"[SKIP] T5-XXL FP8 already exists: {t5_fp8_path}")
    else:
        print("\n[INFO] Downloading T5-XXL FP8 encoder for Flux...")
        t5_path = hf_hub_download(
            repo_id="comfyanonymous/flux_text_encoders", filename="t5xxl_fp8_e4m3fn.safetensors", local_dir=text_enc_dir
        )
        print(f"[OK] T5-XXL FP8 downloaded to: {t5_path}")

    print("\n[DONE] All Flux components downloaded!")


if __name__ == "__main__":
    main()
