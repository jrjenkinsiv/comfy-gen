#!/usr/bin/env python3
"""Click-based CLI for ComfyGen.

This module provides a modern, grouped CLI interface for all ComfyGen functionality.
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can import generate.py
# This is needed when running as installed package (comfy command)
# since generate.py is at project root, not in the package
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import click  # noqa: E402


# Configuration constants (can be overridden with environment variables)
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "http://192.168.1.215:8188")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.1.215:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "comfy-gen")
MOIRA_SSH_USER = os.getenv("MOIRA_SSH_USER", "jrjen")
MOIRA_COMFY_PATH = os.getenv("MOIRA_COMFY_PATH", r"C:\Users\jrjen\comfy")


@click.group()
@click.version_option(version="0.2.0", prog_name="comfy")
def cli():
    """ComfyGen - Programmatic image/video generation using ComfyUI API."""
    pass


# ============================================================================
# GENERATE Commands
# ============================================================================


@cli.group()
def generate():
    """Generate images and videos."""
    pass


@generate.command("image")
@click.option("--workflow", required=True, type=click.Path(exists=True), help="Path to workflow JSON")
@click.option("--prompt", required=True, help="Positive text prompt")
@click.option("--negative-prompt", "-n", default="", help="Negative text prompt (what to avoid)")
@click.option("--output", default="output.png", help="Output image path")
@click.option("--input-image", "-i", help="Input image path (local file or URL) for img2img")
@click.option("--resize", help="Resize input image to WxH (e.g., 512x512)")
@click.option("--crop", type=click.Choice(["center", "cover", "contain"]), help="Crop mode for resize")
@click.option("--denoise", type=float, help="Denoise strength (0.0-1.0) for img2img")
@click.option("--transparent", is_flag=True, help="Generate image with transparent background")
@click.option(
    "--lora", multiple=True, metavar="NAME:STRENGTH", help="Add LoRA with strength (e.g., 'style.safetensors:0.8')"
)
@click.option("--lora-preset", metavar="PRESET_NAME", help="Use a predefined LoRA preset from lora_catalog.yaml")
@click.option("--prompt-preset", metavar="PRESET_NAME", help="Load prompt preset from prompt_catalog.yaml")
@click.option("--steps", type=int, help="Number of sampling steps (1-150, default: 20)")
@click.option("--cfg", type=float, help="Classifier-free guidance scale (1.0-20.0, default: 7.0)")
@click.option("--seed", type=int, help="Random seed for reproducibility (-1 for random)")
@click.option("--width", type=int, help="Output width in pixels (must be divisible by 8)")
@click.option("--height", type=int, help="Output height in pixels (must be divisible by 8)")
@click.option("--sampler", help="Sampler algorithm (e.g., euler, dpmpp_2m)")
@click.option("--scheduler", help="Noise scheduler (e.g., normal, karras)")
@click.option("--preset", help="Use a generation preset (draft, balanced, high-quality)")
@click.option("--validate", is_flag=True, help="Run validation after generation")
@click.option("--no-validate", is_flag=True, help="Disable validation even if config enables it")
@click.option("--auto-retry", is_flag=True, help="Automatically retry if validation fails")
@click.option("--retry-limit", type=int, help="Maximum retry attempts")
@click.option("--positive-threshold", type=float, help="Minimum CLIP score for positive prompt")
@click.option("--quality-score", is_flag=True, help="Run quality scoring after generation")
@click.option("--quality-threshold", type=float, default=7.0, help="Minimum quality score (0-10)")
@click.option("--max-attempts", type=int, default=3, help="Maximum generation attempts")
@click.option(
    "--retry-strategy",
    type=click.Choice(["progressive", "seed_search", "prompt_enhance"]),
    default="progressive",
    help="Retry strategy",
)
@click.option("--enhance-prompt", is_flag=True, help="Enhance prompt using LLM")
@click.option("--enhance-style", metavar="STYLE", help="Style hint for prompt enhancement")
@click.option("--quiet", is_flag=True, help="Suppress progress output")
@click.option("--json-progress", is_flag=True, help="Output machine-readable JSON progress")
@click.option("--no-metadata", is_flag=True, help="Disable JSON metadata sidecar upload")
@click.option("--no-embed-metadata", is_flag=True, help="Disable embedding metadata in PNG files")
@click.option("--dry-run", is_flag=True, help="Validate workflow without generating")
def generate_image(**kwargs):
    """Generate an image (default generation mode)."""
    # Import generate.py main logic and call it with converted args
    from generate import main as generate_main

    # Convert Click kwargs back to sys.argv format for generate.py
    args = []

    # Required args
    args.extend(["--workflow", kwargs["workflow"]])
    if kwargs.get("prompt"):
        args.extend(["--prompt", kwargs["prompt"]])

    # Optional args
    if kwargs.get("negative_prompt"):
        args.extend(["--negative-prompt", kwargs["negative_prompt"]])
    if kwargs.get("output") and kwargs["output"] != "output.png":
        args.extend(["--output", kwargs["output"]])
    if kwargs.get("input_image"):
        args.extend(["--input-image", kwargs["input_image"]])
    if kwargs.get("resize"):
        args.extend(["--resize", kwargs["resize"]])
    if kwargs.get("crop"):
        args.extend(["--crop", kwargs["crop"]])
    if kwargs.get("denoise") is not None:
        args.extend(["--denoise", str(kwargs["denoise"])])
    if kwargs.get("transparent"):
        args.append("--transparent")

    # LoRA args
    for lora in kwargs.get("lora", []):
        args.extend(["--lora", lora])
    if kwargs.get("lora_preset"):
        args.extend(["--lora-preset", kwargs["lora_preset"]])

    # Prompt preset
    if kwargs.get("prompt_preset"):
        args.extend(["--prompt-preset", kwargs["prompt_preset"]])

    # Generation params
    if kwargs.get("steps") is not None:
        args.extend(["--steps", str(kwargs["steps"])])
    if kwargs.get("cfg") is not None:
        args.extend(["--cfg", str(kwargs["cfg"])])
    if kwargs.get("seed") is not None:
        args.extend(["--seed", str(kwargs["seed"])])
    if kwargs.get("width") is not None:
        args.extend(["--width", str(kwargs["width"])])
    if kwargs.get("height") is not None:
        args.extend(["--height", str(kwargs["height"])])
    if kwargs.get("sampler"):
        args.extend(["--sampler", kwargs["sampler"]])
    if kwargs.get("scheduler"):
        args.extend(["--scheduler", kwargs["scheduler"]])
    if kwargs.get("preset"):
        args.extend(["--preset", kwargs["preset"]])

    # Validation args
    if kwargs.get("validate"):
        args.append("--validate")
    if kwargs.get("no_validate"):
        args.append("--no-validate")
    if kwargs.get("auto_retry"):
        args.append("--auto-retry")
    if kwargs.get("retry_limit") is not None:
        args.extend(["--retry-limit", str(kwargs["retry_limit"])])
    if kwargs.get("positive_threshold") is not None:
        args.extend(["--positive-threshold", str(kwargs["positive_threshold"])])

    # Quality args
    if kwargs.get("quality_score"):
        args.append("--quality-score")
    if kwargs.get("quality_threshold") != 7.0:
        args.extend(["--quality-threshold", str(kwargs["quality_threshold"])])
    if kwargs.get("max_attempts") != 3:
        args.extend(["--max-attempts", str(kwargs["max_attempts"])])
    if kwargs.get("retry_strategy") != "progressive":
        args.extend(["--retry-strategy", kwargs["retry_strategy"]])

    # Prompt enhancement
    if kwargs.get("enhance_prompt"):
        args.append("--enhance-prompt")
    if kwargs.get("enhance_style"):
        args.extend(["--enhance-style", kwargs["enhance_style"]])

    # Output control
    if kwargs.get("quiet"):
        args.append("--quiet")
    if kwargs.get("json_progress"):
        args.append("--json-progress")
    if kwargs.get("no_metadata"):
        args.append("--no-metadata")
    if kwargs.get("no_embed_metadata"):
        args.append("--no-embed-metadata")
    if kwargs.get("dry_run"):
        args.append("--dry-run")

    # Call generate.py main with constructed args
    old_argv = sys.argv
    try:
        sys.argv = ["generate.py"] + args
        generate_main()
    finally:
        sys.argv = old_argv


@generate.command("video")
@click.option("--workflow", required=True, type=click.Path(exists=True), help="Path to workflow JSON (Wan 2.2)")
@click.option("--prompt", required=True, help="Motion prompt for video generation")
@click.option("--output", default="output.mp4", help="Output video path")
@click.option("--input-image", "-i", help="Input image for I2V")
@click.option("--steps", type=int, help="Number of sampling steps")
@click.option("--cfg", type=float, help="Classifier-free guidance scale")
@click.option("--seed", type=int, help="Random seed")
@click.option("--quiet", is_flag=True, help="Suppress progress output")
def generate_video(**kwargs):
    """Generate a video using Wan 2.2."""
    # Similar wrapper to generate_image but for video workflows
    from generate import main as generate_main

    args = ["--workflow", kwargs["workflow"], "--prompt", kwargs["prompt"]]

    if kwargs.get("output") and kwargs["output"] != "output.mp4":
        args.extend(["--output", kwargs["output"]])
    if kwargs.get("input_image"):
        args.extend(["--input-image", kwargs["input_image"]])
    if kwargs.get("steps") is not None:
        args.extend(["--steps", str(kwargs["steps"])])
    if kwargs.get("cfg") is not None:
        args.extend(["--cfg", str(kwargs["cfg"])])
    if kwargs.get("seed") is not None:
        args.extend(["--seed", str(kwargs["seed"])])
    if kwargs.get("quiet"):
        args.append("--quiet")

    old_argv = sys.argv
    try:
        sys.argv = ["generate.py"] + args
        generate_main()
    finally:
        sys.argv = old_argv


# ============================================================================
# VALIDATE Command
# ============================================================================


@cli.command()
@click.argument("workflow", type=click.Path(exists=True))
def validate(workflow):
    """Validate a workflow JSON file without generating."""
    from generate import main as generate_main

    old_argv = sys.argv
    try:
        sys.argv = ["generate.py", "--workflow", workflow, "--dry-run", "--prompt", "test"]
        generate_main()
    finally:
        sys.argv = old_argv


# ============================================================================
# GALLERY Commands
# ============================================================================


@cli.group()
def gallery():
    """Browse and manage MinIO gallery."""
    pass


@gallery.command("list")
@click.option("--limit", type=int, default=20, help="Number of recent images to show")
@click.option("--filter", help="Filter by filename pattern")
def gallery_list(limit, filter):
    """List recent generations in MinIO."""
    from minio import Minio
    from minio.error import S3Error

    try:
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

        objects = client.list_objects(BUCKET_NAME)
        items = []

        for obj in objects:
            if filter and filter not in obj.object_name:
                continue
            # Skip metadata files
            if obj.object_name.endswith(".json"):
                continue
            items.append(obj)

        # Sort by last_modified descending
        items.sort(key=lambda x: x.last_modified, reverse=True)
        items = items[:limit]

        if not items:
            click.echo("No images found")
            return

        click.echo(f"Recent {len(items)} images:")
        for obj in items:
            url = f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{obj.object_name}"
            size_kb = obj.size / 1024
            click.echo(f"  {obj.last_modified.strftime('%Y-%m-%d %H:%M:%S')} - {obj.object_name} ({size_kb:.1f} KB)")
            click.echo(f"    {url}")

    except S3Error as e:
        click.echo(f"[ERROR] MinIO error: {e}", err=True)
        sys.exit(1)


@gallery.command("open")
@click.argument("filename")
def gallery_open(filename):
    """Open an image in the default browser."""
    import webbrowser

    url = f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{filename}"
    click.echo(f"Opening {url}")
    webbrowser.open(url)


@gallery.command("delete")
@click.argument("filename")
@click.confirmation_option(prompt="Are you sure you want to delete this image?")
def gallery_delete(filename):
    """Delete an image from MinIO."""
    from minio import Minio
    from minio.error import S3Error

    try:
        client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

        client.remove_object(BUCKET_NAME, filename)
        click.echo(f"[OK] Deleted {filename}")

        # Also try to delete metadata sidecar
        try:
            client.remove_object(BUCKET_NAME, f"{filename}.json")
            click.echo(f"[OK] Deleted metadata {filename}.json")
        except S3Error:
            # Silently ignore if metadata doesn't exist
            pass

    except S3Error as e:
        click.echo(f"[ERROR] MinIO error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# MODELS Commands
# ============================================================================


@cli.group()
def models():
    """Manage models (checkpoints, VAE, etc.)."""
    pass


@models.command("list")
@click.option(
    "--type",
    "model_type",
    type=click.Choice(["checkpoints", "loras", "vae", "all"]),
    default="all",
    help="Filter by model type",
)
def models_list(model_type):
    """List installed models."""
    import requests

    try:
        response = requests.get(f"{COMFYUI_HOST}/object_info", timeout=10)
        if response.status_code != 200:
            click.echo(f"[ERROR] Failed to get model list: HTTP {response.status_code}", err=True)
            sys.exit(1)

        object_info = response.json()

        # Extract models
        models = {}

        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                if "ckpt_name" in checkpoint_info["input"]["required"]:
                    models["checkpoints"] = checkpoint_info["input"]["required"]["ckpt_name"][0]

        if "LoraLoader" in object_info:
            lora_info = object_info["LoraLoader"]
            if "input" in lora_info and "required" in lora_info["input"]:
                if "lora_name" in lora_info["input"]["required"]:
                    models["loras"] = lora_info["input"]["required"]["lora_name"][0]

        if "VAELoader" in object_info:
            vae_info = object_info["VAELoader"]
            if "input" in vae_info and "required" in vae_info["input"]:
                if "vae_name" in vae_info["input"]["required"]:
                    models["vae"] = vae_info["input"]["required"]["vae_name"][0]

        # Display models
        if model_type == "all":
            for mtype, mlist in models.items():
                click.echo(f"\n{mtype.upper()}:")
                for m in sorted(mlist):
                    click.echo(f"  - {m}")
        else:
            if model_type in models:
                click.echo(f"{model_type.upper()}:")
                for m in sorted(models[model_type]):
                    click.echo(f"  - {m}")
            else:
                click.echo(f"No {model_type} found")

    except requests.RequestException as e:
        click.echo(f"[ERROR] Failed to connect to ComfyUI: {e}", err=True)
        sys.exit(1)


@models.command("info")
@click.argument("model_name")
def models_info(model_name):
    """Get information about a specific model."""
    # TODO: Implement model info retrieval
    click.echo(f"Model info for: {model_name}")
    click.echo("(Not yet implemented - will show file size, hash, metadata)")


@models.command("download")
@click.argument("model_id")
@click.option("--source", type=click.Choice(["civitai", "huggingface"]), required=True, help="Download source")
def models_download(model_id, source):
    """Download a model from CivitAI or HuggingFace."""
    # TODO: Implement model download
    if source == "civitai":
        click.echo(f"Downloading model {model_id} from CivitAI...")
        click.echo("(Use 'comfy civitai' commands for now)")
    else:
        click.echo(f"Downloading model {model_id} from HuggingFace...")
        click.echo("(Use 'comfy hf' commands for now)")


# ============================================================================
# LORAS Commands
# ============================================================================


@cli.group()
def loras():
    """Manage LoRA adapters."""
    pass


@loras.command("list")
@click.option("--preset", help="Show LoRAs in a specific preset")
def loras_list(preset):
    """List available LoRAs and presets."""
    from generate import list_available_loras, load_lora_presets

    if preset:
        # Show specific preset
        catalog = load_lora_presets()
        if catalog and "model_suggestions" in catalog:
            if preset in catalog["model_suggestions"]:
                preset_data = catalog["model_suggestions"][preset]
                click.echo(f"LoRA preset '{preset}':")
                if "default_loras" in preset_data:
                    for lora_name in preset_data["default_loras"]:
                        click.echo(f"  - {lora_name}")
            else:
                click.echo(f"Preset '{preset}' not found")
                click.echo(f"Available presets: {', '.join(catalog['model_suggestions'].keys())}")
        return

    # List all LoRAs
    available_loras = list_available_loras()
    if available_loras:
        click.echo(f"Available LoRAs ({len(available_loras)}):")
        for lora in sorted(available_loras):
            click.echo(f"  - {lora}")
    else:
        click.echo("No LoRAs found")

    # List presets
    catalog = load_lora_presets()
    if catalog and "model_suggestions" in catalog:
        presets = catalog["model_suggestions"]
        if presets:
            click.echo(f"\nAvailable presets:")
            for preset_name in sorted(presets.keys()):
                click.echo(f"  - {preset_name}")


@loras.command("verify")
@click.argument("lora_file")
def loras_verify(lora_file):
    """Verify LoRA base model via CivitAI hash lookup."""
    from scripts.civitai_audit import audit_lora

    click.echo(f"Verifying {lora_file}...")
    result = audit_lora(lora_file)

    if result.get("status") == "found":
        click.echo(f"[OK] Found on CivitAI:")
        click.echo(f"  Model: {result.get('civitai_model_name')}")
        click.echo(f"  Base Model: {result.get('base_model')}")
        if result.get("trained_words"):
            click.echo(f"  Trained Words: {', '.join(result['trained_words'])}")
    elif result.get("status") == "not_found":
        click.echo(f"[WARN] Not found on CivitAI")
    else:
        click.echo(f"[ERROR] Verification failed: {result.get('status')}")


@loras.command("catalog")
@click.option("--update", is_flag=True, help="Update lora_catalog.yaml from server")
def loras_catalog(update):
    """Show or update LoRA catalog."""
    import yaml

    if update:
        # TODO: Implement catalog update
        click.echo("Updating lora_catalog.yaml...")
        click.echo("(Not yet implemented)")
    else:
        catalog_path = Path("lora_catalog.yaml")
        if catalog_path.exists():
            with open(catalog_path) as f:
                catalog = yaml.safe_load(f)
            click.echo(yaml.dump(catalog, default_flow_style=False))
        else:
            click.echo("lora_catalog.yaml not found")


# ============================================================================
# CIVITAI Commands
# ============================================================================


@cli.group()
def civitai():
    """CivitAI model discovery and download."""
    pass


@civitai.command("search")
@click.argument("query")
@click.option("--type", "model_type", help="Filter by type (Checkpoint, LORA, VAE)")
@click.option("--base-model", help="Filter by base model (SD 1.5, SDXL)")
@click.option("--limit", type=int, default=10, help="Maximum results")
@click.option("--nsfw", is_flag=True, default=True, help="Include NSFW results")
def civitai_search(query, model_type, base_model, limit, nsfw):
    """Search models on CivitAI."""
    from comfygen.civitai_client import CivitAIClient

    client = CivitAIClient()
    results = client.search_models(query=query, model_type=model_type, base_model=base_model, nsfw=nsfw, limit=limit)

    if not results:
        click.echo("No results found")
        return

    click.echo(f"Found {len(results)} models:\n")
    for r in results:
        click.echo(f"[{r['id']}] {r['name']}")
        click.echo(f"  Type: {r['type']} | Base: {r['base_model']}")
        click.echo(f"  Creator: {r['creator']} | Downloads: {r['downloads']}")
        if r["description"]:
            desc = r["description"][:100] + "..." if len(r["description"]) > 100 else r["description"]
            click.echo(f"  {desc}")
        click.echo()


@civitai.command("info")
@click.argument("model_id", type=int)
def civitai_info(model_id):
    """Get detailed information about a model by ID."""
    from comfygen.civitai_client import CivitAIClient

    client = CivitAIClient()
    info = client.get_model_info(model_id)

    if not info:
        click.echo(f"Model {model_id} not found")
        return

    click.echo(f"Model: {info['name']}")
    click.echo(f"ID: {info['id']}")
    click.echo(f"Type: {info['type']}")
    click.echo(f"Creator: {info['creator']}")
    click.echo(f"Downloads: {info['downloads']}")
    click.echo(f"Rating: {info['rating']}")
    if info.get("versions"):
        click.echo(f"\nVersions:")
        for v in info["versions"][:5]:
            click.echo(f"  - {v.get('name')} (Base: {v.get('base_model')})")


@civitai.command("lookup")
@click.argument("hash_value")
def civitai_lookup(hash_value):
    """Look up a model by SHA256 hash (for verification)."""
    from comfygen.civitai_client import CivitAIClient

    client = CivitAIClient()
    info = client.lookup_by_hash(hash_value)

    if not info:
        click.echo(f"No model found with hash {hash_value}")
        return

    click.echo(f"Model: {info['name']}")
    click.echo(f"ID: {info['id']}")
    click.echo(f"Base Model: {info['base_model']}")
    if info.get("trained_words"):
        click.echo(f"Trained Words: {', '.join(info['trained_words'])}")


# ============================================================================
# HF (HuggingFace) Commands
# ============================================================================


@cli.group()
def hf():
    """HuggingFace Hub integration."""
    pass


@hf.command("search")
@click.argument("query", required=False)
@click.option("--library", help="Filter by library (diffusers, transformers)")
@click.option("--tags", multiple=True, help="Filter by tags")
@click.option("--limit", type=int, default=10, help="Maximum results")
def hf_search(query, library, tags, limit):
    """Search models on HuggingFace Hub."""
    from comfygen.huggingface_client import HuggingFaceClient

    client = HuggingFaceClient()
    results = client.search_models(query=query, library=library, tags=list(tags) if tags else None, limit=limit)

    if not results:
        click.echo("No results found")
        return

    click.echo(f"Found {len(results)} models:\n")
    for r in results:
        click.echo(f"{r['id']}")
        click.echo(f"  Author: {r['author']} | Downloads: {r['downloads']} | Likes: {r['likes']}")
        if r.get("tags"):
            click.echo(f"  Tags: {', '.join(r['tags'][:5])}")
        click.echo()


@hf.command("info")
@click.argument("model_id")
def hf_info(model_id):
    """Get detailed information about a HuggingFace model."""
    from comfygen.huggingface_client import HuggingFaceClient

    client = HuggingFaceClient()
    info = client.get_model_info(model_id)

    if not info:
        click.echo(f"Model {model_id} not found")
        return

    click.echo(f"Model: {info['id']}")
    click.echo(f"Author: {info['author']}")
    click.echo(f"Downloads: {info['downloads']}")
    click.echo(f"Likes: {info['likes']}")
    if info.get("tags"):
        click.echo(f"Tags: {', '.join(info['tags'])}")
    if info.get("pipeline_tag"):
        click.echo(f"Pipeline: {info['pipeline_tag']}")


@hf.command("download")
@click.argument("model_id")
@click.argument("filename")
@click.option("--output", help="Output path (default: current directory)")
def hf_download(model_id, filename, output):
    """Download a model file from HuggingFace Hub."""
    from comfygen.huggingface_client import HuggingFaceClient

    client = HuggingFaceClient()
    path = client.download_file(model_id, filename, cache_dir=output)

    if path:
        click.echo(f"[OK] Downloaded to: {path}")
    else:
        click.echo(f"[ERROR] Download failed", err=True)
        sys.exit(1)


# ============================================================================
# SERVER Commands
# ============================================================================


@cli.group()
def server():
    """ComfyUI server management."""
    pass


@server.command("status")
def server_status():
    """Check ComfyUI server status."""
    import requests

    try:
        response = requests.get(f"{COMFYUI_HOST}/system_stats", timeout=5)
        if response.status_code == 200:
            click.echo("[OK] ComfyUI server is running")
            stats = response.json()
            if stats:
                click.echo(f"System stats: {stats}")
        else:
            click.echo(f"[WARN] Server returned status {response.status_code}")
    except requests.ConnectionError:
        click.echo(f"[ERROR] Cannot connect to ComfyUI at {COMFYUI_HOST}", err=True)
        sys.exit(1)
    except requests.Timeout:
        click.echo(f"[ERROR] Connection timeout", err=True)
        sys.exit(1)


@server.command("start")
def server_start():
    """Start ComfyUI server on moira (requires SSH access)."""
    import subprocess

    venv_python = f"{MOIRA_COMFY_PATH}\\.venv\\Scripts\\python.exe"
    start_script = f"{MOIRA_COMFY_PATH}\\..\\comfy-gen\\scripts\\start_comfyui.py"
    cmd = f'ssh moira "{venv_python} {start_script}"'

    click.echo("Starting ComfyUI on moira...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        click.echo(result.stdout)
        if result.returncode != 0:
            click.echo(result.stderr, err=True)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        click.echo("[WARN] Command timed out (server may still be starting)")
    except Exception as e:
        click.echo(f"[ERROR] Failed to start server: {e}", err=True)
        sys.exit(1)


@server.command("stop")
def server_stop():
    """Stop ComfyUI server on moira."""
    # TODO: Implement server stop via SSH task kill
    click.echo("Stopping ComfyUI server...")
    click.echo("(Not yet implemented - requires SSH task kill)")


# ============================================================================
# CONFIG Commands
# ============================================================================


@cli.group()
def config():
    """Configuration management."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    import yaml

    config_files = ["presets.yaml", "lora_catalog.yaml", "prompt_catalog.yaml"]

    for config_file in config_files:
        path = Path(config_file)
        if path.exists():
            click.echo(f"\n=== {config_file} ===")
            with open(path) as f:
                data = yaml.safe_load(f)
            click.echo(yaml.dump(data, default_flow_style=False))


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a configuration value."""
    # TODO: Implement configuration setting
    click.echo(f"Setting {key} = {value}")
    click.echo("(Not yet implemented)")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
