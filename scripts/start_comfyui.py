"""Start ComfyUI server on moira in detached mode.

Run via SSH to start ComfyUI as a background process.
"""

import subprocess
import sys
import os

COMFYUI_PATH = r"C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI"
PYTHON_PATH = r"C:\Users\jrjen\comfy\.venv\Scripts\python.exe"
LOG_FILE = r"C:\Users\jrjen\comfyui_server.log"


def main():
    print(f"[INFO] Starting ComfyUI server...")
    print(f"[INFO] ComfyUI path: {COMFYUI_PATH}")
    print(f"[INFO] Python path: {PYTHON_PATH}")
    print(f"[INFO] Log file: {LOG_FILE}")

    # Change to ComfyUI directory
    os.chdir(COMFYUI_PATH)

    # Open log file
    log_file = open(LOG_FILE, "w")

    # Start ComfyUI as a detached subprocess
    # DETACHED_PROCESS = 0x00000008
    # CREATE_NEW_PROCESS_GROUP = 0x00000200
    # CREATE_NO_WINDOW = 0x08000000
    creation_flags = 0x00000008 | 0x00000200 | 0x08000000

    process = subprocess.Popen(
        [PYTHON_PATH, "main.py", "--listen", "0.0.0.0", "--port", "8188"],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
        cwd=COMFYUI_PATH,
    )

    print(f"[OK] ComfyUI started with PID: {process.pid}")
    print(f"[INFO] Check log file: {LOG_FILE}")
    print(f"[INFO] API should be available at http://192.168.1.215:8188")

    return 0


if __name__ == "__main__":
    sys.exit(main())
