"""ComfyGen - Comprehensive package for image/video generation with ComfyUI.

This package provides:
- Client interfaces for ComfyUI, MinIO, and CivitAI
- Workflow manipulation and management
- Model registry and recommendation
- MCP tools for AI agent integration
"""

__version__ = "0.2.0"

from clients.civitai_client import CivitAIClient
from clients.comfyui_client import ComfyUIClient
from clients.minio_client import MinIOClient

__all__ = [
    "ComfyUIClient",
    "MinIOClient",
    "CivitAIClient",
]
