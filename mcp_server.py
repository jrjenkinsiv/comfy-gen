#!/usr/bin/env python3
"""MCP Server for ComfyUI Service Management.

This server exposes tools for managing ComfyUI service lifecycle:
- start_comfyui: Start the ComfyUI server
- stop_comfyui: Stop the ComfyUI server
- restart_comfyui: Restart the ComfyUI server
- check_comfyui_status: Check if ComfyUI is running and healthy

Run this server to allow MCP clients (like Claude Desktop) to control ComfyUI.
"""

import sys
import os
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from mcp.server import FastMCP

# Import our service management scripts
import start_comfyui
import stop_comfyui
import restart_comfyui
import check_comfyui_status

# Initialize FastMCP server
mcp = FastMCP("ComfyUI Service Manager")


@mcp.tool()
def start_comfyui_service() -> str:
    """Start the ComfyUI server on moira.
    
    This tool starts ComfyUI as a background process. The server will be
    available at http://192.168.1.215:8188.
    
    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = start_comfyui.main()
        if result == 0:
            return "ComfyUI started successfully. API available at http://192.168.1.215:8188"
        else:
            return "Failed to start ComfyUI. Check logs for details."
    except Exception as e:
        return f"Error starting ComfyUI: {str(e)}"


@mcp.tool()
def stop_comfyui_service() -> str:
    """Stop the ComfyUI server on moira.
    
    This tool terminates the running ComfyUI process.
    
    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = stop_comfyui.stop_comfyui()
        if result == 0:
            return "ComfyUI stopped successfully"
        else:
            return "Failed to stop ComfyUI or ComfyUI was not running"
    except Exception as e:
        return f"Error stopping ComfyUI: {str(e)}"


@mcp.tool()
def restart_comfyui_service() -> str:
    """Restart the ComfyUI server on moira.
    
    This tool stops and then starts the ComfyUI process, useful for
    applying configuration changes or recovering from errors.
    
    Returns:
        str: Status message indicating success or failure
    """
    try:
        result = restart_comfyui.restart_comfyui()
        if result == 0:
            return "ComfyUI restarted successfully. API available at http://192.168.1.215:8188"
        else:
            return "Failed to restart ComfyUI. Check logs for details."
    except Exception as e:
        return f"Error restarting ComfyUI: {str(e)}"


@mcp.tool()
def check_comfyui_service_status() -> str:
    """Check the status of the ComfyUI server.
    
    This tool checks if ComfyUI process is running and if the API is responding.
    
    Returns:
        str: Status report including process state and API health
    """
    try:
        # Capture output from check_status
        import io
        import contextlib
        
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            result = check_comfyui_status.check_status()
        
        output = f.getvalue()
        return output
    except Exception as e:
        return f"Error checking ComfyUI status: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
