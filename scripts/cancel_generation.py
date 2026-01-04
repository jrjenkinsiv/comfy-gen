#!/usr/bin/env python3
"""Cancel or manage ComfyUI generation queue.

Usage:
    # Cancel current running generation
    python3 scripts/cancel_generation.py
    
    # List current queue
    python3 scripts/cancel_generation.py --list
    
    # Cancel specific prompt by ID
    python3 scripts/cancel_generation.py <prompt_id>
"""

import argparse
import requests
import sys

COMFYUI_HOST = "http://192.168.1.215:8188"


def interrupt_current():
    """Interrupt the currently running generation."""
    url = f"{COMFYUI_HOST}/interrupt"
    try:
        response = requests.post(url)
        if response.status_code == 200:
            print("[OK] Interrupted current generation")
            return True
        else:
            print(f"[ERROR] Failed to interrupt: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


def list_queue():
    """List current queue and running items."""
    url = f"{COMFYUI_HOST}/queue"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            # Display running items
            running = data.get("queue_running", [])
            if running:
                print("[INFO] Currently Running:")
                for item in running:
                    prompt_id = item[1]
                    print(f"  - Prompt ID: {prompt_id}")
            else:
                print("[INFO] No items currently running")
            
            # Display pending queue
            pending = data.get("queue_pending", [])
            if pending:
                print(f"[INFO] Queue ({len(pending)} items pending):")
                for item in pending:
                    prompt_id = item[1]
                    print(f"  - Prompt ID: {prompt_id}")
            else:
                print("[INFO] Queue is empty")
            
            return True
        else:
            print(f"[ERROR] Failed to get queue: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


def delete_from_queue(prompt_id):
    """Delete a specific prompt from the queue."""
    url = f"{COMFYUI_HOST}/queue"
    payload = {"delete": [prompt_id]}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[OK] Deleted prompt {prompt_id} from queue")
            return True
        else:
            print(f"[ERROR] Failed to delete from queue: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Cancel or manage ComfyUI generation queue"
    )
    parser.add_argument(
        "prompt_id",
        nargs="?",
        help="Prompt ID to cancel (if not provided, interrupts current generation)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List current queue and running items"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List queue
        success = list_queue()
        sys.exit(0 if success else 1)
    elif args.prompt_id:
        # Cancel specific prompt
        success = delete_from_queue(args.prompt_id)
        sys.exit(0 if success else 1)
    else:
        # Interrupt current generation
        success = interrupt_current()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
