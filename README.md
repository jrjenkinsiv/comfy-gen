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

ComfyUI is assumed to be already running on moira at localhost:8188.

## Usage

Trigger the "Generate Images" workflow with a prompt and workflow file.

Generated images are stored in MinIO on moira. Access via:
- MinIO Console: http://192.168.1.215:9000 (login with minioadmin/minioadmin)
- Bucket: comfy-gen
- Direct URL: Logged in workflow output

## Infrastructure Integration

Uses the deploy pipeline from github-runner-manager:
- Runner on ant-man executes CI
- Deploys to moira via SSH/tar extract
- GPU acceleration on RTX 5090