"""Start all ComfyGen services on moira after restart.

This script starts ComfyUI and MinIO services with health checks.
Designed for post-restart recovery when services don't auto-start.

Usage:
    python start_all_services.py          # Start all services
    python start_all_services.py --status # Check service status only
    python start_all_services.py --comfyui-only  # Start only ComfyUI
    python start_all_services.py --minio-only    # Start only MinIO
"""

import subprocess
import sys
import os
import argparse
import time
import requests
from pathlib import Path

# ComfyUI Configuration
COMFYUI_PATH = r"C:\Users\jrjen\AppData\Local\Programs\@comfyorgcomfyui-electron\resources\ComfyUI"
COMFYUI_PYTHON = r"C:\Users\jrjen\comfy\.venv\Scripts\python.exe"
COMFYUI_LOG = r"C:\Users\jrjen\comfyui_server.log"
COMFYUI_URL = "http://192.168.1.215:8188"
COMFYUI_HEALTH_ENDPOINT = "/system_stats"

# MinIO Configuration
MINIO_EXE = r"C:\mlflow-artifacts\minio.exe"
MINIO_DATA_DIR = r"C:\mlflow-artifacts\data"
MINIO_CONSOLE_PORT = 9001
MINIO_LOG = r"C:\Users\jrjen\minio_server.log"
MINIO_URL = "http://192.168.1.215:9000"
MINIO_HEALTH_ENDPOINT = "/minio/health/live"

# Windows process creation flags
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def check_comfyui_health() -> bool:
    """Check if ComfyUI API is responding."""
    try:
        response = requests.get(f"{COMFYUI_URL}{COMFYUI_HEALTH_ENDPOINT}", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def check_minio_health() -> bool:
    """Check if MinIO API is responding."""
    try:
        response = requests.get(f"{MINIO_URL}{MINIO_HEALTH_ENDPOINT}", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def start_comfyui() -> bool:
    """Start ComfyUI server in detached mode.
    
    Returns:
        bool: True if started successfully, False otherwise
    """
    print("[....] Starting ComfyUI server...")
    
    # Check if already running
    if check_comfyui_health():
        print(f"[OK] ComfyUI already running at {COMFYUI_URL}")
        return True
    
    # Verify paths exist
    if not os.path.exists(COMFYUI_PYTHON):
        print(f"[ERROR] Python not found at {COMFYUI_PYTHON}")
        return False
    
    if not os.path.exists(COMFYUI_PATH):
        print(f"[ERROR] ComfyUI not found at {COMFYUI_PATH}")
        return False
    
    # Start ComfyUI as detached process
    try:
        log_file = open(COMFYUI_LOG, "w")
        creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            [COMFYUI_PYTHON, "main.py", "--listen", "0.0.0.0", "--port", "8188"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            cwd=COMFYUI_PATH,
        )
        
        print(f"[OK] ComfyUI process started (PID: {process.pid})")
        print(f"[INFO] Log file: {COMFYUI_LOG}")
        
        # Wait for service to become healthy
        print("[....] Waiting for ComfyUI API to respond...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_comfyui_health():
                print(f"[OK] ComfyUI API is healthy at {COMFYUI_URL}")
                return True
        
        print(f"[WARN] ComfyUI process started but API not responding after 30s")
        print(f"[WARN] Check log file: {COMFYUI_LOG}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Failed to start ComfyUI: {e}")
        return False


def start_minio() -> bool:
    """Start MinIO server in detached mode.
    
    Returns:
        bool: True if started successfully, False otherwise
    """
    print("[....] Starting MinIO server...")
    
    # Check if already running
    if check_minio_health():
        print(f"[OK] MinIO already running at {MINIO_URL}")
        return True
    
    # Verify paths exist
    if not os.path.exists(MINIO_EXE):
        print(f"[ERROR] MinIO executable not found at {MINIO_EXE}")
        return False
    
    if not os.path.exists(MINIO_DATA_DIR):
        print(f"[ERROR] MinIO data directory not found at {MINIO_DATA_DIR}")
        return False
    
    # Start MinIO as detached process
    try:
        log_file = open(MINIO_LOG, "w")
        creation_flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
        
        process = subprocess.Popen(
            [MINIO_EXE, "server", MINIO_DATA_DIR, "--console-address", f":{MINIO_CONSOLE_PORT}"],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        
        print(f"[OK] MinIO process started (PID: {process.pid})")
        print(f"[INFO] Log file: {MINIO_LOG}")
        print(f"[INFO] Console: http://192.168.1.215:{MINIO_CONSOLE_PORT}")
        
        # Wait for service to become healthy
        print("[....] Waiting for MinIO API to respond...")
        for i in range(20):  # Wait up to 20 seconds
            time.sleep(1)
            if check_minio_health():
                print(f"[OK] MinIO API is healthy at {MINIO_URL}")
                return True
        
        print(f"[WARN] MinIO process started but API not responding after 20s")
        print(f"[WARN] Check log file: {MINIO_LOG}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Failed to start MinIO: {e}")
        return False


def check_status():
    """Check and display status of all services."""
    print("\n" + "=" * 60)
    print("ComfyGen Services Status")
    print("=" * 60)
    
    # ComfyUI status
    print("\nComfyUI Server:")
    comfyui_healthy = check_comfyui_health()
    if comfyui_healthy:
        print(f"  Status: [OK] Running")
        print(f"  URL:    {COMFYUI_URL}")
    else:
        print(f"  Status: [--] Stopped or not responding")
        print(f"  URL:    {COMFYUI_URL} (not reachable)")
    
    # MinIO status
    print("\nMinIO Server:")
    minio_healthy = check_minio_health()
    if minio_healthy:
        print(f"  Status: [OK] Running")
        print(f"  URL:    {MINIO_URL}")
        print(f"  Console: http://192.168.1.215:{MINIO_CONSOLE_PORT}")
    else:
        print(f"  Status: [--] Stopped or not responding")
        print(f"  URL:    {MINIO_URL} (not reachable)")
    
    print("\n" + "=" * 60)
    
    return comfyui_healthy and minio_healthy


def main():
    parser = argparse.ArgumentParser(
        description="Start ComfyUI and MinIO services on moira",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_all_services.py              # Start all services
  python start_all_services.py --status     # Check status only
  python start_all_services.py --comfyui-only  # Start only ComfyUI
  python start_all_services.py --minio-only    # Start only MinIO
        """
    )
    parser.add_argument("--status", action="store_true", help="Check service status only")
    parser.add_argument("--comfyui-only", action="store_true", help="Start only ComfyUI")
    parser.add_argument("--minio-only", action="store_true", help="Start only MinIO")
    args = parser.parse_args()
    
    # Status check only
    if args.status:
        all_healthy = check_status()
        return 0 if all_healthy else 1
    
    # Determine which services to start
    start_comfyui_flag = not args.minio_only
    start_minio_flag = not args.comfyui_only
    
    print("\n" + "=" * 60)
    print("Starting ComfyGen Services on moira")
    print("=" * 60 + "\n")
    
    success = True
    
    # Start ComfyUI
    if start_comfyui_flag:
        if not start_comfyui():
            success = False
        print()
    
    # Start MinIO
    if start_minio_flag:
        if not start_minio():
            success = False
        print()
    
    # Final status check
    print("=" * 60)
    print("Startup Complete - Final Status")
    print("=" * 60)
    check_status()
    
    if success:
        print("\n[OK] All requested services started successfully")
        return 0
    else:
        print("\n[WARN] Some services failed to start or are not responding")
        print("[INFO] Check log files for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
