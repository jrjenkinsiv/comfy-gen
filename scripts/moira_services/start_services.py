#!/usr/bin/env python3
"""
Start all ComfyGen services on moira.
Runs MLflow and Gallery as background processes.

Usage:
    python start_services.py          # Start all services
    python start_services.py --stop   # Stop all services
    python start_services.py --status # Check status
"""

import subprocess
import sys
import os
import argparse
import socket
import time
from pathlib import Path

# Service configuration
SERVICES = {
    "mlflow": {
        "port": 5000,
        "script": "start_mlflow.py",
        "description": "MLflow Tracking Server",
    },
    "gallery": {
        "port": 8080,
        "script": "start_gallery.py",
        "description": "ComfyGen Image Gallery",
    },
}

SCRIPT_DIR = Path(__file__).parent


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def get_service_status() -> dict:
    """Get status of all services."""
    status = {}
    for name, config in SERVICES.items():
        port = config["port"]
        running = is_port_in_use(port)
        status[name] = {
            "running": running,
            "port": port,
            "url": f"http://192.168.1.215:{port}" if running else None,
        }
    return status


def start_service(name: str) -> bool:
    """Start a specific service."""
    if name not in SERVICES:
        print(f"[ERROR] Unknown service: {name}")
        return False
    
    config = SERVICES[name]
    port = config["port"]
    
    if is_port_in_use(port):
        print(f"[SKIP] {name} already running on port {port}")
        return True
    
    script = SCRIPT_DIR / config["script"]
    if not script.exists():
        print(f"[ERROR] Script not found: {script}")
        return False
    
    print(f"[....] Starting {name} on port {port}...")
    
    # Start in background
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED_PROCESS = 0x00000008
    
    subprocess.Popen(
        [sys.executable, str(script), "--port", str(port)],
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(SCRIPT_DIR),
    )
    
    # Wait for service to start
    for _ in range(10):
        time.sleep(0.5)
        if is_port_in_use(port):
            print(f"[OK] {name} started on http://192.168.1.215:{port}")
            return True
    
    print(f"[WARN] {name} may not have started - check manually")
    return False


def stop_services():
    """Stop all services by killing Python processes on service ports."""
    print("[....] Stopping services...")
    
    for name, config in SERVICES.items():
        port = config["port"]
        if is_port_in_use(port):
            # Find and kill process using port (Windows)
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
            )
            for line in result.stdout.split("\n"):
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        try:
                            subprocess.run(["taskkill", "/F", "/PID", pid], 
                                         capture_output=True)
                            print(f"[OK] Stopped {name} (PID {pid})")
                        except:
                            print(f"[WARN] Could not stop {name}")
        else:
            print(f"[SKIP] {name} not running")


def print_status():
    """Print status of all services."""
    print("\n" + "=" * 50)
    print("ComfyGen Services Status")
    print("=" * 50)
    
    status = get_service_status()
    for name, info in status.items():
        config = SERVICES[name]
        state = "[OK] Running" if info["running"] else "[--] Stopped"
        print(f"\n{config['description']} ({name})")
        print(f"  Status: {state}")
        print(f"  Port:   {info['port']}")
        if info["url"]:
            print(f"  URL:    {info['url']}")
    
    print("\n" + "=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Manage ComfyGen services")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--service", type=str, help="Start specific service only")
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return
    
    if args.stop:
        stop_services()
        print_status()
        return
    
    # Start services
    print("\n[....] Starting ComfyGen services on moira...")
    print("=" * 50)
    
    if args.service:
        start_service(args.service)
    else:
        for name in SERVICES:
            start_service(name)
    
    print_status()


if __name__ == "__main__":
    main()
