"""Common utilities for ComfyUI service management scripts."""

import platform
import socket
import subprocess
import time


def find_comfyui_process():
    """Find ComfyUI process ID.

    Returns:
        str or None: Process ID if found, None otherwise
    """
    system = platform.system()

    if system == "Windows":
        # Find python.exe running main.py
        cmd = ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output to find ComfyUI process
        for line in result.stdout.strip().split("\n"):
            if "python.exe" in line:
                parts = line.strip('"').split('","')
                if len(parts) >= 2:
                    pid = parts[1]
                    # Verify this is ComfyUI by checking command line
                    cmd_check = ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/FORMAT:LIST"]
                    result_check = subprocess.run(cmd_check, capture_output=True, text=True)
                    if "main.py" in result_check.stdout and "--listen" in result_check.stdout:
                        return pid
    else:
        # Unix-like system
        cmd = ["pgrep", "-f", "python.*main.py.*--listen"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]

    return None


def wait_for_port(host: str, port: int, timeout: int = 60) -> bool:
    """Wait for a port to become available.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Maximum time to wait in seconds (default: 60)

    Returns:
        bool: True if port is available within timeout, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except OSError:
            pass
        time.sleep(1)
    return False


def read_last_n_lines(filepath: str, n: int = 20) -> list:
    """Read last N lines from a file.

    Args:
        filepath: Path to file
        n: Number of lines to read from end (default: 20)

    Returns:
        list: Last N lines from the file, or empty list if file doesn't exist
    """
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) >= n else lines
    except (OSError, FileNotFoundError):
        return []
