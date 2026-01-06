"""Create SSH tunnel to access MinIO securely.

This script creates an SSH tunnel so MinIO can be accessed via localhost
instead of directly over the network. Only machines with SSH keys can access.

Usage:
    python3 scripts/minio_tunnel.py

Then access MinIO at:
    http://localhost:9000/comfy-gen/
"""

import subprocess
import sys

MOIRA_HOST = "moira"  # Uses SSH config
LOCAL_PORT = 9000
REMOTE_PORT = 9000


def main():
    print("[INFO] Creating SSH tunnel to MinIO on moira...")
    print(f"[INFO] Local port: {LOCAL_PORT} -> moira:{REMOTE_PORT}")
    print("[INFO] Access MinIO at: http://localhost:9000/comfy-gen/")
    print("[INFO] Press Ctrl+C to close tunnel")
    print()

    # Create SSH tunnel
    # -N: don't execute remote command
    # -L: local port forwarding
    cmd = ["ssh", "-N", "-L", f"{LOCAL_PORT}:localhost:{REMOTE_PORT}", MOIRA_HOST]

    try:
        process = subprocess.Popen(cmd)
        print(f"[OK] Tunnel established (PID: {process.pid})")

        # Wait for Ctrl+C
        process.wait()
    except KeyboardInterrupt:
        print("\n[INFO] Closing tunnel...")
        process.terminate()
        process.wait()
        print("[OK] Tunnel closed")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to create tunnel: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
