#!/usr/bin/env python3
"""Cancel ComfyUI generation jobs.

Usage:
    python scripts/cancel_generation.py                    # Cancel all current/queued jobs
    python scripts/cancel_generation.py --list             # List current queue
    python scripts/cancel_generation.py --prompt-id <id>   # Cancel specific prompt
"""

import argparse
import sys

import requests

COMFYUI_HOST = "http://192.168.1.215:8188"


def get_queue():
    """Get current queue from ComfyUI."""
    try:
        url = f"{COMFYUI_HOST}/queue"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[ERROR] Failed to get queue: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to ComfyUI: {e}")
        return None


def interrupt_generation():
    """Interrupt currently running generation."""
    try:
        url = f"{COMFYUI_HOST}/interrupt"
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            print("[OK] Interrupted current generation")
            return True
        else:
            print(f"[ERROR] Failed to interrupt: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to ComfyUI: {e}")
        return False


def delete_from_queue(prompt_ids):
    """Delete specific prompts from queue.

    Args:
        prompt_ids: List of prompt IDs to delete
    """
    try:
        url = f"{COMFYUI_HOST}/queue"
        payload = {"delete": prompt_ids}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Deleted {len(prompt_ids)} prompt(s) from queue")
            return True
        else:
            print(f"[ERROR] Failed to delete from queue: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"[ERROR] Failed to connect to ComfyUI: {e}")
        return False


def list_queue(queue_data):
    """Display current queue information."""
    if not queue_data:
        print("[ERROR] No queue data available")
        return

    # Queue has two sections: queue_running and queue_pending
    running = queue_data.get("queue_running", [])
    pending = queue_data.get("queue_pending", [])

    if not running and not pending:
        print("[INFO] Queue is empty")
        return

    print("\n=== Current Queue ===\n")

    if running:
        print("Running:")
        for idx, item in enumerate(running):
            # Item format: [queue_number, prompt_id, prompt_data, extra_data]
            if len(item) >= 2:
                queue_num = item[0]
                prompt_id = item[1]
                print(f"  [{idx + 1}] Queue #{queue_num} - Prompt ID: {prompt_id}")
        print()

    if pending:
        print("Pending:")
        for idx, item in enumerate(pending):
            if len(item) >= 2:
                queue_num = item[0]
                prompt_id = item[1]
                print(f"  [{idx + 1}] Queue #{queue_num} - Prompt ID: {prompt_id}")
        print()

    total = len(running) + len(pending)
    print(f"Total: {total} job(s) in queue")


def cancel_all():
    """Cancel all running and pending jobs."""
    queue_data = get_queue()
    if not queue_data:
        return False

    running = queue_data.get("queue_running", [])
    pending = queue_data.get("queue_pending", [])

    if not running and not pending:
        print("[INFO] Queue is already empty")
        return True

    # First interrupt any running job
    if running:
        interrupt_generation()

    # Then delete all pending jobs
    if pending:
        prompt_ids = [item[1] for item in pending if len(item) >= 2]
        if prompt_ids:
            delete_from_queue(prompt_ids)

    # Also delete running jobs from queue
    if running:
        prompt_ids = [item[1] for item in running if len(item) >= 2]
        if prompt_ids:
            delete_from_queue(prompt_ids)

    print("[OK] All jobs cancelled")
    return True


def cancel_specific(prompt_id):
    """Cancel a specific prompt by ID."""
    queue_data = get_queue()
    if not queue_data:
        return False

    running = queue_data.get("queue_running", [])
    pending = queue_data.get("queue_pending", [])

    # Check if prompt is in running queue
    is_running = any(item[1] == prompt_id for item in running if len(item) >= 2)
    is_pending = any(item[1] == prompt_id for item in pending if len(item) >= 2)

    if not is_running and not is_pending:
        print(f"[ERROR] Prompt ID {prompt_id} not found in queue")
        return False

    # If running, interrupt it
    if is_running:
        interrupt_generation()

    # Delete from queue
    delete_from_queue([prompt_id])
    print(f"[OK] Cancelled prompt {prompt_id}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Cancel ComfyUI generation jobs", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="List current queue without cancelling")
    parser.add_argument("--prompt-id", help="Cancel specific prompt by ID")
    args = parser.parse_args()

    # List queue
    if args.list:
        queue_data = get_queue()
        if queue_data:
            list_queue(queue_data)
            return 0
        return 1

    # Cancel specific prompt
    if args.prompt_id:
        if cancel_specific(args.prompt_id):
            return 0
        return 1

    # Cancel all (default behavior)
    if cancel_all():
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
