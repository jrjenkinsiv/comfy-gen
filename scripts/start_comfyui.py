"""Start ComfyUI server on moira in detached mode.

Run via SSH to start ComfyUI as a background process.
"""

import os
import subprocess
import sys
import time

import requests
from comfyui_utils import read_last_n_lines, wait_for_port

COMFYUI_PATH = r"C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI"
PYTHON_PATH = r"C:\Users\jrjen\comfy\.venv\Scripts\python.exe"
LOG_FILE = r"C:\Users\jrjen\comfyui_server.log"
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
STARTUP_TIMEOUT = 60  # seconds

def check_comfyui_health():
    """Check if ComfyUI API is responding.

    Returns:
        bool: True if API is healthy, False otherwise
    """
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def main():
    print("[INFO] Starting ComfyUI server...")
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
        [PYTHON_PATH, "main.py", "--listen", "0.0.0.0", "--port", str(COMFYUI_PORT)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
        cwd=COMFYUI_PATH,
    )

    print(f"[OK] ComfyUI process started with PID: {process.pid}")
    print(f"[INFO] Log file: {LOG_FILE}")

    # Wait for port to be listening
    print(f"[....] Waiting for port {COMFYUI_PORT} to be listening (timeout: {STARTUP_TIMEOUT}s)...")
    if not wait_for_port(COMFYUI_HOST, COMFYUI_PORT, timeout=STARTUP_TIMEOUT):
        print(f"[ERROR] Port {COMFYUI_PORT} not listening after {STARTUP_TIMEOUT} seconds")
        print("[ERROR] ComfyUI failed to start")
        print(f"[INFO] Last 20 lines of {LOG_FILE}:")
        print("-" * 60)
        last_lines = read_last_n_lines(LOG_FILE, 20)
        for line in last_lines:
            print(line.rstrip())
        print("-" * 60)
        return 1

    print(f"[OK] Port {COMFYUI_PORT} is listening")

    # Wait for API to respond
    print("[....] Waiting for ComfyUI API to respond...")
    start_time = time.time()
    while time.time() - start_time < STARTUP_TIMEOUT:
        if check_comfyui_health():
            print(f"[OK] ComfyUI API is healthy at {COMFYUI_URL}")
            print("[OK] ComfyUI started successfully")
            return 0
        time.sleep(1)

    # API didn't respond in time
    print(f"[ERROR] ComfyUI API not responding after {STARTUP_TIMEOUT} seconds")
    print("[ERROR] Port is listening but API is not healthy")
    print(f"[INFO] Last 20 lines of {LOG_FILE}:")
    print("-" * 60)
    last_lines = read_last_n_lines(LOG_FILE, 20)
    for line in last_lines:
        print(line.rstrip())
    print("-" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
