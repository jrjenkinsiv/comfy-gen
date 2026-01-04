# ComfyGen

Programmatic image/video generation using ComfyUI workflows on home lab infrastructure.

## Overview

Generate images and videos via text prompts without using the ComfyUI GUI. This project provides:

- **CLI Tool**: `generate.py` for local generation
- **CI/CD Pipeline**: GitHub Actions workflow for automated generation
- **Storage**: MinIO bucket for generated assets

## Quick Start

```bash
# Generate an image with automatic model selection
python3 generate.py --auto-select \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png

# Generate using a specific workflow
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a sunset over mountains" \
    --output /tmp/sunset.png

# Get model suggestions for a prompt
python3 scripts/select_model.py "a car driving fast with motion blur"

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

- [docs/MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md) - Complete model inventory
- [docs/LORA_CATALOG.md](docs/LORA_CATALOG.md) - LoRA catalog with semantic descriptions
- [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) - Guide for agents generating images/videos

### Automatic Model Selection

The `--auto-select` flag enables intelligent model and LoRA selection based on your prompt:

```bash
# Automatic selection for image
python3 generate.py --auto-select --prompt "realistic portrait photo"
# Selects: SD 1.5 checkpoint, no LoRAs

# Automatic selection for video with motion
python3 generate.py --auto-select --prompt "a car driving fast with motion blur"
# Selects: Wan 2.2 T2V high noise + acceleration LoRA + motion LoRAs

# Preview suggestions without generating
python3 scripts/select_model.py "your prompt here"
```

**How it works:**
1. Analyzes prompt for keywords (video, motion, speed, physics, etc.)
2. Selects appropriate base model (SD 1.5 for images, Wan 2.2 for video)
3. Suggests compatible LoRAs with optimal strength settings
4. Creates workflow automatically with selected models/LoRAs

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
| `scripts/select_model.py` | Suggest models/LoRAs based on prompt analysis |

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines.

**Key Rules:**
- All scripts must be Python (no batch/PowerShell)
- No NSFW content in repository
- Track work via GitHub issues