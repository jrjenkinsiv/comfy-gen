"""Stop ComfyUI server on moira.

Terminates the ComfyUI process by finding and killing it.
Run via SSH to stop the ComfyUI background process.
"""

import subprocess
import sys
import platform


def find_comfyui_process():
    """Find ComfyUI process ID."""
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


def stop_comfyui():
    """Stop ComfyUI server."""
    print("[INFO] Searching for ComfyUI process...")
    
    pid = find_comfyui_process()
    
    if not pid:
        print("[WARN] No running ComfyUI process found")
        return 0
    
    print(f"[INFO] Found ComfyUI process with PID: {pid}")
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Use taskkill to terminate process
            cmd = ['taskkill', '/PID', pid, '/F']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] ComfyUI process {pid} terminated successfully")
                return 0
            else:
                print(f"[ERROR] Failed to terminate process: {result.stderr}")
                return 1
        else:
            # Use kill on Unix-like systems
            cmd = ['kill', '-TERM', pid]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"[OK] ComfyUI process {pid} terminated successfully")
                return 0
            else:
                print(f"[ERROR] Failed to terminate process: {result.stderr}")
                return 1
    except Exception as e:
        print(f"[ERROR] Exception while stopping ComfyUI: {e}")
        return 1


def main():
    return stop_comfyui()


if __name__ == "__main__":
    sys.exit(main())
