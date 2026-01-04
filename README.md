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

# Cancel a specific generation
python3 generate.py --cancel <prompt_id>

# View in browser
open "http://192.168.1.215:9000/comfy-gen/"
```

## Cancelling Generations

ComfyGen supports multiple ways to cancel running or queued generations:

```bash
# Cancel currently running generation
python3 scripts/cancel_generation.py

# Cancel specific generation by prompt ID
python3 scripts/cancel_generation.py <prompt_id>

# Cancel using generate.py
python3 generate.py --cancel <prompt_id>

# List current queue and running jobs
python3 scripts/cancel_generation.py --list

# Cancel during generation with Ctrl+C
# Press Ctrl+C while generate.py is running
```

The cancellation will:
- Interrupt the current generation on ComfyUI
- Remove the job from the queue
- Clean up any partial output files
- Display confirmation message

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

## Starting ComfyUI

If ComfyUI is not running:
```bash
ssh moira "C:\\Users\\jrjen\\comfy\\.venv\\Scripts\\python.exe C:\\Users\\jrjen\\comfy-gen\\scripts\\start_comfyui.py"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start_comfyui.py` | Start ComfyUI server on moira (run via SSH) |
| `scripts/cancel_generation.py` | Cancel or list ComfyUI generation queue |
| `scripts/set_bucket_policy.py` | Make MinIO bucket publicly readable |
| `scripts/create_bucket.py` | Create the comfy-gen MinIO bucket |

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines.

**Key Rules:**
- All scripts must be Python (no batch/PowerShell)
- No NSFW content in repository
- Track work via GitHub issues