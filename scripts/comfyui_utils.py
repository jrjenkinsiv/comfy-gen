"""Common utilities for ComfyUI service management scripts."""

import platform
import subprocess


def find_comfyui_process():
    """Find ComfyUI process ID.

    Returns:
        str or None: Process ID if found, None otherwise
    """
    system = platform.system()

    if system == "Windows":
        # Find python.exe running main.py
        cmd = ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV', '/NH']
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output to find ComfyUI process
        for line in result.stdout.strip().split('\n'):
            if 'python.exe' in line:
                parts = line.strip('"').split('","')
                if len(parts) >= 2:
                    pid = parts[1]
                    # Verify this is ComfyUI by checking command line
                    cmd_check = ['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine', '/FORMAT:LIST']
                    result_check = subprocess.run(cmd_check, capture_output=True, text=True)
                    if 'main.py' in result_check.stdout and '--listen' in result_check.stdout:
                        return pid
    else:
        # Unix-like system
        cmd = ['pgrep', '-f', 'python.*main.py.*--listen']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]

    return None
