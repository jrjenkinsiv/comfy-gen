# ComfyGen

Programmatic image/video generation using ComfyUI workflows on home lab infrastructure.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [CLI Reference](#cli-reference)
- [Documentation](#documentation)
- [Examples](#examples)
- [Infrastructure](#infrastructure)
- [Development](#development)

## Overview

Generate images and videos via text prompts without using the ComfyUI GUI. This project provides:

- **CLI Tool**: `generate.py` for local generation with validation and auto-retry
- **MCP Server**: AI assistant integration for service management
- **CI/CD Pipeline**: GitHub Actions workflow for automated generation
- **Storage**: MinIO bucket for generated assets with public URLs

## Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Text-to-Image** | Generate images from text prompts using Flux/SD 1.5 | [Quick Start](#quick-start) |
| **Image-to-Image** | Transform images with prompts and denoise control | [Input Images](#input-image-options) |
| **Text-to-Video** | Create videos from prompts with Wan 2.2 | [Model Registry](docs/MODEL_REGISTRY.md) |
| **Image-to-Video** | Animate existing images | [Agent Guide](docs/AGENT_GUIDE.md) |
| **Image Validation** | CLIP-based semantic similarity scoring | [Validation](#image-validation--auto-retry) |
| **Auto-Retry** | Automatic retry with prompt adjustment on failure | [Validation](#image-validation--auto-retry) |
| **Model Validation** | Pre-flight checks for missing models | [Error Handling](docs/ERROR_HANDLING.md) |
| **Dry-Run Mode** | Validate workflows without generation | [Error Handling](docs/ERROR_HANDLING.md) |
| **MCP Server** | AI assistant integration (Claude, VS Code) | [MCP Server](docs/MCP_SERVER.md) |
| **Generation Cancel** | Interrupt running jobs with cleanup | [Canceling](#canceling-generation) |
| **Error Recovery** | Automatic retry with exponential backoff | [Error Handling](docs/ERROR_HANDLING.md) |

## Quick Start

```bash
# Generate an image locally (from magneto)
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png

# Image-to-image (img2img) with SD 1.5
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image /path/to/source.png \
    --prompt "oil painting style" \
    --denoise 0.7 \
    --output /tmp/result.png

# Image-to-video with Wan 2.2
python3 generate.py --workflow workflows/wan22-i2v.json \
    --input-image /path/to/frame.png \
    --prompt "camera slowly pans right" \
    --output /tmp/result.mp4

# Use an image from URL
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image "http://192.168.1.215:9000/comfy-gen/previous_image.png" \
    --prompt "add more detail"

# Generate with validation and auto-retry
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(Porsche 911:2.0) single car, one car only, driving down a country road" \
    --negative-prompt "multiple cars, duplicate, cloned, ghosting" \
    --output /tmp/porsche.png \
    --validate --auto-retry --retry-limit 3

# View in browser
open "http://192.168.1.215:9000/comfy-gen/"
```

## Architecture

```
┌──────────────┐      ┌───────────┐      ┌─────────────┐      ┌──────────────────────┐
│   magneto    │─────▶│  GitHub   │─────▶│   ant-man   │─────▶│   moira (ComfyUI)    │
│ (dev machine)│ push │(workflows)│ CI/CD│  (runner)   │ exec │   + RTX 5090 GPU     │
└──────────────┘      └───────────┘      └─────────────┘      └──────────┬───────────┘
                                                                          │
                                                                          ▼
                                                              ┌─────────────────────┐
                                                              │   MinIO Storage     │
                                                              │   Public Bucket     │
                                                              └─────────────────────┘
                                                                          │
                                                                          ▼
                                                    http://192.168.1.215:9000/comfy-gen/
```

**Data Flow:**
1. Developer pushes code or triggers workflow from magneto (192.168.1.124)
2. GitHub Actions runs on ant-man runner (192.168.1.253)
3. Runner executes generation on moira's ComfyUI API (192.168.1.215:8188)
4. Generated images/videos uploaded to MinIO bucket
5. Assets publicly accessible via HTTP

## Infrastructure

| Machine | Role | IP |
|---------|------|-----|
| magneto | Development | 192.168.1.124 |
| moira | ComfyUI + MinIO + GPU | 192.168.1.215 |
| ant-man | GitHub Runner | 192.168.1.253 |

## Services

| Service | URL | Status Check |
|---------|-----|--------------|
| ComfyUI API | http://192.168.1.215:8188 | `curl http://192.168.1.215:8188/system_stats` |
| MinIO | http://192.168.1.215:9000 | `curl http://192.168.1.215:9000/minio/health/live` |
| MinIO Console | http://192.168.1.215:9001 | Login: minioadmin/minioadmin |

## Models

All models stored in: `C:\Users\jrjen\comfy\models\` on moira.

See [docs/MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md) for complete inventory.

## Viewing Images

Generated images are publicly accessible at:
```
http://192.168.1.215:9000/comfy-gen/<filename>.png
```

List all images:
```bash
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'
```

## CLI Reference

### Basic Usage

```bash
python3 generate.py --workflow <workflow.json> --prompt "<prompt>" [OPTIONS]
```

### Core Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--workflow` | path | Path to workflow JSON file (required) |
| `--prompt` | string | Positive text prompt for generation (required unless --dry-run) |
| `--negative-prompt` | string | Negative text prompt (default: "") |
| `--output` | path | Output file path (default: output.png) |

### Input Image Options

| Argument | Type | Description |
|----------|------|-------------|
| `-i, --input-image` | path/URL | Input image for img2img or I2V workflows |
| `--resize` | WxH | Resize input to dimensions (e.g., 512x512) |
| `--crop` | mode | Crop mode: `center`, `cover`, `contain` |
| `--denoise` | float | Denoise strength 0.0-1.0 (lower = more faithful to input) |

### Validation Options

| Argument | Type | Description |
|----------|------|-------------|
| `--validate` | flag | Run CLIP validation after generation |
| `--auto-retry` | flag | Automatically retry if validation fails |
| `--retry-limit` | int | Maximum retry attempts (default: 3) |
| `--positive-threshold` | float | Minimum CLIP score for positive prompt (default: 0.25) |

### Control Options

| Argument | Type | Description |
|----------|------|-------------|
| `--dry-run` | flag | Validate workflow without generating |
| `--cancel` | prompt_id | Cancel a specific queued/running job |

### Exit Codes

| Code | Meaning | Example Causes |
|------|---------|----------------|
| 0 | Success | Generation completed successfully |
| 1 | Runtime failure | Network error, timeout, generation failed |
| 2 | Configuration error | Server down, missing models, invalid workflow |

### Common Workflows

**Simple image generation:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png
```

**Image transformation (img2img):**
```bash
python3 generate.py \
    --workflow workflows/sd15-img2img.json \
    --input-image /path/to/source.png \
    --prompt "oil painting style" \
    --denoise 0.7 \
    --output /tmp/result.png
```

**Text-to-video:**
```bash
python3 generate.py \
    --workflow workflows/wan22-t2v.json \
    --prompt "a person walking through a park on a sunny day" \
    --output /tmp/video.mp4
```

**Image-to-video:**
```bash
python3 generate.py \
    --workflow workflows/wan22-i2v.json \
    --input-image /path/to/frame.png \
    --prompt "camera slowly pans right" \
    --output /tmp/result.mp4
```

**Validated generation with auto-retry:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --prompt "(Porsche 911:2.0) single car, driving down a country road" \
    --negative-prompt "multiple cars, duplicate, cloned" \
    --output /tmp/porsche.png \
    --validate --auto-retry --retry-limit 3
```

**Dry-run validation:**
```bash
python3 generate.py \
    --workflow workflows/flux-dev.json \
    --dry-run
```

## Input Image Options

For img2img and image-to-video workflows, you can provide an input image:

```bash
# Basic img2img
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image /path/to/image.png \
    --prompt "your prompt"

# With preprocessing
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image /path/to/image.png \
    --resize 512x512 \
    --crop cover \
    --denoise 0.7 \
    --prompt "your prompt"

# From URL
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image "http://192.168.1.215:9000/comfy-gen/source.png" \
    --prompt "your prompt"
```

**Options:**
- `--input-image, -i`: Path to local image file or URL
- `--resize WxH`: Resize to target dimensions (e.g., 512x512)
- `--crop MODE`: Crop mode when resizing
  - `center`: Resize and center crop
  - `cover`: Scale to cover target, crop excess
  - `contain`: Scale to fit inside target, pad with black
- `--denoise FLOAT`: Denoise strength (0.0-1.0), controls how much the output differs from input
  - Lower values (0.3-0.5): More faithful to input
  - Higher values (0.7-0.9): More creative freedom

## Image Validation & Auto-Retry

ComfyGen can automatically validate generated images and retry with adjusted prompts if quality issues are detected.

**Validation uses CLIP** (Contrastive Language-Image Pre-training) to compute semantic similarity between the generated image and your prompt.

### Basic Validation

```bash
# Validate after generation
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a red sports car" \
    --output /tmp/car.png \
    --validate
```

This will:
1. Generate the image
2. Check CLIP similarity score against the prompt
3. Report whether validation passed or failed

### Auto-Retry on Failure

```bash
# Automatically retry up to 3 times if validation fails
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "(Porsche 911:2.0) single car, driving down a country road" \
    --negative-prompt "multiple cars, duplicate, cloned" \
    --output /tmp/porsche.png \
    --validate --auto-retry --retry-limit 3
```

When validation fails and `--auto-retry` is enabled:
- Positive prompt weights are increased (e.g., "single car" → "(single car:1.3)")
- Negative prompt is strengthened with terms like "duplicate, cloned, ghosting"
- Generation is retried with adjusted prompts

### Validation Options

- `--validate` - Enable validation after generation
- `--auto-retry` - Automatically retry if validation fails
- `--retry-limit N` - Maximum retry attempts (default: 3)
- `--positive-threshold FLOAT` - Minimum CLIP score (default: 0.25)

### Dependencies

Validation requires additional packages:
```bash
pip install transformers
```

## Error Handling & Dry-Run Mode

ComfyGen includes robust error handling with automatic retries and workflow validation.

### Server Availability Check

Before generation, the script checks if ComfyUI server is available:

```bash
python3 generate.py --workflow workflows/flux-dev.json --prompt "test"
```

If server is down:
```
[ERROR] Cannot connect to ComfyUI server at http://192.168.1.215:8188
[ERROR] Make sure ComfyUI is running on moira (192.168.1.215:8188)
[ERROR] ComfyUI server is not available
```

Exit code: 2 (configuration error)

### Model Validation

The script queries available models and validates workflow references:

```bash
python3 generate.py --workflow workflows/custom.json --prompt "test"
```

If models are missing:
```
[ERROR] Workflow validation failed - missing models:
  - checkpoint: custom-model.safetensors
    Suggested fallbacks:
      * sd15-v1-5.safetensors
      * sdxl-base-1.0.safetensors
```

### Dry-Run Mode

Validate workflows without generating images:

```bash
# Validate a workflow before running expensive generation
python3 generate.py --workflow workflows/flux-dev.json --dry-run

# Batch validate all workflows
for workflow in workflows/*.json; do
    python3 generate.py --workflow "$workflow" --dry-run || echo "Failed: $workflow"
done
```

If successful:
```
[OK] ComfyUI server is available
[OK] Retrieved available models from server
[OK] Workflow validation passed - all models available
[OK] Dry-run mode - workflow is valid
```

### Automatic Retry

Transient failures (network errors, server errors) are automatically retried with exponential backoff:

```
[ERROR] Connection error: Connection reset by peer
[INFO] Retrying in 2 seconds... (attempt 1/3)
Queued workflow with ID: abc123-def456
```

- Maximum retries: 3
- Initial delay: 2 seconds
- Backoff multiplier: 2x

### Exit Codes

- `0` - Success
- `1` - Generation or runtime failure
- `2` - Configuration error (server down, missing models, invalid workflow)

See [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md) for complete documentation.

## Starting ComfyUI

If ComfyUI is not running:
```bash
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
```

## Documentation

| Document | Description |
|----------|-------------|
| [MCP_SERVER.md](docs/MCP_SERVER.md) | MCP server setup for AI assistant integration (Claude, VS Code) |
| [AGENT_GUIDE.md](docs/AGENT_GUIDE.md) | Guide for AI agents: model selection, workflows, prompts |
| [MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md) | Complete model inventory and compatibility matrix |
| [WORKFLOWS.md](docs/WORKFLOWS.md) | Detailed workflow documentation with parameters and examples |
| [ERROR_HANDLING.md](docs/ERROR_HANDLING.md) | Error handling, validation, dry-run mode, retry logic |
| [LORA_CATALOG.md](docs/LORA_CATALOG.md) | LoRA metadata and intelligent selection system |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | Internal module and function documentation |

## Examples

Working code examples are in the `examples/` directory:

| Example | Description |
|---------|-------------|
| `basic_generation.py` | Simple text-to-image generation |
| `img2img_workflow.py` | Image transformation workflow |
| `video_generation.py` | Wan 2.2 text-to-video and image-to-video |
| `validation_workflow.py` | Auto-retry loop with validation |
| `mcp_usage_example.py` | MCP server tool usage |

Run any example:
```bash
python3 examples/basic_generation.py
```

## MCP Server for Service Management

ComfyGen includes an MCP (Model Context Protocol) server that allows AI assistants like Claude to manage ComfyUI services:

```bash
# Run the MCP server
python3 mcp_server.py
```

### Available MCP Tools

- `start_comfyui_service` - Start the ComfyUI server
- `stop_comfyui_service` - Stop the ComfyUI server
- `restart_comfyui_service` - Restart the ComfyUI server
- `check_comfyui_service_status` - Check if ComfyUI is running and healthy

See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) for complete documentation.

### Claude Desktop Integration

To use these tools in Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "comfyui-service-manager": {
      "command": "python3",
      "args": ["/path/to/comfy-gen/mcp_server.py"]
    }
  }
}
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start_comfyui.py` | Start ComfyUI server on moira (run via SSH) |
| `scripts/stop_comfyui.py` | Stop ComfyUI server on moira (run via SSH) |
| `scripts/restart_comfyui.py` | Restart ComfyUI server on moira (run via SSH) |
| `scripts/check_comfyui_status.py` | Check ComfyUI server status |
| `scripts/cancel_generation.py` | Cancel running/queued jobs or list queue |
| `scripts/set_bucket_policy.py` | Make MinIO bucket publicly readable |
| `scripts/create_bucket.py` | Create the comfy-gen MinIO bucket |
| `mcp_server.py` | MCP server for service management |

## Canceling Generation

Cancel long-running or mistaken generations:

```bash
# Cancel all current/queued jobs
python3 scripts/cancel_generation.py

# List current queue
python3 scripts/cancel_generation.py --list

# Cancel specific prompt by ID
python3 scripts/cancel_generation.py --prompt-id <prompt_id>

# Cancel from generate.py
python3 generate.py --cancel <prompt_id>

# Use Ctrl+C during generation to cancel and cleanup
```

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines.

**Key Rules:**
- All scripts must be Python (no batch/PowerShell)
- No NSFW content in repository
- Track work via GitHub issues