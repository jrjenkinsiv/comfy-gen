"""Generation request and response schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GenerationStatus(str, Enum):
    """Status of a generation request."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressInfo(BaseModel):
    """Progress information for a running generation."""

    current_step: int = Field(description="Current step number")
    total_steps: int = Field(description="Total steps")
    percent: float = Field(description="Completion percentage 0-1")
    preview_url: str | None = Field(default=None, description="Preview image URL if available")

    model_config = {"json_schema_extra": {"example": {"current_step": 15, "total_steps": 30, "percent": 0.5}}}


class GenerationRequest(BaseModel):
    """Request to generate an image."""

    # Required
    prompt: str = Field(description="Text prompt for generation (may include @tags)")

    # Optional generation parameters
    negative_prompt: str = Field(
        default="blurry, low quality, watermark, text, bad anatomy",
        description="Negative prompt to avoid unwanted elements",
    )
    workflow: str = Field(default="flux-dev.json", description="Workflow file to use")
    width: int = Field(default=1024, ge=64, le=4096, description="Output width in pixels")
    height: int = Field(default=1024, ge=64, le=4096, description="Output height in pixels")
    steps: int = Field(default=30, ge=1, le=150, description="Number of sampling steps")
    cfg: float = Field(default=7.5, ge=1.0, le=30.0, description="CFG scale")
    seed: int = Field(default=-1, description="Random seed (-1 for random)")

    # Category/composition options
    categories: list[str] = Field(default_factory=list, description="Explicit category IDs to use")
    policy_tier: str = Field(
        default="general",
        description="Content policy tier: general, mature, or explicit",
    )

    # LoRA configuration
    loras: list[dict[str, Any]] | None = Field(
        default=None, description="Manual LoRA configuration: [{'filename': 'x.safetensors', 'strength': 0.8}]"
    )

    # Output options
    output_filename: str | None = Field(default=None, description="Custom output filename")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompt": "@portrait professional headshot of a woman",
                "negative_prompt": "blurry, low quality",
                "workflow": "flux-dev.json",
                "width": 1024,
                "height": 1024,
                "steps": 30,
                "cfg": 7.5,
                "categories": ["portrait"],
                "policy_tier": "general",
            }
        }
    }


class GenerationResponse(BaseModel):
    """Response from a generation request."""

    generation_id: str = Field(description="Unique ID for this generation")
    status: GenerationStatus = Field(description="Current status")
    message: str | None = Field(default=None, description="Status message or error")

    # Progress (when running)
    progress: ProgressInfo | None = Field(default=None, description="Progress info when running")

    # Result (when completed)
    image_url: str | None = Field(default=None, description="Output image URL when completed")
    recipe_hash: str | None = Field(default=None, description="Hash of the recipe used")

    # Metadata (when completed)
    categories_used: list[str] | None = Field(default=None, description="Categories that were applied")
    generation_time: float | None = Field(default=None, description="Generation time in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "generation_id": "abc123-def456",
                "status": "queued",
                "message": "Generation queued. Poll GET /api/v1/generate/{id} for status.",
            }
        }
    }
