#!/usr/bin/env python3
"""
Start MLflow server on moira.
Runs on 0.0.0.0:5000 to accept connections from magneto.

Usage:
    python start_mlflow.py
    python start_mlflow.py --port 5000
    python start_mlflow.py --background
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

# Configuration
DEFAULT_PORT = 5000
MLFLOW_DIR = Path(r"C:\Users\jrjen\mlflow")
ARTIFACT_ROOT = MLFLOW_DIR / "artifacts"
BACKEND_STORE = f"sqlite:///{MLFLOW_DIR / 'mlflow.db'}"


def start_mlflow(port: int = DEFAULT_PORT, background: bool = False):
    """Start MLflow tracking server."""
    
    # Ensure directories exist
    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "mlflow", "server",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--backend-store-uri", BACKEND_STORE,
        "--default-artifact-root", str(ARTIFACT_ROOT),
    ]
    
    print(f"[OK] Starting MLflow server on port {port}")
    print(f"     Backend: {BACKEND_STORE}")
    print(f"     Artifacts: {ARTIFACT_ROOT}")
    print(f"     URL: http://192.168.1.215:{port}")
    
    if background:
        # Run detached (Windows)
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            cmd,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[OK] MLflow started in background")
    else:
        # Run in foreground
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n[OK] MLflow server stopped")


def main():
    parser = argparse.ArgumentParser(description="Start MLflow server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to run on")
    parser.add_argument("--background", action="store_true", help="Run in background")
    args = parser.parse_args()
    
    start_mlflow(port=args.port, background=args.background)


if __name__ == "__main__":
    main()
