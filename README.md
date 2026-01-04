# ComfyGen

Programmatic image/video generation using ComfyUI workflows on home lab infrastructure.

## Overview

Generate images and videos via text prompts without using the ComfyUI GUI. This project provides:

- **CLI Tool**: `generate.py` for local generation
- **CI/CD Pipeline**: GitHub Actions workflow for automated generation
- **Storage**: MinIO bucket for generated assets

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
magneto (dev) --> GitHub --> ant-man (runner) --> moira (ComfyUI + RTX 5090)
                                                        |
                                                        v
                                                   MinIO bucket
                                                        |
                                                        v
                                      http://192.168.1.215:9000/comfy-gen/
```

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

## Starting ComfyUI

If ComfyUI is not running:
```bash
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start_comfyui.py` | Start ComfyUI server on moira (run via SSH) |
| `scripts/cancel_generation.py` | Cancel running/queued jobs or list queue |
| `scripts/set_bucket_policy.py` | Make MinIO bucket publicly readable |
| `scripts/create_bucket.py` | Create the comfy-gen MinIO bucket |

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