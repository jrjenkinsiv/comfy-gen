# MCP Server for ComfyUI Service Management

This document explains how to use the Model Context Protocol (MCP) server to manage ComfyUI services from AI assistants like Claude.

## What is MCP?

Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to AI assistants (LLMs). It allows AI assistants to:
- Access tools and functions
- Read data from various sources
- Interact with external systems

## Overview

The ComfyGen MCP server exposes tools for managing the ComfyUI service lifecycle, allowing AI assistants to:
- Start the ComfyUI server
- Stop the ComfyUI server
- Restart the ComfyUI server
- Check ComfyUI server status

## Available Tools

### `start_comfyui_service`
Start the ComfyUI server on moira as a background process.

**Returns:** Status message indicating success or failure

**Example usage:**
```
AI: "Start the ComfyUI service"
```

### `stop_comfyui_service`
Stop the running ComfyUI server by terminating its process.

**Returns:** Status message indicating success or failure

**Example usage:**
```
AI: "Stop the ComfyUI service"
```

### `restart_comfyui_service`
Restart the ComfyUI server (stops then starts it).

**Returns:** Status message indicating success or failure

**Example usage:**
```
AI: "Restart ComfyUI to apply the new configuration"
```

### `check_comfyui_service_status`
Check if ComfyUI is running and if the API is responding.

**Returns:** Status report with process state and API health

**Example usage:**
```
AI: "Check if ComfyUI is running"
```

## Running the MCP Server

### Standalone Mode

Run the server directly:

```bash
cd /path/to/comfy-gen
python3 mcp_server.py
```

The server will start and communicate via stdin/stdout using the MCP protocol.

### Integration with Claude Desktop

To enable these tools in Claude Desktop:

1. Locate your Claude Desktop config file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the ComfyUI service manager configuration:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["/absolute/path/to/comfy-gen/mcp_server.py"]
    }
  }
}
```

3. Replace `/absolute/path/to/comfy-gen/` with the actual path to your comfy-gen directory.

4. Restart Claude Desktop.

5. The tools will now be available when chatting with Claude.

### Integration with VS Code

To enable these tools in VS Code with the MCP extension:

1. Install the MCP extension in VS Code (if not already installed)

2. Create or edit `.vscode/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

3. Reload VS Code window

4. The MCP tools will be available to Copilot/AI assistants in VS Code

**Alternative: Global VS Code Configuration**

You can also configure MCP globally in VS Code settings:

1. Open VS Code Settings (JSON)
2. Add to your `settings.json`:

```json
{
  "mcp.servers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["/absolute/path/to/comfy-gen/mcp_server.py"]
    }
  }
}
```

### Integration with Other MCP Clients

The server follows the standard MCP protocol and can be integrated with any MCP-compatible client:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["/path/to/mcp_server.py"],
      "cwd": "/path/to/comfy-gen"
    }
  }
}
```

## Testing

Test the MCP server without running a full client:

```bash
python3 tests/test_mcp_server.py
```

This will:
1. Load the MCP server
2. List all registered tools
3. Display tool descriptions
4. Verify the server is properly configured

## Standalone Script Usage

You can also use the underlying scripts directly without the MCP server:

```bash
# Start ComfyUI
python3 scripts/start_comfyui.py

# Stop ComfyUI
python3 scripts/stop_comfyui.py

# Restart ComfyUI
python3 scripts/restart_comfyui.py

# Check status
python3 scripts/check_comfyui_status.py
```

These scripts are designed to be run on moira via SSH:

```bash
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
```

## Architecture

```
AI Assistant (Claude)
        |
        | MCP Protocol (stdio)
        |
    MCP Server (mcp_server.py)
        |
        | Python function calls
        |
Service Management Scripts
        |
        | Process management
        |
    ComfyUI Process
```

## Requirements

- Python 3.8+
- `mcp` package (installed via `pip install mcp`)
- All dependencies from `requirements.txt`

## Troubleshooting

### "MCP server not responding"
- Verify Python 3 is in your PATH
- Check that the path to `mcp_server.py` is absolute
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### "Failed to start ComfyUI"
- Verify you have SSH access to moira
- Check that the paths in `scripts/start_comfyui.py` are correct
- Ensure ComfyUI is installed at the specified location

### "Tools not showing in Claude Desktop"
- Restart Claude Desktop after modifying the config
- Check Claude Desktop logs for errors
- Verify the JSON config syntax is valid

## Security Considerations

- The MCP server runs locally and communicates via stdin/stdout
- Service management scripts execute system commands (tasklist, taskkill, etc.)
- Ensure only trusted AI assistants have access to the MCP server
- Review tool calls before they execute if your MCP client supports confirmation

## Future Enhancements

Potential additions to the MCP server (see issue #18 for comprehensive MCP server):

### Generation Tools (Planned)
- `generate_image` - Direct image generation from prompts
- `generate_video` - Video generation with Wan 2.2
- `transform_image` - Image-to-image transformations
- `validate_generation` - CLIP-based validation

### Queue Management (Planned)
- `list_queue` - View queued and running jobs
- `cancel_job` - Cancel specific jobs
- `clear_queue` - Cancel all jobs
- `get_queue_status` - Detailed queue statistics

### Workflow Management (Planned)
- `list_workflows` - Available workflow templates
- `validate_workflow` - Pre-flight workflow validation
- `get_workflow_info` - Workflow metadata and requirements

### Model Management (Planned)
- `list_models` - Available models and LoRAs
- `check_model` - Verify model exists
- `get_model_info` - Model metadata and compatibility

### System Monitoring (Planned)
- `get_system_stats` - GPU usage, memory, queue depth
- `get_generation_history` - Recent generations
- `get_minio_stats` - Storage usage and available images

These tools will enable full automation and integration with AI assistants, making ComfyGen completely controllable via natural language.

## Configuration Examples

### Example: Multiple MCP Servers

You can run multiple MCP servers simultaneously:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["/path/to/comfy-gen/mcp_server.py"]
    },
    "comfyui-generation": {
      "command": "python3",
      "args": ["/path/to/comfy-gen/mcp_generation_server.py"],
      "description": "Image/video generation tools (future)"
    }
  }
}
```

### Example: Environment Variables

Pass environment variables to the MCP server:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/comfy-gen",
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000"
      }
    }
  }
}
```
