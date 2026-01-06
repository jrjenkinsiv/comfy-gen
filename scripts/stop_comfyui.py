"""Stop ComfyUI server on moira.

Terminates the ComfyUI process by finding and killing it.
Run via SSH to stop the ComfyUI background process.
"""

import platform
import subprocess
import sys

from comfyui_utils import find_comfyui_process


def stop_comfyui():
    """Stop ComfyUI server."""
    print("[INFO] Searching for ComfyUI process...")

    pid = find_comfyui_process()

    if not pid:
        print("[WARN] No running ComfyUI process found")
        return 0

    print(f"[INFO] Found ComfyUI process with PID: {pid}")

    system = platform.system()

    try:
        if system == "Windows":
            # Use taskkill to terminate process
            cmd = ['taskkill', '/PID', pid, '/F']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] ComfyUI process {pid} terminated successfully")
                return 0
            else:
                print(f"[ERROR] Failed to terminate process: {result.stderr}")
                return 1
        else:
            # Use kill on Unix-like systems
            cmd = ['kill', '-TERM', pid]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] ComfyUI process {pid} terminated successfully")
                return 0
            else:
                print(f"[ERROR] Failed to terminate process: {result.stderr}")
                return 1
    except Exception as e:
        print(f"[ERROR] Exception while stopping ComfyUI: {e}")
        return 1


def main():
    return stop_comfyui()


if __name__ == "__main__":
    sys.exit(main())
