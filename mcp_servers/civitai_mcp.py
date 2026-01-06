#!/usr/bin/env python3
"""CivitAI MCP Server for Agent-Assisted Model Discovery.

This server exposes tools for:
- Model search on CivitAI
- Model details retrieval
- Hash-based lookup for verification (CRITICAL for LoRA compatibility checking)
- Download URL generation with authentication

Run this server to allow MCP clients to discover and verify models from CivitAI.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from mcp.server import FastMCP  # noqa: E402

from comfygen.civitai_client import CivitAIClient  # noqa: E402

# Initialize FastMCP server
mcp = FastMCP("CivitAI Model Discovery Server")

# Lazy-loaded client
_civitai_client = None


def _get_civitai_client() -> CivitAIClient:
    """Get or create CivitAI client (lazy initialization)."""
    global _civitai_client
    if _civitai_client is None:
        api_key = os.getenv("CIVITAI_API_KEY")
        _civitai_client = CivitAIClient(api_key=api_key)
        print(f"[OK] CivitAI client initialized with API key: {'Yes' if api_key else 'No'}")
    return _civitai_client


@mcp.tool()
async def civitai_search_models(
    query: str,
    model_type: Optional[str] = None,
    base_model: Optional[str] = None,
    sort: str = "Most Downloaded",
    nsfw: bool = True,
    limit: int = 10,
) -> dict:
    """Search CivitAI for models by query with filters.

    Args:
        query: Search query (e.g., "battleship", "anime style", "portrait")
        model_type: Filter by type - Checkpoint, LORA, VAE, etc. (optional)
        base_model: Filter by base model - "SD 1.5", "SDXL", "Flux.1 D", etc. (optional)
        sort: Sort method - "Most Downloaded", "Highest Rated", "Newest" (default: Most Downloaded)
        nsfw: Include NSFW results (default: True)
        limit: Maximum results to return (default: 10, max: 100)

    Returns:
        Dictionary with status and search results including:
        - id: CivitAI model ID
        - name: Model name
        - type: Model type
        - description: Brief description
        - creator: Creator username
        - downloads: Download count
        - rating: Average rating
        - base_model: Base model (SD 1.5, SDXL, etc.)
        - version_id: Latest version ID
        - version_name: Latest version name
        - preview_url: Preview image URL
        - download_url: Download URL
        - nsfw: NSFW flag
    """
    try:
        client = _get_civitai_client()
        results = client.search_models(
            query=query,
            model_type=model_type,
            base_model=base_model,
            sort=sort,
            nsfw=nsfw,
            limit=min(limit, 100)  # Cap at 100
        )

        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "query": query
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def civitai_get_model(model_id: int) -> dict:
    """Get detailed information about a specific CivitAI model.

    Args:
        model_id: CivitAI model ID (e.g., 4384, 112902)

    Returns:
        Dictionary with detailed model information including:
        - id: Model ID
        - name: Model name
        - type: Model type
        - description: Full description
        - creator: Creator info
        - stats: Download count, rating, favorites, etc.
        - modelVersions: List of all versions with metadata
        - tags: Associated tags
        - nsfw: NSFW flag
    """
    try:
        client = _get_civitai_client()
        model = client.get_model(model_id)

        if not model:
            return {
                "status": "error",
                "error": f"Model not found: {model_id}"
            }

        return {
            "status": "success",
            "model": model
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def civitai_lookup_hash(file_hash: str) -> dict:
    """Look up model version by SHA256 file hash - CRITICAL for LoRA verification.

    This is the AUTHORITATIVE way to identify what base model a LoRA or checkpoint
    is designed for. Use this instead of guessing by file size or filename.

    Example workflow:
    1. Get SHA256 hash of .safetensors file on moira:
       ssh moira "powershell -Command \\"(Get-FileHash -Algorithm SHA256 'path').Hash\\""
    2. Call this tool with the hash
    3. Check returned 'base_model' field (SD 1.5, SDXL, Wan Video 14B t2v/i2v, etc.)

    Args:
        file_hash: SHA256 hash of the .safetensors file (64 hex characters)

    Returns:
        Dictionary with model version details:
        - status: "success" or "error"
        - model_name: Name of the model
        - model_id: CivitAI model ID
        - version_id: Version ID
        - version_name: Version name
        - base_model: Base model (SD 1.5, SDXL, Wan Video 14B t2v/i2v, etc.)
        - trained_words: Trigger words/activation phrases
        - download_url: Download URL
        - files: List of file information

    Example:
        hash_result = await civitai_lookup_hash("abc123...")
        if hash_result["status"] == "success":
            base_model = hash_result["base_model"]
            print(f"This LoRA is for: {base_model}")
    """
    try:
        # Validate hash format
        if not file_hash or len(file_hash) != 64:
            return {
                "status": "error",
                "error": "Invalid SHA256 hash. Must be 64 hexadecimal characters."
            }

        client = _get_civitai_client()
        result = client.get_model_by_hash(file_hash)

        if not result:
            return {
                "status": "error",
                "error": "Hash lookup failed - no response from CivitAI"
            }

        # Check if it's an error response
        if "error" in result:
            return {
                "status": "error",
                "error": result["error"]
            }

        return {
            "status": "success",
            **result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@mcp.tool()
async def civitai_get_download_url(
    model_id: int,
    version_id: Optional[int] = None
) -> dict:
    """Get authenticated download URL for a CivitAI model.

    Args:
        model_id: CivitAI model ID
        version_id: Optional specific version ID (uses latest if not provided)

    Returns:
        Dictionary with download URL:
        - status: "success" or "error"
        - download_url: Authenticated download URL (includes API key if set)
        - model_id: Model ID
        - version_id: Version ID used
        - requires_auth: Whether authentication is required for this model

    Note:
        - Some models require CIVITAI_API_KEY for download
        - NSFW content always requires authentication
        - URL may include temporary authentication token
    """
    try:
        client = _get_civitai_client()

        # Get the model to validate it exists
        model = client.get_model(model_id)
        if not model:
            return {
                "status": "error",
                "error": f"Model not found: {model_id}"
            }

        # Get download URL
        download_url = client.get_download_url(model_id, version_id)

        if not download_url:
            return {
                "status": "error",
                "error": "Failed to get download URL. Model may not have downloadable files."
            }

        # Determine which version was used
        versions = model.get("modelVersions", [])
        if version_id:
            version = next((v for v in versions if v.get("id") == version_id), None)
        else:
            version = versions[0] if versions else None

        actual_version_id = version.get("id") if version else None

        return {
            "status": "success",
            "download_url": download_url,
            "model_id": model_id,
            "version_id": actual_version_id,
            "requires_auth": client.api_key is None and model.get("nsfw", False)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
