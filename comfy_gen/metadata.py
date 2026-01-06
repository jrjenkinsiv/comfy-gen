"""Metadata handling for ComfyGen - embedding and extracting metadata from PNG files.

This module provides functions for embedding comprehensive generation metadata directly
into PNG image files using PNG text chunks (tEXt/iTXt), following CivitAI's format for
interoperability.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image
from PIL.PngImagePlugin import PngInfo


def embed_metadata_in_png(image_path: str, metadata: Dict[str, Any], output_path: Optional[str] = None) -> bool:
    """Embed metadata into PNG file using PNG text chunks.

    Embeds comprehensive generation metadata into PNG files using both:
    - PNG tEXt chunks for simple key-value pairs
    - CivitAI-compatible "parameters" field for broad compatibility

    Args:
        image_path: Path to the input PNG file
        metadata: Metadata dictionary (nested format from create_metadata_json)
        output_path: Optional output path. If None, overwrites input file.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Open the image
        img = Image.open(image_path)

        # Create PngInfo object for metadata
        png_info = PngInfo()

        # Embed full JSON metadata
        png_info.add_text("comfygen_metadata", json.dumps(metadata, indent=2))

        # Add CivitAI-compatible "parameters" field
        # This makes the metadata readable by CivitAI and other tools
        civitai_params = format_civitai_parameters(metadata)
        png_info.add_text("parameters", civitai_params)

        # Add individual fields for easy access by viewers
        if "input" in metadata:
            if metadata["input"].get("prompt"):
                png_info.add_text("prompt", metadata["input"]["prompt"])
            if metadata["input"].get("negative_prompt"):
                png_info.add_text("negative_prompt", metadata["input"]["negative_prompt"])

        if "workflow" in metadata:
            if metadata["workflow"].get("model"):
                png_info.add_text("model", metadata["workflow"]["model"])

        if "parameters" in metadata:
            params = metadata["parameters"]
            if params.get("seed") is not None:
                png_info.add_text("seed", str(params["seed"]))
            if params.get("steps") is not None:
                png_info.add_text("steps", str(params["steps"]))
            if params.get("cfg") is not None:
                png_info.add_text("cfg", str(params["cfg"]))
            if params.get("sampler"):
                png_info.add_text("sampler", params["sampler"])

        # Determine output path
        out_path = output_path if output_path else image_path

        # Save with embedded metadata
        img.save(out_path, "PNG", pnginfo=png_info)

        return True

    except Exception as e:
        print(f"[ERROR] Failed to embed metadata in PNG: {e}")
        return False


def format_civitai_parameters(metadata: Dict[str, Any]) -> str:
    """Format metadata as CivitAI-compatible parameters string.

    CivitAI uses a specific format for generation parameters:
    "prompt, negative prompt: ..., Steps: X, Sampler: Y, CFG scale: Z, Seed: N, Size: WxH, Model: ..."

    Args:
        metadata: Nested metadata dictionary

    Returns:
        str: CivitAI-formatted parameters string
    """
    parts = []

    # Start with prompt
    if "input" in metadata and metadata["input"].get("prompt"):
        parts.append(metadata["input"]["prompt"])

    # Add negative prompt
    if "input" in metadata and metadata["input"].get("negative_prompt"):
        parts.append(f"Negative prompt: {metadata['input']['negative_prompt']}")

    # Add generation parameters
    param_parts = []

    if "parameters" in metadata:
        params = metadata["parameters"]

        if params.get("steps") is not None:
            param_parts.append(f"Steps: {params['steps']}")

        if params.get("sampler"):
            param_parts.append(f"Sampler: {params['sampler']}")

        if params.get("cfg") is not None:
            param_parts.append(f"CFG scale: {params['cfg']}")

        if params.get("seed") is not None:
            param_parts.append(f"Seed: {params['seed']}")

        if params.get("resolution"):
            width, height = params["resolution"]
            param_parts.append(f"Size: {width}x{height}")

    # Add workflow information
    if "workflow" in metadata:
        if metadata["workflow"].get("model"):
            param_parts.append(f"Model: {metadata['workflow']['model']}")

        if metadata["workflow"].get("vae"):
            param_parts.append(f"VAE: {metadata['workflow']['vae']}")

    # Add LoRAs if present
    if "parameters" in metadata and metadata["parameters"].get("loras"):
        loras = metadata["parameters"]["loras"]
        for lora in loras:
            lora_name = lora.get("name", "unknown")
            lora_strength = lora.get("strength", 1.0)
            param_parts.append(f"Lora: {lora_name}:{lora_strength}")

    # Join parameter parts
    if param_parts:
        parts.append(", ".join(param_parts))

    return ", ".join(parts)


def read_metadata_from_png(image_path: str) -> Optional[Dict[str, Any]]:
    """Read embedded metadata from PNG file.

    Attempts to read metadata from PNG text chunks, prioritizing the
    comfygen_metadata field which contains the full nested structure.

    Args:
        image_path: Path to the PNG file

    Returns:
        dict: Metadata dictionary if found, None otherwise
    """
    try:
        img = Image.open(image_path)

        # Check if it's a PNG - silently return None for other formats
        # (this is expected behavior, not an error)
        if img.format != "PNG":
            return None

        # Get PNG info
        png_info = img.info

        # Try to read comfygen_metadata first (full nested format)
        if "comfygen_metadata" in png_info:
            try:
                metadata = json.loads(png_info["comfygen_metadata"])
                return metadata
            except json.JSONDecodeError as e:
                print(f"[WARN] Failed to parse comfygen_metadata: {e}")

        # Fall back to reading individual fields
        metadata = {}

        # Try to reconstruct from individual fields
        if "prompt" in png_info or "parameters" in png_info:
            metadata["input"] = {
                "prompt": png_info.get("prompt", ""),
                "negative_prompt": png_info.get("negative_prompt", ""),
                "preset": None,
            }

            metadata["workflow"] = {"name": None, "model": png_info.get("model"), "vae": None}

            metadata["parameters"] = {
                "seed": int(png_info["seed"]) if "seed" in png_info else None,
                "steps": int(png_info["steps"]) if "steps" in png_info else None,
                "cfg": float(png_info["cfg"]) if "cfg" in png_info else None,
                "sampler": png_info.get("sampler"),
                "scheduler": None,
                "resolution": None,
                "loras": [],
            }

            return metadata if metadata["input"]["prompt"] else None

        return None

    except Exception as e:
        print(f"[ERROR] Failed to read metadata from PNG: {e}")
        return None


def get_comfyui_version() -> Optional[str]:
    """Get ComfyUI server version.

    Queries the ComfyUI API to get the server version information.

    Returns:
        str: Version string if available, None otherwise
    """
    try:
        import requests
        import os

        # ComfyUI host from environment or default
        comfyui_host = os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188")

        response = requests.get(f"{comfyui_host}/system_stats", timeout=5)

        if response.status_code == 200:
            stats = response.json()
            # ComfyUI doesn't always expose version in system_stats
            # Try to get it from the response or return a placeholder
            return stats.get("version", "unknown")

        return None

    except Exception as e:
        print(f"[WARN] Failed to get ComfyUI version: {e}")
        return None


def format_metadata_for_display(metadata: Dict[str, Any]) -> str:
    """Format metadata for human-readable display.

    Args:
        metadata: Metadata dictionary (nested format)

    Returns:
        str: Formatted metadata string
    """
    lines = []

    lines.append("=== Generation Metadata ===\n")

    # Timestamp and ID
    if "timestamp" in metadata:
        lines.append(f"Timestamp: {metadata['timestamp']}")
    if "generation_id" in metadata:
        lines.append(f"Generation ID: {metadata['generation_id']}")

    # Input
    if "input" in metadata:
        lines.append("\n[Input]")
        lines.append(f"Prompt: {metadata['input'].get('prompt', 'N/A')}")
        if metadata["input"].get("negative_prompt"):
            lines.append(f"Negative: {metadata['input']['negative_prompt']}")
        if metadata["input"].get("preset"):
            lines.append(f"Preset: {metadata['input']['preset']}")

    # Workflow
    if "workflow" in metadata:
        lines.append("\n[Workflow]")
        if metadata["workflow"].get("name"):
            lines.append(f"Name: {metadata['workflow']['name']}")
        if metadata["workflow"].get("model"):
            lines.append(f"Model: {metadata['workflow']['model']}")
        if metadata["workflow"].get("vae"):
            lines.append(f"VAE: {metadata['workflow']['vae']}")

    # Parameters
    if "parameters" in metadata:
        params = metadata["parameters"]
        lines.append("\n[Parameters]")
        if params.get("seed") is not None:
            lines.append(f"Seed: {params['seed']}")
        if params.get("steps") is not None:
            lines.append(f"Steps: {params['steps']}")
        if params.get("cfg") is not None:
            lines.append(f"CFG: {params['cfg']}")
        if params.get("sampler"):
            lines.append(f"Sampler: {params['sampler']}")
        if params.get("scheduler"):
            lines.append(f"Scheduler: {params['scheduler']}")
        if params.get("resolution"):
            width, height = params["resolution"]
            lines.append(f"Resolution: {width}x{height}")

        if params.get("loras"):
            lines.append("\nLoRAs:")
            for lora in params["loras"]:
                lines.append(f"  - {lora.get('name', 'unknown')} (strength: {lora.get('strength', 1.0)})")

    # Quality
    if "quality" in metadata and metadata["quality"].get("composite_score") is not None:
        lines.append("\n[Quality]")
        if metadata["quality"].get("composite_score") is not None:
            lines.append(f"Score: {metadata['quality']['composite_score']}/10")
        if metadata["quality"].get("grade"):
            lines.append(f"Grade: {metadata['quality']['grade']}")

    # Storage
    if "storage" in metadata:
        storage = metadata["storage"]
        lines.append("\n[Storage]")
        if storage.get("file_size_bytes") is not None:
            mb = storage["file_size_bytes"] / (1024 * 1024)
            lines.append(f"File Size: {mb:.2f} MB")
        if storage.get("format"):
            lines.append(f"Format: {storage['format']}")
        if storage.get("generation_time_seconds") is not None:
            lines.append(f"Generation Time: {storage['generation_time_seconds']:.1f}s")
        if storage.get("minio_url"):
            lines.append(f"URL: {storage['minio_url']}")

    return "\n".join(lines)
