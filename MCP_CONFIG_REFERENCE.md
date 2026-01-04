# MCP Configuration Reference

This file explains the structure of `mcp_config.json`.

## Basic Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "python3",
      "args": ["script.py"],
      "cwd": "/path/to/directory",
      "env": {}
    }
  }
}
```

## Fields

### `mcpServers`
Object containing all MCP server configurations. Each key is a unique server identifier.

### Server Configuration

Each server configuration has these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `command` | Yes | Command to run (e.g., "python3", "node") |
| `args` | Yes | Array of arguments passed to command |
| `cwd` | No | Working directory (defaults to current directory) |
| `env` | No | Environment variables as key-value pairs |

## Examples

### Basic Configuration

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/home/user/comfy-gen",
      "env": {}
    }
  }
}
```

### With Environment Variables

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/home/user/comfy-gen",
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000"
      }
    }
  }
}
```

### Multiple Servers

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/home/user/comfy-gen"
    },
    "comfyui-generation": {
      "command": "python3",
      "args": ["mcp_generation_server.py"],
      "cwd": "/home/user/comfy-gen"
    }
  }
}
```

### VS Code Workspace Variable

For VS Code, you can use `${workspaceFolder}`:

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

## Notes

- JSON does not support comments. Use this documentation file for explanations.
- The `env` field can override default environment variables from the parent process.
- Server names (keys in `mcpServers`) must be unique.
- Paths should be absolute or use workspace variables.

## See Also

- [MCP_SERVER.md](docs/MCP_SERVER.md) - Complete MCP server documentation
- [mcp_server.py](mcp_server.py) - Server implementation
