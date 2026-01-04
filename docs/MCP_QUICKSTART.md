# ComfyGen MCP Server - Quick Start

The comprehensive MCP server provides 25 AI-ready tools for image and video generation. This is the **primary interface** for AI agents - no need for CLI commands!

## What's Available

### 🎨 Image Generation (2 tools)
- `generate_image` - Text-to-image with full parameter control
- `img2img` - Transform existing images

### 🎬 Video Generation (2 tools)
- `generate_video` - Text-to-video with Wan 2.2
- `image_to_video` - Animate images to video

### 🧠 Model Management (6 tools)
- `list_models` / `list_loras` - See what's installed
- `suggest_model` / `suggest_loras` - Get recommendations
- `search_civitai` - Discover new models

### 🖼️ Gallery & History (4 tools)
- `list_images` - Browse generated content
- `get_image_info` - See generation parameters
- `delete_image` - Clean up storage
- `get_history` - Review recent generations

### ✍️ Prompt Engineering (3 tools)
- `build_prompt` - Construct weighted prompts
- `suggest_negative` - Get negative prompts
- `analyze_prompt` - Get improvement suggestions

### ⚙️ Progress & Control (4 tools)
- `get_progress` - Monitor generation jobs
- `cancel` - Stop current generation
- `get_queue` - View queued jobs
- `get_system_status` - Check GPU/VRAM/server health

### 🔧 Service Management (4 tools)
- Start/stop/restart/check ComfyUI server

## Setup for VS Code / Claude Desktop

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "comfy-gen": {
      "command": "python3",
      "args": ["/path/to/comfy-gen/mcp_server.py"],
      "env": {
        "COMFYUI_HOST": "http://192.168.1.215:8188",
        "MINIO_ENDPOINT": "192.168.1.215:9000",
        "MINIO_BUCKET": "comfy-gen"
      }
    }
  }
}
```

## Quick Examples

### Generate an Image
```
AI Agent: "Generate a sunset over mountains"
→ Uses generate_image tool
→ Returns: http://192.168.1.215:9000/comfy-gen/20260104_123456_output.png
```

### Intelligent Workflow
```
AI Agent: "Create a realistic portrait and animate it"
1. Uses suggest_model(task="portrait") → Gets SD 1.5
2. Uses generate_image(...) → Creates portrait
3. Uses suggest_loras(...) → Gets motion LoRAs
4. Uses image_to_video(...) → Animates portrait
→ Returns: Video URL
```

### Discover Models
```
AI Agent: "Find detail enhancer LoRAs for cars"
→ Uses search_civitai(query="car detail", type="lora")
→ Returns: List of models with download links
```

## For AI Agents

The MCP server handles all the complexity:
- ✅ Automatic workflow selection
- ✅ Parameter validation
- ✅ Model compatibility checking
- ✅ Progress monitoring
- ✅ Error handling

Just describe what you want - the tools do the rest!

## Documentation

- **Full Guide**: `docs/MCP_COMPREHENSIVE.md`
- **Tool Reference**: All 25 tools documented with examples
- **Code Examples**: `examples/mcp_usage_example.py`
- **Test Suite**: `tests/test_comprehensive_mcp.py`

## Implementation Status

✅ **Core Generation**
- Text-to-image (SD 1.5, Flux, SDXL)
- Image-to-image
- Text-to-video (Wan 2.2)
- Image-to-video (Wan 2.2)

✅ **Model Discovery**
- List installed models/LoRAs
- Smart recommendations
- CivitAI search integration

✅ **Gallery Management**
- Browse generated images
- View generation parameters
- Clean up storage

✅ **Prompt Engineering**
- Build complex prompts
- Get suggestions
- Analyze for improvements

⏳ **Advanced Features** (Workflows pending)
- Inpainting
- Upscaling
- Face restoration
- Model downloads from CivitAI

## Architecture

```
mcp_server.py
└── comfygen/
    ├── comfyui_client.py    # ComfyUI API wrapper
    ├── minio_client.py      # Storage operations
    ├── civitai_client.py    # Model discovery
    ├── workflows.py         # Workflow manipulation
    ├── models.py            # Model registry
    └── tools/               # MCP tool implementations
        ├── generation.py    # Image tools
        ├── video.py         # Video tools
        ├── models.py        # Model tools
        ├── gallery.py       # Gallery tools
        ├── prompts.py       # Prompt tools
        └── control.py       # Control tools
```

## Testing

```bash
# Test MCP server loads all tools
python3 tests/test_comprehensive_mcp.py

# Run example workflows
python3 examples/mcp_usage_example.py
```

## Next Steps

1. Configure your MCP client (VS Code, Claude Desktop, etc.)
2. Start ComfyUI server on moira
3. Ask your AI agent to generate images/videos!

**Note**: The AI agent figures out which tools to use based on your request - you don't need to know the tool names!
