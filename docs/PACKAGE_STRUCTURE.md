# Python Package Structure

This project has **two Python packages** with different purposes. This is intentional but confusing - here's the breakdown:

## Package Overview

| Package | Purpose | Entry Point | Used By |
|---------|---------|-------------|---------|
| `comfy_gen/` | **Core CLI package** - Validation, MLflow, metadata | `python -m comfy_gen` | `generate.py`, CLI users |
| `comfygen/` | **MCP server package** - ComfyUI client, MinIO, tools | `mcp_server.py` | MCP server, tests |

## comfy_gen/ (CLI Package)

**The main user-facing package.** Installed via `pip install -e .`

```
comfy_gen/
├── __init__.py
├── __main__.py         # CLI entry point
├── cli.py              # Click-based CLI commands
├── mlflow_logger.py    # Experiment tracking
├── validation.py       # CLIP validation
├── quality.py          # Quality metrics
├── metadata.py         # Image metadata handling
├── content_validator.py
├── pose_validation.py
├── prompt_enhancer.py
├── api/                # API clients
├── categories/         # Category definitions
├── cli/                # Additional CLI commands
├── composition/        # Composition helpers
├── gui/                # GUI components
├── parsing/            # Input parsing
├── policy/             # Content policies
├── services/           # Service layer
├── tracking/           # Tracking utilities
└── workflows/          # Workflow handling
```

## comfygen/ (MCP Server Package)

**Internal package for MCP server and testing.** NOT installed via pip.

```
comfygen/
├── __init__.py
├── comfyui_client.py   # ComfyUI API client
├── minio_client.py     # MinIO storage client
├── civitai_client.py   # CivitAI API client
├── llm_client.py       # LLM API client
├── tools/              # MCP tool definitions
└── workflows/          # Workflow utilities
```

## Why Two Packages?

**Historical reasons + different dependency trees:**

1. `comfy_gen/` is the pip-installable CLI package with stable dependencies
2. `comfygen/` started as MCP server code with different imports (websocket, mcp, etc.)
3. Merging them would require resolving dependency conflicts

## Future Consideration

Consider consolidating into single `comfy_gen/` package with submodules:
- `comfy_gen.cli` - CLI (current comfy_gen)
- `comfy_gen.mcp` - MCP server (current comfygen)
- `comfy_gen.clients` - API clients

This is tracked as a future cleanup task, not urgent.

## Import Patterns

```python
# For CLI/validation work:
from comfy_gen.mlflow_logger import log_experiment
from comfy_gen.validation import validate_image

# For MCP/client work:
from comfygen.comfyui_client import ComfyUIClient
from comfygen.minio_client import MinIOClient
```

## Avoiding Confusion

| You Want To... | Use Package |
|----------------|-------------|
| Log to MLflow | `comfy_gen.mlflow_logger` |
| Validate images | `comfy_gen.validation` |
| Queue ComfyUI workflows | `comfygen.comfyui_client` |
| Upload to MinIO | `comfygen.minio_client` |
| Run CLI commands | `python -m comfy_gen` or `comfy-gen` |
| Run MCP server | `python mcp_server.py` |
