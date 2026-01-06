"""Common utilities for ComfyUI service management scripts."""

import subprocess
import platform
import socket
import time


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


def check_port_listening(host, port, timeout=60):
    """Check if a port is listening within a timeout period.
    
    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Maximum seconds to wait (default: 60)
    
    Returns:
        bool: True if port is listening, False otherwise
    """
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True
        except (socket.error, OSError):
            pass
        
        # Wait a bit before retrying
        time.sleep(2)
    
    return False


def read_last_lines(file_path, num_lines=20):
    """Read last N lines from a file.
    
    Args:
        file_path: Path to file
        num_lines: Number of lines to read from end (default: 20)
    
    Returns:
        str: Last N lines of file, or empty string if file doesn't exist
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return ''.join(lines[-num_lines:])
    except (FileNotFoundError, PermissionError):
        return ""
