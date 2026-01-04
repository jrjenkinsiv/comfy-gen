"""Restart ComfyUI server on moira.

Stops the running ComfyUI process and starts it again.
Run via SSH to restart the ComfyUI server.
"""

import sys
import time
from pathlib import Path

# Import stop and start functions
import stop_comfyui
import start_comfyui


def restart_comfyui():
    """Restart ComfyUI server."""
    print("[INFO] Restarting ComfyUI server...")
    
    # Stop the server
    print("[INFO] Step 1: Stopping ComfyUI...")
    stop_result = stop_comfyui.stop_comfyui()
    
    # Wait a moment for process to fully terminate
    print("[INFO] Waiting for process to terminate...")
    time.sleep(2)
    
    # Start the server
    print("[INFO] Step 2: Starting ComfyUI...")
    start_result = start_comfyui.main()
    
    if start_result == 0:
        print("[OK] ComfyUI restarted successfully")
        return 0
    else:
        print("[ERROR] Failed to restart ComfyUI")
        return 1


def main():
    return restart_comfyui()


if __name__ == "__main__":
    sys.exit(main())
