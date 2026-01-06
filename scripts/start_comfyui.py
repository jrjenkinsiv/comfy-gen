"""Start ComfyUI server on moira in detached mode.

Run via SSH to start ComfyUI as a background process.
"""

import subprocess
import sys
import os
from comfyui_utils import check_port_listening, read_last_lines

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

    # Start ComfyUI as a detached subprocess
    # DETACHED_PROCESS = 0x00000008
    # CREATE_NEW_PROCESS_GROUP = 0x00000200
    # CREATE_NO_WINDOW = 0x08000000
    creation_flags = 0x00000008 | 0x00000200 | 0x08000000

    # Open log file and start process
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(
            [PYTHON_PATH, "main.py", "--listen", "0.0.0.0", "--port", "8188"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            cwd=COMFYUI_PATH,
        )

    print(f"[INFO] ComfyUI started with PID: {process.pid}")
    print(f"[INFO] Waiting for port 8188 to be listening (timeout: 60 seconds)...")

    # Wait for port 8188 to be available
    if check_port_listening("0.0.0.0", 8188, timeout=60):
        print(f"[OK] ComfyUI is running and listening on port 8188")
        print(f"[INFO] Check log file: {LOG_FILE}")
        print(f"[INFO] API available at http://192.168.1.215:8188")
        return 0
    else:
        print(f"[ERROR] ComfyUI failed to start - port 8188 not listening after 60 seconds")
        print(f"[ERROR] Last 20 lines of log file {LOG_FILE}:")
        print("=" * 80)
        log_content = read_last_lines(LOG_FILE, num_lines=20)
        if log_content:
            print(log_content)
        else:
            print("[WARN] Unable to read log file")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
