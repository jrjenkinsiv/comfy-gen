#!/usr/bin/env python3
"""
Click CLI for ComfyGen - uses typed client to call API.

This replaces direct generate.py calls with proper API calls via ComfyGenClient.
All business logic lives in the API; CLI is just a thin presentation layer.

Usage:
    # Start the API server (in another terminal)
    python -m comfy_gen.api.app

    # Then use CLI
    comfygen generate --prompt "a sunset" --workflow flux-dev.json
    comfygen status <generation_id>
    comfygen health
"""

import os
import sys

import click

from ..api.schemas.generation import GenerationRequest, GenerationStatus
from ..client import ComfyGenClient, ComfyGenError

# Configuration
API_URL = os.getenv("COMFYGEN_API_URL", "http://localhost:8000")


def get_client() -> ComfyGenClient:
    """Get a configured client instance."""
    return ComfyGenClient(base_url=API_URL)


@click.group()
@click.version_option(version="1.0.0", prog_name="comfygen")
@click.option(
    "--api-url",
    envvar="COMFYGEN_API_URL",
    default="http://localhost:8000",
    help="API server URL",
)
@click.pass_context
def cli(ctx: click.Context, api_url: str) -> None:
    """
    ComfyGen CLI - Intelligent image generation via ComfyUI.

    Requires the API server to be running. Start it with:

        python -m comfy_gen.api.app

    Then use this CLI to queue generations, check status, and more.
    """
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url


# ============================================================================
# HEALTH COMMANDS
# ============================================================================


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check API and ComfyUI server health."""
    client = ComfyGenClient(base_url=ctx.obj["api_url"])
    try:
        result = client.health()
        click.echo(click.style("[OK] ", fg="green") + "API server is healthy")
        click.echo(f"  ComfyUI: {result.get('comfyui', 'unknown')}")
        click.echo(f"  MinIO: {result.get('minio', 'unknown')}")
    except ComfyGenError as e:
        click.echo(click.style("[ERROR] ", fg="red") + str(e), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style("[ERROR] ", fg="red") + f"API server unreachable: {e}", err=True)
        sys.exit(1)
    finally:
        client.close()


# ============================================================================
# GENERATE COMMANDS
# ============================================================================


@cli.command()
@click.option("--prompt", "-p", required=True, help="Positive prompt for generation")
@click.option("--negative-prompt", "-n", default="", help="Negative prompt (what to avoid)")
@click.option(
    "--workflow",
    "-w",
    default="flux-dev.json",
    help="Workflow file to use (default: flux-dev.json)",
)
@click.option("--steps", type=int, default=30, help="Number of sampling steps")
@click.option("--cfg", type=float, default=7.5, help="CFG scale (guidance strength)")
@click.option("--width", type=int, default=1024, help="Output width")
@click.option("--height", type=int, default=1024, help="Output height")
@click.option("--seed", type=int, default=-1, help="Random seed (-1 for random)")
@click.option(
    "--categories",
    "-c",
    multiple=True,
    help="Categories to use for intelligent composition (e.g., @car @night)",
)
@click.option(
    "--lora",
    multiple=True,
    metavar="NAME:STRENGTH",
    help="Add LoRA (e.g., 'add_detail.safetensors:0.8')",
)
@click.option("--wait/--no-wait", default=True, help="Wait for completion (default: yes)")
@click.option("--poll-interval", type=float, default=1.0, help="Seconds between status polls")
@click.option("--timeout", type=float, default=300.0, help="Maximum wait time in seconds")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON response")
@click.pass_context
def generate(
    ctx: click.Context,
    prompt: str,
    negative_prompt: str,
    workflow: str,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    seed: int,
    categories: tuple[str, ...],
    lora: tuple[str, ...],
    wait: bool,
    poll_interval: float,
    timeout: float,
    json_output: bool,
) -> None:
    """
    Queue an image generation.

    Examples:

        # Simple generation
        comfygen generate -p "a sunset over mountains"

        # With categories (intelligent composition)
        comfygen generate -p "red ferrari" -c @car -c @night -c @city

        # With LoRAs
        comfygen generate -p "portrait" --lora "add_detail:0.8" --lora "skin_texture:0.5"

        # Don't wait, just queue
        comfygen generate -p "quick test" --no-wait

    \b
    Returns:
        If --wait: Full result with image_url
        If --no-wait: Just the generation_id for polling
    """
    # Parse LoRAs from NAME:STRENGTH format
    loras = []
    for lora_spec in lora:
        if ":" in lora_spec:
            name, strength = lora_spec.rsplit(":", 1)
            loras.append({"filename": name, "strength": float(strength)})
        else:
            loras.append({"filename": lora_spec, "strength": 0.8})

    # Parse categories (strip @ prefix if present)
    parsed_categories = [c.lstrip("@") for c in categories]

    # Build request
    request = GenerationRequest(
        prompt=prompt,
        negative_prompt=negative_prompt,
        workflow=workflow,
        steps=steps,
        cfg=cfg,
        width=width,
        height=height,
        seed=seed,
        categories=parsed_categories if parsed_categories else None,
        loras=loras if loras else None,
    )

    client = ComfyGenClient(base_url=ctx.obj["api_url"])
    try:
        # Queue the generation
        response = client.generate(request)

        if not wait:
            # Just return the generation ID
            if json_output:
                click.echo(response.model_dump_json(indent=2))
            else:
                click.echo(f"Generation queued: {response.generation_id}")
                click.echo(f"Poll status with: comfygen status {response.generation_id}")
            return

        # Wait for completion with progress display
        click.echo(f"Generation {response.generation_id} queued...")

        with click.progressbar(
            length=steps,
            label="Generating",
            show_eta=True,
        ) as bar:
            last_step = 0
            while True:
                status = client.get_generation_status(response.generation_id)

                if status.progress:
                    new_step = status.progress.current_step
                    if new_step > last_step:
                        bar.update(new_step - last_step)
                        last_step = new_step

                if status.status == GenerationStatus.COMPLETED:
                    bar.update(steps - last_step)  # Complete the bar
                    break
                elif status.status == GenerationStatus.FAILED:
                    raise ComfyGenError(status.message or "Generation failed")

                import time

                time.sleep(poll_interval)

        # Show result
        if json_output:
            click.echo(status.model_dump_json(indent=2))
        else:
            click.echo()
            click.echo(click.style("[OK] ", fg="green") + "Generation complete!")
            click.echo(f"  Image URL: {status.image_url}")
            if status.generation_time:
                click.echo(f"  Time: {status.generation_time:.2f}s")

    except ComfyGenError as e:
        click.echo(click.style("[ERROR] ", fg="red") + str(e), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style("[ERROR] ", fg="red") + f"Unexpected error: {e}", err=True)
        sys.exit(1)
    finally:
        client.close()


@cli.command()
@click.argument("generation_id")
@click.option("--json", "json_output", is_flag=True, help="Output raw JSON")
@click.pass_context
def status(ctx: click.Context, generation_id: str, json_output: bool) -> None:
    """
    Check the status of a generation.

    GENERATION_ID is the ID returned from 'comfygen generate'.
    """
    client = ComfyGenClient(base_url=ctx.obj["api_url"])
    try:
        result = client.get_generation_status(generation_id)

        if json_output:
            click.echo(result.model_dump_json(indent=2))
        else:
            status_colors = {
                GenerationStatus.QUEUED: "yellow",
                GenerationStatus.RUNNING: "blue",
                GenerationStatus.COMPLETED: "green",
                GenerationStatus.FAILED: "red",
                GenerationStatus.CANCELLED: "magenta",
            }
            color = status_colors.get(result.status, "white")
            click.echo(f"Status: {click.style(result.status.value, fg=color)}")

            if result.progress:
                pct = result.progress.percent * 100
                click.echo(f"Progress: {result.progress.current_step}/{result.progress.total_steps} ({pct:.0f}%)")
                if result.progress.current_node:
                    click.echo(f"Current node: {result.progress.current_node}")

            if result.image_url:
                click.echo(f"Image URL: {result.image_url}")

            if result.generation_time:
                click.echo(f"Generation time: {result.generation_time:.2f}s")

            if result.message:
                click.echo(f"Message: {result.message}")

    except ComfyGenError as e:
        click.echo(click.style("[ERROR] ", fg="red") + str(e), err=True)
        sys.exit(1)
    finally:
        client.close()


@cli.command()
@click.argument("generation_id")
@click.pass_context
def cancel(ctx: click.Context, generation_id: str) -> None:
    """
    Cancel a queued or running generation.

    GENERATION_ID is the ID returned from 'comfygen generate'.
    """
    client = ComfyGenClient(base_url=ctx.obj["api_url"])
    try:
        client.cancel_generation(generation_id)
        click.echo(click.style("[OK] ", fg="green") + f"Cancelled generation {generation_id}")
    except ComfyGenError as e:
        click.echo(click.style("[ERROR] ", fg="red") + str(e), err=True)
        sys.exit(1)
    finally:
        client.close()


# ============================================================================
# ENTRY POINT
# ============================================================================


def main() -> None:
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
