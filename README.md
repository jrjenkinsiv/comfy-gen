# Comfy-Gen

Programmatic image generation using ComfyUI workflows on our home lab infrastructure.

## Overview

This project provides a pipeline to generate images using ComfyUI workflows programmatically, leveraging our self-hosted ML infrastructure:

- **Trigger**: Push code from magneto (dev machine)
- **CI/CD**: GitHub Actions on ant-man (Jetson runner)
- **Compute**: Image generation on moira (Windows GPU machine)
- **Storage**: Artifacts stored in MinIO on moira

## Architecture

```
magneto (dev) -> GitHub -> ant-man (runner) -> moira (ComfyUI + GPU)
```

## Setup

1. Install ComfyUI on moira
2. Configure workflow templates
3. Set up GitHub Actions pipeline
4. Run generation scripts

## Usage

```bash
# Generate image from workflow
python generate.py --workflow flux-dev.json --prompt "a cat in space"
```

## Infrastructure Integration

Uses the deploy pipeline from github-runner-manager:
- Runner on ant-man executes CI
- Deploys to moira via SSH/tar extract
- GPU acceleration on RTX 5090