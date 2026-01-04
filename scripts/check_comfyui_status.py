"""Check ComfyUI server status.

Checks if ComfyUI is running and responsive.
"""

import requests
import sys
from comfyui_utils import find_comfyui_process


COMFYUI_URL = "http://192.168.1.215:8188"


def check_api_health():
    """Check if ComfyUI API is responding."""
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return response.status_code == 200
    except (requests.RequestException, requests.Timeout):
        return False


def check_status():
    """Check ComfyUI status."""
    process_running = find_comfyui_process()
    api_healthy = check_api_health()
    
    status = {
        "process_running": process_running is not None,
        "process_id": process_running,
        "api_healthy": api_healthy,
        "url": COMFYUI_URL
    }
    
    # Print status
    if status["process_running"]:
        print(f"[OK] ComfyUI process is running (PID: {status['process_id']})")
    else:
        print("[WARN] No ComfyUI process found")
    
    if status["api_healthy"]:
        print(f"[OK] ComfyUI API is responding at {status['url']}")
    else:
        print(f"[WARN] ComfyUI API is not responding at {status['url']}")
    
    # Overall status
    if status["process_running"] and status["api_healthy"]:
        print("[OK] ComfyUI is running and healthy")
        return 0
    elif status["process_running"]:
        print("[WARN] ComfyUI process is running but API is not responding")
        return 1
    else:
        print("[ERROR] ComfyUI is not running")
        return 2


def main():
    return check_status()


if __name__ == "__main__":
    sys.exit(main())
