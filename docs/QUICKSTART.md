# Quick Start Guide

Get your first image generated in 5 minutes.

## Prerequisites

- **Python 3.10+** installed on your machine
- **ComfyUI running on moira** (192.168.1.215:8188)
- **Network access** to local infrastructure (192.168.1.x subnet)

## Installation

```bash
# Clone the repository
git clone https://github.com/jrjenkinsiv/comfy-gen.git
cd comfy-gen

# Install dependencies
pip install -r requirements.txt
```

## Generate Your First Image

Run this command to generate a simple image:

```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "a sunset over mountains, golden hour lighting, beautiful landscape" \
  --output /tmp/sunset.png
```

You should see output like:
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[OK] Workflow validation passed - all models available
Queued workflow with ID: abc123-def456
Waiting for generation to complete...
[OK] Generation complete!
[OK] Image saved locally to: /tmp/sunset.png
[OK] Image available at: http://192.168.1.215:9000/comfy-gen/20260105_203000_sunset.png
```

## Verify Output

**View in browser:**
```
http://192.168.1.215:9000/comfy-gen/<timestamp>_sunset.png
```

**List all generated images:**
```bash
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'
```

**Check local file:**
```bash
ls -lh /tmp/sunset.png
```

## Troubleshooting

### Error: "Cannot connect to ComfyUI server"

**Cause:** ComfyUI is not running on moira.

**Fix:** Start ComfyUI server via SSH:
```bash
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
```

**Verify it's running:**
```bash
curl http://192.168.1.215:8188/system_stats
```

### Error: "Workflow validation failed - missing models"

**Cause:** Required models are not installed on moira.

**Fix:** The workflow requires specific models. See [MODEL_REGISTRY.md](MODEL_REGISTRY.md) for the complete model inventory. For `flux-dev.json`, you need:
- `flux1-dev.safetensors` (checkpoint)
- `t5xxl_fp16.safetensors` (text encoder)
- `clip_l.safetensors` (text encoder)
- `ae.safetensors` (VAE)

Models should be in `C:\Users\jrjen\comfy\models\` on moira.

### Error: "Connection timeout" or "Network unreachable"

**Cause:** You're not on the local network (192.168.1.x subnet).

**Fix:** ComfyGen requires access to:
- ComfyUI API at `192.168.1.215:8188`
- MinIO at `192.168.1.215:9000`

These are only accessible from the local network. If running remotely, use VPN or SSH tunneling.

### Image generated but not visible in MinIO

**Cause:** MinIO bucket policy may not be set to public.

**Fix:** Run the bucket policy script:
```bash
python3 scripts/set_bucket_policy.py
```

This makes the `comfy-gen` bucket publicly readable.

## Next Steps

### Try More Examples

**Image-to-image transformation:**
```bash
python3 generate.py \
  --workflow workflows/sd15-img2img.json \
  --input-image /path/to/source.png \
  --prompt "oil painting style, artistic, detailed brushstrokes" \
  --denoise 0.7 \
  --output /tmp/artistic.png
```

**With validation and auto-retry:**
```bash
python3 generate.py \
  --workflow workflows/flux-dev.json \
  --prompt "(red sports car:1.5) driving on mountain road, single vehicle" \
  --negative-prompt "multiple cars, duplicate, blurry" \
  --validate --auto-retry --retry-limit 3 \
  --output /tmp/car.png
```

### Learn More

- **[USAGE.md](USAGE.md)** - Complete CLI reference, prompt engineering, workflows
- **[MCP_SERVERS.md](MCP_SERVERS.md)** - AI agent integration (Claude, VS Code Copilot)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, LoRA injection, presets
- **[MODEL_REGISTRY.md](MODEL_REGISTRY.md)** - Available models and compatibility
- **[LORA_GUIDE.md](LORA_GUIDE.md)** - LoRA selection and usage

### MCP Server for AI Assistants

ComfyGen includes an MCP server for AI assistants like Claude:

```bash
# Start the MCP server
python3 mcp_server.py
```

Add to your `claude_desktop_config.json`:
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

See [MCP_SERVERS.md](MCP_SERVERS.md) for complete MCP documentation.

## Quick Reference

**Check ComfyUI status:**
```bash
curl http://192.168.1.215:8188/system_stats | python3 -m json.tool
```

**List available workflows:**
```bash
ls workflows/
```

**View MinIO bucket in browser:**
```
http://192.168.1.215:9000/minio/comfy-gen/
```

**Cancel a running generation:**
```bash
python3 scripts/cancel_generation.py
```

**Get help:**
```bash
python3 generate.py --help
```
