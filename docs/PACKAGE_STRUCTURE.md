# Python Package Structure

This project has **two Python packages** with clear, logical names.

## Package Overview

| Package | Purpose | Used By |
|---------|---------|---------|
| `utils/` | **Utilities** - Validation, MLflow, metadata, quality scoring | `generate.py` |
| `clients/` | **API Clients** - ComfyUI, MinIO, CivitAI, HuggingFace + MCP tools | `mcp_server.py` |

## utils/ (Utilities Package)

**Utility modules used by generate.py.**

```
utils/
├── __init__.py
├── __main__.py          # Help output
├── metadata.py          # PNG metadata embedding
├── prompt_enhancer.py   # LLM prompt enhancement
├── quality.py           # Image quality scoring
├── validation.py        # CLIP validation
├── pose_validation.py   # YOLOv8 pose validation
├── content_validator.py # Content validation
└── mlflow_logger.py     # MLflow experiment logging
```

## clients/ (API Clients Package)

**API clients and MCP tools for interacting with external services.**

```
clients/
├── __init__.py
├── comfyui_client.py   # ComfyUI API client (HTTP + WebSocket)
├── minio_client.py     # MinIO storage client
├── civitai_client.py   # CivitAI API client
├── hf_client.py        # HuggingFace client
├── llm_client.py       # LLM API client (Ollama)
├── config.py           # Configuration loader
├── models.py           # Model registry
├── workflows.py        # Workflow utilities
└── tools/              # MCP tool definitions
    ├── gallery.py
    ├── generation.py
    ├── models.py
    ├── prompts.py
    ├── video.py
    └── control.py
```

## Import Patterns

```python
# For validation/logging (used by generate.py):
from utils.mlflow_logger import log_experiment
from utils.validation import validate_image
from utils.quality import score_image

# For API clients (used by mcp_server.py):
from clients.comfyui_client import ComfyUIClient
from clients.minio_client import MinIOClient
from clients.civitai_client import CivitAIClient
```

## Quick Reference

| You Want To... | Use |
|----------------|-----|
| Generate images | `python3 generate.py` |
| Log to MLflow | `utils.mlflow_logger` |
| Validate images | `utils.validation` |
| Score quality | `utils.quality` |
| Queue ComfyUI workflows | `clients.comfyui_client` |
| Upload to MinIO | `clients.minio_client` |
| Run MCP server | `python mcp_server.py` |
