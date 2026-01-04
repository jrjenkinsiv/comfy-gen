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

# Image-to-image transformation
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image /path/to/source.png \
    --prompt "oil painting style" \
    --denoise 0.7 \
    --output /tmp/painted.png

# Image-to-video generation
python3 generate.py --workflow workflows/wan22-i2v.json \
    --input-image /path/to/frame.png \
    --prompt "camera slowly pans right" \
    --output /tmp/video.mp4

# From URL with preprocessing
python3 generate.py --workflow workflows/sd15-img2img.json \
    --input-image "http://192.168.1.215:9000/comfy-gen/previous_image.png" \
    --resize 512x512 \
    --crop center \
    --prompt "add more detail" \
    --output /tmp/enhanced.png

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

## Workflows

| Workflow | Description | Use Case |
|----------|-------------|----------|
| `flux-dev.json` | Basic text-to-image (SD 1.5) | Simple image generation |
| `sd15-img2img.json` | Image-to-image transformation | Style transfer, enhancement |
| `wan22-i2v.json` | Image-to-video (Wan 2.2) | Animate still images |

### CLI Arguments

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `--workflow` | | Path to workflow JSON (required) | `workflows/sd15-img2img.json` |
| `--prompt` | | Text prompt (required) | `"oil painting style"` |
| `--output` | | Output file path | `/tmp/output.png` |
| `--input-image` | `-i` | Input image path or URL | `/path/to/image.png` |
| `--denoise` | | Denoise strength (0.0-1.0) | `0.7` |
| `--resize` | | Resize dimensions | `512x512` |
| `--crop` | | Crop mode | `center`, `cover`, `contain` |

### Image Preprocessing

When using `--resize`, you can specify a crop mode:

- **`center`**: Center crop to target aspect ratio, then resize
- **`cover`**: Scale to cover target dimensions, then crop excess
- **`contain`**: Scale to fit within target dimensions, maintain aspect ratio

## Viewing Images

Generated images are publicly accessible at:
```
http://192.168.1.215:9000/comfy-gen/<filename>.png
```

List all images:
```bash
curl -s http://192.168.1.215:9000/comfy-gen/ | grep -oP '(?<=<Key>)[^<]+'
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
| `scripts/set_bucket_policy.py` | Make MinIO bucket publicly readable |
| `scripts/create_bucket.py` | Create the comfy-gen MinIO bucket |

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines.

**Key Rules:**
- All scripts must be Python (no batch/PowerShell)
- No NSFW content in repository
- Track work via GitHub issues