"""ComfyGen - Comprehensive package for image/video generation with ComfyUI.

This package provides:
- Client interfaces for ComfyUI, MinIO, and CivitAI
- Workflow manipulation and management
- Model registry and recommendation
- MCP tools for AI agent integration
"""

__version__ = "0.2.0"

from comfygen.comfyui_client import ComfyUIClient
from comfygen.minio_client import MinIOClient
from comfygen.civitai_client import CivitAIClient

__all__ = [
    "ComfyUIClient",
    "MinIOClient",
    "CivitAIClient",
]
