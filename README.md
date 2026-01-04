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

# Generate with validation and auto-retry
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a red Porsche 911 on a mountain road" \
    --negative-prompt "multiple cars, duplicate, blurry" \
    --output /tmp/car.png \
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

## Image Validation

ComfyGen supports automated image validation using CLIP to verify generated images match the prompt:

```bash
# Validate image after generation
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a single red car" \
    --output /tmp/car.png \
    --validate

# Auto-retry on validation failure (up to 3 attempts)
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a single red car" \
    --negative-prompt "multiple cars, duplicate, cloned" \
    --output /tmp/car.png \
    --validate --auto-retry --retry-limit 3
```

**Validation Options:**
- `--validate` - Run CLIP-based validation after generation
- `--auto-retry` - Automatically retry with adjusted prompts on validation failure
- `--retry-limit N` - Maximum retry attempts (default: 3)
- `--validation-threshold` - CLIP similarity threshold 0-1 (default: 0.25)

When validation fails with `--auto-retry`, the generator:
1. Strengthens positive prompt emphasis
2. Adds negative terms like "duplicate", "cloned", "multiple"
3. Retries generation with adjusted prompts

See [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) for more details.

## Testing

Run the test suite:
```bash
python3 tests/test_validation.py
```

## Development

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for contribution guidelines.

**Key Rules:**
- All scripts must be Python (no batch/PowerShell)
- No NSFW content in repository
- Track work via GitHub issues