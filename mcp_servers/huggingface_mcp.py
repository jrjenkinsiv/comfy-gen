#!/usr/bin/env python3
"""HuggingFace Hub MCP Server for Agent-Assisted Model Discovery.

This server exposes tools for:
- Model search on HuggingFace Hub
- Model details retrieval
- File listing for model repositories
- File download with authentication

Run this server to allow MCP clients to discover and download models from HuggingFace Hub.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from mcp.server import FastMCP  # noqa: E402

from comfygen.huggingface_client import HuggingFaceClient  # noqa: E402

# Initialize FastMCP server
mcp = FastMCP("HuggingFace Hub Model Discovery Server")

# Lazy-loaded client
_hf_client = None


def _get_hf_client() -> HuggingFaceClient:
    """Get or create HuggingFace client (lazy initialization)."""
    global _hf_client
    if _hf_client is None:
        token = os.getenv("HF_TOKEN")
        _hf_client = HuggingFaceClient(token=token)
        print(f"[OK] HuggingFace Hub client initialized with token: {'Yes' if token else 'No'}")
    return _hf_client


@mcp.tool()
async def hf_search_models(
    query: Optional[str] = None,
    library: Optional[str] = None,
    tags: Optional[str] = None,
    pipeline_tag: Optional[str] = None,
    sort: str = "downloads",
    limit: int = 10,
) -> dict:
    """Search HuggingFace Hub for models by query with filters.

    Args:
        query: Search query (e.g., "stable diffusion", "flux", "text encoder") (optional)
        library: Filter by library - "diffusers", "transformers", etc. (optional)
        tags: Comma-separated tags to filter by (e.g., "text-to-image,sdxl") (optional)
        pipeline_tag: Filter by pipeline tag - "text-to-image", "image-to-image", etc. (optional)
        sort: Sort method - "downloads" (default), "likes", "created", "modified"
        limit: Maximum results to return (default: 10, max: 100)

    Returns:
        Dictionary with status and search results including:
        - id: Full model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")
        - author: Model author/organization
        - name: Model name (last part of ID)
        - downloads: Download count
        - likes: Number of likes
        - tags: Associated tags
        - pipeline_tag: Pipeline tag (text-to-image, etc.)
        - library: Library name (diffusers, transformers, etc.)
        - created_at: Creation timestamp
        - last_modified: Last modification timestamp
    """
    try:
        client = _get_hf_client()

        # Parse tags if provided as comma-separated string
        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",")]

        results = client.search_models(
            query=query,
            library=library,
            tags=tags_list,
            pipeline_tag=pipeline_tag,
            sort=sort,
            limit=min(limit, 100),  # Cap at 100
        )

        return {"status": "success", "results": results, "count": len(results), "query": query or "(no query)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def hf_get_model_info(model_id: str) -> dict:
    """Get detailed information about a specific HuggingFace model.

    Args:
        model_id: HuggingFace model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")

    Returns:
        Dictionary with detailed model information including:
        - id: Full model ID
        - author: Model author/organization
        - name: Model name
        - downloads: Download count
        - likes: Number of likes
        - tags: Associated tags
        - pipeline_tag: Pipeline tag
        - library: Library name
        - created_at: Creation timestamp
        - last_modified: Last modification timestamp
        - card_data: Model card metadata
        - sha: Git SHA of the model
        - siblings: List of files in the repository
        - gated: Whether model requires acceptance of terms
    """
    try:
        client = _get_hf_client()
        model = client.get_model_info(model_id)

        if not model:
            return {"status": "error", "error": f"Model not found: {model_id}"}

        return {"status": "success", "model": model}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def hf_list_files(model_id: str) -> dict:
    """List all files in a HuggingFace model repository.

    Args:
        model_id: HuggingFace model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")

    Returns:
        Dictionary with file list:
        - status: "success" or "error"
        - files: List of file dictionaries with:
          - filename: File name/path in repository
          - size: File size in bytes
        - count: Number of files
    """
    try:
        client = _get_hf_client()
        files = client.get_model_files(model_id)

        return {"status": "success", "files": files, "count": len(files)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
async def hf_download(model_id: str, filename: str, local_dir: str = "/tmp") -> dict:
    """Download a specific file from a HuggingFace model repository.

    Args:
        model_id: HuggingFace model ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")
        filename: File to download (e.g., "model.safetensors", "config.json")
        local_dir: Local directory to save file (default: /tmp)

    Returns:
        Dictionary with download result:
        - status: "success" or "error"
        - path: Path to downloaded file
        - model_id: Model ID
        - filename: Downloaded filename

    Note:
        - Gated models require HF_TOKEN environment variable
        - Some models require accepting terms on HuggingFace website first
        - Downloads are cached in HuggingFace cache directory
        - Use SSH to transfer files to moira models directory if needed
    """
    try:
        client = _get_hf_client()

        downloaded_path = client.download_file(model_id=model_id, filename=filename, local_dir=local_dir)

        if not downloaded_path:
            return {
                "status": "error",
                "error": f"Failed to download {filename} from {model_id}. Check if file exists and token is valid for gated models.",
            }

        return {"status": "success", "path": downloaded_path, "model_id": model_id, "filename": filename}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
