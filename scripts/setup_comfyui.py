#!/usr/bin/env python3
"""Setup ComfyUI on moira (Windows) for programmatic image generation.

This script:
- Clones ComfyUI repository
- Installs Python dependencies
- Configures for GPU usage
"""

import subprocess
import sys
from pathlib import Path

COMFYUI_DIR = Path.home() / "ComfyUI"
COMFYUI_REPO = "https://github.com/comfyanonymous/ComfyUI.git"


def run_command(cmd, cwd=None):
    """Run a command and return success."""
    try:
        subprocess.run(cmd, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"[OK] {cmd}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {cmd}: {e.stderr}")
        return False


def main():
    print("Setting up ComfyUI on moira...")

    # Ensure git is available
    if not run_command("git --version"):
        print("[ERROR] Git not found. Install Git for Windows.")
        sys.exit(1)

    # Clone ComfyUI if not exists
    if not COMFYUI_DIR.exists():
        print(f"Cloning ComfyUI to {COMFYUI_DIR}...")
        if not run_command(f"git clone {COMFYUI_REPO} {COMFYUI_DIR}"):
            sys.exit(1)
    else:
        print(f"ComfyUI already exists at {COMFYUI_DIR}")

    # Install requirements
    requirements_path = COMFYUI_DIR / "requirements.txt"
    if requirements_path.exists():
        print("Installing ComfyUI requirements...")
        # Use pip with --user or system python
        pip_cmd = f"{sys.executable} -m pip install -r {requirements_path}"
        if not run_command(pip_cmd, cwd=COMFYUI_DIR):
            sys.exit(1)
    else:
        print("[WARN] requirements.txt not found")

    # Install torch with CUDA support
    print("Installing PyTorch with CUDA...")
    torch_cmd = f"{sys.executable} -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
    if not run_command(torch_cmd):
        sys.exit(1)

    print("[OK] ComfyUI setup complete!")
    print(f"ComfyUI installed at: {COMFYUI_DIR}")
    print("To start server: python main.py --listen 0.0.0.0 --port 8188")


if __name__ == "__main__":
    main()
