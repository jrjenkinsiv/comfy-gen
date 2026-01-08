# ComfyGen

Programmatic image/video generation using ComfyUI workflows on home lab infrastructure.

## Features

- **Text-to-Image** - Generate images from prompts using Flux, Pony/SDXL, or SD 1.5
- **Image-to-Image** - Transform existing images with style control
- **Text-to-Video** - Create videos from prompts using Wan 2.2
- **Image-to-Video** - Animate existing images
- **Dynamic LoRAs** - Add LoRAs via CLI without modifying workflows
- **CLIP Validation** - Semantic similarity scoring with auto-retry
- **MLflow Tracking** - Full experiment tracking for reproducibility
- **MCP Server** - AI assistant integration (Claude, VS Code)

## Quick Start

```bash
# Clone and install
git clone https://github.com/jrjenkinsiv/comfy-gen.git
cd comfy-gen
pip install -r requirements.txt

# Generate an image
python3 generate.py --workflow workflows/flux-dev.json \
    --prompt "a golden retriever on a beach, sunset lighting" \
    --steps 25 --cfg 3.5

# Generate with LoRAs
python3 generate.py --workflow workflows/pornmaster-pony-stacked-realism.json \
    --prompt "beautiful portrait, photorealistic" \
    --lora "add_detail:0.4" --lora "more_details:0.3" \
    --steps 70 --cfg 9.0

# Generate video
python3 generate.py --workflow workflows/wan22-t2v.json \
    --prompt "ocean waves crashing on rocks" \
    --length 81 --fps 16
```

**View results:** http://192.168.1.215:9000/comfy-gen/

## Architecture

```
┌──────────────┐      ┌───────────┐      ┌─────────────┐
│   magneto    │─────▶│  moira    │─────▶│   MinIO     │
│ (dev machine)│ HTTP │ (ComfyUI) │ save │  Storage    │
└──────────────┘      │ RTX 5090  │      └─────────────┘
                      └───────────┘              │
                                                 ▼
                                   http://192.168.1.215:9000/comfy-gen/
```

| Machine | Role | IP |
|---------|------|-----|
| magneto | Development | 192.168.1.124 |
| moira | ComfyUI + MinIO + GPU | 192.168.1.215 |
| cerebro | MLflow + Gallery | 192.168.1.162 |

## Documentation

### For Agents (Copilot/Claude)

| File | Purpose |
|------|---------|
| [instructions/generation.md](instructions/generation.md) | **Workflow selection, parameters, LoRAs, prompts** |
| [instructions/experiments.md](instructions/experiments.md) | **Session tracking, MLflow, reproducibility** |

### Technical References

| File | Purpose |
|------|---------|
| [docs/MODEL_REGISTRY.md](docs/MODEL_REGISTRY.md) | Model inventory and downloads |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and workflows |
| [docs/MCP_SERVERS.md](docs/MCP_SERVERS.md) | MCP server tools |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | Internal module documentation |
| [docs/METADATA_SCHEMA.md](docs/METADATA_SCHEMA.md) | JSON metadata format |
| [docs/CATEGORY_AUTHORING.md](docs/CATEGORY_AUTHORING.md) | Category YAML guide |

## CLI Reference

```bash
python3 generate.py --help
```

### Core Options

| Option | Description |
|--------|-------------|
| `--workflow` | Path to workflow JSON |
| `--prompt` | Positive text prompt |
| `--negative-prompt` | Negative prompt (what to avoid) |
| `--output` | Output file path |
| `--steps` | Sampling steps (default: 20) |
| `--cfg` | Guidance scale (default: 7.0) |
| `--seed` | Random seed (-1 for random) |
| `--width`, `--height` | Output dimensions |

### LoRA Options

| Option | Description |
|--------|-------------|
| `--lora NAME:STRENGTH` | Add LoRA (repeatable) |
| `--lora-preset PRESET` | Use predefined LoRA set |
| `--list-loras` | Show available LoRAs |

### Validation Options

| Option | Description |
|--------|-------------|
| `--validate` | Run CLIP validation |
| `--auto-retry` | Retry on validation failure |
| `--retry-limit N` | Max retry attempts |
| `--quality-score` | Multi-dimensional quality scoring |

### Video Options

| Option | Description |
|--------|-------------|
| `--length` | Frame count (81 = ~5s at 16fps) |
| `--fps` | Frame rate (default: 16) |
| `--video-resolution` | WxH (e.g., 1280x720) |

### Tracking Options

| Option | Description |
|--------|-------------|
| `--mlflow-log` | Log to MLflow |
| `--mlflow-experiment NAME` | Experiment name |
| `--project NAME` | Project tag |
| `--tags TAGS` | Comma-separated tags |

## Workflows

| Workflow | Model | Best For |
|----------|-------|----------|
| `flux-dev.json` | Flux Dev FP8 | General quality, SFW |
| `pornmaster-pony-stacked-realism.json` | Pony/SDXL | NSFW realism |
| `majicmix-realistic.json` | SD 1.5 | Realistic portraits |
| `wan22-t2v.json` | Wan 2.2 | Text-to-video |
| `wan22-i2v.json` | Wan 2.2 | Image-to-video |

See [instructions/generation.md](instructions/generation.md) for complete workflow guide.

## Project Structure

```
comfy-gen/
├── generate.py              # Main CLI entry point
├── mcp_server.py            # MCP server
├── workflows/               # Workflow JSONs
├── instructions/            # Agent guides (generation, experiments)
├── docs/                    # Technical references
├── experiments/             # Session tracking
│   ├── TEMPLATE.json        # Session format template
│   ├── sessions/            # Curated session JSONs
│   └── archive/             # Historical data
├── scripts/                 # Utility scripts
├── comfy_gen/               # CLI package (validation, MLflow)
├── comfygen/                # MCP server package (clients)
├── lora_catalog.yaml        # LoRA metadata
├── prompt_catalog.yaml      # Prompt presets
└── presets.yaml             # Generation presets
```

## Services

| Service | URL | Check |
|---------|-----|-------|
| ComfyUI | http://192.168.1.215:8188 | `curl http://192.168.1.215:8188/system_stats` |
| MinIO | http://192.168.1.215:9000 | `curl http://192.168.1.215:9000/minio/health/live` |
| MLflow | http://192.168.1.162:5001 | Browser |
| Gallery | http://192.168.1.162:8080 | Browser |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ComfyUI not responding | SSH to moira, run `python3 scripts/restart_comfyui.py` |
| Model not found | Check workflow references correct filename |
| Low validation score | Increase steps, adjust CFG, improve prompt |
| LoRA not working | Verify base model compatibility in `lora_catalog.yaml` |

## License

MIT
