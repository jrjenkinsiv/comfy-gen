# MCP Server Guide

This guide explains how to use the ComfyGen MCP (Model Context Protocol) server to enable AI assistants to generate images directly.

## What is MCP?

The Model Context Protocol (MCP) is a standard protocol that allows AI assistants (like Claude in VS Code, Claude Desktop, etc.) to interact with external tools and services. The ComfyGen MCP server exposes image generation capabilities as tools that AI assistants can call.

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify installation:
   ```bash
   python3 -c "from mcp.server.fastmcp import FastMCP; print('MCP SDK installed')"
   ```

## Configuration

### VS Code

Add to your VS Code settings (`.vscode/settings.json` or User/Workspace settings):

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": "python3",
      "args": ["/absolute/path/to/comfy-gen/mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000",
        "MINIO_ACCESS_KEY": "minioadmin",
        "MINIO_SECRET_KEY": "minioadmin",
        "MINIO_BUCKET": "comfy-gen"
      }
    }
  }
}
```

**Important:** Use the absolute path to `mcp_server.py`.

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent location:

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": "python3",
      "args": ["/absolute/path/to/comfy-gen/mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000"
      }
    }
  }
}
```

## Available Tools

### `generate_image`

Generate an image using ComfyUI.

**Parameters:**
- `prompt` (required): Text description of the image
- `negative_prompt` (optional): Things to avoid (default: "blurry, low quality, bad anatomy, watermark")
- `model` (optional): Model to use - "sd15" or "flux" (default: "sd15")
- `loras` (optional): List of LoRAs, e.g., `[{"name": "lora.safetensors", "strength": 0.8}]`
- `width` (optional): Image width in pixels (default: 512)
- `height` (optional): Image height in pixels (default: 512)
- `steps` (optional): Number of sampling steps (default: 20)
- `cfg` (optional): CFG scale/guidance strength (default: 7.0)
- `seed` (optional): Random seed, -1 for random (default: -1)

**Returns:**
```json
{
  "status": "success",
  "prompt_id": "abc123",
  "image_url": "http://192.168.1.215:9000/comfy-gen/20260104_120000_generated.png",
  "parameters": {
    "prompt": "...",
    "width": 512,
    "height": 512,
    ...
  }
}
```

**Example Usage in Chat:**
```
User: Generate an image of a red sports car on a mountain road
AI: [Calls generate_image with appropriate parameters]
AI: I've generated an image of a red sports car on a mountain road. 
    You can view it here: http://192.168.1.215:9000/comfy-gen/20260104_120000_generated.png
```

### `generate_video`

Generate a video using Wan 2.2 model.

**Status:** Not yet implemented (requires Wan 2.2 workflow template)

### `list_models`

List available checkpoint models from ComfyUI.

**Returns:**
```json
{
  "status": "success",
  "checkpoints": [
    "v1-5-pruned-emaonly-fp16.safetensors",
    "other-model.safetensors"
  ]
}
```

### `list_loras`

List available LoRA files from ComfyUI.

**Returns:**
```json
{
  "status": "success",
  "loras": [
    {"name": "lora1.safetensors"},
    {"name": "lora2.safetensors"}
  ],
  "count": 2
}
```

### `get_progress`

Check the progress of the current generation job.

**Returns:**
```json
{
  "status": "running",
  "prompt_id": "abc123",
  "message": "Generation in progress"
}
```

Possible statuses: `idle`, `queued`, `running`, `completed`, `unknown`, `error`

### `cancel_generation`

Cancel the currently running generation job.

**Returns:**
```json
{
  "status": "success",
  "message": "Cancelled generation abc123"
}
```

### `list_images`

List generated images in the MinIO bucket.

**Parameters:**
- `limit` (optional): Maximum number of images to return (default: 50)

**Returns:**
```json
{
  "status": "success",
  "images": [
    {
      "name": "20260104_120000_generated.png",
      "url": "http://192.168.1.215:9000/comfy-gen/20260104_120000_generated.png",
      "size": 1234567,
      "last_modified": "2026-01-04T12:00:00"
    }
  ],
  "count": 1
}
```

### `get_image_url`

Get the URL and metadata for a specific image in MinIO.

**Parameters:**
- `filename` (required): Name of the image file

**Returns:**
```json
{
  "status": "success",
  "url": "http://192.168.1.215:9000/comfy-gen/image.png",
  "size": 1234567,
  "last_modified": "2026-01-04T12:00:00",
  "content_type": "image/png"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_HOST` | `http://192.168.1.215:8188` | ComfyUI API endpoint |
| `MINIO_ENDPOINT` | `192.168.1.215:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `comfy-gen` | MinIO bucket name |

## Troubleshooting

### MCP Server Not Appearing

1. Check VS Code output panel for MCP errors
2. Verify the absolute path to `mcp_server.py` is correct
3. Ensure Python 3 is in your PATH
4. Check that all dependencies are installed

### "ComfyUI not responding"

1. Verify ComfyUI is running:
   ```bash
   curl http://192.168.1.215:8188/system_stats
   ```

2. Start ComfyUI if needed:
   ```bash
   ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
   ```

### "Model not found"

Use `list_models` tool to see available models. Model names are case-sensitive.

### "Image generation failed"

1. Check ComfyUI logs on moira
2. Verify the workflow template exists in `workflows/` directory
3. Check that the model specified is available (use `list_models`)

## Example Conversations

### Simple Image Generation

```
User: Generate an image of a sunset over mountains

AI: [Calls generate_image tool]
    I've generated an image of a sunset over mountains. 
    View it here: http://192.168.1.215:9000/comfy-gen/20260104_120000_generated.png
```

### Advanced Generation with Parameters

```
User: Create a 768x768 image of a cyberpunk city at night, 30 steps, high detail

AI: [Calls generate_image with width=768, height=768, steps=30, 
     prompt="cyberpunk city at night, highly detailed, neon lights"]
    I've created a 768x768 cyberpunk city scene with 30 sampling steps for high detail.
    Image: http://192.168.1.215:9000/comfy-gen/20260104_120000_generated.png
```

### Listing Available Resources

```
User: What models are available?

AI: [Calls list_models tool]
    Available models:
    - v1-5-pruned-emaonly-fp16.safetensors (SD 1.5)
    
User: What about LoRAs?

AI: [Calls list_loras tool]
    There are 15 LoRA files available, including:
    - acceleration LoRAs for faster generation
    - physics/motion enhancement LoRAs
    See MODEL_REGISTRY.md for full details.
```

## Security Notes

- The MCP server runs with the same permissions as the user running VS Code/Claude
- MinIO credentials are stored in environment variables (use secure credentials in production)
- Generated images are stored in a public MinIO bucket (accessible without authentication)
- ComfyUI API has no authentication by default

## Next Steps

- Implement video generation with Wan 2.2 workflow
- Add support for image-to-image generation
- Add LoRA workflow modification support
- Implement real-time progress streaming
